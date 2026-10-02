"""Synthetic comets: the closed-form box integrals against quadrature, and the renderer's bookkeeping."""
import unittest
import numpy as np
from scipy import integrate
from scipy.special import erf

from domino_calibrator.synth import C_sym, C_cos, C_sin, box_integrals, render, snr_scale, psf_kernel
from domino_calibrator.apertures import circle_moments


def quad_box(f, x0, x1, y0, y1):
    # split at the axes so the singular point, if inside, sits on a corner of each piece
    xs = sorted(set([x0, x1] + ([0.0] if x0 < 0 < x1 else [])))
    ys = sorted(set([y0, y1] + ([0.0] if y0 < 0 < y1 else [])))
    tot = 0.0
    for a, b in zip(xs[:-1], xs[1:]):
        for c, d in zip(ys[:-1], ys[1:]):
            tot += integrate.dblquad(lambda y, x: f(x, y), a, b, c, d, epsabs=1e-12, epsrel=1e-10)[0]
    return tot


class TestSynth(unittest.TestCase):
    def test_box_integrals_vs_quadrature(self):
        f_sym = lambda x, y: 1.0 / np.hypot(x, y)
        f_cos = lambda x, y: x / (x * x + y * y)
        f_sin = lambda x, y: y / (x * x + y * y)
        boxes = [(0.3, 1.1, 0.2, 0.9), (-1.2, -0.4, 0.5, 2.0), (-0.5, 0.5, -0.5, 0.5), (-0.2, 0.7, -1.3, 0.4),
                 (2.0, 3.5, -4.0, -1.0), (-0.05, 0.05, 0.0, 0.1)]
        for (x0, x1, y0, y1) in boxes:
            for C, f in ((C_sym, f_sym), (C_cos, f_cos), (C_sin, f_sin)):
                got = box_integrals(C, np.array([x0, x1]), np.array([y0, y1]))[0, 0]
                want = quad_box(f, x0, x1, y0, y1)
                self.assertAlmostEqual(got, want, delta=2e-7 * max(1.0, abs(want)), msg=str((C.__name__, x0, x1, y0, y1)))

    def test_dipole_odd_symmetric_zero(self):
        e = np.linspace(-3, 3, 13)
        self.assertAlmostEqual(box_integrals(C_cos, e, e).sum(), 0.0, places=12)
        self.assertAlmostEqual(box_integrals(C_sin, e, e).sum(), 0.0, places=12)

    def test_nucleus_only_render(self):
        n, fw = 41, 3.0
        img, (xt, yt) = render(n, 20.33, 19.71, flux_n=1e5, k=0.0, model='none', psf=('gauss', fw), sub=10)
        self.assertLess(abs(img.sum() - 1e5) / 1e5, 1e-6)
        yy, xx = np.indices(img.shape)
        self.assertLess(abs((img * xx).sum() / img.sum() - xt), 1e-6)
        self.assertLess(abs((img * yy).sum() / img.sum() - yt), 1e-6)
        s = fw / 2.3548200450309493
        e = np.arange(n + 1) - 0.5
        ref = 1e5 * np.outer(0.5 * np.diff(erf((e - yt) / (np.sqrt(2) * s))), 0.5 * np.diff(erf((e - xt) / (np.sqrt(2) * s))))
        self.assertLess(np.abs(img - ref).max() / ref.max(), 2e-3)

    def test_coma_flux_no_psf(self):
        # without seeing, the flux of k/rho inside radius R about the nucleus is 2 pi k R (pixel integrals exact)
        img, (xt, yt) = render(121, 60.0, 60.0, k=1.0, model='dipole', a=0.3, psf=None, sub=1, snap=False)
        sl, A, _, _ = circle_moments(xt, yt, 40.0, img.shape)
        F = (img[sl] * A).sum()
        self.assertLess(abs(F / (2 * np.pi * 40.0) - 1), 2e-3)   # pixels uniform inside: an edge effect only

    def test_grow_and_fade_vs_quadrature(self):
        # pixel values of k/rho (1 + a(rho) cos t) without seeing, against dblquad of the same function
        n, xn, yn, a, rs = 21, 10.05, 9.95, 0.3, 2.0
        for model, af in (('grow', lambda r: a * r / (r + rs)), ('fade', lambda r: a * rs / (r + rs))):
            img, (xt, yt) = render(n, xn, yn, k=1.0, a=a, model=model, rho_s=rs, psf=None, sub=10, q=4)
            f = lambda x, y: (1 + af(np.hypot(x, y)) * x / np.hypot(x, y)) / np.hypot(x, y)
            for (i, j) in [(10, 11), (12, 9), (10, 10), (5, 15), (9, 8)]:
                want = quad_box(f, j - 0.5 - xt, j + 0.5 - xt, i - 0.5 - yt, i + 0.5 - yt)
                self.assertLess(abs(img[i, j] - want) / abs(want), 2e-3, (model, i, j, img[i, j], want))

    def test_array_psf_and_post(self):
        kg, _ = psf_kernel(('gauss', 2.0), 5)
        a, t1 = render(41, 20.2, 19.6, flux_n=1e4, k=1.0, a=0.3, model='dipole', psf=('gauss', 2.0), sub=5)
        b, t2 = render(41, 20.2, 19.6, flux_n=1e4, k=1.0, a=0.3, model='dipole', psf=('array', kg), sub=5)
        self.assertEqual(t1, t2)
        self.assertLess(np.abs(a - b).max(), 1e-9 * a.max())
        post = np.array([[0.0, 0.1, 0.0], [0.1, 0.6, 0.1], [0.0, 0.1, 0.0]])
        c, _ = render(41, 20.2, 19.6, flux_n=1e4, k=0.0, model='none', psf=('array', kg), sub=5, post=(post,))
        self.assertLess(abs(c.sum() / 1e4 - 1), 1e-6)
        yy, xx = np.indices(c.shape)
        self.assertLess(abs((c * xx).sum() / c.sum() - t1[0]), 1e-6)

    def test_moffat_kernel(self):
        k, half = psf_kernel(('moffat', 3.0, 2.5), 10)
        self.assertAlmostEqual(k.sum(), 1.0, places=12)
        self.assertEqual(k.shape[0] % 2, 1)

    def test_snr_scale(self):
        img1, (xt, yt) = render(41, 20.0, 20.0, flux_n=1.0, k=0.1, model='dipole', a=0.2, psf=('gauss', 2.0), sub=10)
        s = snr_scale(img1, xt, yt, 2.0, 50.0, 100.0, 5.0)
        sl, A, _, _ = circle_moments(xt, yt, 2.0, img1.shape)
        S = s * (img1[sl] * A).sum()
        self.assertAlmostEqual(S / np.sqrt(S + np.pi * 4.0 * (100.0 + 25.0)), 50.0, places=6)


if __name__ == '__main__':
    unittest.main()
