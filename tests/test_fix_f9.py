"""The fix room's F9: B1's rest, from the second audit room's report (1 Oct 2026, his word for the night,
the fix room's record of 1 Oct 2026, not in this repository, section 24). Written before the fix, to fail on the tool as F8 left it, and to
pass once it is fixed. His rule, as F8 has it: no record from a sky solution that differs from what the header says.

Face 3 (the audit's F8.1): a WCS number written in quotes ('151.5') passed the number check and wcslib read it as 0; a logical
(T) did the same. A number in quotes is now read as its number, as the page reads it; a logical is no number, refused on both
faces in the page's words. The backstop compares these too (it skipped text and logicals).
Face 4 (the audit's F8.8): the page did not read LONPOLE, and wrote a record 32.6" from the command line's. It now refuses a
LONPOLE other than the default it applies (180), as it refuses the other cards it cannot apply; LONPOLE is a WCS number on
both faces.
"""
import os, re, sys, subprocess, unittest, warnings

import numpy as np
from astropy.io import fits
from astropy.wcs import WCS

from domino_calibrator import ades as A
from tests.test_hardening import REC_ARGS, Tmp, comet, write, given
from tests.test_hardening_page import js

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FAR = dict(CRPIX1=1.0, CRPIX2=1.0)          # the comet 34 px from CRPIX: a misread card or pole moves it far


def cli_run(args):
    r = subprocess.run([sys.executable, '-m', 'domino_calibrator.cli'] + args, cwd=ROOT, capture_output=True, encoding='utf-8',
                       errors='replace', timeout=600, env=dict(os.environ, PYTHONUTF8='1'))
    return r.returncode, r.stdout + r.stderr


def lines(out):
    return [l for l in out.splitlines() if l.startswith('# sky (ICRS)') or l.startswith('3I ')]


def page(path):
    """The page's engine on the file, from the start the command line uses here (the comet's box): (need, rd)."""
    return js("""
const fs = require('fs');
const hdus = Z.parseFITS(new Uint8Array(fs.readFileSync(D.p)).buffer), cur = hdus.find((u) => u.readable);
const s = Z.brightestStart(cur.data, cur.nx, cur.ny);
const o = Z.shrink(cur.data, cur.nx, cur.ny, s[0], s[1], { estimator: 'G', radii: Z.publishedRadii(), background: 'annulus' });
const r = Z.decide({ cur: cur, hdus: hdus, o: o, start: s, auto: false });   // the start given (F10)
out = { need: r.need, rd: r.rd };""", {'p': path})


def sky(out):
    m = re.search(r'# sky \(ICRS\): RA (\S+), Dec (\S+) deg', out)
    return (float(m.group(1)), float(m.group(2))) if m else None


class F9_1_Face3TheCommandLine(Tmp):
    def test_a_number_in_quotes_is_read_as_its_number(self):
        img, _ = comet()
        ctl = write(os.path.join(self.d, 'ctl.fits'), img, **FAR)
        rc0, out0 = cli_run([ctl] + given(ctl) + REC_ARGS)
        self.assertEqual(rc0, 0, out0[-400:]); self.assertEqual(len(lines(out0)), 2)
        for key, text in (('CRVAL1', '168.7'), ('CRVAL2', '4.6'), ('CD2_2', '%r' % (1.0 / 3600))):
            with self.subTest(key):
                p = write(os.path.join(self.d, 'q.fits'), img, **dict(FAR, **{key: text}))       # astropy writes it in quotes
                self.assertIsInstance(fits.getheader(p)[key], str)
                rc, out = cli_run([p] + given(p) + REC_ARGS)
                self.assertEqual(rc, 0, out[-400:])
                self.assertEqual(lines(out), lines(out0))

    def test_a_logical_is_no_number(self):
        img, _ = comet()
        for key, v, t in (('CRVAL1', True, 'T'), ('CD1_1', False, 'F'), ('LONPOLE', True, 'T')):
            with self.subTest(key):
                p = write(os.path.join(self.d, 'l.fits'), img, **dict(FAR, **{key: v}))
                rc, out = cli_run([p] + given(p) + REC_ARGS)
                self.assertEqual(rc, 2, out[-400:])
                self.assertNotIn('# version=2022', out)
                self.assertIn("needs a sky position (the WCS card %s = '%s' is not a number)" % (key, t), out)


class F9_2_TheBackstopReadsTextAndLogicals(unittest.TestCase):
    def header(self, key, v):
        h = fits.Header()
        for k, x in (('NAXIS', 2), ('NAXIS1', 71), ('NAXIS2', 71), ('CTYPE1', 'RA---TAN'), ('CTYPE2', 'DEC--TAN'), ('CRPIX1', 1.0),
                     ('CRPIX2', 1.0), ('CRVAL1', 151.5), ('CRVAL2', 10.4), ('CD1_1', -1e-4), ('CD1_2', 0.0), ('CD2_1', 0.0),
                     ('CD2_2', 1e-4), ('RADESYS', 'ICRS')):
            h[k] = x
        h[key] = v
        return h

    def test_a_wcs_that_read_a_quoted_number_or_a_logical_otherwise_is_refused(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            for key, v in (('CRVAL1', '151.5'), ('CRVAL1', True), ('LONPOLE', '0')):
                with self.subTest(key=key, v=v):
                    h = self.header(key, v)
                    w = WCS(h).celestial                          # wcslib, reading the card's text
                    self.assertIsNotNone(A.wcs_as_read(h, w), (key, v))
            h = self.header('CRVAL1', 151.5)                      # the control, written as a number
            self.assertIsNone(A.wcs_as_read(h, WCS(h).celestial))


class F9_3_BothFaces(Tmp):
    def test_lonpole_the_page_refuses_what_it_does_not_apply(self):
        img, _ = comet()
        for lp in (180.0, 0.0, 90.0):
            with self.subTest(LONPOLE=lp):
                p = write(os.path.join(self.d, 'lp.fits'), img, **dict(FAR, LONPOLE=lp))
                rc, out = cli_run([p] + given(p) + REC_ARGS)
                self.assertEqual(rc, 0, out[-400:])                # wcslib applies LONPOLE: the command line's record
                pg = page(p)
                if lp == 180.0:
                    self.assertEqual(pg['need'], [])
                    s = sky(out)
                    self.assertLess(abs(pg['rd'][0] - s[0]) + abs(pg['rd'][1] - s[1]), 2e-6)
                else:
                    self.assertIsNone(pg['rd'])
                    self.assertTrue(any('LONPOLE' in n for n in pg['need']), pg['need'])

    def test_a_logical_is_no_number_on_the_page(self):
        img, _ = comet()
        p = write(os.path.join(self.d, 't.fits'), img, **dict(FAR, CRVAL1=True))
        pg = page(p)
        self.assertIsNone(pg['rd'])
        self.assertIn("a sky position (the WCS card CRVAL1 = 'T' is not a number)", pg['need'])


if __name__ == '__main__':
    unittest.main()
