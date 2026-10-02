#!/usr/bin/env python3
"""The hardening round's science control (bar: the hardening round's record of 27 Sept 2026, not in this repository, bar item 3).

H4's C1 with PX alone: the first frame of each visit, H3's grid (26 seeing/pixel pairs) and H3's 4 x 4 mirror phases,
noiseless, the published radii, G and M with the known background (the frame's zero) and P, exactly as H3 measured
them; each record compared with H3_RAW's. Compared: G and M b0, b2, b6 (x, y) and nbad; P (x, y) [H4's C1]; the
stored curves, all 41 radii (x, y) [the curve line]; and G with the annulus background where H3 ran it [the Ga line].
The bar is bit for bit: every compared number equal, NaN where H3 has NaN, and nothing else.
Input: H0's sky images ($HOME/calib_work/sky_<root>.npz; tools/fetch_frames.py, then runs/h0_prepare.py).
Usage: hard_c1.py LOG
"""
import sys, os, time, json, gzip, hashlib
import numpy as np
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)                        # the repository's root, where domino_calibrator is
sys.path.insert(0, REPO)
from domino_calibrator import shrink, peak_quadratic, PUBLISHED_RADII
from domino_calibrator import degrade as D

WORK = os.path.join(os.environ['HOME'], 'calib_work')
S = 0.02
SEEING = {0.7: [0.24, 0.44, 0.70], 1.0: [0.24, 0.44, 0.70, 1.00], 1.5: [0.24, 0.44, 0.70, 1.00, 1.50],
          2.0: [0.44, 0.70, 1.00, 1.50, 2.00], 3.0: [0.44, 0.70, 1.00, 1.50, 2.00], 4.0: [0.70, 1.00, 1.50, 2.00]}


def mirror_offsets(m, n):
    out = []
    for want in (0.125, 0.375):
        o, _ = D.phase_offset(float(m), n, want)
        out += [o, (2 * m + 1 - o) % n]
    return out


def meas(g, xg, yg):
    """H3's noiseless measurement (runs/h3_grid.py meas), unchanged but for its return of the ok flags."""
    p = peak_quadratic(g, int(round(xg)), int(round(yg)))
    out = {'P': (p['x'] - xg, p['y'] - yg)}
    for est in ('G', 'M'):
        o = shrink(g, p['x'], p['y'], radii=PUBLISHED_RADII, estimator=est, background=0.0)
        out[est] = [o['x0'] - xg, o['y0'] - yg, o['x2'] - xg, o['y2'] - yg, o['x6'] - xg, o['y6'] - yg, int(o['nbad'])]
        out[est + 'c'] = [(o['x'] - xg).tolist(), (o['y'] - yg).tolist()]
        out[est + 'ok'] = np.asarray(o['ok'], bool).tolist()
    yy, xx = np.indices(g.shape)
    ann = np.hypot(xx - xg, yy - yg) <= 30.5 + 1.0
    inside = xg - 31.5 >= 0 and yg - 31.5 >= 0 and xg + 31.5 <= g.shape[1] - 1 and yg + 31.5 <= g.shape[0] - 1
    if inside and np.all(np.isfinite(g[ann])):
        o = shrink(g, p['x'], p['y'], radii=PUBLISHED_RADII, estimator='G', background='annulus')
        out['Ga'] = [o['x0'] - xg, o['y0'] - yg, o['x2'] - xg, o['y2'] - yg, o['x6'] - xg, o['y6'] - yg, int(o['nbad'])]
    return out


def job(args):
    root, fw = args
    z = np.load(os.path.join(WORK, 'sky_%s.npz' % root))
    img = z['sky'].astype(np.float64); m = int(z['m'])
    conv = D.convolve(img, S, fw)
    res = []
    for gs in SEEING[fw]:
        n = D.ground_factor(gs, S)
        offs = mirror_offsets(m, n)
        for ox in offs:
            for oy in offs:
                g, (xg, yg) = D.bin_phase(conv, (float(m), float(m)), n, (ox, oy))
                try:
                    res.append(dict(root=root, fw=fw, gs=gs, ph=(ox, oy), m=meas(g, xg, yg)))
                except Exception as e:      # a raise is recorded and fails the bar; it does not stop the run
                    res.append(dict(root=root, fw=fw, gs=gs, ph=(ox, oy), error=repr(e)))
    return res


def same(a, b):
    """Bit for bit: equal, or NaN in both. Returns (equal, max |diff| over the finite pairs)."""
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = np.isnan(a), np.isnan(b)
    if a.shape != b.shape or np.any(na != nb):
        return False, np.inf
    d = np.abs(a[~na] - b[~nb])
    return bool(np.all(a[~na] == b[~nb])), float(d.max()) if d.size else 0.0


def stamp():
    """The science modules C1's numbers rest on, each with its sha256 (12 hex digits), in C2's form, so that the two logs
    name the same code (round 3, T1.24: the log said only "package MODIFIED")."""
    return ' '.join('%s %s' % (m, hashlib.sha256(open(os.path.join(REPO, 'domino_calibrator', m), 'rb').read()).hexdigest()[:12])
                    for m in ('apertures.py', 'estimators.py', 'shrink.py', 'degrade.py', 'synth.py'))


def main():
    f = open(sys.argv[1], 'w')
    def log(s):
        print(s, flush=True); f.write(s + '\n'); f.flush()
    head = os.popen('git -C %s log -1 --format=%%h' % REPO).read().strip()
    dirty = os.popen('git -C %s status --short -- domino_calibrator/*.py' % REPO).read().strip()
    log('# hardening C1 %s | runs/hard_c1.py | HEAD %s | %s | package %s' % (
        time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()), head, stamp(), 'as committed' if not dirty else 'MODIFIED: ' + dirty.replace('\n', ', ')))
    H0 = json.load(open(os.path.join(HERE, 'H0_FRAMES_2026-09-27.json')))
    seen, roots = set(), []
    for d in H0['frames']:
        if d['visit'] not in seen:
            seen.add(d['visit']); roots.append(d['root'])
    log('# frames (the first of each visit): %s' % ' '.join(roots))
    t0 = time.time()
    out = []
    with Pool(4) as pool:
        for res in pool.imap_unordered(job, [(r, fw) for r in roots for fw in SEEING]):
            out.extend(res)
    errs = [o for o in out if 'error' in o]
    log('# %d records in %.0f s, %d raised%s' % (len(out), time.time() - t0, len(errs), (': first ' + errs[0]['error'][:200]) if errs else ''))
    h3 = json.load(gzip.open(os.path.join(HERE, 'H3_RAW_2026-09-27.json.gz'), 'rt'))
    key = lambda o: (o['root'], o['fw'], o['gs'], tuple(o['ph']))
    h3n = {key(o): o['m'] for o in h3 if o['kind'] == 'noiseless'}
    stats = {k: dict(n=0, unequal=0, worst=0.0) for k in ('C1', 'curve', 'Ga')}
    missing, notok = 0, 0
    first_bad = {}
    for o in out:
        if 'error' in o:
            continue
        k = key(o)
        if k not in h3n:
            missing += 1; continue
        a, b = o['m'], h3n[k]
        for line, pairs in (('C1', [(a[e], b[e]) for e in ('G', 'M')] + [(a['P'], b['P'])]),
                            ('curve', [(a[e + 'c'], b[e + 'c']) for e in ('G', 'M')]),
                            ('Ga', [(a.get('Ga'), b.get('Ga'))] if ('Ga' in a or 'Ga' in b) else [])):
            for u, v in pairs:
                if u is None or v is None:          # Ga run on one side only
                    eq, w = False, np.inf
                else:
                    eq, w = same(u, v)
                stats[line]['n'] += 1
                if not eq:
                    stats[line]['unequal'] += 1
                    first_bad.setdefault(line, (k, w))
                stats[line]['worst'] = max(stats[line]['worst'], w)
        notok += sum(1 for e in ('G', 'M') for ok in a[e + 'ok'] if not ok)
    log('# compared with H3_RAW: %d records (%d not in H3); radii not ok in the new run: %d' % (len(out) - len(errs) - missing, missing, notok))
    for line, what in (('C1', "H4's C1: G, M b0 b2 b6 (x, y), nbad; P (x, y)"), ('curve', 'the curve line: G, M x(r), y(r), 41 radii'),
                       ('Ga', 'the Ga line: G with the annulus, where H3 ran it')):
        s = stats[line]
        log('%-6s %-52s comparisons %5d | unequal %d | max |diff| %.3e ground px%s' % (
            line, what, s['n'], s['unequal'], s['worst'], ('' if not s['unequal'] else ' | first: %s' % (first_bad[line],))))
    ok = (not errs) and missing == 0 and all(stats[l]['unequal'] == 0 and stats[l]['n'] > 0 for l in stats)
    log('# BAR (bit for bit, nothing raised, every record in H3): %s' % ('PASS' if ok else 'FAIL'))
    log('# done in %.0f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
