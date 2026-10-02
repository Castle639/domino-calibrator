"""The fix room's F3: the words (1 Oct 2026; the fix room's record of 1 Oct 2026, not in this repository). Written before the fix, to fail
on the words as F2 left them (102ba50), and to pass once they are fixed. The launch room's should-fixes, as it numbered them,
with his answers (the launch room's report, section 11; this room's section 4):

his 4  The README's words for the new rule, in the README and on the page, as he wrote them.
his 1  The exit codes said in the README.
13  A whole frame's time and memory stated, from a measurement on record, and a cutout suggested.
15  The tests' judge helper tells "the validator is not importable" from "the MPC refused".
16  How to get the MPC's validator and Playwright, and how to check a record.
17  python -m tests.strict --may-skip documented, with the CI's own values.
20  No undefined jargon: no "its stars" or "two stars"; "refuter" defined once in the README.
21  The CHANGELOG up to date with this round, and tested like the README: every number registered and true.
23  A cutout recipe in the README and on the page, that works; the page's 25 Mpx limit stated.
24  The arcsec radii: "PARTIAL, by the letter", and the cells that could not be measured counted.
25  H4's tallies come from one frame per visit, said beside them.
26  "Helps" with its low-signal limit: at SNR 20 the zero-aperture position is further from HST's photocentre than the r = 2 px
    one in 9 of those 20 cells (the summaries' rms0_20 and rms2_20).
28  The page's comparison states G's own 45 of the 130 cells.
29  "The same engine" is "the same method, ported and checked against the Python".
30  CITATION.cff's author is Domino Observatory, the credit in its message, the contact the repository's issues; every field
    that names authors says Domino Observatory alone (his answer 5), pyproject.toml's too; no person's name.
40  The placeholders readable (4.5:1, in the page's Chromium clause) and every format example in a visible hint.
3, 5  The README's rms words follow F1 and F2: the noise from the comet's own sky ring, and after the plate error is added,
    two figures and ADES's decimals.
"""
import os, re, sys, json, math, shutil, tempfile, subprocess, unittest, warnings
import numpy as np

import domino_calibrator
from domino_calibrator import cli
from tests import test_release_words as W
from tests.test_hardening import mpc_judge, ADES_PYLIB, ADES_MASTER, REC_ARGS, comet, write, wcs_cards, given
from tests.test_release_package import citation, pyproject

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
RULE = ("The tool writes an ADES record only from a start you give, on the comet, and only when its checks pass: a sound sky "     # F10 (his word, 1 Oct 2026, night)
        "solution, every radius converged, and a bright, unclipped peak of more than one pixel well above the sky; a star or a "
        "galaxy can pass these checks too, so telling a comet from a star is yours. Otherwise it says why, and the pixel answer stands.")
CREDIT_LINE = "Built by Annie, the Castle's AI."
ISSUES = 'https://github.com/Castle639/domino-calibrator/issues'
WHOLE = os.path.join(ROOT, 'runs', 'FIX_F3_WHOLE_FRAME_2026-10-01.txt')


def readme():
    return W.norm(W.read(os.path.join(ROOT, 'README.md')))


def readme_prose():
    return W.norm(W.readme_text())


def page_visible():
    return re.sub(r'\s+', ' ', W.visible(W.page_html()))


def flat(t):
    return re.sub(r'\s+', ' ', t)


class F3_Rule(unittest.TestCase):
    def test_his_words_in_the_readme_and_on_the_page(self):
        self.assertIn(RULE, flat(readme_prose()))
        self.assertIn(RULE, page_visible())


class F3_ExitCodes(unittest.TestCase):
    def test_the_readme_says_the_three_codes(self):
        t = flat(readme_prose())
        for pat in (r'\b0 when the measurement passed its gates', r'\b2 when a gate refused', r'\b1 when it cannot measure at all'):
            with self.subTest(pat):
                self.assertRegex(t, pat)


class F3_13_WholeFrame(unittest.TestCase):
    def test_a_whole_frames_time_and_memory_from_the_record(self):
        self.assertTrue(os.path.exists(WHOLE), 'no measurement on record: runs/FIX_F3_WHOLE_FRAME_2026-10-01.txt')
        said = re.search(r'^README: (.+)$', W.read(WHOLE), re.M)
        self.assertIsNotNone(said, 'the record gives no README phrase')
        t = flat(readme_prose())
        self.assertIn(said.group(1).strip(), t)
        self.assertIn('runs/FIX_F3_WHOLE_FRAME_2026-10-01.txt', W.read(os.path.join(ROOT, 'README.md')))
        self.assertRegex(t, r'[Cc]ut out the comet')


class F3_15_Judge(unittest.TestCase):
    def test_a_validator_that_will_not_import_is_not_the_mpcs_refusal(self):
        import tests.test_hardening as H
        img, _ = comet()
        d = tempfile.mkdtemp()
        try:
            p = write(os.path.join(d, 'c.fits'), img)
            import io, contextlib
            buf = io.StringIO()
            with contextlib.redirect_stdout(buf), warnings.catch_warnings():
                warnings.simplefilter('ignore')
                cli.main([p] + given(p) + REC_ARGS)
            out = buf.getvalue()
            psv = out[out.index('# version='):]
            empty = os.path.join(d, 'empty_pylib'); os.makedirs(empty)
            saved = H.ADES_PYLIB
            H.ADES_PYLIB = empty
            try:
                ok, why = H.mpc_judge(psv, d)
            finally:
                H.ADES_PYLIB = saved
            self.assertFalse(ok)
            self.assertIn('not importable', why)
            self.assertNotIn('refused', why)
        finally:
            shutil.rmtree(d, ignore_errors=True)


class F3_16_CheckARecord(unittest.TestCase):
    def test_the_readme_says_where_the_validator_and_playwright_come_from(self):
        t = readme()
        for what, pat in (('the validator', r'IAU-ADES/ades-master'), ('its install', r'pip install --target'),
                          ('psvtoxml', r'python -m ades\.psvtoxml'), ('valsubmit', r'python -m ades\.valsubmit'),
                          ('its verdict', r'submit is OK'), ('Windows', r'PYTHONUTF8=1'),
                          ('Playwright', r'npm install playwright'), ('its browser', r'playwright install chromium'),
                          ('its folder', r'PLAYWRIGHT_MODULE')):
            with self.subTest(what):
                self.assertRegex(t, pat)


class F3_17_MaySkip(unittest.TestCase):
    def test_may_skip_documented_with_the_cis_own_values(self):
        t = readme()
        ci = W.read(os.path.join(ROOT, '.github', 'workflows', 'tests.yml'))
        values = sorted(set(re.findall(r'--may-skip (\S+?)(?=["\s])', ci)))
        self.assertTrue(values, 'the CI names no skips')
        for v in values:
            with self.subTest(value=v):
                self.assertIn('--may-skip %s' % v, t)
        self.assertRegex(t, r'--may-skip test_k6_')                                 # without a Python 3.11, the tested one
        self.assertRegex(flat(t), r'Debian or Ubuntu')


class F3_20_Jargon(unittest.TestCase):
    def test_no_stars_and_refuter_defined_once(self):
        faces = {'README.md': readme(), 'CHANGELOG.md': W.read(os.path.join(ROOT, 'CHANGELOG.md')),
                 'CITATION.cff': W.read(os.path.join(ROOT, 'CITATION.cff')), 'the page': page_visible()}
        for face, t in faces.items():
            with self.subTest(face):
                self.assertNotRegex(t, r'(?i)\b(its|two|one|three) stars?\b')
        t = flat(readme_prose())
        self.assertEqual(len(re.findall(r'[Aa] refuter is ', t)), 1, 'refuter defined once, as "A refuter is ..."')


class F3_21_Changelog(unittest.TestCase):
    def changelog(self):
        return W.read(os.path.join(ROOT, 'CHANGELOG.md'))

    def test_every_number_registered_and_true(self):
        t = W.norm(re.sub(r'```.*?```', '\n', self.changelog(), flags=re.S))
        ci = W.read(os.path.join(ROOT, '.github', 'workflows', 'tests.yml'))
        ci_pythons = set(re.findall(r'python(?:-version)?: "(\d\.\d+)"', ci))
        bad = [(tok, cl) for tok, cl in W.unregistered(t) if tok not in ci_pythons]
        self.assertEqual(bad, [])
        self.assertIn('## %s' % domino_calibrator.__version__, self.changelog())

    def test_it_names_this_rounds_changes(self):
        t = flat(self.changelog())
        for what, pat in (('the new rule', re.escape(RULE)), ('the exit codes', r'\b2 when a gate refused'),
                          ('the stations', r'no fixed position'), ('two figures', r'two significant figures'),
                          ('the decimals', r'decimals'), ('the software', r'# software'),
                          ('the sky ring', r'sky ring'), ('INHERIT', r'INHERIT'), ('ds9', r'0-based; add 1 for ds9'),
                          ('names', r'initials, then surname'), ('control characters', r'control character'),
                          ('the credit', re.escape(CREDIT_LINE))):
            with self.subTest(what):
                self.assertRegex(t, pat)


def recipe(text):
    """The cutout recipe: the code block that cuts with astropy's Cutout2D."""
    for b in re.findall(r'```(?:python)?\n(.*?)```', text, flags=re.S):
        if 'Cutout2D' in b:
            return b
    return None


class F3_23_Cutout(unittest.TestCase):
    def test_the_readme_and_the_page_give_the_recipe_and_the_limit(self):
        self.assertIsNotNone(recipe(W.read(os.path.join(ROOT, 'README.md'))), 'no recipe in the README')
        self.assertIn('Cutout2D', W.page_html())
        for face, t in (('README.md', flat(readme_prose())), ('the page', page_visible())):
            with self.subTest(face):
                self.assertRegex(t, r'25 Mpx')

    def test_the_recipe_works(self):
        code = recipe(W.read(os.path.join(ROOT, 'README.md')))
        self.assertIsNotNone(code, 'no recipe in the README')
        d = tempfile.mkdtemp()
        try:
            img, (xt, yt) = comet(71)
            big = np.full((301, 401), 100.0); big[100:171, 200:271] = img                 # the comet at (235.05, 134.95)
            from astropy.io import fits
            h = wcs_cards(fits.Header(), n=301); h['CTYPE1'] = 'RA---TAN-SIP'; h['CTYPE2'] = 'DEC--TAN-SIP'
            for k, v in (('A_ORDER', 2), ('A_2_0', 2e-6), ('A_0_2', -1e-6), ('B_ORDER', 2), ('B_1_1', 1.5e-6)):
                h[k] = v
            h['DATE-OBS'] = '2025-12-12T21:20:32.000'; h['EXPTIME'] = 60.0
            whole = os.path.join(d, 'frame.fits'); fits.PrimaryHDU(big.astype(np.float32), header=h).writeto(whole)
            ns = {}
            src = code.replace('frame.fits', whole).replace('cutout.fits', os.path.join(d, 'cutout.fits'))
            src = re.sub(r'\bx, y = .*', 'x, y = 235.05, 134.95', src)
            exec(compile(src, 'the README recipe', 'exec'), ns)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                rw = cli.measure_file(whole, x=235.05, y=134.95)
            cut = os.path.join(d, 'cutout.fits')
            with fits.open(cut) as f:
                ch = f[0].header
                self.assertEqual(ch.get('DATE-OBS'), '2025-12-12T21:20:32.000'); self.assertEqual(ch.get('EXPTIME'), 60.0)
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                # the comet in the cutout, wherever the recipe put the cutout's origin: the brightest pixel's 5 x 5 box
                ri, _, _ = cli.load_image(cut)
                sx, sy = cli._start(ri)
                rc = cli.measure_file(cut, x=sx, y=sy)
                rw = cli.measure_file(whole, x=rw['x0'], y=rw['y0'])
            self.assertIn('radec', rc, rc.get('sky_error')); self.assertIn('time', rc, rc.get('time_error'))
            dra = (rc['radec'][0] - rw['radec'][0]) * math.cos(math.radians(rw['radec'][1])) * 3600.0
            dde = (rc['radec'][1] - rw['radec'][1]) * 3600.0
            self.assertLess(math.hypot(dra, dde), 1e-3, (dra, dde))                      # the same sky position, within 1 mas
            self.assertEqual(rc['time'], rw['time'])
        finally:
            shutil.rmtree(d, ignore_errors=True)


class F3_24_26_Study(unittest.TestCase):
    def test_partial_by_the_letter_and_the_cells_not_measured(self):
        t = flat(readme_prose())
        self.assertRegex(t, r'PARTIAL, by the letter')
        keys = [k for _, k in W.VERDICTS]
        self.assertIn('nullfailed', keys, 'the grammar has no verdict for "not measurable"')
        self.assertEqual(W.recount('nullfailed', 'ARC', W.AMAT['see'], W.AMAT['pix'])[:2], (21, 45))
        found = [x for x in W.tallies(W.CODE.sub(' ', readme_prose())) if x['verdict'] == 'nullfailed' and x['variant'] == 'ARC']
        self.assertTrue(any((x['n'], x['m']) == (21, 45) for x in found), found)

    def test_h4s_tallies_say_one_frame_per_visit(self):
        for ln in readme_prose().splitlines():
            if re.search(r'on the sky|units of the seeing', ln) and W.TALLY.search(ln):
                with self.subTest(line=ln[:80]):
                    self.assertIn('one frame per visit', ln)

    def test_helps_carries_its_low_signal_limit(self):
        found = [x for x in W.tallies(W.CODE.sub(' ', readme_prose())) if x['verdict'] == 'worse20']
        self.assertTrue(any((x['n'], x['m'], x['see'], x['pix']) == (9, 20, W.PROF['see'], W.PROF['pix']) for x in found), found)
        line = next((ln for ln in readme_prose().splitlines() if 'helps in 20 of 20 cells' in ln), '')
        self.assertRegex(line, r'SNR 20')


class F3_28_PageComparison(unittest.TestCase):
    def test_the_page_states_gs_own_45_of_130(self):
        found = [x for x in W.tallies(W.CODE.sub(' ', W.norm(W.page_what_it_does())))
                 if (x['verdict'], x['variant'], x['n'], x['m']) == ('worse', 'PX', 45, 130)]
        self.assertTrue(found, 'not stated')


class F3_29_SameMethod(unittest.TestCase):
    def test_the_same_method_ported_and_checked(self):
        faces = {'README.md': flat(readme()), 'CHANGELOG.md': flat(W.read(os.path.join(ROOT, 'CHANGELOG.md'))),
                 'CITATION.cff': flat(W.read(os.path.join(ROOT, 'CITATION.cff'))), 'the page': page_visible()}
        for face, t in faces.items():
            with self.subTest(face):
                self.assertNotIn('same engine', t)
        for face in ('README.md', 'the page'):
            with self.subTest(face, what='the words'):
                self.assertIn('the same method, ported and checked against the Python', faces[face])


class F3_30_Credit(unittest.TestCase):
    def test_domino_observatory_wherever_authors_are_named(self):
        c = citation()
        self.assertEqual(c.get('authors'), [{'name': 'Domino Observatory'}])
        self.assertIn(CREDIT_LINE, c.get('message', ''))
        contact = c.get('contact') or []
        self.assertTrue(any(ISSUES in str(x.get('website', '')) for x in contact), contact)
        self.assertEqual(pyproject()['project'].get('authors'), [{'name': 'Domino Observatory'}])
        self.assertIn(ISSUES, readme())
        for face, t in (('README.md', readme()), ('CITATION.cff', W.read(os.path.join(ROOT, 'CITATION.cff')))):
            with self.subTest(face, what='no person named'):
                # F4 (the fix room): names are not spelled here, where the curation would rewrite them inside code; the
                # release bar's S3 scans the whole public folder for them, from its CHECKS. Here: no person's fields
                self.assertNotRegex(t, r'(?i)\b(?:given|family)-names\b')


class F3_40_Hints(unittest.TestCase):
    def test_every_placeholder_example_is_also_in_a_visible_hint(self):
        page = W.page_html()
        for m in re.finditer(r'<input[^>]*id="(\w+)"[^>]*placeholder="([^"]*)"[^>]*>', page):
            fid, ph = m.group(1), m.group(2)
            ex = re.sub(r'^(?:optional; )?(?:e\.g\. )?', '', ph)
            if ex in ('optional', 'from the header, or type it'):
                continue
            with self.subTest(field=fid, example=ex):
                hint = re.search(r'id="%s-hint">([^<]*)<' % fid, page)
                self.assertTrue(hint and ex in hint.group(1), (fid, hint and hint.group(1)))


class F3_3_5_RmsWords(unittest.TestCase):
    def test_the_readme_follows_the_record(self):
        t = flat(readme_prose())
        self.assertRegex(t, r"the comet's own sky ring, 12–24 px")
        self.assertNotRegex(t, r"image's own sky noise")
        self.assertRegex(t, r'two significant figures')
        self.assertRegex(flat(readme()), r'DP = CEILING\(1 [−-] LOG10\(SIGMA\)\)')


if __name__ == '__main__':
    unittest.main()
