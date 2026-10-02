"""Round 2 of the hardening, Python side (the second hardening round's record of 28 Sept 2026, not in this repository): the refuters' confirmed
findings (the refuters' record of 28 Sept 2026, not in this repository, Annie's check tables, numbered 1.1-1.22 and 4.1-4.20 there and in
the test names here). Each finding's test is written to fail on the calibrator as the third room's pull request merged
it (b5b6be4) and to pass once its fix is in. 1.13's two tests are the exception by construction: the code under them is
right, so they pass on b5b6be4, and the bar's mutant check shows each failing where the old test passes. The contract is
round 1's: a stranger's image gets an honest answer or an honest refusal.
"""
import os, re, unittest
from unittest import mock
import numpy as np
from astropy.io import fits

from domino_calibrator.shrink import shrink
from domino_calibrator import ades as A
from domino_calibrator import cli
from tests.test_hardening import start, given
from tests.test_hardening import (pig, wcs_cards, comet, write, run_main, Tmp, REC, REC_ARGS, mpc_judge,
                                             ADES_PYLIB, ADES_MASTER)


def H(**kw):
    """A header from keyword arguments, '_' read as '-' (DATE_OBS -> DATE-OBS); None writes a card with no value."""
    return fits.Header({k.replace('_', '-'): v for k, v in kw.items()})


def lookup_file(path, shift=0.5):
    """A comet cutout whose WCS carries a lookup-table distortion (CPDIS, as in HST's _flc frames): x shifted by `shift`
    px everywhere, the tables in two WCSDVARR extensions. astropy applies it only with the HDUList open."""
    from astropy.wcs import WCS, DistortionLookupTable
    img, _ = comet()
    w = WCS(wcs_cards(fits.Header(), n=img.shape[1]))
    w.cpdis1 = DistortionLookupTable(np.full((8, 8), shift, np.float32), (1.0, 1.0), (1.0, 1.0), (10.0, 10.0))
    w.cpdis2 = DistortionLookupTable(np.zeros((8, 8), np.float32), (1.0, 1.0), (1.0, 1.0), (10.0, 10.0))
    hl = w.to_fits()
    hl[0].data = img.astype(np.float32)
    hl[0].header['DATE-OBS'] = '2025-12-12T21:20:32.000'; hl[0].header['EXPTIME'] = 60.0
    hl.writeto(path, overwrite=True)
    return path


def lines_starting(out, prefix):
    return [ln for ln in out.splitlines() if ln.startswith(prefix)]


def record_row(psv):
    t = psv.strip().split('\n')
    return dict(zip([s.strip() for s in t[-2].split('|')], [s.strip() for s in t[-1].split('|')]))


# ---------------------------------------------------------------- 1: the silent wrong answers (the Python's share)
# F11 (the audit's F8.4): a sky ring flat throughout is refused at the comet's gate, so the noiseless test images carry a faint
# fixed sky noise (1 count against peaks of 3e4); what each test checks is unchanged
SKY_NOISE = np.random.default_rng(7).normal(0.0, 1.0, (41, 41))

class TestSilentWrong2(Tmp):
    def test_1_9_a_date_without_a_time_is_refused_for_every_date_key(self):
        # b5b6be4: the rule covered DATE-OBS alone. DATE-AVG 2025-12-12 was read as midnight; a date-only DATE-END put the
        # mid-exposure at 10:40:16, hours before a 21:20:32 start; a date-only DATE-BEG gave 00:00:30
        for key, h in (('DATE-AVG', H(DATE_AVG='2025-12-12')),
                       ('DATE-END', H(DATE_OBS='2025-12-12T21:20:32.000', DATE_END='2025-12-12')),
                       ('DATE-BEG', H(DATE_BEG='2025-12-12', EXPTIME=60.0))):
            with self.assertRaisesRegex(ValueError, key):
                A.mid_exposure(h)
        self.assertEqual(A.mid_exposure(H(DATE_OBS='2025-12-12', TIME_OBS='21:20:32', EXPTIME=60.0))[0],
                         '2025-12-12T21:21:02.00Z')                   # DATE-OBS with TIME-OBS still stands

    def test_4_7_the_record_refuses_an_impossible_time(self):
        for t in ('2026-13-45T00:00:00Z', '2025-02-30T12:00:00Z', '2025-02-29T12:00:00.00Z', '2025-12-12T25:00:00Z'):
            with self.assertRaises(ValueError, msg=t):                # b5b6be4 wrote each: the schema's pattern checks digits only
                A.ades_psv(168.7, 4.6, t, **REC)
        self.assertIn('2024-02-29T12:00:00.00Z', A.ades_psv(168.7, 4.6, '2024-02-29T12:00:00.00Z', **REC))   # a leap day

    def test_4_3_the_remarks_name_the_radii_fitted(self):
        img = pig(41, 35.3, 20.2, 1.6, amp=3e4) + 150.0 + SKY_NOISE   # 5.7 px from the right edge: the large radii leave it
        p = write(self.p('edge.fits'), img)
        r = cli.measure_file(p, x=35.0, y=20.0, estimator='G', ades=dict(REC))
        o = r['curve']; ok = np.asarray(o['ok'])
        self.assertTrue(2 <= ok.sum() < len(ok), ok.sum())
        # The audit room's B2 (30 Sept 2026): no record unless every radius converged, so the radii off the image refuse it;
        # b5b6be4's "r 2.0-6.0 px" (the radii asked for) cannot recur, and the remarks are checked on radii that all converge
        self.assertNotIn('ades', r)
        self.assertIn('a comet measured (only %d of %d radii converged' % (ok.sum(), len(ok)), r['ades_error'])
        r = cli.measure_file(p, x=35.0, y=20.0, estimator='G', radii=np.round(np.arange(2.0, 4.0 + 1e-9, 0.1), 10), ades=dict(REC))
        self.assertIn('21 of 21 radii, r 2.0-4.0 px', record_row(r['ades'])['remarks'])

    def test_4_2_the_sky_position_is_printed(self):
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        ra, dec = cli.measure_file(p, estimator='G')['radec']
        rc, out = run_main([p])                                      # b5b6be4 printed RA/Dec only inside a record
        sky = lines_starting(out, '# sky')
        self.assertTrue(sky and '%.7f' % ra in sky[0] and '%.7f' % abs(dec) in sky[0], out[-600:])
        q = self.p('nowcs.fits')
        fits.PrimaryHDU(img.astype(np.float32), header=H(DATE_OBS='2025-12-12T21:20:32.000', EXPTIME=60.0)).writeto(q)
        rc, out = run_main([q])
        self.assertTrue(any('no WCS' in ln for ln in lines_starting(out, '# no sky position')), out[-600:])


# ---------------------------------------------------------------- 2: answers lost, or refused for the wrong reason
class TestLostAnswers2(Tmp):
    def test_1_2_a_zero_scatter_keeps_the_record(self):
        img, _ = comet()
        yy, xx = np.indices(img.shape)                                # most of the sky beyond 11 px is one value: the comet's own sky
        flat = (np.hypot(xx - 35.05, yy - 34.95) > 11) & (np.random.default_rng(13).random(img.shape) < 0.6)   # ring, which the
        img[flat] = 100.0                                            # noise is drawn from since the fix room's F2 (item 5), has a MAD
        p = write(self.p('pad.fits'), img)                           # of 0, as the padded border had before; since F11 (the audit's
                                                                     # F8.4) a ring flat throughout is refused at the comet's gate
        r = cli.measure_file(p, *start(p), estimator='M', rms_noise=5, ades=dict(REC))
        self.assertIn('ades', r, r.get('ades_error'))                # b5b6be4: "rmsRA/rmsDec: 0.0, 0.0 cannot be written ..."
        self.assertNotIn('rmsRA', r['ades'])
        self.assertIn('no noise level to draw from', r.get('rms_error', ''))   # its MAD is 0 (the words since round 3, T1.13)

    def test_1_8_an_unparsable_card_keeps_the_answer(self):
        img, _ = comet()
        p = self.p('badcard.fits')
        fits.PrimaryHDU(img.astype(np.float32), header=H(OBJECT='XXXXXXXXX', DATE_OBS='2025-12-12T21:20:32.000', EXPTIME=60.0)).writeto(p)
        b = open(p, 'rb').read(); i = b.index(b'OBJECT  =')
        open(p, 'wb').write(b[:i] + b'OBJECT  = C/2025 N1'.ljust(80) + b[i + 80:])   # unquoted: astropy cannot parse it
        r = cli.measure_file(p, estimator='M')                       # b5b6be4: VerifyError, the pixel answer lost (no WCS here)
        self.assertTrue(np.isfinite(r['x0']))
        self.assertEqual(r.get('time'), '2025-12-12T21:21:02.00Z')   # the time is in cards astropy can read
        self.assertTrue(any('OBJECT' in n for n in r['notes']), r['notes'])   # the card left out is named
        rc, out = run_main([p])
        self.assertEqual(rc, 2); self.assertIn('# zero aperture:', out)   # no WCS here: 2, his exit codes (the fix room's F2)

    def test_1_3_a_bad_curve_path_keeps_the_record(self):
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        bad = os.path.join(self.d, 'no', 'such', 'folder', 'curve.csv')
        rc, out = run_main([p, '--curve', bad] + given(p) + REC_ARGS)          # b5b6be4: a FileNotFoundError traceback, no record
        self.assertIn('# version=2022', out)
        self.assertTrue(out.strip().split('\n')[-2].startswith('permID'))   # the record still comes last
        self.assertTrue(any('curve' in ln and bad in ln for ln in lines_starting(out, '#')), out[-600:])

    def test_1_4_a_negative_rms_noise_keeps_the_answer(self):
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        r = cli.measure_file(p, *start(p), estimator='M', rms_noise=-1, ades=dict(REC))   # b5b6be4: AxisError, the answer lost
        self.assertTrue(np.isfinite(r['x0'])); self.assertIn('ades', r); self.assertIn('rms_error', r)
        rc, out = run_main([p, '--rms-noise', '-1'] + given(p) + REC_ARGS)
        self.assertEqual(rc, 0); self.assertIn('# zero aperture:', out); self.assertIn('# version=2022', out)
        self.assertTrue(any('--rms-noise' in ln for ln in lines_starting(out, '# no scatter')), out[-600:])

    def test_1_5_a_non_finite_start_is_refused_by_name(self):
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        for x in ('inf', '-inf', 'nan'):                             # b5b6be4: OverflowError; for nan, 41 x "aperture leaves the image"
            rc, out = run_main([p, '--x=' + x, '--y', '20', '--background', '100'])   # '=': argparse reads -inf as a flag
            said = [ln for ln in out.splitlines() if 'cannot measure' in ln]
            self.assertEqual(rc, 1, (x, out[:300]))
            self.assertTrue(said and 'start' in said[0] and 'Overflow' not in said[0], (x, said))
        with self.assertRaisesRegex(ValueError, 'start'):
            shrink(img, np.inf, 20.0, background=100.0)

    def test_4_19_a_refusal_always_has_a_reason(self):
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        for exc in (MemoryError(), RuntimeError()):                  # b5b6be4: "# cannot measure: MemoryError: " and nothing after
            with mock.patch.object(cli, 'measure_file', side_effect=exc):
                rc, out = run_main([p])
            said = [ln for ln in out.splitlines() if 'cannot measure' in ln]
            self.assertEqual(rc, 1)
            why = said[0].split('cannot measure:', 1)[1].replace(type(exc).__name__, '').strip(' :')
            self.assertGreater(len(why), 10, said[0])

    def test_1_18_a_lookup_table_wcs_is_read_with_its_file(self):
        from astropy.wcs import WCS
        p = lookup_file(self.p('lookup.fits'))
        r = cli.measure_file(p, estimator='M')                       # b5b6be4: "the WCS could not be read: an HDUList is required"
        self.assertIn('radec', r, r.get('sky_error'))
        with fits.open(p) as f:
            want = WCS(f[0].header, fobj=f).all_pix2world([[r['x0'], r['y0']]], 0)[0]
        self.assertAlmostEqual(r['radec'][0], want[0], places=10); self.assertAlmostEqual(r['radec'][1], want[1], places=10)
        plain = WCS(wcs_cards(fits.Header(), n=71)).all_pix2world([[r['x0'], r['y0']]], 0)[0]
        self.assertGreater(abs(r['radec'][0] - plain[0]) * 3600 * np.cos(np.radians(plain[1])), 0.3)   # the table is in it
        r = cli.measure_file(p, *start(p), estimator='M', rms_noise=5, ades=dict(REC))
        self.assertIn('rms', r, r.get('rms_error'))                   # carried to the sky (F11b: printed, not in the record)


# ---------------------------------------------------------------- 3: what the user must see
class TestWhatTheUserSees2(Tmp):
    def test_4_6_the_record_refusals_name_the_flags(self):
        img, _ = comet()
        rc, out = run_main([write(self.p('c.fits'), img)])           # b5b6be4 named the record's fields, not the flags
        said = lines_starting(out, '# no ADES record')[0]
        for flag in ('--stn', '--desig', '--mode', '--astcat', '--submitter', '--measurer', '--telescope-design',
                     '--telescope-aperture', '--telescope-detector'):
            self.assertIn(flag, said)
        rc, out = run_main([write(self.p('notime.fits'), img, time=False)] + REC_ARGS)
        self.assertIn('--obstime', lines_starting(out, '# no ADES record')[0])    # b5b6be4: the reason, not the remedy
        rc, out = run_main([write(self.p('noexp.fits'), img, time=False, **{'DATE-OBS': '2025-12-12T21:20:32.000'})] + REC_ARGS)
        self.assertIn('--exptime', lines_starting(out, '# no ADES record')[0])

    def test_4_6_the_value_refusals_name_the_remedy(self):
        with self.assertRaisesRegex(ValueError, 'CMOS camera is CMO'):   # b5b6be4: the list, and no word on CMOS
            A.ades_psv(168.7, 4.6, '2025-12-12T21:21:02.00Z', **dict(REC, mode='CMOS'))
        h = wcs_cards(fits.Header(), n=101); h['RADESYS'] = 'FK4'; h['EQUINOX'] = 1950.0
        with self.assertRaisesRegex(ValueError, 're-solve'):             # b5b6be4: the frame refused, with nothing to do
            A.celestial(h)

    def test_4_5_a_colour_cube_is_named(self):
        p = self.p('rgb.fits')
        fits.PrimaryHDU(np.zeros((3, 41, 41), np.float32)).writeto(p)
        rc, out = run_main([p])                                      # b5b6be4: "no 2-D image in this file"
        said = [ln for ln in out.splitlines() if 'cannot measure' in ln]
        self.assertEqual(rc, 1); self.assertIn('3 planes', said[0])


# ---------------------------------------------------------------- 4: the two weak tests, strengthened (1.13)
class TestStrongerTests(Tmp):
    """test_hardening's test_15b and test_16 pass whatever the merge order and whatever rmsCorr's sign (1.13). These two
    can tell: they pass on b5b6be4, whose code is right, and each fails on a mutant of it (the bar's mutant check)."""
    def test_1_13a_the_image_hdu_wins_the_merge(self):
        img, _ = comet()
        ph = fits.PrimaryHDU(); ph.header['DATE-OBS'] = '2025-12-12T20:00:00.000'; ph.header['EXPTIME'] = 30.0
        eh = wcs_cards(fits.Header()); eh['DATE-OBS'] = '2025-12-12T21:20:32.000'; eh['EXPTIME'] = 60.0
        p = self.p('mef.fits'); fits.HDUList([ph, fits.ImageHDU(img.astype(np.float32), header=eh)]).writeto(p)
        r = cli.measure_file(p, *start(p), estimator='M', ades=dict(REC))
        self.assertEqual(r['time'], '2025-12-12T21:21:02.00Z')       # the primary's cards over the image's would give 20:00:15
        self.assertIn('2025-12-12T21:21:02.00Z', r['ades'])

    def test_1_13b_rms_corr_has_its_sign(self):
        # to first order at the reference pixel, RA cos Dec = CD1_1 dx + CD1_2 dy and Dec = CD2_1 dx + CD2_2 dy (1"/px here)
        # standard frame (CD1_1 < 0: x runs west): (east, north) = (-x, +y), so a (x, y) correlation of +0.75 is -0.75
        rra, rde, cor = A.sky_rms(wcs_cards(fits.Header()), 35.0, 35.0, [[4e-4, 1.5e-4], [1.5e-4, 1e-4]])
        self.assertAlmostEqual(rra, 0.02, places=6); self.assertAlmostEqual(rde, 0.01, places=6)
        self.assertAlmostEqual(cor, -0.75, places=5)
        # x runs north (rot90): (east, north) = (-y, +x), so a (x, y) correlation of -0.5 is +0.5
        rra, rde, cor = A.sky_rms(wcs_cards(fits.Header(), rot90=True), 35.0, 35.0, [[4e-4, -1e-4], [-1e-4, 1e-4]])
        self.assertAlmostEqual(rra, 0.01, places=6); self.assertAlmostEqual(rde, 0.02, places=6)
        self.assertAlmostEqual(cor, 0.5, places=5)
        t = A.ades_psv(168.7, 4.6, '2025-12-12T21:21:02.00Z', rms_ra=0.02, rms_dec=0.01, rms_corr=-0.75, **REC)
        self.assertEqual(record_row(t)['rmsCorr'], '-0.7500')


# ---------------------------------------------------------------- the MPC's judge on round 2's records (bar item 4)
@unittest.skipIf(not (ADES_PYLIB and ADES_MASTER), 'the MPC judge needs ADES_PYLIB and ADES_MASTER (see test_hardening)')
class TestMPCJudge2(Tmp):
    def test_judge_accepts_round_2s_cli_records(self):
        img, _ = comet()
        cases = [('the fitted radii in the remarks', [write(self.p('edge.fits'), pig(41, 35.3, 20.2, 1.6, amp=3e4) + 150.0 + SKY_NOISE),
                                                       '--x', '35', '--y', '20', '--radii', '2.0:4.0:0.1']),   # every radius converges (B2)
                 ('a zero scatter: the record without rms', [write(self.p('pad.fits'), np.pad(img, 8, constant_values=100.0)),
                                                             '--estimator', 'M', '--rms-noise', '5']),
                 ('a lookup-table WCS, with rms', [lookup_file(self.p('lookup.fits')), '--estimator', 'M', '--rms-noise', '5'])]
        for what, args in cases:
            rc, out = run_main(args + ([] if '--x' in args else given(args[0])) + REC_ARGS)
            self.assertIn('# version=2022', out, what)               # b5b6be4: no record for the last two
            ok, why = mpc_judge(out[out.index('# version='):], self.d)
            self.assertTrue(ok, '%s: %s' % (what, why))


if __name__ == '__main__':
    unittest.main()
