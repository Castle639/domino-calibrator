"""The fix room's F11: seven of the second audit room's should-fixes, the tool's own (1 Oct 2026, his yes to all 27,
the fix room's record of 1 Oct 2026, not in this repository, section 26). Written before the fix, to fail on the tool as F10 left it, and
to pass once it is fixed. By the report's numbers (11.2): 2 (F1.2), 9 (F2.3), 14 (F8.4), 15 (F8.5), 16 (F8.6), 18 (F8.9),
19 (F8.10).
"""
import os, re, sys, subprocess, unittest, warnings

import numpy as np
from astropy.io import fits

from domino_calibrator import cli, ades as A
from tests.test_hardening import REC, REC_ARGS, Tmp, comet, write, wcs_cards
from tests.test_hardening_page import js

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)


def cli_run(args):
    r = subprocess.run([sys.executable, '-m', 'domino_calibrator.cli'] + args, cwd=ROOT, capture_output=True, encoding='utf-8',
                       errors='replace', timeout=600, env=dict(os.environ, PYTHONUTF8='1'))
    return r.returncode, r.stdout, r.stderr


def engine(path, start):
    return js("""
const fs = require('fs');
const hdus = Z.parseFITS(new Uint8Array(fs.readFileSync(D.p)).buffer), cur = hdus.find((u) => u.readable);
const o = Z.shrink(cur.data, cur.nx, cur.ny, D.start[0], D.start[1], { estimator: 'G', radii: Z.publishedRadii(), background: 'annulus' });
out = Z.decide({ cur: cur, hdus: hdus, o: o, start: D.start, auto: false }).need;""", {'p': path, 'start': start})


def header(n=71):
    h = wcs_cards(fits.Header(), n=n); h['DATE-OBS'] = '2025-12-12T21:20:32.000'; h['EXPTIME'] = 60.0
    return h


class F11_2_NoWarningsFlood(Tmp):
    def test_a_start_off_the_comet_says_why_without_numpys_warnings(self):
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        rc, out, err = cli_run([p, '--x', '12', '--y', '12', '--rms-noise', '50'] + REC_ARGS)
        self.assertEqual(rc, 2, out[-300:])
        self.assertIn('needs a comet measured', out)
        self.assertNotIn('RuntimeWarning', err, err[-600:])


class F11_9_SaturateInTheInheritedPrimary(Tmp):
    def test_the_primarys_saturate_is_read_for_an_inherit_t_image_on_both_faces(self):
        img, _ = comet()
        ph = header(); ph['SATURATE'] = float(img.max()) - 1.0
        for own in (False, True):
            with self.subTest(saturate='the image HDU' if own else 'the primary, INHERIT = T'):
                ih = fits.Header(); ih['INHERIT'] = True
                if own:
                    ih['SATURATE'] = ph['SATURATE']
                p = self.p('mef_%s.fits' % own)
                fits.HDUList([fits.PrimaryHDU(header=ph), fits.ImageHDU(img.astype(np.float32), header=ih)]).writeto(p, overwrite=True)
                r = cli.measure_file(p, 35, 35, ades=dict(REC))
                self.assertIn('its peak is clipped (at SATURATE', r.get('comet_error') or '', r.get('comet_error'))
                self.assertTrue(any('its peak is clipped (at SATURATE' in n for n in engine(p, [35, 35])))


class F11_14_AFlatSkyRing(Tmp):
    def test_a_sky_ring_whose_mad_is_0_still_takes_the_10_sigma_test(self):
        yy, xx = np.mgrid[0:71, 0:71]
        rr = np.hypot(xx - 35.05, yy - 34.95)
        for seed in (1, 3):
            with self.subTest(seed=seed):
                img = 100.0 + 30.0 * np.exp(-rr ** 2 / (2 * 2.5 ** 2)) + np.random.default_rng(seed).normal(0, 7, rr.shape)
                flat = (rr > 8) & (np.random.default_rng(seed + 10).random(rr.shape) < 0.55)
                img[flat] = 100.0                                     # the audit's F8.4: 55% of the sky beyond 8 px exactly 100
                p = write(self.p('f.fits'), img)
                r = cli.measure_file(p, 35, 35, ades=dict(REC))
                self.assertNotIn('ades', r)
                self.assertIn('too faint', r.get('comet_error') or '', r.get('comet_error'))
                self.assertTrue(any('too faint' in n for n in engine(p, [35, 35])))

    def test_a_flat_ring_says_so(self):
        img, _ = comet()
        yy, xx = np.mgrid[0:71, 0:71]
        img = np.where(np.hypot(xx - 35.05, yy - 34.95) > 12, 100.0, img)
        p = write(self.p('flat.fits'), img)
        r = cli.measure_file(p, 35, 35, ades=dict(REC))
        self.assertIn('its sky ring is flat', r.get('comet_error') or '', r.get('comet_error'))
        self.assertTrue(any('its sky ring is flat' in n for n in engine(p, [35, 35])))


class F11_15_NamesThatBreakTheMPCsTools(unittest.TestCase):
    def test_noncharacters_and_line_separators_are_refused_on_both_faces(self):
        for ch in ('￾', '￿', ' ', ' '):
            with self.subTest('U+%04X' % ord(ch)):
                with self.assertRaises(ValueError) as e:
                    A.ades_psv(168.7, 4.6, '2025-12-12T21:21:02.00Z', **dict(REC, submitter='A. N. Obs%srver' % ch))
                self.assertIn('U+%04X' % ord(ch), str(e.exception))
                page = js("out = Z.adesPSV(Object.assign({ ra: 168.7, dec: 4.6, time: '2025-12-12T21:21:02.00Z' }, D));",
                          dict(stn='568', desig='3I', mode='CCD', astCat='Gaia3', submitter='A. N. Obs%srver' % ch,
                               measurers=['A. N. Observer'], design='Reflector', aperture='0.5', detector='CCD'))
                self.assertIn('U+%04X' % ord(ch), str(page))


class F11_16_AOnePlaneCube(Tmp):
    def test_a_one_plane_cube_gives_the_sky_position_its_2_axis_wcs_gives(self):
        img, _ = comet()
        p2 = write(self.p('flat.fits'), img)
        p3 = self.p('cube.fits')
        fits.PrimaryHDU(img[None].astype(np.float32), header=header()).writeto(p3, overwrite=True)
        r2, r3 = cli.measure_file(p2, 35, 35, ades=dict(REC)), cli.measure_file(p3, 35, 35, ades=dict(REC))
        self.assertIn('radec', r3, r3.get('sky_error'))
        self.assertAlmostEqual(r3['radec'][0], r2['radec'][0], places=9); self.assertAlmostEqual(r3['radec'][1], r2['radec'][1], places=9)


class F11_18_TheRadii(Tmp):
    def test_radii_that_break_the_cap_or_collapse_are_refused(self):
        for s in ('1e-9:1e-9:1e-13', '3:3.0000001:1e-10', '1e308:1e308:1', '0.001:1000:1'):
            with self.subTest(s):
                with self.assertRaises(ValueError) as e:
                    cli._radii(s)
                self.assertIn('--radii', str(e.exception))
        self.assertEqual(len(cli._radii('2.0:6.0:0.1')), 41)                    # the control: the published radii


class F11_19_AnUnparsableCtype1(Tmp):
    def test_the_pixel_answer_stands_and_the_sky_is_refused(self):
        img, _ = comet()
        p = write(self.p('c.fits'), img)
        b = bytearray(open(p, 'rb').read())
        i = b.find(b'CTYPE1  = ')
        b[i:i + 80] = ("CTYPE1  = 'RA---TAN'  x").ljust(80).encode('ascii')               # junk after the quote (the audit's F8.10)
        open(p, 'wb').write(bytes(b))
        rc, out, err = cli_run([p, '--x', '35', '--y', '35'] + REC_ARGS)
        self.assertNotIn('cannot measure', out)
        self.assertRegex(out, r'# zero aperture: x \S+ y \S+')
        self.assertEqual(rc, 2, out[-300:])
        self.assertIn('needs a sky position', out)


if __name__ == '__main__':
    unittest.main()
