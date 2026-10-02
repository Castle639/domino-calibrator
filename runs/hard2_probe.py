"""Round 2's bar, measured case by case on today's code (the first failing assertion in a test hides the rest).
the second hardening round's record of 28 Sept 2026, not in this repository. Run from the repository: PYTHONPATH=. python calibrator/runs/hard2_probe.py
(with PLAYWRIGHT_MODULE and node on PATH, as the tests). Writes nothing but temporary files."""
import os, json, tempfile, warnings, io, contextlib
warnings.simplefilter('ignore')
import numpy as np
from astropy.io import fits
from calibrator import ades as A, cli
from calibrator.shrink import shrink
from calibrator.tests.test_hardening import pig, comet, write, run_main, REC
from calibrator.tests.test_hardening_page import js
from calibrator.tests.test_hardening_2 import H, lookup_file
from calibrator.tests import test_hardening_2_page as P2
d = tempfile.mkdtemp()
def show(tag, v): print('%-58s %s' % (tag, str(v)[:150]))
# 1.5: each start
img, _ = comet(); p = write(os.path.join(d, 'c.fits'), img)
for x in ('inf', '-inf', 'nan'):
    rc, out = run_main([p, '--x=' + x, '--y', '20', '--background', '100'])
    said = [l for l in out.splitlines() if 'cannot measure' in l] or [l for l in out.splitlines() if 'unconverged:' in l][:1]
    show('1.5 --x=%s' % x, 'rc %d | %s' % (rc, said[0] if said else out[:80]))
try: shrink(img, np.inf, 20.0, background=100.0); show('1.5 shrink(inf)', 'returned')
except Exception as e: show('1.5 shrink(inf)', '%s: %s' % (type(e).__name__, e))
# 1.11: four headers x two faces
PARSE = P2.PARSE
cases = [dict(DATE_OBS='2025-12-12T21:20:32.000', EXPTIME=None), dict(DATE_OBS='2025-12-12T21:20:32.000', EXPTIME=None, DATE_END='2025-12-12T21:22:32.000'),
         dict(MJD_OBS=None, EXPTIME=60.0), dict(DATE_AVG=None, DATE_OBS='2025-12-12T21:20:32.000', EXPTIME=60.0)]
for k, c in enumerate(cases):
    q = os.path.join(d, 'b%d.fits' % k); fits.PrimaryHDU(np.zeros((8, 8), np.float32), header=H(**c)).writeto(q)
    page = js(PARSE + "out = Z.midExposure(Object.assign({}, h[0].header));", dict(p=q))
    try: py = A.mid_exposure(fits.getheader(q))[0]
    except Exception as e: py = 'refused (%s)' % type(e).__name__
    show('1.11 case %d page | python' % (k + 1), '%s | %s' % (page.get('time') or 'refused: ' + page.get('error', ''), py))
# 1.12: the two PCOUNT files
for pc in (-3100, -100000):
    q = os.path.join(d, 'negp%d.fits' % -pc)
    h0 = fits.Header([('SIMPLE', True), ('BITPIX', 8), ('NAXIS', 0), ('EXTEND', True)])
    h1 = fits.Header([('XTENSION', 'IMAGE'), ('BITPIX', 16), ('NAXIS', 2), ('NAXIS1', 10), ('NAXIS2', 10), ('PCOUNT', pc), ('GCOUNT', 1)])
    open(q, 'wb').write(h0.tostring().encode('ascii') + h1.tostring().encode('ascii') + b'\0' * 2880 * 4)
    try: show('1.12 PCOUNT %d' % pc, P2.js_capped(PARSE + "out = h.length;", dict(p=q)))
    except AssertionError as e: show('1.12 PCOUNT %d' % pc, [l for l in str(e).split('\n') if 'Error' in l or 'memory' in l.lower() or 'failed' in l][:2])
# 4.5 engine: the colour cube, and the CLI on the .fz
im16 = np.round(pig(41, 20.2, 19.9, 1.5, amp=3e4) + 150.0).astype(np.int16)
fz = os.path.join(d, 'c.fits.fz'); fits.HDUList([fits.PrimaryHDU(), fits.CompImageHDU(im16)]).writeto(fz)
rgb = os.path.join(d, 'rgb.fits'); fits.PrimaryHDU(np.stack([im16] * 3)).writeto(rgb)
show('4.5 page parse rgb: unreadable', js(PARSE + "out = h.map(u => u.unreadable || null);", dict(p=rgb)))
show('4.5 CLI on the .fz: x0', cli.measure_file(fz, x=20.0, y=20.0, estimator='M')['x0'])
# 4.6 page: each remedy
TAN = P2.TAN
cr = [dict(CTYPE1='RA---TPV', CTYPE2='DEC--TPV'), dict(CTYPE1='RA---ZPN', CTYPE2='DEC--ZPN'), dict(PV1_1=1.0, PV2_1=1.0),
      dict(A_ORDER=2, B_ORDER=2, A_2_0=1e-5), dict(CTYPE1='DEC--TAN', CTYPE2='RA---TAN'), dict(CPDIS1='LOOKUP', CPDIS2='LOOKUP'), dict(RADESYS='FK4', EQUINOX=1950.0)]
for c, v in zip(cr, P2.wcs_verdicts(TAN, cr)): show('4.6 page WCS %s' % list(c.items())[0][1], v)
show('4.6 page TIMESYS TT', js("out = Z.midExposure({'DATE-OBS': '2025-12-12T21:20:32.000', EXPTIME: 60, TIMESYS: 'TT'});"))
show('4.6 page mode empty', js("out = Z.adesPSV(" + P2.REC_T + ", {mode: ''}));", P2.REC_JS).get('error', '')[-120:])
b64 = os.path.join(d, 'b64.fits'); fits.PrimaryHDU(np.ones((21, 21), np.int64)).writeto(b64)
show('4.6 page BITPIX 64', js(PARSE + "out = h[0].unreadable || '';", dict(p=b64)))
# the CLI's judge case 1 (edge) today
rc, out = run_main([write(os.path.join(d, 'edge.fits'), pig(41, 35.3, 20.2, 1.6, amp=3e4) + 150.0), '--x', '35', '--y', '20'] + __import__('calibrator.tests.test_hardening', fromlist=['REC_ARGS']).REC_ARGS)
show('judge case 1 (edge): a record?', '# version=2022' in out)
# the browser sessions, step by step
T = P2.TestPageInBrowser2; T.setUpClass()
for name, c in T.res.items():
    for k, s in enumerate(c.get('steps', [])):
        first = (s['ades'].strip().split('\n') or [''])[0]
        show('browser %s step %d' % (name, k), 'copy %s | ades "%s" | status "%s" | info "%s" | note "%s"' % (
            'off' if s['copyDisabled'] else 'ON', first[:30], s['status'][:40], s['info'][:45], s['hdrnote'][:60]))
    if c.get('errors') or c.get('timeout') or c.get('error'): show('browser %s: page errors' % name, (c.get('errors'), c.get('timeout'), c.get('error')))
T.tearDownClass()
