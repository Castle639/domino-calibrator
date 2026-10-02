"""The page's engine (page/zeroap.js, through Node) against the Python package on the same cutouts."""
import os, json, shutil, subprocess, tempfile, unittest
import numpy as np
from astropy.io import fits

from domino_calibrator import synth, shrink
from domino_calibrator.ades import pixel_to_radec

PAGE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'page')
NODE = shutil.which('node') or ('/opt/node22/bin/node' if os.path.exists('/opt/node22/bin/node') else None)


def write_cutout(path, sip=False):
    img, (xt, yt) = synth.render(71, 35.25, 34.85, flux_n=3e4, k=400.0, a=0.3, model='dipole', psf=('gauss', 2.5), sub=10)
    rng = np.random.default_rng(5)
    img = synth.add_noise(img, 150.0, 5.0, rng)
    h = fits.Header()
    h['CTYPE1'] = 'RA---TAN-SIP' if sip else 'RA---TAN'; h['CTYPE2'] = 'DEC--TAN-SIP' if sip else 'DEC--TAN'
    h['CRPIX1'] = 30.5; h['CRPIX2'] = 40.25; h['CRVAL1'] = 168.7; h['CRVAL2'] = 4.6
    h['CD1_1'] = -2.1e-4; h['CD1_2'] = 1.5e-5; h['CD2_1'] = 1.2e-5; h['CD2_2'] = 2.08e-4
    if sip:
        h['A_ORDER'] = 2; h['B_ORDER'] = 2; h['A_2_0'] = 3e-5; h['A_0_2'] = -2e-5; h['A_1_1'] = 1e-5; h['B_2_0'] = -1e-5; h['B_1_1'] = 2e-5; h['B_0_2'] = 4e-5
    h['DATE-OBS'] = '2025-12-27T16:04:29.000'; h['EXPTIME'] = 120.0
    fits.PrimaryHDU(img.astype(np.float32), header=h).writeto(path, overwrite=True)
    return img.astype(np.float32).astype(np.float64)


@unittest.skipIf(NODE is None, 'no node')
class TestPage(unittest.TestCase):
    def test_js_matches_python(self):
        with tempfile.TemporaryDirectory() as d:
            for sip in (False, True):
                p = os.path.join(d, 'c%d.fits' % sip)
                img = write_cutout(p, sip)
                for est in ('G', 'M'):
                    r = subprocess.run([NODE, os.path.join(PAGE, 'run_node.js'), p, est, '35', '35'], capture_output=True, text=True, encoding='utf-8', errors='replace', check=True)
                    js = json.loads(r.stdout)
                    py = shrink(img, 35.0, 35.0, estimator=est)
                    self.assertEqual(js['nbad'], py['nbad'])
                    tol = 1e-5 if est == 'G' else 1e-7
                    self.assertLess(np.nanmax(np.abs(np.array(js['x']) - py['x'])), tol, (sip, est))
                    self.assertLess(np.nanmax(np.abs(np.array(js['y']) - py['y'])), tol, (sip, est))
                    self.assertLess(abs(js['x0'] - py['x0']), tol); self.assertLess(abs(js['y0'] - py['y0']), tol)
                    ra, dec = pixel_to_radec(fits.getheader(p), py['x0'], py['y0'])
                    self.assertLess(abs(js['radec'][0] - ra) * 3600 * np.cos(np.radians(dec)), 1e-4)   # arcsec
                    self.assertLess(abs(js['radec'][1] - dec) * 3600, 1e-4)
                    self.assertEqual(js['time'], '2025-12-27T16:05:29.00Z')


if __name__ == '__main__':
    unittest.main()
