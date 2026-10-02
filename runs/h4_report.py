#!/usr/bin/env python3
"""H4 report - reads H4_RAW_{null,real}_2026-09-27.json.gz; written before either raw file existed (H4 bar,
archive/CALIBRATOR_ARCSEC_2026-09-27.md). Conventions as h3_report.py: ground column index increases WEST, rows NORTH,
so a ground offset (dx, dy) is (xi, eta) = (-dx, +dy) * gs arcsec; |b| = length of the 2-D bias vector.

null: C3 - on the five first frames point-symmetrised (as H1), every ARC and SEE phase-mean b0 must be zero:
      M within H1's line (1e-5 ground px) and P within 1e-6, else STOP; G within the reference's own error bar, 3.9 mas
      on the sky (H2(a')), per cell - a G cell beyond it is NULL-FAILED, named, and counts as NOT MEASURED in the real
      tallies (the smoke, visit 03 symmetrised: G's b0 on ARC at 1.5-2.0"/px is not mirror-symmetric, b_first less so).
      b_first's null is printed beside, not gated: the first converged radius differs between mirror phases.
      A variant-estimator cell with fewer than 21 of 41 converged radii in any phase is NOT MEASURED.
real: C1 - PX reproduces H3_RAW: every G and M b0, b2, b6 (x, y) and nbad equal within 1e-9 ground px, for every
           (frame, pair, phase) present in both.
      C2 - at 0.44"/px ARC's radii are the published radii: ARC b0 equals PX b0 within 1e-9 ground px (G and M).
      Then, per visit and pair (the first frame of each visit; noiseless phase-means over 16 phases): b2 (PX, r = 2 px,
      the class baseline), b0 for PX, ARC, SEE, b at each variant's first converged radius, and P; the classes
      (H3's, unchanged): WORKS |b0| <= 0.25|b2| and RMS0 <= RMS2 at SNR 20; FAILS |b0| > 0.75|b2| or RMS0 > RMS2 at
      SNR 100; HELPS otherwise; NOT MEASURED if any noiseless phase converged at fewer than 21 of 41 radii.
      The tallies over the professional (<= 1.0" seeing, <= 0.44"/px: 20 cells), amateur (>= 2" seeing, >= 1.0"/px:
      45) and coarse (>= 0.70"/px: 90) cells, and the pre-registered verdicts, for G (primary) and M (beside):
        RESCUES if not FAILS in >= 36 of the 45 amateur cells, |b0| > |b2| in <= 4 of the 90 coarse cells, and not
                FAILS in any of the 20 professional cells;
        DOES NOT RESCUE if FAILS in >= 23 of the 45 amateur cells;
        PARTIAL otherwise.
Usage: h4_report.py null|real|smoke LOG [RAW]   (smoke: real's path on symmetrised frames, to test this script)
"""
import sys, os, json, gzip
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..'))
VIS = ['22', '03', '04', '05', '06']
EST = ('G', 'M')
TOL = {'G': 2e-4, 'M': 1e-5}
REF_MAS = 3.9          # the reference's error bar, H2(a'), mas on the sky


def sky(dx, dy, gs):
    return np.stack([-np.asarray(dx) * gs, np.asarray(dy) * gs], axis=-1)


def region(fw, gs):
    return dict(prof=(fw <= 1.0 and gs <= 0.44), amat=(fw >= 2.0 and gs >= 1.0), coarse=(gs >= 0.70))


def main(mode, logpath, rawpath=''):
    out = open(logpath, 'w')
    def log(s):
        print(s, flush=True); out.write(s + '\n'); out.flush()
    rawpath = rawpath or os.path.join(HERE, 'H4_RAW_%s_2026-09-27.json.gz' % mode)
    raw = json.load(gzip.open(rawpath, 'rt'))
    H0 = json.load(open(os.path.join(HERE, 'H0_FRAMES_2026-09-27.json')))
    visit_of = {d['root']: d['visit'] for d in H0['frames']}
    pairs = sorted(set((o['fw'], o['gs']) for o in raw))
    if mode == 'null':
        stop, failed = False, []
        log('# H4 null (C3): per frame and pair, phase-mean max |b| over (b0, b_first; x, y): M and P in ground px, G in mas on the sky; converged radii, min over phases')
        for r in sorted(set(o['root'] for o in raw)):
            for (fw, gs) in pairs:
                ms = [o['m'] for o in raw if o['root'] == r and o['fw'] == fw and o['gs'] == gs and o['kind'] == 'noiseless']
                if not ms:
                    continue
                line = '%s seeing %.1f %.2f"/px' % (r, fw, gs)
                for v in ('ARC', 'SEE'):
                    for e in EST:
                        k = v + e
                        A = np.array([x[k] for x in ms], float)
                        nconv = int((41 - A[:, 6]).min())
                        if nconv < 21:
                            line += ' | %s NOT MEASURED (%d/41)' % (k, nconv); continue
                        mu = float(np.abs(np.nanmean(A[:, [0, 1]], axis=0)).max())          # b0: what the classes use
                        muf = float(np.abs(np.nanmean(A[:, [7, 8]], axis=0)).max())         # b_first: descriptive, beside
                        if e == 'M':
                            good = mu <= TOL['M']
                            stop |= not good
                            line += ' | %s %.1e px %d/41 %s' % (k, mu, nconv, 'ok' if good else 'FAIL (STOP)')
                        else:
                            mas = 1000.0 * mu * gs
                            good = mas <= REF_MAS
                            if not good:
                                failed.append('%s|%.1f|%.2f|%s' % (visit_of[r], fw, gs, v))
                            line += ' | %s %.2f mas (first %.2f) %d/41 %s' % (k, mas, 1000.0 * muf * gs, nconv, 'ok' if good else 'NULL-FAILED')
                P = np.array([x['P'] for x in ms], float); mp = float(np.abs(P.mean(axis=0)).max())
                stop |= mp > 1e-6
                line += ' | P %.1e %s' % (mp, 'ok' if mp <= 1e-6 else 'FAIL (STOP)')
                log(line)
        json.dump(failed, open(rawpath + '.nullfailed.json', 'w'))
        log('# C3: M and P %s; G cells NULL-FAILED: %d %s' % ('FAIL -> STOP' if stop else 'PASS', len(failed), failed))
        return
    # ---------------- real ----------------
    nullf = os.path.join(os.path.dirname(rawpath), 'H4_RAW_null_2026-09-27.json.gz.nullfailed.json')   # beside the raw
    nullfailed = set(json.load(open(nullf))) if os.path.exists(nullf) else None
    log('# C3 carried from the null: %s' % ('%d G cells NULL-FAILED' % len(nullfailed) if nullfailed is not None else 'NO NULL FILE (smoke or not run)'))
    nl = [o for o in raw if o['kind'] == 'noiseless']
    # C1: PX against H3_RAW
    h3 = json.load(gzip.open(os.path.join(HERE, 'H3_RAW_2026-09-27.json.gz'), 'rt'))
    key = lambda o: (o['root'], o['fw'], o['gs'], tuple(o['ph']))
    h3n = {key(o): o['m'] for o in h3 if o['kind'] == 'noiseless'}
    worst, n1, missing = 0.0, 0, 0
    for o in nl:
        k = key(o)
        if k not in h3n:
            missing += 1; continue
        for e in EST:
            a, b = np.array(o['m']['PX' + e][:7], float), np.array(h3n[k][e][:7], float)
            if a[6] != b[6]:
                worst = np.inf
            fa, fb = np.isfinite(a[:6]), np.isfinite(b[:6])
            if np.any(fa != fb):
                worst = np.inf
            elif fa.any():
                worst = max(worst, float(np.abs(a[:6][fa] - b[:6][fb]).max()))
        pa, pb = np.array(o['m']['P'], float), np.array(h3n[k]['P'], float)
        worst = max(worst, float(np.abs(pa - pb).max()))
        n1 += 1
    c1 = n1 > 0 and worst <= 1e-9
    log('# C1 PX against H3_RAW: %d records compared (%d not in H3), max |diff| %.2e ground px -> %s' % (n1, missing, worst, 'PASS' if c1 else 'FAIL'))
    # C2: ARC == PX at 0.44"/px
    w2 = 0.0; n2 = 0
    for o in nl:
        if abs(o['gs'] - 0.44) < 1e-9:
            for e in EST:
                a, b = np.array(o['m']['ARC' + e][:2], float), np.array(o['m']['PX' + e][:2], float)
                w2 = max(w2, float(np.abs(a - b).max())); n2 += 1
    c2 = n2 > 0 and w2 <= 1e-9
    log('# C2 ARC == PX at 0.44"/px: %d comparisons, max |diff| %.2e ground px -> %s' % (n2, w2, 'PASS' if c2 else 'FAIL'))
    if not (c1 and c2):
        log('# STOP: a control failed; nothing below is read.')
    # H3's six-frame summary, for PX's reference classes and the subsample check
    h3s = json.load(open(os.path.join(HERE, 'H3_SUMMARY_2026-09-27.json')))
    summary = {}
    log('# per visit and pair (first frame of the visit; noiseless phase-means): lengths in arcsec, PA east of north')
    log('#   b2 = PX r = 2 px (baseline); b0 PX / ARC / SEE with ratio to b2; b_first = the variant\'s first converged radius; P; RMS0/RMS2 at SNR 100, 20; class')
    for v in VIS:
        for (fw, gs) in pairs:
            sel = [o for o in raw if visit_of[o['root']] == v and o['fw'] == fw and o['gs'] == gs]
            ms = [o['m'] for o in sel if o['kind'] == 'noiseless']
            if not ms:
                continue
            rec = dict(visit=v, fw=fw, gs=gs, fwhm_px=float(np.hypot(fw, 0.071) / gs), **region(fw, gs))
            P = sky(*np.array([x['P'] for x in ms], float).mean(axis=0), gs)
            rec['P'] = float(np.hypot(*P))
            for e in EST:
                PX = np.array([x['PX' + e] for x in ms], float)
                b2 = sky(PX[:, 2].mean(), PX[:, 3].mean(), gs); L2 = float(np.hypot(*b2))
                d = dict(b2=L2)
                for var in ('PX', 'ARC', 'SEE'):
                    A = np.array([x[var + e] for x in ms], float)
                    nconv = int((41 - A[:, 6]).min())
                    b0 = sky(A[:, 0].mean(), A[:, 1].mean(), gs); L0 = float(np.hypot(*b0))
                    bf = sky(np.nanmean(A[:, 7]), np.nanmean(A[:, 8]), gs)
                    q = dict(b0=L0, ratio=L0 / L2 if L2 > 0 else np.nan, pa0=float(np.degrees(np.arctan2(*b0)) % 360.0),
                             bfirst=float(np.hypot(*bf)), rfirst_px=float(np.nanmax(A[:, 9])), nconv=nconv)
                    if var in ('ARC', 'SEE'):
                        for snr in (100, 20):
                            nz = [o['m'] for o in sel if o['kind'] == 'snr%d' % snr]
                            if nz:
                                B0 = np.array([x[var + e][:2] for x in nz], float) * gs
                                B2 = np.array([x['R2' + e][:2] for x in nz], float) * gs
                                okr = np.all(np.isfinite(B0), axis=1) & np.all(np.isfinite(B2), axis=1)
                                q['rms0_%d' % snr] = float(np.sqrt((B0[okr] ** 2).sum(axis=1).mean())) if okr.any() else np.nan
                                q['rms2_%d' % snr] = float(np.sqrt((B2[okr] ** 2).sum(axis=1).mean())) if okr.any() else np.nan
                                q['n_%d' % snr] = int(okr.sum()); q['of_%d' % snr] = len(nz)
                        if nconv < 21:
                            q['class'] = 'NOT MEASURED'
                        elif e == 'G' and nullfailed is not None and '%s|%.1f|%.2f|%s' % (v, fw, gs, var) in nullfailed:
                            q['class'] = 'NULL-FAILED'
                        elif q['b0'] > 0.75 * L2 or not (q.get('rms0_100', np.inf) <= q.get('rms2_100', -np.inf)):
                            q['class'] = 'FAILS'
                        elif q['b0'] <= 0.25 * L2 and q.get('rms0_20', np.inf) <= q.get('rms2_20', -np.inf):
                            q['class'] = 'WORKS'
                        else:
                            q['class'] = 'HELPS'
                    d[var] = q
                h3k = '%s|%.1f|%.2f' % (v, fw, gs)
                if h3k in h3s and e in h3s[h3k]:
                    d['PX']['class_h3'] = h3s[h3k][e].get('class', '?')
                    d['PX']['ratio_h3'] = h3s[h3k][e]['ratio']
                rec[e] = d
            summary['%s|%.1f|%.2f' % (v, fw, gs)] = rec
            G = rec['G']
            line = 'v%s %.1f" %.2f"/px (FWHM %.2f px) | b2 %.3f | PX b0 %.3f (%.2f, H3 %s) | ARC b0 %.3f (%.2f) first %.3f @%.2fpx %s | SEE b0 %.3f (%.2f) first %.3f @%.2fpx %s | P %.3f' % (
                v, fw, gs, rec['fwhm_px'], G['b2'], G['PX']['b0'], G['PX']['ratio'], G['PX'].get('class_h3', '?'),
                G['ARC']['b0'], G['ARC']['ratio'], G['ARC']['bfirst'], G['ARC']['rfirst_px'], G['ARC']['class'],
                G['SEE']['b0'], G['SEE']['ratio'], G['SEE']['bfirst'], G['SEE']['rfirst_px'], G['SEE']['class'], rec['P'])
            line += ' | RMS0/2 S100 ARC %.3f/%.3f SEE %.3f/%.3f S20 ARC %.3f/%.3f SEE %.3f/%.3f' % (
                G['ARC'].get('rms0_100', np.nan), G['ARC'].get('rms2_100', np.nan), G['SEE'].get('rms0_100', np.nan), G['SEE'].get('rms2_100', np.nan),
                G['ARC'].get('rms0_20', np.nan), G['ARC'].get('rms2_20', np.nan), G['SEE'].get('rms0_20', np.nan), G['SEE'].get('rms2_20', np.nan))
            M = rec['M']
            line += ' || M b2 %.3f PX %.3f (%.2f) ARC %.3f (%.2f) %s SEE %.3f (%.2f) %s' % (
                M['b2'], M['PX']['b0'], M['PX']['ratio'], M['ARC']['b0'], M['ARC']['ratio'], M['ARC']['class'], M['SEE']['b0'], M['SEE']['ratio'], M['SEE']['class'])
            log(line)
    # the subsample check: PX's ratio from the first frame against H3's six-frame mean
    dr = [abs(rec['G']['PX']['ratio'] - rec['G']['PX']['ratio_h3']) for rec in summary.values() if 'ratio_h3' in rec['G']['PX']]
    log('# subsample check (not the bar): G PX b0/b2 from the first frame vs H3\'s six-frame mean, max |diff| %.3f over %d cells' % (max(dr), len(dr)))
    # tallies and verdicts
    for e in EST:
        for var in ('ARC', 'SEE'):
            t = {}
            for reg in ('prof', 'amat', 'coarse'):
                cs = [rec[e][var]['class'] for rec in summary.values() if rec[reg]]
                t[reg] = {c: cs.count(c) for c in sorted(set(cs))}
            allc = [rec[e][var]['class'] for rec in summary.values()]
            worse = sum(1 for rec in summary.values() if rec['coarse'] and rec[e][var]['b0'] > rec[e]['b2'])
            worse_all = sum(1 for rec in summary.values() if rec[e][var]['b0'] > rec[e]['b2'])
            amat_notfail = sum(1 for rec in summary.values() if rec['amat'] and rec[e][var]['class'] in ('WORKS', 'HELPS'))
            amat_fail = sum(1 for rec in summary.values() if rec['amat'] and rec[e][var]['class'] == 'FAILS')
            prof_fail = sum(1 for rec in summary.values() if rec['prof'] and rec[e][var]['class'] == 'FAILS')
            if amat_notfail >= 36 and worse <= 4 and prof_fail == 0:
                verdict = 'RESCUES'
            elif amat_fail >= 23:
                verdict = 'DOES NOT RESCUE'
            else:
                verdict = 'PARTIAL'
            log('# %s %s: all %s | professional %s | amateur %s | coarse %s | |b0|>|b2| coarse %d/90 (all %d/130) | amateur not FAILS %d/45 | professional FAILS %d/20 -> %s' % (
                e, var, {c: allc.count(c) for c in sorted(set(allc))}, t['prof'], t['amat'], t['coarse'], worse, worse_all, amat_notfail, prof_fail, verdict))
    # closest to HST's reference, per region (descriptive, not the bar): G's b2, PX b0, ARC b0, SEE b0, ARC first, P
    for reg in ('prof', 'amat', 'coarse'):
        cnt = {}
        for rec in summary.values():
            if not rec[reg]:
                continue
            G = rec['G']
            cand = {'b2': G['b2'], 'PX b0': G['PX']['b0'], 'ARC b0': G['ARC']['b0'], 'SEE b0': G['SEE']['b0'], 'ARC first': G['ARC']['bfirst'], 'P': rec['P']}
            best = min(cand, key=cand.get)
            cnt[best] = cnt.get(best, 0) + 1
        log('# closest to HST (G), %s cells: %s' % (reg, cnt))
    sp = os.path.join(HERE, 'H4_SUMMARY_2026-09-27.json') if mode == 'real' else rawpath + '.summary.json'
    json.dump(summary, open(sp, 'w'), indent=0)
    log('# summary: %s' % sp)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else '')
