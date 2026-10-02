#!/usr/bin/env python3
"""H3 post hoc - the items the H3 bar promised and h3_report.py did not deliver, and the 20:25 re-scoring with a log.
Found by the two refuters (R1, R2; archive/CALIBRATOR_2026-09-27.md, 'The refuters'). Everything here is POST HOC:
it reads H3_RAW / H3_SUMMARY / H0_FRAMES and changes no H3 number or class.

1. P (the quadratic peak): bias length and PA per visit-pair (noiseless phase-mean, frame mean), as the bar listed.
2. Angles of G's and M's b2 AND b0 to PsAng (antisolar) and to PsAMV (-v) separately, per visit.
3. The reference's error bar (3.9 mas, H2(a')) against every b0 (G, M, Ga), not only G's.
4. The noisy realisations per visit and SNR (5 per frame: 25-35 per visit, not "30").
5. The re-scoring of 20:25 UTC: runs with any unconverged radius left out; the classes again; and where the runaway
   r = 2 fits (> 3") sit by SNR.
Usage: h3_posthoc.py LOG
"""
import sys, os, json, gzip
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PS = {'22': (292.964, 109.376), '03': (291.360, 107.030), '04': (290.624, 104.124), '05': (293.059, 102.022), '06': (12.964, 99.631)}
VIS = ['22', '03', '04', '05', '06']
REF_BAR = 0.0039


def dang(a, b):
    return float(abs((a - b + 180.0) % 360.0 - 180.0))


def pa(xi, eta):
    return float(np.degrees(np.arctan2(xi, eta)) % 360.0)


def main(logpath):
    out = open(logpath, 'w')
    def log(s):
        print(s, flush=True); out.write(s + '\n'); out.flush()
    rp = os.path.join(HERE, 'H3_RAW_2026-09-27.json')
    raw = json.load(open(rp)) if os.path.exists(rp) else json.load(gzip.open(rp + '.gz', 'rt'))
    S = json.load(open(os.path.join(HERE, 'H3_SUMMARY_2026-09-27.json')))
    H0 = json.load(open(os.path.join(HERE, 'H0_FRAMES_2026-09-27.json')))
    vis = {d['root']: d['visit'] for d in H0['frames']}
    log('# H3 post hoc | reads H3_RAW (%d records), H3_SUMMARY (%d cells); changes no H3 number or class' % (len(raw), len(S)))
    # 1. P
    log('# 1. P, the quadratic peak: |b| arcsec @ PA (noiseless phase-mean over 16 phases, then the mean over the visit\'s frames)')
    Pv = {}
    for o in raw:
        if o['kind'] == 'noiseless':
            k = (vis[o['root']], o['fw'], o['gs'])
            Pv.setdefault(k, {}).setdefault(o['root'], []).append(o['m']['P'])
    for k in sorted(Pv, key=lambda t: (VIS.index(t[0]), t[1], t[2])):
        F = np.array([np.mean(a, axis=0) for a in Pv[k].values()]) * k[2]
        xi, eta = -F[:, 0].mean(), F[:, 1].mean()
        g = S['%s|%.1f|%.2f' % k]['G']
        log('  v%s %.1f" %.2f"/px: P %.3f" @%3.0f | G b2 %.3f" @%3.0f, b0 %.3f" @%3.0f' % (k[0], k[1], k[2], np.hypot(xi, eta), pa(xi, eta), g['b2']['len'], g['b2']['pa'], g['b0']['len'], g['b0']['pa']))
    # 2. angles
    log('# 2. angles (deg) to PsAng (antisolar) and to PsAMV (-v), separately: min-max over each visit\'s 26 pairs')
    for est in ('G', 'M'):
        for key in ('b2', 'b0'):
            parts = []
            for v in VIS:
                cs = [r for r in S.values() if r['visit'] == v]
                a1 = [dang(r[est][key]['pa'], PS[v][0]) for r in cs]; a2 = [dang(r[est][key]['pa'], PS[v][1]) for r in cs]
                parts.append('v%s antisolar %3.0f-%3.0f, -v %3.0f-%3.0f' % (v, min(a1), max(a1), min(a2), max(a2)))
            log('  %s %s: %s' % (est, key, ' | '.join(parts)))
    # 3. reference bar
    log('# 3. b0 below the reference\'s error bar (%.1f mas), every estimator:' % (REF_BAR * 1000))
    for est in ('G', 'M', 'Ga'):
        below = [(r['visit'], r['fw'], r['gs'], round(r[est]['b0']['len'] * 1000, 1)) for r in S.values() if est in r and r[est]['b0']['len'] < REF_BAR]
        near = [(r['visit'], r['fw'], r['gs'], round(r[est]['b0']['len'] * 1000, 1)) for r in S.values() if est in r and REF_BAR <= r[est]['b0']['len'] < 3 * REF_BAR]
        log('  %s: below %d %s | within 1-3x the bar (direction uncertain by tens of degrees) %d %s' % (est, len(below), below, len(near), near))
    # 4. counts
    log('# 4. noisy realisations per visit and SNR (5 per frame and pair):')
    for v in VIS:
        nf = len(set(o['root'] for o in raw if vis[o['root']] == v))
        n1 = [r['G']['n_100'] for r in S.values() if r['visit'] == v]; n2 = [r['G']['n_20'] for r in S.values() if r['visit'] == v]
        log('  v%s: %d frames -> %d per pair (SNR 100: %d-%d kept; SNR 20: %d-%d kept)' % (v, nf, 5 * nf, min(n1), max(n1), min(n2), max(n2)))
    # 5. re-scoring and runaways
    log('# 5. re-scoring with every noisy run that had any unconverged radius left out (the 20:25 UTC check, now logged)')
    nz = {}
    for o in raw:
        if o['kind'].startswith('snr'):
            k = '%s|%.1f|%.2f' % (vis[o['root']], o['fw'], o['gs'])
            nz.setdefault((k, o['kind']), []).append((o['m']['G'], o['gs']))
    excl, tally, changed = 0, {}, []
    run_by_snr = {'snr100': 0, 'snr20': 0}
    for (k, kind), v in nz.items():
        for g, gs in v:
            if np.hypot(g[2], g[3]) * gs > 3.0:
                run_by_snr[kind] += 1
    for k, r in S.items():
        G = r['G']; rms = {}
        for snr in ('snr100', 'snr20'):
            a = np.array([g for g, gs in nz[(k, snr)]]); keep = a[:, 6] == 0; excl += int((~keep).sum()); a = a[keep] * r['gs']
            rms[snr] = (np.sqrt((a[:, 0] ** 2 + a[:, 1] ** 2).mean()), np.sqrt((a[:, 2] ** 2 + a[:, 3] ** 2).mean()))
        b0, b2 = G['b0']['len'], G['b2']['len']
        cls = 'FAILS' if (b0 > 0.75 * b2 or rms['snr100'][0] > rms['snr100'][1]) else ('WORKS' if (b0 <= 0.25 * b2 and rms['snr20'][0] <= rms['snr20'][1]) else 'HELPS')
        tally[cls] = tally.get(cls, 0) + 1
        if cls != G['class']:
            changed.append((k, G['class'], cls))
    log('  runs left out: %d of %d; tally %s; cells whose class changes: %d %s' % (excl, sum(len(v) for v in nz.values()), tally, len(changed), changed))
    log('  runaway r = 2 fits (G, |b2| > 3"): SNR 100: %d, SNR 20: %d' % (run_by_snr['snr100'], run_by_snr['snr20']))


if __name__ == '__main__':
    main(sys.argv[1])
