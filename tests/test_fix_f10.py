"""The fix room's F10: B2's cure, from the second audit room's report (1 Oct 2026, his word for the night's second part,
the fix room's record of 1 Oct 2026, not in this repository, section 25). Written before the fix, to fail on the tool as F9 left it, and
to pass once it is fixed. His cure, both: the words say what the checks measure, and that telling a comet from a star is
the observer's; a record comes only from a start the observer gives, typed or clicked (the page's F8.7 first: a typed start
equal to the brightest box counted as automatic); the automatic start still gives the pixel answer and its reasons, without
a record, and says what to do next; a single-pixel peak is refused on both faces (F8.2). No new option.
"""
import os, re, sys, json, subprocess, tempfile, shutil, unittest, warnings

import numpy as np
from astropy.io import fits

from domino_calibrator import cli, synth
from tests.test_hardening import REC, REC_ARGS, Tmp, comet, write, wcs_cards
from tests.test_hardening_page import js, NODE, PW, PAGE, fits_bytes
from tests.test_hardening_page import REC_PAGE

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CLI_START = 'a start you give: give --x and --y on the comet to get a record'
PAGE_START = 'a start you give: click on the comet to get a record'
SINGLE = 'its peak is a single pixel'


def cli_run(args):
    r = subprocess.run([sys.executable, '-m', 'domino_calibrator.cli'] + args, cwd=ROOT, capture_output=True, encoding='utf-8',
                       errors='replace', timeout=600, env=dict(os.environ, PYTHONUTF8='1'))
    return r.returncode, r.stdout + r.stderr


def engine(path, start, auto, est='G'):
    return js("""
const fs = require('fs');
const hdus = Z.parseFITS(new Uint8Array(fs.readFileSync(D.p)).buffer), cur = hdus.find((u) => u.readable);
const s = D.start || Z.brightestStart(cur.data, cur.nx, cur.ny);
const o = Z.shrink(cur.data, cur.nx, cur.ny, s[0], s[1], { estimator: D.est || 'G', radii: Z.publishedRadii(), background: 'annulus' });
const r = Z.decide({ cur: cur, hdus: hdus, o: o, start: s, auto: D.auto });
out = { need: r.need, rd: r.rd };""", {'p': path, 'start': start, 'auto': auto, 'est': est})


def hot(path, seed=1, est_pixel=(22, 40)):
    d = np.random.default_rng(seed).normal(100, 5, (64, 64)); d[est_pixel[1], est_pixel[0]] += 25000
    h = wcs_cards(fits.Header(), n=64); h['DATE-OBS'] = '2025-12-12T21:20:32.000'; h['EXPTIME'] = 60.0
    fits.PrimaryHDU(d.astype(np.float32), header=h).writeto(path, overwrite=True)
    return path


class F10_1_ARecordOnlyFromAGivenStart(Tmp):
    def test_the_automatic_start_gives_the_pixel_answer_and_says_what_to_do(self):
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        rc, out = cli_run([p] + REC_ARGS)
        self.assertEqual(rc, 0, out[-400:])                                # the checks passed: the measurement's code
        self.assertNotIn('# version=2022', out)
        self.assertRegex(out, r'# zero aperture: x \S+ y \S+')
        self.assertIn(CLI_START, out)
        rc, out = cli_run([p, '--x', '35', '--y', '35'] + REC_ARGS)        # the control: a start given, a record
        self.assertEqual(rc, 0, out[-400:]); self.assertIn('# version=2022', out)

    def test_the_page_engine_the_same(self):
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        e = engine(p, None, True)
        self.assertIn(PAGE_START, ' '.join(e['need']))
        e = engine(p, [35, 35], False)
        self.assertEqual(e['need'], [])


class F10_2_ASinglePixelIsNoSource(Tmp):
    def test_a_hot_pixel_is_refused_on_both_faces_from_a_start_on_it(self):
        for est in ('G', 'M'):
            for seed in (1, 2, 3):
                with self.subTest(est=est, seed=seed):
                    p = hot(self.p('hot.fits'), seed)
                    r = cli.measure_file(p, 22, 40, est, ades=dict(REC))
                    self.assertNotIn('ades', r)
                    self.assertTrue(r.get('comet_error'), r)
                    if est == 'M':                    # G started on a lone pixel fails earlier, with its own true reason
                        self.assertIn(SINGLE, r['comet_error'])
                    e = engine(p, [22, 40], False, est)
                    self.assertIsNone(None if e['need'] else 'no need', e)
                    if est == 'M':
                        self.assertTrue(any(SINGLE in n for n in e['need']), e['need'])

    def test_a_sharp_real_source_still_passes(self):
        # a comet at 1.5"/px in 2.1" seeing: FWHM 1.4 px, the sharpest the study's gate must keep
        img, _ = synth.render(101, 50.3, 50.7, flux_n=4e4, k=200.0, a=0.2, model='dipole', psf=('gauss', 1.4 / 2.3548), sub=10)
        img = synth.add_noise(img, 400.0, 20.0, np.random.default_rng(3))
        p = write(self.p('sharp.fits'), img)
        r = cli.measure_file(p, 50, 51)
        self.assertNotIn('comet_error', r, r.get('comet_error'))


@unittest.skipIf(NODE is None or PW is None, 'no node or no playwright')
class F10_3_ThePageInABrowser(unittest.TestCase):
    """The page as a user meets it: no click, no record; the start typed equal to the brightest box is a start given (F8.7)."""
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore')
        cls.d = tempfile.mkdtemp()
        img = (synth.render(100, 40.3, 50.7, flux_n=2e4, k=400.0, a=0.3, model='dipole', psf=('gauss', 1.3), sub=10)[0]
               + synth.render(100, 70.0, 50.0, flux_n=8e3, k=0.0, a=0.0, model='dipole', psf=('gauss', 1.3), sub=10)[0])
        img = synth.add_noise(img, 100.0, 5.0, np.random.default_rng(3)).astype(np.float32)
        wcs = dict(CTYPE1='RA---TAN', CTYPE2='DEC--TAN', CRPIX1=50.0, CRPIX2=50.0, CRVAL1=168.7, CRVAL2=4.6, CD1_1=-2.1e-4,
                   CD1_2=0.0, CD2_1=0.0, CD2_2=2.1e-4)
        cls.two = fits_bytes(os.path.join(cls.d, 'two.fits'), img, **dict(wcs, **{'DATE-OBS': '2025-12-27T16:04:29.000', 'EXPTIME': 120.0}))
        bx, by = cli._start(img.astype(float))
        cls.box = (bx, by)
        cases = [dict(name='auto', steps=[dict(file=cls.two, set=dict(REC_PAGE), run=True)]),
                 dict(name='typed_box', steps=[dict(file=cls.two, x=bx, y=by, set=dict(REC_PAGE), run=True)])]
        cp = os.path.join(cls.d, 'cases.json'); json.dump(cases, open(cp, 'w', encoding='utf-8'))
        r = subprocess.run([NODE, os.path.join(PAGE, 'browser_cases.js'), cp], capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=300, env=dict(os.environ, PLAYWRIGHT_MODULE=PW))
        cls.err = r.stderr[-800:]
        try:
            cls.res = {c['name']: c for c in json.loads(r.stdout)}
        except Exception:
            cls.res = None

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def step(self, name):
        self.assertIsNotNone(self.res, 'browser_cases.js gave no result: ' + self.err)
        return self.res[name]['steps'][-1]

    def test_no_click_no_record_and_the_page_says_click(self):
        s = self.step('auto')
        self.assertNotIn('version=2022', s['ades'], s['status'])
        self.assertTrue(s['copyDisabled'])
        self.assertIn('click on the comet', s['text'])

    def test_a_start_typed_equal_to_the_brightest_box_is_a_start_given(self):
        s = self.step('typed_box')
        self.assertIn('version=2022', s['ades'], (self.box, s['status'], s['text'][-400:]))


class F10_4_TheWords(unittest.TestCase):
    def test_each_face_says_what_the_checks_measure_and_whose_the_comet_is(self):
        faces = {'README.md': open(os.path.join(ROOT, 'README.md'), encoding='utf-8').read(),
                 'CHANGELOG.md': open(os.path.join(ROOT, 'CHANGELOG.md'), encoding='utf-8').read(),
                 'the page': open(os.path.join(ROOT, 'page', 'index.html'), encoding='utf-8').read(),
                 '--help': subprocess.run([sys.executable, '-m', 'domino_calibrator.cli', '--help'], cwd=ROOT, capture_output=True,
                                          encoding='utf-8').stdout}
        for face, t in faces.items():
            t = re.sub(r'\s+', ' ', t)
            with self.subTest(face):
                self.assertNotIn('only when it has measured a comet', t)
                self.assertIn('telling a comet from a star is yours', t)
                self.assertRegex(t, r'only from a start you give')
                self.assertIn('more than one pixel', t)


if __name__ == '__main__':
    unittest.main()
