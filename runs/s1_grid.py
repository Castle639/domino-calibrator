#!/usr/bin/env python3
"""S1 - the synthetic bias grid. Bar: archive/CALIBRATOR_2026-09-27.md, section S1 (committed before this ran).

Truth = the nucleus. Asymmetry toward +x (theta_a = 0): a positive b is toward the bright side.
Grid: FWHM 1.0, 1.5, 2.0, 3.0, 4.0, 6.0 px (Gaussian seeing) x coma {dipole a 0.1, dipole a 0.3, grow a 0.3
rho_s 2 FWHM, fade a 0.3 rho_s 2 FWHM} x eta {0, 0.1, 1} (eta = F_n / F_coma(rho < FWHM), symmetric part).
Noiseless: 36 symmetric sub-pixel phases, phase-mean. Noisy: SNR 100 and 30, 108 realizations (3 per phase),
sky 100 e-/px, read noise 5 e-. Estimators M, G (published radii, annulus background) and P.
Outputs: the log; runs/S1_RESULTS_2026-09-27.json (every number the log summarises, and the mean
curves x(r)).
"""
import sys, os, time, json, argparse
import numpy as np
from multiprocessing import Pool

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))      # the repository's root
from domino_calibrator import synth, shrink, peak_quadratic, PUBLISHED_RADII

N_IMG, C0, SUB = 71, 35, 10
PH = [-0.45, -0.25, -0.05, 0.05, 0.25, 0.45]
PHASES = [(px, py) for px in PH for py in PH]
FWHMS = [1.0, 1.5, 2.0, 3.0, 4.0, 6.0]
MODELS = [('dipole', 0.1, None), ('dipole', 0.3, None), ('grow', 0.3, 2.0), ('fade', 0.3, 2.0)]   # rho_s in FWHM
ETAS = [0.0, 0.1, 1.0]
SNRS = [100.0, 30.0]
NREAL = 108
SKY, RN = 100.0, 5.0
CACHE = {}


def cfg_key(f, m, e):
    return '%s%.1f|FWHM%.1f|eta%.1f' % (m[0], m[1], f, e) + ('|rs%.0fF' % m[2] if m[2] else '')


def do_render(args):
    f, m, e, (px, py) = args
    k = 1.0
    fn = e * 2 * np.pi * k * f
    rho_s = m[2] * f if m[2] else None
    img, (xt, yt) = synth.render(N_IMG, C0 + px, C0 + py, flux_n=fn, k=k, a=m[1], theta=0.0, model=m[0], rho_s=rho_s,
                                 psf=('gauss', f), sub=SUB)
    return (cfg_key(f, m, e), px, py), (img, xt, yt)


def measure(img, xt, yt, curves=False):
    p = peak_quadratic(img, C0, C0)
    out = {'P': [p['x'] - xt, p['y'] - yt, bool(p['ok'])]}
    for est in ('M', 'G'):
        o = shrink(img, p['x'], p['y'], radii=PUBLISHED_RADII, estimator=est)
        out[est] = [o['x0'] - xt, o['y0'] - yt, o['x2'] - xt, o['y2'] - yt, o['x6'] - xt, o['y6'] - yt, o['sx'], int(o['nbad'])]
        if curves:
            out[est + '_curve'] = [(o['x'] - xt).tolist(), (o['y'] - yt).tolist()]
    return out


def do_noiseless(key):
    img, xt, yt = CACHE[key]
    try:
        return key, measure(img, xt, yt, curves=True)
    except Exception as e:                      # S1 run 1 died on one uncaught error: now one task fails, not the run
        return key, {'error': repr(e)}


def do_noisy(args):
    key, snr, seed = args
    img1, xt, yt = CACHE[key]
    fw = float(key[0].split('|')[1][4:])
    rng = np.random.default_rng(seed)
    s = synth.snr_scale(img1, xt, yt, fw, snr, SKY, RN)
    img = synth.add_noise(s * img1, SKY, RN, rng)
    try:
        return (key[0], snr), measure(img, xt, yt)
    except Exception as e:
        return (key[0], snr), {'error': repr(e)}


def classify(b0, b2, rms0_30, rms2_30, rms0_100, rms2_100):
    if abs(b0) > 0.75 * abs(b2) or rms0_100 > rms2_100:
        return 'FAILS'
    if abs(b0) <= 0.25 * abs(b2) and rms0_30 <= rms2_30:
        return 'WORKS'
    return 'HELPS'


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('log'); ap.add_argument('--workers', type=int, default=4)
    A = ap.parse_args()
    f = open(A.log, 'w')
    def log(s):
        print(s, flush=True); f.write(s + '\n'); f.flush()
    here = os.path.dirname(os.path.abspath(__file__))
    log('# S1 %s | runs/s1_grid.py | commit %s' % (time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        os.popen('git -C %s log -1 --format=%%h' % here).read().strip()))
    t0 = time.time()
    tasks = [(fw, m, e, ph) for fw in FWHMS for m in MODELS for e in ETAS for ph in PHASES]
    with Pool(A.workers) as pool:
        for key, val in pool.imap_unordered(do_render, tasks, chunksize=4):
            CACHE[key] = val
    log('# stage 1: %d renders in %.0f s' % (len(CACHE), time.time() - t0))
    t1 = time.time()
    with Pool(A.workers) as pool:                       # forked after CACHE is filled: the workers inherit it
        noiseless = dict(pool.map(do_noiseless, list(CACHE), chunksize=4))
        nerr = sum('error' in v for v in noiseless.values())
        log('# stage 2: %d noiseless measures in %.0f s (%d errors)' % (len(noiseless), time.time() - t1, nerr))
        work = os.path.join(os.environ['HOME'], 'calib_work'); os.makedirs(work, exist_ok=True)
        json.dump({'%s|%+.2f|%+.2f' % k: v for k, v in noiseless.items()}, open(os.path.join(work, 's1_stage2.json'), 'w'))
        t2 = time.time()
        ntasks = []
        for fw in FWHMS:
            for m in MODELS:
                for e in ETAS:
                    ck = cfg_key(fw, m, e)
                    for si, snr in enumerate(SNRS):
                        for i in range(NREAL):
                            px, py = PHASES[i % len(PHASES)]
                            seed = int(fw * 10) * 1000003 + MODELS.index(m) * 10007 + ETAS.index(e) * 101 + si * 13 + i * 7919
                            ntasks.append(((ck, px, py), snr, seed))
        noisy, nerr3 = {}, 0
        for key, val in pool.imap_unordered(do_noisy, ntasks, chunksize=8):
            if 'error' in val:
                nerr3 += 1; continue
            noisy.setdefault(key, []).append(val)
        log('# stage 3: %d noisy measures in %.0f s (%d errors, left out)' % (len(ntasks), time.time() - t2, nerr3))
        json.dump({'%s|%d' % k: v for k, v in noisy.items()}, open(os.path.join(work, 's1_stage3.json'), 'w'))
    # ---- summaries ----
    res = {}
    log('# per configuration. Noiseless phase-means (px): b0, b2, b6 along the asymmetry (x); |y| max beside. Noisy: RMS of the 2-D error (px)')
    log('# class (G, the bar): WORKS |b0| <= 0.25|b2| and RMS0 <= RMS2 at SNR 30; FAILS |b0| > 0.75|b2| or RMS0 > RMS2 at SNR 100; else HELPS')
    for fw in FWHMS:
        for m in MODELS:
            for e in ETAS:
                ck = cfg_key(fw, m, e)
                ms = [noiseless[(ck, px, py)] for (px, py) in PHASES if 'error' not in noiseless[(ck, px, py)]]
                R = {'FWHM': fw, 'model': m[0], 'a': m[1], 'rho_s_FWHM': m[2], 'eta': e}
                for est in ('M', 'G'):
                    Aa = np.array([x[est][:7] for x in ms])
                    mu = Aa.mean(axis=0)
                    R[est] = dict(b0=mu[0], b2=mu[2], b6=mu[4], y_max=float(np.abs(mu[[1, 3, 5]]).max()), slope=mu[6],
                                  phase_amp_b0=float(np.abs(Aa[:, 0] - mu[0]).max()), nbad=int(sum(x[est][7] for x in ms)),
                                  curve=np.mean([x[est + '_curve'][0] for x in ms], axis=0).tolist())
                    for snr in SNRS:
                        vs = noisy[(ck, snr)]
                        B = np.array([v[est][:6] for v in vs]); ok = np.all(np.isfinite(B), axis=1); B = B[ok]
                        R[est]['snr%d' % snr] = dict(
                            mean_b0=float(B[:, 0].mean()), se_b0=float(B[:, 0].std(ddof=1) / np.sqrt(len(B))),
                            mean_b2=float(B[:, 2].mean()), se_b2=float(B[:, 2].std(ddof=1) / np.sqrt(len(B))),
                            rms0=float(np.sqrt((B[:, 0] ** 2 + B[:, 1] ** 2).mean())), rms2=float(np.sqrt((B[:, 2] ** 2 + B[:, 3] ** 2).mean())),
                            sd0=float(np.hypot(*B[:, 0:2].std(axis=0, ddof=1))), sd2=float(np.hypot(*B[:, 2:4].std(axis=0, ddof=1))),
                            n=int(len(B)), nbad_runs=int(sum(v[est][7] > 0 for v in vs)))
                    s30, s100 = R[est]['snr30'], R[est]['snr100']
                    R[est]['class'] = classify(R[est]['b0'], R[est]['b2'], s30['rms0'], s30['rms2'], s100['rms0'], s100['rms2'])
                    R[est] = {k: (float(v) if isinstance(v, (np.floating,)) else v) for k, v in R[est].items()}
                P = np.array([x['P'][:2] for x in ms]).mean(axis=0)
                R['P'] = dict(bx=float(P[0]), by=float(P[1]))
                res[ck] = R
                g, mm = R['G'], R['M']
                log('%-26s | G b0 %+.4f b2 %+.4f b6 %+.4f (y %.0e) b0/b2 %+.3f slope %+.4f | RMS0/RMS2 SNR100 %.3f/%.3f SNR30 %.3f/%.3f | %-5s || M b0 %+.4f b2 %+.4f b6 %+.4f b0/b2 %+.3f | RMS SNR30 %.3f/%.3f | %-5s || P %+.4f' % (
                    ck, g['b0'], g['b2'], g['b6'], g['y_max'], g['b0'] / g['b2'] if g['b2'] else np.nan, g['slope'],
                    g['snr100']['rms0'], g['snr100']['rms2'], g['snr30']['rms0'], g['snr30']['rms2'], g['class'],
                    mm['b0'], mm['b2'], mm['b6'], mm['b0'] / mm['b2'] if mm['b2'] else np.nan, mm['snr30']['rms0'], mm['snr30']['rms2'], mm['class'],
                    R['P']['bx']))
    json.dump(res, open(os.path.join(here, 'S1_RESULTS_2026-09-27.json'), 'w'), indent=0)
    tally = {}
    for R in res.values():
        for est in ('G', 'M'):
            tally.setdefault(est, {}).setdefault(R[est]['class'], 0)
            tally[est][R[est]['class']] += 1
    log('# tally: %s' % json.dumps(tally))
    nbad = sum(R[e]['nbad'] for R in res.values() for e in ('M', 'G'))
    log('# unconverged radii, noiseless: %d; noisy runs with any: %s' % (nbad, {e: sum(R[e]['snr%d' % s]['nbad_runs'] for R in res.values() for s in SNRS) for e in ('M', 'G')}))
    log('# done in %.0f s' % (time.time() - t0))
