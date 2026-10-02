#!/usr/bin/env python3
"""How long, and how much memory, one run of the command line takes on a whole camera frame (the fix room's F3, item 13: the
audit's F1.24, a whole frame took 34-47 s and 1.3 GB a run, and the README said no size or time). The frame is made here the
audit room's way (its confirm_wave3_logs/C1_mkwhole.py, frame w6248: a comet, a saturated star and 29 other stars on a
6248 x 4176 uint16 frame, a SIP WCS at 0.78"/px), written to a temporary folder, and measured from the comet's position by
the command line in a child process, twice: its wall time, and its peak memory (the child's maximum resident set size, from
getrusage). The record's last line is the README's phrase, the larger of the two runs, rounded.

  python runs/fix_f3_whole_frame.py LOG      from the repository's root
"""
import os, sys, time, shutil, tempfile, resource, subprocess
import numpy as np
from astropy.io import fits

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
from domino_calibrator import synth

SKY, RN, FW = 1000.0, 10.0, 3.0
SIG = FW / 2.3548200450309493


def gauss_add(img, x, y, peak):
    n = 12; ix, iy = int(round(x)), int(round(y))
    y0, y1, x0, x1 = max(iy - n, 0), min(iy + n + 1, img.shape[0]), max(ix - n, 0), min(ix + n + 1, img.shape[1])
    yy, xx = np.mgrid[y0:y1, x0:x1]
    img[y0:y1, x0:x1] += peak * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * SIG * SIG))


def frame(path, nx=6248, ny=4176, comet=(4800.3, 3100.6), sat=(2000.4, 1500.7), seed=11, crval=(120.55, 28.45)):
    """The audit room's w6248, as its C1_mkwhole.py makes it; returns the comet's position."""
    rng = np.random.default_rng(seed)
    img = np.zeros((ny, nx))
    n = 101; ix, iy = int(round(comet[0])) - 50, int(round(comet[1])) - 50
    st, (xt, yt) = synth.render(n, comet[0] - ix, comet[1] - iy, flux_n=1.0, k=1.0, a=0.3, theta=0.6, psf=('gauss', FW))
    st *= 1500.0 / st.max()
    img[iy:iy + n, ix:ix + n] += st
    gauss_add(img, sat[0], sat[1], 300000.0)
    for k in range(29):
        while True:
            x, y = rng.uniform(40, nx - 40), rng.uniform(40, ny - 40)
            if min(np.hypot(x - comet[0], y - comet[1]), np.hypot(x - sat[0], y - sat[1])) > 80:
                break
        gauss_add(img, x, y, rng.uniform(3000, 20000) if k < 5 else rng.uniform(50, 1000))
    raw = rng.poisson(np.clip(img + SKY, 0, None)).astype(float) + rng.normal(0.0, RN, img.shape)
    data = np.clip(np.round(raw), 0, 65535).astype(np.uint16)
    s = 0.78 / 3600.0; th = np.radians(1.3)
    h = fits.Header()
    for k2, v in (('WCSAXES', 2), ('CTYPE1', 'RA---TAN-SIP'), ('CTYPE2', 'DEC--TAN-SIP'), ('EQUINOX', 2000.0), ('LONPOLE', 180.0), ('LATPOLE', 0.0),
                  ('CRVAL1', crval[0]), ('CRVAL2', crval[1]), ('CRPIX1', nx / 2 + 0.5), ('CRPIX2', ny / 2 + 0.5), ('CUNIT1', 'deg'), ('CUNIT2', 'deg'),
                  ('CD1_1', -s * np.cos(th)), ('CD1_2', s * np.sin(th)), ('CD2_1', s * np.sin(th)), ('CD2_2', s * np.cos(th)),
                  ('A_ORDER', 2), ('A_0_2', 2.1e-7), ('A_1_1', -1.3e-7), ('A_2_0', 3.0e-7), ('B_ORDER', 2), ('B_0_2', -2.4e-7), ('B_1_1', 1.1e-7), ('B_2_0', 1.6e-7),
                  ('DATE-OBS', '2026-10-01T01:10:00.000'), ('EXPTIME', 90.0)):
        h[k2] = v
    fits.PrimaryHDU(data, h).writeto(path, overwrite=True)
    return ix + xt, iy + yt


def main():
    log = open(sys.argv[1], 'w', encoding='utf-8')

    def say(s):
        print(s); log.write(s + '\n'); log.flush()
    head = os.popen('git -C %s rev-parse --short HEAD' % ROOT).read().strip()
    d = tempfile.mkdtemp()
    try:
        p = os.path.join(d, 'w6248.fits')
        cx, cy = frame(p)
        mpx = 6248 * 4176 / 1e6
        say('# fix_f3_whole_frame | HEAD %s | %s | the frame 6248 x 4176, %.1f Mpx, uint16, %.1f MB on disk | the comet at (%.2f, %.2f)'
            % (head, sys.version.split()[0], mpx, os.path.getsize(p) / 1e6, cx, cy))
        runs = []
        for k in range(2):
            before = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
            t0 = time.perf_counter()
            r = subprocess.run([sys.executable, '-m', 'domino_calibrator.cli', p, '--x', '%.2f' % cx, '--y', '%.2f' % cy],
                               cwd=ROOT, capture_output=True, encoding='utf-8', errors='replace')
            t = time.perf_counter() - t0
            peak = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss       # kB on Linux; the largest child so far
            gb = peak * (1 if sys.platform == 'darwin' else 1024) / 1e9
            zero = next((ln for ln in r.stdout.splitlines() if ln.startswith('# zero aperture:')), '(none)')
            say('run %d: exit %d, %.1f s, peak memory %.2f GB (the children\'s largest so far; before it %.2f GB) | %s' % (
                k + 1, r.returncode, t, gb, before * (1 if sys.platform == 'darwin' else 1024) / 1e9, zero[:80]))
            runs.append((t, gb))
        t = max(x[0] for x in runs); gb = max(x[1] for x in runs)
        say('README: on a %.0f Mpx frame, one run took about %.0f s and %.1f GB of memory' % (mpx, t, gb))
    finally:
        shutil.rmtree(d, ignore_errors=True)


if __name__ == '__main__':
    main()
