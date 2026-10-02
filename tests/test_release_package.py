r"""The first release's packaging (the release room's record of 28 Sept 2026, not in this repository, the bar): the credit line on both faces and
in the README; one version everywhere; the MIT LICENSE with the credit notice; CITATION.cff; pyproject.toml (pip
install from the folder, the tested versions as the minimums); a fresh environment where pip installs the folder and
the command line runs on a test image, its record judged by the MPC's validator; the CI file. Written to fail on the
calibrator as the sixth room's pull request merged it (1e19288) and to pass once the packaging is in; every case is a
subTest.

His decisions (the launch road's section 7, and this room's): MIT; the credit "A Castle product from Domino
Observatory. Built by Annie, the Castle's AI."; the pip name domino-calibrator; "Copyright (c) 2026 Domino Observatory".
Read at source on 28 Sept 2026:
- SPDX's MIT (https://spdx.org/licenses/MIT.json): its text, and its template, where the notice is any text of up to
  5,000 characters before "Permission is hereby granted", so the credit may stand under the copyright line;
- CFF 1.2.0's schema (https://citation-file-format.github.io/1.2.0/schema.json): authors, cff-version, message and
  title are required; an entity needs only a name.
The minimums are the versions this suite runs on (the only ones measured), read from the running kit, not typed in.

The fresh environments need PyPI (through the environment's proxy) and take about a minute each. Each builds from a
copy of the folder, so nothing is written into it: one with the tested versions pinned, one with what pip picks today
(on 28 Sept, astropy 8.0.1 was PyPI's newest; 6.1.7 is tested).

The twelfth room (29 Sept 2026; the launch plan's missing step 1, the issue list's entry 1, the fourth pass's D4.7):
`pip install .` into a system Python that PEP 668 marks as externally managed stops with "error:
externally-managed-environment" (measured on Ubuntu 24.04's Python 3.12, whose marker its libpython3.12-stdlib ships).
PEP 668 (https://peps.python.org/pep-0668/, read 29 Sept 2026): the marker is an EXTERNALLY-MANAGED file in the
directory identified by sysconfig.get_path("stdlib"). K8 runs the README's install block as a stranger types it, in a
shell whose python3 and pip are such a Python, with a control: a plain pip install there is refused. K9 asks the page's
one install hint to say the same. Written to fail on the words as the eleventh room left them (10ac2b0).

Its amendment, the same room, his word ([his words, not quoted in public]):
the three assumptions step 1 was shown with, checked at source and measured, were three faults. (1) Ubuntu 24.04's four
images (desktop 24.04.5.1, server 24.04.5, WSL 24.04.5 and the cloud image; their manifests, read 29 Sept 2026) hold
python3.12 but not python3.12-venv, and without it Ubuntu's own venv stops ("ensurepip is not available ... apt install
python3.12-venv"): K10. (2) GitHub's Ubuntu 24.04 image writes /etc/pip.conf with break-system-packages = true
(actions/runner-images, install-python.sh), under which Ubuntu's pip installs instead of refusing (measured here, that file
given to pip as a global config): K8's shell now reads no pip configuration, as a stock Ubuntu has none. (3) In
PowerShell, `.venv\Scripts\activate` runs Activate.ps1, which Python's venv docs say may need the execution policy
changed, and which Microsoft's default for Windows clients (Restricted) blocks: K11. Written to fail on the words as
97190cc left them.

Its second amendment, the same room, read and measured while the first ran green: (4) the README's block run with
python3 3.10 (Ubuntu 22.04's default version) stops at pip, "requires a different Python: 3.10.20 not in '>=3.11'",
before the paragraph names the version: K12. (5) K11 asks for the Windows forms Microsoft and pip document: a command
given by its path, with ".\" for the current directory (about_Command_Precedence), and the console command as pip's
executable (the PyPA's entry points spec: "wrapped in a console executable"; pip's distlib names it '%s.exe'). Written
to fail on the words as 7d32021 left them.

The thirteenth room (29 Sept 2026; the launch list's first inside step, the tests on any machine; the issue list's entries
2, 3, 5 and 7): K5, K7, K6 and K8 compared the files with the running Python and libraries, as W4 did, so the suite went red
on any machine but the Castle's (measured on what pip picks today: 7 failures on Python 3.11, 15 on 3.13 and on 3.14). The
tested versions are now read from one record, pyproject.toml's minimums, and K13 alone compares the running versions with
it: equal in the job that runs the tested versions (DOMINO_CALIBRATOR_TESTED_VERSIONS=1), at least the record anywhere
else. K6 installs the tested versions on the tested Python when this machine has one, finds each environment's programs
where the platform puts them (sysconfig's venv scheme), and skips, naming what is missing, without PyPI or the MPC's
validator; K8 skips without PyPI; K8 and K10 look for a system Python at least as new as the record's, not the running one.
This docstring is raw: its PowerShell line held an invalid escape (a SyntaxWarning from Python 3.12 on, "will not work in
the future"), and two valid ones that Python read as a bell and a lost backslash. The bar: runs/any_machine.py.

The same room, the launch list's step 2 (the issue list's entry 6; his words: Linux's picks on all four Pythons, [his words, not quoted in public]; Windows and macOS [his words, not quoted in public]; K14, [his words, not quoted in public]): K7 reads the rewritten workflow, two jobs. The tested
versions on Linux; what pip picks today on Linux (Python 3.11 to 3.14), Windows and macOS (3.14), each with 3.11 beside it
for K6. Both run the suite through tests/strict.py, which fails on any skip a job does not name (off Linux, only K8 and
K10's Debian records); off Linux the README's own install lines run too (tests/readme_install.py). The actions are their
newest majors, on Node 24: Node 20 left GitHub's runners on 23 Sept 2026 (GitHub's changelog, read at source), and the
seventh room's v4 and v5 ran on it. K14, new: every .py in the folder compiles with SyntaxWarning and DeprecationWarning as
errors. The bar: runs/ci_bar.py.

The launch list's step 3, the import rename (30 Sept 2026, the calibrator's build room; the issue list's entry 9: the import
name calibrator is an unrelated project's on PyPI): the package is domino_calibrator/, inside the folder that goes public,
and the tests run from that folder's root whatever the checkout is called. K5 reads the new listing, K6 asks that the
distribution's one top-level name is domino_calibrator (so the old name cannot come from it), and K7
that the CI runs the suite, the fetcher, the install and the README's lines from inside its checkout, with its tools
outside it. The bar: runs/rename_bar.py.
"""
import os, re, sys, glob, json, shutil, tomllib, tempfile, unittest, warnings, functools, sysconfig, subprocess

import numpy, scipy, astropy, yaml
from packaging.version import Version
import domino_calibrator
from tests.test_hardening import comet, write, REC_ARGS, mpc_judge, ADES_PYLIB, ADES_MASTER, given

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)                             # the checkout's root, the folder that goes public (calibrator/ here)
ROOT = os.path.dirname(PKG)
NAME = 'domino-calibrator'
CREDIT = "A Castle product from Domino Observatory. Built by Annie, the Castle's AI."
COPYRIGHT = 'Copyright (c) 2026 Domino Observatory'
KIT = {'numpy': numpy.__version__, 'scipy': scipy.__version__, 'astropy': astropy.__version__}      # the running versions
PY = '%d.%d' % sys.version_info[:2]
FLAG = 'DOMINO_CALIBRATOR_TESTED_VERSIONS'      # "1": this job runs the tested versions (the CI's tested job, the Castle's runs)
# SPDX's MIT text after its notice (https://spdx.org/licenses/MIT.json, licenseText, read 28 Sept 2026)
MIT_BODY = ('Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated '
            'documentation files (the "Software"), to deal in the Software without restriction, including without '
            'limitation the rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the '
            'Software, and to permit persons to whom the Software is furnished to do so, subject to the following '
            'conditions: The above copyright notice and this permission notice shall be included in all copies or '
            'substantial portions of the Software. THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS '
            'OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE '
            'AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR '
            'OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION '
            'WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.')


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def squash(t):
    return re.sub(r'\s+', ' ', t).strip()


def page_visible():
    h = re.sub(r'<(script|style)\b.*?</\1>', ' ', read(os.path.join(PKG, 'page', 'index.html')), flags=re.S)
    import html
    return squash(html.unescape(re.sub(r'<[^>]+>', ' ', h)))


def cli_version():
    c = subprocess.run([sys.executable, '-m', 'domino_calibrator.cli', '--version'], cwd=PKG, capture_output=True, text=True, encoding='utf-8', errors='replace')
    return c.returncode, c.stdout + c.stderr


def pyproject():
    p = os.path.join(PKG, 'pyproject.toml')
    if not os.path.exists(p):
        return None
    with open(p, 'rb') as f:
        return tomllib.load(f)


def citation():
    p = os.path.join(PKG, 'CITATION.cff')
    return yaml.safe_load(read(p)) if os.path.exists(p) else None


def tested_versions():
    """The tested versions, recorded once: pyproject.toml's minimums, which it says are the versions the suite was run on.
    {'Python': '3.11', 'numpy': ..., 'scipy': ..., 'astropy': ...}, or what of it can be read."""
    proj = (pyproject() or {}).get('project', {})
    m = re.fullmatch(r'>=(\d+\.\d+)', proj.get('requires-python', ''))
    rec = {'Python': m.group(1)} if m else {}
    for d in proj.get('dependencies', []):
        dm = re.fullmatch(r'([A-Za-z0-9_.-]+)>=(\d[\w.]*)', d)
        if dm:
            rec[dm.group(1)] = dm.group(2)
    return rec


RECORD = tested_versions()


def venv_program(venv, name):
    """A program inside a virtual environment, where this platform puts it: sysconfig's venv scheme (Python 3.11 on) gives
    the bin folder on POSIX and the Scripts folder on Windows, and EXE the extension ('.exe' on Windows, '' elsewhere)."""
    scripts = sysconfig.get_path('scripts', 'venv', vars={'base': venv, 'platbase': venv})
    return os.path.join(scripts, name + (sysconfig.get_config_var('EXE') or ''))


def tested_python():
    """The tested Python (the record's version) on this machine, or None: the running one if it is that version; else
    `python3.11` (the record's version) on the PATH; else, on Windows, what the launcher runs for `py -3.11` (Python's
    Windows docs: "to launch Python 3.7, try the command: py -3.7"). Each candidate is asked its version."""
    want = RECORD.get('Python')
    if not want:
        return None
    cands = [sys.executable] if PY == want else []
    cands += [p for p in (shutil.which('python' + want),) if p]
    if shutil.which('py'):
        c = subprocess.run(['py', '-' + want, '-c', 'import sys; print(sys.executable)'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        if c.returncode == 0 and c.stdout.strip():
            cands.append(c.stdout.strip())
    for exe in cands:
        c = subprocess.run([exe, '-c', 'import sys; print("%d.%d" % sys.version_info[:2])'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        if c.returncode == 0 and c.stdout.strip() == want:
            return exe
    return None


@functools.lru_cache(maxsize=None)
def pypi_unreachable():
    """None when pip reaches PyPI from here; else why not, for the tests that install from it to skip with (the issue
    list's entry 5). pip's own download of pip, with no retries: pip's configuration, proxy and certificates, as the
    installs themselves meet them."""
    tmp = tempfile.mkdtemp(prefix='probe_')
    try:
        c = subprocess.run([sys.executable, '-m', 'pip', 'download', '--no-deps', '--retries', '0', '--timeout', '15',
                            '--disable-pip-version-check', '-q', '-d', tmp, 'pip'], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    if c.returncode == 0:
        return None
    last = [l.strip() for l in (c.stdout + c.stderr).splitlines() if l.strip()]
    return 'pip cannot reach PyPI from here (pip download pip: %s)' % (last[-1][:200] if last else 'exit %d' % c.returncode)


# ---------------------------------------------------------------- the credit line
class TestCredit(unittest.TestCase):
    def test_k1_the_credit_line_on_both_faces_in_the_readme_and_the_license(self):
        # the launch road's section 7: "A Castle product from Domino Observatory. Built by Annie, the Castle's AI."
        # Amended 30 Sept 2026, night (his call, the audit's option (a)): GitHub read LICENSE as "Other" with the line inside
        # its notice (licensee 92.54 % against MIT), so the line leaves LICENSE and stays in the README, the page, --version
        # and CITATION.cff
        with self.subTest('README.md'):
            self.assertIn(CREDIT, squash(read(os.path.join(PKG, 'README.md'))))
        with self.subTest('the page'):
            self.assertIn(CREDIT, page_visible())
        with self.subTest('the command line: --version'):
            rc, out = cli_version()
            self.assertEqual(rc, 0, out[-300:])
            self.assertIn(CREDIT, squash(out))
        with self.subTest('CITATION.cff'):
            self.assertIn(CREDIT, squash(read(os.path.join(PKG, 'CITATION.cff'))))
        with self.subTest('not in LICENSE, which is MIT exactly'):
            p = os.path.join(PKG, 'LICENSE')
            self.assertTrue(os.path.exists(p), 'no LICENSE in calibrator/')
            self.assertNotIn(CREDIT, squash(read(p)))


# ---------------------------------------------------------------- one version everywhere
class TestVersion(unittest.TestCase):
    def test_k2_one_version_in_the_package_pyproject_citation_the_page_and_the_command_line(self):
        v = domino_calibrator.__version__
        with self.subTest('the package says one'):
            self.assertRegex(v, r'^\d+\.\d+\.\d+$')
        with self.subTest('pyproject.toml'):
            pp = pyproject()
            self.assertIsNotNone(pp, 'no pyproject.toml in calibrator/')
            proj = pp['project']
            if 'version' in proj.get('dynamic', []):
                self.assertEqual(pp['tool']['setuptools']['dynamic']['version'], {'attr': 'domino_calibrator.__version__'})
            else:
                self.assertEqual(proj.get('version'), v)
        with self.subTest('CITATION.cff'):
            c = citation()
            self.assertIsNotNone(c, 'no CITATION.cff in calibrator/')
            self.assertEqual(str(c.get('version')), v)
        with self.subTest('the page shows it'):
            self.assertIn('%s %s' % (NAME, v), page_visible())
        with self.subTest('the command line shows it'):
            rc, out = cli_version()
            self.assertEqual(rc, 0, out[-300:])
            self.assertIn('%s %s' % (NAME, v), out)


# ---------------------------------------------------------------- the LICENSE and CITATION.cff
class TestLicenseAndCitation(unittest.TestCase):
    def test_k3_the_license_is_mit_by_spdxs_text_with_the_credit_in_its_notice(self):
        p = os.path.join(PKG, 'LICENSE')
        with self.subTest('present'):
            self.assertTrue(os.path.exists(p), 'no LICENSE in calibrator/')
        t = read(p) if os.path.exists(p) else ''
        i = t.find('Permission is hereby granted')
        notice, body = t[:i], t[i:]
        with self.subTest('the notice: the copyright line alone (amended 30 Sept 2026, night: the audit\'s option (a))'):
            self.assertGreaterEqual(i, 0)
            self.assertEqual(squash(notice), squash('MIT License ' + COPYRIGHT))
        with self.subTest("the body is SPDX's MIT, word for word"):
            self.assertEqual(squash(body), MIT_BODY)
        with self.subTest('pyproject and CITATION.cff say MIT'):
            pp, c = pyproject(), citation()
            self.assertIsNotNone(pp); self.assertIsNotNone(c)
            self.assertEqual(pp['project'].get('license'), 'MIT')
            self.assertEqual(c.get('license'), 'MIT')

    def test_k4_citation_cff_by_the_1_2_0_schema_its_authors_from_the_credit(self):
        c = citation()
        with self.subTest('present'):
            self.assertIsNotNone(c, 'no CITATION.cff in calibrator/')
        c = c or {}
        with self.subTest("the schema's required keys"):
            for k in ('authors', 'cff-version', 'message', 'title'):
                self.assertIn(k, c)
            self.assertEqual(str(c.get('cff-version')), '1.2.0')
            self.assertIsInstance(c.get('message'), str)
        with self.subTest('title and type'):
            self.assertEqual(c.get('title'), NAME)
            self.assertEqual(c.get('type', 'software'), 'software')
        # the fix room (his answer 5, 1 Oct 2026): "Domino Observatory" alone wherever a field names the authors; the credit
        # line stays where people read it, CITATION.cff's message among them
        with self.subTest('the authors: Domino Observatory alone, an entity named in the credit; the credit in the message'):
            a = c.get('authors') or []
            self.assertTrue(a)
            for e in a:
                self.assertIn('name', e)                          # an entity, not a person
                self.assertNotIn('given-names', e); self.assertNotIn('family-names', e)
                self.assertIn(e['name'], CREDIT)
            self.assertEqual([e.get('name') for e in a], ['Domino Observatory'])
            self.assertIn(CREDIT, c.get('message') or '')


# ---------------------------------------------------------------- pyproject.toml
class TestPyproject(unittest.TestCase):
    def test_k5_pyproject_the_name_the_tested_minimums_and_hstpsf_left_out(self):
        pp = pyproject()
        with self.subTest('present'):
            self.assertIsNotNone(pp, 'no pyproject.toml in calibrator/')
        pp = pp or {'project': {}, 'tool': {}}
        proj = pp['project']
        with self.subTest('the name'):
            self.assertEqual(proj.get('name'), NAME)
        # the thirteenth room: pyproject.toml is the record of the tested versions, so its form is checked here, the words
        # against it here and in K7 and W4, and the running versions against it in K13 alone
        with self.subTest('Python: a minimum, the tested one'):
            self.assertRegex(proj.get('requires-python', ''), r'^>=\d+\.\d+$')
        with self.subTest('the dependencies: numpy, scipy and astropy, each with its tested version as the minimum'):
            deps = proj.get('dependencies', [])
            self.assertEqual(sorted(re.sub(r'>=.*', '', d) for d in deps), ['astropy', 'numpy', 'scipy'])
            for d in deps:
                self.assertRegex(d, r'^[a-z]+>=\d+\.\d+\.\d+$')
        with self.subTest('the README names the tested versions'):
            r = read(os.path.join(PKG, 'README.md'))
            self.assertEqual(sorted(RECORD), ['Python', 'astropy', 'numpy', 'scipy'])
            for k, v in RECORD.items():
                self.assertIn('%s %s' % (k, v), r)
        with self.subTest('the modules: every one but hstpsf.py (it needs TinyTim and the Castle\'s psfkit)'):
            st = pp.get('tool', {}).get('setuptools', {})
            mods = set(st.get('py-modules', []))
            want = {'domino_calibrator.' + os.path.basename(f)[:-3] for f in glob.glob(os.path.join(PKG, 'domino_calibrator', '*.py'))
                    if os.path.basename(f) not in ('__init__.py', 'hstpsf.py')}
            self.assertIsNone(st.get('package-dir'))            # the step-3 layout: the package is the folder domino_calibrator/
            self.assertEqual(mods, want)
            self.assertGreater(len(want), 7)
        with self.subTest('a console command, if any, is the command line'):
            for name, target in proj.get('scripts', {}).items():
                self.assertEqual(target, 'domino_calibrator.cli:main', name)


# ---------------------------------------------------------------- pip install into a fresh environment, and a run
def fresh_install(tmp, pins, python=None):
    """A copy of the folder (without runs/ and caches), a fresh venv made by `python` (the running one if None), pip install
    of the copy. Returns (ok, log, py).
    The copy sits in its own folder, away from where the commands run: from a folder holding it, `python -m` would import
    the copy and not the installed package (amended at the fix step; its own subTest caught it)."""
    src = os.path.join(tmp, 'src', 'checkout')
    shutil.copytree(PKG, src, ignore=shutil.ignore_patterns('runs', '__pycache__', '*.egg-info', 'build'))
    venv = os.path.join(tmp, 'venv')
    os.makedirs(os.path.join(tmp, 'run'))                 # where every command runs: no source in it
    log = ''
    c = subprocess.run([python or sys.executable, '-m', 'venv', '--clear', venv], capture_output=True, text=True, encoding='utf-8', errors='replace')
    log += c.stdout + c.stderr
    py = venv_program(venv, 'python')
    if c.returncode != 0:
        return False, log, py
    args = [py, '-m', 'pip', 'install', '--disable-pip-version-check', '-q', src]
    if pins:
        con = os.path.join(tmp, 'constraints.txt')
        with open(con, 'w', encoding='utf-8') as f:
            f.write(''.join('%s==%s\n' % kv for kv in pins.items()))
        args += ['-c', con]
    c = subprocess.run(args, cwd=os.path.join(tmp, 'run'), capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
    log += c.stdout + c.stderr
    return c.returncode == 0, log, py


def in_venv(py, code, cwd):
    c = subprocess.run([py, '-c', code], cwd=cwd, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
    return c.returncode, (c.stdout + c.stderr).strip()


class TestFreshInstall(unittest.TestCase):
    def test_k6_pip_installs_the_folder_and_the_command_line_runs_on_a_test_image(self):
        # the thirteenth room: the tested versions are the record's, installed on the tested Python (on another Python they
        # may have no wheels: none for 3.14, PyPI's file lists, 29 Sept 2026); without PyPI, or the MPC's validator, skip
        offline = pypi_unreachable()
        if offline:
            self.skipTest(offline)
        tested = {k: RECORD.get(k) for k in ('numpy', 'scipy', 'astropy')}
        for label, python, pins in (('the tested versions', tested_python(), tested), ('what pip picks today', sys.executable, None)):
            if python is None:
                with self.subTest(label, what='the tested Python'):
                    self.skipTest('the tested versions are installed on the tested Python, %s, and this machine has none'
                                  % RECORD.get('Python'))
                continue
            tmp = tempfile.mkdtemp(prefix='fresh_')
            try:
                ok, log, py = fresh_install(tmp, pins, python)
                with self.subTest(label, what='pip install from the folder'):
                    self.assertTrue(ok, log[-800:])
                if not ok:
                    continue
                run = os.path.join(tmp, 'run')
                rc, where = in_venv(py, 'import domino_calibrator; print(domino_calibrator.__file__)', run)
                with self.subTest(label, what='imported from the environment, not the Castle'):
                    self.assertEqual(rc, 0, where)
                    self.assertIn(os.path.join(tmp, 'venv'), where)
                rc, vers = in_venv(py, 'import sys, importlib.metadata as m, numpy, scipy, astropy; print("%%d.%%d.%%d" %% '
                                       'sys.version_info[:3], m.version("%s"), numpy.__version__, scipy.__version__, '
                                       'astropy.__version__)' % NAME, run)
                v = vers.split() if rc == 0 else []
                print('\n    [%s] installed: Python %s | %s %s | numpy scipy astropy: %s' % (
                    label, v[0] if v else '?', NAME, v[1] if len(v) > 1 else '?', ' '.join(v[2:])))
                with self.subTest(label, what='the Python it was made from'):
                    self.assertEqual(len(v), 5, vers)
                    if pins:
                        self.assertEqual(v[0].rsplit('.', 1)[0], RECORD.get('Python'))
                with self.subTest(label, what="the installed version is the package's"):
                    self.assertEqual(v[1:2], [domino_calibrator.__version__])
                with self.subTest(label, what='the tested versions, where pinned'):
                    if pins:
                        self.assertEqual(v[2:], [pins['numpy'], pins['scipy'], pins['astropy']])
                rc, out = in_venv(py, 'import domino_calibrator.hstpsf', run)
                with self.subTest(label, what='hstpsf is not in the package'):
                    self.assertNotEqual(rc, 0)
                    self.assertIn("No module named 'domino_calibrator.hstpsf'", out)
                rc, out = in_venv(py, 'import json, importlib.metadata as m; print(json.dumps([str(f) for f in '
                                      'm.distribution("%s").files]))' % NAME, run)
                with self.subTest(label, what="the distribution's one top-level name is domino_calibrator (entry 9)"):
                    self.assertEqual(rc, 0, out[-300:])
                    files = json.loads(out) if rc == 0 else []
                    self.assertEqual(sorted({f.split('/')[0] for f in files if not f.startswith('..')
                                             and not f.split('/')[0].endswith('.dist-info')}), ['domino_calibrator'])
                img, _ = comet()
                fits_path = write(os.path.join(run, 'c.fits'), img)
                commands = [[py, '-m', 'domino_calibrator.cli']]
                for name in (pyproject() or {}).get('project', {}).get('scripts', {}):
                    commands.append([venv_program(os.path.join(tmp, 'venv'), name)])
                for cmd in commands:
                    c = subprocess.run(cmd + [fits_path] + given(fits_path) + REC_ARGS, cwd=run, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=300)
                    out = c.stdout
                    with self.subTest(label, command=os.path.basename(cmd[-1]), what='runs on the test image'):
                        self.assertEqual(c.returncode, 0, (c.stdout + c.stderr)[-600:])
                        self.assertRegex(out, r'# zero aperture: x \d+\.\d{4} y \d+\.\d{4}')
                        self.assertIn('# version=2022', out)
                    with self.subTest(label, command=os.path.basename(cmd[-1]), what="the MPC's judge on its record"):
                        if not (ADES_PYLIB and ADES_MASTER):
                            self.skipTest('the MPC judge needs ADES_PYLIB and ADES_MASTER (see test_hardening)')
                        ok, why = mpc_judge(out[out.index('# version='):], run)
                        self.assertTrue(ok, why)
                    c = subprocess.run(cmd + ['--version'], cwd=run, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
                    with self.subTest(label, command=os.path.basename(cmd[-1]), what='--version: the version and the credit'):
                        self.assertEqual(c.returncode, 0, (c.stdout + c.stderr)[-300:])
                        self.assertIn('%s %s' % (NAME, domino_calibrator.__version__), c.stdout)
                        self.assertIn(CREDIT, squash(c.stdout))
            finally:
                shutil.rmtree(tmp, ignore_errors=True)


# ---------------------------------------------------------------- the CI, written now, run once the public repository exists
# the thirteenth room, step 2, read at source on 29 Sept 2026: the actions' newest majors, each on Node 24 (their action.yml);
# GitHub's runner images ubuntu-24.04, windows-2025 and macos-26, each with Python 3.11 and 3.14
NODE24 = {'actions/checkout@v7', 'actions/setup-python@v7', 'actions/setup-node@v7', 'actions/cache@v6'}
PICKS = {('ubuntu-24.04', '3.11'), ('ubuntu-24.04', '3.12'), ('ubuntu-24.04', '3.13'), ('ubuntu-24.04', '3.14'),
         ('windows-2025', '3.14'), ('macos-26', '3.14')}
OFF_LINUX_SKIPS = '--may-skip test_k8_ --may-skip test_k10_'      # K8 and K10's Debian records: Linux's by design
WINDOWS_SKIPS = OFF_LINUX_SKIPS + ' --may-skip test_the_command_line_with_raw_bytes_in_argv'   # and raw bytes in argv: UTF-16 there


def job_block(text, job):
    """A job's lines in the workflow, as written: from its key to the next job's, or the end."""
    m = re.search(r'^  %s:\n(.*?)(?=^  [\w-]+:\n|\Z)' % re.escape(job), text, flags=re.S | re.M)
    return m.group(1) if m else ''


class TestCI(unittest.TestCase):
    def test_k7_the_ci_runs_what_the_green_run_runs(self):
        p = os.path.join(PKG, '.github', 'workflows', 'tests.yml')
        with self.subTest("present, in the checkout's root (the Castle has no .github/: nothing runs on the private repository)"):
            self.assertTrue(os.path.exists(p), 'no .github/workflows/tests.yml in the checkout')
            self.assertFalse(os.path.exists(os.path.join(ROOT, '.github')))
        if not os.path.exists(p):
            return
        t = read(p)
        with self.subTest('it parses'):
            w = yaml.safe_load(t)
            self.assertIn('jobs', w)
        # the thirteenth room, step 1: the record's versions, not the running ones; the tested job says so with the flag, for
        # K13. Step 2 (the issue list's entry 6; his words: Linux's picks on all four Pythons, Windows and macOS on every
        # push): two jobs, a strict runner, the README's own lines off Linux, and the actions on Node 24
        w = yaml.safe_load(t) or {}
        jobs = w.get('jobs') or {}
        tested, picks = jobs.get('tested') or {}, jobs.get('picks') or {}
        tt, pt = job_block(t, 'tested'), job_block(t, 'picks')
        inc = ((picks.get('strategy') or {}).get('matrix') or {}).get('include') or []
        runs = lambda job: [str(s.get('run', '')).strip() for s in (job.get('steps') or []) if 'run' in s]
        with self.subTest('two jobs: the tested versions, and what pip picks today'):
            self.assertEqual(sorted(jobs), ['picks', 'tested'])
        with self.subTest("the tested job: Linux, the record's Python and versions, the flag"):
            self.assertEqual(tested.get('runs-on'), 'ubuntu-24.04')
            for n in ['python-version: "%s"' % RECORD.get('Python')] + [
                    '%s==%s' % (k, RECORD.get(k)) for k in ('numpy', 'scipy', 'astropy')] + ['%s: "1"' % FLAG]:
                self.assertIn(n, tt)
        with self.subTest('what pip picks today: Linux on Python 3.11 to 3.14, Windows and macOS on 3.14, nothing pinned'):
            self.assertEqual(sorted((e.get('os'), str(e.get('python'))) for e in inc), sorted(PICKS))
            self.assertEqual(picks.get('runs-on'), '${{ matrix.os }}')
            self.assertIs((picks.get('strategy') or {}).get('fail-fast'), False)
            self.assertNotIn(FLAG, pt)
            self.assertNotRegex(pt, r'(?:numpy|scipy|astropy)==')
        with self.subTest("the record's Python beside each picks job's own, for K6's install of the tested versions"):
            vers = [(s.get('with') or {}).get('python-version') for s in (picks.get('steps') or [])
                    if str(s.get('uses', '')).startswith('actions/setup-python@')]
            self.assertEqual([[l.strip() for l in str(v).splitlines() if l.strip()] for v in vers],
                             [[RECORD.get('Python'), '${{ matrix.python }}']])
        with self.subTest('nothing skipped: the strict runner in both jobs; off Linux, only K8 and K10 may skip (and on Windows, F1\'s raw bytes)'):
            self.assertIn('python -m tests.strict', runs(tested))
            self.assertIn('python -m tests.strict ${{ matrix.may_skip }}', runs(picks))
            for e in inc:
                if str(e.get('os', '')).startswith('ubuntu'):
                    self.assertNotIn('may_skip', e)
                else:
                    self.assertEqual(e.get('may_skip'), WINDOWS_SKIPS if str(e.get('os', '')).startswith('windows') else OFF_LINUX_SKIPS)
        with self.subTest("the README's own install lines, on Windows and macOS"):
            st = [s for s in (picks.get('steps') or []) if str(s.get('run', '')).strip() == 'python tests/readme_install.py']
            self.assertEqual([s.get('if') for s in st], ["runner.os != 'Linux'"])
        with self.subTest("the actions on Node 24, their newest majors (Node 20 left GitHub's runners on 23 Sept 2026)"):
            used = ['%s@v%s' % m for m in re.findall(r'^\s*(?:-\s+)?uses:\s*([\w./-]+)@[0-9a-f]{40}  # v(\d+)\.\d+\.\d+', t, flags=re.M)]   # F13
            self.assertEqual(len(used), len(re.findall(r'^\s*(?:-\s+)?uses:', t, flags=re.M)))          # every one pinned by SHA
            self.assertTrue(used)
            self.assertEqual(set(used) - NODE24, set())
        with self.subTest("minutes: a time cap on each job, a new push cancels the one running, read-only"):
            for j in (tested, picks):
                self.assertIsInstance(j.get('timeout-minutes'), int)
            self.assertIs((w.get('concurrency') or {}).get('cancel-in-progress'), True)
            self.assertEqual(w.get('permissions'), {'contents': 'read'})
        # step 3 (the import rename): the checkout's root is the folder that goes public, whatever it is called; the suite, the
        # fetcher, the install and the README's lines run in it, and the tools stay outside it (K14 compiles every .py inside)
        for jname, job in (('tested', tested), ('picks', picks)):
            steps = job.get('steps') or []
            co = [(s.get('with') or {}).get('path') for s in steps if str(s.get('uses', '')).startswith('actions/checkout@')]
            with self.subTest('one checkout, into a folder of its own', job=jname):
                self.assertEqual(len(co), 1)
                self.assertTrue(co and co[0], 'the checkout has no path of its own: the tools would land inside it')
            where = co[0] if co else None
            for s in steps:
                r = str(s.get('run', ''))
                if re.search(r'tests\.strict|fetch_frames\.py|pip install \.(?:\s|$)|readme_install\.py', r):
                    with self.subTest('run from inside the checkout', job=jname, step=s.get('name', r[:40])):
                        self.assertEqual(s.get('working-directory'), where)
                if re.search(r'ades-master|playwright', r):
                    with self.subTest('the tools stay outside the checkout', job=jname, step=s.get('name', r[:40])):
                        self.assertIsNone(s.get('working-directory'))
                        self.assertNotIn(str(where), r)
        for job, text in (('tested', tt), ('picks', pt)):          # what each job shares with the green run in the Castle
            for n in ('fetch_frames.py 22 03 04 05 06', 'IAU-ADES/ades-master', '39ae5a9',
                      'playwright@1.56.1', 'ADES_PYLIB', 'ADES_MASTER', 'PLAYWRIGHT_MODULE'):
                with self.subTest('it names', job=job, what=n):
                    self.assertIn(n, text)


# ---------------------------------------------------------------- the README's install block, as a stranger types it
def install_block():
    """The first fenced block under the README's '## Install', as written."""
    m = re.search(r'^## Install\n(.*?)(?=^## )', read(os.path.join(PKG, 'README.md')), flags=re.S | re.M)
    b = re.search(r'```[^\n]*\n(.*?)```', m.group(1), flags=re.S) if m else None
    return b.group(1) if b else ''


def managed_python():
    """A system Python as Ubuntu ships it (/usr/bin/python3.N), at least the record's version (the README's minimum; the
    thirteenth room: not the running one, which left none on Python 3.13 and 3.14 here), that PEP 668 marks as externally
    managed; or None. This cloud's own /usr/bin/python3 is 3.11 and unmarked, so the stranger's shell is built."""
    want = tuple(int(x) for x in RECORD.get('Python', PY).split('.'))
    for exe in sorted(glob.glob('/usr/bin/python3.*'), key=lambda p: [int(x) for x in re.findall(r'\d+', p)]):
        if not re.fullmatch(r'/usr/bin/python3\.\d+', exe):
            continue
        c = subprocess.run([exe, '-c', 'import os, sys, sysconfig; print(sys.version_info[:2] >= %r and os.path.exists('
                            'os.path.join(sysconfig.get_path("stdlib"), "EXTERNALLY-MANAGED")))' % (want,)],
                           capture_output=True, text=True, encoding='utf-8', errors='replace')
        if c.stdout.strip() == 'True':
            return exe
    return None


def stranger_env(tmp, exe):
    """Ubuntu's shell: python3 is that Python and pip its pip (Ubuntu's /usr/bin/pip runs /usr/bin/python3), then the
    system's folders; nothing of this suite's own environment, and no pip configuration file, as a stock Ubuntu has none
    (GitHub's image writes /etc/pip.conf with break-system-packages = true; pip loads no file when PIP_CONFIG_FILE is
    os.devnull, its configuration.py)."""
    b = os.path.join(tmp, 'bin')
    os.makedirs(b)
    os.symlink(exe, os.path.join(b, 'python3'))
    with open(os.path.join(b, 'pip'), 'w', encoding='utf-8') as f:
        f.write('#!/bin/sh\nexec %s -m pip "$@"\n' % exe)
    os.chmod(os.path.join(b, 'pip'), 0o755)
    env = {k: v for k, v in os.environ.items() if k not in ('VIRTUAL_ENV', 'PYTHONPATH', 'PYTHONHOME')
           and not (k.startswith('PIP_') and k != 'PIP_CERT')}          # PIP_CERT: the proxy's CA, to reach PyPI
    env['PATH'] = b + ':/usr/bin:/bin'
    env['PIP_CONFIG_FILE'] = os.devnull
    return env


def install_section():
    """The README's '## Install', up to the next section."""
    m = re.search(r'^## Install\n(.*?)(?=^## )', read(os.path.join(PKG, 'README.md')), flags=re.S | re.M)
    return m.group(1) if m else ''


class TestInstallBlock(unittest.TestCase):
    def test_k8_the_readmes_install_block_as_written_installs_where_pep_668_refuses_a_plain_pip_install(self):
        exe = managed_python()
        if not sys.platform.startswith('linux') or exe is None:
            self.skipTest('no system Python >= %s here that PEP 668 marks as externally managed' % RECORD.get('Python', PY))
        block = install_block()
        with self.subTest("the README has an install block"):
            self.assertTrue(block.strip(), "no fenced block under the README's '## Install'")
        tmp = tempfile.mkdtemp(prefix='stranger_')
        try:
            env = stranger_env(tmp, exe)
            src = os.path.join(tmp, 'checkout')             # the folder as a stranger's checkout holds it
            shutil.copytree(PKG, src, ignore=shutil.ignore_patterns('runs', '__pycache__', '*.egg-info', 'build', '.venv'))
            c = subprocess.run(['pip', 'install', '--dry-run', '.'], cwd=src, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace',
                               timeout=300)                 # --dry-run: pip's own gate still runs (its install.py), nothing lands
            with self.subTest('control: that Python refuses a plain pip install (PEP 668)', python=exe):
                self.assertNotEqual(c.returncode, 0, (c.stdout + c.stderr)[-400:])
                self.assertIn('externally-managed-environment', c.stdout + c.stderr)
            offline = pypi_unreachable()                    # the thirteenth room: the block installs from PyPI
            if offline:
                self.skipTest(offline)
            script = block + ('\ndomino-calibrator --version'
                              '\ncd /    # step 3: from the checkout\'s root, python imports the source tree, which is there'
                              '\npython -c "import domino_calibrator; print(\'module:\', domino_calibrator.__file__)"'
                              '\npython -c "import sys, importlib.metadata as m, numpy, scipy, astropy; print(\'picked:\', '
                              'sys.version.split()[0], m.version(\'%s\'), numpy.__version__, scipy.__version__, '
                              'astropy.__version__)"\n' % NAME)
            c = subprocess.run(['bash', '-e', '-c', script], cwd=src, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=900)
            out = c.stdout
            picked = re.search(r'^picked: (.*)$', out, flags=re.M)
            print('\n    [the README\'s block, %s] %s' % (os.path.basename(exe), picked.group(1) if picked else 'no answer'))
            with self.subTest('the block runs to its end'):
                self.assertEqual(c.returncode, 0, (c.stdout + c.stderr)[-800:])
            with self.subTest('then the command answers with the version and the credit'):
                self.assertIn('%s %s' % (NAME, domino_calibrator.__version__), out)
                self.assertIn(CREDIT, squash(out))
            with self.subTest("the package is an environment's, not the system's"):
                m = re.search(r'^module: (.*)$', out, flags=re.M)
                self.assertIsNotNone(m, out[-400:])
                if m:
                    self.assertIn('site-packages', m.group(1))
                    self.assertFalse(m.group(1).startswith('/usr/'), m.group(1))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)


class TestPageInstallHint(unittest.TestCase):
    def test_k9_the_pages_install_hint_names_the_virtual_environment(self):
        # the page's one install hint said "pip install . in its folder": the same refusal awaits it
        t = page_visible()
        with self.subTest('no bare pip install on the page'):
            self.assertNotIn('pip install .', t)
        with self.subTest("it names the virtual environment, with the README"):
            self.assertRegex(t, r'virtual environment[^.]{0,80}README\.md|README\.md[^.]{0,80}virtual environment')


class TestDebianVenvPackage(unittest.TestCase):
    def test_k10_the_readme_names_the_package_that_holds_venvs_pip_on_debian_and_ubuntu(self):
        # the amendment's (1): a fresh Ubuntu 24.04 has no python3.12-venv, and its venv stops without it
        t = install_section()
        with self.subTest('the README names it, before the block'):
            self.assertIn('apt install python3-venv', t)
            if 'apt install python3-venv' in t and '```' in t:
                self.assertLess(t.index('apt install python3-venv'), t.index('```'))
        with self.subTest("the distro's own records: python3-venv brings the package that holds the stdlib's ensurepip"):
            exe = managed_python()
            if exe is None or not (shutil.which('dpkg') and shutil.which('apt-cache')):
                self.skipTest('no Debian or Ubuntu system Python here to read the packages of')
            c = subprocess.run([exe, '-c', 'import sys, sysconfig; print("%d.%d" % sys.version_info[:2], '
                                'sysconfig.get_path("stdlib"))'], capture_output=True, text=True, encoding='utf-8', errors='replace')
            ver, stdlib = c.stdout.split()
            own = subprocess.run(['dpkg', '-S', os.path.join(stdlib, 'ensurepip', '__main__.py')], capture_output=True,
                                 text=True, encoding='utf-8', errors='replace')
            deps = subprocess.run(['apt-cache', 'depends', 'python3-venv'], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout
            self.assertEqual(own.stdout.split(':')[0], 'python%s-venv' % ver, own.stdout + own.stderr)
            self.assertIn('Depends: python%s-venv' % ver, deps)


class TestWindowsLine(unittest.TestCase):
    def test_k11_the_readmes_windows_line_needs_no_activation_script(self):
        # the amendment's (3). Python's venv docs (https://docs.python.org/3/library/venv.html, read 29 Sept 2026): on
        # Windows, Activate.ps1 may need the execution policy changed; Microsoft (about_Execution_Policies): with no policy
        # set in any scope, the effective policy is Restricted, "the default for Windows clients". The docs' own way round:
        # "You don't specifically need to activate a virtual environment, as you can just specify the full path to that
        # environment's Python interpreter". The second amendment: each program by its path, ".\" for the current
        # directory, and its extension (Microsoft's about_Command_Precedence; pip's distlib, '%s.exe'). Read, not run:
        # the first run on Windows is the CI's.
        t = install_section()
        for s in ('py -m venv .venv', '.\\.venv\\Scripts\\python.exe -m pip install .', '.\\.venv\\Scripts\\domino-calibrator.exe'):
            with self.subTest('it names', what=s):
                self.assertIn(s, t)
        with self.subTest('no activation script'):
            self.assertNotRegex(t, r'Scripts\\[Aa]ctivate')


class TestPythonFirst(unittest.TestCase):
    def test_k12_the_readme_names_the_python_it_needs_before_the_block(self):
        # the second amendment's (4): pip refuses an older Python only after the venv is made; say it first
        t = install_section()
        low = (pyproject() or {}).get('project', {}).get('requires-python', '')
        want = 'Python %s or newer' % low.lstrip('>=')
        with self.subTest('requires-python is a minimum', value=low):
            self.assertRegex(low, r'^>=\d+\.\d+$')
        with self.subTest('the README says it, before the block', words=want):
            self.assertIn(want, t)
            if want in t and '```' in t:
                self.assertLess(t.index(want), t.index('```'))


class TestRunningVersions(unittest.TestCase):
    def test_k13_the_running_versions_against_the_record(self):
        # the thirteenth room (the issue list's entry 2): K5, K7, K6, K8 and W4 read the record, and the running versions
        # are compared with it here only: equal in the job that runs the tested versions (FLAG set to 1: the CI's tested
        # job, the Castle's own runs), at least the record anywhere else (the minimums pip holds an install to)
        running = dict(KIT, Python=PY)
        tested_job = os.environ.get(FLAG) == '1'
        names = ('Python', 'numpy', 'scipy', 'astropy')
        print('\n    [%s] running: %s | the record: %s' % (
            'the tested-versions job' if tested_job else 'not the tested-versions job',
            ', '.join('%s %s' % (k, running[k]) for k in names), ', '.join('%s %s' % (k, RECORD.get(k)) for k in names)))
        with self.subTest('the record, from pyproject.toml'):
            self.assertEqual(sorted(RECORD), sorted(names))
        for k in names:
            if k not in RECORD:
                continue
            with self.subTest(k, job='the tested versions' if tested_job else 'any other'):
                if tested_job:
                    self.assertEqual(running[k], RECORD[k])
                else:
                    self.assertGreaterEqual(Version(running[k]), Version(RECORD[k]))


class TestEscapes(unittest.TestCase):
    def test_k14_every_python_file_compiles_with_warnings_as_errors(self):
        # the thirteenth room, step 2 (his yes: [his words, not quoted in public]): step 1 found an invalid escape in this file's docstring, a
        # SyntaxWarning from Python 3.12 on that "will not work in the future", and on 3.11 a DeprecationWarning nobody sees;
        # every .py in the folder that goes public compiles here with both as errors, on every Python the CI runs
        files = sorted(glob.glob(os.path.join(PKG, '**', '*.py'), recursive=True))
        bad = []
        for f in files:
            with warnings.catch_warnings():
                warnings.simplefilter('error', SyntaxWarning)
                warnings.simplefilter('error', DeprecationWarning)
                try:
                    compile(read(f), f, 'exec')
                except SyntaxError as e:
                    bad.append('%s:%s %s' % (os.path.relpath(f, PKG), e.lineno, e.msg))
        with self.subTest('the files, found'):
            self.assertGreater(len(files), 40)
        with self.subTest('none fails'):
            self.assertEqual(bad, [])


if __name__ == '__main__':
    unittest.main()
