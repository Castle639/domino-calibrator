#!/usr/bin/env python3
"""S0(a) toy - the expected value, measured OUTSIDE the pipeline (no pixels, no PSF, no calibrator code).

Scene: I(rho, theta) = k/rho (1 + a cos theta), nucleus at the origin. The self-centred moment photocentre in
a circle of radius r is the c on the x axis with  int_{A(c)} (x - c) I dA = 0.  In polar coordinates about the
nucleus the circle (centre (c, 0), radius r > c) is rho < R(theta) = c cos(theta) + sqrt(r^2 - c^2 sin^2 theta), so
    g(c) = k int_0^{2 pi} (1 + a cos t) [cos t R(t)^2 / 2 - c R(t)] dt = 0,
one integral in theta, solved for c by brentq. Scale-free: c/r depends on a only. First order: c = a r / 2.
Also the nucleus-centred moment (aperture fixed on the nucleus): a r / 4 exactly.
Log: runs/s0a_toy_RUNLOG_2026-09-27.txt
"""
import sys, time
import numpy as np
from scipy.integrate import quad
from scipy.optimize import brentq


def g(c, r, a):
    R = lambda t: c * np.cos(t) + np.sqrt(r * r - (c * np.sin(t)) ** 2)
    f = lambda t: (1 + a * np.cos(t)) * (np.cos(t) * R(t) ** 2 / 2 - c * R(t))
    return quad(f, 0, 2 * np.pi, epsabs=1e-13, epsrel=1e-13, limit=200)[0]


def fixed_point(r, a):
    return brentq(lambda c: g(c, r, a), 0.0, 0.99 * r, xtol=1e-14, rtol=1e-14)


def nucleus_centred(r, a):
    num = quad(lambda t: (1 + a * np.cos(t)) * np.cos(t) * r * r / 2, 0, 2 * np.pi, epsabs=1e-14)[0]
    den = quad(lambda t: (1 + a * np.cos(t)) * r, 0, 2 * np.pi, epsabs=1e-14)[0]
    return num / den


if __name__ == '__main__':
    out = open(sys.argv[1], 'w') if len(sys.argv) > 1 else None
    def log(s):
        print(s, flush=True)
        if out: out.write(s + '\n')
    log('# S0(a) toy %s | no pixels, no PSF, no calibrator import' % time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime()))
    for a in (0.1, 0.3, 0.6):
        for r in (1.0, 20.0, 60.0):
            c = fixed_point(r, a)
            log('a %.2f r %5.1f  self-centred fixed point c = %.10f  c/r = %.10f  (a/2 = %.4f, ratio %.6f)  nucleus-centred moment/r = %.10f (a/4 = %.4f)' % (
                a, r, c, c / r, a / 2, (c / r) / (a / 2), nucleus_centred(r, a) / r, a / 4))
