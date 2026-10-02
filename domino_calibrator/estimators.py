"""Photocentre estimators inside a synthetic aperture of radius r.

M  moment photocentre: first moment of (image - background) over the exact circle-pixel overlaps,
   re-centred on itself until it moves < tol. With exact moments the fixed point does not depend on
   any constant background (sum of w (x - c) over the aperture is exactly zero); the background changes
   the noise and the speed of convergence only.
G  symmetric fit: a circular Gaussian integrated over pixels (free amplitude, centre, width), least
   squares weighted by each pixel's overlap with the aperture, the aperture re-centred on the fit until it
   moves < tol. Background fixed beforehand (Farnocchia et al. 2016: from the 2.5r-5r annulus).
P  brightness peak: vertex of a quadratic surface fitted to the 3x3 pixels around the brightest pixel.

Farnocchia et al. 2016 (arXiv:1507.01980, l. 162-165, 523-526) describe "a model designed to fit the
symmetric light distribution from a point source" with the annulus background; which function, weighting
and re-centring Tholen's software uses is not published. M and G bracket the plausible readings.

The failure contract (the hardening round's record of 27 Sept 2026, not in this repository): an estimator never raises on data. Each
returns ok and a reason ('' when ok); an M or G that is not ok has no position (x, y NaN). An aperture is
measured only if it holds at least MIN_PIXELS pixels of positive overlap, every one of them finite (lane 5's
conditioning rule), and G's amplitude must be above 0. P keeps its documented fallback: the brightest pixel's
centre, with ok False and the reason.
"""
import numpy as np
from scipy.optimize import least_squares
from scipy.special import erf

from .apertures import circle_moments, annulus_mask

__all__ = ['moment_centroid', 'gauss_fit', 'peak_quadratic', 'annulus_background', 'sigma_clipped_median', 'MIN_PIXELS']

R2 = np.sqrt(2.0)
SQ2PI = np.sqrt(2.0 * np.pi)
MIN_PIXELS = 8          # the fewest pixels an aperture (or an annulus) may hold: lane 5's rule, the annulus's old one


def sigma_clipped_median(v, nsig=3.0, iters=5):
    v = np.asarray(v, float).ravel()
    v = v[np.isfinite(v)]
    for _ in range(iters):
        if v.size < 3:
            break
        med = np.median(v)
        mad = 1.4826 * np.median(np.abs(v - med))
        if mad <= 0:
            break
        keep = np.abs(v - med) < nsig * mad
        if keep.all():
            break
        v = v[keep]
    return float(np.median(v)) if v.size else float('nan')


def annulus_background(img, xc, yc, r, rin_fac=2.5, rout_fac=5.0):
    """Sigma-clipped median of the finite pixels whose centres lie in [rin_fac r, rout_fac r).
    Raises ValueError if fewer than MIN_PIXELS of them are finite (shrink records that as the radius's reason)."""
    m = annulus_mask(xc, yc, rin_fac * r, rout_fac * r, img.shape)
    v = img[m]
    if int(np.isfinite(v).sum()) < MIN_PIXELS:
        raise ValueError('annulus %.1f-%.1f px has fewer than %d finite pixels in the image' % (rin_fac * r, rout_fac * r, MIN_PIXELS))
    return sigma_clipped_median(v)


def _aitken(x0, x1, x2):
    d1, d2 = x1 - x0, x2 - x1
    den = d2 - d1
    if abs(den) < 1e-15:
        return x2
    g = d2 / d1 if abs(d1) > 1e-15 else 0.0
    if not (0.0 < g < 0.995):
        return x2
    return x2 - d2 * d2 / den


def _aperture_ok(A, pix):
    """The conditioning rule for one aperture: '' if it may be measured, else the reason."""
    use = A > 0
    if int(use.sum()) < MIN_PIXELS:
        return 'fewer than %d pixels in the aperture' % MIN_PIXELS
    if not np.all(np.isfinite(pix[use])):
        return 'non-finite pixel in the aperture'
    return ''


def moment_centroid(img, x0, y0, r, bkg=0.0, tol=1e-6, maxit=500):
    """Self-centred moment photocentre in a circle of radius r. Returns dict(x, y, n, flux, ok, reason);
    x and y are NaN unless ok."""
    xc, yc = float(x0), float(y0)
    hist = []
    F = float('nan')
    fail = lambda it, why: dict(x=np.nan, y=np.nan, n=it, flux=F, ok=False, reason=why)
    if not np.isfinite(bkg):
        return fail(0, 'background not finite')
    for it in range(1, maxit + 1):
        try:
            sl, A, Mx, My = circle_moments(xc, yc, r, img.shape)
        except ValueError:          # the iteration left the image (S1 run 1, 19:10 UTC): unconverged, not a crash
            return fail(it, 'aperture leaves the image')
        why = _aperture_ok(A, img[sl])
        if why:
            return fail(it, why)
        d = np.where(A > 0, img[sl] - bkg, 0.0)   # pixels the circle misses carry no weight: a NaN there is not data
        F = float((d * A).sum())                    # (H1 run 1, 19:17 UTC: NaN x 0 = NaN had poisoned the sums)
        if not np.isfinite(F) or F <= 0:
            return fail(it, 'flux in the aperture is not above the background')
        X, Y = float((d * Mx).sum() / F), float((d * My).sum() / F)
        if np.hypot(X - xc, Y - yc) < tol:
            return dict(x=X, y=Y, n=it, flux=F, ok=True, reason='')
        hist.append((X, Y))
        xc, yc = X, Y
        if len(hist) >= 3 and it % 3 == 0:    # Aitken's delta-squared on the last three iterates, per axis
            (xa, ya), (xb, yb), (xd, yd) = hist[-3:]
            xn, yn = _aitken(xa, xb, xd), _aitken(ya, yb, yd)
            step = np.hypot(xd - xb, yd - yb)
            if np.hypot(xn - xd, yn - yd) <= max(10.0 * step, 1e-3) and np.hypot(xn - xd, yn - yd) <= r:
                xc, yc = xn, yn             # a bounded jump only: noisy iterates can throw Aitken far away
            hist = []
    return fail(maxit, 'no convergence in %d iterations' % maxit)


def _pig(q, xx, yy):
    """Pixel-integrated circular Gaussian: q = (amp, x0, y0, log s)."""
    A, x0, y0, t = q
    s = np.exp(t)
    ax_p, ax_m = (xx + 0.5 - x0) / (R2 * s), (xx - 0.5 - x0) / (R2 * s)
    ay_p, ay_m = (yy + 0.5 - y0) / (R2 * s), (yy - 0.5 - y0) / (R2 * s)
    gx = 0.5 * (erf(ax_p) - erf(ax_m))
    gy = 0.5 * (erf(ay_p) - erf(ay_m))
    return A * gx * gy, (gx, gy, ax_p, ax_m, ay_p, ay_m, s)


def _pig_jac(q, xx, yy):
    A, x0, y0, t = q
    _, (gx, gy, ax_p, ax_m, ay_p, ay_m, s) = _pig(q, xx, yy)
    ex_p, ex_m, ey_p, ey_m = np.exp(-ax_p ** 2), np.exp(-ax_m ** 2), np.exp(-ay_p ** 2), np.exp(-ay_m ** 2)
    dgx_dx0 = -(ex_p - ex_m) / (SQ2PI * s)
    dgy_dy0 = -(ey_p - ey_m) / (SQ2PI * s)
    # d/ds of 0.5 erf((u)/(sqrt2 s)) = -(u/(sqrt(2pi) s^2)) exp(-u^2/2s^2); chain with ds/dt = s
    dgx_dt = -((R2 * s * ax_p) * ex_p - (R2 * s * ax_m) * ex_m) / (SQ2PI * s)
    dgy_dt = -((R2 * s * ay_p) * ey_p - (R2 * s * ay_m) * ey_m) / (SQ2PI * s)
    return np.stack([gx * gy, A * gy * dgx_dx0, A * gx * dgy_dy0, A * (dgx_dt * gy + gx * dgy_dt)], axis=-1)


def gauss_fit(img, x0, y0, r, bkg, s0=None, tol=1e-4, maxit=60):
    """Symmetric-fit photocentre: circular pixel-integrated Gaussian fitted inside the aperture, the
    aperture re-centred on the fit. Returns dict(x, y, s, amp, n, ok, at_bound, reason); x and y are NaN
    unless ok (s and amp are kept for a runaway, at_bound True)."""
    xa, ya = float(x0), float(y0)
    s_init = float(s0) if s0 else max(0.6, 0.5 * r)
    q = None
    fail = lambda it, why, s=np.nan, amp=np.nan, at_bound=False: dict(x=np.nan, y=np.nan, s=s, amp=amp, n=it, ok=False,
                                                                      at_bound=at_bound, reason=why)
    if not np.isfinite(bkg):
        return fail(0, 'background not finite')
    for it in range(1, maxit + 1):
        try:
            sl, A, _, _ = circle_moments(xa, ya, r, img.shape)
        except ValueError:
            return fail(it, 'aperture leaves the image')
        why = _aperture_ok(A, img[sl])      # scipy raised on a NaN pixel, and on fewer pixels than its 4 parameters
        if why:
            return fail(it, why)
        ii, jj = np.mgrid[sl[0], sl[1]]
        use = A > 0
        xx, yy = jj[use].astype(float), ii[use].astype(float)
        d = img[sl][use] - bkg
        w = np.sqrt(A[use])
        if q is None:
            q = np.array([max(float(d.sum()), 1e-6), xa, ya, np.log(s_init)])
        fun = lambda p: (_pig(p, xx, yy)[0] - d) * w
        jac = lambda p: _pig_jac(p, xx, yy) * w[:, None]
        res = least_squares(fun, q, jac=jac, method='lm', xtol=1e-10, ftol=1e-10, max_nfev=400)
        q = res.x
        if not np.all(np.isfinite(q)):
            return fail(it, 'the fit went non-finite')
        s = float(np.exp(q[3]))
        wild = (s < 0.05) or (s > 20.0 * r) or np.hypot(q[1] - xa, q[2] - ya) > r
        if wild:
            return fail(it, 'the fit ran away (width %.3g px, or a jump beyond r)' % s, s=s, amp=float(q[0]), at_bound=True)
        if np.hypot(q[1] - xa, q[2] - ya) < tol:
            if not res.success:
                return fail(it, 'the least-squares fit did not converge', s=s, amp=float(q[0]))
            if not q[0] > 0:
                return fail(it, 'amplitude not above 0: no source to centre on', s=s, amp=float(q[0]))
            return dict(x=float(q[1]), y=float(q[2]), s=s, amp=float(q[0]), n=it, ok=True, at_bound=False, reason='')
        xa, ya = float(q[1]), float(q[2])
    return fail(maxit, 'no convergence in %d re-centrings' % maxit, s=float(np.exp(q[3])), amp=float(q[0]))


def peak_quadratic(img, x0, y0, search=3):
    """Brightness peak: vertex of z = c0 + c1 x + c2 y + c3 x^2 + c4 xy + c5 y^2 fitted to the 3x3 pixels
    around the brightest pixel within +-search px of (x0, y0) (the window clipped to the image). Returns
    dict(x, y, ok, reason). ok=False, with the brightest pixel's centre, if that pixel is on the image's edge or
    beside a non-finite pixel, if the surface is not a maximum, or if the vertex leaves the central pixel's
    +-1 px; x and y are NaN only if the window holds no finite pixel."""
    ny, nx = img.shape
    ix, iy = int(round(x0)), int(round(y0))
    i0, i1, j0, j1 = max(iy - search, 0), min(iy + search + 1, ny), max(ix - search, 0), min(ix + search + 1, nx)
    win = img[i0:i1, j0:j1] if (i1 > i0 and j1 > j0) else np.empty((0, 0))
    if not np.isfinite(win).any():
        return dict(x=np.nan, y=np.nan, ok=False, reason='no finite pixel within %d px of the start' % search)
    py, px = np.unravel_index(np.nanargmax(win), win.shape)
    cy, cx = i0 + py, j0 + px
    if not (1 <= cy <= ny - 2 and 1 <= cx <= nx - 2):
        return dict(x=float(cx), y=float(cy), ok=False, reason='the brightest pixel is on the image edge')
    z = img[cy - 1:cy + 2, cx - 1:cx + 2].astype(float)
    if not np.all(np.isfinite(z)):
        return dict(x=float(cx), y=float(cy), ok=False, reason='non-finite pixel beside the brightest')
    yy, xx = np.mgrid[-1:2, -1:2]
    X = np.stack([np.ones(9), xx.ravel(), yy.ravel(), xx.ravel() ** 2, (xx * yy).ravel(), yy.ravel() ** 2], axis=1)
    c = np.linalg.lstsq(X, z.ravel(), rcond=None)[0]
    H = np.array([[2 * c[3], c[4]], [c[4], 2 * c[5]]])
    if not np.all(np.linalg.eigvalsh(H) < 0):
        return dict(x=float(cx), y=float(cy), ok=False, reason='the 3x3 surface is not a maximum')
    v = np.linalg.solve(H, -c[1:3])
    if not np.all(np.abs(v) <= 1.0):
        return dict(x=float(cx), y=float(cy), ok=False, reason="the vertex lies beyond the brightest pixel's +-1 px")
    return dict(x=float(cx + v[0]), y=float(cy + v[1]), ok=True, reason='')
