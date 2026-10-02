"""Hubble's 3I frames prepared for the calibrator: load, locate, clean against siblings, resample north-up.

Frames: WFC3/UVIS2-2K2C-SUB F350LP _flc (electrons per detector pixel), data/hst-3i/, checked against
CHECKSUMS.sha256 by tools/fetch_frames.py. Coordinates 0-based (numpy), x = column, y = row.
Cleaning follows K1d (a private record of 14 Sept 2026): a pixel more than `nsig` sigma above the median of
its dither-position siblings is replaced by that median; its 8 neighbours are replaced too if they exceed
`nsig_grow` sigma. Inside r <= `core` px of the comet nothing is replaced (hits there are counted).
Resampling: output pixels on a square, north-up, east-left gnomonic grid of scale s (arcsec) about the reference;
GridMap sends it through the frame's FULL WCS (SIP and the D2IM/CPDIS lookup tables) on a node grid every `step`
output pixels, with bicubic splines between nodes; values are multiplied by the local |d(x,y)/d(i,j)| (detector
pixels per output pixel) so that flux is conserved. (SkyMap, the cubic polynomial, missed the lookup tables by
0.07 px: H0 run 2, 18:49 UTC; it stays for the local Jacobian and the tests.)
"""
import os, re, warnings
import numpy as np
from scipy import ndimage

def _frames_folder():
    """Hubble's frames: data/hst-3i/ at the repository's root, beside this package, where tools/fetch_frames.py puts them
    when it runs from the root and where the checksum list it reads is kept. Where the repository is a folder inside a
    larger tree that keeps that list itself (the Castle, with calibrator/ in it), the tree's own data/hst-3i/, beside the
    folder. The first of the two that holds CHECKSUMS.sha256; with neither, the repository's own."""
    repo = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for base in (repo, os.path.dirname(repo)):
        d = os.path.join(base, 'data', 'hst-3i')
        if os.path.isfile(os.path.join(d, 'CHECKSUMS.sha256')):
            return d
    return os.path.join(repo, 'data', 'hst-3i')


DATA = _frames_folder()

__all__ = ['load', 'find_peak', 'refind', 'dither_groups', 'clean_group', 'SkyMap', 'resample', 'GridMap', 'resample_grid', 'tan_inverse']


def load(root, data=DATA):
    from astropy.io import fits
    from astropy.wcs import WCS
    path = os.path.join(data, root + '_flc.fits')
    with fits.open(path) as f:
        p, s = f[0].header.copy(), f[1].header.copy()
        sci = f[1].data.astype(np.float64); err = f[2].data.astype(np.float64); dq = f[3].data.astype(np.int32)
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            w = WCS(s, f)
    return dict(root=root, visit=root[4:6], sci=sci, err=err, dq=dq, phdr=p, hdr=s, wcs=w,
                expstart=float(p['EXPSTART']), exptime=float(p['EXPTIME']), sky=float(s.get('MDRIZSKY', 0.0)))


def find_peak(sci, x0, y0, search=300, box=5, coarse=25, fine=10):
    """The comet's peak: the brightest pixel of a coarse (coarse x coarse) box-smoothing within +-search px of (x0, y0),
    where the coma outweighs a cosmic ray or a star trail; then K0's 5x5-smoothed peak within +-fine px of it.
    (H0 run 1, 18:39 UTC: the single 5x5 stage caught 50-80 k e- objects 220-340 px away in 04pjq, 05qpq, 06toq -
    the three frames K0 re-centred in its pass 2; with the coarse stage, 04pjq's 79 k e- trail 219 px away still won,
    and the comet sits up to 110 px from CRPIX, so the window stays +-300 px. Pass 2 is `refind`: a frame more than
    20 px from its visit's median peak is searched again within +-20 px of that median.)"""
    ix, iy = int(round(x0)), int(round(y0))
    win = sci[iy - search:iy + search + 1, ix - search:ix + search + 1]
    cs = ndimage.uniform_filter(win, coarse, mode='nearest')
    cy, cx = np.unravel_index(np.argmax(cs), cs.shape)
    sm = ndimage.uniform_filter(win, box, mode='nearest')
    y0f, x0f = max(cy - fine, 0), max(cx - fine, 0)
    sub = sm[y0f:cy + fine + 1, x0f:cx + fine + 1]
    py, px = np.unravel_index(np.argmax(sub), sub.shape)
    return ix - search + x0f + px, iy - search + y0f + py


def refind(frames, tol=20):
    """K0's pass 2: frames whose peak lies > tol px from their visit's median peak are searched within +-tol px of it.
    frames: dicts with root, visit, sci, px, py (updated in place). Returns the roots re-found."""
    out = []
    for v in sorted(set(f['visit'] for f in frames)):
        fs = [f for f in frames if f['visit'] == v]
        mx, my = np.median([f['px'] for f in fs]), np.median([f['py'] for f in fs])
        for f in fs:
            if np.hypot(f['px'] - mx, f['py'] - my) > tol:
                f['px'], f['py'] = find_peak(f['sci'], mx, my, search=tol, coarse=5, fine=tol)
                out.append(f['root'])
    return out


def dither_groups(frames):
    """Split each visit's frames at the midpoint of its peak-x range (K1d). Returns {root: 'VV' + 'A'/'B'}."""
    out = {}
    for v in sorted(set(f['visit'] for f in frames)):
        fs = [f for f in frames if f['visit'] == v]
        xs = [f['px'] for f in fs]
        mid = 0.5 * (min(xs) + max(xs))
        for f in fs:
            out[f['root']] = v + ('B' if f['px'] > mid else 'A') if max(xs) - min(xs) > 1.5 else v + 'A'
    return out


def clean_group(cuts, errs, core_xy, nsig=5.0, nsig_grow=2.0, core=5.0):
    """cuts, errs: lists of same-shape arrays (one dither position, aligned by construction). Returns the
    cleaned list and per-frame stats (replaced pixels, flux replaced, hits inside the core)."""
    n = len(cuts)
    out, stats = [], []
    yy, xx = np.indices(cuts[0].shape)
    rr = np.hypot(xx - core_xy[0], yy - core_xy[1])
    for i in range(n):
        others = [cuts[j] for j in range(n) if j != i]
        if not others:
            out.append(cuts[i].copy()); stats.append(dict(replaced=0, flux=0.0, core_hits=0)); continue
        ref = np.median(np.array(others), axis=0)
        sig = np.sqrt(errs[i] ** 2 + np.mean(np.array([errs[j] for j in range(n) if j != i]) ** 2, axis=0))
        z = (cuts[i] - ref) / sig
        hit = z > nsig
        grow = ndimage.binary_dilation(hit, structure=np.ones((3, 3), bool)) & (z > nsig_grow)
        m = (hit | grow) & (rr > core)
        c = cuts[i].copy(); c[m] = ref[m]
        out.append(c)
        stats.append(dict(replaced=int(m.sum()), flux=float((cuts[i] - ref)[m].sum()), core_hits=int((hit & (rr <= core)).sum())))
    return out, stats


class SkyMap:
    """Sky offsets (xi = dRA cos dec, eta = dDec; arcsec, east and north positive) about a reference pixel,
    to cutout pixel coordinates, by a cubic polynomial fitted to the full WCS."""

    def __init__(self, wcs, xref_full, yref_full, x_off, y_off, half_px, step=32, deg=3):
        # control points on the cutout (full-frame coordinates for the WCS)
        g = np.arange(-half_px, half_px + 1e-9, step)
        GX, GY = np.meshgrid(g, g)
        xf, yf = xref_full + GX.ravel(), yref_full + GY.ravel()
        ra0, de0 = wcs.all_pix2world([[xref_full, yref_full]], 0)[0]
        sk = wcs.all_pix2world(np.stack([xf, yf], axis=1), 0)
        dra = (sk[:, 0] - ra0 + 180.0) % 360.0 - 180.0
        xi = dra * np.cos(np.radians(de0)) * 3600.0
        eta = (sk[:, 1] - de0) * 3600.0
        self.ra0, self.de0 = float(ra0), float(de0)
        self.deg = deg
        self.terms = [(i, j) for i in range(deg + 1) for j in range(deg + 1 - i)]
        X = self._design(xi, eta)
        self.cx = np.linalg.lstsq(X, GX.ravel(), rcond=None)[0]
        self.cy = np.linalg.lstsq(X, GY.ravel(), rcond=None)[0]
        self.resid = float(np.hypot(X @ self.cx - GX.ravel(), X @ self.cy - GY.ravel()).max())
        self.x_ref_cut, self.y_ref_cut = xref_full - x_off, yref_full - y_off
        # local Jacobian at the reference (arcsec per px), by inversion of the polynomial's derivative
        Dx = self._grad(self.cx, 0.0, 0.0); Dy = self._grad(self.cy, 0.0, 0.0)
        self.Jinv = np.array([Dx, Dy])            # d(x,y)/d(xi,eta), px per arcsec
        self.J = np.linalg.inv(self.Jinv)         # d(xi,eta)/d(x,y)

    def _design(self, xi, eta):
        return np.stack([xi ** i * eta ** j for (i, j) in self.terms], axis=1)

    def _grad(self, c, xi, eta):
        dxi = sum(c[k] * i * xi ** max(i - 1, 0) * eta ** j for k, (i, j) in enumerate(self.terms) if i > 0)
        deta = sum(c[k] * j * xi ** i * eta ** max(j - 1, 0) for k, (i, j) in enumerate(self.terms) if j > 0)
        return np.array([dxi, deta], dtype=float)

    def to_cut(self, xi, eta):
        X = self._design(np.ravel(xi), np.ravel(eta))
        return (X @ self.cx).reshape(np.shape(xi)) + self.x_ref_cut, (X @ self.cy).reshape(np.shape(xi)) + self.y_ref_cut

    def area_factor(self, xi, eta):
        """|d(x,y)/d(xi,eta)| (detector px per arcsec^2) at each point."""
        xi, eta = np.ravel(xi), np.ravel(eta)
        def d(c, wrt):
            out = np.zeros_like(xi)
            for k, (i, j) in enumerate(self.terms):
                if wrt == 0 and i > 0:
                    out += c[k] * i * xi ** (i - 1) * eta ** j
                if wrt == 1 and j > 0:
                    out += c[k] * j * xi ** i * eta ** (j - 1)
            return out
        return np.abs(d(self.cx, 0) * d(self.cy, 1) - d(self.cx, 1) * d(self.cy, 0))


def resample(cut, smap, s, half_arcsec, order=3):
    """The cutout on a north-up, east-left grid of scale s arcsec, (2m+1)^2 px with m = round(half/s); the
    reference sits at the centre pixel (m, m). Column index increases westward (xi = -(j - m) s)."""
    m = int(round(half_arcsec / s))
    k = (np.arange(2 * m + 1) - m) * s
    XI, ETA = np.meshgrid(-k, k)
    xc, yc = smap.to_cut(XI, ETA)
    val = ndimage.map_coordinates(cut, [yc.ravel(), xc.ravel()], order=order, mode='constant', cval=np.nan)
    img = (val * smap.area_factor(XI, ETA) * s * s).reshape(XI.shape)
    return img, (float(m), float(m))


def tan_inverse(xi, eta, ra0, de0):
    """Standard (gnomonic) coordinates in arcsec (xi east, eta north) about (ra0, de0) -> (ra, dec) in degrees."""
    x, y = np.radians(np.asarray(xi, float) / 3600.0), np.radians(np.asarray(eta, float) / 3600.0)
    a0, d0 = np.radians(ra0), np.radians(de0)
    den = np.cos(d0) - y * np.sin(d0)
    ra = a0 + np.arctan2(x, den)
    dec = np.arctan2(np.sin(d0) + y * np.cos(d0), np.hypot(x, den))
    return np.degrees(ra) % 360.0, np.degrees(dec)


class GridMap:
    """The output grid ((2m+1)^2 px, scale s, north up, east left, the reference at pixel (m, m)) mapped to cutout
    pixel coordinates through the full WCS at nodes every `step` output pixels, bicubic splines between."""

    def __init__(self, wcs, xref_full, yref_full, x_off, y_off, s, half_arcsec, step=10):
        from scipy.interpolate import RectBivariateSpline
        self.wcs, self.x_off, self.y_off, self.s = wcs, x_off, y_off, s
        self.m = m = int(round(half_arcsec / s))
        self.ra0, self.de0 = (float(v) for v in wcs.all_pix2world([[xref_full, yref_full]], 0)[0])
        nodes = np.unique(np.concatenate([np.arange(0, 2 * m + 1, step), [2 * m]])).astype(float)
        J, I = np.meshgrid(nodes, nodes)
        X, Y = self._exact(I, J)
        self.sx = RectBivariateSpline(nodes, nodes, X, kx=3, ky=3)
        self.sy = RectBivariateSpline(nodes, nodes, Y, kx=3, ky=3)
        self.x_ref_cut, self.y_ref_cut = xref_full - x_off, yref_full - y_off

    def _exact(self, I, J):
        xi, eta = -(np.asarray(J, float) - self.m) * self.s, (np.asarray(I, float) - self.m) * self.s
        ra, dec = tan_inverse(xi, eta, self.ra0, self.de0)
        xy = self.wcs.all_world2pix(np.stack([np.ravel(ra), np.ravel(dec)], axis=1), 0, tolerance=1e-7, maxiter=100)
        return (xy[:, 0].reshape(np.shape(I)) - self.x_off, xy[:, 1].reshape(np.shape(I)) - self.y_off)

    def check(self, n=2000, seed=0, margin=1.0):
        """Largest |spline - full WCS| (cutout px) at n random output positions."""
        rng = np.random.default_rng(seed)
        I = rng.uniform(margin, 2 * self.m - margin, n); J = rng.uniform(margin, 2 * self.m - margin, n)
        X, Y = self._exact(I, J)
        return float(np.hypot(self.sx.ev(I, J) - X, self.sy.ev(I, J) - Y).max())

    def maps(self):
        idx = np.arange(2 * self.m + 1, dtype=float)
        X, Y = self.sx(idx, idx), self.sy(idx, idx)
        Xi, Xj = self.sx(idx, idx, dx=1), self.sx(idx, idx, dy=1)
        Yi, Yj = self.sy(idx, idx, dx=1), self.sy(idx, idx, dy=1)
        return X, Y, np.abs(Xj * Yi - Xi * Yj)


def resample_grid(cut, gmap, order=3):
    """The cutout on gmap's grid; returns (image, (m, m)). Flux-conserving: value * detector px per output px."""
    X, Y, area = gmap.maps()
    val = ndimage.map_coordinates(cut, [Y.ravel(), X.ravel()], order=order, mode='constant', cval=np.nan)
    return (val.reshape(X.shape) * area), (float(gmap.m), float(gmap.m))
