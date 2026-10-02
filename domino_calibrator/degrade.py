"""A sharp image degraded to a ground telescope: seeing, then ground pixels, then noise.

Input: a fine, square, north-up grid (scale s arcsec/px) with a reference point at a known fine-pixel position.
seeing: Gaussian (erf-integrated on the fine grid) or Moffat (2x2-sampled), FWHM in arcsec, convolved by FFT.
ground pixels: blocks of n x n fine pixels, n = ground_scale / s exactly (an integer), starting at the fine
offset `phase` = (ox, oy), 0 <= ox, oy < n. A fine coordinate x_f is ground coordinate (x_f - ox - (n-1)/2) / n.
Ground pixels touched by the input's NaN border (after convolution) are NaN; `crop` keeps the finite core.
The input's own PSF (HST's, FWHM ~0.07 arcsec) is left in: seeing FWHM 0.7 arcsec becomes ~0.703.
"""
import numpy as np
from scipy.signal import fftconvolve
from scipy.special import erf

from .synth import fwhm_to_sigma, moffat_alpha

__all__ = ['seeing_kernel', 'convolve', 'bin_phase', 'phase_offset', 'ground_factor', 'degrade', 'ground_coord']


def seeing_kernel(fwhm, s, kind='gauss', beta=2.5):
    if kind == 'gauss':
        sg = fwhm_to_sigma(fwhm) / s
        K = int(np.ceil(4 * sg)) + 1          # 4 sigma: the NaN reach stays inside the +-24" field (flux beyond: 6e-5)
        e = np.arange(-K, K + 2) - 0.5
        g = 0.5 * np.diff(erf(e / (np.sqrt(2.0) * sg)))
        k = np.outer(g, g)
    elif kind == 'moffat':
        al = moffat_alpha(fwhm, beta) / s
        K = int(np.ceil(5.0 * fwhm / s)) + 1
        yy, xx = np.mgrid[-K:K + 1, -K:K + 1].astype(float)
        k = np.zeros_like(xx)
        for dy in (-0.25, 0.25):
            for dx in (-0.25, 0.25):
                k += (1.0 + ((xx + dx) ** 2 + (yy + dy) ** 2) / al ** 2) ** (-beta)
    else:
        raise ValueError(kind)
    return k / k.sum()


def ground_coord(x_f, ox, n):
    return (x_f - ox - (n - 1) / 2.0) / n


def convolve(img, s, fwhm, kind='gauss', beta=2.5):
    """Seeing on the fine grid; NaN input pixels are missing, and every output pixel within the kernel's reach
    of one is NaN."""
    bad = ~np.isfinite(img)
    a = np.where(bad, 0.0, img)
    k = seeing_kernel(fwhm, s, kind, beta) if fwhm > 0 else np.ones((1, 1))
    conv = fftconvolve(a, k, mode='same')
    if bad.any():
        reach = fftconvolve(bad.astype(float), np.ones_like(k), mode='same') > 0.5
        conv[reach] = np.nan
    return conv


def bin_phase(conv, ref, n, phase=(0, 0)):
    """Blocks of n x n fine pixels from fine offset `phase`. Returns (ground image, (xg, yg) of ref)."""
    ox, oy = int(phase[0]), int(phase[1])
    ny, nx = conv.shape
    NX, NY = (nx - ox) // n, (ny - oy) // n
    g = conv[oy:oy + NY * n, ox:ox + NX * n].reshape(NY, n, NX, n).sum(axis=(1, 3))
    return g, (ground_coord(ref[0], ox, n), ground_coord(ref[1], oy, n))


def phase_offset(x_f, n, want):
    """The fine offset o in [0, n) that puts fine coordinate x_f at ground phase ~want (in [-0.5, 0.5)); returns
    (o, achieved phase)."""
    best = None
    for o in range(n):
        g = ground_coord(x_f, o, n)
        ph = g - np.round(g)
        d = abs(ph - want)
        if best is None or d < best[0]:
            best = (d, o, ph)
    return best[1], float(best[2])


def ground_factor(ground_scale, s):
    n = int(round(ground_scale / s))
    if abs(n * s - ground_scale) > 1e-9 * max(1.0, ground_scale):
        raise ValueError('ground scale %.4f is not an integer multiple of %.4f' % (ground_scale, s))
    return n


def degrade(img, ref, s, fwhm, ground_scale, phase=(0, 0), kind='gauss', beta=2.5):
    """Returns (ground image, (xg, yg) of the reference, n)."""
    n = ground_factor(ground_scale, s)
    g, r = bin_phase(convolve(img, s, fwhm, kind, beta), ref, n, phase)
    return g, r, n
