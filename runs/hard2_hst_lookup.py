"""Round 2, 1.18 on the study's own frames (the second hardening round's record of 28 Sept 2026, not in this repository): HST's lookup-table WCS
(CPDIS, D2IMDIS) through both faces, before (b5b6be4) and after round 2. For each first frame of a visit, SCI,1: the
command line's WCS (calibrator.ades.celestial, with and without the open file), the page's makeWCS (zeroap.js, then and
now) on the same header cards, and how far the page's SIP-only position of b5b6be4 lay from the full WCS, at five
pixels across the chip. Needs the frames (tools/fetch_frames.py) and, for "then", b5b6be4's zeroap.js and ades.py:
    git show b5b6be4:calibrator/page/zeroap.js > OLD/zeroap_b5b6be4.js; git show b5b6be4:calibrator/ades.py > OLD/ades_b5b6be4.py
    PYTHONPATH=. python calibrator/runs/hard2_hst_lookup.py OLD
"""
import importlib.util, json, os, subprocess, sys, tempfile, time, warnings
warnings.simplefilter('ignore')
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from calibrator import ades as A

OLD = sys.argv[1]
NODE = '/opt/node22/bin/node'
spec = importlib.util.spec_from_file_location('ades_old', os.path.join(OLD, 'ades_b5b6be4.py'))
A_old = importlib.util.module_from_spec(spec); spec.loader.exec_module(A_old)
PTS = [[100.0, 100.0], [2048.0, 1024.0], [4000.0, 100.0], [100.0, 1950.0], [4000.0, 1950.0]]


def page(js, cards, pts):
    d = tempfile.mkdtemp(); p = os.path.join(d, 'c.json'); json.dump(dict(h=cards, pts=pts), open(p, 'w'))
    code = ("const Z = require(%s); const D = JSON.parse(require('fs').readFileSync(%s, 'utf8')); const w = Z.makeWCS(D.h);"
            "console.log(JSON.stringify(!w ? null : w.unsupported ? {u: w.unsupported} : {pts: D.pts.map(q => w.pixToSky(q[0], q[1]))}));"
            % (json.dumps(js), json.dumps(p)))
    return json.loads(subprocess.run([NODE, '-e', code], capture_output=True, text=True, check=True).stdout)


def cards(h):                                      # the header as the page's parser keeps it: numbers, strings, booleans
    return {c.keyword: (c.value if isinstance(c.value, (int, float, bool, str)) else None) for c in h.cards if c.keyword not in ('', 'COMMENT', 'HISTORY')}


print('# 1.18 on HST frames, %s UTC | SCI,1 of the first frame of each visit' % time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()))
for root in ('ifle03geq', 'ifle04pdq', 'ifle05qlq', 'ifle06tjq', 'ifle22f7q'):
    path = os.path.join('data', 'hst-3i', root + '_flc.fits')
    with fits.open(path) as f:
        h = f[1].header.copy()
        try:
            A_old.celestial(h); then = 'read'
        except ValueError as e:
            then = 'refused: ' + str(e)[:70]
        w, _ = A.celestial(h, fobj=f)
        full = w.all_pix2world(PTS, 0)
    keys = sorted(k for k in h if k.startswith(('CPDIS', 'D2IMDIS')))
    old = page(os.path.join(OLD, 'zeroap_b5b6be4.js'), cards(h), PTS)
    new = page(os.path.abspath('calibrator/page/zeroap.js'), cards(h), PTS)
    if old and 'pts' in old:
        g = np.array(old['pts']); d = np.hypot((g[:, 0] - full[:, 0]) * np.cos(np.radians(full[:, 1])), g[:, 1] - full[:, 1]) * 3600
        oldtxt = 'MEASURED, %.3f-%.3f" from the full WCS (median %.3f")' % (d.min(), d.max(), np.median(d))
    else:
        oldtxt = str(old)
    print('%s | %s | command line then: %s; now: read, with the tables | page then: %s | page now: %s'
          % (root, ' '.join('%s=%s' % (k, h[k]) for k in keys), then, oldtxt, (new or {}).get('u', new)))
