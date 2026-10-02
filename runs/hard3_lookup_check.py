"""Round 3, item 4's own bar, measured (the third hardening round's record of 28 Sept 2026, not in this repository, bar item 3): the page's WCS with
HST's lookup tables (page/zeroap.js, through Node) against astropy 6.1.7's (the command line's), on SCI,1 of the first
frame of each visit and on the three synthetic files of test_hardening_3_page, on a 15 x 15 grid off the integers that
runs through the tables' clamped edges. Then mutants of the page, each on a copy in the scratchpad, which must fail the
bar (10 microarcseconds) where they differ enough to matter: (a) no D2IM tables; (b) the tables' index off by one (the
"- 1" of 1-based pixels dropped); (c) CPDIS read at the raw pixel rather than the D2IM-corrected one, recorded as it is.
    PYTHONPATH=. python calibrator/runs/hard3_lookup_check.py SCRATCH LOG
"""
import json, os, subprocess, sys, tempfile, time, warnings
warnings.simplefilter('ignore')
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from calibrator.tests.test_hardening_2 import lookup_file
from calibrator.tests.test_hardening_3_page import rich_lookup_file, sky_arcsec, FRAMES, frame

SCRATCH, LOG = sys.argv[1], sys.argv[2]
NODE = '/opt/node22/bin/node'
PAGE = os.path.abspath('calibrator/page/zeroap.js')
BAR = 1e-5
MUTANTS = [('(a) no D2IM tables', 'if (tables.D2IMDIS1 || tables.D2IMDIS2) {', 'if (false) {'),
           ('(b) the index off by one', '+ T.crpix[k]) - 1.0;', '+ T.crpix[k]);'),
           ('(c) CPDIS at the raw pixel', "if (tables.CPDIS1) fx += lookupOffset(tables.CPDIS1, [X, Y]);\n        if (tables.CPDIS2) fy += lookupOffset(tables.CPDIS2, [X, Y]);",
            "if (tables.CPDIS1) fx += lookupOffset(tables.CPDIS1, [x + 1, y + 1]);\n        if (tables.CPDIS2) fy += lookupOffset(tables.CPDIS2, [x + 1, y + 1]);")]


def page_sky(js, path, ext, pts):
    d = tempfile.mkdtemp(dir=SCRATCH); p = os.path.join(d, 'c.json'); json.dump(dict(p=path, i=ext, pts=pts), open(p, 'w'))
    code = ("const Z = require(%s); const D = JSON.parse(require('fs').readFileSync(%s, 'utf8'));"
            "const b = require('fs').readFileSync(D.p); const h = Z.parseFITS(b.buffer.slice(b.byteOffset, b.byteOffset + b.byteLength));"
            "const w = Z.makeWCS(h[D.i].header, h[0].header, h);"
            "console.log(JSON.stringify(!w ? null : w.unsupported ? {u: w.unsupported} : {pts: D.pts.map(q => w.pixToSky(q[0], q[1])), notes: w.notes}));"
            % (json.dumps(js), json.dumps(p)))
    return json.loads(subprocess.run([NODE, '-e', code], capture_output=True, text=True, check=True).stdout)


def astropy_sky(path, ext, pts):
    with fits.open(path) as f:
        return WCS(f[ext].header, fobj=f).all_pix2world(pts, 0)


def grid(nx, ny, lo=-3.0):
    xs = np.linspace(lo, nx - 1 - lo, 15) + 0.137
    ys = np.linspace(lo, ny - 1 - lo, 15) + 0.291
    return [[float(x), float(y)] for x in xs for y in ys]


out = open(LOG, 'w')
say = lambda s: (out.write(s + '\n'), out.flush(), print(s))
say('# round 3, item 4: the page against astropy with HST\'s lookup tables, %s UTC | bar %.0e" | zeroap.js sha256 %s'
    % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()), BAR, subprocess.run(['sha256sum', PAGE], capture_output=True, text=True).stdout[:12]))
cases = [(root, frame(root), 1, grid(2047, 2050)) for root in FRAMES]
d = tempfile.mkdtemp(dir=SCRATCH)
cases += [('synthetic: round 2\'s lookup_file', lookup_file(os.path.join(d, 'lookup.fits')), 0, grid(71, 71, -8.0)),
          ('synthetic: SIP, D2IM, CPDIS', rich_lookup_file(os.path.join(d, 'rich.fits')), 0, grid(71, 71, -8.0)),
          ('synthetic: the same, DP1 transposed', rich_lookup_file(os.path.join(d, 'richT.fits'), transpose=True), 0, grid(71, 71, -8.0))]
want = {name: astropy_sky(p, ext, pts) for name, p, ext, pts in cases}
say('## the page as committed: max and median distance to astropy over %d points per file (microarcseconds)' % len(cases[0][3]))
for name, p, ext, pts in cases:
    o = page_sky(PAGE, p, ext, pts)
    if 'pts' not in (o or {}):
        say('%-38s | REFUSED: %s' % (name, o)); continue
    dd = sky_arcsec(o['pts'], want[name]) * 1e6
    say('%-38s | max %9.4f | median %9.4f | %s | notes: %s' % (name, dd.max(), np.median(dd), 'PASS' if dd.max() / 1e6 <= BAR else 'FAIL', '; '.join(o['notes'])))
say('## the mutants, each must fail the bar where it differs enough to matter (max over the grid, microarcseconds)')
src = open(PAGE, encoding='utf-8').read()
for label, old, new in MUTANTS:
    assert src.count(old) == 1, label
    mp = os.path.join(d, 'zeroap_mutant.js'); open(mp, 'w', encoding='utf-8').write(src.replace(old, new))
    row = []
    for name, p, ext, pts in cases:
        o = page_sky(mp, p, ext, pts)
        dd = sky_arcsec(o['pts'], want[name]) * 1e6
        row.append('%s %.4g' % (name.split(':')[-1].strip(), dd.max()))
    say('%-30s | %s' % (label, ' | '.join(row)))
say('# done')
