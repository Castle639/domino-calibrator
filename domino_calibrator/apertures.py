"""Exact overlap of a circle with square pixels: area and first moments, in closed form.

Pixel (i, j) of a numpy image covers x in [j - 0.5, j + 0.5], y in [i - 0.5, i + 0.5]: pixel centres sit
on integer coordinates, x is the column index, y the row index (0-based, as numpy; WCS calls use origin 0).

For one pixel and one circle the overlap is integrated column-wise: at abscissa u (relative to the circle
centre) the circle spans v in [-h(u), h(u)], h = sqrt(r^2 - u^2), and the pixel spans [b0, b1]. Between
the breakpoints u = +-r, +-sqrt(r^2 - b0^2), +-sqrt(r^2 - b1^2) the top of the overlap is either b1 or h and
the bottom either b0 or -h, so every piece integrates in closed form:
    int h du   = (u h + r^2 asin(u/r)) / 2
    int u h du = -h^3 / 3
    int h^2 du = r^2 u - u^3 / 3
Area A = int (top - bot) du, first moments Mu = int u (top - bot) du, Mv = int (top^2 - bot^2)/2 du.
No sub-sampling: for a constant image the aperture-weighted moment is exactly the aperture centre.
"""
import numpy as np

__all__ = ['pixel_overlap', 'circle_moments', 'annulus_mask']


def _F0(u, r):
    u = np.clip(u, -r, r)
    h = np.sqrt(np.maximum(r * r - u * u, 0.0))
    return 0.5 * (u * h + r * r * np.arcsin(u / r))


def _F1(u, r):
    u = np.clip(u, -r, r)
    h = np.sqrt(np.maximum(r * r - u * u, 0.0))
    return -h ** 3 / 3.0


def _F2(u, r):
    return r * r * u - u ** 3 / 3.0


def pixel_overlap(a0, a1, b0, b1, r):
    """Overlap of the disk u^2 + v^2 <= r^2 with the boxes [a0, a1] x [b0, b1] (arrays, same shape).
    Returns (A, Mu, Mv): area and first moments about the circle centre."""
    a0, a1, b0, b1 = (np.asarray(t, float) for t in (a0, a1, b0, b1))
    shp = a0.shape
    a0, a1, b0, b1 = a0.ravel(), a1.ravel(), b0.ravel(), b1.ravel()
    s0 = np.sqrt(np.maximum(r * r - b0 * b0, 0.0))
    s1 = np.sqrt(np.maximum(r * r - b1 * b1, 0.0))
    bp = np.stack([a0, a1, -np.full_like(a0, r), np.full_like(a0, r), -s0, s0, -s1, s1], axis=1)
    bp = np.clip(bp, a0[:, None], a1[:, None])
    bp.sort(axis=1)
    p, q = bp[:, :-1], bp[:, 1:]
    m = 0.5 * (p + q)
    inside = np.abs(m) < r
    h = np.sqrt(np.maximum(r * r - m * m, 0.0))
    B0, B1 = b0[:, None], b1[:, None]
    top_h = h < B1          # top of the overlap is the circle
    bot_h = -h > B0         # bottom of the overlap is the circle
    top = np.where(top_h, h, B1)
    bot = np.where(bot_h, -h, B0)
    valid = inside & (top > bot) & (q > p)
    F0q, F0p = _F0(q, r), _F0(p, r)
    F1q, F1p = _F1(q, r), _F1(p, r)
    F2d = _F2(q, r) - _F2(p, r)
    dq = q - p
    d2 = 0.5 * (q * q - p * p)
    # area
    A_top = np.where(top_h, F0q - F0p, B1 * dq)
    A_bot = np.where(bot_h, -(F0q - F0p), B0 * dq)
    # u-moment
    U_top = np.where(top_h, F1q - F1p, B1 * d2)
    U_bot = np.where(bot_h, -(F1q - F1p), B0 * d2)
    # v-moment: int top^2/2 - bot^2/2
    V_top = np.where(top_h, 0.5 * F2d, 0.5 * B1 * B1 * dq)
    V_bot = np.where(bot_h, 0.5 * F2d, 0.5 * B0 * B0 * dq)
    A = np.where(valid, A_top - A_bot, 0.0).sum(axis=1)
    Mu = np.where(valid, U_top - U_bot, 0.0).sum(axis=1)
    Mv = np.where(valid, V_top - V_bot, 0.0).sum(axis=1)
    return A.reshape(shp), Mu.reshape(shp), Mv.reshape(shp)


def circle_moments(xc, yc, r, shape):
    """Exact overlap of the circle (centre (xc, yc), radius r) with the pixels of an image of `shape`.
    Returns (sl, A, Mx, My): the bounding slices (rows, cols), overlap areas, and the absolute first moments
    int x dA, int y dA of each overlap region. Raises if the circle leaves the image."""
    ny, nx = shape
    j0, j1 = int(np.floor(xc - r + 0.5)), int(np.floor(xc + r + 0.5))
    i0, i1 = int(np.floor(yc - r + 0.5)), int(np.floor(yc + r + 0.5))
    if j0 < 0 or i0 < 0 or j1 > nx - 1 or i1 > ny - 1:
        raise ValueError('aperture (%.3f, %.3f, r=%.3f) leaves the image %s' % (xc, yc, r, shape))
    jj, ii = np.meshgrid(np.arange(j0, j1 + 1), np.arange(i0, i1 + 1))
    A, Mu, Mv = pixel_overlap(jj - 0.5 - xc, jj + 0.5 - xc, ii - 0.5 - yc, ii + 0.5 - yc, r)
    return (slice(i0, i1 + 1), slice(j0, j1 + 1)), A, Mu + xc * A, Mv + yc * A


def annulus_mask(xc, yc, rin, rout, shape):
    """Pixels whose centres lie in rin <= rho < rout (the usual sky-annulus convention)."""
    yy, xx = np.indices(shape)
    rho = np.hypot(xx - xc, yy - yc)
    return (rho >= rin) & (rho < rout)
