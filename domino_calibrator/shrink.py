"""The shrinking-aperture sequence and its extrapolation to zero aperture.

Published form (Farnocchia et al. 2016, arXiv:1507.01980, l. 519-521): photocentres in synthetic apertures of
radius 2.0 to 6.0 px in steps of 0.1 px, a straight line through x(r) and y(r), the zero-aperture position its
intercept. Background (l. 523-526): an annulus 2.5r-5r around each aperture. Both are parameters here.
"""
import numpy as np

from .estimators import moment_centroid, gauss_fit, peak_quadratic, annulus_background

__all__ = ['PUBLISHED_RADII', 'shrink', 'linear_extrapolate']

PUBLISHED_RADII = np.round(np.arange(2.0, 6.0 + 1e-9, 0.1), 10)


def linear_extrapolate(radii, v):
    """Least-squares line v = v0 + s r over the given radii; returns (v0, s)."""
    r = np.asarray(radii, float)
    v = np.asarray(v, float)
    X = np.stack([np.ones_like(r), r], axis=1)
    c = np.linalg.lstsq(X, v, rcond=None)[0]
    return float(c[0]), float(c[1])


def shrink(img, x0, y0, radii=PUBLISHED_RADII, estimator='M', background='annulus', annulus=(2.5, 5.0),
           tol_m=1e-6, tol_g=1e-4, warm=True):
    """Photocentre at each radius, the line through them, and its value at r = 0.

    estimator  'M' (moment) or 'G' (symmetric Gaussian fit).
    background 'annulus' (sigma-clipped median in annulus[0]*r - annulus[1]*r about the current start),
               or a number (a known sky, per pixel).
    Starting point: (x0, y0) for the first radius; each next radius starts from the previous answer if warm.
    Returns a dict: radii, x, y, ok, reason, bkg, s (G widths); x0, y0 (intercepts), sx, sy (slopes per px);
    x2, y2 / x6, y6 (the answers at the radii nearest 2 and 6 px); nbad (radii that did not converge).
    Every radius carries ok and a reason ('' when ok); a radius that is not ok has no position (x, y NaN),
    never its runaway (the hardening round's record of 27 Sept 2026, not in this repository). The data never raise here; arguments that
    are not data (an unknown estimator, a background that is neither 'annulus' nor a number, a start that is not
    a finite position) do.
    """
    radii = np.asarray(radii, float)
    if estimator not in ('M', 'G'):
        raise ValueError("estimator must be 'M' or 'G', not %r" % (estimator,))
    if isinstance(background, str) and background != 'annulus':
        raise ValueError("background must be 'annulus' or a number, not %r" % (background,))
    known = None if isinstance(background, str) else float(background)
    xs, ys, oks, why, bk, ss = [], [], [], [], [], []
    sx0, sy0 = float(x0), float(y0)
    if not (np.isfinite(sx0) and np.isfinite(sy0)):   # inf raised OverflowError; nan gave 41 x "leaves the image"
        raise ValueError('the start (%r, %r) is not a finite pixel position' % (x0, y0))
    s_prev = None
    for r in radii:
        if known is None:
            try:
                b, bwhy = annulus_background(img, sx0, sy0, r, *annulus), 'background: no finite value in the annulus'
            except ValueError as e:     # the annulus does not fit: this radius is unconverged
                b, bwhy = np.nan, 'background: %s' % e
        else:
            b, bwhy = known, 'background is not a finite number'
        if not np.isfinite(b):
            o = dict(x=np.nan, y=np.nan, ok=False, s=np.nan, reason=bwhy)
        elif estimator == 'M':
            o = moment_centroid(img, sx0, sy0, r, bkg=b, tol=tol_m)
            s_prev = None
        else:
            o = gauss_fit(img, sx0, sy0, r, bkg=b, s0=s_prev, tol=tol_g)
            s_prev = o.get('s') if o['ok'] and np.isfinite(o.get('s', np.nan)) else None
        ok = bool(o['ok']) and bool(np.isfinite(o['x'])) and bool(np.isfinite(o['y']))
        xs.append(o['x'] if ok else np.nan); ys.append(o['y'] if ok else np.nan); oks.append(ok)
        why.append('' if ok else (o.get('reason') or 'not converged')); bk.append(b); ss.append(o.get('s', np.nan))
        if warm and ok:
            sx0, sy0 = o['x'], o['y']
        else:
            sx0, sy0 = float(x0), float(y0)
    xs, ys, oks = np.array(xs), np.array(ys), np.array(oks, bool)
    good = oks & np.isfinite(xs) & np.isfinite(ys)
    out = dict(radii=radii, x=xs, y=ys, ok=oks, reason=why, bkg=np.array(bk), s=np.array(ss), estimator=estimator,
               nbad=int((~good).sum()))
    if good.sum() >= 2:
        out['x0'], out['sx'] = linear_extrapolate(radii[good], xs[good])
        out['y0'], out['sy'] = linear_extrapolate(radii[good], ys[good])
    else:
        out['x0'] = out['y0'] = out['sx'] = out['sy'] = np.nan
    i2, i6 = int(np.argmin(np.abs(radii - 2.0))), int(np.argmin(np.abs(radii - 6.0)))
    # an unconverged radius reports NaN, not its runaway position (H3 post hoc, 20:25 UTC: 51 of 7,800 noisy G runs)
    out['x2'], out['y2'] = (xs[i2], ys[i2]) if good[i2] else (np.nan, np.nan)
    out['x6'], out['y6'] = (xs[i6], ys[i6]) if good[i6] else (np.nan, np.nan)
    return out


def peak(img, x0, y0, search=3):
    return peak_quadratic(img, x0, y0, search=search)
