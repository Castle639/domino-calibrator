"""The fix room's F4: the public tree (1 Oct 2026; the fix room's record of 1 Oct 2026, not in this repository). Written before the fix, to
fail on the folder as F3 left it (c2083e8) and to pass once it is fixed. The launch room's should-fixes, as it numbered them,
with his answers (the launch room's report, section 11; this room's section 4), those the suite can check on calibrator/ itself:

32  The sdist's contents set explicitly: the package and its documents, and no fragment of tests/.
33  On PyPI, the README's logo and the files it names: the logo at absolute URLs (PyPI's sanitizer keeps the <img> and drops
    the <source>), and the repository named as where the files are.
35  The publishing workflow, by Trusted Publishing (his answer 3): a release and a manual run its only triggers, `id-token:
    write` only in the jobs that publish, each in its environment, the build in a job of its own; TestPyPI by hand, PyPI on a
    release, and nothing run until his keys at steps 12 and 13.
36  runs/ kept, with a short README inside that names every family of files in it.

The curation's items (18, 22, 27, 34) are checked on the built folder, by runs/fix_f4_bar.py.
"""
import os, re, sys, shutil, fnmatch, tarfile, tempfile, subprocess, unittest

from tests.test_release_package import pypi_unreachable, venv_program

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO_URL = 'https://github.com/Castle639/domino-calibrator'
RAW = 'https://raw.githubusercontent.com/Castle639/domino-calibrator/main/'
MODULES = ('__init__', 'ades', 'apertures', 'cli', 'degrade', 'estimators', 'hst', 'shrink', 'synth')
SDIST = ({'CHANGELOG.md', 'CITATION.cff', 'LICENSE', 'MANIFEST.in', 'PKG-INFO', 'README.md', 'pyproject.toml', 'setup.cfg'}
         | {'domino_calibrator/%s.py' % m for m in MODULES}
         | {'domino_calibrator.egg-info/' + f for f in ('PKG-INFO', 'SOURCES.txt', 'dependency_links.txt', 'entry_points.txt',
                                                       'requires.txt', 'top_level.txt')})


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def sdist_files(src, tmp):
    """The sdist's files, built from `src` with setuptools as pyproject.toml asks (>= 77) in a fresh environment: (files, log)."""
    venv = os.path.join(tmp, 'venv')
    c = subprocess.run([sys.executable, '-m', 'venv', '--clear', venv], capture_output=True, text=True, encoding='utf-8', errors='replace')
    if c.returncode != 0:
        return None, c.stdout + c.stderr
    py = venv_program(venv, 'python')
    c = subprocess.run([py, '-m', 'pip', 'install', '--disable-pip-version-check', '-q', 'setuptools>=77'], capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=900)
    if c.returncode != 0:
        return None, c.stdout + c.stderr
    out = os.path.join(tmp, 'dist')
    c = subprocess.run([py, '-c', 'import sys; from setuptools import build_meta as b; print(b.build_sdist(sys.argv[1]))', out],
                       cwd=src, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
    if c.returncode != 0:
        return None, c.stdout + c.stderr
    name = c.stdout.strip().splitlines()[-1]
    with tarfile.open(os.path.join(out, name)) as t:
        return sorted(m.name.split('/', 1)[1] for m in t.getmembers() if m.isfile()), c.stdout + c.stderr


class F4_32_Sdist(unittest.TestCase):
    def test_the_sdist_holds_the_package_and_its_documents_only(self):
        offline = pypi_unreachable()
        if offline:
            self.skipTest(offline)
        tmp = tempfile.mkdtemp(prefix='sdist_')
        try:
            src = os.path.join(tmp, 'src', 'checkout')
            shutil.copytree(ROOT, src, ignore=shutil.ignore_patterns('__pycache__', '*.egg-info', 'build', 'dist'))
            files, log = sdist_files(src, tmp)
            self.assertIsNotNone(files, log[-600:])
            with self.subTest('no fragment of tests/, runs/ or page/'):
                self.assertEqual([f for f in files if f.split('/')[0] in ('tests', 'runs', 'page', '.github')], [])
            with self.subTest('exactly the package, its documents and the metadata setuptools writes'):
                self.assertEqual(set(files), SDIST)
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


def readme_head():
    r = read(os.path.join(ROOT, 'README.md'))
    return r[:r.index('\n## ')] if '\n## ' in r else r


class F4_33_PyPI(unittest.TestCase):
    def test_the_logo_at_absolute_urls_each_a_file_of_the_folder(self):
        r = re.sub(r'```.*?```', ' ', read(os.path.join(ROOT, 'README.md')), flags=re.S)
        refs = re.findall(r'\b(?:src|srcset)="([^"]*)"', r) + re.findall(r'!\[[^\]]*\]\(([^)\s]+)', r)
        self.assertTrue(refs, 'no image in the README')
        for u in refs:
            with self.subTest(image=u):
                self.assertTrue(u.startswith(RAW), 'not an absolute URL into the repository: %s' % u)
                self.assertTrue(os.path.isfile(os.path.join(ROOT, u[len(RAW):])), 'no such file in the folder: %s' % u[len(RAW):])

    def test_no_relative_link(self):
        r = re.sub(r'```.*?```', ' ', read(os.path.join(ROOT, 'README.md')), flags=re.S)
        links = re.findall(r'(?<!!)\[[^\]]*\]\(([^)\s]+)', r) + re.findall(r'<a\b[^>]*\bhref="([^"]*)"', r)
        self.assertEqual([u for u in links if not u.startswith('https://')], [])

    def test_the_repository_named_where_the_files_are(self):
        self.assertRegex(' '.join(readme_head().split()),
                         r'files[^.]*\bare in (?:its|the) repository, %s\b' % re.escape(REPO_URL))


def jobs(text):
    """A workflow's jobs, as {name: its block}, read as the file is written (two-space indents)."""
    m = re.search(r'^jobs:\n(.*)', text, flags=re.S | re.M)
    out, name = {}, None
    for ln in (m.group(1) if m else '').splitlines():
        h = re.match(r'^  ([\w-]+):\s*$', ln)
        if h:
            name = h.group(1); out[name] = ''
        elif name:
            out[name] += ln + '\n'
    return out


def top(text):
    """The workflow's text before its jobs."""
    return text[:text.index('\njobs:')] if '\njobs:' in text else text


class F4_35_Publish(unittest.TestCase):
    PATH = os.path.join(ROOT, '.github', 'workflows', 'publish.yml')

    def wf(self):
        self.assertTrue(os.path.exists(self.PATH), 'no .github/workflows/publish.yml')
        return read(self.PATH)

    def test_triggers_a_release_and_a_manual_run_only(self):
        t = top(self.wf())
        on = re.search(r'^on:\n((?:  .*\n)+)', t, flags=re.M)
        self.assertIsNotNone(on, 'no on: block')
        events = re.findall(r'^  ([\w-]+):', on.group(1), flags=re.M)
        self.assertEqual(sorted(events), ['release', 'workflow_dispatch'])
        self.assertRegex(on.group(1), r'release:\n    types: \[published\]')

    def test_least_permissions_id_token_only_where_it_publishes(self):
        w = self.wf()
        self.assertRegex(top(w), r'(?m)^permissions:\n  contents: read\n', 'the workflow\'s own permissions: contents: read only')
        self.assertNotIn('id-token', top(w))
        js = jobs(w)
        pub = {n: b for n, b in js.items() if 'pypa/gh-action-pypi-publish' in b}
        self.assertEqual(sorted(pub), ['pypi', 'testpypi'])
        for n, b in js.items():
            with self.subTest(job=n):
                if n in pub:
                    self.assertRegex(b, r'\n    permissions:\n      id-token: write\n')
                    self.assertRegex(b, r'\n    environment:\n      name: %s\n      url: https://%s/p/domino-calibrator\n'
                                     % (n, 'pypi.org' if n == 'pypi' else r'test\.pypi\.org'))
                    self.assertRegex(b, r'uses: pypa/gh-action-pypi-publish@[0-9a-f]{40}  # v1\.\d+\.\d+')   # F13: release/v1, pinned by SHA
                    self.assertRegex(b, r'uses: actions/download-artifact@[0-9a-f]{40}  # v8\.\d+\.\d+')
                    self.assertRegex(b, r'\n    needs: build\n')
                    self.assertNotIn('actions/checkout', b)                   # a publishing job runs no code of the repository
                else:
                    self.assertNotIn('id-token', b)

    def test_the_build_in_its_own_job_and_each_index_on_its_own_trigger(self):
        w = self.wf()
        js = jobs(w)
        self.assertIn('build', js)
        b = js.get('build', '')
        for what, pat in (('checkout without credentials', r'uses: actions/checkout@[0-9a-f]{40}  # v7\.\d+\.\d+\n        with:\n          persist-credentials: false'),
                          ('the tested Python', r'uses: actions/setup-python@[0-9a-f]{40}  # v7\.\d+\.\d+\n        with:\n          python-version: "3\.11"'),
                          ('the build', r'python -m build\b'), ('the dists handed on', r'uses: actions/upload-artifact@[0-9a-f]{40}  # v7\.\d+\.\d+'),
                          ('the tag is the version', r'github\.event\.release\.tag_name')):
            with self.subTest(what):
                self.assertRegex(b, pat)
        with self.subTest('TestPyPI by hand only, at its own address'):
            self.assertRegex(js.get('testpypi', ''), r"(?m)^    if: github\.event_name == 'workflow_dispatch'\n")
            self.assertIn('repository-url: https://test.pypi.org/legacy/', js.get('testpypi', ''))
        with self.subTest('PyPI on a release only'):
            self.assertRegex(js.get('pypi', ''), r"(?m)^    if: github\.event_name == 'release'\n")
            self.assertNotIn('repository-url', js.get('pypi', ''))
        with self.subTest('no secret, no password: Trusted Publishing only'):
            self.assertNotRegex(w, r'secrets\.|password:|username:')


def runs_files():
    c = subprocess.run(['git', '-C', ROOT, 'ls-files', 'runs'], capture_output=True, text=True, encoding='utf-8')
    names = [os.path.basename(f) for f in c.stdout.split('\n') if f.strip()] if c.returncode == 0 else []
    return names or sorted(os.listdir(os.path.join(ROOT, 'runs')))


def families(text):
    """The file families a runs/ README names: its code spans that hold a wildcard."""
    return [s for s in re.findall(r'`([^`\s]+)`', text) if '*' in s]


class F4_36_RunsReadme(unittest.TestCase):
    PATH = os.path.join(ROOT, 'runs', 'README.md')

    def test_a_short_readme_naming_every_family(self):
        self.assertTrue(os.path.exists(self.PATH), 'no runs/README.md')
        t = read(self.PATH)
        fam = families(t)
        with self.subTest('short'):
            self.assertLessEqual(len(t.splitlines()), 60)
        with self.subTest('the control: a name no family holds is caught'):
            self.assertFalse(any(fnmatch.fnmatchcase('ZZ_UNNAMED_2026-10-01.bin', p) for p in fam))
        stray = [f for f in runs_files() if f != 'README.md' and not any(fnmatch.fnmatchcase(f, p) for p in fam)]
        with self.subTest('every file in runs/ in a family the README names'):
            self.assertEqual(stray, [])
        with self.subTest('the study first: how to reproduce it'):
            self.assertRegex(t, r'tools/fetch_frames\.py')
            self.assertRegex(t, r'(?i)reproduc')


if __name__ == '__main__':
    unittest.main()
