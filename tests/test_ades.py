"""ADES record: WCS round trip and the PSV layout."""
import unittest
from astropy.io import fits

from domino_calibrator.ades import pixel_to_radec, ades_psv, mid_exposure_iso


def tan_header():
    h = fits.Header()
    h['NAXIS'] = 2; h['NAXIS1'] = 100; h['NAXIS2'] = 100
    h['CTYPE1'] = 'RA---TAN'; h['CTYPE2'] = 'DEC--TAN'
    h['CRPIX1'] = 51.0; h['CRPIX2'] = 51.0            # FITS 1-based: 0-based pixel (50, 50)
    h['CRVAL1'] = 168.7; h['CRVAL2'] = 4.6
    h['CD1_1'] = -1.0 / 3600; h['CD1_2'] = 0.0; h['CD2_1'] = 0.0; h['CD2_2'] = 1.0 / 3600
    h['DATE-OBS'] = '2025-12-12T21:20:32.000'; h['EXPTIME'] = 170.0
    return h


class TestADES(unittest.TestCase):
    def test_wcs_origin(self):
        ra, dec = pixel_to_radec(tan_header(), 50.0, 50.0)
        self.assertAlmostEqual(ra, 168.7, places=10); self.assertAlmostEqual(dec, 4.6, places=10)
        ra2, dec2 = pixel_to_radec(tan_header(), 51.0, 50.0)   # +x is west here (CD1_1 < 0)
        self.assertLess(ra2, ra)

    def test_mid_exposure(self):
        self.assertEqual(mid_exposure_iso(tan_header()), '2025-12-12T21:21:57.00Z')

    def test_psv(self):
        # the hardening round (the hardening round's record of 27 Sept 2026, not in this repository): the record takes the user's values (#13)
        # and is version 2022, the only one submit.xsd accepts (#12); these two lines are the bar's named change
        t = ades_psv(168.7, 4.6, '2025-12-12T21:21:57.00Z', 'XXX', desig='3I', mode='CCD', ast_cat='Gaia3', submitter='A. N. Observer',
                     measurers=['A. N. Observer'], design='Reflector', aperture='0.5', detector='CCD', rms_ra=0.3, rms_dec=0.3)
        lines = t.strip().split('\n')
        self.assertEqual(lines[0], '# version=2022')
        self.assertIn('! mpcCode XXX', lines)
        head, row = lines[-2], lines[-1]
        names = [s.strip() for s in head.split('|')]
        vals = [s.strip() for s in row.split('|')]
        self.assertEqual(names, ['permID', 'mode', 'stn', 'obsTime', 'ra', 'dec', 'rmsRA', 'rmsDec', 'astCat', 'remarks'])
        d = dict(zip(names, vals))
        self.assertEqual(d['ra'], '168.700000'); self.assertEqual(d['dec'], '+4.600000')   # rms 0.30": ADES's DP is 6 (the fix
                                                                                       # room's F1, item 3)
        self.assertEqual(d['permID'], '3I'); self.assertEqual(d['mode'], 'CCD')


if __name__ == '__main__':
    unittest.main()
