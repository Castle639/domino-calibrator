"""The fifth refuter pass (the refuters' record of 29 Sept 2026, not in this repository): his amendment E2, as tests. Written to fail on the
calibrator as the fourth pass left it (dbf15a0; the folder unchanged since but for logs, 4e321c5) and to pass once the
words are fixed; every case is a subTest, and the cases marked "control" pass before and after.
- E2 (his amendment, the sequel of D1.6): with --rms-noise the README and --help told the user to add the plate solution's
  error to rmsRA and rmsDec before submitting, and no more. A user who does exactly that submits a remark that has become
  false ("the sky-noise scatter only, without the plate solution error") and an rmsCorr from the sky noise alone, about
  800 times too strong for a 0.1 arcsec plate error. The words name the whole edit: the error added in quadrature,
  rmsCorr deleted, the remarks' rms clause deleted; and they say what the remarks do say. The fix is in the words only.
"""
import contextlib, io, math, os, re, shutil, tempfile, unittest, warnings
import numpy as np

from domino_calibrator import cli
from tests.test_hardening import comet, write, run_main, REC_ARGS, mpc_judge, ADES_PYLIB, ADES_MASTER, given
from tests.test_hardening_2 import record_row

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def faces():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            cli.main(['--help'])
        except SystemExit:
            pass
    helptext = ' '.join(buf.getvalue().split())
    readme = ' '.join(re.sub(r'```.*?```', ' ', open(os.path.join(PKG, 'README.md'), encoding='utf-8').read(), flags=re.S).split())
    return (('--help', helptext), ('README.md', readme))


def follow_the_words(out, plate=0.1):
    """The edit the words ask for, done as a user would (F11b): rmsRA and rmsDec added to the record after dec, each the
    printed sky scatter and the plate solution's error in quadrature, at two significant figures."""
    psv = out[out.find('# version=2022'):]
    s = re.search(r'^# sky-noise scatter on the sky, [^:]*: RA\*cos\(Dec\) (\S+)", Dec (\S+)"', out, re.M)
    lines = psv.rstrip('\n').split('\n')
    keys, vals = [s_.strip() for s_ in lines[-2].split('|')], [s_.strip() for s_ in lines[-1].split('|')]
    i = keys.index('dec') + 1
    new = ['%.2g' % math.hypot(float(v), plate) for v in s.groups()]
    keys[i:i], vals[i:i] = ['rmsRA', 'rmsDec'], new
    return '\n'.join(lines[:-2] + ['|'.join(keys), '|'.join(vals)]) + '\n'


class TestE2TheWordsNameTheWholeEdit(unittest.TestCase):
    def test_e2_the_instruction_names_every_field_it_changes(self):
        for face, t in faces():
            with self.subTest(face, part='the error goes in in quadrature'):      # dbf15a0, --help: "add your plate solution's before submitting"
                self.assertRegex(t, r"plate solution's random error[^.]*in quadrature")
            with self.subTest(face, part='no rmsCorr and no remark to delete'):   # F11b: the record holds no rms, so no hand deletion
                self.assertNotRegex(t, r'delete rmsCorr')
                self.assertNotRegex(t, r"delete the remarks' rms clause")

    def test_e2_the_words_say_what_the_remarks_say(self):
        for face, t in faces():
            with self.subTest(face):                    # dbf15a0: "(the record's remarks say so)"; F11b: the record says nothing of it
                self.assertRegex(t, r'record carries no rmsRA, rmsDec or rmsCorr')
                self.assertNotRegex(t, r'remarks say')

    def test_e2_control_the_d1_6_words_stay(self):
        for face, t in faces():
            with self.subTest(face):                    # control: D1.6's own test, unchanged
                self.assertRegex(t, r'rmsRA[^.]*sky-noise[^.]*only')
                self.assertRegex(t, r'plate solution')


class TestE2TheRecordAndTheEdit(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore')
        self.d = tempfile.mkdtemp()
        img, _ = comet()
        self.c = write(os.path.join(self.d, 'c.fits'), img + np.random.default_rng(3).normal(0, 3.0, img.shape))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def record(self, whole=False):
        rc, out = run_main([self.c, '--rms-noise', '5'] + given(self.c) + REC_ARGS)
        self.assertEqual(rc, 0, out)
        at = out.find('# version=2022')
        self.assertGreaterEqual(at, 0, out)
        return out if whole else out[at:]

    def test_e2_the_record_holds_no_rms(self):
        row = record_row(self.record())
        with self.subTest('no rmsRA, rmsDec or rmsCorr (F11b, his choice for the audit\'s F2.2)'):
            self.assertFalse(row.get('rmsRA') or row.get('rmsDec') or row.get('rmsCorr'), row)
        with self.subTest('no rms clause in the remarks'):
            self.assertNotIn('rms', row['remarks'])

    @unittest.skipIf(not (ADES_PYLIB and ADES_MASTER), 'the MPC judge needs ADES_PYLIB and ADES_MASTER')
    def test_e2_control_the_judge_accepts_the_record_edited_as_the_words_say(self):
        edited = follow_the_words(self.record(whole=True))
        row = record_row(edited)
        with self.subTest('control: the edit adds rmsRA and rmsDec, the plate error in them, and no rmsCorr'):
            self.assertNotIn('rmsCorr', row)
            self.assertNotIn('rms', row['remarks'])
            self.assertAlmostEqual(float(row['rmsRA']), 0.1, delta=0.01)
        d = tempfile.mkdtemp()
        try:
            ok, why = mpc_judge(edited, d)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        with self.subTest('control: the MPC judge accepts it'):
            self.assertTrue(ok, why)


if __name__ == '__main__':
    unittest.main()
