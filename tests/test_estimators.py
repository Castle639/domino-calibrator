"""Estimators M, G, P and the shrinking-aperture sequence on sources with a known answer."""
import unittest
import numpy as np
from scipy.special import erf

from domino_calibrator.estimators import moment_centroid, gauss_fit, peak_quadratic, annulus_background
from domino_calibrator.shrink import shrink, linear_extrapolate, PUBLISHED_RADII


def pig_image(n, x0, y0, s, amp=1e5):
    e = np.arange(n + 1) - 0.5
    gx = 0.5 * np.diff(erf((e - x0) / (np.sqrt(2) * s)))
    gy = 0.5 * np.diff(erf((e - y0) / (np.sqrt(2) * s)))
    return amp * np.outer(gy, gx)


class TestEstimators(unittest.TestCase):
    def test_moment_symmetric_source(self):
        img = pig_image(61, 30.3, 29.7, 1.5)
        o = moment_centroid(img, 30.0, 30.0, 6.0)
        self.assertTrue(o['ok'])
        self.assertLess(np.hypot(o['x'] - 30.3, o['y'] - 29.7), 2e-3)

    def test_moment_background_invariance(self):
        img = pig_image(61, 30.3, 29.7, 2.0)
        a = moment_centroid(img, 29.0, 31.0, 4.0, bkg=0.0)
        b = moment_centroid(img + 1000.0, 29.0, 31.0, 4.0, bkg=0.0)
        c = moment_centroid(img + 1000.0, 29.0, 31.0, 4.0, bkg=400.0)
        for o in (a, b, c):
            self.assertTrue(o['ok'])
        self.assertLess(np.hypot(a['x'] - b['x'], a['y'] - b['y']), 1e-5)
        self.assertLess(np.hypot(a['x'] - c['x'], a['y'] - c['y']), 1e-5)

    def test_gauss_fit_exact(self):
        img = pig_image(61, 30.3, 29.7, 1.8)
        o = gauss_fit(img, 30.0, 30.0, 5.0, bkg=0.0)
        self.assertTrue(o['ok'])
        self.assertLess(np.hypot(o['x'] - 30.3, o['y'] - 29.7), 1e-5)
        self.assertAlmostEqual(o['s'], 1.8, delta=1e-5)

    def test_gauss_fit_with_background(self):
        img = pig_image(81, 40.2, 39.6, 1.5) + 250.0
        b = annulus_background(img, 40.0, 40.0, 4.0)
        self.assertAlmostEqual(b, 250.0, delta=0.5)
        o = gauss_fit(img, 40.0, 40.0, 4.0, bkg=250.0)
        self.assertLess(np.hypot(o['x'] - 40.2, o['y'] - 39.6), 1e-5)

    def test_peak_quadratic(self):
        img = pig_image(31, 15.0, 15.0, 1.5)
        o = peak_quadratic(img, 15, 15)
        self.assertTrue(o['ok'])
        self.assertLess(np.hypot(o['x'] - 15.0, o['y'] - 15.0), 1e-9)
        img = pig_image(31, 15.3, 14.8, 1.5)
        o = peak_quadratic(img, 15, 15)
        self.assertTrue(o['ok'])
        self.assertLess(np.hypot(o['x'] - 15.3, o['y'] - 14.8), 0.1)   # a 3x3 quadratic is not exact off-centre

    def test_linear_extrapolate(self):
        r = PUBLISHED_RADII
        self.assertEqual(len(r), 41)
        self.assertAlmostEqual(r[0], 2.0); self.assertAlmostEqual(r[-1], 6.0)
        v0, s = linear_extrapolate(r, 3.0 + 0.25 * r)
        self.assertAlmostEqual(v0, 3.0, places=12); self.assertAlmostEqual(s, 0.25, places=12)

    def test_shrink_point_source(self):
        # T run 1 (17:58 UTC): the first version asked M for 2e-3 px at phase (0.2, -0.4) and failed at 4.2e-3:
        # M's pixel-phase bias on a symmetric source is real (0.02 px at r = 2, FWHM 3.5 px; 1e-4 at r = 6).
        # Exact by symmetry at phases 0 and 1/2; G is exact at every phase. The phase bias is measured in S0.
        for (x, y) in [(40.0, 40.0), (40.5, 40.5), (40.2, 39.6)]:
            img = pig_image(81, x, y, 1.5) + 100.0
            for est in ('M', 'G'):
                o = shrink(img, 40.0, 40.0, estimator=est)
                self.assertEqual(o['nbad'], 0)
                sym = est == 'G' or (x, y) != (40.2, 39.6)
                tol = 1e-7 if sym else 1e-2
                self.assertLess(np.hypot(o['x0'] - x, o['y0'] - y), tol, (est, x, y))
                self.assertLess(np.hypot(o['x2'] - x, o['y2'] - y), 1e-7 if sym else 3e-2, (est, x, y))


class TestRobust(unittest.TestCase):
    def test_leaving_the_image_is_unconverged_not_a_crash(self):
        # S1 run 1 (19:10 UTC) died when one noisy realisation's M iteration left a 71-px image
        rng = np.random.default_rng(0)
        img = rng.normal(100.0, 10.0, (41, 41))                    # pure noise: nothing to converge on
        img[20, 38] += 5000.0                                       # a hot pixel near the edge pulls the aperture out
        for est in ('M', 'G'):
            o = shrink(img, 20.0, 20.0, estimator=est)
            self.assertTrue(o['nbad'] >= 0)                          # returns, whatever it found
        o = moment_centroid(img, 38.5, 20.0, 6.0, bkg=100.0)
        self.assertFalse(o['ok'])

    def test_unconverged_radius_reports_nan(self):
        # H3 post hoc (20:25 UTC): x2 was the runaway position of an unconverged r = 2 fit
        rng = np.random.default_rng(0)
        img = rng.normal(100.0, 10.0, (41, 41)); img[20, 38] += 5000.0
        for est in ('M', 'G'):
            o = shrink(img, 20.0, 20.0, estimator=est)
            i2 = int(np.argmin(np.abs(o['radii'] - 2.0)))
            if not o['ok'][i2]:
                self.assertTrue(np.isnan(o['x2']) and np.isnan(o['y2']))
            else:
                self.assertTrue(np.isfinite(o['x2']))

    def test_nan_outside_the_circle_is_not_data(self):
        # H1 run 1 (19:17 UTC): NaN in the aperture's bounding-box corners (outside the circle) made M unconverged
        img = pig_image(41, 20.2, 19.7, 1.5)
        a = moment_centroid(img, 20.0, 20.0, 5.9)
        img2 = img.copy(); img2[14, 14] = np.nan; img2[26, 26] = np.nan   # corners of the r = 5.9 box, outside the circle
        b = moment_centroid(img2, 20.0, 20.0, 5.9)
        self.assertTrue(b['ok'])
        self.assertLess(np.hypot(a['x'] - b['x'], a['y'] - b['y']), 1e-9)


if __name__ == '__main__':
    unittest.main()
