"""The sky map, the resampler and the degrader on synthetic inputs with a known answer."""
import unittest, warnings
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS
from scipy.special import erf

from domino_calibrator.hst import SkyMap, resample, GridMap, resample_grid
from domino_calibrator.degrade import degrade, ground_coord, seeing_kernel
from domino_calibrator.apertures import circle_moments


def skew_wcs(n=801):
    h = fits.Header()
    h['NAXIS'] = 2; h['NAXIS1'] = n; h['NAXIS2'] = n
    h['CTYPE1'] = 'RA---TAN'; h['CTYPE2'] = 'DEC--TAN'
    h['CRPIX1'] = 401.0; h['CRPIX2'] = 401.0; h['CRVAL1'] = 168.7; h['CRVAL2'] = 4.6
    # UVIS-like: 0.0396 arcsec px, rotated, 3.8 deg skew, parity as the frames (det < 0)
    J = np.array([[0.037438, 0.015382], [0.012848, -0.036638]]) / 3600.0   # (xi, eta) per (x, y)
    h['CD1_1'] = J[0, 0]; h['CD1_2'] = J[0, 1]; h['CD2_1'] = J[1, 0]; h['CD2_2'] = J[1, 1]
    # FITS TAN: the CD matrix gives tangent-plane degrees (xi = dRA cos dec at the reference), no cos(dec) factor.
    # (T run 4, 18:15 UTC: the first version divided CD1_x by cos(dec); the code read back 1/cos(4.6 deg) = 1.00323.)
    with warnings.catch_warnings():
        warnings.simplefilter('ignore')
        return WCS(h), J * 3600.0


def pig(n, x0, y0, s, amp):
    e = np.arange(n + 1) - 0.5
    return amp * np.outer(0.5 * np.diff(erf((e - y0) / (np.sqrt(2) * s))), 0.5 * np.diff(erf((e - x0) / (np.sqrt(2) * s))))


class TestHstDegrade(unittest.TestCase):
    def test_skymap_linear(self):
        w, J = skew_wcs()
        sm = SkyMap(w, 400.0, 400.0, 0, 0, 380)
        self.assertLess(sm.resid, 1e-3)
        np.testing.assert_allclose(sm.J, J, rtol=2e-4)
        self.assertAlmostEqual(float(sm.area_factor(np.array([0.0]), np.array([0.0]))[0]), 1 / abs(np.linalg.det(J)), delta=1e-3 / abs(np.linalg.det(J)))
        # a sky offset of (+1, +2) arcsec lands where J predicts
        x, y = sm.to_cut(np.array([1.0]), np.array([2.0]))
        d = np.linalg.solve(J, [1.0, 2.0])
        self.assertAlmostEqual(float(x[0]), 400 + d[0], delta=0.01); self.assertAlmostEqual(float(y[0]), 400 + d[1], delta=0.01)

    def test_resample_blob(self):
        w, J = skew_wcs()
        det_off = np.linalg.solve(J, [-3.0, 5.0])        # a blob 3" west, 5" north of the reference
        img = pig(801, 400 + det_off[0], 400 + det_off[1], 2.0, 1e6)
        sm = SkyMap(w, 400.0, 400.0, 0, 0, 380)
        sky, (m, _) = resample(img, sm, 0.02, 10.0)
        yy, xx = np.indices(sky.shape)
        good = np.isfinite(sky)
        tot = sky[good].sum()
        cx = (sky[good] * xx[good]).sum() / tot; cy = (sky[good] * yy[good]).sum() / tot
        self.assertAlmostEqual((cx - m) * 0.02, +3.0, delta=2e-3)   # west = +column
        self.assertAlmostEqual((cy - m) * 0.02, +5.0, delta=2e-3)
        self.assertLess(abs(tot / 1e6 - 1), 2e-3)                  # flux conserved

    def test_gridmap(self):
        w, J = skew_wcs()
        g = GridMap(w, 400.0, 400.0, 0, 0, 0.02, 10.0, step=10)
        self.assertLess(g.check(), 1e-3)
        X, Y, A = g.maps()
        self.assertAlmostEqual(float(X[g.m, g.m]), 400.0, delta=1e-6); self.assertAlmostEqual(float(Y[g.m, g.m]), 400.0, delta=1e-6)
        self.assertLess(abs(float(A[g.m, g.m]) / (0.02 ** 2 / abs(np.linalg.det(J))) - 1), 1e-4)
        det_off = np.linalg.solve(J, [-3.0, 5.0])
        img = pig(801, 400 + det_off[0], 400 + det_off[1], 2.0, 1e6)
        sky, (m, _) = resample_grid(img, g)
        yy, xx = np.indices(sky.shape); good = np.isfinite(sky); tot = sky[good].sum()
        self.assertAlmostEqual(((sky[good] * xx[good]).sum() / tot - m) * 0.02, 3.0, delta=2e-3)
        self.assertAlmostEqual(((sky[good] * yy[good]).sum() / tot - m) * 0.02, 5.0, delta=2e-3)
        self.assertLess(abs(tot / 1e6 - 1), 2e-3)

    def test_degrade_bookkeeping(self):
        s, G = 0.02, 1.0
        img = np.zeros((501, 501)); img[250, 250] = 1.0e5          # a delta at the reference
        for ph in [(0, 0), (13, 37), (49, 1)]:
            g, (xg, yg), n = degrade(img, (250.0, 250.0), s, 0.0, G, phase=ph)
            self.assertEqual(n, 50)
            iy, ix = np.unravel_index(np.argmax(g), g.shape)
            self.assertLessEqual(abs(ix - xg), 0.5 + 1e-9); self.assertLessEqual(abs(iy - yg), 0.5 + 1e-9)
            self.assertAlmostEqual(g.sum(), 1e5, delta=1e-6)
        # with seeing: the ground image's centroid is the reference, flux conserved
        g, (xg, yg), n = degrade(img, (250.0, 250.0), s, 1.5, G, phase=(7, 21))
        sl, A, Mx, My = circle_moments(xg, yg, 4.0, g.shape)
        F = (g[sl] * A).sum()
        self.assertLess(abs((g[sl] * Mx).sum() / F - xg), 1e-3); self.assertLess(abs((g[sl] * My).sum() / F - yg), 1e-3)
        self.assertLess(abs(g.sum() / 1e5 - 1), 1e-9)

    def test_kernels(self):
        for kind in ('gauss', 'moffat'):
            k = seeing_kernel(1.0, 0.02, kind)
            self.assertAlmostEqual(k.sum(), 1.0, places=12)
            c = k.shape[0] // 2
            half = k[c, c] / 2
            prof = k[c, c:]
            i = np.argmax(prof < half)
            fwhm = 2 * (i - 1 + (prof[i - 1] - half) / (prof[i - 1] - prof[i])) * 0.02
            self.assertAlmostEqual(fwhm, 1.0, delta=0.02, msg=kind)


if __name__ == '__main__':
    unittest.main()
