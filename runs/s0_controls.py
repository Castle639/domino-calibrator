#!/usr/bin/env python3
"""S0 - the controls, synthetic. Bar: archive/CALIBRATOR_2026-09-27.md, section S0 (committed before this ran).

(a) the pipeline against the toy (runs/s0a_toy_RUNLOG_2026-09-27.txt): dipole coma k/rho (1 + a cos t),
    no seeing, exact pixel integrals (render psf=None, sub=1), 301 x 301, estimator M with a known background 0.
(b) noiseless symmetric nulls over 36 symmetric sub-pixel phases: FWHM 1-6 px x {coma only, eta 0.1, eta 1,
    point} x M/G/P, Gaussian seeing; Moffat beta 2.5 at FWHM 3.
(c) noisy nulls: FWHM 1.5, 3 px x {eta 0.1, point} x SNR 20, 50; 200 realizations each, random sub-pixel phase,
    sky 100 e-/px, read noise 5 e-.
Usage: s0_controls.py a|b|c LOG [--workers N]
"""
import sys, os, time, argparse
import numpy as np
from multiprocessing import Pool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))      # the repository's root
from domino_calibrator import synth, shrink, moment_centroid, peak_quadratic, PUBLISHED_RADII

TOY = {0.1: 0.0498600547, 0.3: 0.1463611721, 0.6: 0.2740471206}   # c/r, s0a_toy_RUNLOG (18:00:38 UTC)
N_IMG, C0, SUB = 71, 35, 10
PH = [-0.45, -0.25, -0.05, 0.05, 0.25, 0.45]                          # symmetric sub-pixel centres (sub = 10)
PH_ALL = [-0.45 + 0.1 * i for i in range(10)]
FWHMS = [1.0, 1.5, 2.0, 3.0, 4.0, 6.0]
SKY, RN = 100.0, 5.0


def scene(fwhm, eta, psf_kind='gauss'):
    """(k, flux_n, model) for a symmetric scene; eta = F_n / F_coma(rho < FWHM) = F_n / (2 pi k FWHM)."""
    if eta == 'point':
        return 0.0, 1.0, 'none'
    k = 1.0
    return k, eta * 2 * np.pi * k * fwhm, 'dipole'


def psf_of(fwhm, kind):
    return ('gauss', fwhm) if kind == 'gauss' else ('moffat', fwhm, 2.5)


def measure(img, xt, yt, sky_known=None):
    """b0, b2, b6 for M and G, and P, relative to the truth (xt, yt). Start: the quadratic peak near the centre."""
    p = peak_quadratic(img, C0, C0)
    out = {'P': (p['x'] - xt, p['y'] - yt, p['ok'])}
    for est in ('M', 'G'):
        o = shrink(img, p['x'], p['y'], radii=PUBLISHED_RADII, estimator=est)
        out[est] = (o['x0'] - xt, o['y0'] - yt, o['x2'] - xt, o['y2'] - yt, o['x6'] - xt, o['y6'] - yt, o['nbad'])
    return out


def job_b(args):
    fwhm, eta, kind, px, py = args
    k, fn, model = scene(fwhm, eta)
    img, (xt, yt) = synth.render(N_IMG, C0 + px, C0 + py, flux_n=fn, k=k, a=0.0, model=model, psf=psf_of(fwhm, kind), sub=SUB)
    return (fwhm, eta, kind, px, py), measure(img, xt, yt)


def job_c(args):
    fwhm, eta, snr, seed = args
    rng = np.random.default_rng(seed)
    px, py = rng.choice(PH_ALL), rng.choice(PH_ALL)
    k, fn, model = scene(fwhm, eta)
    img1, (xt, yt) = synth.render(N_IMG, C0 + px, C0 + py, flux_n=fn, k=k, a=0.0, model=model, psf=('gauss', fwhm), sub=SUB)
    s = synth.snr_scale(img1, xt, yt, fwhm, snr, SKY, RN)
    img = synth.add_noise(s * img1, SKY, RN, rng)
    return (fwhm, eta, snr), measure(img, xt, yt)


def run_a(log):
    log('S0(a): pipeline M vs the toy; render psf=None sub=1 (exact pixel integrals), 301x301, known background 0')
    ok_all = True
    for (nx, ny) in [(150.0, 150.0), (150.3, 149.8)]:
        for a in (0.1, 0.3, 0.6):
            img, (xt, yt) = synth.render(301, nx, ny, k=1.0, a=a, model='dipole', psf=None, sub=1, snap=False)
            rs = [2.0, 4.0, 6.0, 20.0, 30.0, 40.0, 50.0, 60.0]
            cs = []
            for r in rs:
                o = moment_centroid(img, xt, yt, r, bkg=0.0, tol=1e-9, maxit=2000)
                cs.append((o['x'] - xt, o['y'] - yt, o['ok']))
            big = [i for i, r in enumerate(rs) if r >= 20]
            X = np.array([rs[i] for i in big]); Y = np.array([cs[i][0] for i in big])
            slope, icpt = np.polyfit(X, Y, 1)
            rat = {r: cs[i][0] / (TOY[a] * r) for i, r in enumerate(rs)}
            p20 = abs(rat[20.0] - 1) <= 0.01; p60 = abs(rat[60.0] - 1) <= 0.003
            pint = abs(icpt) <= 0.05; psl = abs(slope / TOY[a] - 1) <= 0.003
            ok = p20 and p60 and pint and psl and all(c[2] for c in cs)
            ok_all &= ok
            log('  nucleus (%.1f, %.1f) a %.1f | c/c_toy at r=2,4,6: %.5f %.5f %.5f | r=20..60: %s | y offsets max %.1e | fit 20-60: slope/toy %.6f intercept %+.5f px | %s' % (
                nx, ny, a, rat[2.0], rat[4.0], rat[6.0], ' '.join('%.6f' % rat[r] for r in rs[3:]),
                max(abs(c[1]) for c in cs), slope / TOY[a], icpt, 'PASS' if ok else 'FAIL'))
    log('S0(a) verdict: %s' % ('PASS' if ok_all else 'FAIL'))


def run_b(log, workers):
    log('S0(b): noiseless symmetric nulls, 36 symmetric phases; biases in px; mean over phases (the bar) and max |.| over phases (beside)')
    tasks = [(f, e, 'gauss', px, py) for f in FWHMS for e in (0.0, 0.1, 1.0, 'point') for px in PH for py in PH]
    tasks += [(3.0, e, 'moffat', px, py) for e in (0.0, 0.1, 1.0, 'point') for px in PH for py in PH]
    t0 = time.time()
    with Pool(workers) as pool:
        res = pool.map(job_b, tasks, chunksize=4)
    log('  %d renders+measures in %.0f s' % (len(res), time.time() - t0))
    groups = {}
    for key, m in res:
        groups.setdefault(key[:3], []).append(m)
    ok_all = True
    for g in sorted(groups, key=lambda t: (t[2], t[0], str(t[1]))):
        ms = groups[g]
        line = '  FWHM %.1f %-6s %-7s' % (g[0], g[2], ('eta ' + str(g[1])) if g[1] != 'point' else 'point')
        for est in ('M', 'G'):
            A = np.array([m[est][:6] for m in ms]); nbad = sum(m[est][6] for m in ms)
            mean = np.abs(A.mean(axis=0)).max(); mx0 = np.hypot(A[:, 0], A[:, 1]).max(); mx2 = np.hypot(A[:, 2], A[:, 3]).max()
            tol = 1e-5 if est == 'M' else 1e-4
            ok = mean <= tol and nbad == 0
            ok_all &= ok
            line += ' | %s mean %.1e max|b0| %.4f max|b2| %.4f nbad %d %s' % (est, mean, mx0, mx2, nbad, 'ok' if ok else 'FAIL')
        P = np.array([m['P'][:2] for m in ms]); pok = sum(m['P'][2] for m in ms)
        okp = np.abs(P.mean(axis=0)).max() <= 1e-4
        ok_all &= okp
        line += ' | P mean %.1e max|b| %.4f ok %d/%d %s' % (np.abs(P.mean(axis=0)).max(), np.hypot(P[:, 0], P[:, 1]).max(), pok, len(ms), 'ok' if okp else 'FAIL')
        log(line)
    log('S0(b) verdict: %s' % ('PASS' if ok_all else 'FAIL'))


def run_c(log, workers):
    log('S0(c): noisy nulls, 200 realizations, random sub-pixel phase; mean +- SE (px) per axis; bar |mean| <= 3.5 SE')
    tasks = [(f, e, s, 1000 * i + int(10 * f) + (7 if e == 'point' else 3) * 100000 + int(s) * 10000000)
             for f in (1.5, 3.0) for e in (0.1, 'point') for s in (20.0, 50.0) for i in range(200)]
    t0 = time.time()
    with Pool(workers) as pool:
        res = pool.map(job_c, tasks, chunksize=8)
    log('  %d realizations in %.0f s' % (len(res), time.time() - t0))
    groups = {}
    for key, m in res:
        groups.setdefault(key, []).append(m)
    ok_all, worst = True, 0.0
    for g in sorted(groups, key=lambda t: (t[0], str(t[1]), t[2])):
        ms = groups[g]
        line = '  FWHM %.1f %-7s SNR %3.0f' % (g[0], ('eta ' + str(g[1])) if g[1] != 'point' else 'point', g[2])
        for est in ('M', 'G'):
            A = np.array([m[est][:4] for m in ms]); nbad = sum(m[est][6] > 0 for m in ms)
            good = np.all(np.isfinite(A), axis=1)
            A = A[good]
            mu, se = A.mean(axis=0), A.std(axis=0, ddof=1) / np.sqrt(len(A))
            z = np.abs(mu / se); worst = max(worst, z.max())
            ok = bool(np.all(z <= 3.5))
            ok_all &= ok
            s0, s2 = np.hypot(*A[:, 0:2].std(axis=0, ddof=1)), np.hypot(*A[:, 2:4].std(axis=0, ddof=1))
            line += ' | %s b0 (%+.4f+-%.4f, %+.4f+-%.4f) b2 (%+.4f+-%.4f, %+.4f+-%.4f) max z %.2f | sd b0 %.4f b2 %.4f ratio %.2f | runs w/ bad radii %d, NaN %d %s' % (
                est, mu[0], se[0], mu[1], se[1], mu[2], se[2], mu[3], se[3], z.max(), s0, s2, s0 / s2, nbad, int((~good).sum()), 'ok' if ok else 'FAIL')
        log(line)
    log('S0(c) verdict: %s (largest |mean|/SE %.2f)' % ('PASS' if ok_all else 'FAIL', worst))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('part'); ap.add_argument('log'); ap.add_argument('--workers', type=int, default=4)
    A = ap.parse_args()
    f = open(A.log, 'w')
    def log(s):
        print(s, flush=True); f.write(s + '\n'); f.flush()
    log('# S0(%s) %s | runs/s0_controls.py | commit %s' % (A.part, time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        os.popen('git -C %s log -1 --format=%%h' % os.path.dirname(os.path.abspath(__file__))).read().strip()))
    t0 = time.time()
    {'a': lambda: run_a(log), 'b': lambda: run_b(log, A.workers), 'c': lambda: run_c(log, A.workers)}[A.part]()
    log('# done in %.0f s' % (time.time() - t0))
