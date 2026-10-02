#!/usr/bin/env python3
"""The hardening round's noisy control, C2 (the hardening round's record of 27 Sept 2026, not in this repository, step 4; asked by both lane 1
refuters): C1 is noiseless and no radius fails in it, so rules that act only on a failed radius (the new refusals, and
the warm-start reset and width seed that follow them) are invisible to it. C2 re-runs H3's own job (runs/h3_grid.py,
imported, unchanged) for the first frame of each visit with H3's own seeds (1000 i + int(10 fw), i the frame's index
among the 30), and compares every record, noiseless and noisy (SNR 100 and 20, 5 draws per frame, pair and SNR), with
H3_RAW: G and M b0, b2, b6 (x, y) and nbad, P, and G with the annulus where H3 ran it. The bar is bit for bit, nothing
raised; a difference is a science-change candidate, named, not explained away.
Usage: hard_c2.py LOG
"""
import sys, os, time, json, gzip
import numpy as np
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(HERE)                        # the repository's root, where domino_calibrator is
sys.path.insert(0, REPO); sys.path.insert(0, HERE)
import h3_grid as H3


def same(a, b):
    a, b = np.asarray(a, float), np.asarray(b, float)
    na, nb = np.isnan(a), np.isnan(b)
    if a.shape != b.shape or np.any(na != nb):
        return False, np.inf
    d = np.abs(a[~na] - b[~nb])
    return bool(np.all(a[~na] == b[~nb])), float(d.max()) if d.size else 0.0


def main():
    f = open(sys.argv[1], 'w')
    def log(s):
        print(s, flush=True); f.write(s + '\n'); f.flush()
    mods = ' '.join('%s %s' % (m, os.popen('sha256sum %s' % os.path.join(REPO, 'domino_calibrator', m)).read()[:12])
                    for m in ('apertures.py', 'estimators.py', 'shrink.py', 'degrade.py', 'synth.py'))
    log('# hardening C2 %s | runs/hard_c2.py | HEAD %s | %s' % (time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        os.popen('git -C %s log -1 --format=%%h' % REPO).read().strip(), mods))
    frames = json.load(open(os.path.join(HERE, 'H0_FRAMES_2026-09-27.json')))['frames']
    roots = [d['root'] for d in frames]
    seen, first = set(), []
    for i, d in enumerate(frames):
        if d['visit'] not in seen:
            seen.add(d['visit']); first.append((i, d['root']))
    log('# frames (the first of each visit, with H3 index): %s' % ' '.join('%s[%d]' % (r, i) for i, r in first))
    H3.MODE = 'real'                                   # set before the pool forks, as h3_grid's main does
    tasks = [(r, fw, 1000 * i + int(fw * 10)) for i, r in first for fw in H3.SEEING]
    t0 = time.time()
    out = []
    with Pool(4) as pool:
        for res in pool.imap_unordered(H3.job, tasks):
            out.extend(res)
    errs = [o for o in out if 'error' in o]
    log('# %d records in %.0f s, %d raised%s' % (len(out), time.time() - t0, len(errs), (': first ' + errs[0]['error'][:200]) if errs else ''))
    h3 = json.load(gzip.open(os.path.join(HERE, 'H3_RAW_2026-09-27.json.gz'), 'rt'))
    wanted = {r for _, r in first}
    key = lambda o: (o['root'], o['fw'], o['gs'], o['kind'], tuple(o['ph']))
    ref = {}
    for o in h3:
        if o['root'] in wanted:
            ref.setdefault(key(o), []).append(o['m'])
    new = {}
    for o in out:
        if 'error' not in o:
            new.setdefault(key(o), []).append(o['m'])
    stats = {k: dict(n=0, unequal=0, worst=0.0, first=None) for k in ('noiseless', 'snr100', 'snr20')}
    missing = extra = 0
    diffs = []                                         # every unequal comparison, classified below
    for k in set(ref) | set(new):
        a, b = new.get(k, []), ref.get(k, [])
        if len(a) != len(b):
            missing += max(0, len(b) - len(a)); extra += max(0, len(a) - len(b))
        for ma, mb in zip(a, b):           # records with the same key come in the job's order in both runs
            for e in ('G', 'M', 'P', 'Ga'):
                if (e in ma) != (e in mb):
                    eq, w = False, np.inf
                elif e not in ma:
                    continue
                else:
                    eq, w = same(ma[e], mb[e])
                s = stats[k[3]]
                s['n'] += 1
                if not eq:
                    s['unequal'] += 1
                    s['first'] = s['first'] or (k, e, ma.get(e), mb.get(e))
                    diffs.append((k, e, ma.get(e), mb.get(e)))
                s['worst'] = max(s['worst'], w)
    log('# compared with H3_RAW: new %d, H3 %d records for these frames | H3 records with no new twin %d, new with no H3 twin %d'
        % (sum(len(v) for v in new.values()), sum(len(v) for v in ref.values()), missing, extra))
    for kind in ('noiseless', 'snr100', 'snr20'):
        s = stats[kind]
        log('%-9s comparisons %5d | unequal %d | max |diff| %.3e ground px%s' % (kind, s['n'], s['unequal'], s['worst'],
            '' if not s['unequal'] else ' | first: %s' % (s['first'],)))
    ok = not errs and missing == 0 and extra == 0 and all(stats[k]['unequal'] == 0 and stats[k]['n'] > 0 for k in stats)
    log('# BAR (bit for bit, nothing raised, every record twinned): %s' % ('PASS' if ok else 'FAIL'))
    # each difference, classified: REPORTING = the same nbad and the same zero-aperture position (b0) bit for bit, and
    # every differing slot a b2 or b6 (x, y) that is NaN now and finite in H3_RAW (an unconverged radius's runaway,
    # which H3_RAW stored before the first room's rule "an unconverged radius reports NaN"); FITTED = anything else
    kinds = {'REPORTING': 0, 'FITTED': 0}
    for k, e, a, b in diffs:
        if a is None or b is None:
            c = 'FITTED'
        else:
            a, b = np.asarray(a, float), np.asarray(b, float)
            slots = [i for i in range(7) if not (a[i] == b[i] or (np.isnan(a[i]) and np.isnan(b[i])))]
            c = 'REPORTING' if (a[6] == b[6] and 0 not in slots and 1 not in slots and slots
                                and all(i in (2, 3, 4, 5) and np.isnan(a[i]) and np.isfinite(b[i]) for i in slots)) else 'FITTED'
        kinds[c] += 1
        log('  %-9s %s %-3s %s | new %s | H3 %s' % (c, k[3], e, k[:3] + (k[4],), a if a is None else np.round(np.asarray(a, float), 4).tolist(),
                                                   b if b is None else np.round(np.asarray(b, float), 4).tolist()))
    log('# the differences: %d REPORTING, %d FITTED' % (kinds['REPORTING'], kinds['FITTED']))
    log('# done in %.0f s' % (time.time() - t0))


if __name__ == '__main__':
    main()
