#!/usr/bin/env python3
"""H2 - injection. Bar: archive/CALIBRATOR_2026-09-27.md, section H2 (committed before this ran).

(a) How far is HST's own zero-aperture position from a known nucleus? Synthetic comets on the HST detector grid
    (0.0396"/px), TinyTim F350LP at (758, 814), despace 0.001 um, SUB=5, charge-diffusion kernels after binning
    (TinyTim's own path); 101 x 101 px, 16 symmetric sub-pixel phases; G, M on the published radii (annulus), P.
(b) The degrade chain against direct rendering: the same sky scene rendered (1) on the 0.02" grid with a 0.071"
    Gaussian (HST) and pushed through domino_calibrator.degrade, (2) directly at the ground scale with a Gaussian of
    FWHM sqrt(seeing^2 + 0.071^2) (domino_calibrator.synth); 10 x 10 near-uniform phases each (the chain can only reach
    phases in steps of 1/n, so both sides average a uniform grid instead of matching phases); G (known bkg) and M.
Usage: h2_injection.py a|b LOG
"""
import sys, os, time, json, argparse
import numpy as np
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.dirname(HERE))       # the repository's root, where domino_calibrator is
from domino_calibrator import synth, shrink, peak_quadratic, PUBLISHED_RADII
from domino_calibrator import degrade as D

MAS = 39.6        # mas per HST px (IDCSCALE 0.03962)
PSF = None
SYMPSF = '--sympsf' in sys.argv


def meas(img, xt, yt, c0, background='annulus'):
    p = peak_quadratic(img, c0, c0)
    out = {'P': (p['x'] - xt, p['y'] - yt)}
    for est in ('G', 'M'):
        o = shrink(img, p['x'], p['y'], radii=PUBLISHED_RADII, estimator=est, background=background)
        out[est] = (o['x0'] - xt, o['y0'] - yt, o['x2'] - xt, o['y2'] - yt, o['x6'] - xt, o['y6'] - yt, o['nbad'])
    return out


# ---------------- (a) ----------------
A_MODELS = [('sym', 'dipole', 0.0, None, 0.2), ('dip0.1', 'dipole', 0.1, None, 0.2),
            ('dip0.3 eta0', 'dipole', 0.3, None, 0.0), ('dip0.3', 'dipole', 0.3, None, 0.2), ('dip0.3 eta1', 'dipole', 0.3, None, 1.0),
            ('fade rs5', 'fade', 0.3, 5.0, 0.2), ('fade rs25', 'fade', 0.3, 25.0, 0.2),
            ('grow rs5', 'grow', 0.3, 5.0, 0.2), ('grow rs25', 'grow', 0.3, 25.0, 0.2)]
A_PH = [-0.4, -0.2, 0.2, 0.4]


def job_a(args):
    name, model, a, rs, eta, px, py = args
    fn = eta * 2 * np.pi * 1.0 * 1.8
    img, (xt, yt) = synth.render(101, 50 + px, 50 + py, flux_n=fn, k=1.0, a=a, model=model, rho_s=rs,
                                 psf=('array', PSF['S']), sub=PSF['sub'], post=PSF['kernels'])
    return name, meas(img, xt, yt, 50)


def run_a(log):
    global PSF
    from domino_calibrator.hstpsf import tinytim_psf
    PSF = tinytim_psf(758, 814, despace=0.001, sub=5)
    if SYMPSF:     # H2(a') - the null with TinyTim's optical PSF made point-symmetric (18:28 UTC diagnosis)
        PSF = dict(PSF, S=0.5 * (PSF['S'] + PSF['S'][::-1, ::-1]))
    log('TinyTim (758, 814) despace 0.001 um SUB 5: %s, Z4 line %s, point-symmetrised: %s' % (PSF['S'].shape, PSF['z4'], SYMPSF))
    tasks = [(m[0],) + m[1:] + (px, py) for m in A_MODELS for px in A_PH for py in A_PH]
    with Pool(4) as pool:
        res = pool.map(job_a, tasks)
    ok = True
    log('(a) offsets from the nucleus at HST resolution, phase-mean over 16 phases (mas; x along the asymmetry) | max over phases')
    for m in A_MODELS:
        ms = [r for n, r in res if n == m[0]]
        line = '  %-12s eta %.1f' % (m[0], m[4])
        for est in ('G', 'M'):
            Aa = np.array([r[est][:6] for r in ms]) * MAS
            mu = Aa.mean(axis=0); mx = np.abs(Aa).max(axis=0)
            nb = sum(r[est][6] for r in ms)
            line += ' | %s b0 (%+.2f, %+.2f) b2 (%+.2f, %+.2f) b6 (%+.2f, %+.2f) max|b0x| %.2f nbad %d' % (est, mu[0], mu[1], mu[2], mu[3], mu[4], mu[5], mx[0], nb)
            if m[0] == 'sym':
                ok &= bool(np.abs(mu).max() <= 1e-4 * MAS)
        P = np.array([r['P'] for r in ms]) * MAS
        line += ' | P (%+.2f, %+.2f) max %.2f' % (P[:, 0].mean(), P[:, 1].mean(), np.abs(P[:, 0]).max())
        if m[0] == 'sym':
            ok &= bool(np.abs(P.mean(axis=0)).max() <= 1e-4 * MAS)
        log(line)
    log('(a) null (sym) phase-mean <= 1e-4 px: %s' % ('PASS' if ok else 'FAIL'))


# ---------------- (b) ----------------
S_FINE, N_FINE, C_FINE, HST_FWHM = 0.02, 2401, 1200, 0.071
K_ARC = 1.0e4                     # coma: K_ARC / rho" per arcsec^2
B_MODELS = [('dip0.3', 'dipole', 0.3, None), ('fade rs2"', 'fade', 0.3, 2.0)]
B_CFG = [(1.0, 0.24), (1.0, 0.44), (1.0, 1.00), (3.0, 0.70), (3.0, 1.50), (3.0, 2.00)]
B_PH_DIRECT = [-0.45 + 0.1 * i for i in range(10)]          # every sub = 10 centre: a uniform phase grid
B_PH_CHAIN = list(range(10))                                  # fine offsets round(k n / 10): near-uniform phases
FN_ARC = 0.1 * 2 * np.pi * K_ARC * 1.0     # eta 0.1 of the coma inside 1"
FINE = {}


def job_b_direct(args):
    mname, model, a, rs, fw, gs, px, py = args
    fe = np.hypot(fw, HST_FWHM) / gs
    img, (xt, yt) = synth.render(69, 34 + px, 34 + py, flux_n=FN_ARC, k=K_ARC * gs, a=a, model=model,
                                 rho_s=(rs / gs if rs else None), psf=('gauss', fe), sub=10)
    return (mname, fw, gs), meas(img, xt, yt, 34, background=0.0)


def job_b_chain(args):
    mname, fw, gs, kx, ky = args
    conv, (xt, yt) = FINE[(mname, fw)]
    n = D.ground_factor(gs, S_FINE)
    ox, oy = int(round(kx * n / 10.0)) % n, int(round(ky * n / 10.0)) % n
    g, (xg, yg) = D.bin_phase(conv, (xt, yt), n, (ox, oy))
    return (mname, fw, gs), meas(g, xg, yg, int(round(xg)), background=0.0)


def run_b(log):
    t0 = time.time()
    for m in B_MODELS:
        img, (xt, yt) = synth.render(N_FINE, C_FINE + 0.25, C_FINE + 0.25, flux_n=FN_ARC, k=K_ARC * S_FINE, a=m[2], model=m[1],
                                     rho_s=(m[3] / S_FINE if m[3] else None), psf=('gauss', HST_FWHM / S_FINE), sub=2)
        for fw in sorted(set(c[0] for c in B_CFG)):
            FINE[(m[0], fw)] = (D.convolve(img, S_FINE, fw), (xt, yt))
        log('  fine render %s: %.0f s so far' % (m[0], time.time() - t0))
    chain = [(m[0], fw, gs, kx, ky) for m in B_MODELS for (fw, gs) in B_CFG for kx in B_PH_CHAIN for ky in B_PH_CHAIN]
    direct = [(m[0], m[1], m[2], m[3], fw, gs, px, py) for m in B_MODELS for (fw, gs) in B_CFG for px in B_PH_DIRECT for py in B_PH_DIRECT]
    with Pool(4) as pool:
        rc = pool.map(job_b_chain, chain)
        rd = pool.map(job_b_direct, direct)
    ok = True
    log('(b) chain vs direct, phase-means over 10 x 10 near-uniform phases (ground px); bar |chain - direct| <= 0.005 + 0.03 |direct| on b0, b2, b6 (x), |y| <= 0.005')
    for m in B_MODELS:
        for (fw, gs) in B_CFG:
            key = (m[0], fw, gs)
            line = '  %-9s seeing %.1f" %.2f"/px (FWHM %.2f px)' % (m[0], fw, gs, np.hypot(fw, HST_FWHM) / gs)
            for est in ('G', 'M'):
                C = np.array([r[est][:6] for k, r in rc if k == key]).mean(axis=0)
                Dd = np.array([r[est][:6] for k, r in rd if k == key]).mean(axis=0)
                d = C - Dd
                tol = 0.005 + 0.03 * np.abs(Dd[[0, 2, 4]])
                good = bool(np.all(np.abs(d[[0, 2, 4]]) <= tol) and np.all(np.abs(C[[1, 3, 5]]) <= 0.005) and np.all(np.abs(Dd[[1, 3, 5]]) <= 0.005))
                ok &= good
                line += ' | %s chain b0 %+.4f b2 %+.4f b6 %+.4f direct %+.4f %+.4f %+.4f %s' % (est, C[0], C[2], C[4], Dd[0], Dd[2], Dd[4], 'ok' if good else 'FAIL')
            log(line)
    log('(b) verdict: %s' % ('PASS' if ok else 'FAIL'))


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('part'); ap.add_argument('log'); ap.add_argument('--sympsf', action='store_true')
    A = ap.parse_args()
    f = open(A.log, 'w')
    def log(s):
        print(s, flush=True); f.write(s + '\n'); f.flush()
    log('# H2(%s) %s | runs/h2_injection.py | commit %s' % (A.part, time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        os.popen('git -C %s log -1 --format=%%h' % ROOT).read().strip()))
    t0 = time.time()
    (run_a if A.part == 'a' else run_b)(log)
    log('# done in %.0f s' % (time.time() - t0))
