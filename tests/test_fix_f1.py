"""The fix room's F1: the record as an MPC reviewer would see it (1 Oct 2026; the fix room's record of 1 Oct 2026, not in this repository).
Written before the fix, to fail on the tool as the launch room left it (main at c372783), and to pass once the record is fixed.
His answers (the launch room's report, section 11, and this room's section 4), item by item, as the launch room numbered the
audit's should-fixes; ADES read at source (the ADES description of 16 Mar 2026 in IAU-ADES/ades-master at 39ae5a9,
doc/ADES_Description_16Mar2026.docx, and xsd/submit.xsd):

1  A station with no fixed position in the MPC's list (space-based or roving: 31 codes; runs/MPC_OBSCODES_NO_POSITION_2026-10-01.json)
   gives no record, with the reason: ADES's Location Group "must be present for such cases", and this tool does not write it.
2  rmsRA and rmsDec at two significant figures: "Reported uncertainties should be reported with two significant figures if the
   leading significant digit is '1', otherwise either one or two ... Submissions with more than two significant figures in
   reported uncertainties may be rejected by the MPC." The tool writes two.
3  ra and dec with as many decimals as the uncertainty supports, "DP = CEILING(1 - LOG10(SIGMA))", SIGMA the written rms in
   degrees (RA's divided by cos Dec, since ra is RA itself), at most the schema's 9; without an rms, 6 decimals (0.0036"): his
   choice of a fixed default far below any ground uncertainty (Table 15 gives no format for ra or dec).
4  Names asked as initials, then surname: "Names of measurers (initials then surname)", the same for observers.
6  The record names the software in ADES's place for it (Table 18: software, astrometry, "Description of software used for
   astrometry"), with the version and the part it did: ADES has no place of its own for the plate solution's program.
7  A name holding a control character, or bytes that are not UTF-8, is refused with the reason, on both faces.
8  A designation holding a character outside ASCII (３I, ٣I) is refused with the reason, on both faces.
Every record the tests make is put to the MPC's judge where it is installed (ADES_PYLIB, ADES_MASTER).
"""
import os, re, sys, json, math, shutil, tempfile, subprocess, unittest, warnings

from domino_calibrator import cli, ades as A, __version__
from tests.test_hardening import REC, REC_ARGS, Tmp, run_main, comet, write, mpc_judge, ADES_PYLIB, ADES_MASTER, start, given
from tests.test_hardening_page import js, NODE, PAGE, REC_JS

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
LIST = os.path.join(ROOT, 'runs', 'MPC_OBSCODES_NO_POSITION_2026-10-01.json')
# the 31 codes as read on 1 Oct 2026, 11:55:11 UTC (the list's sha256 005435f0...); the record above holds their names
NO_FIXED_POSITION = ('245', '247', '249', '250', '258', '270', '273', '274', '275', '288', '289', '311', '313', '314', '315',
                     '332', '335', '336', '338', '339', 'C49', 'C50', 'C51', 'C52', 'C53', 'C54', 'C55', 'C56', 'C57', 'C58', 'C59')
SOFTWARE = "domino-calibrator %s (zero-aperture position, through the image's own plate solution)" % __version__
TIME = '2025-12-12T21:21:02.00Z'


def record_row(psv):
    """The data record's fields, by the keyword record's names."""
    lines = [l for l in psv.splitlines() if l.strip() and not l.startswith(('#', '!'))]
    return dict(zip([s.strip() for s in lines[0].split('|')], [s.strip() for s in lines[1].split('|')]))


def sig_figs(s):
    """The significant figures of a positive decimal as written: leading zeros never count; trailing zeros count after a
    decimal point and not before one."""
    digits = s.replace('.', '').lstrip('0')
    return len(digits if '.' in s else digits.rstrip('0') or '0')


def decimals(s):
    return len(s.split('.')[1]) if '.' in s else 0


def dp(sigma_arcsec):
    """ADES's DP = CEILING(1 - LOG10(SIGMA)), SIGMA in degrees, within the schema's 0-9."""
    return min(max(math.ceil(1.0 - math.log10(sigma_arcsec / 3600.0)), 0), 9)


def args(over):
    """REC_ARGS with some values replaced: {'--stn': '250'}."""
    a = list(REC_ARGS)
    for k, v in over.items():
        a[a.index(k) + 1] = v
    return a


def option_help(text, flag):
    """An option's own help in argparse's --help: its line and the indented lines that continue it, as one line. An option's
    line is argparse's, indented by exactly two spaces (amendment 1: the red run read the docstring's usage line, printed at
    the head of --help, instead)."""
    lines = text.splitlines()
    for i, line in enumerate(lines):
        if re.match(r'  ' + re.escape(flag) + r'(\s|,|$)', line):
            chunk = [line]
            for more in lines[i + 1:]:
                if re.match(r'\s+-', more) or not more.startswith('   '):
                    break
                chunk.append(more)
            return ' '.join(' '.join(chunk).split())
    return ''


def page_records(cases):
    """The page's engine on each case's record values: [{psv, notes} or {error}]."""
    return js('out = D.cases.map((c) => Z.adesPSV(Object.assign({ra: 168.7, dec: 4.6, time: %r}, D.rec, c)));' % TIME,
              {'cases': cases, 'rec': REC_JS})


class F1Base(Tmp):
    def judge(self, psv, label):
        if ADES_PYLIB and ADES_MASTER:
            ok, why = mpc_judge(psv[psv.index('# version='):], self.d)
            self.assertTrue(ok, '%s: %s' % (label, why))


class F1_1_Stations(F1Base):
    def test_the_list_is_the_record(self):
        rec = json.load(open(LIST, encoding='utf-8'))
        self.assertEqual(tuple(c['code'] for c in rec['no_fixed_position']), NO_FIXED_POSITION)
        self.assertEqual(tuple(A.NO_FIXED_POSITION), NO_FIXED_POSITION)           # the tool's own list
        self.assertEqual(tuple(js('out = Z.NO_FIXED_POSITION;')), NO_FIXED_POSITION)   # the page's

    def test_a_station_without_a_fixed_position_gets_no_record(self):
        for stn in NO_FIXED_POSITION:
            with self.subTest(face='python', stn=stn):
                with self.assertRaises(ValueError) as e:
                    A.ades_psv(168.7, 4.6, TIME, **dict(REC, stn=stn))
                self.assertIn("has no fixed position in the MPC's list", str(e.exception))
        for stn, r in zip(NO_FIXED_POSITION, page_records([{'stn': s} for s in NO_FIXED_POSITION])):
            with self.subTest(face='page', stn=stn):
                self.assertNotIn('psv', r); self.assertIn("has no fixed position in the MPC's list", r.get('error', ''))
        img, _ = comet(); p = write(self.p('c.fits'), img)
        for stn in ('250', '247'):
            with self.subTest(face='command line', stn=stn):
                rc, out = run_main([p] + given(p) + args({'--stn': stn}))
                self.assertNotIn('# version=', out); self.assertIn("has no fixed position in the MPC's list", out)
                self.assertIn('# zero aperture:', out)                            # the pixel answer stands

    def test_control_a_fixed_station_still_gets_its_record(self):
        img, _ = comet(); p = write(self.p('c.fits'), img)
        rc, out = run_main([p] + given(p) + REC_ARGS)
        self.assertIn('# version=2022', out); self.judge(out, 'stn 568')
        r, = page_records([{'stn': '568'}]); self.assertIn('psv', r, r)


class F1_2_RmsFigures(F1Base):
    CASES = [(0.01234, 0.0995), (1.234, 12.34), (0.000123, 0.5), (0.1449, 0.0151), (0.35, 0.0026)]

    def test_rms_at_two_significant_figures(self):
        for rra, rde in self.CASES:
            with self.subTest(rms=(rra, rde)):
                row = record_row(A.ades_psv(168.7, 4.6, TIME, rms_ra=rra, rms_dec=rde, **REC))
                for k, v in (('rmsRA', rra), ('rmsDec', rde)):
                    s = row[k]
                    self.assertEqual(sig_figs(s), 2, (k, s))                     # ADES: two if the lead is 1, else one or two
                    self.assertLessEqual(abs(float(s) - v), 0.5 * 10 ** (math.floor(math.log10(v)) - 1) * 1.000001, (k, s, v))

    def test_an_rms_that_two_figures_cannot_write_in_seven_characters_is_refused(self):
        with self.assertRaises(ValueError) as e:                                   # 0.000012 is 8 characters
            A.ades_psv(168.7, 4.6, TIME, rms_ra=0.0000123, rms_dec=0.5, **REC)
        self.assertIn('rmsRA', str(e.exception))

    def test_the_command_lines_scatter_at_two_figures_and_the_judge(self):
        img, _ = comet(); p = write(self.p('c.fits'), img)
        rc, out = run_main([p, '--rms-noise', '5'] + given(p) + REC_ARGS)
        self.assertIn('# version=2022', out, out[-400:])
        m = re.search(r'^# sky-noise scatter on the sky, [^:]*: RA\*cos\(Dec\) (\S+)", Dec (\S+)"', out, re.M)   # F11b: beside
        self.assertIsNotNone(m, out[-600:])                                                  # the record, not in it
        for v in m.groups():
            self.assertEqual(sig_figs(v), 2, v)
        self.judge(out, '--rms-noise 5')


class F1_3_Decimals(F1Base):
    CASES = [(0.2, 0.2, 4.6), (0.02, 0.03, 4.6), (2.0, 1.5, 4.6), (0.2, 0.2, 75.0), (0.00012, 0.0004, -30.0), (9.0, 40.0, 60.0)]

    def test_with_an_rms_the_decimals_follow_the_uncertainty(self):
        for rra, rde, dec in self.CASES:
            with self.subTest(rms=(rra, rde), dec=dec):
                row = record_row(A.ades_psv(168.7, dec, TIME, rms_ra=rra, rms_dec=rde, **REC))
                self.assertEqual(decimals(row['ra']), dp(float(row['rmsRA']) / math.cos(math.radians(dec))), row)
                self.assertEqual(decimals(row['dec']), dp(float(row['rmsDec'])), row)

    def test_without_an_rms_six_decimals_on_both_faces(self):
        for ra, dec in ((168.7, 4.6), (12.3456789, -45.6789012), (359.99999994, 89.99999999)):
            with self.subTest(face='python', ra=ra, dec=dec):
                row = record_row(A.ades_psv(ra, dec, TIME, **REC))
                self.assertEqual((decimals(row['ra']), decimals(row['dec'])), (6, 6), row)
        rows = js("out = D.pts.map((p) => Z.adesPSV(Object.assign({}, D.rec, {ra: p[0], dec: p[1], time: %r})).psv);" % TIME,
                  {'pts': [[168.7, 4.6], [12.3456789, -45.6789012]], 'rec': REC_JS})
        for psv in rows:
            with self.subTest(face='page'):
                row = record_row(psv)
                self.assertEqual((decimals(row['ra']), decimals(row['dec'])), (6, 6), row)

    def test_ra_wraps_at_its_written_decimals(self):
        want = {359.9999999: '0.000000', 359.9999994: '359.999999'}
        for ra, s in want.items():
            with self.subTest(face='python', ra=ra):
                self.assertEqual(record_row(A.ades_psv(ra, 4.6, TIME, **REC))['ra'], s)
        got = js("out = D.ras.map((r) => Z.adesPSV(Object.assign({}, D.rec, {ra: r, dec: 4.6, time: %r})).psv);" % TIME,
                 {'ras': list(want), 'rec': REC_JS})
        for (ra, s), psv in zip(want.items(), got):
            with self.subTest(face='page', ra=ra):
                self.assertEqual(record_row(psv)['ra'], s)

    def test_the_command_line_end_to_end_and_the_judge(self):
        img, _ = comet(); p = write(self.p('c.fits'), img)
        rc, out = run_main([p] + given(p) + REC_ARGS)
        row = record_row(out[out.index('# version='):])
        self.assertEqual((decimals(row['ra']), decimals(row['dec'])), (6, 6), row); self.judge(out, 'no rms')
        rc, out = run_main([p, '--rms-noise', '5'] + given(p) + REC_ARGS)
        row = record_row(out[out.index('# version='):])
        self.assertEqual((decimals(row['ra']), decimals(row['dec'])), (6, 6), row); self.judge(out, '--rms-noise 5')   # F11b: no rms in it


class F1_4_Names(unittest.TestCase):
    def test_the_page_asks_initials_then_surname(self):
        page = open(os.path.join(PAGE, 'index.html'), encoding='utf-8').read()
        self.assertNotRegex(page, r'(?i)surname,\s*initial')
        for fid in ('submitter', 'measurers', 'observers'):
            with self.subTest(field=fid):
                tag = re.search(r'<input[^>]*id="%s"[^>]*>' % fid, page)
                self.assertIsNotNone(tag, fid)
                hint = re.search(r'id="%s-hint">([^<]*)<' % fid, page)
                self.assertTrue(hint and re.search(r'(?i)initials,? then (the )?surname', hint.group(1)), (fid, hint and hint.group(1)))
                ph = re.search(r'placeholder="([^"]*)"', tag.group(0))
                if ph:                                                           # every example name is initials, then a surname
                    names = [n.strip() for n in re.sub(r'^(optional; )?e\.g\. ', '', ph.group(1)).split(';') if n.strip()]
                    for n in names:
                        self.assertRegex(n, r'^([A-Z]\. ?)+[A-Z][a-z]+$', (fid, ph.group(1)))

    def test_the_command_line_asks_initials_then_surname(self):
        import io, contextlib
        buf = io.StringIO()
        with contextlib.redirect_stdout(buf), self.assertRaises(SystemExit):
            cli.main(['--help'])
        for flag in ('--submitter', '--measurer', '--observer'):
            with self.subTest(flag=flag):
                h = option_help(buf.getvalue(), flag)
                self.assertRegex(h, r'(?i)initials,? then (the )?surname', (flag, h))


class F1_6_Software(F1Base):
    def test_the_record_names_the_software_after_the_telescope(self):
        img, _ = comet(); p = write(self.p('c.fits'), img)
        rc, out = run_main([p] + given(p) + REC_ARGS)
        psv = out[out.index('# version='):]
        r, = page_records([{}])
        self.assertLessEqual(len(SOFTWARE), 100)                                   # String100
        for face, text in (('command line', psv), ('page', r.get('psv', ''))):
            with self.subTest(face=face):
                lines = text.splitlines()
                self.assertIn('# software', lines, text[:600])
                k = lines.index('# software')
                self.assertEqual(lines[k + 1], '! astrometry ' + SOFTWARE)
                self.assertLess(lines.index('# telescope'), k)
        self.assertEqual(js('out = Z.VERSION;'), __version__)                      # the page's version is the package's
        self.judge(psv, 'the software block')


class F1_7_ControlCharacters(F1Base):
    FIELDS = {'submitter': 'submitter', 'measurers': 'measurers', 'observers': 'observers', 'observatory_name': 'observatoryName',
              'design': 'design', 'detector': 'detector'}
    BAD = ['A. N.\x07Observer', 'A. N. Observer\x1b[31m', 'A. N.\x7fObserver', 'A. N.\x85Observer', 'A. N.\x00Observer', 'A.\tN. Observer']

    def test_a_control_character_in_a_name_is_refused_on_both_faces(self):
        for field, jfield in self.FIELDS.items():
            for bad in self.BAD:
                with self.subTest(face='python', field=field, bad=bad):
                    v = [bad] if field in ('measurers', 'observers') else bad
                    with self.assertRaises(ValueError) as e:
                        A.ades_psv(168.7, 4.6, TIME, **dict(REC, **{field: v}))
                    self.assertIn('control character', str(e.exception))
            got = page_records([{jfield: bad} for bad in self.BAD])
            for bad, r in zip(self.BAD, got):
                with self.subTest(face='page', field=jfield, bad=bad):
                    self.assertNotIn('psv', r); self.assertIn('control character', r.get('error', ''))

    def test_bytes_that_are_not_utf8_are_refused(self):
        bad = 'A. N. Obs\udcffrver'                                              # argv's byte 0xff, as Python decodes it
        with self.assertRaises(ValueError) as e:
            A.ades_psv(168.7, 4.6, TIME, **dict(REC, submitter=bad))
        self.assertIn('not UTF-8', str(e.exception))
        r, = page_records([{'submitter': 'A. N. Obs\ud800rver'}])                  # a lone surrogate, the page's form of it
        self.assertNotIn('psv', r); self.assertIn('not UTF-8', r.get('error', ''))

    @unittest.skipIf(os.name == 'nt', 'POSIX argv carries raw bytes; Windows passes UTF-16')
    def test_the_command_line_with_raw_bytes_in_argv(self):
        img, _ = comet(); p = write(self.p('c.fits'), img)
        a = [x.encode() for x in args({'--submitter': 'X'})]
        a[a.index(b'X')] = b'A. N. Obs\xffrver'
        r = subprocess.run([sys.executable, '-m', 'domino_calibrator.cli', p.encode()] + [x.encode() for x in given(p)] + a, cwd=ROOT, capture_output=True,
                           env=dict(os.environ, PYTHONUTF8='1'))
        out = r.stdout.decode('utf-8', 'replace') + r.stderr.decode('utf-8', 'replace')
        self.assertNotIn('Traceback', out); self.assertNotIn('# version=', out); self.assertIn('not UTF-8', out)

    def test_control_printable_names_outside_ascii_still_pass(self):
        for name in ('A. N. Observer', 'Ł. Żółć', 'J.-P. Lévêque', 'Ö. Güneş'):
            with self.subTest(face='python', name=name):
                A.ades_psv(168.7, 4.6, TIME, **dict(REC, submitter=name, measurers=[name]))
        for name, r in zip(('Ł. Żółć', 'Ö. Güneş'), page_records([{'submitter': 'Ł. Żółć'}, {'submitter': 'Ö. Güneş'}])):
            with self.subTest(face='page', name=name):
                self.assertIn('psv', r, r)


class F1_8_AsciiDesignations(F1Base):
    BAD = ['３I', '٣I', '1Ｐ', 'C/2025 Ｎ1', 'C/2025 N١']

    def test_a_designation_outside_ascii_is_refused_on_both_faces(self):
        for d in self.BAD:
            with self.subTest(face='python', desig=d):
                with self.assertRaises(ValueError) as e:
                    A.ades_psv(168.7, 4.6, TIME, **dict(REC, desig=d))
                self.assertIn('outside ASCII', str(e.exception))
        for d, r in zip(self.BAD, page_records([{'desig': d} for d in self.BAD])):
            with self.subTest(face='page', desig=d):
                self.assertNotIn('psv', r); self.assertIn('outside ASCII', r.get('error', ''))

    def test_control_ascii_designations_still_pass(self):
        for d in ('3I', '1P', 'C/2025 N1', '2I', 'P/2019 LD2'):
            with self.subTest(desig=d):
                A.ades_psv(168.7, 4.6, TIME, **dict(REC, desig=d))
        for r in page_records([{'desig': d} for d in ('3I', '1P', 'C/2025 N1')]):
            self.assertIn('psv', r, r)


if __name__ == '__main__':
    unittest.main()
