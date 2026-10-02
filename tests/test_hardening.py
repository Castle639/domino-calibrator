"""The hardening round's bar, Python side (the hardening round's record of 27 Sept 2026, not in this repository): one test per in-scope finding,
written to fail on the calibrator as merged in c0ae330 and to pass once its fix is in. Findings are numbered as in
the first refuters' record of 27 Sept 2026, not in this repository (Annie's check tables). The contract under test: a stranger's image gets an
honest answer or an honest refusal. Estimators never raise; every radius carries ok and a reason; an unconverged radius
has no position; an ADES record is written only from real values, and it passes the MPC's own validator.

The MPC's judge (TestMPCJudge) runs IAU-ADES/ades-master's own scripts (psvtoxml, valsubmit) and its xsd/submit.xsd.
It needs ADES_PYLIB (a directory holding the installed `ades` package and lxml) and ADES_MASTER (a clone of
https://github.com/IAU-ADES/ades-master); without them it skips, and a bar run that skips it has not run it.
"""
import os, io, re, sys, json, shutil, tempfile, unittest, warnings, contextlib, subprocess
import numpy as np
from astropy.io import fits
from scipy.special import erf

from domino_calibrator import synth
from domino_calibrator.apertures import circle_moments
from domino_calibrator.estimators import moment_centroid, gauss_fit, peak_quadratic
from domino_calibrator.shrink import shrink, PUBLISHED_RADII
from domino_calibrator import ades as A
from domino_calibrator import cli

ADES_PYLIB = os.environ.get('ADES_PYLIB')
ADES_MASTER = os.environ.get('ADES_MASTER')

# the user's own values for an ADES record (all required; nothing defaults)
REC = dict(stn='568', desig='3I', mode='CCD', ast_cat='Gaia3', submitter='A. N. Observer', measurers=['A. N. Observer'],
           design='Reflector', aperture='0.5', detector='CCD')
REC_ARGS = ['--stn', '568', '--desig', '3I', '--mode', 'CCD', '--astcat', 'Gaia3', '--submitter', 'A. N. Observer',
            '--measurer', 'A. N. Observer', '--telescope-design', 'Reflector', '--telescope-aperture', '0.5',
            '--telescope-detector', 'CCD']


def pig(n, x0, y0, s, amp=1e5, ny=None):
    """A pixel-integrated circular Gaussian on an n x n (or ny x n) grid."""
    ny = ny or n
    ex, ey = np.arange(n + 1) - 0.5, np.arange(ny + 1) - 0.5
    gx = 0.5 * np.diff(erf((ex - x0) / (np.sqrt(2) * s)))
    gy = 0.5 * np.diff(erf((ey - y0) / (np.sqrt(2) * s)))
    return amp * np.outer(gy, gx)


def wcs_cards(h, n=71, rot90=False, scale=1.0 / 3600):
    h['CTYPE1'] = 'RA---TAN'; h['CTYPE2'] = 'DEC--TAN'; h['CRPIX1'] = (n + 1) / 2.0; h['CRPIX2'] = (n + 1) / 2.0
    h['CRVAL1'] = 168.7; h['CRVAL2'] = 4.6
    if rot90:        # x runs north, y runs west: the frame's rows are RA and its columns Dec
        h['CD1_1'] = 0.0; h['CD1_2'] = -scale; h['CD2_1'] = scale; h['CD2_2'] = 0.0
    else:
        h['CD1_1'] = -scale; h['CD1_2'] = 0.0; h['CD2_1'] = 0.0; h['CD2_2'] = scale
    return h


def comet(n=71):
    img, (xt, yt) = synth.render(n, 35.05, 34.95, flux_n=2e4, k=500.0, a=0.2, model='dipole', psf=('gauss', 3.0), sub=10)
    return img + 100.0, (xt, yt)


def start(path):
    """The automatic start's own position for the file (the brightest 5 x 5 box), to give as the observer's start: since F10
    (his cure for the second audit's B2') a record comes only from a start the observer gives, and the tests that took the
    automatic start's record give that same start, so that each measures what it measured before."""
    return cli._start(cli.load_image(path)[0])


def given(path):
    """start(path) as the command line's --x and --y."""
    x, y = start(path)
    return ['--x', repr(x), '--y', repr(y)]


def write(path, img, time=True, **cards):
    h = wcs_cards(fits.Header(), n=img.shape[-1])
    if time:
        h['DATE-OBS'] = '2025-12-12T21:20:32.000'; h['EXPTIME'] = 60.0
    for k, v in cards.items():
        h[k] = v
    fits.PrimaryHDU(img.astype(np.float32), header=h).writeto(path, overwrite=True)
    return path


def run_main(args):
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf), warnings.catch_warnings():
        warnings.simplefilter('ignore')
        rc = cli.main(args)
    return rc, buf.getvalue()


class Tmp(unittest.TestCase):
    def setUp(self):
        self.d = tempfile.mkdtemp()
        warnings.simplefilter('ignore')

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def p(self, name):
        return os.path.join(self.d, name)


# ---------------------------------------------------------------- item 1: the failure contract (#1, #2, #6, #7)
class TestFailureContract(Tmp):
    def test_01_G_nan_in_aperture_is_a_reason_not_a_raise(self):
        img = pig(41, 20.2, 19.9, 1.5) + 100.0
        img[20, 23] = np.nan                                   # a masked pixel 3 px from the core
        o = gauss_fit(img, 20.2, 19.9, 4.0, bkg=100.0)          # raised ValueError on c0ae330
        self.assertFalse(o['ok']); self.assertIn('non-finite', o['reason'])
        s = shrink(img, 20.0, 20.0, estimator='G', background=100.0)
        for r, ok, why in zip(s['radii'], s['ok'], s['reason']):
            self.assertEqual(ok, why == '', (r, why))
        self.assertTrue(s['ok'][0])                             # r = 2 does not reach the pixel: its answer is kept
        self.assertTrue(np.isfinite(s['x0']))
        self.assertTrue(all('non-finite' in w for ok, w in zip(s['ok'], s['reason']) if not ok))
        p = write(self.p('nan.fits'), np.pad(img, 15, constant_values=100.0))
        r = cli.measure_file(p, estimator='G')                  # the CLI (default G) crashed and lost every good radius
        self.assertTrue(np.isfinite(r['x0']))

    def test_02_small_apertures_are_refused_not_raised(self):
        img = pig(41, 20.2, 19.9, 1.5) + 100.0
        for r in (0.3, 0.5, 0.7, 1.0):
            npx = int((circle_moments(20.2, 19.9, r, img.shape)[1] > 0).sum())
            for est in ('G', 'M'):
                o = gauss_fit(img, 20.2, 19.9, r, bkg=100.0) if est == 'G' else moment_centroid(img, 20.2, 19.9, r, bkg=100.0)
                if npx < 8:                                     # G raised (lm: residuals < variables); M said ok from 1-7 pixels
                    self.assertFalse(o['ok'], (est, r, npx)); self.assertIn('fewer than 8', o['reason'])
        s = shrink(img, 20.2, 19.9, radii=np.round(np.arange(0.3, 1.01, 0.1), 10), estimator='G', background=100.0)
        self.assertEqual(len(s['reason']), 8)

    def test_03_G_amplitude_must_be_positive(self):
        img = 1000.0 - pig(41, 20.3, 19.8, 1.5, amp=5e3)          # a dip, not a source
        o = gauss_fit(img, 20.0, 20.0, 4.0, bkg=1000.0)          # c0ae330: ok True, amplitude -5000
        # the thirteenth room (the issue list's entry 7): from scipy 1.17 the fit's width runs away first, and the dip is
        # refused as "the fit ran away"; either refusal is honest, and the dip is never accepted
        self.assertFalse(o['ok']); self.assertRegex(o['reason'], r'amplitude|ran away')

    def test_04_P_never_raises(self):
        img = pig(41, 0.3, 20.0, 1.5)                            # the peak on the image's first column
        for x in (0, 1, 2):
            o = peak_quadratic(img, x, 20)                       # c0ae330: ValueError (the search window wrapped, empty)
            self.assertFalse(o['ok']); self.assertTrue(o['reason'])
        img = pig(41, 20.2, 20.1, 1.5); img[20, 21] = np.nan
        o = peak_quadratic(img, 20, 20)
        self.assertFalse(o['ok']); self.assertIn('non-finite', o['reason'])
        o = peak_quadratic(pig(41, 20.2, 20.1, 1.5), 20, 20)     # an ordinary peak is unchanged
        self.assertTrue(o['ok']); self.assertEqual(o['reason'], '')

    def test_05_every_radius_carries_ok_and_a_reason(self):
        img = np.random.default_rng(0).normal(100.0, 10.0, (41, 41)); img[20, 38] += 5000.0
        for est in ('M', 'G'):
            s = shrink(img, 20.0, 20.0, estimator=est)
            self.assertEqual(len(s['reason']), len(s['radii']))
            for ok, why in zip(s['ok'], s['reason']):
                self.assertEqual(bool(ok), why == '')

    def test_06_cube_with_one_plane_is_measured(self):
        img, _ = comet()
        h = wcs_cards(fits.Header()); h['DATE-OBS'] = '2025-12-12T21:20:32.000'; h['EXPTIME'] = 60.0
        p = self.p('cube.fits')
        fits.PrimaryHDU(img[None].astype(np.float32), header=h).writeto(p)      # NAXIS3 = 1
        r = cli.measure_file(p, estimator='M')                                   # c0ae330: IndexError
        self.assertEqual(r['curve']['nbad'], 0)

    def test_07_no_image_is_an_honest_refusal(self):
        p = self.p('cube2.fits')
        fits.PrimaryHDU(np.zeros((2, 21, 21), np.float32)).writeto(p)           # a real cube: no 2-D image to measure
        rc, out = run_main([p])                                                   # c0ae330: IndexError traceback
        self.assertEqual(rc, 1); self.assertIn('cannot measure', out)


# ---------------------------------------------------------------- item 2: the silent wrong answers (#5, #11, #13, #15-#17, #19)
class TestSilentWrong(Tmp):
    def test_05_no_time_no_record(self):
        img, _ = comet()
        p = write(self.p('notime.fits'), img, time=False)
        rc, out = run_main([p] + REC_ARGS)                          # c0ae330 has no such flags; its record carried a placeholder
        self.assertNotIn('YYYY', out); self.assertNotIn('permID', out)
        self.assertIn('no ADES record', out)
        r = cli.measure_file(p, estimator='G', ades=dict(REC))
        self.assertNotIn('ades', r); self.assertIn('time', r['ades_error'])

    def test_05b_default_run_writes_no_placeholder(self):
        img, _ = comet()
        rc, out = run_main([write(self.p('notime2.fits'), img, time=False)])
        self.assertNotIn('YYYY', out)                               # c0ae330 printed obsTime YYYY-MM-DDThh:mm:ss.ssZ

    def test_11_unconverged_radii_have_no_position(self):
        img = np.random.default_rng(0).normal(100.0, 10.0, (41, 41))   # G at r = 4.5 ran to x = -10.03 on c0ae330
        s = shrink(img, 20.0, 20.0, estimator='G', background=100.0)
        self.assertTrue((~s['ok']).any())
        self.assertTrue(np.all(np.isnan(s['x'][~s['ok']])) and np.all(np.isnan(s['y'][~s['ok']])))
        p = write(self.p('noise.fits'), img); csv = self.p('curve.csv')
        rc, out = run_main([p, '--x', '20', '--y', '20', '--background', '100', '--curve', csv])
        lines = [ln for ln in out.splitlines() if re.match(r'^\d+\.\d\d ', ln)]
        bad = [ln for ln in lines if 'unconverged' in ln]
        self.assertTrue(bad); self.assertTrue(all(' nan ' in ln + ' ' for ln in bad))
        rows = open(csv, encoding='utf-8').read().strip().split('\n')
        self.assertEqual(rows[0], 'r_px,x,y,ok,reason')
        badrows = [r.split(',') for r in rows[1:] if r.split(',')[3] == '0']
        self.assertTrue(badrows); self.assertTrue(all(r[1] == 'nan' and r[4] for r in badrows))

    def test_13_designation_field_by_the_schema_pattern(self):
        self.assertEqual(A.designation_field('3I'), 'permID')
        self.assertEqual(A.designation_field('73P-C'), 'permID')
        self.assertEqual(A.designation_field('C/2025 N1'), 'provID')
        with self.assertRaises(ValueError):
            A.designation_field('my comet')
        t = A.ades_psv(168.7, 4.6, '2025-12-12T21:21:02.00Z', **dict(REC, desig='C/2025 N1'))
        self.assertIn('provID', t.strip().split('\n')[-2]); self.assertNotIn('permID', t)   # c0ae330 put it in permID

    def test_13b_mode_and_astcat_are_the_users(self):
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        args = [a if a not in ('CCD', 'Gaia3') else {'CCD': 'CMO', 'Gaia3': 'Gaia3E'}[a] for a in REC_ARGS]
        args[args.index('--telescope-detector') + 1] = 'CMOS'
        rc, out = run_main([p] + given(p) + args)                    # c0ae330: no --mode or --astcat
        row = dict(zip([s.strip() for s in out.strip().split('\n')[-2].split('|')], [s.strip() for s in out.strip().split('\n')[-1].split('|')]))
        self.assertEqual(row['mode'], 'CMO'); self.assertEqual(row['astCat'], 'Gaia3E')
        for bad in (dict(mode='CMOS'), dict(ast_cat='GaiaDR3'), dict(mode='')):   # not on the MPC's lists
            with self.assertRaises(ValueError):
                A.ades_psv(168.7, 4.6, '2025-12-12T21:21:02.00Z', **dict(REC, **bad))

    def test_13c_nothing_defaults(self):
        img, _ = comet()
        rc, out = run_main([write(self.p('d.fits'), img)])          # c0ae330: CCD, Gaia3, 3I and XXX written unasked
        self.assertNotIn('Gaia3', out); self.assertNotIn('|CCD', out.replace(' ', ''))
        self.assertIn('no ADES record', out)
        for k in ('stn', 'desig', 'mode', 'ast_cat', 'submitter', 'measurers', 'design', 'aperture', 'detector'):
            r = cli.measure_file(write(self.p('e.fits'), img), estimator='M', ades={q: v for q, v in REC.items() if q != k})
            self.assertNotIn('ades', r, k); self.assertIn(k.replace('ast_cat', 'astCat'), r['ades_error'])

    def test_15_time(self):
        H = lambda **kw: fits.Header({k.replace('_', '-'): v for k, v in kw.items()})
        with self.assertRaises(ValueError):                           # c0ae330 wrote the start as the mid-exposure
            A.mid_exposure(H(DATE_OBS='2025-12-12T21:20:32.000'))
        self.assertEqual(A.mid_exposure(H(DATE_OBS='2025-12-12T21:20:32.000'), exptime=60.0)[0], '2025-12-12T21:21:02.00Z')
        self.assertEqual(A.mid_exposure(H(DATE_OBS='2025-12-12T21:20:32.000', EXPTIME=60.0, DATE_AVG='2025-12-12T21:22:32.000'))[0],
                         '2025-12-12T21:22:32.00Z')                   # DATE-AVG was never read
        self.assertEqual(A.mid_exposure(H(MJD_OBS=61021.0, EXPTIME=60.0, MJD_AVG=61021.5))[0], '2025-12-12T12:00:00.00Z')
        self.assertEqual(A.mid_exposure(H(DATE_OBS='2025-12-12T21:20:32.000', DATE_END='2025-12-12T21:22:32.000'))[0],
                         '2025-12-12T21:21:32.00Z')                   # DATE-END was never read
        self.assertEqual(A.mid_exposure(H(DATE_OBS='2025-12-12T21:20:32.000', EXPTIME=60.0, TIMESYS='TT'))[0],
                         '2025-12-12T21:19:52.81Z')                   # TIMESYS was never read: TT - UTC = 69.184 s
        with self.assertRaises(ValueError):
            A.mid_exposure(H(DATE_OBS='2025-12-12T21:20:32.000', EXPTIME=60.0, TIMESYS='LOCAL'))
        t, note = A.mid_exposure(H(DATE_OBS='2025-12-12T21:20:32.000', EXPTIME=60.0))
        self.assertIn('DATE-OBS', note); self.assertIn('EXPTIME', note)
        self.assertEqual(A.mid_exposure(H(DATE_OBS='2025-12-12T21:20:32.000'), obstime='2025-12-12T21:30:00.00Z')[0], '2025-12-12T21:30:00.00Z')

    def test_15b_the_two_headers_are_merged(self):
        img, _ = comet()
        ph = fits.PrimaryHDU(); ph.header['EXPTIME'] = 60.0                      # EXPTIME only in the primary
        eh = wcs_cards(fits.Header()); eh['DATE-OBS'] = '2025-12-12T21:20:32.000'
        p = self.p('mef.fits'); fits.HDUList([ph, fits.ImageHDU(img.astype(np.float32), header=eh)]).writeto(p)
        r = cli.measure_file(p, *start(p), estimator='M', ades=dict(REC))        # c0ae330 wrote 21:20:32, the start
        self.assertIn('2025-12-12T21:21:02.00Z', r['ades'])

    def test_15c_a_date_without_a_time_is_refused(self):       # added after the red run; red on c0ae330 (midnight + EXPTIME/2)
        with self.assertRaises(ValueError):
            A.mid_exposure_iso(fits.Header({'DATE-OBS': '2025-12-12', 'EXPTIME': 60.0}))

    def test_08_cli_radii_are_checked(self):                    # added after the red run: lane 1 F7, the CLI half of #8
        img, _ = comet()
        p = write(self.p('radii.fits'), img)
        for bad in ('2:6:0', '2:6:-0.1', '6:2:0.1', '0:6:0.1', '2:6'):
            rc, out = run_main([p, '--radii', bad])              # c0ae330: a traceback (or an endless range)
            self.assertEqual(rc, 1, bad); self.assertIn('cannot measure', out)

    def test_16_rms_through_the_wcs(self):
        h = wcs_cards(fits.Header(), rot90=True)
        rra, rde, cor = A.sky_rms(h, 35.0, 35.0, [[4e-4, 0.0], [0.0, 1e-4]])   # x (the larger scatter) runs north
        self.assertAlmostEqual(rra, 0.01, places=6); self.assertAlmostEqual(rde, 0.02, places=6); self.assertAlmostEqual(cor, 0.0, places=6)
        n = 71
        yy, xx = np.indices((n, n))
        img = 100.0 + 3e3 * np.exp(-0.5 * (((xx - 35.1) / 4.0) ** 2 + ((yy - 34.9) / 1.2) ** 2))  # long in x
        img = img + np.random.default_rng(3).normal(0.0, 3.0, img.shape)
        h = wcs_cards(fits.Header(), rot90=True); h['DATE-OBS'] = '2025-12-12T21:20:32.000'; h['EXPTIME'] = 60.0
        p = self.p('rot.fits'); fits.PrimaryHDU(img.astype(np.float32), header=h).writeto(p)
        r = cli.measure_file(p, *start(p), estimator='M', rms_noise=30, ades=dict(REC))
        self.assertLess(r['rms'][0], r['rms'][1])                      # c0ae330 wrote x's scatter as rmsRA (F11b: printed, not in the record)

    def test_16b_nan_border_keeps_the_noise(self):
        img, _ = comet()
        img[:3] = np.nan; img[-3:] = np.nan; img[:, :3] = np.nan; img[:, -3:] = np.nan
        p = write(self.p('border.fits'), img)
        r = cli.measure_file(p, *start(p), estimator='M', rms_noise=5, ades=dict(REC))   # c0ae330: the noise was NaN, rms silently dropped
        self.assertTrue(np.all(np.isfinite(r['sd_px'])))
        self.assertIn('rms', r, r.get('rms_error'))                    # carried to the sky (F11b: printed, not in the record)

    def test_17_frames_and_axes(self):
        base = wcs_cards(fits.Header(), n=101)
        sw = base.copy(); sw['CTYPE1'] = 'DEC--TAN'; sw['CTYPE2'] = 'RA---TAN'; sw['CRVAL1'] = 4.6; sw['CRVAL2'] = 168.7
        sw['CD1_1'] = 0.0; sw['CD1_2'] = 1 / 3600.; sw['CD2_1'] = -1 / 3600.; sw['CD2_2'] = 0.0
        ra, dec = A.pixel_to_radec(sw, 50.0, 50.0)                      # c0ae330: (4.6, 168.7)
        self.assertAlmostEqual(ra, 168.7, places=9); self.assertAlmostEqual(dec, 4.6, places=9)
        for cards in (dict(RADESYS='FK4', EQUINOX=1950.0), dict(EQUINOX=1950.0), dict(RADESYS='FK5', EQUINOX=1975.0),
                      dict(CTYPE1='GLON-TAN', CTYPE2='GLAT-TAN')):
            h = base.copy(); h.update(cards)
            with self.assertRaises(ValueError, msg=str(cards)):         # c0ae330 passed each through as RA/Dec
                A.pixel_to_radec(h, 50.0, 50.0)
        h = base.copy(); h['RADESYS'] = 'FK5'; h['EQUINOX'] = 2000.0
        ra, dec = A.pixel_to_radec(h, 50.0, 50.0)                       # accepted, and said
        w, notes = A.celestial(h)
        self.assertTrue(any('ICRS' in n for n in notes))

    def test_17b_wcs_warnings_reach_the_user(self):
        img, _ = comet()
        p = write(self.p('sip.fits'), img, A_ORDER=2, B_ORDER=2, A_2_0=1e-5, B_0_2=1e-5)   # SIP terms, no -SIP in CTYPE
        r = cli.measure_file(p, estimator='M')
        self.assertTrue(any('SIP' in n for n in r['notes']))            # c0ae330 silenced WCS warnings (FITSFixedWarning)
        rc, out = run_main([p, '--estimator', 'M'])                      # ... and astropy's logger printed this one raw
        self.assertFalse([ln for ln in out.splitlines() if ln.startswith('INFO:') or ln.startswith('WARNING:')])
        self.assertTrue(any(ln.startswith('# WCS note') and 'SIP' in ln for ln in out.splitlines()))

    def test_19_blank_pixels_are_not_data(self):
        img, _ = comet(41)
        raw = np.round(img * 10).astype(np.int64) - 32768                  # unsigned 16-bit, stored with BZERO 32768
        raw[20, 38] = -32768                                               # BLANK
        h = wcs_cards(fits.Header(), n=41); h['DATE-OBS'] = '2025-12-12T21:20:32.000'; h['EXPTIME'] = 60.0
        hdu = fits.PrimaryHDU(raw.astype(np.int16), header=h, do_not_scale_image_data=True)
        hdu.header['BZERO'] = 32768; hdu.header['BSCALE'] = 1; hdu.header['BLANK'] = -32768
        p = self.p('blank.fits'); hdu.writeto(p)
        im, hdr, notes = cli.load_image(p)                                 # c0ae330 read the blank as 0
        self.assertTrue(np.isnan(im[20, 38])); self.assertEqual(int(np.isnan(im).sum()), 1)
        self.assertAlmostEqual(im[20, 20], (raw[20, 20] + 32768), places=6)


# ---------------------------------------------------------------- item 4: an ADES record the MPC's validator accepts (#12, #14)
class TestADESRecord(Tmp):
    def test_12_version_2022_and_the_required_blocks(self):
        t = A.ades_psv(168.7, 4.6, '2025-12-12T21:21:02.00Z', **dict(REC, observers=['B. Observer'], observatory_name='My Observatory'))
        lines = t.strip().split('\n')
        self.assertEqual(lines[0], '# version=2022')                      # c0ae330: 2017, which submit.xsd refuses
        self.assertEqual(lines[1], '# observatory')                        # the obsBlock opens with the observatory
        for block in ('# submitter', '# measurers', '# telescope', '# observers'):
            self.assertIn(block, lines)
        for card in ('! mpcCode 568', '! name A. N. Observer', '! design Reflector', '! aperture 0.5', '! detector CCD', '! name My Observatory'):
            self.assertIn(card, lines)

    def test_14_ra_rounds_into_range(self):
        t = A.ades_psv(359.99999996, 1.0, '2025-12-12T21:21:02.00Z', **REC)
        row = dict(zip([s.strip() for s in t.strip().split('\n')[-2].split('|')], [s.strip() for s in t.strip().split('\n')[-1].split('|')]))
        self.assertEqual(row['ra'], '0.000000')                            # c0ae330: 360.0000000, outside RAType (6 decimals since
                                                                           # the fix room's F1, item 3)

    def test_12b_bad_context_values_are_refused(self):
        for bad in (dict(submitter=''), dict(measurers=[]), dict(aperture='-1'), dict(aperture='1234567'), dict(design='x' * 36),
                    dict(detector='y' * 26), dict(stn='56'), dict(submitter='a|b')):
            with self.assertRaises(ValueError, msg=str(bad)):
                A.ades_psv(168.7, 4.6, '2025-12-12T21:21:02.00Z', **dict(REC, **bad))


def mpc_judge(psv, workdir):
    """ADES-Master's own path: psvtoxml, then valsubmit (its first line), then lxml against its xsd/submit.xsd."""
    # The MPC's tools read and write in the platform's encoding unless Python's UTF-8 mode is on: on Windows, its valsubmit
    # stopped on a name outside the code page (the CI's first run, 30 Sept 2026). The record itself is UTF-8.
    env = dict(os.environ, PYTHONPATH=ADES_PYLIB, PYTHONUTF8='1')
    # A validator installed for another Python (its lxml built for that one) failed 11 tests as if the MPC refused the records
    # (the audit's F1.1; the fix room's F3, item 15): it is asked first whether it imports here, and said so if not
    imp = subprocess.run([sys.executable, '-c', 'import importlib.util as u, sys, ades, lxml.etree\n'
                          'sys.exit(0 if u.find_spec("ades.psvtoxml") and u.find_spec("ades.valsubmit") else 1)'],
                         env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if imp.returncode != 0:
        return False, ("the MPC's validator is not importable with this Python (%s) from ADES_PYLIB: install it with this "
                       "Python's own pip, --target, as the README says (%s)" % (sys.version.split()[0],
                                                                                (imp.stderr.strip().splitlines() or [''])[-1][:200]))
    f = os.path.join(workdir, 'rec.psv'); x = os.path.join(workdir, 'rec.xml')
    open(f, 'w', encoding='utf-8').write(psv)
    c = subprocess.run([sys.executable, '-m', 'ades.psvtoxml', f, x], cwd=workdir, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
    if c.returncode != 0 or not os.path.exists(x):
        return False, 'psvtoxml refused: ' + (c.stdout + c.stderr).strip()[-300:]
    subprocess.run([sys.executable, '-m', 'ades.valsubmit', x], cwd=workdir, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
    first = open(os.path.join(workdir, 'valsubmit.file'), encoding='utf-8').readline().strip() if os.path.exists(os.path.join(workdir, 'valsubmit.file')) else 'no valsubmit.file'
    code = ('import sys\nfrom lxml import etree\ns = etree.XMLSchema(etree.parse(sys.argv[1]))\n'
            'print("VALID" if s.validate(etree.parse(sys.argv[2])) else "INVALID " + str(s.error_log.last_error))')
    v = subprocess.run([sys.executable, '-c', code, os.path.join(ADES_MASTER, 'xsd', 'submit.xsd'), x], env=env, capture_output=True, text=True, encoding='utf-8', errors='replace')
    ok = first == 'submit is OK' and v.stdout.strip() == 'VALID'
    return ok, first + ' | xsd/submit.xsd: ' + (v.stdout + v.stderr).strip()[:300]


@unittest.skipIf(not (ADES_PYLIB and ADES_MASTER), 'the MPC judge needs ADES_PYLIB and ADES_MASTER (see the docstring)')
class TestMPCJudge(Tmp):
    def test_mpc_judge_accepts_the_cli_record(self):
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        rc, out = run_main([p])                                            # whatever the CLI prints as a record must pass
        if '# version=' in out:
            ok, why = mpc_judge(out[out.index('# version='):], self.d)
            self.assertTrue(ok, 'the default record: ' + why)             # c0ae330: version 2017, blocks missing
        variants = [REC_ARGS, REC_ARGS + ['--observer', 'B. Observer', '--observatory-name', 'Test Observatory'],
                    [a if a != '3I' else 'C/2025 N1' for a in REC_ARGS], [a if a != 'CCD' else 'CMO' for a in REC_ARGS]]
        for k, args in enumerate(variants):
            rc, out = run_main([p, '--rms-noise', '5'] + given(p) + args if k == 0 else [p] + given(p) + args)
            self.assertIn('# version=2022', out, args)
            ok, why = mpc_judge(out[out.index('# version='):], self.d)
            self.assertTrue(ok, '%s: %s' % (args, why))


if __name__ == '__main__':
    unittest.main()
