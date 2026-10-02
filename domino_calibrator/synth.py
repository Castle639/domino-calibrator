"""Synthetic comets with a known nucleus: a point nucleus plus a coma I = k/rho (1 + a(rho) cos(theta - theta_a)),
seen through seeing and pixels, with Poisson, sky and read noise.

The 1/rho and cos(theta)/rho parts are integrated exactly over every sub-pixel box by their cumulative
integrals from the nucleus (signed, so any box is four corner values):
    int_0^x int_0^y 1/rho          = sgn(x) sgn(y) [ |x| asinh(|y|/|x|) + |y| asinh(|x|/|y|) ]
    int_0^x int_0^y u/(u^2 + v^2)  = sgn(y) [ |x| atan(|y|/|x|) + (|y|/2) ln(1 + x^2/y^2) ]
The nucleus is snapped to a sub-pixel centre, so the cusp's discretisation is symmetric about the truth.
Seeing (Gaussian or Moffat) is convolved on the sub-grid, then the sub-grid is binned to detector pixels.
The 'grow' profile a(rho) = a_max rho / (rho + rho_s) has no closed form; its cos part is sampled q x q per
sub-pixel (a bounded integrand; with an even q the sampling is symmetric about the nucleus). 'fade',
a(rho) = a_max rho_s / (rho + rho_s) (asymmetric near the nucleus, round far out), is the exact dipole minus
the grow term.
Units: detector pixels; image values are expected electrons.
"""
import numpy as np
from scipy.signal import fftconvolve
from scipy.special import erf

from .apertures import circle_moments

__all__ = ['C_sym', 'C_cos', 'C_sin', 'box_integrals', 'psf_kernel', 'render', 'add_noise', 'snr_scale',
           'fwhm_to_sigma', 'moffat_alpha']

K2F = 2.0 * np.sqrt(2.0 * np.log(2.0))


def fwhm_to_sigma(fwhm):
    return fwhm / K2F


def moffat_alpha(fwhm, beta):
    return fwhm / (2.0 * np.sqrt(2.0 ** (1.0 / beta) - 1.0))


def _G(a, b):
    """int_0^a int_0^b 1/rho for a, b >= 0."""
    a = np.asarray(a, float); b = np.asarray(b, float)
    out = np.zeros(np.broadcast(a, b).shape)
    pa, pb = a > 0, b > 0
    both = pa & pb
    A, B = np.broadcast_to(a, out.shape), np.broadcast_to(b, out.shape)
    out[both] = A[both] * np.arcsinh(B[both] / A[both]) + B[both] * np.arcsinh(A[both] / B[both])
    return out


def _H(x, y):
    """int_0^x int_0^y u / (u^2 + v^2) dv du for x, y >= 0."""
    x = np.asarray(x, float); y = np.asarray(y, float)
    out = np.zeros(np.broadcast(x, y).shape)
    X, Y = np.broadcast_to(x, out.shape), np.broadcast_to(y, out.shape)
    both = (X > 0) & (Y > 0)
    out[both] = X[both] * np.arctan(Y[both] / X[both]) + 0.5 * Y[both] * np.log1p((X[both] / Y[both]) ** 2)
    return out


def C_sym(x, y):
    return np.sign(x) * np.sign(y) * _G(np.abs(x), np.abs(y))


def C_cos(x, y):
    return np.sign(y) * _H(np.abs(x), np.abs(y))


def C_sin(x, y):
    return np.sign(x) * _H(np.abs(y), np.abs(x))


def box_integrals(C, xe, ye):
    """Integrals over the boxes [xe_j, xe_j+1] x [ye_i, ye_i+1] from a cumulative C (edges relative to the
    nucleus). Returns an array (len(ye)-1, len(xe)-1)."""
    X, Y = np.meshgrid(np.asarray(xe, float), np.asarray(ye, float))
    Cv = C(X, Y)
    return Cv[1:, 1:] - Cv[1:, :-1] - Cv[:-1, 1:] + Cv[:-1, :-1]


def psf_kernel(psf, sub):
    """Sub-grid kernel (odd size, unit sum) and its half-width in detector px.
    psf = ('gauss', fwhm) or ('moffat', fwhm, beta), fwhm in detector px."""
    kind = psf[0]
    if kind == 'gauss':
        s = fwhm_to_sigma(psf[1]) * sub
        K = int(np.ceil(6.0 * s)) + 1
        e = np.arange(-K, K + 2) - 0.5
        g = 0.5 * np.diff(erf(e / (np.sqrt(2.0) * s)))
        k = np.outer(g, g)
        half_px = (K + 1) / sub
    elif kind == 'array':
        k = np.asarray(psf[1], float)
        if k.shape[0] % 2 == 0 or k.shape[0] != k.shape[1]:
            raise ValueError('array PSF must be square with odd size')
        half_px = (k.shape[0] // 2 + 1) / sub
        return k / k.sum(), half_px
    elif kind == 'moffat':
        fwhm, beta = psf[1], psf[2]
        al = moffat_alpha(fwhm, beta) * sub
        K = int(np.ceil(5.0 * fwhm * sub)) + 1
        o = (np.arange(2) + 0.5) / 2 - 0.5
        yy, xx = np.mgrid[-K:K + 1, -K:K + 1].astype(float)
        k = np.zeros_like(xx)
        for dy in o:
            for dx in o:
                k += (1.0 + ((xx + dx) ** 2 + (yy + dy) ** 2) / al ** 2) ** (-beta)
        half_px = (K + 1) / sub
    else:
        raise ValueError(kind)
    return k / k.sum(), half_px


def render(n, xn, yn, flux_n=0.0, k=1.0, a=0.0, theta=0.0, model='dipole', rho_s=None, psf=('gauss', 2.0),
           sub=10, q=4, snap=True, post=()):
    """Noiseless image, n x n detector px, of the nucleus (flux_n) plus the coma. Returns (img, (xt, yt)):
    (xt, yt) is the true nucleus position after snapping to a sub-pixel centre.
    model 'dipole': a(rho) = a (scale-free); 'grow': a(rho) = a rho / (rho + rho_s); 'none': no coma.
    psf None: no seeing (then sub may be 1 and snap False: the pixel integrals are exact anywhere).
    psf ('array', K): K is an odd, square kernel sampled on the sub-grid (e.g. TinyTim's SUB=sub optical PSF);
    post: 3x3 kernels correlated after binning (TinyTim's weighted_kernel, kernel_xy: its own path)."""
    if psf is None:
        ker, pad = None, 1
    else:
        ker, half = psf_kernel(psf, sub)
        pad = int(np.ceil(half)) + 2
    N = n + 2 * pad
    edges = -pad - 0.5 + np.arange(N * sub + 1) / sub
    if snap:
        cen = 0.5 * (edges[1:] + edges[:-1])
        xt = float(cen[np.argmin(np.abs(cen - xn))]); yt = float(cen[np.argmin(np.abs(cen - yn))])
    else:
        xt, yt = float(xn), float(yn)
    xe, ye = edges - xt, edges - yt
    S = np.zeros((N * sub, N * sub))
    if model != 'none' and k != 0:
        S += k * box_integrals(C_sym, xe, ye)
        if model in ('dipole', 'fade') and a != 0:
            S += k * a * (np.cos(theta) * box_integrals(C_cos, xe, ye) + np.sin(theta) * box_integrals(C_sin, xe, ye))
        if model in ('grow', 'fade') and a != 0:
            # grow: + a cos/(rho + rho_s); fade = a rho_s/(rho (rho + rho_s)) cos = dipole(a) - a cos/(rho + rho_s)
            sgn = 1.0 if model == 'grow' else -1.0
            o = ((np.arange(q) + 0.5) / q - 0.5) / sub
            cx = 0.5 * (xe[1:] + xe[:-1]); cy = 0.5 * (ye[1:] + ye[:-1])
            acc = np.zeros_like(S)
            for dy in o:
                Y = (cy + dy)[:, None]
                for dx in o:
                    X = (cx + dx)[None, :]
                    rho = np.hypot(X, Y)
                    with np.errstate(invalid='ignore', divide='ignore'):
                        c = np.where(rho > 0, (X * np.cos(theta) + Y * np.sin(theta)) / (rho * (rho + rho_s)), 0.0)
                    acc += c
            S += sgn * k * a * acc / (q * q) / (sub * sub)
    if flux_n:
        jx = int(np.argmin(np.abs(0.5 * (edges[1:] + edges[:-1]) - xt)))
        jy = int(np.argmin(np.abs(0.5 * (edges[1:] + edges[:-1]) - yt)))
        if not snap:
            raise ValueError('a nucleus needs snap=True')
        S[jy, jx] += flux_n
    if ker is not None:
        S = fftconvolve(S, ker, mode='same')
    img = S.reshape(N, sub, N, sub).sum(axis=(1, 3))
    if post:
        from scipy import ndimage
        for kk in post:
            img = ndimage.correlate(img, kk, mode='constant', cval=0.0)
    img = img[pad:pad + n, pad:pad + n]
    return img, (xt, yt)


def add_noise(img, sky, rn, rng):
    """Poisson(img + sky) + Gaussian read noise; the sky stays in the image (a real frame's background)."""
    lam = np.clip(img + sky, 0.0, None)
    return rng.poisson(lam).astype(float) + rng.normal(0.0, rn, img.shape)


def snr_scale(img1, xt, yt, fwhm, snr, sky, rn):
    """Factor s so that s * img1 has S/N = snr for the flux inside r = fwhm about the nucleus:
    s S1 / sqrt(s S1 + pi fwhm^2 (sky + rn^2)) = snr."""
    sl, A, _, _ = circle_moments(xt, yt, fwhm, img1.shape)
    S1 = float((img1[sl] * A).sum())
    Bn = np.pi * fwhm ** 2 * (sky + rn * rn)
    return (snr ** 2 * S1 + np.sqrt(snr ** 4 * S1 ** 2 + 4.0 * S1 ** 2 * snr ** 2 * Bn)) / (2.0 * S1 ** 2)
