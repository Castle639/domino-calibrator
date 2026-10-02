#!/usr/bin/env python3
"""H4 - the aperture range in arcsec and in units of the seeing, on H3's frames and grid.
Bar: archive/CALIBRATOR_ARCSEC_2026-09-27.md, section H4 (committed before the run).

The first room's Next #1: at >= 0.70"/px the published 2.0-6.0 px radii span 1.4-12" and, for 3I, the
extrapolation fails. Does it survive if the 41 radii are fixed in arcsec, or in units of the seeing?
Variants, 41 radii each, ascending, warm-started from P exactly as H3:
  PX   2.0-6.0 px, the published radii (H3's; here the control)
  ARC  0.88-2.64", the published radii at 0.44"/px, the coarsest professional scale: (2.0-6.0) * 0.44 / gs px
  SEE  1.0-3.0 FWHM, FWHM = sqrt(seeing^2 + 0.071^2) / gs px (H3's fpx)
Estimators: G (known background, the frame's zero) and M, as H3; P as H3. A G fit that scipy cannot make (fewer
pixels in the aperture than its four parameters) is an unconverged radius, not a crash.
Noiseless: H3's 4 x 4 mirror-pair phases. Noisy: SNR 100 and 20, NREAL per frame, pair and SNR, H3's noise model
(sky 100 e-/px, read noise 5 e-, flux in r = FWHM); each noisy image gets G and M at r = 2 px (the class baseline,
as H3) and the ARC and SEE sequences.
Usage: h4_arcsec.py probe|null|smoke|real LOG [--frames N] [--nreal N] [--raw PATH]
  probe: the first frame of visit 22, point-symmetrised (no bias is printed), one phase per pair: timing and
         convergence only, to size the run.
  null:  the first frame of each visit, point-symmetrised (as H1): control C3.
  smoke: real's path on point-symmetrised frames (no 3I information), to run the report end to end before the data.
  real:  the frames (the first of each visit with --frames 5), noiseless and noisy.
"""
import sys, os, time, json, argparse, gzip
import numpy as np
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.dirname(HERE))       # the repository's root, where domino_calibrator is
from domino_calibrator import synth, peak_quadratic, PUBLISHED_RADII
from domino_calibrator import degrade as D
from domino_calibrator.estimators import gauss_fit as _gauss_fit
SH = sys.modules['domino_calibrator.shrink']


def safe_gauss_fit(img, x0, y0, r, bkg, s0=None, tol=1e-4, maxit=60):
    """G, except that an aperture scipy cannot fit (fewer residuals than parameters) is unconverged."""
    try:
        return _gauss_fit(img, x0, y0, r, bkg, s0=s0, tol=tol, maxit=maxit)
    except ValueError:
        return dict(x=np.nan, y=np.nan, s=np.nan, amp=np.nan, n=0, ok=False, at_bound=False)


SH.gauss_fit = safe_gauss_fit          # shrink's own loop, unchanged, now calls the guarded fit

WORK = os.path.join(os.environ['HOME'], 'calib_work')
S = 0.02
SEEING = {0.7: [0.24, 0.44, 0.70], 1.0: [0.24, 0.44, 0.70, 1.00], 1.5: [0.24, 0.44, 0.70, 1.00, 1.50],
          2.0: [0.44, 0.70, 1.00, 1.50, 2.00], 3.0: [0.44, 0.70, 1.00, 1.50, 2.00], 4.0: [0.70, 1.00, 1.50, 2.00]}
SNRS = [100.0, 20.0]
SKY, RN = 100.0, 5.0
MODE = None
NREAL = 30
ARC_SCALE = 0.44                       # ARC = the published radii at 0.44"/px: 0.88-2.64 arcsec
SEE_LO, SEE_HI = 1.0, 3.0


def radii_for(gs, fpx):
    return {'PX': PUBLISHED_RADII,
            'ARC': PUBLISHED_RADII * (ARC_SCALE / gs),     # bit-identical to PX at 0.44"/px (smoke: linspace missed by 2e-9 px)
            'SEE': np.linspace(SEE_LO, SEE_HI, 41) * fpx}


def mirror_offsets(m, n):
    """H3's four fine offsets per axis: two exact mirror pairs (~+-1/8, ~+-3/8 ground px)."""
    out = []
    for want in (0.125, 0.375):
        o, _ = D.phase_offset(float(m), n, want)
        out += [o, (2 * m + 1 - o) % n]
    return out


def seq(g, px, py, xg, yg, R, est):
    o = SH.shrink(g, px, py, radii=R, estimator=est, background=0.0)
    good = o['ok'] & np.isfinite(o['x']) & np.isfinite(o['y'])
    ng = int(good.sum())
    i = int(np.argmax(good)) if ng else 0
    first = [float(o['x'][i] - xg), float(o['y'][i] - yg), float(R[i])] if ng else [np.nan, np.nan, np.nan]
    rec = [o['x0'] - xg, o['y0'] - yg, o['x2'] - xg, o['y2'] - yg, o['x6'] - xg, o['y6'] - yg, int(o['nbad'])] + first
    return o, rec


def meas(g, xg, yg, gs, fpx, names=('PX', 'ARC', 'SEE'), curves=False):
    p = peak_quadratic(g, int(round(xg)), int(round(yg)))
    out = {'P': (p['x'] - xg, p['y'] - yg)}
    R = radii_for(gs, fpx)
    for v in names:
        for est in ('G', 'M'):
            o, rec = seq(g, p['x'], p['y'], xg, yg, R[v], est)
            out[v + est] = rec
            if curves and v != 'PX':
                out[v + est + 'c'] = [(o['x'] - xg).tolist(), (o['y'] - yg).tolist()]
    return out


def meas_noisy(g, xg, yg, gs, fpx):
    p = peak_quadratic(g, int(round(xg)), int(round(yg)))
    out = {'P': (p['x'] - xg, p['y'] - yg)}
    R = radii_for(gs, fpx)
    for est in ('G', 'M'):
        o = SH.shrink(g, p['x'], p['y'], radii=np.array([2.0]), estimator=est, background=0.0)
        out['R2' + est] = [o['x2'] - xg, o['y2'] - yg]
    for v in ('ARC', 'SEE'):
        for est in ('G', 'M'):
            o = SH.shrink(g, p['x'], p['y'], radii=R[v], estimator=est, background=0.0)
            out[v + est] = [o['x0'] - xg, o['y0'] - yg, int(o['nbad'])]
    return out


def job(args):
    root, fw, seed = args
    z = np.load(os.path.join(WORK, 'sky_%s.npz' % root))
    img = z['sky'].astype(np.float64); m = int(z['m'])
    if MODE in ('null', 'probe', 'smoke'):
        img = 0.5 * (img + img[::-1, ::-1])
    conv = D.convolve(img, S, fw)
    rng = np.random.default_rng(seed)
    res = []
    for gs in SEEING[fw]:
        n = D.ground_factor(gs, S)
        offs = mirror_offsets(m, n)
        fpx = np.hypot(fw, 0.071) / gs
        phases = [(offs[0], offs[0])] if MODE == 'probe' else [(ox, oy) for ox in offs for oy in offs]
        t0 = time.time()
        for (ox, oy) in phases:
            g, (xg, yg) = D.bin_phase(conv, (float(m), float(m)), n, (ox, oy))
            try:
                mm = meas(g, xg, yg, gs, fpx, names=('ARC', 'SEE') if MODE == 'null' else ('PX', 'ARC', 'SEE'),
                          curves=(MODE in ('real', 'smoke')))
                res.append(dict(root=root, fw=fw, gs=gs, kind='noiseless', ph=(ox, oy), m=mm))
            except Exception as e:          # one failure is recorded, not a crash (S1 run 1)
                res.append(dict(root=root, fw=fw, gs=gs, kind='noiseless', ph=(ox, oy), error=repr(e)))
        t1 = time.time()
        if MODE in ('real', 'probe', 'smoke'):
            for snr in SNRS:
                for i in range(1 if MODE == 'probe' else NREAL):
                    ox, oy = offs[rng.integers(4)], offs[rng.integers(4)]
                    g1, (xg, yg) = D.bin_phase(conv, (float(m), float(m)), n, (ox, oy))
                    fin = np.isfinite(g1)
                    s = synth.snr_scale(np.where(fin, g1, 0.0), xg, yg, fpx, snr, SKY, RN)
                    g = synth.add_noise(np.where(fin, s * g1, 0.0), SKY, RN, rng) - SKY
                    g[~fin] = np.nan
                    try:
                        res.append(dict(root=root, fw=fw, gs=gs, kind='snr%d' % snr, ph=(ox, oy), m=meas_noisy(g, xg, yg, gs, fpx)))
                    except Exception as e:
                        res.append(dict(root=root, fw=fw, gs=gs, kind='snr%d' % snr, ph=(ox, oy), error=repr(e)))
        if MODE == 'probe':
            res.append(dict(root=root, fw=fw, gs=gs, kind='timing', t_noiseless=t1 - t0, t_noisy=time.time() - t1))
    return res


def main():
    global MODE, NREAL
    ap = argparse.ArgumentParser(); ap.add_argument('mode'); ap.add_argument('log')
    ap.add_argument('--frames', type=int, default=0); ap.add_argument('--nreal', type=int, default=30)
    ap.add_argument('--raw', default='')
    A = ap.parse_args()
    MODE, NREAL = A.mode, A.nreal
    f = open(A.log, 'w')
    def log(s):
        print(s, flush=True); f.write(s + '\n'); f.flush()
    log('# H4 %s %s | runs/h4_arcsec.py | commit %s | NREAL %d' % (MODE, time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        os.popen('git -C %s log -1 --format=%%h' % ROOT).read().strip(), NREAL))
    H0 = json.load(open(os.path.join(HERE, 'H0_FRAMES_2026-09-27.json')))
    frames = H0['frames']
    if MODE in ('null', 'probe') or A.frames == 5:
        seen, roots = set(), []
        for d in frames:
            if d['visit'] not in seen:
                seen.add(d['visit']); roots.append(d['root'])
        if MODE == 'probe':
            roots = [d['root'] for d in frames if d['visit'] == '22'][:1]
    else:
        roots = [d['root'] for d in frames]
        if A.frames:
            roots = roots[:A.frames]
    log('# frames: %s' % ' '.join(roots))
    tasks = [(r, fw, 1000 * i + int(fw * 10) + 7) for i, r in enumerate(roots) for fw in SEEING]
    t0 = time.time()
    out = []
    with Pool(4) as pool:
        for res in pool.imap_unordered(job, tasks):
            out.extend(res)
    errs = [o for o in out if 'error' in o]
    log('# %d records in %.0f s (%d errors%s)' % (len(out), time.time() - t0, len(errs), (': first ' + errs[0]['error'][:160]) if errs else ''))
    if MODE == 'probe':
        for o in sorted([o for o in out if o['kind'] == 'timing'], key=lambda o: (o['fw'], o['gs'])):
            nl = [x for x in out if x['kind'] == 'noiseless' and x['fw'] == o['fw'] and x['gs'] == o['gs'] and 'm' in x]
            conv = ' '.join('%s %d/41' % (k, 41 - nl[0]['m'][k][6]) for k in ('PXG', 'ARCG', 'SEEG', 'PXM', 'ARCM', 'SEEM')) if nl else 'error'
            R = radii_for(o['gs'], np.hypot(o['fw'], 0.071) / o['gs'])
            log('seeing %.1f %.2f"/px: noiseless %.2f s/phase, noisy %.2f s/image | converged %s | ARC %.2f-%.2f px SEE %.2f-%.2f px' % (
                o['fw'], o['gs'], o['t_noiseless'], o['t_noisy'] / 2.0, conv, R['ARC'][0], R['ARC'][-1], R['SEE'][0], R['SEE'][-1]))
    else:
        raw = A.raw or os.path.join(HERE, 'H4_RAW_%s_2026-09-27.json.gz' % MODE)
        with gzip.open(raw, 'wt') as g:
            json.dump([o for o in out if 'error' not in o], g)
        log('# raw: %s' % os.path.relpath(raw, ROOT))
    log('# done in %.0f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
