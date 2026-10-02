"""Round 3 of the hardening, Part B, the command line's share (the third hardening round's record of 28 Sept 2026, not in this repository, Part B): the
fifth invitation's item 6 as the sixth invitation lists it (the sixth invitation, of 28 Sept 2026, not in this repository), numbered as
Annie's check tables in the refuters' second record of 28 Sept 2026, not in this repository (T1.x, T4.x). Each test is written to fail on the
calibrator as the fifth room's pull request merged it (847d438, whose calibrator is 7416259's) and to pass once its fix
is in; every case is a subTest, and the cases marked "control" stand before and after. T1.8's pin passes on 847d438 by
construction (it pins that code's numbers): the bar's mutant check shows it failing where the old tests pass.
The contract is round 1's: a stranger's image gets an honest answer or an honest refusal.
"""
import os, re, sys, time, hashlib, importlib.util, subprocess, unittest
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from domino_calibrator import ades as A
from domino_calibrator import cli
from tests.test_hardening import start, given
from tests.test_hardening import (wcs_cards, comet, write, run_main, Tmp, REC, REC_ARGS, mpc_judge,
                                             ADES_PYLIB, ADES_MASTER)
from tests.test_hardening_2 import H, lines_starting, record_row
from tests.test_hardening_3 import header_with, cutout

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))    # the checkout's root, where the package imports from
CURVE_ROW = re.compile(r'^\d+\.\d+ ')                                 # a row of the curve: r x y [# unconverged: why]
# IRAF's TNX and ZPX: the distortion in WAT cards. wcslib reads a simple one (TNX, a constant 2 x 2 polynomial: applied, 5.09"
# from plain TAN, measured at wake-up) and fails on others with "Internal error in wcslib header parser" (a 4 x 4 polynomial
# with half cross terms, as IRAF writes them; every ZPX tried)
HALF = '"3. 4. 4. 2. 1. 71. 1. 71. 0.0001 0.00002 -0.00003 0.000004 0.0000005 -0.0000006 0.00000007 0.00000008 -0.00000009 0.0000001"'
SIMPLE = '"3. 2. 2. 1. -1. 1. -1. 1. 0.001 0. 0. 0."'


def wat(code, cor):
    """IRAF's cards for a TNX or ZPX WCS: CTYPE, and each axis's WAT string cut into 68-character cards as IRAF writes them."""
    cards = dict(CTYPE1='RA---' + code, CTYPE2='DEC--' + code, WAT0_001='system=image')
    for i, s in ((1, 'wtype=%s axtype=ra lngcor = %s' % (code.lower(), cor)), (2, 'wtype=%s axtype=dec latcor = %s' % (code.lower(), cor))):
        for k in range(0, len(s), 68):
            cards['WAT%d_%03d' % (i, k // 68 + 1)] = s[k:k + 68]
    return cards


def need_line(out):
    return lines_starting(out, '# no ADES record')


# ---------------------------------------------------------------- the remedies and messages (the check tables' order)
class TestTheUsersValues(Tmp):
    def test_t1_21_an_impossible_obstime_is_one_line_and_no_circle(self):
        # 847d438: astropy's message on two lines, the second without '#' (so the output cannot be cut as the record's
        # promise says), and the remedy "give it with --obstime" for the --obstime just given (T1.21; T4.7)
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        for t in ('2026-02-30T12:00:00Z', '2026-13-01T00:00:00Z', '2025-12-12T25:00:00Z'):
            with self.subTest(t):
                rc, out = run_main([p, '--estimator', 'M', '--obstime', t] + REC_ARGS)
                self.assertEqual(rc, 0)
                self.assertEqual([ln for ln in out.splitlines() if not (ln.startswith('#') or CURVE_ROW.match(ln))], [])
                need = need_line(out)
                self.assertEqual(len(need), 1, out[-600:])
                self.assertIn(t, need[0]); self.assertIn('exist', need[0])
                self.assertNotIn('give it with --obstime', need[0])
        with self.subTest('control: a time that exists'):
            rc, out = run_main([p, '--estimator', 'M', '--obstime', '2025-12-12T21:21:02Z'] + REC_ARGS)
            self.assertIn('# time: 2025-12-12T21:21:02.00Z', out)

    def test_t1_19_t4_7_the_time_remedy_names_what_helps(self):
        # 847d438 appended "give it with --obstime, or the exposure with --exptime" to every time refusal: --exptime cannot
        # help without a start, beside a DATE-AVG, or with a TIMESYS the command line does not convert, and it was offered
        # back for the user's own --exptime; an --exptime that DATE-AVG overrides was dropped without a word (T1.19, T4.7)
        img, _ = comet()
        cases = (('control: no exposure time (both help)', dict(time=True, **{'EXPTIME': None}), None, True),
                 ('no time at all', dict(time=False), None, False),
                 ('a TIMESYS the command line does not convert', dict(time=True, TIMESYS='LOCAL'), None, False),
                 ('a DATE-AVG that is not a date', dict(time=False, **{'DATE-AVG': '2025-12-32T21:21:02.000'}), None, False),
                 ("the user's own --exptime, not a number of seconds", dict(time=True, **{'EXPTIME': None}), -5.0, False))
        for name, cards, exptime, exp_helps in cases:
            with self.subTest(name):
                p = write(self.p('t.fits'), img, **cards)
                if cards.get('EXPTIME', 0) is None:                   # a card with no value: absent (round 2's rule 2)
                    with fits.open(p, mode='update') as f:
                        del f[0].header['EXPTIME']
                r = cli.measure_file(p, estimator='M', ades=dict(REC), exptime=exptime)
                e = r.get('ades_error', '')
                self.assertNotIn('time', r); self.assertIn('mid-exposure time', e)
                self.assertIn('with --obstime', e)
                self.assertEqual('with --exptime' in e, exp_helps, e)
        with self.subTest('an --exptime that DATE-AVG overrides is said'):
            p = write(self.p('avg.fits'), img, **{'DATE-AVG': '2025-12-12T21:22:32.000'})
            r = cli.measure_file(p, estimator='M', exptime=60.0)
            self.assertEqual(r.get('time'), '2025-12-12T21:22:32.00Z')
            self.assertRegex(r.get('time_note', ''), re.compile('exptime|exposure', re.I))   # 847d438: "obsTime from DATE-AVG"

    def test_t4_3_x_without_y_is_refused(self):
        # 847d438: one of --x, --y fell silently to the automatic start (the brightest 5 x 5 pixel: a star, a cosmic ray)
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        for flags in (['--x', '30'], ['--y', '30']):
            with self.subTest(' '.join(flags)):
                rc, out = run_main([p, '--estimator', 'M'] + flags)
                self.assertEqual(rc, 1, out[:300])
                why = lines_starting(out, '# cannot measure')
                self.assertTrue(why and '--x' in why[0] and '--y' in why[0], out[:300])
        for kw in (dict(x=30.0), dict(y=30.0)):
            with self.subTest('measure_file(%s)' % ', '.join('%s=%s' % i for i in kw.items())):
                with self.assertRaisesRegex(ValueError, r'\bx\b.*\by\b'):
                    cli.measure_file(p, estimator='M', **kw)
        with self.subTest('control: both'):
            self.assertEqual(cli.measure_file(p, 30.0, 31.0, estimator='M')['start'], (30.0, 31.0))

    def test_t4_9_no_wcs_names_plate_solving(self):
        # 847d438: "no WCS in the header", no remedy; an unsolved image is an amateur's likeliest first refusal
        img, _ = comet()
        h = fits.Header(); h['DATE-OBS'] = '2025-12-12T21:20:32.000'; h['EXPTIME'] = 60.0
        p = self.p('nowcs.fits'); fits.PrimaryHDU(img.astype(np.float32), header=h).writeto(p)
        r = cli.measure_file(p, estimator='M', ades=dict(REC))
        self.assertIn('solve', r.get('sky_error', '').lower())
        rc, out = run_main([p, '--estimator', 'M'])
        self.assertTrue(any('solve' in ln.lower() for ln in lines_starting(out, '# no sky position')), out[-300:])

    def test_t4_10_t1_23_rms_noise_is_3_to_1000(self):
        # 847d438: 1 or 2 redraws read as a fault of the image ("fewer than 3 of 1 noise redraws gave a position"); no
        # ceiling, so a mistyped 1000000000 is a hang (one redraw: 0.124 s with G, 0.084 s with M on a 71-px cutout)
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        for n in (1, 2):
            with self.subTest('--rms-noise %d' % n):
                r = cli.measure_file(p, *start(p), estimator='M', rms_noise=n, ades=dict(REC))
                self.assertIn('--rms-noise', r.get('rms_error', ''))
                self.assertNotIn('sd_px', r); self.assertIn('ades', r)   # the record stands, without the scatter
        for n in (1001, 1000000000):
            with self.subTest('--rms-noise %d' % n):
                try:
                    c = subprocess.run([sys.executable, '-m', 'domino_calibrator.cli', p, '--estimator', 'M', '--rms-noise', str(n)],
                                       capture_output=True, text=True, encoding='utf-8', errors='replace', cwd=ROOT, timeout=20,
                                       env=dict(os.environ, PYTHONPATH=ROOT, PYTHONDONTWRITEBYTECODE='1'))
                except subprocess.TimeoutExpired:
                    self.fail('--rms-noise %d ran past 20 s' % n)
                self.assertEqual(c.returncode, 0, c.stdout[-300:])
                why = lines_starting(c.stdout, '# no scatter')
                self.assertTrue(why and '--rms-noise' in why[0] and '1000' in why[0], c.stdout[-300:])
        for n in (0, 3):
            with self.subTest('control: --rms-noise %d' % n):
                self.assertEqual('sd_px' in cli.measure_file(p, estimator='M', rms_noise=n), n == 3)

    def test_t4_16_tnx_and_zpx_are_named(self):
        # 847d438: "the WCS could not be read: Internal error in wcslib header parser:" (the fourth room's check; again at
        # wake-up); the page sent these headers to the command line. What wcslib reads stays read (control)
        for code in ('TNX', 'ZPX'):
            with self.subTest(code):
                cards = wat(code, HALF)
                if code == 'ZPX':
                    cards['PV2_1'] = 1.0
                r = cli.measure_file(cutout(self.p('iraf.fits'), header_with(**cards)), estimator='M')
                e = r.get('sky_error', '')
                self.assertNotIn('radec', r)
                self.assertIn(code, e); self.assertRegex(e, 'SIP|TPV')
                self.assertNotIn('Internal error', e); self.assertNotIn('wcsset', e)
        with self.subTest('control: a TNX header wcslib reads is read as astropy reads it'):
            h = header_with(**wat('TNX', SIMPLE))
            r = cli.measure_file(cutout(self.p('tnx.fits'), h), estimator='M')
            self.assertIn('radec', r, r.get('sky_error'))
            want = WCS(h).all_pix2world([[r['x0'], r['y0']]], 0)[0]
            self.assertLess(np.hypot((r['radec'][0] - want[0]) * np.cos(np.radians(want[1])), r['radec'][1] - want[1]) * 3600, 1e-6)

    def test_t4_17_a_corrupt_or_truncated_file_names_its_fault(self):
        # 847d438 (the fourth room's check, R): "[Errno 22] Invalid argument"; PCOUNT -3100 read as a 10 x 10 image of
        # zeros, 41 radii unconverged; "TypeError: buffer is too small for requested array". The page names each
        files = []
        p = self.p('naxis3.fits')
        h = fits.Header([('SIMPLE', True), ('BITPIX', 16), ('NAXIS', 3), ('NAXIS1', 10), ('NAXIS2', 10), ('NAXIS3', -100)])
        open(p, 'wb').write(h.tostring().encode('ascii') + b'\0' * 2880 * 4); files.append(('NAXIS3 = -100', p, 'NAXIS3'))
        for pc in (-3100, -100000):
            q = self.p('pcount%d.fits' % -pc)
            h0 = fits.Header([('SIMPLE', True), ('BITPIX', 8), ('NAXIS', 0), ('EXTEND', True)])
            h1 = fits.Header([('XTENSION', 'IMAGE'), ('BITPIX', 16), ('NAXIS', 2), ('NAXIS1', 10), ('NAXIS2', 10), ('PCOUNT', pc), ('GCOUNT', 1)])
            open(q, 'wb').write(h0.tostring().encode('ascii') + h1.tostring().encode('ascii') + b'\0' * 2880 * 4)
            files.append(('PCOUNT = %d' % pc, q, 'PCOUNT'))
        img, _ = comet()
        b = open(write(self.p('good.fits'), img), 'rb').read()
        t = self.p('truncated.fits'); open(t, 'wb').write(b[:len(b) // 2]); files.append(('cut off halfway through its image', t, None))
        for name, f, card in files:
            with self.subTest(name):
                rc, out = run_main([f, '--estimator', 'M'])
                why = lines_starting(out, '# cannot measure')
                self.assertEqual(rc, 1, out[:300]); self.assertEqual(len(why), 1, out[:300])
                if card:
                    self.assertIn(card, why[0]); self.assertIn('corrupt', why[0])
                else:
                    self.assertRegex(why[0], 'truncated|ends before')
                self.assertNotIn('Errno', why[0]); self.assertNotIn('buffer is too small', why[0])

    def test_t4_18_the_radii_are_written_as_they_are(self):
        # 847d438 wrote every radius to 0.1 px: a 0.05 step's 2.05-5.95 became "2.0-6.0" in the record's remarks and on
        # the first line
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        rc, out = run_main([p, '--estimator', 'M', '--radii', '2.05:5.95:0.05'] + given(p) + REC_ARGS)
        self.assertIn('# version=2022', out, out[-300:])
        with self.subTest("the record's remarks"):
            self.assertIn('r 2.05-5.95 px', record_row(out[out.index('# version='):])['remarks'])
        with self.subTest('the first line'):
            self.assertIn('radii 2.05-5.95 px (79)', lines_starting(out, '# start')[0])
        with self.subTest('control: the published radii'):
            rc, out = run_main([p, '--estimator', 'M'] + given(p) + REC_ARGS)
            self.assertIn('r 2.0-6.0 px', record_row(out[out.index('# version='):])['remarks'])
            self.assertIn('radii 2.0-6.0 px (41)', lines_starting(out, '# start')[0])

    def test_t1_13_a_zero_mad_border_is_not_all_alike(self):
        # 847d438: "its pixels are all alike" for a median absolute deviation of 0, which a quantised low sky gives
        img, _ = comet()                                              # the comet's own sky ring since the fix room's F2 (item 5)
        yy, xx = np.indices(img.shape); rr = np.hypot(xx - 35.05, yy - 34.95)
        border = (rr > 11) & (rr <= 25)                               # the ring 12-24 px about wherever the fit ends, within 1 px
        q = img.copy(); q[border] = np.where(np.random.default_rng(7).random(img.shape) < 0.3, 101.0, 100.0)[border]
        r = cli.measure_file(write(self.p('quant.fits'), q), estimator='M', rms_noise=5, ades=dict(REC))
        e = r.get('rms_error', '')
        self.assertTrue(e); self.assertNotIn('all alike', e); self.assertIn('half', e)
        with self.subTest('control: a border that is all alike'):
            q[border] = 100.0
            e = cli.measure_file(write(self.p('flat.fits'), q), estimator='M', rms_noise=5).get('rms_error', '')
            self.assertIn('alike', e)

    def test_t1_15_a_time_outside_the_years_0000_9999_is_refused(self):
        # 847d438 wrote MJD-OBS 3e6 as '10072-08-06T00:00:30.0Z' and -700000 as '-58-05-06T00:00:30.000Z' (measured at
        # wake-up): the command line printed them as the time, and only the record refused them
        for mjd in (3e6, -700000.0):
            with self.subTest('MJD-OBS %g' % mjd):
                with self.assertRaisesRegex(ValueError, 'year'):
                    A.mid_exposure(H(MJD_OBS=mjd, EXPTIME=60.0))
        img, _ = comet()
        rc, out = run_main([write(self.p('far.fits'), img, time=False, **{'MJD-OBS': 3e6, 'EXPTIME': 60.0}), '--estimator', 'M'] + REC_ARGS)
        with self.subTest('the command line'):
            self.assertEqual(lines_starting(out, '# time:'), [])
            self.assertIn('year', need_line(out)[0])
        with self.subTest('control: MJD-OBS 61021.89'):
            self.assertTrue(A.mid_exposure(H(MJD_OBS=61021.89, EXPTIME=60.0))[0].startswith('2025-12-12T'))


# ---------------------------------------------------------------- the tests and the guard
# Re-pinned by the fix room's F2 (1 Oct 2026, item 5): the noise is now drawn from the comet's own sky ring (12-24 px, 3.014
# here, the fixture's 3.0), not the image's 5-px border, so every scatter moved, this one by 0.969. Its first pin (847d438, twice,
# 21:04 UTC): sd_x=0.00584832337722688, sd_y=0.001270641314107988, cov_xy=-8.212607486803452e-07, rmsRA=0.0012706413392380587,
# rmsDec=0.005848323371462107, rmsCorr=0.11051656444153767.
PIN = dict(sd_x=0.0056647828442291815, sd_y=0.001230746473028378, cov_xy=-7.706419577809545e-07,
           rmsRA=0.0012307464973739179, rmsDec=0.005664782838644504, rmsCorr=0.11053541450378475)


class TestTheGuard3b(Tmp):
    def test_t1_8_the_scatter_is_pinned(self):
        # T1.8: nothing pinned the scatter (test_16 checks an inequality, test_16b and test_1_18 its presence), so a changed
        # draw would move every record's rms and pass. test_16's file: M, 30 redraws, seed 1
        n = 71
        yy, xx = np.indices((n, n))
        img = 100.0 + 3e3 * np.exp(-0.5 * (((xx - 35.1) / 4.0) ** 2 + ((yy - 34.9) / 1.2) ** 2))
        img = img + np.random.default_rng(3).normal(0.0, 3.0, img.shape)
        h = wcs_cards(fits.Header(), rot90=True); h['DATE-OBS'] = '2025-12-12T21:20:32.000'; h['EXPTIME'] = 60.0
        p = self.p('rot.fits'); fits.PrimaryHDU(img.astype(np.float32), header=h).writeto(p)
        r = cli.measure_file(p, estimator='M', rms_noise=30, ades=dict(REC))
        self.assertEqual(r.get('rms_n'), (30, 30), r.get('rms_error'))
        got = dict(sd_x=r['sd_px'][0], sd_y=r['sd_px'][1], cov_xy=float(r['cov_px'][0][1]), rmsRA=r['rms'][0], rmsDec=r['rms'][1], rmsCorr=r['rms'][2])
        # the thirteenth room (the issue list's entry 3): 1e-9 relative, not 1e-12. numpy 2.5.3 on Python 3.13 and 3.14 moves
        # these by 1.5e-11 to 1.4e-10 relative (runs/ANY_T_RUNLOG_2026-09-29_pick313.txt, _pick314.txt); the pin's mutants
        # (the generator seeded one off, the redraws transposed: runs/any_machine.py, M6 and M7) must still turn it red
        for k, v in PIN.items():
            with self.subTest(k):
                self.assertLessEqual(abs(got[k] - v), 1e-9 * abs(v), (got[k], v))

    def test_t1_24_c1_names_the_modules_it_ran_on(self):
        # 847d438's C1 log said only "package MODIFIED", naming ades.py and cli.py, not what the science modules were
        # (HARD3_C1_RUNLOG_2026-09-28.txt, line 1); C2's names each module's sha256
        spec = importlib.util.spec_from_file_location('hard_c1', os.path.join(ROOT, 'runs', 'hard_c1.py'))
        m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
        self.assertTrue(hasattr(m, 'stamp'), "hard_c1.py has no stamp(): its log names no module's hash")
        s = m.stamp()
        for mod in ('apertures.py', 'estimators.py', 'shrink.py', 'degrade.py', 'synth.py'):
            with self.subTest(mod):
                self.assertIn('%s %s' % (mod, hashlib.sha256(open(os.path.join(ROOT, 'domino_calibrator', mod), 'rb').read()).hexdigest()[:12]), s)


# ---------------------------------------------------------------- the MPC's judge on Part B's records (bar item 4)
@unittest.skipIf(not (ADES_PYLIB and ADES_MASTER), 'the MPC judge needs ADES_PYLIB and ADES_MASTER (see test_hardening)')
class TestMPCJudge3b(Tmp):
    def test_judge_accepts_part_bs_cli_record(self):
        # control: the record with radii off the published grid (847d438 writes it, with "r 2.0-6.0 px"; after, "2.05-5.95")
        img, _ = comet()
        rc, out = run_main([write(self.p('c.fits'), img), '--estimator', 'M', '--radii', '2.05:5.95:0.05'] + given(self.p('c.fits')) + REC_ARGS)
        self.assertIn('# version=2022', out, out[-300:])
        ok, why = mpc_judge(out[out.index('# version='):], self.d)
        self.assertTrue(ok, why)


if __name__ == '__main__':
    unittest.main()
