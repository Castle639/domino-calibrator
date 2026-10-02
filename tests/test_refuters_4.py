"""The release's refuter pass (the refuters' third record of 28 Sept 2026, not in this repository): the sort's class 1 and class 2 findings, and his
amendment, as tests, for the command line; the page's share is test_refuters_4_page.py and the words' is
test_release_words.py (W3's new claims and W7). Written to fail on the calibrator as the seventh room left it (0e311b5; the
folder unchanged since but for logs, 84a0881) and to pass once each fix is in; every case is a subTest, and the cases
marked "control" pass before and after.
- D1.2 (class 1): "r=2" was the photocentre at the radius nearest 2 px, whatever --radii said: `--radii 3:8:0.1` printed
  the r = 3.0 photocentre as "r=2". The label names the radius it reports.
- D1.1 (class 2): round 3's size check (T4.17) compared astropy's offset in the decompressed stream with a gzipped file's
  size on disk, so every sound .fits.gz was refused as truncated, while the page sends a .gz to the command line, "which
  reads it". The command line reads it again, and a cut-short file is still named cut short.
- D1.6 (his amendment): rmsRA and rmsDec were the scatter under sky-noise redraws only, and the record did not say so;
  ADES defines them as the random uncertainty of the whole reduction. The record's remarks, --help and the README say it.
"""
import bz2, contextlib, gzip, io, os, re, shutil, tempfile, unittest, warnings
import numpy as np

from domino_calibrator import cli
from tests.test_hardening import comet, write, run_main, REC_ARGS, mpc_judge, ADES_PYLIB, ADES_MASTER, given
from tests.test_hardening_2 import record_row

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)


def zero_line(out):
    return next((ln for ln in out.splitlines() if ln.startswith('# zero aperture:')), '')


class TestD12TheRadiusIsNamed(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore')
        self.d = tempfile.mkdtemp()
        img, _ = comet()
        self.c = write(os.path.join(self.d, 'c.fits'), img)

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def test_d1_2_r_is_2_only_at_2(self):
        cases = [('control: the published radii', [], 'r=2: (35.0837, 34.9498; 0-based; add 1 for ds9)'),   # the ds9 words since
                 ('radii 3-8 px: the photocentre at 3.0 px was printed as "r=2"', ['--radii', '3:8:0.1'],   # the fix room's F2
                  'r=3.0: (35.0920, 34.9499; 0-based; add 1 for ds9)'),
                 ('radii 2.05-5.95 px: at 2.05 px, printed as "r=2"', ['--radii', '2.05:5.95:0.05'], 'r=2.05: (')]
        for name, extra, want in cases:
            with self.subTest(name):
                rc, out = run_main([self.c] + extra)
                self.assertEqual(rc, 0, out)
                self.assertIn('| ' + want, zero_line(out))
                if extra:
                    self.assertNotIn('r=2:', out)


class TestD11TheCommandLineReadsAGzip(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore')
        self.d = tempfile.mkdtemp()
        img, _ = comet()
        self.c = write(os.path.join(self.d, 'c.fits'), img)
        self.raw = open(self.c, 'rb').read()

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def p(self, name, data):
        path = os.path.join(self.d, name)
        open(path, 'wb').write(data)
        return path

    def answer(self, out):
        return [ln for ln in out.splitlines() if ln.startswith(('# zero aperture:', '# sky (ICRS):', '# time:'))]

    def test_d1_1_a_compressed_file_is_measured_as_the_file_itself(self):
        rc0, out0 = run_main([self.c])
        with self.subTest('control: the file itself'):
            self.assertEqual(rc0, 0, out0)
            self.assertEqual(len(self.answer(out0)), 3, out0)
        for name, data in (('c.fits.gz', gzip.compress(self.raw)), ('c.fits.bz2', bz2.compress(self.raw))):
            with self.subTest(name):                  # 0e311b5: "HDU 0: the file ends before its data does (...): it is truncated"
                rc, out = run_main([self.p(name, data)])
                self.assertEqual(rc, 0, out)
                self.assertEqual(self.answer(out), self.answer(out0))

    def test_d1_1_the_pages_sentence_holds(self):
        # the page refuses a .gz and sends it to the command line, "which reads it" (zeroap.js): the sentence is true
        js = open(os.path.join(PKG, 'page', 'zeroap.js'), encoding='utf-8').read()
        said = re.search(r"a gzipped file \(\.gz\)[^']*'[^;]*which reads it", js)
        self.assertIsNotNone(said, 'the page no longer says the command line reads a .gz: this test needs its sentence')
        rc, out = run_main([self.p('c.fits.gz', gzip.compress(self.raw))])
        self.assertEqual(rc, 0, out)

    def test_d1_1_a_cut_short_file_is_still_refused(self):
        # the bar's one amendment, before any fix: the gzipped case was written expecting "truncated"; on 0e311b5 it says
        # "Empty or corrupt FITS file" (astropy's words, on one line), so it asks what it can carry: one line, no traceback
        z = gzip.compress(self.raw)
        cases = [('control: an uncompressed file cut halfway (T4.17)', 'half.fits', self.raw[:len(self.raw) // 2], 'truncated'),
                 ('control: a gzipped file cut halfway', 'half.fits.gz', z[:len(z) // 2], None)]
        for name, fn, data, word in cases:
            with self.subTest(name):
                rc, out = run_main([self.p(fn, data)])
                self.assertEqual(rc, 1, out)
                lines = [ln for ln in out.splitlines() if ln.strip()]
                self.assertEqual(len(lines), 1, out)
                self.assertTrue(lines[0].startswith('# cannot measure:'), out)
                if word:
                    self.assertIn(word, lines[0])


class TestD16TheRmsSaysWhatItIs(unittest.TestCase):
    def setUp(self):
        warnings.simplefilter('ignore')
        self.d = tempfile.mkdtemp()
        img, _ = comet()
        self.c = write(os.path.join(self.d, 'c.fits'), img + np.random.default_rng(3).normal(0, 3.0, img.shape))

    def tearDown(self):
        shutil.rmtree(self.d, ignore_errors=True)

    def record(self, extra):
        rc, out = run_main([self.c] + given(self.c) + extra + REC_ARGS)
        self.assertEqual(rc, 0, out)
        at = out.find('# version=2022')
        self.assertGreaterEqual(at, 0, out)
        return out[at:]

    def test_d1_6_the_records_remarks_name_the_rms(self):
        with self.subTest('with --rms-noise: no rms in the record, and no word about one (F11b, his choice for the audit\'s F2.2)'):
            row = record_row(self.record(['--rms-noise', '5']))   # D1.6's remark is gone with the rms it explained
            for k in ('rmsRA', 'rmsDec', 'rmsCorr'):
                self.assertNotIn(k, row, row)
            self.assertNotIn('rms', row['remarks'])
        with self.subTest('control: without --rms-noise, no rms and no word about one'):
            row = record_row(self.record([]))
            self.assertFalse(row.get('rmsRA'), row)
            self.assertNotIn('rms', row['remarks'])

    def test_d1_6_help_and_readme_name_the_rms(self):
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf):
            try:
                cli.main(['--help'])
            except SystemExit:
                pass
        helptext = ' '.join(buf.getvalue().split())
        readme = ' '.join(re.sub(r'```.*?```', ' ', open(os.path.join(PKG, 'README.md'), encoding='utf-8').read(), flags=re.S).split())
        for face, t in (('--help', helptext), ('README.md', readme)):
            with self.subTest(face):                   # 0e311b5: "(sky-limited approximation)" in --help; nothing in the README
                self.assertRegex(t, r'rmsRA[^.]*sky-noise[^.]*only')
                self.assertRegex(t, r'plate solution')

    @unittest.skipIf(not (ADES_PYLIB and ADES_MASTER), 'the MPC judge needs ADES_PYLIB and ADES_MASTER')
    def test_judge_accepts_the_record_with_its_rms_and_its_remark(self):
        # control: the record with rmsRA, rmsDec and rmsCorr, before and after its remark grows
        d = tempfile.mkdtemp()
        try:
            ok, why = mpc_judge(self.record(['--rms-noise', '5']), d)
        finally:
            shutil.rmtree(d, ignore_errors=True)
        self.assertTrue(ok, why)


if __name__ == '__main__':
    unittest.main()
