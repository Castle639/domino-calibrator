"""The launch list's inside steps 4 and 5 (30 Sept 2026, the calibrator's build room; the build room's brief of 30 Sept 2026, not in this repository,
section 1; the launch steps' record of 29 Sept 2026, not in this repository).

Step 4, the repository's words, with its name and owner (his calls: domino-calibrator, under Castle639; [his words, not quoted in public]). K15: the README's clone line, before the install block; the test command,
from the checkout's root whatever it is called (the issue list's entry 4), with what its skips need named beside it (entry
40). K16: the page's two README mentions, links to the repository's README. K17: the repository's address in pyproject.toml
and CITATION.cff (entry 8's address; its comma in the authors' name and its date-released are not this step's). Written to
fail on the calibrator as step 3 left it.

Step 5, GitHub Pages' publishing workflow. GitHub serves a site from a branch's root, from its /docs folder, or through a
workflow (docs.github.com, "Configuring a publishing source for your GitHub Pages site", read 30 Sept 2026); the page is in
page/, so a workflow. K18 reads it: on a push to main or by hand, never a pull request; the token's three permissions and no
more; one deployment at a time; page/ uploaded as it is; the actions their newest majors, each on Node 24 (their action.yml,
read at source that morning: configure-pages v6, upload-pages-artifact v5 with upload-artifact v7 inside it, deploy-pages
v5; the docs' own examples declare node20, which left GitHub's runners on 23 Sept 2026). Written to fail before the file
exists. Its first run is his key (the launch list's step 10).
"""
import os, re, tomllib, unittest

import yaml

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)                             # the checkout's root, the folder that goes public
REPO = 'https://github.com/Castle639/domino-calibrator'
README_LINK = REPO + '#readme'
PAGES_ACTIONS = ['actions/checkout@v7', 'actions/configure-pages@v6', 'actions/upload-pages-artifact@v5', 'actions/deploy-pages@v5']


def read(*p):
    with open(os.path.join(PKG, *p), encoding='utf-8') as f:
        return f.read()


def section(t, head):
    """A README section's text, from its '## ' heading to the next."""
    m = re.search(r'^## %s\n(.*?)(?=^## |\Z)' % re.escape(head), t, flags=re.S | re.M)
    return m.group(1) if m else ''


def bullets(t):
    """A section's top-level bullets, each with its continuation."""
    return [b.strip() for b in re.split(r'^- ', t, flags=re.M)[1:]]


class TestRepositoryWords(unittest.TestCase):
    def test_k15_the_readme_says_where_the_repository_is_and_how_its_tests_run(self):
        r = read('README.md')
        inst = section(r, 'Install')
        fence = inst.find('```')
        with self.subTest('the clone line and the folder it makes, before the install block'):
            self.assertIn('`git clone %s`' % REPO, inst)
            self.assertIn('`cd domino-calibrator`', inst)
            if fence >= 0 and 'cd domino-calibrator' in inst:
                self.assertLess(inst.index('cd domino-calibrator'), fence)
        first = next((b for b in bullets(section(r, 'How it was tested')) if b.startswith('`tests/`')), '')
        with self.subTest("the test command, from the checkout's root whatever it is called (entry 4)"):
            self.assertIn('`python -m unittest discover -s tests -t .`', first)
            self.assertIn("from the checkout's root, whatever it is called", first)
        for n in ('`python tools/fetch_frames.py 22 03 04 05 06`', '`data/hst-3i/`', 'Node', 'Playwright', '`PLAYWRIGHT_MODULE`',
                  "the MPC's validator", '`ADES_PYLIB`', '`ADES_MASTER`', 'PyPI', '`python -m tests.strict`'):
            with self.subTest('beside the test command, what its skips need (entry 40)', names=n):
                self.assertIn(n, first)

    def test_k16_the_pages_readme_mentions_are_links_to_the_repositorys_readme(self):
        h = read('page', 'index.html')
        linked = re.findall(r'<a href="%s"><code>README\.md</code></a>' % re.escape(README_LINK), h)
        with self.subTest('two, each a link to the README on the repository'):
            self.assertEqual(len(linked), 2)
            self.assertEqual(len(re.findall(r'<code>README\.md</code>', h)), len(linked))
        with self.subTest('no other address outside the page: its links go to the repository alone'):
            outside = [a for a in re.findall(r'<a\b[^>]*\bhref="([^"]*)"', h) if '://' in a or a.startswith('//')]
            self.assertEqual(sorted(set(outside)), [README_LINK])

    def test_k17_the_repositorys_address_in_pyproject_and_citation(self):
        with open(os.path.join(PKG, 'pyproject.toml'), 'rb') as f:
            urls = tomllib.load(f).get('project', {}).get('urls', {})
        with self.subTest('pyproject.toml: the repository and its issues'):
            self.assertEqual(urls.get('Repository'), REPO)
            self.assertEqual(urls.get('Issues'), REPO + '/issues')
        c = yaml.safe_load(read('CITATION.cff')) or {}
        with self.subTest('CITATION.cff: repository-code'):
            self.assertEqual(c.get('repository-code'), REPO)


class TestPagesWorkflow(unittest.TestCase):
    def test_k18_github_pages_publishes_page_on_a_push_to_main(self):
        p = os.path.join(PKG, '.github', 'workflows', 'pages.yml')
        with self.subTest('present, beside the tests workflow'):
            self.assertTrue(os.path.exists(p), 'no .github/workflows/pages.yml')
        if not os.path.exists(p):
            return
        w = yaml.safe_load(read('.github', 'workflows', 'pages.yml')) or {}
        on = w.get('on', w.get(True)) or {}                 # PyYAML reads the key `on` as YAML 1.1's true
        with self.subTest('on a push to main, or by hand; never a pull request'):
            self.assertEqual(sorted(on), ['push', 'workflow_dispatch'])
            self.assertEqual((on.get('push') or {}).get('branches'), ['main'])
        with self.subTest("its token: read the contents, write the page, an id token; nothing more"):
            self.assertEqual(w.get('permissions'), {'contents': 'read', 'pages': 'write', 'id-token': 'write'})
        with self.subTest('one deployment at a time, a running one let finish'):
            self.assertEqual(w.get('concurrency'), {'group': 'pages', 'cancel-in-progress': False})
        jobs = w.get('jobs') or {}
        j = jobs.get('deploy') or {}
        with self.subTest('one job, on Ubuntu 24.04, with a time cap, in the github-pages environment'):
            self.assertEqual(list(jobs), ['deploy'])
            self.assertEqual(j.get('runs-on'), 'ubuntu-24.04')
            self.assertIsInstance(j.get('timeout-minutes'), int)
            self.assertEqual(j.get('environment'), {'name': 'github-pages', 'url': '${{ steps.deployment.outputs.page_url }}'})
        steps = j.get('steps') or []
        with self.subTest('the four actions, their newest majors on Node 24, and nothing else'):
            self.assertEqual(['%s@v%s' % m for m in re.findall(r'uses: ([\w./-]+)@[0-9a-f]{40}  # v(\d+)\.\d+\.\d+',   # F13: by SHA,
                                                                 read('.github', 'workflows', 'pages.yml'))], PAGES_ACTIONS)   # the release beside
            self.assertEqual([s for s in steps if 'run' in s], [])
        with self.subTest('it uploads page/, and its deploy step is the one the environment names'):
            self.assertEqual([(s.get('with') or {}).get('path') for s in steps if str(s.get('uses', '')).startswith('actions/upload-pages-artifact@')], ['page'])
            self.assertEqual([s.get('id') for s in steps if str(s.get('uses', '')).startswith('actions/deploy-pages@')], ['deployment'])


if __name__ == '__main__':
    unittest.main()


# ---------------------------------------------------------------- the CI's first run (the launch list's step 9, 30 Sept 2026)
# The first run on GitHub (Castle639/domino-calibrator at 934ca629) was green on Linux and macOS and red on Windows, 4 of 229:
# a path's backslashes doubled in the curve's failure line; text read in Windows' code page, twice (Node's output, the MPC's
# validator); and git's line endings on checkout, which changed the fonts' licence. K19-K21 hold the fixes on any system.
import ast, subprocess, sys, tempfile, shutil


class TestCurvePath(unittest.TestCase):
    def test_k19_the_curves_failure_names_the_path_as_given(self):
        from tests.test_hardening import comet, write, run_main, REC_ARGS, given
        from tests.test_hardening_2 import lines_starting
        d = tempfile.mkdtemp()
        try:
            img, _ = comet()
            p = write(os.path.join(d, 'c.fits'), img)
            odd = 'no such\\folder' if os.sep == '/' else 'no such folder'     # a backslash in a name, where one can be
            bad = os.path.join(d, odd, 'curve.csv')
            rc, out = run_main([p, '--curve', bad] + given(p) + REC_ARGS)
            self.assertEqual(rc, 0)
            self.assertTrue(out.strip().split('\n')[-2].startswith('permID'))   # the record still comes last
            self.assertTrue(any('curve' in ln and ln.rstrip().endswith(bad) for ln in lines_starting(out, '#')), out[-600:])
        finally:
            shutil.rmtree(d, ignore_errors=True)


SUBPROCESS_TEXT = {'run', 'check_output', 'Popen', 'call', 'check_call'}


def encoding_omissions(paths):
    """Each text-mode open() and each subprocess call reading text, with no encoding named: (file, line, what)."""
    found = []
    for f in paths:
        tree = ast.parse(open(f, encoding='utf-8').read(), f)
        for n in ast.walk(tree):
            if not isinstance(n, ast.Call):
                continue
            kw = {k.arg: k.value for k in n.keywords if k.arg}
            fn = n.func
            name = fn.id if isinstance(fn, ast.Name) else fn.attr if isinstance(fn, ast.Attribute) else ''
            owner = fn.value.id if isinstance(fn, ast.Attribute) and isinstance(fn.value, ast.Name) else ''
            if name == 'open' and owner in ('', 'io', 'builtins'):
                mode = n.args[1] if len(n.args) > 1 else kw.get('mode')
                text = not (isinstance(mode, ast.Constant) and isinstance(mode.value, str) and 'b' in mode.value)
                if text and 'encoding' not in kw:
                    found.append((f, n.lineno, 'open'))
            elif name in ('read_text', 'write_text') and 'encoding' not in kw:
                found.append((f, n.lineno, name))
            elif name in SUBPROCESS_TEXT and owner == 'subprocess':
                t = kw.get('text', kw.get('universal_newlines'))
                if isinstance(t, ast.Constant) and t.value is True and 'encoding' not in kw:
                    found.append((f, n.lineno, 'subprocess.' + name))
    return sorted(found)                                   # in source order (ast.walk is breadth-first)


class TestTextNamesItsEncoding(unittest.TestCase):
    def test_k20_every_text_open_and_text_subprocess_names_its_encoding(self):
        paths = [os.path.join(PKG, d, f) for d in ('domino_calibrator', 'tests')
                 for f in sorted(os.listdir(os.path.join(PKG, d))) if f.endswith('.py')]
        with self.subTest('control: a planted omission of each kind is found'):
            t = tempfile.mkdtemp()
            try:
                plant = os.path.join(t, 'plant.py')
                open(plant, 'w', encoding='utf-8').write(
                    "import subprocess, pathlib\nopen('x').read()\nopen('x', 'w')\npathlib.Path('x').read_text()\n"
                    "subprocess.run(['a'], text=True)\nopen('x', 'rb')\nopen('x', encoding='utf-8')\n")
                self.assertEqual([w for _, _, w in encoding_omissions([plant])], ['open', 'open', 'read_text', 'subprocess.run'])
            finally:
                shutil.rmtree(t, ignore_errors=True)
        self.assertEqual(encoding_omissions(paths), [])


class TestReleaseNotes(unittest.TestCase):
    def test_k25_the_notes_tell_windows_users_of_the_validator_about_utf8_mode(self):
        # the CI's first run (30 Sept 2026): the MPC's validator read our UTF-8 record in the Windows code page and stopped
        t = ' '.join(read('CHANGELOG.md').split())
        self.assertIn('PYTHONUTF8=1', t)
        m = re.search(r'[^.]*PYTHONUTF8=1[^.]*', t)
        self.assertTrue(m and 'Windows' in t[max(0, m.start() - 400):m.end()] and 'validator' in t[max(0, m.start() - 400):m.end()], t[-600:])


class TestTheCheckoutIsTheCommit(unittest.TestCase):
    def test_k21_git_converts_no_file(self):
        p = os.path.join(PKG, '.gitattributes')
        self.assertTrue(os.path.exists(p), 'no .gitattributes: a Windows checkout rewrites line endings')
        lines = [l.strip() for l in open(p, encoding='utf-8') if l.strip() and not l.startswith('#')]
        self.assertEqual(lines, ['* -text'])
