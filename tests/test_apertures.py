"""Exact apertures: area and moments against geometry and against brute-force sampling."""
import unittest
import numpy as np

from domino_calibrator.apertures import pixel_overlap, circle_moments


def brute(a0, a1, b0, b1, r, n=600):
    """Midpoint sampling of one box, n x n points: (A, Mu, Mv)."""
    u = a0 + (np.arange(n) + 0.5) / n * (a1 - a0)
    v = b0 + (np.arange(n) + 0.5) / n * (b1 - b0)
    U, V = np.meshgrid(u, v)
    ins = (U * U + V * V) <= r * r
    dA = (a1 - a0) * (b1 - b0) / n / n
    return ins.sum() * dA, (U * ins).sum() * dA, (V * ins).sum() * dA


class TestApertures(unittest.TestCase):
    def test_full_circle_area_and_moments(self):
        for (xc, yc, r) in [(10.3, 11.8, 3.7), (15.0, 15.0, 2.0), (14.51, 13.49, 6.0), (20.25, 20.75, 0.3)]:
            sl, A, Mx, My = circle_moments(xc, yc, r, (40, 40))
            self.assertAlmostEqual(A.sum(), np.pi * r * r, delta=1e-10 * max(1, r * r))
            self.assertAlmostEqual(Mx.sum(), xc * np.pi * r * r, delta=1e-9 * max(1, r * r * xc))
            self.assertAlmostEqual(My.sum(), yc * np.pi * r * r, delta=1e-9 * max(1, r * r * yc))
            self.assertTrue(np.all(A >= -1e-15) and np.all(A <= 1 + 1e-12))

    def test_against_brute_force(self):
        rng = np.random.default_rng(3)
        r = 2.37
        worst = 0.0
        for _ in range(40):
            a0 = rng.uniform(-3.5, 2.5); b0 = rng.uniform(-3.5, 2.5)
            A, Mu, Mv = pixel_overlap(np.array([a0]), np.array([a0 + 1]), np.array([b0]), np.array([b0 + 1]), r)
            Ab, Mub, Mvb = brute(a0, a0 + 1, b0, b0 + 1, r)
            worst = max(worst, abs(A[0] - Ab), abs(Mu[0] - Mub), abs(Mv[0] - Mvb))
        self.assertLess(worst, 5e-3)   # the brute force's own error at n = 600 is ~1/n of the edge length

    def test_quarter_circles(self):
        r = 0.5
        A, Mu, Mv = pixel_overlap(np.array([0.0, -1.0, 0.0, -1.0]), np.array([1.0, 0.0, 1.0, 0.0]),
                                  np.array([0.0, 0.0, -1.0, -1.0]), np.array([1.0, 1.0, 0.0, 0.0]), r)
        np.testing.assert_allclose(A, np.pi * r * r / 4, atol=1e-14)
        c = 4 * r / (3 * np.pi) * np.pi * r * r / 4   # centroid of a quarter disk times its area
        np.testing.assert_allclose(np.abs(Mu), c, atol=1e-14)
        np.testing.assert_allclose(np.abs(Mv), c, atol=1e-14)

    def test_outside_and_leaving(self):
        A, Mu, Mv = pixel_overlap(np.array([5.0]), np.array([6.0]), np.array([0.0]), np.array([1.0]), 2.0)
        self.assertEqual(A[0], 0.0)
        with self.assertRaises(ValueError):
            circle_moments(2.0, 2.0, 3.0, (20, 20))


if __name__ == '__main__':
    unittest.main()
