"""The hardening round's bar, page side (the hardening round's record of 27 Sept 2026, not in this repository): the page's engine (page/zeroap.js,
through Node) brought to the Python's contract, finding by finding (#3, #4, #8-#10, #18's refusal, and the page's own
copies of #5, #6, #12-#15, #17, #19), and the page itself in a headless browser (page/browser_cases.js). Written to fail
on the calibrator as merged in c0ae330 and to pass once each fix is in.
"""
import os, sys, json, shutil, tempfile, unittest, warnings, subprocess
import numpy as np
from astropy.io import fits

from domino_calibrator import synth
from domino_calibrator.estimators import moment_centroid, gauss_fit
from domino_calibrator.shrink import shrink
from tests.test_hardening import pig, REC, mpc_judge, ADES_PYLIB, ADES_MASTER

PAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'page')
NODE = shutil.which('node') or ('/opt/node22/bin/node' if os.path.exists('/opt/node22/bin/node') else None)
PW = os.environ.get('PLAYWRIGHT_MODULE') or ('/opt/node22/lib/node_modules/playwright'
                                              if os.path.exists('/opt/node22/lib/node_modules/playwright') else None)
REC_JS = dict(stn=REC['stn'], desig=REC['desig'], mode=REC['mode'], astCat=REC['ast_cat'], submitter=REC['submitter'],
              measurers=REC['measurers'], design=REC['design'], aperture=REC['aperture'], detector=REC['detector'])


def js(code, data=None, timeout=120):
    """Run `code` in Node with Z = zeroap.js and D = the JSON data; the code sets `out`, printed as JSON (NaN -> null)."""
    d = tempfile.mkdtemp()
    try:
        dp = os.path.join(d, 'data.json'); open(dp, 'w', encoding='utf-8').write(json.dumps(data if data is not None else {}))
        sp = os.path.join(d, 's.js')
        open(sp, 'w', encoding='utf-8').write("const Z = require(%s); const D = JSON.parse(require('fs').readFileSync(%s, 'utf8')); let out;\n%s\n"
                            "process.stdout.write(JSON.stringify(out));\n" % (json.dumps(os.path.join(PAGE, 'zeroap.js')), json.dumps(dp), code))
        r = subprocess.run([NODE, sp], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=timeout)
        if r.returncode != 0:
            raise AssertionError('node failed: ' + r.stderr.strip()[-600:])
        return json.loads(r.stdout)
    finally:
        shutil.rmtree(d, ignore_errors=True)


def nan(v):
    return np.array([np.nan if u is None else u for u in v], float)


def img_payload(img):
    return dict(img=[None if not np.isfinite(v) else float(v) for v in img.ravel()], nx=img.shape[1], ny=img.shape[0])


SHRINK_JS = ("const im = Float64Array.from(D.img.map(v => v === null ? NaN : v));\n"
             "out = Z.shrink(im, D.nx, D.ny, D.x0, D.y0, D.opts);")


def parity(test, img, x0, y0, est, background, radii=None, tol=None):
    """The page's shrink against the Python's on the same pixels: ok per radius, positions where ok, NaN where not."""
    opts = dict(estimator=est, background=background)
    if radii is not None:
        opts['radii'] = [float(r) for r in radii]
    o = js(SHRINK_JS, dict(img_payload(img), x0=x0, y0=y0, opts=opts))
    p = shrink(img, x0, y0, estimator=est, background=background, **({} if radii is None else dict(radii=np.asarray(radii))))
    tol = tol or (1e-5 if est == 'G' else 1e-7)
    test.assertEqual([bool(v) for v in o['ok']], [bool(v) for v in p['ok']])
    test.assertEqual(len(o['reason']), len(p['radii']))
    for k in range(len(p['radii'])):
        test.assertEqual(bool(o['ok'][k]), o['reason'][k] == '')
    x, y = nan(o['x']), nan(o['y'])
    test.assertTrue(np.array_equal(np.isnan(x), np.isnan(p['x'])))
    good = np.isfinite(p['x'])
    if good.any():
        test.assertLess(np.max(np.abs(x[good] - p['x'][good])), tol)
        test.assertLess(np.max(np.abs(y[good] - p['y'][good])), tol)
    test.assertEqual(o['nbad'], p['nbad'])
    return o, p


def fits_bytes(path, img, **cards):
    h = fits.Header()
    for k, v in cards.items():
        h[k] = v
    fits.PrimaryHDU(img, header=h).writeto(path, overwrite=True)
    return path


@unittest.skipIf(NODE is None, 'no node')
class TestPageEngine(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore')
        self.d = tempfile.mkdtemp()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_03_edge_is_a_reason_not_a_throw(self):
        img = pig(41, 35.3, 20.2, 1.6) + 100.0                    # 5.7 px from the right edge: r = 6 leaves the image
        for est in ('G', 'M'):
            o, p = parity(self, img, 35.0, 20.0, est, 100.0)       # c0ae330: "aperture leaves the image", no result
            self.assertTrue(any('leaves the image' in w for w in o['reason']))

    def test_03b_small_annulus_is_a_reason_not_a_throw(self):
        img = pig(21, 10.2, 9.9, 1.5) + 100.0                     # a 21 x 21 cutout: the 2.5r-5r annulus runs out
        for est in ('G', 'M'):
            o, p = parity(self, img, 10.0, 10.0, est, 'annulus')  # c0ae330: "annulus has fewer than 8 pixels", no result

    def test_04a_aitken_jump_is_bounded_as_in_python(self):
        yy, xx = np.indices((81, 81))
        img = 1e4 * np.exp(-0.5 * ((xx - 40.0) ** 2 + (yy - 40.0) ** 2) / 10.0 ** 2)   # sigma 10 px: M creeps at r = 2
        o = js("const im = Float64Array.from(D.img); out = Z.momentCentroid(im, D.nx, D.ny, 30.0, 40.0, 2.0, 0.0);", img_payload(img))
        p = moment_centroid(img, 30.0, 40.0, 2.0, bkg=0.0)
        self.assertEqual(bool(o['ok']), bool(p['ok']), (o, p))     # c0ae330: the page jumped 9.8 px and said ok
        self.assertEqual(o['n'], p['n'])
        if p['ok']:
            self.assertLess(abs(o['x'] - p['x']), 1e-9)

    def test_04b_nan_background_is_a_reason(self):
        img = pig(41, 20.2, 19.9, 1.5) + 100.0
        yy, xx = np.indices(img.shape); img[np.hypot(xx - 20, yy - 20) > 8.5] = np.nan   # the annulus of r >= 3.4 is empty
        o, p = parity(self, img, 20.0, 20.0, 'M', 'annulus')       # c0ae330: the page read the NaN background as 0
        self.assertTrue(any('background' in w for w in o['reason']))

    def test_04c_G_small_apertures_are_refused(self):
        img = pig(41, 20.2, 19.9, 1.5) + 100.0
        o = js("const im = Float64Array.from(D.img); out = [0.3, 0.5, 0.7].map(r => Z.gaussFit(im, D.nx, D.ny, 20.2, 19.9, r, 100.0));",
               img_payload(img))
        for q in o:                                                 # c0ae330: ok from 1-5 pixels and four parameters
            self.assertFalse(q['ok']); self.assertIn('fewer than 8', q['reason'])
        self.assertFalse(js("const im = Float64Array.from(D.img); out = Z.gaussFit(im, D.nx, D.ny, 20.0, 20.0, 4.0, 1000.0);",
                            img_payload(1000.0 - pig(41, 20.3, 19.8, 1.5, amp=5e3)))['ok'])    # amplitude <= 0, as in Python

    def test_05_no_time_no_record(self):
        o = js("out = Z.adesPSV(Object.assign({ra: 168.7, dec: 4.6, time: ''}, D));", REC_JS)
        self.assertIn('time', o.get('error', '')); self.assertNotIn('YYYY', json.dumps(o))   # c0ae330: a copy-ready placeholder

    def test_06_cube_with_one_plane(self):
        p = fits_bytes(os.path.join(self.d, 'cube.fits'), (pig(21, 10.2, 9.9, 1.5) + 100.0)[None].astype(np.float32))
        o = js("const b = require('fs').readFileSync(D.p); const h = Z.parseFITS(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));"
               "out = h.map(u => ({has: !!u.data, nx: u.nx, ny: u.ny}));", dict(p=p))
        self.assertTrue(o[0]['has']); self.assertEqual((o[0]['nx'], o[0]['ny']), (21, 21))

    def test_08_radii_are_validated(self):
        o = js("out = [[2, 6, 0], [2, 6, -0.1], [2, 6, NaN], [6, 2, 0.1], [0, 6, 0.1], [2, 6, 0.1]].map(a => Z.radiiFrom(a[0], a[1], a[2]));")
        for q in o[:5]:
            self.assertTrue(q.get('error'), q)                     # c0ae330: a zero or negative step froze the tab
        self.assertEqual(len(o[5]['radii']), 41); self.assertAlmostEqual(o[5]['radii'][-1], 6.0)

    def test_09_unparseable_date_is_a_reason_not_a_throw(self):
        o = js("out = [Z.midExposure({'DATE-OBS': '27/12/25', EXPTIME: 60}), Z.midExposure({'DATE-OBS': 'yesterday', EXPTIME: 60})];")
        for q in o:                                                 # c0ae330: RangeError, and the page dropped the file
            self.assertTrue(q.get('error')); self.assertFalse(q.get('time'))

    def test_10_big_images_are_refused_and_the_stretch_is_sampled(self):
        p = os.path.join(self.d, 'big.fits')
        h = fits.Header(); h['SIMPLE'] = True; h['BITPIX'] = 16; h['NAXIS'] = 2; h['NAXIS1'] = 8192; h['NAXIS2'] = 8192
        open(p, 'wb').write(h.tostring().encode('ascii'))           # a header that promises 67 Mpx (the data is not needed)
        o = js("const b = require('fs').readFileSync(D.p); const h = Z.parseFITS(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));"
               "out = h.map(u => ({has: !!u.data, tooBig: u.tooBig || null, nx: u.nx, ny: u.ny}));", dict(p=p))
        self.assertFalse(o[0]['has']); self.assertTrue(o[0]['tooBig'])
        o = js("const n = 4096 * 4096, a = new Float64Array(n); for (let i = 0; i < n; i++) a[i] = i % 1000; let reads = 0;"
               "const P = new Proxy(a, {get(t, k) { if (typeof k === 'string' && /^\\d+$/.test(k)) reads++; const v = t[k]; return typeof v === 'function' ? v.bind(t) : v; }});"
               "const s = Z.stretch(P, n); out = {lo: s.lo, hi: s.hi, reads: reads};", timeout=300)
        self.assertLessEqual(o['reads'], 2000000)                   # c0ae330 sorted every pixel on load (16.7 M here)
        self.assertLess(o['lo'], 100); self.assertGreater(o['hi'], 900)

    def test_12_14_ades_2022_parity(self):
        o = js("out = [Z.adesPSV(Object.assign({ra: 168.7, dec: 4.6, time: '2025-12-12T21:21:02.00Z'}, D)),"
               " Z.adesPSV(Object.assign({ra: 359.99999996, dec: 1.0, time: '2025-12-12T21:21:02.00Z'}, D)),"
               " Z.adesPSV(Object.assign({ra: 168.7, dec: 4.6, time: '2025-12-12T21:21:02.00Z'}, D, {desig: 'C/2025 N1'})),"
               " Z.adesPSV(Object.assign({ra: 168.7, dec: 4.6, time: '2025-12-12T21:21:02.00Z'}, D, {mode: 'CMOS'})),"
               " Z.adesPSV(Object.assign({ra: 168.7, dec: 4.6, time: '2025-12-12T21:21:02.00Z'}, D, {astCat: 'GaiaDR3'}))];", REC_JS)
        lines = o[0]['psv'].strip().split('\n')
        self.assertEqual(lines[0], '# version=2022'); self.assertEqual(lines[1], '# observatory')
        for block in ('# submitter', '# measurers', '# telescope'):
            self.assertIn(block, lines)
        row = dict(zip([s.strip() for s in o[1]['psv'].strip().split('\n')[-2].split('|')], [s.strip() for s in o[1]['psv'].strip().split('\n')[-1].split('|')]))
        self.assertEqual(row['ra'], '0.000000')                     # c0ae330: 360.0000000 (6 decimals since the fix room's F1)
        self.assertIn('provID', o[2]['psv'].strip().split('\n')[-2])
        self.assertTrue(o[3].get('error')); self.assertTrue(o[4].get('error'))

    def test_15_time_parity(self):
        o = js("out = [Z.midExposure({'DATE-OBS': '2025-12-12T21:20:32.000'}),"
               " Z.midExposure({'DATE-OBS': '2025-12-12T21:20:32.000', EXPTIME: 60, 'DATE-AVG': '2025-12-12T21:22:32.000'}),"
               " Z.midExposure({'DATE-OBS': '2025-12-12T21:20:32.000', 'DATE-END': '2025-12-12T21:22:32.000'}),"
               " Z.midExposure({'MJD-OBS': 61021.0, EXPTIME: 60, 'MJD-AVG': 61021.5}),"
               " Z.midExposure({'DATE-OBS': '2025-12-12T21:20:32.000', EXPTIME: 60, TIMESYS: 'TT'}),"
               " Z.midExposure({'DATE-OBS': '2025-12-12T21:20:32.000', EXPTIME: 60})];")
        self.assertTrue(o[0].get('error'))                          # c0ae330 wrote the start as the mid-exposure
        self.assertEqual(o[1]['time'], '2025-12-12T21:22:32.00Z')
        self.assertEqual(o[2]['time'], '2025-12-12T21:21:32.00Z')
        self.assertEqual(o[3]['time'], '2025-12-12T12:00:00.00Z')
        self.assertTrue(o[4].get('error'))                          # the page reads UTC only, and says so
        self.assertEqual(o[5]['time'], '2025-12-12T21:21:02.00Z'); self.assertIn('EXPTIME', o[5]['note'])

    def test_18_17_unsupported_wcs_is_refused_not_misread(self):
        base = dict(CTYPE1='RA---TAN', CTYPE2='DEC--TAN', CRPIX1=36.0, CRPIX2=36.0, CRVAL1=168.7, CRVAL2=4.6,
                    CD1_1=-2.1e-4, CD1_2=0.0, CD2_1=0.0, CD2_2=2.1e-4)
        cases = [dict(CTYPE1='RA---TPV', CTYPE2='DEC--TPV'), dict(PV1_1=1.0, PV2_1=1.0), dict(A_ORDER=2, B_ORDER=2, A_2_0=1e-5),
                 dict(CTYPE1='DEC--TAN', CTYPE2='RA---TAN'), dict(RADESYS='FK4', EQUINOX=1950.0), dict(EQUINOX=1950.0),
                 dict(CTYPE1='GLON-TAN', CTYPE2='GLAT-TAN'), dict(CTYPE1='RA---ZPN', CTYPE2='DEC--ZPN')]
        o = js("out = D.cases.map(c => { const w = Z.makeWCS(Object.assign({}, D.base, c)); return w ? (w.unsupported || 'MEASURED') : null; });",
               dict(base=base, cases=cases))
        for c, v in zip(cases, o):                                  # c0ae330: TPV/ZPN read as "no WCS"; the rest measured wrong
            self.assertTrue(isinstance(v, str) and v != 'MEASURED', (c, v))
        ok = js("const w = Z.makeWCS(Object.assign({}, D.base, {RADESYS: 'FK5', EQUINOX: 2000})); out = {u: w.unsupported || null, notes: w.notes || []};",
                dict(base=base))
        self.assertIsNone(ok['u']); self.assertTrue(any('ICRS' in n for n in ok['notes']))

    def test_19_blank_pixels_are_not_data(self):
        a = np.full((21, 21), 1000, np.int16); a[10, 12] = -32768
        p = fits_bytes(os.path.join(self.d, 'blank.fits'), a, BLANK=-32768)
        o = js("const b = require('fs').readFileSync(D.p); const h = Z.parseFITS(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));"
               "out = [h[0].data[10 * 21 + 12], h[0].data[0]];", dict(p=p))
        self.assertIsNone(o[0]); self.assertEqual(o[1], 1000.0)     # c0ae330: -32768, a pixel of data

    @unittest.skipIf(not (ADES_PYLIB and ADES_MASTER), 'the MPC judge needs ADES_PYLIB and ADES_MASTER')
    def test_mpc_judge_accepts_the_page_record(self):
        o = js("out = [Z.adesPSV(Object.assign({ra: 168.7, dec: 4.6, time: '2025-12-12T21:21:02.00Z'}, D)),"
               " Z.adesPSV(Object.assign({ra: 168.7, dec: 4.6, time: '2025-12-12T21:21:02.00Z'}, D, {desig: 'C/2025 N1', mode: 'CMO'}))];", REC_JS)
        for q in o:
            ok, why = mpc_judge(q['psv'] if isinstance(q, dict) else q, self.d)   # c0ae330: version 2017, blocks missing
            self.assertTrue(ok, why)


@unittest.skipIf(NODE is None or PW is None, 'no node or no playwright')
class TestPageInBrowser(unittest.TestCase):
    """The page as a user meets it: page/browser_cases.js drives headless Chromium through each case (heap capped at
    256 MB, 8 s per case, so a frozen tab ends the case instead of the machine) and reports what the page shows."""
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore')
        cls.d = tempfile.mkdtemp()
        img, _ = synth.render(71, 35.25, 34.85, flux_n=3e4, k=400.0, a=0.3, model='dipole', psf=('gauss', 2.5), sub=10)
        img = synth.add_noise(img, 150.0, 5.0, np.random.default_rng(5)).astype(np.float32)
        wcs = dict(CTYPE1='RA---TAN', CTYPE2='DEC--TAN', CRPIX1=36.0, CRPIX2=36.0, CRVAL1=168.7, CRVAL2=4.6,
                   CD1_1=-2.1e-4, CD1_2=0.0, CD2_1=0.0, CD2_2=2.1e-4)
        cls.good = fits_bytes(os.path.join(cls.d, 'good.fits'), img, **dict(wcs, **{'DATE-OBS': '2025-12-27T16:04:29.000', 'EXPTIME': 120.0}))
        cls.baddate = fits_bytes(os.path.join(cls.d, 'baddate.fits'), img, **dict(wcs, **{'DATE-OBS': '27/12/25', 'EXPTIME': 120.0}))
        cls.notime = fits_bytes(os.path.join(cls.d, 'notime.fits'), img, **wcs)
        edge = (pig(41, 35.3, 20.2, 1.6, amp=3e4) + 150.0).astype(np.float32)
        cls.edge = fits_bytes(os.path.join(cls.d, 'edge.fits'), edge, **dict(wcs, CRPIX1=21.0, CRPIX2=21.0, **{'DATE-OBS': '2025-12-27T16:04:29.000', 'EXPTIME': 120.0}))
        cases = [dict(name='step0', file=cls.good, x=35, y=35, set={'rs': '0'}),
                 dict(name='baddate', file=cls.baddate, x=35, y=35, set={}),
                 dict(name='edge', file=cls.edge, x=35, y=20, set={}),
                 dict(name='notime', file=cls.notime, x=35, y=35, set=dict(REC_PAGE)),
                 dict(name='full', file=cls.good, x=35, y=35, set=dict(REC_PAGE))]
        cp = os.path.join(cls.d, 'cases.json'); json.dump(cases, open(cp, 'w', encoding='utf-8'))
        r = subprocess.run([NODE, os.path.join(PAGE, 'browser_cases.js'), cp], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300,
                           env=dict(os.environ, PLAYWRIGHT_MODULE=PW))
        cls.err = r.stderr[-800:]
        try:
            cls.res = {c['name']: c for c in json.loads(r.stdout)}
        except Exception:
            cls.res = None

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def case(self, name):
        self.assertIsNotNone(self.res, 'browser_cases.js gave no result: ' + self.err)
        return self.res[name]

    def test_08_zero_step_is_refused_not_frozen(self):
        c = self.case('step0')                                      # c0ae330: the tab froze (the case timed out or crashed)
        self.assertFalse(c.get('timeout') or c.get('crashed'), c); self.assertIn('step', c['status'])

    def test_09_bad_date_keeps_the_file(self):
        c = self.case('baddate')                                    # c0ae330: "Could not read: Invalid time value"
        self.assertNotIn('Could not read', c['info']); self.assertIn('71', c['info']); self.assertEqual(c['tobs'], '')

    def test_03_edge_gives_a_measurement(self):
        c = self.case('edge')                                       # c0ae330: "Error: aperture leaves the image", nothing else
        self.assertNotIn('Error', c['status']); self.assertIn('did not converge', c['status']); self.assertIn('Zero-aperture', c['zero'])

    def test_05_no_time_no_record_and_nothing_to_copy(self):
        c = self.case('notime')                                     # c0ae330: a record with YYYY-MM-DDThh:mm:ss.ssZ, copyable
        self.assertNotIn('YYYY', c['ades']); self.assertNotIn('permID', c['ades']); self.assertTrue(c['copyDisabled'])

    def test_full_record_on_the_page(self):
        c = self.case('full')
        self.assertIn('# version=2022', c['ades']); self.assertFalse(c['copyDisabled']); self.assertEqual(c['errors'], [])


REC_PAGE = {'stn': REC['stn'], 'desig': REC['desig'], 'mode': REC['mode'], 'astcat': REC['ast_cat'], 'submitter': REC['submitter'],
            'measurers': ', '.join(REC['measurers']), 'design': REC['design'], 'aperture': REC['aperture'], 'detector': REC['detector']}


if __name__ == '__main__':
    unittest.main()
