"""Found in round 2 (the second hardening round's record of 28 Sept 2026, not in this repository, "Found in this room"): PV terms on a TAN header, through
the command line's WCS (calibrator.ades.celestial, i.e. astropy). astropy turns a TAN header with PV terms into TPV only
when some PVi_j has j >= 5 (SCAMP's full solutions); below that, wcslib reads PVi_1 and PVi_2 on the longitude axis as
the projection's reference point (phi0, theta0), as the FITS standard defines them. The probe compares each case with
plain TAN and with the same terms under an explicit TPV header, at a pixel 30 px and 25 px from the reference pixel.
Run from the repository: PYTHONPATH=. python calibrator/runs/hard2_pv_probe.py
"""
import time, warnings
warnings.simplefilter('ignore')
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from calibrator.ades import celestial
from calibrator.tests.test_hardening import wcs_cards

h = wcs_cards(fits.Header(), n=71)                      # TAN, 1"/px, reference pixel (35, 35) 0-based
pt = [[5.0, 60.0]]
plain = WCS(h).all_pix2world(pt, 0)[0]


def arcsec(a, b):
    return float(np.hypot((a[0] - b[0]) * np.cos(np.radians(b[1])), a[1] - b[1]) * 3600)


print('# PV on TAN through the command line\'s WCS, %s UTC | pixel (5, 60), 39 px from the reference pixel' % time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()))
cases = [('PV1_1, PV2_1 = 1 alone', dict(PV1_1=1.0, PV2_1=1.0)),
         ('SCAMP first order: PV_0-PV_2 (identity)', dict(PV1_0=0.0, PV1_1=1.0, PV1_2=0.0, PV2_0=0.0, PV2_1=1.0, PV2_2=0.0)),
         ('SCAMP to index 5: + PV1_5 = PV2_5 = 0.01', dict(PV1_0=0.0, PV1_1=1.0, PV1_2=0.0, PV1_5=1e-2, PV2_0=0.0, PV2_1=1.0, PV2_2=0.0, PV2_5=1e-2))]
for name, c in cases:
    hh = h.copy(); hh.update(c)
    w, notes = celestial(hh)
    v = w.all_pix2world(pt, 0)[0]
    t = hh.copy(); t['CTYPE1'] = 'RA---TPV'; t['CTYPE2'] = 'DEC--TPV'
    vt = WCS(t).all_pix2world(pt, 0)[0]
    print('%-44s | from plain TAN %12.4f" | from the same terms as TPV %12.4f" | the command line\'s WCS notes: %s'
          % (name, arcsec(v, plain), arcsec(v, vt), notes or 'none'))
