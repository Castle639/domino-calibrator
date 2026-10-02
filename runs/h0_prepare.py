#!/usr/bin/env python3
"""H0 - Hubble's 3I frames prepared. Bar: archive/CALIBRATOR_2026-09-27.md, section H0 (committed before this ran).

The 30 unsaturated 170 s F350LP frames of HST 18152 visits 22, 03-06 (data/hst-3i/, sha256-checked by fetch_frames).
Per frame: the peak near CRPIX (a 25x25 coarse stage, then K0's 5x5 peak within +-10 px; K0's pass 2 for a frame
> 20 px from its visit's median) against K0's centroids; cutout +-640 px about its
dither position's first peak; the sibling clean (5 sigma, grow 2 sigma, core r <= 5 px untouched, hits counted);
DQ-flagged pixels are kept (their values are normal: 18:16 UTC look, median z 0.00, 0.2 % > 5 sigma).
The HST-resolution reference: G, M on the published radii (2.0-6.0 HST px, annulus 2.5r-5r) and P. The reference
point is G's zero-aperture position. The sky map (cubic, full WCS) about it; the cutout resampled to 0.02 arcsec,
north up, east left, +-24 arcsec, through the full WCS on a 10-px node grid (GridMap; H0 run 2's cubic missed the lookup
tables by 0.07 px), the map checked at 2000 random points, flux-checked at r = 10 arcsec. JPL Horizons: PsAng, PsAMV, r, delta, phase angle at
each visit's mid-exposure time, observer HST (@-48).
Outputs: the log; runs/H0_FRAMES_2026-09-27.json (per frame: groups, positions, stats, the map);
$HOME/calib_work/sky_<root>.npz (float32 sky images, not in the repo); data/hst-3i/horizons/3I_from_HST_psang_2026-09-27.txt.
"""
import sys, os, time, json, re, subprocess, urllib.parse
import numpy as np
from multiprocessing import Pool

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))       # the repository's root, where domino_calibrator is
from domino_calibrator import hst, shrink, peak_quadratic, PUBLISHED_RADII
from domino_calibrator.apertures import circle_moments

WORK = os.path.join(os.environ['HOME'], 'calib_work')
H = 640
S_FINE, HALF = 0.02, 24.0
VISITS = ['22', '03', '04', '05', '06']


def k0_positions():
    """The 30 frames and the position each peak is checked against (H0.1), from runs/H0_POSITIONS_2026-09-30.txt (the launch
    list's step 6: the same frames and floats H0 read before, so that H0 reads nothing outside the repository)."""
    ref = {}
    for ln in open(os.path.join(HERE, 'H0_POSITIONS_2026-09-30.txt')):
        if ln.strip() and not ln.startswith('#'):
            f = ln.split(); ref[f[0]] = (float(f[1]), float(f[2]))
    return ref


def reference(cut, px, py):
    p = peak_quadratic(cut, px, py)
    out = {'P': (p['x'], p['y'], p['ok'])}
    for est in ('G', 'M'):
        o = shrink(cut, p['x'], p['y'], radii=PUBLISHED_RADII, estimator=est)
        out[est] = dict(x0=o['x0'], y0=o['y0'], x2=o['x2'], y2=o['y2'], x6=o['x6'], y6=o['y6'], sx=o['sx'], sy=o['sy'], nbad=o['nbad'],
                        s=o['s'].tolist() if est == 'G' else None)
    return out


def prep_group(args):
    gname, roots, peaks = args
    frames = [hst.load(r) for r in roots]
    for f in frames:
        f['px'], f['py'] = peaks[f['root']]
    X0, Y0 = frames[0]['px'] - H, frames[0]['py'] - H
    cuts = [f['sci'][Y0:Y0 + 2 * H + 1, X0:X0 + 2 * H + 1] - f['sky'] for f in frames]
    errs = [f['err'][Y0:Y0 + 2 * H + 1, X0:X0 + 2 * H + 1] for f in frames]
    clean, stats = hst.clean_group(cuts, errs, (H, H))
    out = []
    for f, c, st in zip(frames, clean, stats):
        pxc, pyc = f['px'] - X0, f['py'] - Y0
        ref = reference(c, pxc, pyc)
        xr, yr = ref['G']['x0'], ref['G']['y0']
        smap = hst.SkyMap(f['wcs'], xr + X0, yr + Y0, X0, Y0, H - 8, step=32)     # the local Jacobian, reported
        gmap = hst.GridMap(f['wcs'], xr + X0, yr + Y0, X0, Y0, S_FINE, HALF, step=10)
        map_err = gmap.check()
        sky, (m, _) = hst.resample_grid(c, gmap)
        # flux check at r = 10 arcsec: detector pixels whose centres map within 10" vs the sky grid's exact aperture
        yy, xx = np.indices(c.shape)
        sk = f['wcs'].all_pix2world(np.stack([(xx + X0).ravel().astype(float), (yy + Y0).ravel().astype(float)], axis=1), 0)
        xi = ((sk[:, 0] - gmap.ra0 + 180.0) % 360.0 - 180.0) * np.cos(np.radians(gmap.de0)) * 3600.0
        eta = (sk[:, 1] - gmap.de0) * 3600.0
        sel = np.hypot(xi, eta).reshape(c.shape) < 10.0      # the full WCS, independent of the polynomial
        F_det = float(c[sel].sum())
        sl, A, _, _ = circle_moments(m, m, 10.0 / S_FINE, sky.shape)
        F_sky = float((np.nan_to_num(sky[sl]) * A).sum())
        np.savez_compressed(os.path.join(WORK, 'sky_%s.npz' % f['root']), sky=sky.astype(np.float32), m=m)
        J = smap.J
        orient = float(np.degrees(np.arctan2(J[0, 1], J[1, 1])))   # sky PA of the detector +y axis, E of N
        out.append(dict(root=f['root'], visit=f['visit'], group=gname, expstart=f['expstart'], exptime=f['exptime'], mdrizsky=f['sky'],
                        peak=(int(f['px']), int(f['py'])), cut_origin=(int(X0), int(Y0)), clean=st, ref=ref,
                        ref_full=(xr + X0, yr + Y0), radec_ref=(gmap.ra0, gmap.de0), map_resid_px=map_err, poly_resid_px=smap.resid, J=J.tolist(),
                        scale=(float(np.hypot(*J[:, 0])), float(np.hypot(*J[:, 1]))), skew_deg=float(np.degrees(np.arccos(J[:, 0] @ J[:, 1] / np.hypot(*J[:, 0]) / np.hypot(*J[:, 1]))) - 90),
                        det_y_pa=orient, flux10_det=F_det, flux10_sky=F_sky))
    return out


def horizons(times_jd):
    q = dict(format='text', COMMAND="'DES=C/2025 N1;CAP;NOFRAG'", OBJ_DATA='NO', MAKE_EPHEM='YES', EPHEM_TYPE='OBSERVER',
             CENTER="'500@-48'", TLIST="'" + ' '.join('%.6f' % t for t in times_jd) + "'", TLIST_TYPE='JD', TIME_TYPE='UT',
             QUANTITIES="'1,19,20,24,27'", CSV_FORMAT='YES', ANG_FORMAT='DEG')
    url = 'https://ssd.jpl.nasa.gov/api/horizons.api?' + urllib.parse.urlencode(q)
    r = subprocess.run(['curl', '-sS', '-f', '--max-time', '120', url], capture_output=True, text=True)
    return url, r.returncode, r.stdout, r.stderr


if __name__ == '__main__':
    os.makedirs(WORK, exist_ok=True)
    logf = open(sys.argv[1], 'w')
    def log(s):
        print(s, flush=True); logf.write(s + '\n'); logf.flush()
    log('# H0 %s | runs/h0_prepare.py | commit %s' % (time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()),
        os.popen('git -C %s log -1 --format=%%h' % os.path.dirname(HERE)).read().strip()))
    t0 = time.time()
    k0 = k0_positions()
    roots = sorted(k0)                 # programme 18152's visits 22 and 03-06, the 170 s exposures: the positions file's frames
    log('# frames: %d (%s)' % (len(roots), ' '.join(roots)))
    # dither groups from peaks (cheap: peak only)
    pk = []
    for r in roots:
        f = hst.load(r); x, y = hst.find_peak(f['sci'], f['hdr']['CRPIX1'] - 1, f['hdr']['CRPIX2'] - 1)
        pk.append(dict(root=r, visit=r[4:6], px=x, py=y, sci=f['sci']))
    re = hst.refind(pk)
    log('# pass 2 (K0\'s re-centring): re-found %s' % (re or 'none'))
    peaks = {d['root']: (int(d['px']), int(d['py'])) for d in pk}
    for d in pk:
        d.pop('sci')
    g = hst.dither_groups(pk)
    groups = {}
    for r in roots:
        groups.setdefault(g[r], []).append(r)
    log('# dither groups: ' + ' '.join('%s:%d' % (k, len(v)) for k, v in sorted(groups.items())))
    with Pool(4) as pool:
        res = [x for out in pool.map(prep_group, [(k, v, peaks) for k, v in sorted(groups.items())]) for x in out]
    res.sort(key=lambda d: d['root'])
    # ---- checks ----
    ok1 = ok3 = ok4 = True
    log('# per frame: peak vs K0 | clean: replaced px, flux e-, core hits | map resid px | scales "/px, skew deg | flux(10") sky/det | reference (cutout px): G0 - M0, G0 - P, G0 - G2 in mas (sky)')
    for d in res:
        kx, ky = k0[d['root']]
        dk = float(np.hypot(d['peak'][0] - kx, d['peak'][1] - ky)); ok1 &= dk <= 1.5
        ok3 &= d['map_resid_px'] < 0.01
        fr = d['flux10_sky'] / d['flux10_det']; ok4 &= abs(fr - 1) < 0.005
        J = np.array(d['J'])
        R = d['ref']; G, M = R['G'], R['M']
        def mas(dx, dy):
            v = J @ np.array([dx, dy]) * 1000.0; return '(%+.1f,%+.1f)' % (v[0], v[1])
        log('%s %s | peak-K0 %.2f px | clean %5d px %9.0f e- core %d | resid %.4f | %.5f %.5f skew %+.2f | flux %.5f | G0-M0 %s G0-P %s G0-G2 %s | nbad G %d M %d | G s(r=2) %.2f px' % (
            d['root'], d['group'], dk, d['clean']['replaced'], d['clean']['flux'], d['clean']['core_hits'], d['map_resid_px'],
            d['scale'][0], d['scale'][1], d['skew_deg'], fr, mas(G['x0'] - M['x0'], G['y0'] - M['y0']),
            mas(G['x0'] - R['P'][0], G['y0'] - R['P'][1]), mas(G['x0'] - G['x2'], G['y0'] - G['y2']), G['nbad'], M['nbad'], G['s'][0]))
    # within-position scatter of the reference (removing the group mean), in mas
    sc = []
    for gname, rs in groups.items():
        ds = [d for d in res if d['group'] == gname]
        if len(ds) < 2: continue
        P = np.array([np.array(d['J']) @ np.array(d['ref_full']) for d in ds]) * 1000.0
        sc.extend(list(np.hypot(*(P - P.mean(axis=0)).T)))
    log('# reference, within-position scatter about the group mean (mas, detector-fixed; includes any drift): median %.1f max %.1f' % (np.median(sc), np.max(sc)))
    # Horizons
    vis_t = {}
    for d in res:
        vis_t.setdefault(d['visit'], []).append(d['expstart'] + d['exptime'] / 2 / 86400.0)
    tjd = [np.mean(vis_t[v]) + 2400000.5 for v in VISITS]
    url, rc, txt, err = horizons(tjd)
    hz_path = os.path.join(hst.DATA, 'horizons', '3I_from_HST_psang_2026-09-27.txt')        # beside the frames
    open(hz_path, 'w').write('# ' + url + '\n' + txt)
    rows = []
    if rc == 0 and '$$SOE' in txt:
        body = txt.split('$$SOE')[1].split('$$EOE')[0].strip().splitlines()
        for v, line in zip(VISITS, body):
            c = [s.strip() for s in line.split(',')]
            rows.append((v, c))
        log('# Horizons (observer HST @-48): %d rows; raw in %s' % (len(rows), os.path.relpath(hz_path, os.path.dirname(os.path.dirname(hst.DATA)))))
        for v, c in rows:
            log('  visit %s: %s' % (v, ' | '.join(c)))
    else:
        log('# Horizons FAILED rc %d %s' % (rc, err.strip()[:200]))
    json.dump(dict(frames=res, groups=groups, horizons=[(v, c) for v, c in rows]), open(os.path.join(HERE, 'H0_FRAMES_2026-09-27.json'), 'w'), indent=0, default=float)
    log('# H0.3 map: GridMap vs the full WCS at 2000 random points, max over frames %.4f px (the old cubic: %.4f px)' % (max(d['map_resid_px'] for d in res), max(d['poly_resid_px'] for d in res)))
    log('# H0.1 peaks within 1.5 px of K0: %s | H0.3 map residual < 0.01 px: %s | H0.4 flux(10") within 0.5 %%: %s | H0.6 Horizons 5 rows: %s' % (
        'PASS' if ok1 else 'FAIL', 'PASS' if ok3 else 'FAIL', 'PASS' if ok4 else 'FAIL', 'PASS' if len(rows) == 5 else 'FAIL'))
    log('# done in %.0f s' % (time.time() - t0))
