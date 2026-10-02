"""Round 2 of the hardening, page side (the second hardening round's record of 28 Sept 2026, not in this repository): the page's engine (page/zeroap.js,
through Node) and the page itself in a headless browser (page/browser_cases.js, its multi-step cases: a user's session,
not one load), finding by finding, numbered as in the refuters' record of 28 Sept 2026, not in this repository. Written to fail on the
calibrator as the third room's pull request merged it (b5b6be4) and to pass once each fix is in.
"""
import os, re, json, shutil, tempfile, unittest, warnings, subprocess
import numpy as np
from astropy.io import fits

from domino_calibrator import synth
from domino_calibrator import ades as A
from domino_calibrator import cli
from tests.test_hardening import pig, mpc_judge, ADES_PYLIB, ADES_MASTER
from tests.test_hardening_page import (js, nan, img_payload, fits_bytes, SHRINK_JS, PAGE, NODE, PW, REC_JS,
                                                  REC_PAGE)
from tests.test_hardening_2 import H, lookup_file, SKY_NOISE

PARSE = ("const b = require('fs').readFileSync(D.p); "
         "const h = Z.parseFITS(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));\n")
REC_T = "Object.assign({ra: 168.7, dec: 4.6, time: '2025-12-12T21:21:02.00Z'}, D"      # + the case's own values, then ')'
TAN = dict(CTYPE1='RA---TAN', CTYPE2='DEC--TAN', CRPIX1=36.0, CRPIX2=36.0, CRVAL1=168.7, CRVAL2=4.6,
           CD1_1=-2.1e-4, CD1_2=0.0, CD2_1=0.0, CD2_2=2.1e-4)


def js_capped(code, data=None, timeout=60, heap_mb=200):
    """js() with Node's heap capped and a shorter clock: a loop that eats memory ends the case, not the machine."""
    d = tempfile.mkdtemp()
    try:
        dp = os.path.join(d, 'data.json'); open(dp, 'w', encoding='utf-8').write(json.dumps(data if data is not None else {}))
        sp = os.path.join(d, 's.js')
        open(sp, 'w', encoding='utf-8').write("const Z = require(%s); const D = JSON.parse(require('fs').readFileSync(%s, 'utf8')); let out;\n%s\n"
                            "process.stdout.write(JSON.stringify(out));\n" % (json.dumps(os.path.join(PAGE, 'zeroap.js')), json.dumps(dp), code))
        try:
            r = subprocess.run([NODE, '--max-old-space-size=%d' % heap_mb, sp], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        except subprocess.TimeoutExpired:
            raise AssertionError('node ran past %d s' % timeout)
        if r.returncode != 0:
            raise AssertionError('node failed (exit %d): %s' % (r.returncode, r.stderr.strip()[-300:]))
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def wcs_verdicts(base, cases):
    return js("out = D.cases.map(c => { const w = Z.makeWCS(Object.assign({}, D.base, c)); return w ? (w.unsupported || 'MEASURED') : null; });",
              dict(base=base, cases=cases))


@unittest.skipIf(NODE is None, 'no node')
class TestPageEngine2(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore')
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def p(self, name):
        return os.path.join(self.d, name)

    # ------------------------------------------------ 1: the silent wrong answers
    def test_1_11_a_blank_card_is_absent_not_zero(self):
        # the rule on both faces: a card with no value is absent. b5b6be4's page read '' as 0 (the start as the middle;
        # 1858-11-17), and its Python refused a blank DATE-AVG instead of reading DATE-OBS and EXPTIME
        cases = [dict(DATE_OBS='2025-12-12T21:20:32.000', EXPTIME=None),
                 dict(DATE_OBS='2025-12-12T21:20:32.000', EXPTIME=None, DATE_END='2025-12-12T21:22:32.000'),
                 dict(MJD_OBS=None, EXPTIME=60.0),
                 dict(DATE_AVG=None, DATE_OBS='2025-12-12T21:20:32.000', EXPTIME=60.0)]
        want = [None, '2025-12-12T21:21:32.00Z', None, '2025-12-12T21:21:02.00Z']
        for k, (c, w) in enumerate(zip(cases, want)):
            p = self.p('blank%d.fits' % k)
            fits.PrimaryHDU(np.zeros((8, 8), np.float32), header=H(**c)).writeto(p)
            page = js(PARSE + "out = Z.midExposure(Object.assign({}, h[0].header));", dict(p=p))
            try:
                py = A.mid_exposure(fits.getheader(p))[0]
            except (ValueError, TypeError):
                py = None
            self.assertEqual(page.get('time'), w, (c, page))
            self.assertEqual(py, w, (c, py))

    def test_1_6_an_impossible_header_date_is_refused(self):
        o = js("out = [Z.midExposure({'DATE-OBS': '2025-02-31T12:00:00', EXPTIME: 60}), Z.midExposure({'DATE-OBS': '2025-02-29T12:00:00', EXPTIME: 60}),"
               " Z.midExposure({'DATE-AVG': '2025-04-31T12:00:00'}), Z.midExposure({'DATE-OBS': '2024-02-29T12:00:00', EXPTIME: 60})];")
        for q in o[:3]:                                             # b5b6be4 rolled each into the next month (2025-03-03T12:00:30.00Z)
            self.assertTrue(q.get('error'), q); self.assertFalse(q.get('time'), q)
        self.assertEqual(o[3].get('time'), '2024-02-29T12:00:30.00Z')     # a leap day stands

    def test_4_7_an_impossible_typed_time_is_refused(self):
        o = js("out = ['2026-13-45T00:00:00Z', '2025-02-30T12:00:00Z', '2025-12-12T25:00:00Z', '2025-12-12T21:21:02.00Z']"
               ".map(t => Z.adesPSV(" + REC_T + ", {time: t})));", REC_JS)
        for q in o[:3]:                                             # b5b6be4: a record for each (a pattern check only)
            self.assertTrue(q.get('error'), q); self.assertIn('time', q['error'])
        self.assertIn('2025-12-12T21:21:02.00Z', o[3].get('psv', ''))

    def test_1_18_lookup_table_distortion_is_refused(self):
        p = lookup_file(self.p('lookup.fits'))                      # the CLI reads it with its file open (test_hardening_2)
        o = js(PARSE + "const w = Z.makeWCS(h[0].header); out = w ? (w.unsupported || 'MEASURED') : null;", dict(p=p))
        self.assertTrue(isinstance(o, str) and o != 'MEASURED', o)  # b5b6be4: measured without the table, 0.5 px off
        sip = dict(TAN, CTYPE1='RA---TAN-SIP', CTYPE2='DEC--TAN-SIP', A_ORDER=2, B_ORDER=2, A_2_0=1e-6, B_0_2=1e-6)
        cases =[dict(CPDIS1='LOOKUP', CPDIS2='LOOKUP'), dict(D2IMDIS1='LOOKUP', D2IMDIS2='LOOKUP')]   # HST _flc: SIP with both
        for c, v in zip(cases, wcs_verdicts(sip, cases)):
            self.assertTrue(isinstance(v, str) and v != 'MEASURED', (c, v))

    def test_1_15_the_pc_matrix_takes_its_fits_defaults(self):
        from astropy.wcs import WCS
        base = dict(CTYPE1='RA---TAN', CTYPE2='DEC--TAN', CRPIX1=36.0, CRPIX2=36.0, CRVAL1=168.7, CRVAL2=4.6, CDELT1=-2.1e-4, CDELT2=2.1e-4)
        cases = [dict(PC1_2=0.05, PC2_1=-0.04), dict(PC1_1=0.9), dict(PC2_2=1.1, PC1_2=0.02)]   # the rest default (1 on, 0 off the diagonal)
        pts = [[0.0, 0.0], [70.0, 10.0], [35.0, 35.0], [5.0, 66.0]]
        o = js("out = D.cases.map(c => { const w = Z.makeWCS(Object.assign({}, D.base, c)); return w && !w.unsupported ? D.pts.map(p => w.pixToSky(p[0], p[1])) : null; });",
               dict(base=base, cases=cases, pts=pts))
        for c, got in zip(cases, o):
            self.assertIsNotNone(got, c)
            want = WCS(fits.Header(dict(base, **c))).all_pix2world(pts, 0)
            g = np.array([[np.nan if v is None else v for v in q] for q in got], float)
            d = np.hypot((g[:, 0] - want[:, 0]) * np.cos(np.radians(want[:, 1])), g[:, 1] - want[:, 1]) * 3600
            self.assertLess(np.max(d), 1e-4, (c, d))                # b5b6be4: PC1_2 ignored without PC1_1; a missing PC2_2 read as NaN

    def test_1_14_names_are_not_split_at_commas(self):
        o = js("out = [Z.adesPSV(" + REC_T + ", {measurers: 'Smith, J.', observers: 'Doe, A.; Roe, B.'})),"
               " Z.adesPSV(" + REC_T + ", {measurers: 'Smith, J.\\nDoe, A.'}))];", REC_JS)
        t = o[0].get('psv', '').split('\n')
        self.assertIn('# measurers', t, o[0])
        m = t.index('# measurers'); self.assertEqual(t[m + 1:m + 3], ['! name Smith, J.', '# telescope'])   # b5b6be4: "Smith" and "J."
        b = t.index('# observers'); self.assertEqual(t[b + 1:b + 3], ['! name Doe, A.', '! name Roe, B.'])
        t = o[1].get('psv', '').split('\n'); m = t.index('# measurers')
        self.assertEqual(t[m + 1:m + 3], ['! name Smith, J.', '! name Doe, A.'])
        ph = re.search(r'id="measurers"[^>]*placeholder="([^"]*)"', open(os.path.join(PAGE, 'index.html'), encoding='utf-8').read()).group(1)
        self.assertNotIn('comma', ph); self.assertIn(';', ph)      # the box says how names are separated

    # ------------------------------------------------ 2: answers lost, or refused for the wrong reason
    def test_1_1_a_finite_time_never_throws(self):
        o = js("const f = (h) => { try { return Z.midExposure(h); } catch (e) { return {threw: String(e)}; } };"
               "out = [f({'MJD-OBS': 1e12, EXPTIME: 60}), f({'DATE-OBS': '2025-12-12T21:20:32', EXPTIME: 1e20}), f({'MJD-AVG': -1e12})];")
        for q in o:                                                 # b5b6be4: RangeError: Invalid time value (and the file dropped)
            self.assertNotIn('threw', q, q); self.assertTrue(q.get('error'), q)

    def test_1_12_a_corrupt_size_does_not_loop(self):
        p = self.p('neg.fits')
        h = fits.Header([('SIMPLE', True), ('BITPIX', 16), ('NAXIS', 3), ('NAXIS1', 10), ('NAXIS2', 10), ('NAXIS3', -100)])
        open(p, 'wb').write(h.tostring().encode('ascii') + b'\0' * 2880 * 4)
        files = [p]
        for pc in (-3100, -100000):     # -3100 steps back onto its own header (the loop); -100000 off the file's start (a throw)
            q = self.p('pcount%d.fits' % -pc); files.append(q)
            h0 = fits.Header([('SIMPLE', True), ('BITPIX', 8), ('NAXIS', 0), ('EXTEND', True)])
            h1 = fits.Header([('XTENSION', 'IMAGE'), ('BITPIX', 16), ('NAXIS', 2), ('NAXIS1', 10), ('NAXIS2', 10), ('PCOUNT', pc), ('GCOUNT', 1)])
            open(q, 'wb').write(h0.tostring().encode('ascii') + h1.tostring().encode('ascii') + b'\0' * 2880 * 4)
        for f in files:                 # b5b6be4: NAXIS3 -100 and PCOUNT -3100 ran Node out of memory; -100000 threw RangeError
            o = js_capped(PARSE + "out = h.map(u => ({has: !!u.data}));", dict(p=f))
            self.assertFalse(any(u['has'] for u in o), (f, o))

    # ------------------------------------------------ 3: what the user must see
    def test_4_4_a_deprecated_catalogue_is_noted(self):
        o = js("out = ['Tyc2', 'UCAC4'].map(c => Z.adesPSV(" + REC_T + ", {astCat: c})));", REC_JS)
        self.assertTrue(o[0].get('psv'), o[0])
        self.assertTrue(any('deprecated' in n for n in o[0].get('notes') or []), o[0])   # b5b6be4: said on the command line only
        self.assertFalse(any('deprecated' in n for n in o[1].get('notes') or []), o[1])

    def test_4_5_fz_and_colour_cubes_are_named(self):
        img = np.round(pig(41, 20.2, 19.9, 1.5, amp=3e4) + 150.0).astype(np.int16)
        fz = self.p('c.fits.fz'); fits.HDUList([fits.PrimaryHDU(), fits.CompImageHDU(img)]).writeto(fz)
        rgb = self.p('rgb.fits'); fits.PrimaryHDU(np.stack([img] * 3)).writeto(rgb)
        o = js(PARSE + "out = h.map(u => u.unreadable || null);", dict(p=fz))
        self.assertTrue(any(u and 'funpack' in u for u in o), o)   # b5b6be4: not an image at all ("no 2-D image in this file")
        o = js(PARSE + "out = h.map(u => u.unreadable || null);", dict(p=rgb))
        self.assertTrue(any(u and '3 planes' in u for u in o), o)
        r = cli.measure_file(fz, x=20.0, y=20.0, estimator='M')    # the command line, which the refusal names, reads it
        self.assertTrue(np.isfinite(r['x0']))

    def test_4_6_the_page_names_the_remedy(self):
        # amended before any fix (15:57 UTC): the PV case was PV1_1 and PV2_1 alone, which the command line misreads (a probe:
        # below index 5 astropy keeps TAN and wcslib reads PV1_1, PV1_2 as the projection's reference point, silently). It is now
        # SCAMP's shape, which astropy reads as TPV; the low-order shape must be refused without sending the user there.
        scamp = dict(PV1_0=0.0, PV1_1=1.0, PV1_2=0.0, PV1_5=1e-4, PV2_0=0.0, PV2_1=1.0, PV2_2=0.0, PV2_5=1e-4)
        cli_reads = [dict(CTYPE1='RA---TPV', CTYPE2='DEC--TPV'), dict(CTYPE1='RA---ZPN', CTYPE2='DEC--ZPN'), scamp,
                     dict(A_ORDER=2, B_ORDER=2, A_2_0=1e-5), dict(CTYPE1='DEC--TAN', CTYPE2='RA---TAN'), dict(CPDIS1='LOOKUP', CPDIS2='LOOKUP')]
        for c, v in zip(cli_reads, wcs_verdicts(TAN, cli_reads)):  # b5b6be4 never said that the command line reads these
            self.assertIn('command line', v or '', c)
        low = wcs_verdicts(TAN, [dict(PV1_0=0.0, PV1_1=1.0, PV1_2=0.0, PV2_0=0.0, PV2_1=1.0, PV2_2=0.0)])[0]
        self.assertTrue(isinstance(low, str) and low != 'MEASURED' and 'command line' not in low, low)
        fk4 = wcs_verdicts(TAN, [dict(RADESYS='FK4', EQUINOX=1950.0)])[0]
        self.assertIn('re-solve', fk4 or '')
        t = js("out = Z.midExposure({'DATE-OBS': '2025-12-12T21:20:32.000', EXPTIME: 60, TIMESYS: 'TT'});")
        self.assertIn('command line', t.get('error', ''))
        m = js("out = Z.adesPSV(" + REC_T + ", {mode: ''}));", REC_JS)
        self.assertIn('mode: choose', m.get('error', ''))          # b5b6be4: "not one of the MPC's current modes", for no choice
        b64 = self.p('b64.fits'); fits.PrimaryHDU(np.ones((21, 21), np.int64)).writeto(b64)
        self.assertIn('command line', js(PARSE + "out = h[0].unreadable || '';", dict(p=b64)))


@unittest.skipIf(NODE is None or PW is None, 'no node or no playwright')
class TestPageInBrowser2(unittest.TestCase):
    """The page as a user meets it, over a session: load, measure, then change something (page/browser_cases.js, steps)."""
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore')
        cls.d = tempfile.mkdtemp()
        P = lambda name: os.path.join(cls.d, name)
        img, _ = synth.render(71, 35.25, 34.85, flux_n=3e4, k=400.0, a=0.3, model='dipole', psf=('gauss', 2.5), sub=10)
        img = synth.add_noise(img, 150.0, 5.0, np.random.default_rng(5)).astype(np.float32)
        T = {'DATE-OBS': '2025-12-27T16:04:29.000', 'EXPTIME': 120.0}
        good = fits_bytes(P('good.fits'), img, **dict(TAN, **T))
        notime = fits_bytes(P('notime.fits'), img, **TAN)
        cls.edge_img = (pig(41, 35.3, 20.2, 1.6, amp=3e4) + 150.0 + SKY_NOISE).astype(np.float32)   # SKY_NOISE: F11, the audit's F8.4
        edge = fits_bytes(P('edge.fits'), cls.edge_img, **dict(TAN, CRPIX1=21.0, CRPIX2=21.0, **T))
        garbage = P('garbage.fits'); open(garbage, 'w', encoding='utf-8').write('this is not a FITS file\n' * 40)
        fz = P('c.fits.fz'); fits.HDUList([fits.PrimaryHDU(), fits.CompImageHDU(np.round(img).astype(np.int16))]).writeto(fz)
        rgb = fits_bytes(P('rgb.fits'), np.stack([img] * 3))
        bigtime = fits_bytes(P('bigtime.fits'), img, **dict(TAN, **{'MJD-OBS': 1e12, 'EXPTIME': 120.0}))
        tt = fits_bytes(P('tt.fits'), img, **dict(TAN, TIMESYS='TT', **T))
        first = dict(file=good, x=35, y=35, set=dict(REC_PAGE), run=True)
        cases = [dict(name='newfile', steps=[first, dict(file=notime)]),
                 dict(name='badfile', steps=[first, dict(file=garbage), dict(run=True)]),
                 dict(name='field', steps=[first, dict(set={'tobs': '2025-12-27T16:10:00.00Z', 'stn': 'J95'})]),
                 dict(name='start', steps=[first, dict(x=30, y=31)]),
                 dict(name='method', steps=[first, dict(set={'est': 'M'})]),
                 dict(name='edgefull', steps=[dict(file=edge, x=35, y=20, set=dict(REC_PAGE), run=True),   # the radii off the image: no record (B2)
                                              dict(set=dict(r1='4.0'), run=True)]),                         # radii that all converge: its record
                 dict(name='tyc2', steps=[dict(first, set=dict(REC_PAGE, astcat='Tyc2'))]),
                 dict(name='fz', steps=[dict(file=fz)]),
                 dict(name='rgb', steps=[dict(file=rgb)]),
                 dict(name='bigtime', steps=[dict(file=bigtime)]),
                 dict(name='tt', steps=[dict(file=tt)])]
        cp = P('cases.json'); json.dump(cases, open(cp, 'w', encoding='utf-8'))
        r = subprocess.run([NODE, os.path.join(PAGE, 'browser_cases.js'), cp], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600,
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

    def test_1_10_4_9_another_file_clears_the_answer(self):
        s0, s1 = self.steps('newfile', 2)
        self.assertIn('# version=2022', s0['ades']); self.assertFalse(s0['copyDisabled'])   # first a record, as a user makes one
        self.assertTrue(s1['copyDisabled'], s1['ades'])             # b5b6be4: file 1's record, copyable beside file 2's image
        self.assertNotIn('# version', s1['ades']); self.assertEqual(s1['zero'].strip(), '')

    def test_1_10_a_failed_load_forgets_the_old_image(self):
        s0, s1, s2 = self.steps('badfile', 3)
        self.assertIn('Could not read', s1['info'])
        self.assertTrue(s1['copyDisabled'], s1['ades']); self.assertNotIn('# version', s1['ades'])   # b5b6be4: the old record, live
        self.assertIn('Load a FITS', s2['status']); self.assertTrue(s2['copyDisabled'])   # b5b6be4: Measure went on with the old image

    def test_1_10_a_changed_field_never_leaves_a_stale_record(self):
        s0, s1 = self.steps('field', 2)
        self.assertIn('2025-12-27T16:05:29.00Z', s0['ades'])
        if not s1['copyDisabled']:                                  # a live record must be the boxes' record
            self.assertIn('2025-12-27T16:10:00.00Z', s1['ades']); self.assertIn('! mpcCode J95', s1['ades'])   # b5b6be4: the old one
            self.assertNotIn('16:05:29', s1['ades'])

    def test_1_10_a_new_start_or_method_clears_the_answer(self):
        for name in ('start', 'method'):
            s0, s1 = self.steps(name, 2)
            self.assertFalse(s0['copyDisabled'], name)
            self.assertTrue(s1['copyDisabled'], name); self.assertNotIn('# version', s1['ades'], name)   # b5b6be4: the old answer

    def test_4_3_the_page_remarks_name_the_radii_fitted(self):
        o = js(SHRINK_JS, dict(img_payload(self.edge_img.astype(np.float64)), x0=35.0, y0=20.0, opts=dict(estimator='G', background='annulus')))
        ok = [r for r, k in zip(o['radii'], o['ok']) if k]
        # the audit room's B2 (30 Sept 2026): no record unless every radius converged; b5b6be4's "r 2-6 px" cannot recur
        s0, s1 = self.steps('edgefull', 2)
        self.assertNotIn('# version=2022', s0['ades'])
        self.assertIn('needs a comet measured (only %d of %d radii converged' % (len(ok), len(o['radii'])), s0['ades'])
        self.assertIn('# version=2022', s1['ades']); self.assertIn('21 of 21 radii, r 2.0-4.0 px', s1['ades'])

    def test_4_4_the_page_notes_a_deprecated_catalogue(self):
        s0, = self.steps('tyc2', 1)
        self.assertIn('# version=2022', s0['ades']); self.assertIn('deprecated', s0['text'])   # b5b6be4: a record, and not a word
        self.assertNotIn('deprecated', self.steps('newfile', 2)[0]['text'])                     # Gaia3: nothing to say

    def test_4_5_fz_and_colour_cubes_are_named_on_the_page(self):
        self.assertIn('funpack', self.steps('fz', 1)[0]['info'])   # b5b6be4: "Could not read: no 2-D image in this file"
        self.assertIn('3 planes', self.steps('rgb', 1)[0]['info'])

    def test_1_1_a_huge_header_time_keeps_the_file(self):
        s0, = self.steps('bigtime', 1)
        self.assertNotIn('Could not read', s0['info']); self.assertIn('71', s0['info'])   # b5b6be4: "Could not read: Invalid time value"
        self.assertEqual(s0['tobs'], '')

    def test_4_6_the_time_refusal_is_said_once_and_names_the_command_line(self):
        s0, = self.steps('tt', 1)
        self.assertLessEqual(s0['hdrnote'].count('type the mid-exposure'), 1, s0['hdrnote'])   # b5b6be4: said twice
        self.assertIn('command line', s0['hdrnote'])

    @unittest.skipIf(not (ADES_PYLIB and ADES_MASTER), 'the MPC judge needs ADES_PYLIB and ADES_MASTER')
    def test_judge_accepts_round_2s_page_records(self):
        for name, n in (('edgefull', 2), ('tyc2', 1)):              # the fitted radii in the remarks; a deprecated catalogue
            s0 = self.steps(name, n)[-1]
            self.assertIn('# version=2022', s0['ades'], name)
            d = tempfile.mkdtemp()
            try:
                ok, why = mpc_judge(s0['ades'], d)
            finally:
                shutil.rmtree(d, ignore_errors=True)
            self.assertTrue(ok, '%s: %s' % (name, why))
        o = js("out = Z.adesPSV(" + REC_T + ", {measurers: 'Smith, J.; Doe, A.', observers: 'Roe, B.'}));", REC_JS)
        d = tempfile.mkdtemp()
        try:
            ok, why = mpc_judge(o['psv'], d)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertTrue(ok, 'names with commas: ' + why)


if __name__ == '__main__':
    unittest.main()
