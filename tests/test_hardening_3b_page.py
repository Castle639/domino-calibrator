"""Round 3 of the hardening, Part B, the page's share (the third hardening round's record of 28 Sept 2026, not in this repository, Part B): the page's
engine (page/zeroap.js, through Node) and the page itself in a headless browser (page/browser_cases.js), for the fifth
invitation's item 6 as the sixth invitation lists it (the sixth invitation, of 28 Sept 2026, not in this repository), numbered as Annie's
check tables in the refuters' second record of 28 Sept 2026, not in this repository. Written to fail on the calibrator as the fifth room's pull
request merged it (847d438, whose calibrator is 7416259's) and to pass once each fix is in; every case is a subTest. T1.20's
two tests pass on 847d438 by construction (they strengthen weak tests of code that is right): the bar's mutant check shows
each failing where the old tests pass.
"""
import os, re, gzip, json, shutil, tempfile, unittest, warnings, subprocess
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from domino_calibrator import cli
from tests.test_hardening import pig, comet, write, REC, mpc_judge, ADES_PYLIB, ADES_MASTER
from tests.test_hardening_page import js, fits_bytes, PAGE, NODE, PW, REC_PAGE
from tests.test_hardening_2_page import PARSE, TAN, wcs_verdicts
from tests.test_hardening_2 import record_row
from tests.test_hardening_3b import wat, HALF

REC3 = dict(REC_PAGE, measurers='; '.join(REC['measurers']))              # names are separated by semicolons (round 2)
HTML = os.path.join(PAGE, 'index.html')


def with_cards(path, cards):
    """The FITS file at path with header cards written over, as raw 80-byte images: {keyword: image}."""
    b = bytearray(open(path, 'rb').read())
    for key, image in cards.items():
        k = key.ljust(8).encode('ascii')
        at = next(i for i in range(0, len(b), 80) if b[i:i + 8] == k)
        b[at:at + 80] = image.ljust(80).encode('ascii')
    open(path, 'wb').write(bytes(b))
    return path


def pixels(img):
    """The image for Node: NaN as null, infinities by name (JSON has neither)."""
    return [None if np.isnan(v) else ('inf' if v == np.inf else ('-inf' if v == -np.inf else float(v))) for v in img.ravel()]


START_JS = ("const im = Float64Array.from(D.img.map(v => v === null ? NaN : (v === 'inf' ? Infinity : (v === '-inf' ? -Infinity : v))));"
            "out = Z.brightestStart(im, D.nx, D.ny);")


@unittest.skipIf(NODE is None, 'no node')
class TestPageEngine3b(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore')
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def p(self, name):
        return os.path.join(self.d, name)

    def test_t4_8_a_gzipped_or_non_fits_file_is_named(self):
        # 847d438: the reader stopped at a first block without SIMPLE and said nothing, so the page answered "no 2-D image
        # in this file" for a .fits.gz (which the command line reads), a PNG or a text file; .gz was not in the picker
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        gz = self.p('c.fits.gz'); open(gz, 'wb').write(gzip.compress(open(p, 'rb').read()))
        png = self.p('c.png'); open(png, 'wb').write(b'\x89PNG\r\n\x1a\n' + bytes(range(256)) * 12)
        txt = self.p('notes.txt'); open(txt, 'w', encoding='utf-8').write('this is not a FITS file\n' * 200)
        tiny = self.p('tiny.txt'); open(tiny, 'w', encoding='utf-8').write('shorter than one FITS block\n')
        for name, f, word in (('a gzipped FITS file', gz, 'gunzip'), ('a PNG', png, 'not a FITS file'),
                              ('a text file', txt, 'not a FITS file'), ('a file shorter than one FITS block', tiny, 'not a FITS file')):
            with self.subTest(name):
                o = js(PARSE + "out = h.map(u => u.unreadable || null);", dict(p=f))
                self.assertTrue(any(u and word in u for u in o), o)
        with self.subTest('the file picker offers .gz'):
            accept = re.search(r'id="file"[^>]*accept="([^"]*)"', open(HTML, encoding='utf-8').read()).group(1)
            self.assertIn('.gz', [a.strip() for a in accept.split(',')])
        with self.subTest('control: the FITS file itself'):
            self.assertEqual(js(PARSE + "out = h.map(u => !!u.readable);", dict(p=p)), [True])

    def test_t4_11_timesys_names_the_command_line_only_where_it_converts(self):
        # 847d438: "the command line converts TT and TAI" for every TIMESYS, TDB included; the command line converts TT, TDT,
        # TAI and IAT and refuses the rest (the sentence true as written, the pointer wrong)
        ts = ['TDB', 'LOCAL', 'GPS', 'TT', 'TDT', 'TAI', 'IAT']
        o = js("out = D.ts.map(t => Z.midExposure({'DATE-OBS': '2025-12-12T21:20:32.000', EXPTIME: 60, TIMESYS: t}));", dict(ts=ts))
        for t, q in zip(ts, o):
            with self.subTest(t if t in ('TDB', 'LOCAL', 'GPS') else 'control: ' + t):
                self.assertFalse(q.get('time'), q)
                self.assertEqual('command line' in q.get('error', ''), t in ('TT', 'TDT', 'TAI', 'IAT'), q)

    def test_t4_12_the_page_says_what_the_command_line_is(self):
        # 847d438 sent the user to "the command line" in nine messages and never said what it is (python -m domino_calibrator.cli,
        # the calibrator package's README)
        b64 = self.p('b64.fits'); fits.PrimaryHDU(np.ones((21, 21), np.int64)).writeto(b64)
        fz = self.p('c.fits.fz'); fits.HDUList([fits.PrimaryHDU(), fits.CompImageHDU(np.round(pig(41, 20.2, 19.9, 1.5, amp=3e4) + 150.0).astype(np.int16))]).writeto(fz)
        sip = dict(TAN, CTYPE1='RA---TAN-SIP', CTYPE2='DEC--TAN-SIP', A_ORDER=2, B_ORDER=2, A_2_0=1e-6, B_0_2=1e-6)
        scamp5 = dict(PV1_0=0.0, PV1_1=1.0, PV1_2=0.0, PV1_5=1e-4, PV2_0=0.0, PV2_1=1.0, PV2_2=0.0, PV2_5=1e-4)
        msgs = list(zip(['Dec first', 'TPV', 'SIP without -SIP', 'AXISCORR', "SCAMP's terms on TAN", 'lookup tables without the file'],
                        wcs_verdicts(TAN, [dict(CTYPE1='DEC--TAN', CTYPE2='RA---TAN'), dict(CTYPE1='RA---TPV', CTYPE2='DEC--TPV'),
                                           dict(A_ORDER=2, B_ORDER=2, A_2_0=1e-5), dict(AXISCORR=1), scamp5, dict(CPDIS1='Lookup', CPDIS2='Lookup')])))
        msgs.append(("SCAMP's terms beside SIP", wcs_verdicts(sip, [scamp5])[0]))
        msgs.append(('TIMESYS TT', js("out = Z.midExposure({'DATE-OBS': '2025-12-12T21:20:32.000', EXPTIME: 60, TIMESYS: 'TT'}).error;")))
        msgs.append(('BITPIX 64', js(PARSE + "out = h[0].unreadable;", dict(p=b64))))
        msgs.append(('fpack', [u for u in js(PARSE + "out = h.map(u => u.unreadable || null);", dict(p=fz)) if u][0]))
        for name, m in msgs:
            with self.subTest(name):
                self.assertIn('command line', m or '')
                self.assertIn('python -m domino_calibrator.cli', m)
        with self.subTest('the page says it once, under "What it does"'):
            html = open(HTML, encoding='utf-8').read()
            self.assertIn('python -m domino_calibrator.cli', html[html.index('<h2>What it does</h2>'):])

    def test_t4_16_tnx_and_zpx_are_not_sent_to_the_command_line(self):
        # 847d438: "the command line reads the other FITS projections" for IRAF's TNX and ZPX, which it refuses in IRAF's
        # own shape ("Internal error in wcslib header parser"; test_hardening_3b); re-solving is the remedy that works
        for code in ('TNX', 'ZPX'):
            with self.subTest(code):
                v = wcs_verdicts(TAN, [wat(code, HALF)])[0]
                self.assertTrue(isinstance(v, str) and v != 'MEASURED', v)
                self.assertIn(code, v); self.assertIn('re-solve', v)
                self.assertNotIn('the command line reads the other', v)
        with self.subTest('control: ZPN, a FITS projection, is sent there'):
            self.assertIn('command line', wcs_verdicts(TAN, [dict(CTYPE1='RA---ZPN', CTYPE2='DEC--ZPN')])[0])

    def test_t1_7_a_string_opens_where_its_quote_is(self):
        # 847d438 took a string only when its quote opened in columns 11-15, so a free-format quote at column 21 kept its
        # quotes ("the WCS is not equatorial", "not a FITS date-time"); and a quote written twice ('O''Brien') ended it
        img, _ = comet()
        p = with_cards(write(self.p('c.fits'), img, OBJECT='X'),
                       {'CTYPE1': "CTYPE1  =           'RA---TAN'", 'CTYPE2': "CTYPE2  =           'DEC--TAN'",
                        'DATE-OBS': "DATE-OBS=           '2025-12-12T21:20:32.000'", 'OBJECT': "OBJECT  = 'O''Brien'"})
        hh = fits.getheader(p)                                        # astropy's reading: the reference
        self.assertEqual((hh['CTYPE1'], hh['OBJECT']), ('RA---TAN', "O'Brien"))
        o = js(PARSE + "const H = h[0].header, w = Z.makeWCS(H);"
               "out = {ct: H.CTYPE1, obj: H.OBJECT, w: w ? (w.unsupported || 'MEASURED') : null, t: Z.midExposure(H)};", dict(p=p))
        with self.subTest('CTYPE1, its quote at column 21'):
            self.assertEqual(o['ct'], 'RA---TAN'); self.assertEqual(o['w'], 'MEASURED')
        with self.subTest('DATE-OBS, its quote at column 21'):
            self.assertEqual(o['t'].get('time'), '2025-12-12T21:21:02.00Z', o['t'])
        with self.subTest('a quote written twice is one quote'):
            self.assertEqual(o['obj'], "O'Brien")
        with self.subTest('a string never closed is left out and named, as astropy cannot read it'):
            # added with the fixes (its red measured on 847d438's copy): the page read "'abc" as 'ab' or 'abc', unnamed; astropy
            # raises "Unparsable card", and the command line leaves such a card out and names it (round 3, Part A, T1.1)
            q = with_cards(write(self.p('open.fits'), img, OBJECT='X'), {'OBJECT': "OBJECT  = 'abc"})
            o = js(PARSE + "out = {obj: h[0].header.OBJECT === undefined ? null : h[0].header.OBJECT, dropped: h[0].dropped};", dict(p=q))
            self.assertIsNone(o['obj'], o); self.assertIn('OBJECT', o['dropped'])

    def test_t1_12_sip_needs_both_orders(self):
        # 847d438 applied SIP with A_ORDER and no B_ORDER (or the reverse); astropy refuses the header ("A_ORDER provided
        # without corresponding B_ORDER keyword for SIP distortion"), so the faces answered differently, silently
        sip = dict(TAN, CTYPE1='RA---TAN-SIP', CTYPE2='DEC--TAN-SIP')
        cases = [('A_ORDER alone', dict(A_ORDER=2, A_2_0=1e-4)), ('B_ORDER alone', dict(B_ORDER=2, B_0_2=1e-4))]
        for (name, c), v in zip(cases, wcs_verdicts(sip, [c for _, c in cases])):
            with self.subTest(name):
                self.assertTrue(isinstance(v, str) and v != 'MEASURED' and ('A_ORDER' in v or 'B_ORDER' in v), v)
        with self.subTest('control: both orders, as astropy applies them'):
            c = dict(sip, A_ORDER=2, B_ORDER=2, A_2_0=1e-4, B_0_2=1e-4)
            pts = [[0.0, 0.0], [70.0, 10.0], [35.0, 35.0], [5.0, 66.0]]
            o = js("const w = Z.makeWCS(D.h); out = w && !w.unsupported ? D.pts.map(p => w.pixToSky(p[0], p[1])) : null;", dict(h=c, pts=pts))
            want = WCS(fits.Header(c)).all_pix2world(pts, 0)
            g = np.array(o, float)
            self.assertLess(np.max(np.hypot((g[:, 0] - want[:, 0]) * np.cos(np.radians(want[:, 1])), g[:, 1] - want[:, 1]) * 3600), 1e-6)

    def test_t1_15_a_time_outside_the_years_0000_9999_is_refused_on_the_page(self):
        # 847d438 put '+010072-08-06T00:00:30Z' (MJD-OBS 3e6) and '-000058-05-06T00:00:30Z' (-700000) in the time box; only
        # the record refused them
        o = js("out = D.cases.map(h => Z.midExposure(h));", dict(cases=[{'MJD-OBS': 3e6, 'EXPTIME': 60}, {'MJD-OBS': -700000, 'EXPTIME': 60},
                                                                        {'MJD-OBS': 61021.89, 'EXPTIME': 60}]))
        for name, q in zip(('MJD-OBS 3e6', 'MJD-OBS -700000'), o[:2]):
            with self.subTest(name):
                self.assertFalse(q.get('time'), q); self.assertIn('year', q.get('error', ''))
        with self.subTest('control: MJD-OBS 61021.89'):
            self.assertTrue(o[2].get('time', '').startswith('2025-12-12T'), o[2])

    def test_t1_18_the_automatic_start_is_one_rule_on_both_faces(self):
        # 847d438: the page summed 5 x 5 boxes inside the image (non-finite pixels as 0; the first maximum in row order), the
        # command line averaged them over every pixel with reflected edges and read an infinity as 1.8e308
        rng = np.random.default_rng(11)
        base = rng.normal(100.0, 3.0, (40, 50))
        edge = base.copy(); edge[18:23, 0:2] += 5e3
        inf = base.copy(); inf[20, 25] += 3e3; inf[10, 40] = np.inf; inf[30, 10] = np.nan
        flat = base.copy(); flat[10:20, 12:24] = 4000.0
        for name, img in (('the brightest light on the edge', edge), ('an infinite pixel away from the comet', inf),
                          ('control: a saturated plateau, equal boxes, the first in row order', flat), ('control: the comet', comet()[0])):
            with self.subTest(name):
                page = js(START_JS, dict(img=pixels(img), nx=img.shape[1], ny=img.shape[0]))
                self.assertEqual(tuple(float(v) for v in page), cli._start(img))


@unittest.skipIf(NODE is None or PW is None, 'no node or no playwright')
class TestPageInBrowser3b(unittest.TestCase):
    """The page as a user meets it (page/browser_cases.js): Part B's findings on the page, and T1.20's cases."""
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore')
        cls.d = tempfile.mkdtemp()
        P = lambda name: os.path.join(cls.d, name)
        from domino_calibrator import synth
        img, _ = synth.render(71, 35.25, 34.85, flux_n=3e4, k=400.0, a=0.3, model='dipole', psf=('gauss', 2.5), sub=10)
        img = synth.add_noise(img, 150.0, 5.0, np.random.default_rng(5)).astype(np.float32)
        T = {'DATE-OBS': '2025-12-27T16:04:29.000', 'EXPTIME': 120.0}
        good = fits_bytes(P('good.fits'), img, **dict(TAN, **T))
        gz = P('good.fits.gz'); open(gz, 'wb').write(gzip.compress(open(good, 'rb').read()))
        nowcs = fits_bytes(P('nowcs.fits'), img, **T)
        ph = fits.PrimaryHDU(); ph.header.update(T)
        two = P('two.fits'); fits.HDUList([ph, fits.ImageHDU(img, header=fits.Header(TAN)), fits.ImageHDU(img[::-1].copy(), header=fits.Header(TAN))]).writeto(two)
        first = dict(file=good, x=35, y=35, set=dict(REC3), run=True)
        cases = [dict(name='empty_start', steps=[first, dict(set={'sx': ''}, run=True)]),
                 dict(name='empty_bg', steps=[dict(first, set=dict(REC3, bgm='value', bgv='150')), dict(set={'bgv': ''}, run=True)]),
                 dict(name='gz', steps=[dict(file=gz)]),
                 dict(name='nowcs', steps=[dict(file=nowcs, x=35, y=35, set=dict(REC3), run=True)]),
                 dict(name='field', steps=[first, dict(set={'tobs': '2025-12-27T16:10:00.00Z', 'stn': 'J95'})]),
                 dict(name='radii05', steps=[dict(first, set=dict(REC3, est='M', r0='2.05', r1='5.95', rs='0.05'))]),
                 dict(name='radii', steps=[first, dict(set={'r1': '5.0'})]),
                 dict(name='bgmode', steps=[first, dict(set={'bgm': 'value'})]),
                 dict(name='bgvalue', steps=[dict(first, set=dict(REC3, bgm='value', bgv='150')), dict(set={'bgv': '140'})]),
                 dict(name='hdu', steps=[dict(file=two, x=35, y=35, set=dict(REC3), run=True), dict(set={'hdu': '2'})])]
        cp = P('cases.json'); json.dump(cases, open(cp, 'w', encoding='utf-8'))
        r = subprocess.run([NODE, os.path.join(PAGE, 'browser_cases.js'), cp], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900,
                           env=dict(os.environ, PLAYWRIGHT_MODULE=PW))
        cls.err = r.stderr[-800:]
        try:
            cls.res = {c['name']: c for c in json.loads(r.stdout)}
        except Exception:
            cls.res = None

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def steps(self, name, n):
        self.assertIsNotNone(self.res, 'browser_cases.js gave no result: ' + self.err)
        c = self.res[name]
        self.assertEqual(len(c.get('steps', [])), n, {k: v for k, v in c.items() if k != 'steps'})
        return c['steps']

    def test_t4_3_an_empty_box_is_refused_by_name(self):
        # 847d438: Number('') is 0, so an emptied start box measured from x = 0 ("41 of 41 radii did not converge") and an
        # emptied known background measured with 0
        for name, word in (('empty_start', 'start'), ('empty_bg', 'background')):
            with self.subTest(name):
                s0, s1 = self.steps(name, 2)
                self.assertIn('# version=2022', s0['ades'])                  # first a record, as a user makes one
                self.assertIn(word, s1['status']); self.assertIn('empty', s1['status'])
                self.assertTrue(s1['copyDisabled']); self.assertNotIn('# version', s1['ades'])

    def test_t4_8_a_gzipped_file_is_named_on_the_page(self):
        s0, = self.steps('gz', 1)                                         # 847d438: "Could not read: no 2-D image in this file"
        self.assertIn('Could not read', s0['info']); self.assertIn('gunzip', s0['info'])

    def test_t4_9_no_wcs_names_plate_solving_on_the_page(self):
        s0, = self.steps('nowcs', 1)                                      # 847d438: "no WCS (pixels only)"; "no WCS in the header"
        with self.subTest('the info line'):
            self.assertIn('solve', s0['info'].lower())
        with self.subTest("the record's refusal"):
            self.assertNotIn('# version', s0['ades']); self.assertIn('solve', s0['ades'].lower())

    def test_t4_11_a_typed_time_says_it_was_typed(self):
        # 847d438: after the user typed a time, the note still read "Time: obsTime from DATE-OBS (the start) + EXPTIME/2"
        s0, s1 = self.steps('field', 2)
        self.assertIn('DATE-OBS', s0['hdrnote'])                          # control: the header's time, said so
        self.assertIn('typed', s1['hdrnote']); self.assertIn('2025-12-27T16:05:29', s1['hdrnote'])   # and what the header gave

    def test_t4_18_the_page_remarks_name_the_radii_as_they_are(self):
        s0, = self.steps('radii05', 1)                                    # 847d438: "r 2.0-6.0 px" for 2.05-5.95
        self.assertIn('# version=2022', s0['ades'], s0['status'])
        self.assertIn('r 2.05-5.95 px', record_row(s0['ades'])['remarks'])

    def test_t1_20_a_changed_field_rewrites_the_live_record(self):
        # T1.20: round 2's field test asserted nothing once Copy was disabled, so a page that disabled Copy on a record
        # field (and left the old record) passed it. A record field rewrites the record and Copy stays live
        s0, s1 = self.steps('field', 2)
        self.assertFalse(s0['copyDisabled']); self.assertIn('2025-12-27T16:05:29.00Z', s0['ades'])
        self.assertFalse(s1['copyDisabled'], s1['ades'])
        self.assertIn('2025-12-27T16:10:00.00Z', s1['ades']); self.assertIn('! mpcCode J95', s1['ades'])
        self.assertNotIn('16:05:29', s1['ades'])

    def test_t1_20_a_new_radii_background_or_hdu_clears_the_answer(self):
        # T1.20: no browser case changed the radii, the background or the HDU, so a page that kept the old answer after
        # them passed every test
        for name in ('radii', 'bgmode', 'bgvalue', 'hdu'):
            with self.subTest(name):
                s0, s1 = self.steps(name, 2)
                self.assertIn('# version=2022', s0['ades']); self.assertFalse(s0['copyDisabled'])
                self.assertTrue(s1['copyDisabled'], s1['ades']); self.assertNotIn('# version', s1['ades'])
                self.assertEqual(s1['zero'].strip(), '')

    @unittest.skipIf(not (ADES_PYLIB and ADES_MASTER), 'the MPC judge needs ADES_PYLIB and ADES_MASTER')
    def test_judge_accepts_part_bs_page_record(self):
        # control: the record with radii off the published grid (847d438 writes it, with "r 2.0-6.0 px")
        s0, = self.steps('radii05', 1)
        self.assertIn('# version=2022', s0['ades'])
        d = tempfile.mkdtemp()
        try:
            ok, why = mpc_judge(s0['ades'], d)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertTrue(ok, why)


if __name__ == '__main__':
    unittest.main()
