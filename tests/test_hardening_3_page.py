"""Round 3 of the hardening, Part A, page side (the third hardening round's record of 28 Sept 2026, not in this repository): the page's engine
(page/zeroap.js, through Node) and the page itself in a headless browser (page/browser_cases.js), for the fifth
invitation's items 1-5 (the fifth invitation, of 28 Sept 2026, not in this repository), numbered as Annie's check tables in
the refuters' second record of 28 Sept 2026, not in this repository. Item 4 is his word for this session: the page reads HST's lookup tables
(CPDIS, D2IMDIS, from the file's own WCSDVARR and D2IMARR extensions, the record-valued DPj and D2IMj cards included)
and applies them as astropy 6.1.7 does (read at its source: astropy/wcs/src/distortion.c and pipeline.c at v6.1.7: the
D2IM tables at the pixel, then SIP and CPDIS at the D2IM-corrected pixel, 1-based, bilinear, clamped at the table's
edges), and it decodes only the image the user chooses. Written to fail on the calibrator as the fourth room's pull
request merged it (e7051b4) and to pass once each fix is in; every case is a subTest.
"""
import os, re, json, shutil, tempfile, unittest, warnings, subprocess
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from domino_calibrator import synth
from domino_calibrator import cli
from tests.test_hardening import pig, comet, wcs_cards, REC, mpc_judge, ADES_PYLIB, ADES_MASTER
from tests.test_hardening_page import js, fits_bytes, PAGE, NODE, PW, REC_JS, REC_PAGE
from tests.test_hardening_2_page import PARSE, REC_T, TAN, wcs_verdicts
from tests.test_hardening_2 import lookup_file, record_row
from tests.test_hardening_3 import with_raw_card, SCAMP1, FLC
from domino_calibrator.hst import DATA

FRAMES = ('ifle03geq', 'ifle04pdq', 'ifle05qlq', 'ifle06tjq', 'ifle22f7q')   # the first frame of each visit, as round 2's run
REC3 = dict(REC_PAGE, measurers='; '.join(REC['measurers']))              # names are separated by semicolons (round 2)
LOOKUP_JS = PARSE + ("const w = Z.makeWCS(h[D.i].header, h[0].header, h);"
                     "out = !w ? null : w.unsupported ? {u: w.unsupported} : {pts: D.pts.map(q => w.pixToSky(q[0], q[1]))};")
BAR = 1e-5                                                                # arcsec: the page against astropy, item 4's bar


def frame(root):
    return os.path.join(DATA, root + '_flc.fits')


def sky_arcsec(got, want):
    g, w = np.asarray(got, float), np.asarray(want, float)
    return np.hypot(((g[:, 0] - w[:, 0] + 180.0) % 360.0 - 180.0) * np.cos(np.radians(w[:, 1])), g[:, 1] - w[:, 1]) * 3600


def rich_lookup_file(path, transpose=False):
    """A cutout whose WCS stacks everything astropy applies from a file: SIP, D2IM tables and CPDIS tables, the tables
    random, not square, each with its own CRPIX, CRVAL and CDELT. transpose: DP1's AXIS cards swapped, so that astropy reads
    table 1 transposed (its CRPIX, CRVAL, CDELT as written)."""
    from astropy.wcs import DistortionLookupTable
    rng = np.random.default_rng(3)
    img, _ = comet()
    h = wcs_cards(fits.Header(), n=img.shape[1]); h['CTYPE1'] = 'RA---TAN-SIP'; h['CTYPE2'] = 'DEC--TAN-SIP'
    for k, v in dict(A_ORDER=2, B_ORDER=2, A_2_0=2e-5, A_1_1=-1e-5, A_0_2=4e-6, B_0_2=1.5e-5, B_1_1=5e-6, B_2_0=-3e-6).items():
        h[k] = v
    w = WCS(h)
    t = lambda shape, a: rng.uniform(-a, a, shape).astype(np.float32)
    w.det2im1 = DistortionLookupTable(t((8, 9), 0.05), (1.0, 1.0), (0.0, 0.0), (10.0, 10.0))
    w.det2im2 = DistortionLookupTable(t((8, 9), 0.05), (2.0, 1.5), (5.0, 3.0), (9.0, 11.0))
    w.cpdis1 = DistortionLookupTable(t((7, 10), 0.3), (1.0, 1.0), (1.0, 1.0), (8.0, 12.0))
    w.cpdis2 = DistortionLookupTable(t((7, 10), 0.3), (0.5, 2.0), (0.0, 4.0), (8.0, 12.0))
    hl = w.to_fits(relax=True)
    hl[0].data = img.astype(np.float32)
    hl[0].header['DATE-OBS'] = '2025-12-12T21:20:32.000'; hl[0].header['EXPTIME'] = 60.0
    if transpose:
        hl[0].header['DP1.AXIS.1'] = 2; hl[0].header['DP1.AXIS.2'] = 1
    hl.writeto(path, overwrite=True)
    return path


def astropy_sky(path, ext, pts):
    with fits.open(path) as f, warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return WCS(f[ext].header, fobj=f).all_pix2world(pts, 0)


def mef(path, pcards, icards, img=None):
    """A two-HDU file: an empty primary with pcards, the comet in an image extension with TAN (round 2's) and icards;
    a value None writes a card with no value."""
    img = comet()[0] if img is None else img
    ph = fits.PrimaryHDU()
    for k, v in pcards.items():
        ph.header[k] = v
    ih = fits.Header()
    for k, v in dict(TAN, **icards).items():
        ih[k] = v
    fits.HDUList([ph, fits.ImageHDU(img.astype(np.float32), header=ih)]).writeto(path, overwrite=True)
    return path


@unittest.skipIf(NODE is None, 'no node')
class TestPageEngine3(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore')
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def p(self, name):
        return os.path.join(self.d, name)

    # ------------------------------------------------ item 1: PV
    def test_t1_17_pv_the_page_says_what_the_command_line_does(self):
        scamp5 = dict(SCAMP1, PV1_5=1e-4, PV2_5=1e-4)
        sip = dict(TAN, CTYPE1='RA---TAN-SIP', CTYPE2='DEC--TAN-SIP', A_ORDER=2, B_ORDER=2, A_2_0=1e-6, B_0_2=1e-6)
        with self.subTest("TAN-SIP with SCAMP's terms: the command line keeps the SIP and drops the PV terms"):
            v = wcs_verdicts(sip, [scamp5])[0] or ''
            self.assertNotIn('as TPV', v); self.assertIn('drops', v)     # e7051b4: "the command line does (as TPV)"
        with self.subTest('a first-order SCAMP solution on TAN: the CTYPE remedy'):
            v = wcs_verdicts(TAN, [SCAMP1])[0] or ''
            self.assertIn('RA---TPV', v); self.assertNotIn('command line', v)   # e7051b4: "re-solve the image with SIP or TPV"
        with self.subTest("control: plain TAN with SCAMP's full terms is TPV to the command line"):
            v = wcs_verdicts(TAN, [scamp5])[0] or ''
            self.assertIn('command line', v); self.assertIn('TPV', v)

    # ------------------------------------------------ item 2 and 3: the cards (T1.1's page face, T1.5, T1.7's parse)
    def test_t1_5_a_card_without_its_value_indicator_is_left_out_and_named(self):
        # e7051b4: `EXPTIME =60.0` read from column 11 as 0.0, so the start was written as the middle, silently; astropy reads
        # the card as the text '=60.0' (an invalid card), which the command line leaves out (test_hardening_3, T1.1)
        for name, card, key in (('a value from column 10', b'EXPTIME =60.0', 'EXPTIME'), ('no "= " at all', b'OBJECT    3I', 'OBJECT')):
            with self.subTest(name):
                p = with_raw_card(self.p('card.fits'), card)
                o = js(PARSE + "out = {t: Z.midExposure(Object.assign({}, h[0].header)), dropped: h[0].dropped || null};", dict(p=p))
                self.assertIn(key, o['dropped'] or [], o)
                if key == 'EXPTIME':
                    self.assertFalse(o['t'].get('time'), o['t']); self.assertIn('exposure', o['t'].get('error', ''))

    # ------------------------------------------------ item 3: the other silent wrong answers (the page's share)
    def test_t1_4_an_end_before_the_start_is_refused_on_the_page(self):
        cases = [{'DATE-OBS': '2025-12-12T23:59:30', 'DATE-END': '2025-12-12T00:00:30'},
                 {'DATE-OBS': '2025-12-12T21:20:32', 'DATE-END': '2025-12-11T21:22:32'},
                 {'MJD-OBS': 61021.89, 'MJD-END': 61021.80},
                 {'DATE-BEG': '2025-12-12T21:20:32', 'DATE-END': '2025-12-12T21:10:32'},
                 {'DATE-OBS': '2025-12-12T21:20:32.000', 'DATE-END': '2025-12-12T21:22:32.000'}]
        o = js("out = D.cases.map(h => Z.midExposure(h));", dict(cases=cases))
        for c, q in zip(cases[:4], o[:4]):
            with self.subTest(json.dumps(c)):                        # e7051b4: a middle before the start (12 h early), silently
                self.assertFalse(q.get('time'), q); self.assertIn('END', q.get('error', ''))
        with self.subTest('control: an end after the start'):
            self.assertEqual(o[4].get('time'), '2025-12-12T21:21:32.00Z')

    def test_t4_1_t1_22_a_partial_wcs_is_refused_on_the_page(self):
        # the rule that says what a scale is decides T1.22 too (in item 6's list): FITS defaults CDELT to 1 beside a PC matrix
        drop = lambda *ks: {k: v for k, v in TAN.items() if k not in ks}
        cases = [('no CRVAL', drop('CRVAL1', 'CRVAL2'), 'CRVAL'), ('no CRVAL2', drop('CRVAL2'), 'CRVAL2'),
                 ('no CRPIX', drop('CRPIX1', 'CRPIX2'), 'CRPIX'), ('no scale', drop('CD1_1', 'CD1_2', 'CD2_1', 'CD2_2'), 'scale')]
        got = wcs_verdicts({}, [c for _, c, _ in cases])
        for (name, c, word), v in zip(cases, got):
            with self.subTest(name):                                 # e7051b4: MEASURED, "RA NaN" (and a record refused for it)
                self.assertTrue(isinstance(v, str) and v != 'MEASURED' and word in v, v)
        with self.subTest('T1.22: a PC matrix without CDELT'):
            c = dict(drop('CD1_1', 'CD1_2', 'CD2_1', 'CD2_2'), PC1_1=-2.1e-4, PC1_2=0.0, PC2_1=0.0, PC2_2=2.1e-4)
            pts = [[0.0, 0.0], [70.0, 10.0], [35.0, 35.0], [5.0, 66.0]]
            o = js("const w = Z.makeWCS(D.h); out = w && !w.unsupported ? D.pts.map(p => w.pixToSky(p[0], p[1])) : null;", dict(h=c, pts=pts))
            self.assertIsNotNone(o)
            g = np.array([[np.nan if v is None else v for v in q] for q in o], float)
            self.assertTrue(np.isfinite(g).all(), o)                 # e7051b4: NaN ("RA NaN")
            self.assertLess(np.max(sky_arcsec(g, WCS(fits.Header(c)).all_pix2world(pts, 0))), 1e-6)

    def test_t1_6_an_empty_timesys_is_utc_on_the_page(self):
        o = js("out = Z.midExposure({'DATE-OBS': '2025-12-12T21:20:32.000', EXPTIME: 60, TIMESYS: ''});")
        self.assertEqual(o.get('time'), '2025-12-12T21:21:02.00Z', o)  # e7051b4: "TIMESYS : the page reads UTC only"; the Python: UTC

    def test_t4_15_the_page_reads_cunit(self):
        # e7051b4: CUNIT ignored, a header in arcsec 509,702" off (T4.15); astropy converts (wcslib's units)
        pts = [[0.0, 0.0], [70.0, 10.0], [35.0, 35.0], [5.0, 66.0]]
        for unit, f in (('deg', 1.0), ('arcmin', 60.0), ('arcsec', 3600.0), ('mas', 3.6e6), ('rad', np.pi / 180)):
            with self.subTest(unit):
                c = dict(TAN, CUNIT1=unit, CUNIT2=unit, CRVAL1=TAN['CRVAL1'] * f, CRVAL2=TAN['CRVAL2'] * f,
                         CD1_1=TAN['CD1_1'] * f, CD1_2=0.0, CD2_1=0.0, CD2_2=TAN['CD2_2'] * f)
                o = js("const w = Z.makeWCS(D.h); out = w && !w.unsupported ? D.pts.map(p => w.pixToSky(p[0], p[1])) : (w && w.unsupported);", dict(h=c, pts=pts))
                self.assertIsInstance(o, list, o)
                self.assertLess(np.max(sky_arcsec(o, WCS(fits.Header(c)).all_pix2world(pts, 0))), 1e-6)
        with self.subTest('a unit the page does not know is refused'):
            v = wcs_verdicts(TAN, [dict(CUNIT1='furlong', CUNIT2='furlong')])[0]
            self.assertTrue(isinstance(v, str) and v != 'MEASURED' and 'CUNIT' in v, v)

    def test_t4_4_a_comma_in_a_name_is_noted(self):
        o = js("out = [Z.adesPSV(" + REC_T + ", {measurers: 'A. N. Observer, B. Other'})), Z.adesPSV(" + REC_T + ", {measurers: 'A. N. Observer; B. Other'}))];", REC_JS)
        self.assertIn('! name A. N. Observer, B. Other', o[0].get('psv', ''))   # one name, as round 2's rule 7 says
        self.assertTrue(any('comma' in n for n in o[0].get('notes') or []), o[0])   # e7051b4: no word of it
        with self.subTest('control: names separated by a semicolon'):
            self.assertFalse(any('comma' in n for n in o[1].get('notes') or []), o[1])

    # ------------------------------------------------ item 4: HST's lookup tables (his word: this session)
    def test_lookup_the_page_matches_astropy_on_synthetic_files(self):
        pts = [[x, y] for x in (-5.0, 0.0, 3.3, 17.8, 35.0, 52.1, 70.0, 78.6) for y in (-4.0, 0.0, 9.9, 35.0, 49.4, 70.0, 81.0)]
        for name, p in (("round 2's file: a CPDIS table, 0.5 px everywhere", lookup_file(self.p('lookup.fits'))),
                        ('SIP, D2IM and CPDIS tables, random, not square', rich_lookup_file(self.p('rich.fits'))),
                        ("the same, DP1's table transposed by its AXIS cards", rich_lookup_file(self.p('richT.fits'), transpose=True))):
            with self.subTest(name):
                o = js(LOOKUP_JS, dict(p=p, i=0, pts=pts))           # e7051b4: refused ("lookup-table distortion ...")
                self.assertIn('pts', o or {}, o)
                d = sky_arcsec(o['pts'], astropy_sky(p, 0, pts))
                self.assertLess(d.max(), BAR, 'max %.3g" at %s' % (d.max(), pts[int(d.argmax())]))

    @unittest.skipIf(not os.path.exists(frame(FRAMES[0])), 'the HST frames: tools/fetch_frames.py 22 03 04 05 06')
    def test_lookup_the_page_matches_astropy_on_hubbles_frames(self):
        # SCI,1: 2047 x 2050 px; D2IMARR 1-2 and WCSDVARR 1-2, each 64 x 32, CDELT 64 (measured at wake-up). The grid runs
        # through the tables' clamped edges (x < 64, y < 65 in 1-based pixels) and the interior, off the integers
        pts = [[x, y] for x in (0.0, 30.5, 63.0, 64.25, 700.7, 1023.0, 1500.2, 2046.0) for y in (0.0, 40.25, 64.0, 65.5, 800.3, 1400.0, 2049.0)]
        for root in FRAMES:
            with self.subTest(root):
                o = js(LOOKUP_JS, dict(p=frame(root), i=1, pts=pts))  # e7051b4: refused, naming the command line
                self.assertIn('pts', o or {}, o)
                d = sky_arcsec(o['pts'], astropy_sky(frame(root), 1, pts))
                self.assertLess(d.max(), BAR, 'max %.3g" at %s' % (d.max(), pts[int(d.argmax())]))

    def test_lookup_a_table_not_in_hand_or_not_a_table_is_refused(self):
        # controls, green by design: what the page cannot apply as astropy does stays refused after item 4
        p = lookup_file(self.p('lookup.fits'))
        q = self.p('notables.fits')
        with fits.open(p) as f:
            fits.HDUList([fits.PrimaryHDU(f[0].data, header=f[0].header)]).writeto(q)
        with self.subTest("control: CPDIS Lookup, the table's extension missing"):
            o = js(LOOKUP_JS, dict(p=q, i=0, pts=[[1.0, 1.0]]))
            self.assertIn('u', o or {}, o)
        for c in (dict(CPDIS1='Polynomial', CPDIS2='Polynomial'), dict(D2IMDIS1='Polynomial', D2IMDIS2='Polynomial')):
            with self.subTest('control: ' + json.dumps(c)):
                v = wcs_verdicts(TAN, [c])[0]
                self.assertTrue(isinstance(v, str) and v != 'MEASURED', v)
        with self.subTest('control: the tables without their file: refused, naming the command line (round 2, test_4_6)'):
            o = js(PARSE + "const w = Z.makeWCS(h[0].header); out = w ? (w.unsupported || 'MEASURED') : null;", dict(p=p))
            self.assertTrue(isinstance(o, str) and 'command line' in o, o)

    def test_1_19_the_page_decodes_only_the_image_chosen(self):
        a = (np.arange(200 * 150, dtype=np.float32).reshape(150, 200) / 7)
        b = (np.arange(100 * 100) % 3000).astype(np.int16).reshape(100, 100)
        c = np.linspace(0.0, 1.0, 2000).reshape(40, 50)
        p = self.p('mef3.fits'); fits.HDUList([fits.PrimaryHDU(), fits.ImageHDU(a), fits.ImageHDU(b), fits.ImageHDU(c)]).writeto(p)
        o = js(PARSE + "const before = Z.decodedPixels; const d = Array.from(h[2].data);"
               "out = {before: before === undefined ? null : before, after: Z.decodedPixels === undefined ? null : Z.decodedPixels, d: d,"
               " readable: h.map(u => u.nx === undefined ? null : !!u.readable)};", dict(p=p))
        self.assertEqual(o['before'], 0, o['before'])               # e7051b4: the parse decoded every image, and kept no count
        self.assertEqual(o['after'], 100 * 100)
        self.assertEqual(o['readable'], [None, True, True, True])    # known without decoding, for the page's HDU list
        self.assertTrue(np.array_equal(np.array(o['d'], float), b.astype(float).ravel()))


# init scripts for browser_cases.js (run in the page before its own)
SLOW_FIRST_READ = ("(() => { const orig = Blob.prototype.arrayBuffer; let n = 0; Blob.prototype.arrayBuffer = function () {"
                   " const p = orig.call(this); return n++ === 0 ? p.then((b) => new Promise((r) => setTimeout(() => r(b), 1500))) : p; }; })();")
CLIP = {'ok': "Object.defineProperty(navigator, 'clipboard', { value: { writeText: (t) => { window.__copied = t; return Promise.resolve(); } }, configurable: true });",
        'none': "Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true });",
        'refused': "Object.defineProperty(navigator, 'clipboard', { value: { writeText: () => Promise.reject(new Error('Write permission denied')) }, configurable: true });"}
# The tenth room (test_page_copy.py): the page copies by selection first (the copy command, inside the click) and asks the
# async clipboard second, so each stub sets both ways: 'ok' records either way's text, 'none' and 'refused' refuse both.
CLIP['ok'] += (" document.execCommand = function (c) { if (c !== 'copy') return false; const a = document.activeElement;"
               " window.__copied = a && typeof a.value === 'string' ? a.value.substring(a.selectionStart, a.selectionEnd) : String(window.getSelection()); return true; };")
CLIP['none'] += " document.execCommand = function () { return false; };"
CLIP['refused'] += " document.execCommand = function () { return false; };"


@unittest.skipIf(NODE is None or PW is None, 'no node or no playwright')
class TestPageInBrowser3(unittest.TestCase):
    """The page as a user meets it (page/browser_cases.js, with round 3's init scripts and steps)."""
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore')
        cls.d = tempfile.mkdtemp()
        P = lambda name: os.path.join(cls.d, name)
        img, _ = synth.render(71, 35.25, 34.85, flux_n=3e4, k=400.0, a=0.3, model='dipole', psf=('gauss', 2.5), sub=10)
        img = synth.add_noise(img, 150.0, 5.0, np.random.default_rng(5)).astype(np.float32)
        T = {'DATE-OBS': '2025-12-27T16:04:29.000', 'EXPTIME': 120.0}
        good = fits_bytes(P('good.fits'), img, **dict(TAN, **T))
        small = fits_bytes(P('small.fits'), (pig(41, 20.3, 20.2, 1.6, amp=3e4) + 150.0).astype(np.float32), **dict(TAN, CRPIX1=21.0, CRPIX2=21.0, **T))
        col10 = with_raw_card(P('col10.fits'), b'EXPTIME =60.0')
        tt_blank = mef(P('tt_blank.fits'), {'DATE-OBS': '2025-12-12T21:20:32.000', 'EXPTIME': 60.0, 'TIMESYS': 'TT'}, {'TIMESYS': None})
        exp_blank = mef(P('exp_blank.fits'), {'DATE-OBS': '2025-12-12T21:20:32.000', 'EXPTIME': 60.0}, {'EXPTIME': None})
        first = dict(file=good, x=35, y=35, set=dict(REC3), run=True)
        cases = [dict(name='race', init=SLOW_FIRST_READ, steps=[dict(file=good, nowait=True), dict(file=small),
                                                               dict(sleep=2500, eval="document.getElementById('hdu').options.length")]),
                 dict(name='copy_ok', init=CLIP['ok'], steps=[first, dict(copy=True, eval='window.__copied || null')]),
                 dict(name='copy_none', init=CLIP['none'], steps=[first, dict(copy=True)]),
                 dict(name='copy_refused', init=CLIP['refused'], steps=[first, dict(copy=True)]),
                 dict(name='commas', steps=[dict(first, set=dict(REC3, measurers='A. N. Observer, B. Other'))]),
                 dict(name='col10', steps=[dict(file=col10)]),
                 dict(name='tt_blank', steps=[dict(file=tt_blank)]),
                 dict(name='exp_blank', steps=[dict(file=exp_blank)])]
        if os.path.exists(FLC):
            cases.append(dict(name='flc', steps=[dict(file=FLC, wait=90000, x=685, y=734, set=dict(REC3, est='M'), run=True,
                                                      eval='window.ZeroAp.decodedPixels === undefined ? null : window.ZeroAp.decodedPixels')]))
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

    def test_t1_3_a_later_load_wins(self):
        s = self.steps('race', 3)[2]                                # file A's read slowed 1.5 s; file B chosen meanwhile
        self.assertIn('41×41', s['info']); self.assertNotIn('71×71', s['info'])   # e7051b4: A's late parse shown under B's name
        self.assertEqual(s['eval'], 1)                              # B's one HDU in the list, not A's appended

    def test_t4_2_copy_says_whether_it_copied(self):
        s0, s1 = self.steps('copy_ok', 2)
        with self.subTest('the clipboard took it'):
            self.assertEqual(s1['eval'], s0['ades'])
            self.assertRegex(s1['text'], re.compile('copied', re.I)); self.assertNotRegex(s1['text'], re.compile('could not copy', re.I))
        for name in ('copy_none', 'copy_refused'):                  # e7051b4: not a word, and the old clipboard stays
            with self.subTest(name):
                self.assertRegex(self.steps(name, 2)[1]['text'], re.compile('could not copy', re.I))

    def test_t4_4_a_comma_in_names_is_noted_on_the_page(self):
        s0, = self.steps('commas', 1)
        self.assertIn('! name A. N. Observer, B. Other', s0['ades'])
        self.assertIn('comma', s0['text'])                          # e7051b4: one name, and no word of it

    def test_t1_5_a_card_left_out_is_named_on_the_page(self):
        s0, = self.steps('col10', 1)
        self.assertEqual(s0['tobs'], '', s0['hdrnote'])             # e7051b4: 2025-12-12T21:20:32.00Z, the start as the middle
        self.assertIn('EXPTIME', s0['hdrnote']); self.assertIn('left out', s0['hdrnote'])

    def test_t1_6_a_blank_image_card_hides_nothing_on_the_page(self):
        with self.subTest('a blank TIMESYS over the primary TT'):
            s0, = self.steps('tt_blank', 1)                         # e7051b4: read as UTC, 69 s off
            self.assertEqual(s0['tobs'], ''); self.assertIn('TT', s0['hdrnote'])
        with self.subTest("a blank EXPTIME over the primary's"):
            s0, = self.steps('exp_blank', 1)                        # e7051b4: "no exposure time"
            self.assertEqual(s0['tobs'], '2025-12-12T21:21:02.00Z', s0['hdrnote'])

    @unittest.skipIf(not os.path.exists(FLC), 'the HST frames: tools/fetch_frames.py 03')
    def test_lookup_the_page_on_a_real_hubble_frame(self):
        s0, = self.steps('flc', 1)
        self.assertIn('"/px', s0['info']); self.assertNotIn('not usable', s0['info'])   # e7051b4: "WCS not usable here: lookup-table ..."
        self.assertIn('# version=2022', s0['ades'], s0['ades'][:300])
        r = cli.measure_file(FLC, x=685.0, y=734.0, estimator='M', ades=dict(REC))      # the command line on the same frame
        page, want = record_row(s0['ades']), record_row(r['ades'])
        for k in ('ra', 'dec'):                                      # the record's 6 decimals (the fix room's F1, item 3):
            self.assertLessEqual(abs(float(page[k]) - float(want[k])), 1.01e-6, (k, page[k], want[k]))   # equal, or one step apart
        self.assertIsNotNone(s0['eval'])                             # 1.19's half: the chosen image and its tables, not ERR and DQ
        self.assertLess(s0['eval'], 2 * 2047 * 2050)

    @unittest.skipIf(not (ADES_PYLIB and ADES_MASTER), 'the MPC judge needs ADES_PYLIB and ADES_MASTER')
    def test_judge_accepts_round_3s_page_records(self):
        names = ['commas'] + (['flc'] if os.path.exists(FLC) else [])
        for name in names:
            with self.subTest(name):
                s0 = self.steps(name, 1)[0]
                self.assertIn('# version=2022', s0['ades'])
                d = tempfile.mkdtemp()
                try:
                    ok, why = mpc_judge(s0['ades'], d)
                finally:
                    shutil.rmtree(d, ignore_errors=True)
                self.assertTrue(ok, why)


if __name__ == '__main__':
    unittest.main()
