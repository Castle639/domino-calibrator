"""The release's refuter pass (the refuters' third record of 28 Sept 2026, not in this repository), the page's share: D1.2 (class 1) in a headless
browser (page/browser_cases.js). The page said "at r = 2" and "The r = 2 photocentre sits ... of it" of the photocentre at
the radius nearest 2 px, whatever its radii boxes said. Written to fail on the calibrator as the seventh room left it
(0e311b5) and to pass once the fix is in; every case is a subTest, and the control passes before and after.
"""
import os, json, shutil, tempfile, unittest, warnings, subprocess
import numpy as np

from tests.test_hardening_page import fits_bytes, PAGE, NODE, PW, REC_PAGE
from tests.test_hardening_2_page import TAN
from tests.test_hardening import REC

REC4 = dict(REC_PAGE, measurers='; '.join(REC['measurers']))


@unittest.skipIf(NODE is None or PW is None, 'no node or playwright')
class TestD12ThePageNamesTheRadius(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore')
        cls.d = tempfile.mkdtemp()
        from domino_calibrator import synth
        img, _ = synth.render(71, 35.25, 34.85, flux_n=3e4, k=400.0, a=0.3, model='dipole', psf=('gauss', 2.5), sub=10)
        img = synth.add_noise(img, 150.0, 5.0, np.random.default_rng(5)).astype(np.float32)
        T = {'DATE-OBS': '2025-12-27T16:04:29.000', 'EXPTIME': 120.0}
        good = fits_bytes(os.path.join(cls.d, 'good.fits'), img, **dict(TAN, **T))
        first = dict(file=good, x=35, y=35, set=dict(REC4), run=True)
        cases = [dict(name='published', steps=[first]),
                 dict(name='radii3to8', steps=[dict(first, set=dict(REC4, r0='3.0', r1='8.0', rs='0.1'))]),
                 dict(name='radii205', steps=[dict(first, set=dict(REC4, r0='2.05', r1='5.95', rs='0.05'))])]
        cp = os.path.join(cls.d, 'cases.json'); json.dump(cases, open(cp, 'w', encoding='utf-8'))
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

    def zero(self, name):
        self.assertIsNotNone(self.res, 'browser_cases.js gave no result: ' + self.err)
        s = self.res[name]['steps']
        self.assertEqual(len(s), 1, self.res[name])
        return s[0]['zero']

    def test_d1_2_the_page_says_r_is_2_only_at_2(self):
        with self.subTest('control: the published radii'):
            z = self.zero('published')
            self.assertIn('at r = 2: (', z); self.assertIn('The r = 2 photocentre sits', z)
        for name, r in (('radii3to8', '3.0'), ('radii205', '2.05')):
            with self.subTest(name):                    # 0e311b5: "at r = 2: (...)" and "The r = 2 photocentre sits ..."
                z = self.zero(name)
                self.assertIn('at r = %s: (' % r, z); self.assertIn('The r = %s photocentre sits' % r, z)
                self.assertNotIn('r = 2:', z); self.assertNotIn('r = 2 photocentre', z)


if __name__ == '__main__':
    unittest.main()
