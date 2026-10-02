"""Round 3 of the hardening, Part A, Python side (the third hardening round's record of 28 Sept 2026, not in this repository): the fifth invitation's
items 1-5 (the fifth invitation, of 28 Sept 2026, not in this repository), from the fourth room's refuters (archive/
the refuters' second record of 28 Sept 2026, not in this repository, Annie's check tables T1.1-T1.24 and T4.1-T4.18, numbered so in the test names here)
and round 2's own find, the command line's PV misread. Each test is written to fail on the calibrator as the fourth
room's pull request merged it (e7051b4, whose calibrator is 9e62fae's) and to pass once its fix is in. Every case is a
subTest, so a red run lists each failing case, not only the first; the cases marked "control" stand before and after.
The contract is round 1's: a stranger's image gets an honest answer or an honest refusal.
"""
import os, sys, subprocess, unittest
import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from domino_calibrator import ades as A
from domino_calibrator import cli
from domino_calibrator.hst import DATA
from tests.test_hardening import start, given
from tests.test_hardening import (wcs_cards, comet, write, run_main, Tmp, REC, REC_ARGS, mpc_judge,
                                             ADES_PYLIB, ADES_MASTER)
from tests.test_hardening_2 import H, lines_starting, record_row

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))    # the checkout's root, where the package imports from
FLC = os.path.join(DATA, 'ifle03geq_flc.fits')                         # gitignored: tools/fetch_frames.py 03
SCAMP1 = dict(PV1_0=0.0, PV1_1=1.0, PV1_2=0.0, PV2_0=0.0, PV2_1=1.0, PV2_2=0.0)   # a pre-2012 SCAMP first-order solution (the identity)
SIP0 = dict(CTYPE1='RA---TAN-SIP', CTYPE2='DEC--TAN-SIP', A_ORDER=2, B_ORDER=2, A_2_0=0.0, B_0_2=0.0)
PT = [[5.0, 60.0]]                                                    # 39 px from the reference pixel, as round 2's probe


def arcsec(a, b):
    return float(np.hypot((a[0] - b[0]) * np.cos(np.radians(b[1])), a[1] - b[1]) * 3600)


def header_with(**cards):
    """wcs_cards' TAN header (71 px, 1"/px) with cards set (None: a card with no value) or removed (the value DROP)."""
    h = wcs_cards(fits.Header(), n=71)
    for k, v in cards.items():
        k = k.replace('_', '-') if k.startswith(('DATE_', 'MJD_')) else k
        if v is DROP:
            del h[k]
        else:
            h[k] = v
    return h


DROP = object()


def cutout(path, header, img=None):
    img = comet()[0] if img is None else img
    fits.PrimaryHDU(img.astype(np.float32), header=header).writeto(path, overwrite=True)
    return path


def with_raw_card(path, card, mef=False):
    """test_1_8's comet cutout with one raw 80-byte card written over OBJECT (over EXPTIME for a card of that name): in the
    primary of a one-HDU file, or in the image extension of a two-HDU file whose primary carries DATE-OBS."""
    img, _ = comet()
    h = wcs_cards(fits.Header()); h['EXPTIME'] = 60.0; h['OBJECT'] = 'XXXXXXXX'
    if mef:
        ph = fits.PrimaryHDU(); ph.header['DATE-OBS'] = '2025-12-12T21:20:32.000'
        fits.HDUList([ph, fits.ImageHDU(img.astype(np.float32), header=h)]).writeto(path, overwrite=True)
    else:
        h['DATE-OBS'] = '2025-12-12T21:20:32.000'
        fits.PrimaryHDU(img.astype(np.float32), header=h).writeto(path, overwrite=True)
    b = open(path, 'rb').read()
    key = b'EXPTIME =' if card.startswith(b'EXPTIME') else b'OBJECT  ='
    i = b.rindex(key)                                                 # the image's own card (the extension's, in a MEF)
    open(path, 'wb').write(b[:i] + card.ljust(80) + b[i + 80:])
    return path


# ---------------------------------------------------------------- item 1: the command line's PV misread (his word: first)
class TestPV(Tmp):
    def test_pv_1_low_order_pv_terms_that_move_the_position_are_refused(self):
        # Round 2's find (the second hardening round's record of 28 Sept 2026, not in this repository): below index 5 astropy keeps TAN and wcslib reads
        # PV1_1, PV1_2 as the projection's reference point, as the FITS standard defines them. e7051b4: each case read, a
        # SCAMP first-order solution 707,991" from plain TAN (on TAN-SIP too, measured at wake-up), with no note
        for name, cards in (('TAN, SCAMP first order', SCAMP1), ('TAN-SIP, SCAMP first order', dict(SIP0, **SCAMP1)),
                            ('TAN, PV1_1 and PV2_1 alone', dict(PV1_1=1.0, PV2_1=1.0))):
            with self.subTest(name):
                with self.assertRaisesRegex(ValueError, 'PV') as cm:
                    A.celestial(header_with(**cards))
                self.assertIn('TPV', str(cm.exception))              # the remedy, for SCAMP's solutions
        r = cli.measure_file(cutout(self.p('scamp1.fits'), header_with(DATE_OBS='2025-12-12T21:20:32.000', EXPTIME=60.0, **SCAMP1)),
                             estimator='M', ades=dict(REC))
        with self.subTest('the command line: no sky position, and why'):
            self.assertNotIn('radec', r); self.assertIn('PV', r.get('sky_error', ''))
            self.assertNotIn('ades', r)
        rc, out = run_main([self.p('scamp1.fits')])
        with self.subTest('the command line says it'):
            self.assertTrue(any('PV' in ln for ln in lines_starting(out, '# no sky position')), out[-500:])
        # controls: terms that change nothing are read; SCAMP's full solutions (an index of 5 or more) are TPV to astropy
        plain = WCS(header_with()).all_pix2world(PT, 0)[0]
        for name, cards in (('control: the standard defaults written out', dict(PV1_1=0.0, PV1_2=90.0)),
                            ('control: PV2_1 alone (TAN takes none)', dict(PV2_1=1.0))):
            with self.subTest(name):
                w, _ = A.celestial(header_with(**cards))
                self.assertLess(arcsec(w.all_pix2world(PT, 0)[0], plain), 1e-6)
        with self.subTest('control: SCAMP to index 5 is read as TPV'):
            h = header_with(PV1_5=1e-2, PV2_5=1e-2, **SCAMP1)
            t = h.copy(); t['CTYPE1'] = 'RA---TPV'; t['CTYPE2'] = 'DEC--TPV'
            w, _ = A.celestial(h)
            self.assertLess(arcsec(w.all_pix2world(PT, 0)[0], WCS(t).all_pix2world(PT, 0)[0]), 1e-6)

    def test_pv_2_a_declared_distortion_that_is_not_applied_is_refused(self):
        # his yes (my first call after it: 19:44 UTC): the same class. astropy applies CPDIS and D2IMDIS only as lookup
        # tables, and D2IMDIS only with the file open; otherwise it drops the distortion. e7051b4: each case read without it
        # (0.0000" from plain TAN; for a polynomial, astropy's note "Polynomial distortion is not implemented.")
        empty = fits.HDUList([fits.PrimaryHDU()])
        for name, cards, fobj in (('CPDIS Polynomial', dict(CPDIS1='Polynomial', CPDIS2='Polynomial'), empty),
                                  ('D2IMDIS Polynomial', dict(D2IMDIS1='Polynomial', D2IMDIS2='Polynomial'), empty),
                                  ('D2IMDIS Lookup, the file not given', dict(D2IMDIS1='Lookup', D2IMDIS2='Lookup'), None)):
            with self.subTest(name):
                with self.assertRaisesRegex(ValueError, 'D2IMDIS|CPDIS'):
                    A.celestial(header_with(**cards), fobj=fobj)
        r = cli.measure_file(cutout(self.p('poly.fits'), header_with(CPDIS1='Polynomial', CPDIS2='Polynomial')), estimator='M')
        with self.subTest('the command line: no sky position'):
            self.assertNotIn('radec', r); self.assertIn('CPDIS', r.get('sky_error', ''))


# ---------------------------------------------------------------- item 2: round 2's own regression (T1.1)
class TestTheMerge(Tmp):
    # (name, the raw card, what the merge does with it). A card astropy cannot write back is left out and named; a card
    # with no "= " in columns 1-10 is astropy's invalid card (read as raw text: '  3I', '=60.0'), left out and named, as
    # the page will (T1.5); a comment that cannot be written back is dropped and the value kept, as the page reads it
    SHAPES = (('a NUL in the keyword', b"OBJ\x00ECT = '3I'", 'left out'), ('no "= " in columns 9-10', b'OBJECT    3I', 'left out'),
              ('a TAB in the comment', b"OBJECT  = '3I'  / a\tcomment", 'kept'), ('a value from column 10', b'EXPTIME =60.0', 'left out'))

    def test_t1_1_a_card_that_cannot_be_written_back_keeps_the_answer(self):
        # e7051b4: the merge guarded the read of a card, not its write. Three shapes raised out of measure_file in a one-HDU
        # file, all four in the extension of a two-HDU file (the refuters' run; measured again at wake-up): the pixel
        # answer lost, which b5b6be4 kept. Rule 10 (round 2): what cannot be carried is left out, named; the rest stands
        for mef in (False, True):
            for name, card, fate in self.SHAPES:
                with self.subTest(name, mef=mef):
                    p = with_raw_card(self.p('card.fits'), card, mef=mef)
                    try:
                        r = cli.measure_file(p, estimator='M')
                    except Exception as e:
                        self.fail('raised %s: %s' % (type(e).__name__, str(e)[:120]))
                    self.assertTrue(np.isfinite(r['x0']))
                    key = 'EXPTIME' if card.startswith(b'EXPTIME') else 'ECT'
                    named = any('left out' in n and key in n for n in r['notes'])
                    self.assertEqual(named, fate == 'left out', r['notes'])
                    if fate == 'kept':
                        self.assertEqual(cli.load_image(p)[1].get('OBJECT'), '3I')
                    if key == 'EXPTIME':                             # read by astropy as the text '=60.0': no exposure time
                        self.assertNotIn('time', r); self.assertIn('exposure', r.get('time_error', ''))
                    else:
                        self.assertEqual(r.get('time'), '2025-12-12T21:21:02.00Z', r.get('time_error'))
                    rc, out = run_main([p])
                    self.assertEqual(rc, 0); self.assertIn('# zero aperture:', out)


# ---------------------------------------------------------------- item 3: the other silent wrong answers (the Python's share)
class TestSilentWrong3(Tmp):
    def test_t1_4_an_end_before_the_start_is_refused(self):
        # e7051b4: the middle of the two, before the start, silently (a midnight rollover: 12 h early)
        for name, h in (('DATE-END across midnight', H(DATE_OBS='2025-12-12T23:59:30', DATE_END='2025-12-12T00:00:30')),
                        ('DATE-END a day early', H(DATE_OBS='2025-12-12T21:20:32', DATE_END='2025-12-11T21:22:32')),
                        ('MJD-END before MJD-OBS', H(MJD_OBS=61021.89, MJD_END=61021.80)),
                        ('DATE-END before DATE-BEG', H(DATE_BEG='2025-12-12T21:20:32', DATE_END='2025-12-12T21:10:32'))):
            with self.subTest(name):
                with self.assertRaisesRegex(ValueError, 'END'):
                    A.mid_exposure(h)
        with self.subTest('control: an end after the start'):
            self.assertEqual(A.mid_exposure(H(DATE_OBS='2025-12-12T21:20:32.000', DATE_END='2025-12-12T21:22:32.000'))[0],
                             '2025-12-12T21:21:32.00Z')

    def test_t4_1_a_partial_wcs_is_refused(self):
        # e7051b4: wcslib's defaults filled the gaps: no CRVAL gave RA 0, Dec 0; no CD, 184" off; no CRPIX, 35" off; no note
        for name, drop, word in (('no CRVAL', ('CRVAL1', 'CRVAL2'), 'CRVAL'), ('no CRVAL2', ('CRVAL2',), 'CRVAL2'),
                                 ('no CRPIX', ('CRPIX1', 'CRPIX2'), 'CRPIX'),
                                 ('no scale: no CD, CDELT or PC', ('CD1_1', 'CD1_2', 'CD2_1', 'CD2_2'), 'scale')):
            with self.subTest(name):
                h = header_with(**{k: DROP for k in drop})
                with self.assertRaisesRegex(ValueError, word):
                    A.celestial(h)
                h['DATE-OBS'] = '2025-12-12T21:20:32.000'; h['EXPTIME'] = 60.0
                r = cli.measure_file(cutout(self.p('partial.fits'), h), estimator='M', ades=dict(REC))
                self.assertNotIn('radec', r); self.assertIn(word, r.get('sky_error', ''))
        with self.subTest('control: a PC matrix without CDELT is FITS (CDELT defaults to 1)'):
            h = header_with(CD1_1=DROP, CD1_2=DROP, CD2_1=DROP, CD2_2=DROP, PC1_1=-1 / 3600, PC2_2=1 / 3600)
            w, _ = A.celestial(h)
            self.assertLess(arcsec(w.all_pix2world(PT, 0)[0], WCS(header_with()).all_pix2world(PT, 0)[0]), 1e-6)

    def test_t1_6_the_blank_card_rule_reaches_the_frame_the_wcs_and_the_merge(self):
        # round 2's rule 2 stopped at the time. e7051b4: a blank EQUINOX hid EPOCH and a blank RADESYS hid RADECSYS (both
        # taken as ICRS, silently); a blank CTYPE1 in the image HDU counted as a WCS ("'NoneType' object has no attribute
        # 'strip'"); a blank card in the image HDU hid the primary's (a TT header 69 s off; an exposure time lost)
        for name, cards in (('a blank EQUINOX over EPOCH 1950', dict(EQUINOX=None, EPOCH=1950.0)),
                            ('a blank RADESYS over RADECSYS FK4', dict(RADESYS=None, RADECSYS='FK4')),
                            ('an empty RADESYS over RADECSYS FK4', dict(RADESYS='', RADECSYS='FK4'))):
            with self.subTest(name):
                with self.assertRaisesRegex(ValueError, 'FK4'):
                    A.celestial(header_with(**cards))
        img, _ = comet()

        def mef(pcards, icards, wcs_in_image=True):
            ph = fits.PrimaryHDU(header=wcs_cards(fits.Header()) if not wcs_in_image else None)
            for k, v in pcards.items():
                ph.header[k] = v
            ih = wcs_cards(fits.Header()) if wcs_in_image else fits.Header()
            for k, v in icards.items():
                ih[k] = v
            p = self.p('mef.fits'); fits.HDUList([ph, fits.ImageHDU(img.astype(np.float32), header=ih)]).writeto(p, overwrite=True)
            return p

        with self.subTest('a blank CTYPE1 in the image HDU is no WCS: the primary has none for it without INHERIT = T'):
            p = mef({}, {'CTYPE1': None}, wcs_in_image=False)        # the FITS convention since the fix room's F2 (item 9)
            r = cli.measure_file(p, estimator='M')
            self.assertNotIn('radec', r); self.assertIn('INHERIT', r.get('sky_error', ''))
        with self.subTest('a blank CTYPE1 in the image HDU, with INHERIT = T: the primary WCS is read'):
            p = mef({}, {'CTYPE1': None, 'INHERIT': True}, wcs_in_image=False)
            r = cli.measure_file(p, estimator='M')
            self.assertIn('radec', r, r.get('sky_error'))
            want = WCS(wcs_cards(fits.Header())).all_pix2world([[r['x0'], r['y0']]], 0)[0]
            self.assertLess(arcsec(r['radec'], want), 1e-6)
        with self.subTest('a blank TIMESYS in the image HDU keeps the primary TT'):
            p = mef({'TIMESYS': 'TT', 'DATE-OBS': '2025-12-12T21:20:32.000', 'EXPTIME': 60.0}, {'TIMESYS': None})
            self.assertEqual(cli.measure_file(p, estimator='M').get('time'), '2025-12-12T21:19:52.81Z')
        with self.subTest("a blank EXPTIME in the image HDU keeps the primary's"):
            p = mef({'DATE-OBS': '2025-12-12T21:20:32.000', 'EXPTIME': 60.0}, {'EXPTIME': None})
            self.assertEqual(cli.measure_file(p, estimator='M').get('time'), '2025-12-12T21:21:02.00Z')


# ---------------------------------------------------------------- item 5: answers and data lost
class TestLost3(Tmp):
    def blank_frame(self, blank):
        img, _ = comet(41)                                            # test_19's unsigned 16-bit frame (BZERO 32768)
        raw = np.round(img * 10).astype(np.int64) - 32768
        h = wcs_cards(fits.Header(), n=41); h['DATE-OBS'] = '2025-12-12T21:20:32.000'; h['EXPTIME'] = 60.0
        hdu = fits.PrimaryHDU(raw.astype(np.int16), header=h, do_not_scale_image_data=True)
        hdu.header['BZERO'] = 32768; hdu.header['BSCALE'] = 1; hdu.header['BLANK'] = blank
        p = self.p('blank.fits'); hdu.writeto(p, overwrite=True)
        return p

    def test_t1_2_a_blank_that_is_not_an_integer_keeps_the_answer(self):
        # e7051b4: "cannot measure: TypeError" (no value) and "invalid literal for int()" (a string), exit 1; the page measures
        for name, blank in (('BLANK with no value', None), ("BLANK = 'x'", 'x')):
            with self.subTest(name):
                p = self.blank_frame(blank)
                try:
                    r = cli.measure_file(p, estimator='M')
                except Exception as e:
                    self.fail('raised %s: %s' % (type(e).__name__, str(e)[:120]))
                self.assertTrue(np.isfinite(r['x0']))
                rc, out = run_main([p])                               # the comet gate refuses this 41-px frame (34 of 41 radii
                self.assertEqual(rc, 2); self.assertIn('# zero aperture:', out)   # converge): 2, his exit codes (the fix room's F2)
                if blank is not None:                                 # said, not silent: no pixel is taken as blank
                    self.assertTrue(any('BLANK' in n for n in r['notes']), r['notes'])

    def test_t1_10_the_curve_never_overwrites_the_input(self):
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        link = self.p('link.fits'); os.symlink(p, link)
        for name, target in (('the same path', p), ('a second name for the same file', link)):
            with self.subTest(name):
                before = open(p, 'rb').read()
                rc, out = run_main([p, '--curve', target] + given(p) + REC_ARGS)   # e7051b4: the FITS file truncated into a CSV
                self.assertEqual(open(p, 'rb').read(), before)
                self.assertEqual(rc, 0); self.assertIn('# version=2022', out)
                self.assertTrue(any('curve' in ln for ln in lines_starting(out, '# no curve file')), out[-400:])

    def test_t4_6_a_name_the_console_cannot_encode_keeps_the_record(self):
        # Windows, output redirected: Python writes in the code page (cp1252 simulated here), which has no 'Ł'. e7051b4: exit 1,
        # a UnicodeEncodeError traceback, the record lost. The MPC's judge accepts such a name (T4.6's check), so it is kept
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        args = [a if a != 'A. N. Observer' else 'Łukasz Ołów' for a in REC_ARGS]
        r = subprocess.run([sys.executable, '-m', 'domino_calibrator.cli', p] + given(p) + args, capture_output=True, cwd=ROOT, timeout=300,
                           env=dict(os.environ, PYTHONIOENCODING='cp1252', PYTHONPATH=ROOT, PYTHONDONTWRITEBYTECODE='1'))
        self.assertEqual(r.returncode, 0, r.stderr.decode('utf-8', 'replace')[-300:])
        out = r.stdout.decode('utf-8')
        self.assertIn('! name Łukasz Ołów', out)


# ---------------------------------------------------------------- the MPC's judge on Part A's records (bar item 4)
@unittest.skipIf(not (ADES_PYLIB and ADES_MASTER), 'the MPC judge needs ADES_PYLIB and ADES_MASTER (see test_hardening)')
class TestMPCJudge3(Tmp):
    def test_judge_accepts_round_3s_cli_records(self):
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        rc, out = run_main([p] + given(p) + [a if a != 'A. N. Observer' else 'Łukasz Ołów' for a in REC_ARGS])
        with self.subTest('control: a name outside ASCII (in-process, no code page in the way)'):
            self.assertIn('# version=2022', out)
            ok, why = mpc_judge(out[out.index('# version='):], self.d)
            self.assertTrue(ok, why)
        if os.path.exists(FLC):                                       # control: the command line on a real HST frame
            with self.subTest("control: an HST _flc frame (SCI,1), its lookup tables read"):
                rc, out = run_main([FLC, '--x', '685', '--y', '734', '--estimator', 'M'] + REC_ARGS)
                self.assertIn('# version=2022', out, out[-400:])
                ok, why = mpc_judge(out[out.index('# version='):], self.d)
                self.assertTrue(ok, why)


if __name__ == '__main__':
    unittest.main()
