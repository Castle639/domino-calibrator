"""The command line on a synthetic cutout with a WCS: runs end to end and its ADES record matches its own numbers."""
import os, tempfile, unittest, io, contextlib
import numpy as np
from astropy.io import fits

from domino_calibrator import synth
from domino_calibrator.cli import measure_file, main
from domino_calibrator.ades import pixel_to_radec
from tests.test_hardening import start


def cutout_with_wcs(path):
    img, (xt, yt) = synth.render(71, 35.05, 34.95, flux_n=2e4, k=500.0, a=0.2, model='dipole', psf=('gauss', 3.0), sub=10)
    img = img + 100.0
    h = fits.Header()
    h['CTYPE1'] = 'RA---TAN'; h['CTYPE2'] = 'DEC--TAN'; h['CRPIX1'] = 36.0; h['CRPIX2'] = 36.0
    h['CRVAL1'] = 168.7; h['CRVAL2'] = 4.6; h['CD1_1'] = -1.0 / 3600; h['CD1_2'] = 0.0; h['CD2_1'] = 0.0; h['CD2_2'] = 1.0 / 3600
    h['DATE-OBS'] = '2025-12-12T21:20:32.000'; h['EXPTIME'] = 60.0
    fits.PrimaryHDU(img.astype(np.float32), header=h).writeto(path, overwrite=True)
    return xt, yt


class TestCLI(unittest.TestCase):
    def test_end_to_end(self):
        with tempfile.TemporaryDirectory() as d:
            p = os.path.join(d, 'c.fits')
            xt, yt = cutout_with_wcs(p)
            # the hardening round: nothing defaults in the record, so the test gives its values (the bar's named change)
            r = measure_file(p, *start(p), estimator='G', ades=dict(stn='XXX', desig='3I', mode='CCD', ast_cat='Gaia3', submitter='A. N. Observer',
                                                         measurers=['A. N. Observer'], design='Reflector', aperture='0.5', detector='CCD'))
            self.assertEqual(r['curve']['nbad'], 0)
            self.assertIn('ades', r)
            ra, dec = pixel_to_radec(fits.getheader(p), r['x0'], r['y0'])
            self.assertAlmostEqual(ra, r['radec'][0], places=9); self.assertAlmostEqual(dec, r['radec'][1], places=9)
            row = r['ades'].strip().split('\n')[-1].split('|')
            self.assertAlmostEqual(float(row[4]), ra, places=6); self.assertAlmostEqual(float(row[5]), dec, places=6)
            self.assertIn('2025-12-12T21:21:02.00Z', r['ades'])
            # the zero-aperture position sits between the nucleus and the r = 2 photocentre, along +x (the bright side)
            self.assertLess(abs(r['y0'] - yt), 0.02)
            self.assertLess(r['x0'] - xt, r['x2'] - xt)
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf):
                self.assertEqual(main([p, '--estimator', 'M']), 0)
            self.assertIn('# zero aperture:', buf.getvalue())


if __name__ == '__main__':
    unittest.main()
