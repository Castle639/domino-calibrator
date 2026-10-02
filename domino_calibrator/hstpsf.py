"""Hubble's PSF for the calibrator: TinyTim WFC3/UVIS2 F350LP through the Castle's psfkit recipe
(tools/psfkit.py), with one change: the despace answer is a parameter, and never exactly 0.

TinyTim 7.5 drops its whole focus term - despace and field focus - at despace exactly 0 (a private
record of 21 Sept 2026, the star of 25 Sept); +-0.001 um restores the smooth curve. psfkit.tinytim()
answers 0; here the default is 0.001.
"""
import os, re, subprocess, sys
import numpy as np

# psfkit: tools/ at the repository's root, beside this package; or, where the repository is a folder inside a larger tree
# that keeps it (the Castle), the tree's own tools/, beside the folder
_REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
_TOOLS = next((d for d in (os.path.join(_REPO, 'tools'), os.path.join(os.path.dirname(_REPO), 'tools'))
               if os.path.isfile(os.path.join(d, 'psfkit.py'))), os.path.join(_REPO, 'tools'))
if _TOOLS not in sys.path:
    sys.path.insert(0, _TOOLS)
import psfkit  # noqa: E402

__all__ = ['tinytim_psf']


def tinytim_psf(x, y, despace=0.001, spec=11, sub=5, work=None, name=None):
    """Run tiny1/tiny2/tiny3 at chip position (x, y) (UVIS2, F350LP, list spectrum `spec`, 3.0" diameter).
    Returns dict(S=subsampled optical PSF (sum 1, odd size, peak at the centre), sub, kernels=(weighted_kernel,
    kernel_xy) - TinyTim's own post-binning charge-diffusion pair, param=path, fits=path)."""
    if despace == 0:
        raise ValueError('despace exactly 0 drops TinyTim\'s focus term; use +-0.001')
    work = work or os.path.join(os.environ['HOME'], 'calib_work', 'tinytim')
    name = name or ('cal%d_%d_d%s_s%d' % (x, y, ('%+.3f' % despace).replace('+', 'p').replace('-', 'm').replace('.', ''), sub))
    d = os.path.join(work, name); os.makedirs(d, exist_ok=True)
    out, par = os.path.join(d, name + '00.fits'), os.path.join(d, name + '.param')
    if not os.path.exists(out):
        env = dict(os.environ, TINYTIM=psfkit.TT)
        ans = '22\n2\n%d %d\nf350lp\n1\n%d\n3.0\n%g\n%s\n' % (x, y, spec, despace, name)
        subprocess.run([os.path.join(psfkit.TT, 'tiny1'), name + '.param'], input=ans, text=True, encoding='utf-8', cwd=d, env=env, capture_output=True, check=True)
        txt = open(par, encoding='utf-8').read()
        assert re.search(r'^%d %d +# Position 1' % (x, y), txt, re.M), 'position line'
        subprocess.run([os.path.join(psfkit.TT, 'tiny2'), name + '.param'], cwd=d, env=env, capture_output=True, check=True)
        subprocess.run([os.path.join(psfkit.TT, 'tiny3'), name + '.param', 'SUB=%d' % sub], cwd=d, env=env, capture_output=True, check=True)
    from astropy.io import fits
    S = fits.open(out)[0].data.astype(np.float64)
    if S.shape[0] % 2 == 0:
        S = S[:-1, :-1]
    S = S / S.sum()
    p = psfkit.read_param(par)
    wk = psfkit.weighted_kernel(p); kxy, _ = psfkit.kernel_xy(p)
    z4 = re.search(r'^\s*([-\d.eE+]+)\s+# Z4', open(par, encoding='utf-8').read(), re.M)
    return dict(S=S, sub=sub, kernels=(wk, kxy), param=par, fits=out, z4=float(z4.group(1)) if z4 else None)
