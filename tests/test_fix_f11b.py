"""The fix room's F11b: two of the second audit room's should-fixes, the record's uncertainty (1 Oct 2026, his yes to all 27,
the fix room's record of 1 Oct 2026, not in this repository, section 26). Written before the fix, to fail on the tool as F11 left it, and
to pass once it is fixed. By the report's numbers (11.2):
7 (F2.1)  --rms-noise from 3-5 redraws wrote a collapsed ellipse (rmsCorr -0.99) and a too-small rmsRA at full precision.
8 (F2.2)  --rms-noise wrote the sky noise as rmsRA and rmsDec; the line as printed validated, and the hand edits were easy to
          skip. His choice: the record never presents sky noise alone as the whole uncertainty. ADES defines rmsRA and rmsDec
          as the random uncertainty of the whole image processing and astrometric reduction, so the room's form (for his
          review): the record carries no rmsRA, rmsDec or rmsCorr from the sky noise; the scatter is printed beside it, in
          arcsec at two significant figures, with its number of redraws, how rough that many make it, and what to do.
"""
import math, os, re, unittest, warnings

import numpy as np

from domino_calibrator import cli
from tests.test_hardening import REC_ARGS, Tmp, comet, write, run_main, given
from tests.test_hardening_2 import record_row

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def noisy(d):
    img, _ = comet()
    return write(os.path.join(d, 'c.fits'), img + np.random.default_rng(3).normal(0, 3.0, img.shape))


def record(out):
    at = out.find('# version=2022')
    return out[at:] if at >= 0 else None


def scatter(out):
    m = re.search(r'^# sky-noise scatter on the sky, from (\d+) of (\d+) redraws: RA\*cos\(Dec\) (\S+)", Dec (\S+)"(.*)$', out, re.M)
    return m


class F11b_8_NoSkyNoiseInTheRecord(Tmp):
    def test_the_record_carries_no_rms_from_the_sky_noise(self):
        p = noisy(self.d)
        rc, out = run_main([p, '--rms-noise', '5'] + given(p) + REC_ARGS)
        self.assertEqual(rc, 0, out[-500:])
        row = record_row(record(out))
        for k in ('rmsRA', 'rmsDec', 'rmsCorr'):
            self.assertNotIn(k, row, row)
        self.assertNotIn('rms', row['remarks'])
        self.assertEqual(len(row['ra'].split('.')[1]), 6, row)               # the record's own 6 decimals, as without --rms-noise
        rc0, out0 = run_main([p] + given(p) + REC_ARGS)                      # the control: the same record without --rms-noise
        self.assertEqual(record(out), record(out0))

    def test_the_scatter_is_printed_beside_it_with_what_to_do(self):
        p = noisy(self.d)
        rc, out = run_main([p, '--rms-noise', '5'] + given(p) + REC_ARGS)
        m = scatter(out)
        self.assertIsNotNone(m, out[-800:])
        self.assertEqual((m.group(1), m.group(2)), ('5', '5'))
        for v in (m.group(3), m.group(4)):
            self.assertRegex(v, r'^0\.0*[1-9]\d?$|^[1-9]\.\d$|^[1-9]\d$')   # two significant figures
        said = ' '.join(l for l in out.splitlines() if l.startswith('# '))
        self.assertRegex(said, r"sky noise only[^.]*not in the record")
        self.assertRegex(said, r"plate solution's random error[^.]*in quadrature")
        self.assertRegex(said, r'two significant figures')
        self.assertLess(out.find('# sky-noise scatter'), out.find('# version=2022'))


class F11b_7_FewRedraws(Tmp):
    def test_few_redraws_say_how_rough_and_give_no_correlation(self):
        p = noisy(self.d)
        for n, corr in ((5, False), (30, True)):
            with self.subTest(redraws=n):
                rc, out = run_main([p, '--rms-noise', str(n)] + given(p) + REC_ARGS)
                m = scatter(out)
                self.assertIsNotNone(m, out[-800:])
                rough = round(100 / math.sqrt(2 * (n - 1)))
                self.assertIn('good to about %d%%' % rough, m.group(5))
                self.assertEqual(bool(re.search(r'correlation [+-]\d', m.group(5))), corr, m.group(5))   # amendment 1: a value, not the word
                if not corr:
                    self.assertIn('no correlation from fewer than %d redraws' % cli.CORR_MIN, m.group(5))


class F11b_TheWords(unittest.TestCase):
    def test_help_and_readme_say_the_record_holds_no_sky_noise_rms(self):
        import contextlib, io
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                cli.main(['--help'])
            except SystemExit:
                pass
        helptext = ' '.join(buf.getvalue().split())
        readme = ' '.join(re.sub(r'```.*?```', ' ', open(os.path.join(PKG, 'README.md'), encoding='utf-8').read(), flags=re.S).split())
        for face, t in (('--help', helptext), ('README.md', readme)):
            with self.subTest(face):
                self.assertRegex(t, r'record carries no rmsRA, rmsDec or rmsCorr')
                self.assertRegex(t, r"plate solution's random error[^.]*in quadrature")
                self.assertNotRegex(t, r'delete rmsCorr')
                self.assertNotRegex(t, r"delete the remarks' rms clause")


if __name__ == '__main__':
    unittest.main()
