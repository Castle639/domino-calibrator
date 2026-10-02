#!/usr/bin/env python3
"""tools/psfkit.py (copied from its makers' private repository at b1da95b, curated for this one) - the Castle's PSF kit: TinyTim's WFC3/UVIS PSF at any chip position, spectrum and
sub-pixel position, rendered the way TinyTim's own unsubsampled path renders it; and the width method.

22 Sept 2026. A Castle product from Domino Observatory. Built by Annie, the Castle's AI.
First function set:
the kernels, the render, the method. `python3 tools/psfkit.py` runs the self-test (K, V3, offsets).\nSecond function set, the same day: render_at (any real sub-pixel offset) and trail_kernel.
TinyTim 7.5 comes from the Space Telescope Science Institute's own repository (github.com/spacetelescope/tinytim,
c3d06ef), built from its source; nothing here writes into it.

TinyTim's path, read at source (c3d06ef):
  tiny3.c 215-231   SUB=1: Distort() integrates the critically sampled PSF onto detector pixels, then
                    Convolve(weighted_kernel), then Convolve(kernel_xy): two 3x3 passes = one 5x5.
  tiny3.c 238-258   SUB=n: no kernel; the header carries Convolve_kernel(weighted_kernel, kernel_xy).
  acs.c 249-303     Convolve_kernel keeps only the central 3x3 of that 5x5 and renormalises, so the
                    header kernel applied after rebinning blurs less than TinyTim's own path.
  acs.c 210-243     weighted_kernel = sum_i w_i * norm(lerp(kernel, lambda_i)) (zeroed at param.c 44);
                    the segment comes from `while (lambda > kw[iw] && iw < NUM_WFC3_KERNELS-2) ++iw`
                    (line 216), so every lambda > 0.4 um uses the 0.6-0.8 um segment.
  acs.c 51-139      kernel_xy = 3x3 Gaussian; sigma = polynomial in (x/40.96+4, y/40.96+4) at
                    lambda = the first wavelength; for UVIS only the constant 0.45816 is non-zero.
  misc.c 64-110     Convolve is a 3x3 correlation in place; edge rows/columns are not convolved.
  distort.c 240-330 each output pixel is sampled (pixel/psf_scale*3, odd, >= 3)^2 times: 11x11 at
                    SUB=1; 3x3 per subpixel at SUB=7 (21x21 per detector pixel after binning).
"""
import os, re, time, subprocess
import numpy as np
from scipy import ndimage
from scipy.optimize import least_squares
from scipy.special import erf

HOME = os.environ['HOME']
TT = os.environ.get('TINYTIM', os.path.join(HOME, 'tt', 'src'))
K2F = 2.0 * np.sqrt(2.0 * np.log(2.0))
R2 = np.sqrt(2.0)

# ---------------- TinyTim ----------------
def tinytim(name, spec, x, y, sub, workdir):
    """tiny1 with the recipe's nine answers (spectrum # and position varied), tiny2, tiny3 SUB=sub.
    Returns (fits path, param path). An existing output is reused."""
    d = os.path.join(workdir, name); os.makedirs(d, exist_ok=True)
    out, par = os.path.join(d, name + '00.fits'), os.path.join(d, name + '.param')
    if not os.path.exists(out):
        env = dict(os.environ, TINYTIM=TT)
        ans = '22\n2\n%d %d\nf350lp\n1\n%d\n3.0\n0\n%s\n' % (x, y, spec, name)
        subprocess.run([os.path.join(TT, 'tiny1'), name + '.param'], input=ans, text=True, cwd=d, env=env, capture_output=True, check=True)
        txt = open(par).read()
        assert re.search(r'^%d %d +# Position 1' % (x, y), txt, re.M), 'position line'
        assert re.search(r'^2\.980 +# PSF diameter', txt, re.M), 'diameter line'
        subprocess.run([os.path.join(TT, 'tiny2'), name + '.param'], cwd=d, env=env, capture_output=True, check=True)
        subprocess.run([os.path.join(TT, 'tiny3'), name + '.param', 'SUB=%d' % sub], cwd=d, env=env, capture_output=True, check=True)
    return out, par

def _rows(L, start, nrow, ncol):
    rows, j = [], start
    while len(rows) < nrow:
        s = L[j].split('#')[0].split(); j += 1
        if len(s) == ncol:
            rows.append([float(v) for v in s])
    return rows

def read_param(path):
    """The parts of a TinyTim param file the kernels need."""
    L = [l.rstrip('\n') for l in open(path)]
    p = dict(waves=[], weights=[], kw=[], kernels=[], bw=[], blur=[])
    for i, l in enumerate(L):
        if '# Wavelength' in l and 'weight' in l:
            a = l.split('#')[0].split(); p['waves'].append(float(a[0])); p['weights'].append(float(a[1]))
        elif '# Position 1' in l:
            p['pos'] = tuple(int(v) for v in l.split('#')[0].split())
        elif '# Camera' in l and 'ID' not in l:
            p['camera'] = l.split('#')[0].strip()
        elif '= Wavelength (microns) of kernel' in l:
            p['kw'].append(float(l.split('=')[0])); p['kernels'].append(_rows(L, i + 1, 3, 3))
        elif re.match(r'^\s*[0-9.]+\s+= wavelength \d+\s*$', l):
            p['bw'].append(float(l.split('=')[0])); p['blur'].append(_rows(L, i + 1, 6, 6))
    for k in ('waves', 'weights', 'kw', 'kernels', 'bw', 'blur'):
        p[k] = np.array(p[k], float)
    return p

def weighted_kernel(p):
    """acs.c 210-243, summed over every wavelength in the param (tiny3.c 191-194)."""
    kw, K, W = p['kw'], p['kernels'], np.zeros((3, 3))
    for lam, w in zip(p['waves'], p['weights']):
        iw = 0
        while lam > kw[iw] and iw < len(kw) - 2:
            iw += 1
        k = (K[iw + 1] - K[iw]) / (kw[iw + 1] - kw[iw]) * (lam - kw[iw]) + K[iw]
        W += k / k.sum() * w
    return W

def kernel_xy(p, x=None, y=None):
    """acs.c 51-139. Returns (3x3 kernel, sigma)."""
    x = p['pos'][0] if x is None else x; y = p['pos'][1] if y is None else y
    d = 40.96
    xx = x / d + 4
    yy = (y + (2048 if p['camera'] in ('WFC3_UVIS1', 'ACS_WFC1') else 0)) / d + 4
    lam, bw, B = p['waves'][0], p['bw'], p['blur']
    poly = lambda c: sum(c[i][j] * xx ** i * yy ** j for i in range(6) for j in range(6))
    n, i = len(bw), 0
    while i < n - 1:
        if lam < bw[i]:
            break
        i += 1
    if i < n - 1:
        s0, s1 = poly(B[i]), poly(B[i + 1]); sigma = (s1 - s0) / (bw[i + 1] - bw[i]) * (lam - bw[i]) + s0
    else:
        sigma = poly(B[n - 1])
    if sigma > 0:
        yy_, xx_ = np.mgrid[-1:2, -1:2]; k = np.exp(-0.5 * (np.hypot(yy_, xx_) / sigma) ** 2); k /= k.sum()
    else:
        k = np.zeros((3, 3)); k[1, 1] = 1.0
    return k, float(sigma)

def full5(k1, k2):
    """The 5x5 kernel TinyTim's two passes amount to (tiny3.c 230-231); acs.c 268-288's loop."""
    a = np.zeros((5, 5)); a[1:4, 1:4] = k1; out = np.zeros((5, 5))
    for j in range(5):
        for i in range(5):
            for jj in (-1, 0, 1):
                for ii in (-1, 0, 1):
                    if 0 <= j + jj <= 4 and 0 <= i + ii <= 4:
                        out[j, i] += a[j + jj, i + ii] * k2[jj + 1, ii + 1]
    return out

def combine_truncated(k1, k2):
    """acs.c 249-303: central 3x3 of the 5x5, renormalised - what a subsampled PSF's header carries."""
    c = full5(k1, k2)[1:4, 1:4]; return c / c.sum()

def header_kernel(fits_path):
    from astropy.io import fits
    com = [str(c).strip() for c in fits.open(fits_path)[0].header.get('COMMENT', [])]
    i = [j for j, l in enumerate(com) if 'following kernel' in l][0]
    return np.array([[float(v) for v in com[i + 1 + r].split()] for r in range(3)])

def render(S, sub, ky, kx, kernels, half=43):
    """Bin a SUB=sub TinyTim PSF (peak at the array centre, sub odd) onto detector pixels with the PSF
    centre at (-ky/sub, -kx/sub) px from the centre of pixel (half, half); then apply `kernels` in order
    (TinyTim's own path: (weighted_kernel, kernel_xy))."""
    c, n, h = S.shape[0] // 2, 2 * half + 1, sub // 2
    y0, x0 = c - h + ky - sub * half, c - h + kx - sub * half
    blk = S[y0:y0 + sub * n, x0:x0 + sub * n]
    assert y0 >= 0 and x0 >= 0 and blk.shape == (sub * n, sub * n), 'offset or half too large'
    P = blk.reshape(n, sub, n, sub).sum(axis=(1, 3))
    for k in kernels:
        P = ndimage.correlate(P, k, mode='constant', cval=0.0)
    return P

# ---------------- the method ----------------
def _pig(q, yy, xx):
    A, y0, x0, sy, sx, B = q
    gx = 0.5 * (erf((xx + 0.5 - x0) / (R2 * sx)) - erf((xx - 0.5 - x0) / (R2 * sx)))
    gy = 0.5 * (erf((yy + 0.5 - y0) / (R2 * sy)) - erf((yy - 0.5 - y0) / (R2 * sy)))
    return A * gx * gy + B

def width(img, ny, nx, box=11, search=2):
    """THE METHOD, fixed in chat 22 Sept 2026 before any star (his yes): a 2D Gaussian integrated over
    each pixel, axis-aligned, free centre and background, unweighted least squares, box x box on the
    brightest pixel within +-search px of (ny, nx). FWHM = 2.3548 sqrt(sx sy); fx, fy; fitted centre."""
    s = img[ny - search:ny + search + 1, nx - search:nx + search + 1]
    py, px = np.unravel_index(np.argmax(s), s.shape); cy, cx = ny - search + py, nx - search + px
    h = box // 2; cut = img[cy - h:cy + h + 1, cx - h:cx + h + 1]
    yy, xx = np.mgrid[cy - h:cy + h + 1, cx - h:cx + h + 1].astype(float)
    edge = np.concatenate([cut[0], cut[-1], cut[1:-1, 0], cut[1:-1, -1]]); B0 = float(np.median(edge))
    q0 = [max(float(cut.sum() - B0 * cut.size), 1e-9), cy, cx, 0.8, 0.8, B0]
    lo = [0.0, cy - 2, cx - 2, 0.2, 0.2, -np.inf]; hi = [np.inf, cy + 2, cx + 2, 5.0, 5.0, np.inf]
    r = least_squares(lambda q: (_pig(q, yy, xx) - cut).ravel(), q0, bounds=(lo, hi), x_scale='jac')
    A, y0, x0, sy, sx, B = r.x
    return dict(fwhm=K2F * np.sqrt(sx * sy), fx=K2F * sx, fy=K2F * sy, y0=y0, x0=x0, flux=A, bg=B, ok=bool(r.success))

# ---------------- second function set (22 Sept 2026): any real offset, and a trail ----------------
def trail_kernel(length_px, uy, ux, sub):
    """A uniform line segment of length_px detector pixels along the unit vector (uy, ux), on the
    sub-grid (bilinear deposition, 8 points per subpixel of path, centred on 0); sum 1."""
    if length_px <= 0:
        return np.ones((1, 1))
    L = length_px * sub; n = max(int(np.ceil(L * 8)), 2)
    t = (np.arange(n) + 0.5) / n - 0.5
    R = int(np.ceil(L / 2)) + 2; K = np.zeros((2 * R + 1, 2 * R + 1))
    for y, x in zip(t * L * uy, t * L * ux):
        iy, ix = int(np.floor(y)), int(np.floor(x)); fy, fx = y - iy, x - ix
        K[iy + R, ix + R] += (1 - fy) * (1 - fx); K[iy + 1 + R, ix + R] += fy * (1 - fx)
        K[iy + R, ix + 1 + R] += (1 - fy) * fx; K[iy + 1 + R, ix + 1 + R] += fy * fx
    return K / K.sum()

def render_at(S, sub, dy, dx, kernels, trail=None, half=43):
    """The PSF centre at (dy, dx) px (any real numbers) from the centre of pixel (half, half): the SUB
    grid is smeared by `trail` = (length_px, uy, ux) if given, shifted by (dy*sub, dx*sub) subpixels
    (cubic spline; exact at whole subpixels), binned, then `kernels` applied in order."""
    A = S
    if trail is not None and trail[0] > 0:
        A = ndimage.convolve(A, trail_kernel(trail[0], trail[1], trail[2], sub), mode='constant', cval=0.0)
    if dy != 0 or dx != 0:
        A = ndimage.shift(A, (dy * sub, dx * sub), order=3, mode='constant', cval=0.0)
    return render(A, sub, 0, 0, kernels, half)

# ---------------- self-test ----------------
def selftest(logpath=None):
    from astropy.io import fits
    if logpath: os.makedirs(os.path.dirname(logpath), exist_ok=True)   # a fresh machine has no such folder
    out = open(logpath, 'w') if logpath else None
    def log(*a):
        s = ' '.join(str(v) for v in a); print(s, flush=True)
        if out: out.write(s + '\n'); out.flush()
    t0 = time.time(); work = os.path.join(HOME, 'psfkit_selftest')
    log('PSFKIT SELFTEST START', time.strftime('%Y-%m-%d %H:%M:%S %z'), '| TinyTim outputs + the pinned PSF only; no HST frame')
    ref_path = os.environ.get('PSFKIT_REF', '')   # the pinned reference PSF: TinyTim's UVIS2 F350LP PSF at (2040, 1024)
    if not os.path.isfile(ref_path):
        log('PSFKIT SELFTEST needs the pinned reference PSF (PSFKIT_REF: a FITS file, not in this repository) and '
            'TinyTim 7.5 (TINYTIM): nothing tested')
        return 2
    ref = fits.open(ref_path)[0].data.astype(np.float64)
    fpath, ppath = tinytim('g2v_c', 11, 2040, 1024, 7, work)
    S = fits.open(fpath)[0].data.astype(np.float64); p = read_param(ppath)
    wk = weighted_kernel(p); kxy, sig = kernel_xy(p); K5 = full5(wk, kxy); Kh = header_kernel(fpath)
    dK = float(np.abs(combine_truncated(wk, kxy) - Kh).max())
    ring = float(K5.sum() - K5[1:4, 1:4].sum())
    log('param: %d wavelengths %.4f-%.4f um, sum of weights %.6f | kernels at %s um | blur_xy at %s um' % (
        len(p['waves']), p['waves'][0], p['waves'][-1], p['weights'].sum(), p['kw'].tolist(), p['bw'].tolist()))
    log('weighted_kernel rows:', np.round(wk, 6).tolist(), '| kernel_xy sigma %.5f centre %.6f' % (sig, kxy[1, 1]))
    log('full 5x5 (TinyTim path): centre %.6f, outer ring holds %.4f of %.6f = %.2f %% | header 3x3 centre %.6f' % (
        K5[2, 2], ring, K5.sum(), 100 * ring / K5.sum(), Kh[1, 1]))
    log('K  ours, combined by TinyTim\'s truncation rule, vs the SUB=7 header kernel: max|diff| %.2e (line <= 1e-6) -> %s' % (
        dK, 'PASS' if dK <= 1e-6 else 'FAIL'))
    mr = width(ref, 44, 44)
    P = render(S, 7, 0, 0, (wk, kxy), half=44); P = P / P.sum()
    m = width(P, 44, 44); dF = 100 * (m['fwhm'] / mr['fwhm'] - 1); dP = 100 * np.abs(P - ref).max() / ref.max()
    log('V3 (0,0), TinyTim path (weighted_kernel then kernel_xy), 89x89 normalised as tiny3 does, vs the pinned PSF:')
    log('   METHOD FWHM %.4f vs %.4f = %+.3f %% (line 0.5 %%) | max|diff| %.3f %% of peak (line 1 %%) -> %s' % (
        m['fwhm'], mr['fwhm'], dF, dP, 'PASS' if abs(dF) <= 0.5 and dP <= 1.0 else 'FAIL'))
    Po = render(S, 7, 0, 0, (Kh,), half=43); mo = width(Po, 43, 43)
    log('   regression, the toy\'s old path (header kernel, 87x87, as run 21:24): FWHM %+.3f %%, max|diff| %.3f %% (toy: -1.178 %%, 2.860 %%)' % (
        100 * (mo['fwhm'] / mr['fwhm'] - 1), 100 * np.abs(Po - ref[1:-1, 1:-1]).max() / ref.max()))
    fw, fx, fy, ce = [], [], [], []
    for ky in range(-3, 4):
        for kx in range(-3, 4):
            q = width(render(S, 7, ky, kx, (wk, kxy)), 43, 43)
            fw.append(q['fwhm']); fx.append(q['fx']); fy.append(q['fy'])
            ce.append(max(abs(q['y0'] - (43 - ky / 7)), abs(q['x0'] - (43 - kx / 7))))
    st = lambda a: '%.4f / %.4f / %.4f' % (min(a), float(np.median(a)), max(a))
    log('OFFSETS, TinyTim path, G2V at (2040,1024), 49 offsets, METHOD FWHM min/median/max %s | fx %s | fy %s | max centre error %.4f px | spread %.1f %% of the narrowest' % (
        st(fw), st(fx), st(fy), max(ce), 100 * (max(fw) / min(fw) - 1)))
    log('PSFKIT SELFTEST END', time.strftime('%Y-%m-%d %H:%M:%S %z'), '| %.1f s' % (time.time() - t0))

if __name__ == '__main__':
    raise SystemExit(selftest(os.path.join(HOME, 'psfkit_selftest', 'psfkit_selftest_log.txt')))
