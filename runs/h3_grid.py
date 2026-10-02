#!/usr/bin/env python3
"""H1 (null: each frame symmetrised about its HST reference) and H3 (the real frames): Hubble's 3I degraded to ground
seeing and pixels, measured with the shrinking aperture. Bars: archive/CALIBRATOR_2026-09-27.md, H1 and H3.

Input: H0's sky images ($HOME/calib_work/sky_<root>.npz: 0.02" north-up east-left, the HST reference = G's zero-aperture
position at HST resolution, at the centre pixel m) and H0_FRAMES_2026-09-27.json (visits, Horizons).
Grid: the 26 (seeing, ground pixel) pairs fixed in the H0 bar. Phases: 4 x 4 fine offsets per ground pixel, in exact
mirror pairs (o' = 2m + 1 - o mod n), so the phase set is symmetric about the reference.
Estimators: G with a known background (the frame's zero, MDRIZSKY-subtracted), M (background-free fixed point), P;
G with the published annulus wherever the whole 2.5r-5r annulus at r = 6 px is finite.
Noisy (H3 only): SNR 100 and 20 (flux in r = FWHM), 5 realisations per frame and pair and SNR (30 per visit),
random mirror-set phase, sky 100 e-/px, read noise 5 e-.
Usage: h3_grid.py null|real LOG [--frames N]
"""
import sys, os, time, json, argparse
import numpy as np
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.dirname(HERE))       # the repository's root, where domino_calibrator is
from domino_calibrator import synth, shrink, peak_quadratic, PUBLISHED_RADII
from domino_calibrator import degrade as D

WORK = os.path.join(os.environ['HOME'], 'calib_work')
S = 0.02
SEEING = {0.7: [0.24, 0.44, 0.70], 1.0: [0.24, 0.44, 0.70, 1.00], 1.5: [0.24, 0.44, 0.70, 1.00, 1.50],
          2.0: [0.44, 0.70, 1.00, 1.50, 2.00], 3.0: [0.44, 0.70, 1.00, 1.50, 2.00], 4.0: [0.70, 1.00, 1.50, 2.00]}
SNRS = [100.0, 20.0]
NREAL = 5
SKY, RN = 100.0, 5.0
MODE = None


def mirror_offsets(m, n):
    """Four fine offsets per axis whose ground phases are two exact mirror pairs (~+-1/8, ~+-3/8)."""
    out = []
    for want in (0.125, 0.375):
        o, _ = D.phase_offset(float(m), n, want)
        out += [o, (2 * m + 1 - o) % n]
    return out


def meas(g, xg, yg, fwhm_px):
    c0x, c0y = int(round(xg)), int(round(yg))
    p = peak_quadratic(g, c0x, c0y)
    out = {'P': (p['x'] - xg, p['y'] - yg)}
    for est, bk in (('G', 0.0), ('M', 0.0)):
        o = shrink(g, p['x'], p['y'], radii=PUBLISHED_RADII, estimator=est, background=bk)
        out[est] = [o['x0'] - xg, o['y0'] - yg, o['x2'] - xg, o['y2'] - yg, o['x6'] - xg, o['y6'] - yg, int(o['nbad'])]
        out[est + 'c'] = [(o['x'] - xg).tolist(), (o['y'] - yg).tolist()]
    yy, xx = np.indices(g.shape)
    ann = np.hypot(xx - xg, yy - yg) <= 30.5 + 1.0
    inside = xg - 31.5 >= 0 and yg - 31.5 >= 0 and xg + 31.5 <= g.shape[1] - 1 and yg + 31.5 <= g.shape[0] - 1
    if inside and np.all(np.isfinite(g[ann])):
        o = shrink(g, p['x'], p['y'], radii=PUBLISHED_RADII, estimator='G', background='annulus')
        out['Ga'] = [o['x0'] - xg, o['y0'] - yg, o['x2'] - xg, o['y2'] - yg, o['x6'] - xg, o['y6'] - yg, int(o['nbad'])]
    return out


def job(args):
    root, fw, seed = args
    z = np.load(os.path.join(WORK, 'sky_%s.npz' % root))
    img = z['sky'].astype(np.float64); m = int(z['m'])
    if MODE == 'null':
        img = 0.5 * (img + img[::-1, ::-1])
    conv = D.convolve(img, S, fw)
    rng = np.random.default_rng(seed)
    res = []
    for gs in SEEING[fw]:
        n = D.ground_factor(gs, S)
        offs = mirror_offsets(m, n)
        fpx = np.hypot(fw, 0.071) / gs
        for ox in offs:
            for oy in offs:
                g, (xg, yg) = D.bin_phase(conv, (float(m), float(m)), n, (ox, oy))
                try:
                    res.append(dict(root=root, fw=fw, gs=gs, kind='noiseless', ph=(ox, oy), m=meas(g, xg, yg, fpx)))
                except Exception as e:          # one failure is recorded, not a crash (S1 run 1)
                    res.append(dict(root=root, fw=fw, gs=gs, kind='noiseless', ph=(ox, oy), error=repr(e)))
        if MODE == 'real':
            for snr in SNRS:
                for i in range(NREAL):
                    ox, oy = offs[rng.integers(4)], offs[rng.integers(4)]
                    g1, (xg, yg) = D.bin_phase(conv, (float(m), float(m)), n, (ox, oy))
                    fin = np.isfinite(g1)
                    s = synth.snr_scale(np.where(fin, g1, 0.0), xg, yg, fpx, snr, SKY, RN)
                    g = synth.add_noise(np.where(fin, s * g1, 0.0), SKY, RN, rng) - SKY
                    g[~fin] = np.nan
                    try:
                        r = meas(g, xg, yg, fpx)
                    except Exception as e:
                        res.append(dict(root=root, fw=fw, gs=gs, kind='snr%d' % snr, ph=(ox, oy), error=repr(e))); continue
                    for k in ('Gc', 'Mc'):
                        r.pop(k, None)
                    res.append(dict(root=root, fw=fw, gs=gs, kind='snr%d' % snr, ph=(ox, oy), m=r))
    return res


if __name__ == '__main__':
    ap = argparse.ArgumentParser(); ap.add_argument('mode'); ap.add_argument('log'); ap.add_argument('--frames', type=int, default=0)
    A = ap.parse_args()
    MODE = A.mode
    f = open(A.log, 'w')
    def log(s):
        print(s, flush=True); f.write(s + '\n'); f.flush()
    log('# H%s %s | runs/h3_grid.py %s | commit %s' % ('1' if MODE == 'null' else '3', time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()), MODE,
        os.popen('git -C %s log -1 --format=%%h' % ROOT).read().strip()))
    H0 = json.load(open(os.path.join(HERE, 'H0_FRAMES_2026-09-27.json')))
    frames = H0['frames']
    if MODE == 'null':
        seen, pick = set(), []
        for d in frames:
            if d['visit'] not in seen:
                seen.add(d['visit']); pick.append(d['root'])
        roots = pick
    else:
        roots = [d['root'] for d in frames]
    if A.frames:
        roots = roots[:A.frames]
    log('# frames: %s' % ' '.join(roots))
    tasks = [(r, fw, 1000 * i + int(fw * 10)) for i, r in enumerate(roots) for fw in SEEING]
    t0 = time.time()
    out = []
    with Pool(4) as pool:
        for res in pool.imap_unordered(job, tasks):
            out.extend(res)
    errs = [o for o in out if 'error' in o]
    log('# %d measurements in %.0f s (%d errors%s)' % (len(out), time.time() - t0, len(errs), (': first ' + errs[0]['error'][:120]) if errs else ''))
    out = [o for o in out if 'error' not in o]
    json.dump(out, open(os.path.join(HERE, 'H%s_RAW_2026-09-27.json' % ('1' if MODE == 'null' else '3')), 'w'))
    # ---- the null's bar ----
    if MODE == 'null':
        ok = True
        log('# per frame and pair: phase-mean |b| max over (b0, b2, b6; x, y) in ground px for G, M; P | max per-phase |b0|, |b2| beside')
        for r in roots:
            for fw in SEEING:
                for gs in SEEING[fw]:
                    ms = [o['m'] for o in out if o['root'] == r and o['fw'] == fw and o['gs'] == gs and o['kind'] == 'noiseless']
                    line = '%s seeing %.1f %.2f"/px FWHM %.2f px' % (r, fw, gs, np.hypot(fw, 0.071) / gs)
                    for est, tol in (('G', 2e-4), ('M', 1e-5), ('Ga', 2e-4)):
                        if est not in ms[0]:
                            continue
                        Aa = np.array([x[est][:6] for x in ms]); mu = np.abs(Aa.mean(axis=0)).max()
                        nb = sum(x[est][6] for x in ms)
                        good = mu <= tol and nb == 0
                        ok &= good
                        line += ' | %s %.1e (max|b0| %.4f max|b2| %.4f) %s' % (est, mu, np.hypot(Aa[:, 0], Aa[:, 1]).max(), np.hypot(Aa[:, 2], Aa[:, 3]).max(), 'ok' if good else 'FAIL')
                    P = np.array([x['P'] for x in ms]); mp = np.abs(P.mean(axis=0)).max()
                    ok &= mp <= 1e-6
                    line += ' | P %.1e (max %.4f) %s' % (mp, np.hypot(P[:, 0], P[:, 1]).max(), 'ok' if mp <= 1e-6 else 'FAIL')
                    log(line)
        log('# H1 verdict: %s' % ('PASS' if ok else 'FAIL'))
    log('# done in %.0f s' % (time.time() - t0))
