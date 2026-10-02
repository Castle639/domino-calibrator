"""The fix room's F12: the second audit room's should-fixes that are words (1 Oct 2026, his yes to all 27, with his choices
for 21 and 22; the fix room's record of 1 Oct 2026, not in this repository, section 28). Written before the fix, to fail on the tool as
F11b left it, and to pass once it is fixed. By the report's numbers (11.2):
1 (F1.1)   Checking a record put ades-lib/ inside the checkout, where the suite reads every Python file.
3 (F1.3)   the cutout recipe took the image from HDU 0 and died on Hubble's frames (and most pipelines' extension images).
4 (F6.3)   a whole frame on the page: a click lands far from where it was meant, and the refusal names no cure.
5 (F3.2)   runs/h3_report.py could not run from the repository's root.
6 (F3.3)   "G was measured in 50 of the 130 cells" read as a finding about the tool, where it is the study's footprint.
11 (F7.2)  the CHANGELOG said draft and waited for the CI's first run.
20 (F9.2)  no word where people read first on the pixel scale and the seeing at which the method fails.
21 (F9.3)  the house idiom in the package's code and docstrings (his choice: plain words there, kept in runs/, explained).
22 (F9.4)  the disclosure (his choice: one line on the Castle, one that Domino Observatory is a project and not a station,
           the issues as the contact, the AI named as now).
24 (F9.6)  the data's credit, the method's citation, and "calibration" claiming more than the limits.
25 (F5.1)  the CHANGELOG's three estimators.
27 (F5.4)  the credit's variants in the package's own headers.
Items 23, 27's tools and archive lines, 12 and 13 live in files the Castle keeps as written: the public copy's curation
carries them, and the release bar checks them there.
"""
import io, os, re, ast, gzip, json, math, shutil, tempfile, subprocess, sys, tokenize, unittest, warnings

import numpy as np
from astropy.io import fits

from tests import test_release_words as W
from tests.test_hardening import comet, wcs_cards
from tests.test_hardening_page import NODE, PW, PAGE, fits_bytes
from tests.test_fix_f3 import readme, readme_prose, page_visible, flat, recipe, CREDIT_LINE, ISSUES

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CHANGELOG = os.path.join(ROOT, 'CHANGELOG.md')

# the house's references, as its records write them: rounds, audits, rooms, findings, items, commits, his words
REF = re.compile(r"\bround [0-9]\b|\bthe (?:second |first )?audit(?: room)?'s\b|\bthe audit room\b|\bthe fix room\b|"
                 r"\bthe (?:calibrator|hardening|launch|release) room\b|\brefuter pass\b|\bF[0-9]+\.[0-9]+\b|"
                 r"\bT[0-9]\.[0-9]+\b|\bitem [0-9]+\b|\(#[0-9]+|\b(?=[0-9a-f]*[a-f])(?=[0-9a-f]*[0-9])[0-9a-f]{7}\b|\bB[0-9]'?(?![\w])|"
                 r"\bhis (?:answer|choice|word|words|cure|rule|yes|call|key)\b")


def section(text, start, end):
    i = text.find(start)
    j = text.find(end, i + 1) if i >= 0 else -1
    return text[i:j] if i >= 0 and j > i else ''


def py_comments(path):
    """A Python file's comments and docstrings, each (line, text)."""
    src = open(path, encoding='utf-8').read()
    out = [(t.start[0], t.string) for t in tokenize.generate_tokens(io.StringIO(src).readline) if t.type == tokenize.COMMENT]
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)):
            d = ast.get_docstring(node, clean=False)
            if d:
                out.append((node.body[0].lineno, d))
    return out


def js_comments(path):
    """A JavaScript or HTML file's comments, each (line, text): // to the line's end outside quotes, /* */ and <!-- -->."""
    src = open(path, encoding='utf-8').read()
    out = []
    for m in re.finditer(r'/\*.*?\*/|<!--.*?-->', src, flags=re.S):
        out.append((src.count('\n', 0, m.start()) + 1, m.group(0)))
    for n, line in enumerate(src.splitlines(), 1):
        for m in re.finditer(r'(?:^|(?<=\s))//', line):
            before = line[:m.start()]
            if all(before.count(q) % 2 == 0 for q in ("'", '"', '`')):
                out.append((n, line[m.start():]))
                break
    return out


def package_comments():
    files = [os.path.join(ROOT, 'domino_calibrator', f) for f in sorted(os.listdir(os.path.join(ROOT, 'domino_calibrator')))
             if f.endswith('.py')]
    got = []
    for p in files:
        got += [(os.path.relpath(p, ROOT), n, t) for n, t in py_comments(p)]
    for p in (os.path.join(ROOT, 'page', 'zeroap.js'), os.path.join(ROOT, 'page', 'index.html')):
        got += [(os.path.relpath(p, ROOT), n, t) for n, t in js_comments(p)]
    return got


class F12_1_CheckingARecord(unittest.TestCase):
    def test_ades_lib_beside_the_checkout_not_inside_it(self):
        t = readme()
        self.assertIn('pip install --target ../ades-lib ../ades-master', t)
        self.assertIn('PYTHONPATH=../ades-lib', t)
        self.assertNotRegex(t, r'--target ades-lib\b')
        self.assertRegex(flat(t), r'beside (?:this|the) checkout, not inside it')


class F12_3_TheRecipeFindsTheImage(unittest.TestCase):
    def run_recipe(self, d, frame, x, y):
        code = recipe(W.read(os.path.join(ROOT, 'README.md')))
        code = code.replace("r'frame.fits'", repr(frame)).replace("r'cutout.fits'", repr(os.path.join(d, 'cutout.fits')))
        code = re.sub(r'^x, y = [^#\n]*', 'x, y = %r, %r ' % (x, y), code, flags=re.M)
        r = subprocess.run([sys.executable, '-c', 'import warnings; warnings.simplefilter("ignore")\n' + code], cwd=d,
                           capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
        return r

    def test_an_image_in_an_extension_with_its_time_in_the_primary(self):
        d = tempfile.mkdtemp()
        try:
            img, _ = comet(71)
            big = np.full((301, 401), 100.0); big[100:171, 200:271] = img
            h = wcs_cards(fits.Header(), n=301)
            ph = fits.Header(); ph['DATE-OBS'] = '2025-12-12T21:20:32.000'; ph['EXPTIME'] = 60.0
            frame = os.path.join(d, 'mef.fits')
            fits.HDUList([fits.PrimaryHDU(header=ph), fits.ImageHDU(big.astype(np.float32), header=h)]).writeto(frame)
            r = self.run_recipe(d, frame, 235.05, 134.95)
            self.assertEqual(r.returncode, 0, r.stderr[-600:])
            with fits.open(os.path.join(d, 'cutout.fits')) as f:
                self.assertEqual(f[0].data.shape, (101, 101))
                self.assertEqual(f[0].header['DATE-OBS'], '2025-12-12T21:20:32.000')
                self.assertEqual(f[0].header['EXPTIME'], 60.0)
                self.assertEqual(f[0].header['CTYPE1'], 'RA---TAN')
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_hubbles_own_frame(self):
        frames = [os.path.join(b, 'data', 'hst-3i', 'ifle03geq_flc.fits') for b in (ROOT, os.path.dirname(ROOT))]
        frame = next((p for p in frames if os.path.exists(p)), None)
        if frame is None:
            self.skipTest("Hubble's frame ifle03geq_flc.fits is not here (python tools/fetch_frames.py 03)")
        d = tempfile.mkdtemp()
        try:
            r = self.run_recipe(d, frame, 1000.0, 1000.0)
            self.assertEqual(r.returncode, 0, r.stderr[-600:])
            with fits.open(os.path.join(d, 'cutout.fits')) as f:
                self.assertEqual(f[0].data.shape, (101, 101))
                self.assertIn('DATE-OBS', f[0].header)
                self.assertIn('EXPTIME', f[0].header)
                self.assertTrue(f[0].header['CTYPE1'].startswith('RA---TAN'))
        finally:
            shutil.rmtree(d, ignore_errors=True)


@unittest.skipIf(NODE is None or PW is None, 'no node or no playwright')
class F12_4_AWholeFrameOnThePage(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore')
        cls.d = tempfile.mkdtemp()
        rng = np.random.default_rng(5)
        big = rng.normal(100.0, 5.0, (1600, 2000))
        img, _ = comet(71)
        big[765:836, 965:1036] += img - 100.0                        # the comet near (1000, 800)
        wcs = dict(CTYPE1='RA---TAN', CTYPE2='DEC--TAN', CRPIX1=1000.0, CRPIX2=800.0, CRVAL1=168.7, CRVAL2=4.6, CD1_1=-2.1e-4,
                   CD1_2=0.0, CD2_1=0.0, CD2_2=2.1e-4)
        frame = fits_bytes(os.path.join(cls.d, 'frame.fits'), big.astype(np.float32),
                           **dict(wcs, **{'DATE-OBS': '2025-12-27T16:04:29.000', 'EXPTIME': 120.0}))
        from tests.test_hardening_page import REC_PAGE
        cases = [dict(name='sky', steps=[dict(file=frame, x=300, y=300, set=dict(REC_PAGE), run=True)])]
        cp = os.path.join(cls.d, 'cases.json'); json.dump(cases, open(cp, 'w', encoding='utf-8'))
        r = subprocess.run([NODE, os.path.join(PAGE, 'browser_cases.js'), cp], capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=300, env=dict(os.environ, PLAYWRIGHT_MODULE=PW))
        cls.err = r.stderr[-800:]
        try:
            cls.res = {c['name']: c for c in json.loads(r.stdout)}
        except Exception:
            cls.res = None

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def test_the_page_says_how_far_a_click_lands_and_what_to_do(self):
        self.assertIsNotNone(self.res, 'browser_cases.js gave no result: ' + self.err)
        s = self.res['sky']['steps'][-1]
        self.assertIn('shown at 1:5', s['info'])
        self.assertIn('a click lands within about 5 px', s['info'])
        self.assertNotIn('version=2022', s['ades'])
        self.assertIn('type x and y on the comet', s['ades'])
        self.assertIn('cut out the comet first', s['ades'])


# The study's summary, compared across machines: a float's last digits can differ where numpy takes another machine's
# arithmetic paths (GitHub's runners, 2 Oct 2026: up to 2.1e-15 relative; numpy here without AVX-512: up to 8.9e-16
# relative, 5.7e-14 absolute). Each float is held to 1e-9 relative plus 1e-12 absolute; every other value, every key and
# every length must be equal. An infinity or a NaN matches only itself.
REL, ABS = 1e-9, 1e-12


def summary_differences(got, want, path=''):
    """The places where got and want differ beyond the tolerance, as (path, got, want)."""
    if isinstance(want, dict) or isinstance(got, dict):
        if not (isinstance(got, dict) and isinstance(want, dict)) or got.keys() != want.keys():
            return [(path, got, want)]
        return [d for k in want for d in summary_differences(got[k], want[k], path + '/' + k)]
    if isinstance(want, list) or isinstance(got, list):
        if not (isinstance(got, list) and isinstance(want, list)) or len(got) != len(want):
            return [(path, got, want)]
        return [d for i, (g, w) in enumerate(zip(got, want)) for d in summary_differences(g, w, '%s[%d]' % (path, i))]
    if isinstance(want, float) and isinstance(got, float):
        if got == want or (got != got and want != want):
            return []
        if not (math.isfinite(got) and math.isfinite(want)) or abs(got - want) > REL * max(abs(got), abs(want)) + ABS:
            return [(path, got, want)]
        return []
    return [] if type(got) is type(want) and got == want else [(path, got, want)]


class F12_5_TheStudysReportFromTheRoot(unittest.TestCase):
    def test_h3_report_runs_from_a_public_checkout(self):
        horizons = next((p for p in (os.path.join(b, 'data', 'hst-3i', 'horizons', '3I_from_HST_psang_2026-09-27.txt')
                                     for b in (ROOT, os.path.dirname(ROOT))) if os.path.exists(p)), None)
        self.assertIsNotNone(horizons, "H0's Horizons rows are not here")
        d = tempfile.mkdtemp()
        try:
            os.makedirs(os.path.join(d, 'runs')); os.makedirs(os.path.join(d, 'data', 'hst-3i', 'horizons'))
            for f in ('h3_report.py', 'H3_RAW_2026-09-27.json.gz', 'H0_FRAMES_2026-09-27.json'):
                shutil.copy(os.path.join(ROOT, 'runs', f), os.path.join(d, 'runs', f))
            shutil.copy(horizons, os.path.join(d, 'data', 'hst-3i', 'horizons'))
            r = subprocess.run([sys.executable, os.path.join('runs', 'h3_report.py'), 'report.txt'], cwd=d, capture_output=True,
                               text=True, encoding='utf-8', errors='replace', timeout=600)
            self.assertEqual(r.returncode, 0, r.stderr[-600:])
            got = json.load(open(os.path.join(d, 'runs', 'H3_SUMMARY_2026-09-27.json'), encoding='utf-8'))
            want = json.load(open(os.path.join(ROOT, 'runs', 'H3_SUMMARY_2026-09-27.json'), encoding='utf-8'))
            bad = summary_differences(got, want)
            self.assertEqual(bad, [], '%d values differ beyond the tolerance; the first: %r' % (len(bad), bad[:3]))
        finally:
            shutil.rmtree(d, ignore_errors=True)


class F12_6_TheFootprint(unittest.TestCase):
    def test_the_annulus_count_says_it_is_the_studys_footprint(self):
        line = next((ln for ln in readme_prose().splitlines() if 'G was measured in 50 of the 130 cells' in ln), '')
        self.assertTrue(line)
        self.assertRegex(line, r"the study's footprint")
        self.assertRegex(line, r'not a finding about the tool')


class F12_11_25_TheChangelog(unittest.TestCase):
    def test_no_draft_and_no_wait_for_the_first_run(self):
        t = flat(W.read(CHANGELOG))
        for gone in ('a draft, not released', 'still to come', "To be finished after the CI's first run"):
            with self.subTest(gone):
                self.assertNotIn(gone, t)

    def test_the_estimators_as_the_package_has_them(self):
        t = flat(W.read(CHANGELOG))
        self.assertNotIn('Three estimators', t)
        self.assertRegex(t, r"G, the symmetric fit, the command line's and the page's default")
        self.assertRegex(t, r"`shrink\(\)`[^.]*defaults to M")
        self.assertRegex(t, r'P, the brightness peak[^.]*not offered for the line')


class F12_20_WhereItFails(unittest.TestCase):
    def test_the_use_section_names_the_pixel_scale_and_the_seeing(self):
        use = flat(section(readme(), '## Use', '## The estimators'))
        self.assertRegex(use, r'pixel scale and (?:your )?seeing')
        self.assertRegex(use, r'fails in 42 of 45 cells at ≥ 2″ seeing and ≥ 1\.0″/px')   # amendment 2: with its tally, as W1.1 asks


class F12_21_PlainWords(unittest.TestCase):
    def test_the_packages_comments_and_docstrings_name_no_house_reference(self):
        bad = [(f, n, m.group(0)) for f, n, t in package_comments() for m in REF.finditer(t)]
        self.assertEqual(bad, [], '%d references, the first: %s' % (len(bad), bad[:12]))

    def test_runs_readme_explains_the_records_idiom(self):
        t = flat(W.read(os.path.join(ROOT, 'runs', 'README.md')))
        part = section(t, '**How these records speak**', '**The study**') or section(t, '**How these records speak**', '**The checks**')
        self.assertTrue(part, 'no paragraph on how the records speak')
        for w in ('round', 'room', 'bar', 'refuter', 'his '):
            with self.subTest(w):
                self.assertIn(w, part)


class F12_22_WhoMadeIt(unittest.TestCase):
    def test_the_castle_the_project_the_contact_and_the_ai(self):
        t = flat(section(readme(), '## Who made it', '\n## ') or readme()[readme().find('## Who made it'):])
        self.assertRegex(t, r'The Castle is ')
        self.assertIn('Domino Observatory is a project, not an observing station', t)
        self.assertIn(ISSUES, t)
        self.assertIn(CREDIT_LINE, t)


class F12_24_Credits(unittest.TestCase):
    def test_the_data_and_the_method_are_credited(self):
        t = flat(readme())
        for what in ('programme 18152', 'Man-To Hui', 'STScI', 'MAST', 'NAS 5-26555',
                     'High precision comet trajectory estimates', '10.1016/j.icarus.2015.10.035', 'Tholen & Chesley 2004'):
            with self.subTest(what):
                self.assertIn(what, t)
        self.assertIn('programme 18152', page_visible())

    def test_calibration_claims_no_more_than_the_limits(self):
        faces = {'README.md': flat(readme()), 'CHANGELOG.md': flat(W.read(CHANGELOG)),
                 'CITATION.cff': flat(W.read(os.path.join(ROOT, 'CITATION.cff'))),
                 'pyproject.toml': flat(W.read(os.path.join(ROOT, 'pyproject.toml')))}
        for face, t in faces.items():
            with self.subTest(face):
                self.assertNotRegex(t, r'\bcalibrat(?:ed|ion)\b')


class F12_27_OneCredit(unittest.TestCase):
    def test_no_signed_header_in_the_package_or_the_page(self):
        for p in [os.path.join(ROOT, 'domino_calibrator', f) for f in os.listdir(os.path.join(ROOT, 'domino_calibrator'))
                  if f.endswith('.py')] + [os.path.join(ROOT, 'page', 'zeroap.js'), os.path.join(ROOT, 'page', 'index.html')]:
            with self.subTest(os.path.relpath(p, ROOT)):
                self.assertNotRegex(W.read(p), r'Castle, 27 Sept 2026')


if __name__ == '__main__':
    unittest.main()
