#!/usr/bin/env python3
"""H3 report - reads H3_RAW_2026-09-27.json and H0's Horizons rows; written before the raw file existed (H3 bar).

Sky convention of the ground images: column index increases WEST (east left), rows increase NORTH, so a ground-pixel
offset (dx, dy) is (xi, eta) = (-dx, +dy) * scale arcsec (xi = dRA cos dec, east positive). PA east of north.
Horizons (observer HST): PsAng = PA of the extended Sun-to-target radius vector (antisolar direction on the sky);
PsAMV = PA of the negative heliocentric velocity vector. "Tailward" = within 45 deg of either.
Classes (H3 bar): WORKS |b0| <= 0.25|b2| and RMS0 <= RMS2 at SNR 20; FAILS |b0| > 0.75|b2| or RMS0 > RMS2 at SNR 100;
else HELPS. |b| = length of the 2-D bias vector. The reference's error bar (H2(a')): 3.9 mas.
Usage: h3_report.py LOG
"""
import sys, os, json, re, gzip
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(next((r for r in (os.path.join(HERE, '..'), os.path.join(HERE, '..', '..'))   # the public checkout's
                            if os.path.isdir(os.path.join(r, 'data', 'hst-3i'))), os.path.join(HERE, '..')))   # root, or the Castle's
REF_BAR = 0.0039      # arcsec
KM_PER_ARCSEC_AU = 149597870.7 / 206264.806


def horizons_table():
    txt = open(os.path.join(ROOT, 'data', 'hst-3i', 'horizons', '3I_from_HST_psang_2026-09-27.txt'), encoding='utf-8').read()
    head = txt.split('$$SOE')[0].strip().splitlines()
    cols = None
    for l in reversed(head):
        if 'Date' in l and ',' in l:
            cols = [c.strip() for c in l.split(',')]
            break
    rows = [[c.strip() for c in l.split(',')] for l in txt.split('$$SOE')[1].split('$$EOE')[0].strip().splitlines()]
    return cols, rows


def pa(xi, eta):
    return float(np.degrees(np.arctan2(xi, eta)) % 360.0)


def dang(a, b):
    return float(abs((a - b + 180.0) % 360.0 - 180.0))


def main(logpath):
    out = open(logpath, 'w')
    def log(s):
        print(s, flush=True); out.write(s + '\n'); out.flush()
    p = os.path.join(HERE, 'H3_RAW_2026-09-27.json')           # the public checkout keeps it gzipped
    raw = json.load(open(p, encoding='utf-8')) if os.path.exists(p) else json.load(gzip.open(p + '.gz', 'rt', encoding='utf-8'))
    H0 = json.load(open(os.path.join(HERE, 'H0_FRAMES_2026-09-27.json')))
    visit_of = {d['root']: d['visit'] for d in H0['frames']}
    cols, rows = horizons_table()
    VIS = ['22', '03', '04', '05', '06']
    hz = {}
    def col(name):
        for i, c in enumerate(cols):                 # exact names first ('r' must not match 'R.A.')
            if c.strip() == name:
                return i
        for i, c in enumerate(cols):
            if c.replace(' ', '').lower().startswith(name.lower()) and name.lower() != 'r':
                return i
        raise KeyError(name)
    iA, iM, iD, iR = col('PsAng'), col('PsAMV'), col('delta'), col('r')
    for v, r in zip(VIS, rows):
        hz[v] = dict(psang=float(r[iA]), psamv=float(r[iM]), delta=float(r[iD]), r=float(r[iR]), date=r[0])
    log('# H3 report | Horizons columns used: %s=%s %s=%s %s=%s %s=%s' % (cols[iA], iA, cols[iM], iM, cols[iD], iD, cols[iR], iR))
    for v in VIS:
        log('#   visit %s %s: PsAng %.2f PsAMV %.2f delta %.4f au r %.4f au -> 1" = %.0f km' % (v, hz[v]['date'], hz[v]['psang'], hz[v]['psamv'], hz[v]['delta'], hz[v]['r'], hz[v]['delta'] * KM_PER_ARCSEC_AU))
    pairs = sorted(set((o['fw'], o['gs']) for o in raw))
    summary = {}
    log('# per visit and pair: G (known bkg) noiseless phase-mean over 16 phases, mean over the visit\'s frames (sd across frames);')
    log('#   b2, b0, b6 as |b| arcsec @ PA; b0/b2 length ratio; tailward? (b2 within 45 deg of PsAng or PsAMV); RMS0/RMS2 SNR100, SNR20; class. M and G-annulus beside.')
    for v in VIS:
        for (fw, gs) in pairs:
            sel = [o for o in raw if visit_of[o['root']] == v and o['fw'] == fw and o['gs'] == gs]
            if not sel:
                continue
            fpx = np.hypot(fw, 0.071) / gs
            rec = dict(visit=v, fw=fw, gs=gs, fwhm_px=fpx)
            for est in ('G', 'M', 'Ga'):
                per_frame = {}
                for o in sel:
                    if o['kind'] == 'noiseless' and est in o['m']:
                        per_frame.setdefault(o['root'], []).append(o['m'][est][:6])
                if not per_frame:
                    continue
                F = np.array([np.mean(a, axis=0) for a in per_frame.values()])       # frames x 6 (ground px)
                sky = np.stack([-F[:, 0::2] * gs, F[:, 1::2] * gs], axis=-1)            # frames x 3 (b0, b2, b6) x (xi, eta)
                mu, sd = sky.mean(axis=0), sky.std(axis=0, ddof=1) if len(F) > 1 else np.zeros((3, 2))
                d = {}
                for i, nm in enumerate(('b0', 'b2', 'b6')):
                    L = float(np.hypot(*mu[i]))
                    d[nm] = dict(xi=float(mu[i, 0]), eta=float(mu[i, 1]), len=L, pa=pa(*mu[i]), sd_xi=float(sd[i, 0]), sd_eta=float(sd[i, 1]),
                                 km=L * hz[v]['delta'] * KM_PER_ARCSEC_AU)
                d['ratio'] = d['b0']['len'] / d['b2']['len'] if d['b2']['len'] > 0 else float('nan')
                d['nframes'] = len(F)
                for snr in (100, 20):
                    nz = [o['m'][est] for o in sel if o['kind'] == 'snr%d' % snr and est in o['m']]
                    if nz:
                        B = np.array([x[:6] for x in nz]) * gs
                        ok = np.all(np.isfinite(B), axis=1); B = B[ok]
                        d['rms0_%d' % snr] = float(np.sqrt((B[:, 0] ** 2 + B[:, 1] ** 2).mean()))
                        d['rms2_%d' % snr] = float(np.sqrt((B[:, 2] ** 2 + B[:, 3] ** 2).mean()))
                        d['n_%d' % snr] = int(len(B))
                if 'rms0_20' in d and 'rms0_100' in d:
                    if d['b0']['len'] > 0.75 * d['b2']['len'] or d['rms0_100'] > d['rms2_100']:
                        d['class'] = 'FAILS'
                    elif d['b0']['len'] <= 0.25 * d['b2']['len'] and d['rms0_20'] <= d['rms2_20']:
                        d['class'] = 'WORKS'
                    else:
                        d['class'] = 'HELPS'
                d['tail_b2'] = min(dang(d['b2']['pa'], hz[v]['psang']), dang(d['b2']['pa'], hz[v]['psamv']))
                d['sun_b2'] = dang(d['b2']['pa'], (hz[v]['psang'] + 180.0) % 360.0)
                rec[est] = d
            summary['%s|%.1f|%.2f' % (v, fw, gs)] = rec
            G = rec['G']
            line = 'v%s seeing %.1f" %.2f"/px (FWHM %.2f px) | G b2 %.3f" @%3.0f (sd %.3f) b0 %.3f" @%3.0f (%.0f km) b6 %.3f" @%3.0f | b0/b2 %.2f | b2 vs tail %3.0f deg, vs sun %3.0f deg %s | RMS0/2 S100 %.3f/%.3f S20 %.3f/%.3f | %s' % (
                v, fw, gs, fpx, G['b2']['len'], G['b2']['pa'], np.hypot(G['b2']['sd_xi'], G['b2']['sd_eta']), G['b0']['len'], G['b0']['pa'], G['b0']['km'],
                G['b6']['len'], G['b6']['pa'], G['ratio'], G['tail_b2'], G['sun_b2'], 'TAILWARD' if G['tail_b2'] <= 45 else ('SUNWARD' if G['sun_b2'] <= 45 else 'neither'),
                G.get('rms0_100', np.nan), G.get('rms2_100', np.nan), G.get('rms0_20', np.nan), G.get('rms2_20', np.nan), G.get('class', '?'))
            M = rec['M']
            line += ' || M b2 %.3f" b0 %.3f" @%3.0f ratio %.2f %s' % (M['b2']['len'], M['b0']['len'], M['b0']['pa'], M['ratio'], M.get('class', '?'))
            if 'Ga' in rec:
                Ga = rec['Ga']
                line += ' || G-annulus b2 %.3f" b0 %.3f" @%3.0f ratio %.2f %s' % (Ga['b2']['len'], Ga['b0']['len'], Ga['b0']['pa'], Ga['ratio'], Ga.get('class', '?'))
            if G['b0']['len'] < REF_BAR:
                line += ' | b0 below the reference bar (%.4f")' % REF_BAR
            log(line)
    # tallies
    for est in ('G', 'M', 'Ga'):
        t = {}
        for rec in summary.values():
            if est in rec and 'class' in rec[est]:
                t[rec[est]['class']] = t.get(rec[est]['class'], 0) + 1
        log('# tally %s: %s' % (est, t))
    tw = [rec['G']['tail_b2'] <= 45 for rec in summary.values()]
    sw = [rec['G']['sun_b2'] <= 45 for rec in summary.values()]
    log('# direction of G b2: tailward (<=45 deg of PsAng or PsAMV) in %d of %d visit-pairs; sunward (<=45 deg of PsAng+180) in %d' % (sum(tw), len(tw), sum(sw)))
    json.dump(summary, open(os.path.join(HERE, 'H3_SUMMARY_2026-09-27.json'), 'w'), indent=0)


if __name__ == '__main__':
    main(sys.argv[1])
