"""Launch step 2's bar: the CI for three systems (the launch list's step 2; the issue list's entry 6;
the launch road of 27 Sept 2026, not in this repository, section 7). Written before the CI file and its helpers change (29 Sept 2026, the
calibrator's thirteenth room), to be run red on the calibrator as step 1 left it (c94c531). His words: Linux's picks on all
four Pythons, [his words, not quoted in public]; Windows and macOS on every push, [his words, not quoted in public]; K14, [his words, not quoted in public].

The workflow cannot run here: its first run is his key (the launch list's step 9). Read at source for it, 29 Sept 2026:
GitHub's runner images (ubuntu-24.04, windows-2025, macos-26: Python 3.11 and 3.14 in each tool cache; Ubuntu's
python3-venv); Node 20 no longer on GitHub's runners from 23 Sept 2026 (GitHub's changelog); the actions' newest majors,
checkout v7, setup-python v7, setup-node v7, cache v6, each on Node 24; setup-python puts every version it is given on the
PATH, the last as the default. This bar checks what this machine can, each clause with a control:
  W1  actionlint 1.7.12, with ShellCheck 0.11.0 on its PATH, finds nothing in the workflow; control: a planted fault is found
  W2  every action the workflow uses runs on Node 24 at the ref it names (its action.yml at that ref, read at source)
  W3  K7 passes on the workflow, and turns red on each workflow mutant:
        wm1  the tested-versions flag off the tested job          wm6  checkout back on its Node 20 major (v4)
        wm2  a skip allowed on a Linux job                        wm7  the README's install lines no longer run
        wm3  Windows gone from the matrix                         wm8  the picks job back on plain discovery
        wm4  macOS gone from the matrix                           wm9  Python 3.11 no longer beside the job's Python
        wm5  a Linux Python gone from the matrix                  wm10 a time cap removed
  W4  the strict runner (tests/strict.py) on planted suites: a pass exits 0; an unallowed skip exits 1 and is named; an
      allowed skip exits 0; a failure exits 1
  W5  the README's install as written (tests/readme_install.py): here, on Linux, the block installs and the command answers
      with the version and the credit; its Windows reading is exactly K11's three commands; control: a README whose block
      cannot install makes it exit non-zero
  W6  K14 passes on the calibrator and fails on a copy holding an invalid escape
  W7  the CI's own command, `python -m calibrator.tests.strict`, on the tested setup with the flag and on what pip picks on
      3.14: exit 0, nothing skipped
  W8  step 1's bar (runs/any_machine.py) still met, 19 of 19
Usage: python calibrator/runs/ci_bar.py SCRATCH REPO TESTED_PYTHON [CLAUSES]
  SCRATCH as for any_machine.py, plus actionlint/actionlint and shellcheck/bin/shellcheck; CLAUSES, optional, a
  comma-separated choice of W1-W8 (all when left out).
"""
import os, re, sys, glob, time, shutil, subprocess, tempfile, concurrent.futures
import yaml

SCRATCH, REPO, TESTED_PY = sys.argv[1], sys.argv[2], sys.argv[3]
ONLY = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else None
PKG = os.path.join(REPO, 'calibrator')
WF = os.path.join('.github', 'workflows', 'tests.yml')
OUT = os.path.join(SCRATCH, 'ci_bar')
ACTIONLINT = os.path.join(SCRATCH, 'actionlint', 'actionlint')
SHELLCHECK_DIR = os.path.join(SCRATCH, 'shellcheck', 'bin')
PICK314 = os.path.join(SCRATCH, 'pick314', 'bin', 'python')
FLAG = 'DOMINO_CALIBRATOR_TESTED_VERSIONS'
PW = '/opt/node22/lib/node_modules/playwright'
T = 'calibrator.tests.'
K7 = T + 'test_release_package.TestCI.test_k7_the_ci_runs_what_the_green_run_runs'
K14 = T + 'test_release_package.TestEscapes.test_k14_every_python_file_compiles_with_warnings_as_errors'
K11_WINDOWS = ['py -m venv .venv', '.\\.venv\\Scripts\\python.exe -m pip install .', '.\\.venv\\Scripts\\domino-calibrator.exe']
CREDIT = "A Castle product from Domino Observatory. Built by Annie, the Castle's AI."
# the workflow mutants: (old text, new text, how many times old occurs)
WM = {
    'wm1': ('DOMINO_CALIBRATOR_TESTED_VERSIONS: "1"', 'DOMINO_CALIBRATOR_SOMETHING_ELSE: "1"', 1),
    'wm2': ('- { os: ubuntu-24.04, python: "3.14" }', '- { os: ubuntu-24.04, python: "3.14", may_skip: "--may-skip test_k8_" }', 1),
    'wm3': ('          - { os: windows-2025, python: "3.14", may_skip: "--may-skip test_k8_ --may-skip test_k10_" }\n', '', 1),
    'wm4': ('          - { os: macos-26, python: "3.14", may_skip: "--may-skip test_k8_ --may-skip test_k10_" }\n', '', 1),
    'wm5': ('          - { os: ubuntu-24.04, python: "3.12" }\n', '', 1),
    'wm6': ('actions/checkout@v7', 'actions/checkout@v4', 2),
    'wm7': ('run: python calibrator/tests/readme_install.py', 'run: echo the README is not run', 1),
    'wm8': ('run: python -m calibrator.tests.strict ${{ matrix.may_skip }}', 'run: python -m unittest discover -s calibrator/tests -t .', 1),
    'wm9': ('          python-version: |\n            3.11\n            ${{ matrix.python }}\n',
            '          python-version: ${{ matrix.python }}\n', 1),
    'wm10': ('    timeout-minutes: 60\n', '', 2),
}
RESULTS = []


def say(*a):
    print(*a, flush=True)


def want(c):
    return ONLY is None or c in ONLY


def verdict(name, ok, evidence):
    RESULTS.append((name, ok))
    say('%-5s %s  %s' % (name, 'PASS' if ok else 'FAIL', evidence))


def env_for(lib='pylib', flag=False, extra=None):
    e = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'VIRTUAL_ENV', FLAG)}
    e.update(PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1', PLAYWRIGHT_MODULE=PW,
             ADES_MASTER=os.path.join(SCRATCH, 'ades-master'), ADES_PYLIB=os.path.join(SCRATCH, lib))
    if flag:
        e[FLAG] = '1'
    e.update(extra or {})
    return e


def copy_pkg(dest):
    shutil.copytree(PKG, os.path.join(dest, 'calibrator'), ignore=shutil.ignore_patterns('__pycache__', '*RAW*', '*.egg-info', 'build'))
    return os.path.join(dest, 'calibrator')


def one_test(py, env, cwd, test_id):
    c = subprocess.run([py, '-m', 'unittest', test_id], cwd=cwd, env=env, capture_output=True, text=True, timeout=900)
    out = c.stdout + c.stderr
    tail = re.findall(r'^(OK|FAILED)(?: \((.*)\))?$', out, flags=re.M)
    cnt = lambda k: int((re.search(k + r'=(\d+)', tail[-1][1] or '') or [0, 0])[1]) if tail else 0
    f, e, s = cnt('failures'), cnt('errors'), cnt('skipped')
    return ('green' if tail and tail[-1][0] == 'OK' and s == 0 else ('red' if f and not e else ('error' if tail else 'no result'))), out


def uses_of(text):
    return re.findall(r'^\s*(?:-\s+)?uses:\s*(\S+)', text, flags=re.M)


def w1():
    wf = os.path.join(PKG, WF)
    env = dict(os.environ, PATH=SHELLCHECK_DIR + os.pathsep + os.environ.get('PATH', ''))
    sc = subprocess.run(['shellcheck', '--version'], env=env, capture_output=True, text=True).stdout.split('\n')[1:2]
    c = subprocess.run([ACTIONLINT, '-no-color', wf], cwd=PKG, env=env, capture_output=True, text=True)
    found = (c.stdout + c.stderr).strip()
    tmp = tempfile.mkdtemp(prefix='al_'); os.makedirs(os.path.join(tmp, '.github', 'workflows'))
    planted = open(wf, encoding='utf-8').read().replace('runs-on:', 'runs-onn:', 1)
    open(os.path.join(tmp, WF), 'w', encoding='utf-8').write(planted)
    ctl = subprocess.run([ACTIONLINT, '-no-color', os.path.join(tmp, WF)], cwd=tmp, env=env, capture_output=True, text=True)
    shutil.rmtree(tmp, ignore_errors=True)
    verdict('W1', c.returncode == 0 and not found and ctl.returncode != 0,
            'actionlint on the workflow: exit %d, %s | ShellCheck %s | control, "runs-on" misspelt: exit %d, %d finding line(s)'
            % (c.returncode, 'nothing found' if not found else found.replace('\n', ' // ')[:600],
               sc[0].strip() if sc else 'NOT FOUND', ctl.returncode, len([l for l in ctl.stdout.splitlines() if ' [' in l])))


def w2():
    text = open(os.path.join(PKG, WF), encoding='utf-8').read()
    seen, bad = {}, []
    for u in sorted(set(uses_of(text))):
        m = re.fullmatch(r'([\w.-]+)/([\w.-]+)@([\w.-]+)', u)
        if not m:
            bad.append('%s: not owner/repo@ref' % u); continue
        using = None
        for name in ('action.yml', 'action.yaml'):
            c = subprocess.run(['curl', '-sS', '-f', '-m', '30', 'https://raw.githubusercontent.com/%s/%s/%s/%s' % (m.group(1), m.group(2), m.group(3), name)],
                               capture_output=True, text=True)
            if c.returncode == 0:
                using = str((yaml.safe_load(c.stdout) or {}).get('runs', {}).get('using'))
                break
        seen[u] = using
        if using not in ('node24', 'composite', 'docker'):
            bad.append('%s runs on %s' % (u, using))
    verdict('W2', bool(seen) and not bad, 'the actions and what they run on: %s%s' % (
        ', '.join('%s %s' % kv for kv in seen.items()), '' if not bad else ' | not Node 24: ' + '; '.join(bad)))


def w3():
    d = os.path.join(OUT, 'wf_mutants'); shutil.rmtree(d, ignore_errors=True)
    ctl = os.path.join(d, 'control'); copy_pkg(ctl)
    state, out = one_test(TESTED_PY, env_for(flag=True), ctl, K7)
    verdict('W3', state == 'green', 'K7 on the workflow as written: %s%s' % (state, '' if state == 'green' else ' | ' + out.strip()[-300:].replace('\n', ' // ')))
    for name, (old, new, n) in WM.items():
        pkg = copy_pkg(os.path.join(d, name))
        path = os.path.join(pkg, WF)
        t = open(path, encoding='utf-8').read()
        if t.count(old) != n:
            verdict('W3.' + name, False, 'the mutation text occurs %d times, not %d: %r' % (t.count(old), n, old[:70])); continue
        open(path, 'w', encoding='utf-8').write(t.replace(old, new))
        state, _ = one_test(TESTED_PY, env_for(flag=True), os.path.join(d, name), K7)
        verdict('W3.' + name, state == 'red', 'K7 on the mutant: %s' % state)


def plant(root, name, body):
    p = os.path.join(root, name); os.makedirs(p)
    open(os.path.join(p, '__init__.py'), 'w').close()
    open(os.path.join(p, 'test_planted.py'), 'w').write('import unittest\n\nclass Planted(unittest.TestCase):\n' + body)
    return p


def w4():
    root = tempfile.mkdtemp(prefix='plant_')
    ok = '    def test_passes(self):\n        pass\n'
    cases = [('a pass alone', plant(root, 'plant_pass', ok), [], 0, None),
             ('an unallowed skip', plant(root, 'plant_skip', ok + "    def test_skips(self):\n        self.skipTest('planted: no tool here')\n"), [], 1, 'test_skips'),
             ('an allowed skip', os.path.join(root, 'plant_skip'), ['--may-skip', 'test_skips'], 0, 'test_skips'),
             ('a failure', plant(root, 'plant_fail', ok + '    def test_fails(self):\n        self.assertEqual(1, 2)\n'), [], 1, None)]
    got = []
    for label, start, args, want_rc, named in cases:
        c = subprocess.run([TESTED_PY, '-m', 'calibrator.tests.strict', '-s', start, '-t', root] + args, cwd=REPO,
                           env=env_for(), capture_output=True, text=True, timeout=300)
        out = c.stdout + c.stderr
        good = c.returncode == want_rc and (named is None or named in out)
        got.append((label, c.returncode, good, out.strip().splitlines()[-1:] if out.strip() else ['(no output)']))
    shutil.rmtree(root, ignore_errors=True)
    verdict('W4', all(g for _, _, g, _ in got), ' | '.join('%s: exit %d%s' % (l, rc, '' if g else ' WRONG (%s)' % last[0][:120])
                                                          for l, rc, g, last in got))


def w5():
    script = os.path.join(PKG, 'tests', 'readme_install.py')
    c = subprocess.run([TESTED_PY, script], cwd=REPO, env=env_for(), capture_output=True, text=True, timeout=1200)
    out = c.stdout + c.stderr
    v = re.search(r"^__version__ = '([^']+)'", open(os.path.join(PKG, '__init__.py'), encoding='utf-8').read(), flags=re.M).group(1)
    squash = re.sub(r'\s+', ' ', out)
    posix_ok = c.returncode == 0 and ('domino-calibrator %s' % v) in out and CREDIT in squash
    p = subprocess.run([TESTED_PY, script, '--print', 'windows'], cwd=REPO, env=env_for(), capture_output=True, text=True, timeout=120)
    win = [l for l in p.stdout.splitlines() if l.strip()]
    d = os.path.join(OUT, 'readme_broken'); shutil.rmtree(d, ignore_errors=True)
    pkg = copy_pkg(d)
    r = open(os.path.join(pkg, 'README.md'), encoding='utf-8').read()
    n = r.count('pip install .\n```')
    open(os.path.join(pkg, 'README.md'), 'w', encoding='utf-8').write(r.replace('pip install .\n```', 'pip install ./no-such-folder\n```'))
    b = subprocess.run([TESTED_PY, os.path.join(pkg, 'tests', 'readme_install.py')], cwd=d, env=env_for(),
                       capture_output=True, text=True, timeout=1200) if os.path.exists(os.path.join(pkg, 'tests', 'readme_install.py')) else None
    verdict('W5', posix_ok and win == K11_WINDOWS and n == 1 and b is not None and b.returncode != 0,
            'here (Linux): exit %d, the answer %s | the Windows reading: %s | control, the block broken (%d place): exit %s'
            % (c.returncode, 'with the version and the credit' if posix_ok else 'WRONG: ' + out.strip()[-300:].replace('\n', ' // '),
               'exactly K11\'s three' if win == K11_WINDOWS else 'WRONG: %r' % win, n, b.returncode if b else 'no script'))


def w6():
    state, out = one_test(TESTED_PY, env_for(flag=True), REPO, K14)
    d = os.path.join(OUT, 'k14_mutant'); shutil.rmtree(d, ignore_errors=True)
    pkg = copy_pkg(d)
    t = open(os.path.join(pkg, '__init__.py'), encoding='utf-8').read()
    open(os.path.join(pkg, '__init__.py'), 'w', encoding='utf-8').write(t.replace('"""calibrator - open', '"""\\d calibrator - open', 1))
    mstate, _ = one_test(TESTED_PY, env_for(flag=True), d, K14)
    verdict('W6', state == 'green' and mstate == 'red', 'K14 on the calibrator: %s | on a copy with an invalid escape: %s%s'
            % (state, mstate, '' if state == 'green' else ' | ' + out.strip()[-200:].replace('\n', ' // ')))


def strict_suite(name, py, env):
    t0 = time.time()
    c = subprocess.run([py, '-m', 'calibrator.tests.strict'], cwd=REPO, env=env, stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, timeout=3600)
    with open(os.path.join(OUT, name + '.txt'), 'w') as f:
        f.write('# %s: %s -m calibrator.tests.strict, %s UTC, %.0f s\n\n' % (name, py, time.strftime('%F %T', time.gmtime(t0)), time.time() - t0) + c.stdout)
    ran = re.findall(r'^Ran (\d+) tests? in', c.stdout, flags=re.M)
    tail = re.findall(r'^(OK|FAILED)(?: \((.*)\))?$', c.stdout, flags=re.M)
    return c.returncode, (ran[-1] if ran else '?'), (tail[-1] if tail else ('?', '')), time.time() - t0


def w7():
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        a = ex.submit(strict_suite, 'W7_tested', TESTED_PY, env_for('pylib', True))
        b = ex.submit(strict_suite, 'W7_pick314', PICK314, env_for('pylib314', False))
        ra, rb = a.result(), b.result()
    fine = lambda r: r[0] == 0 and r[2][0] == 'OK' and 'skipped' not in (r[2][1] or '')
    verdict('W7', fine(ra) and fine(rb), 'the tested setup, the flag set: exit %d, ran %s, %s (%.0f s) | pick314: exit %d, ran %s, %s (%.0f s)'
            % (ra[0], ra[1], ' '.join(x for x in ra[2] if x), ra[3], rb[0], rb[1], ' '.join(x for x in rb[2] if x), rb[3]))


def w8():
    c = subprocess.run([TESTED_PY, os.path.join(PKG, 'runs', 'any_machine.py'), SCRATCH, REPO, TESTED_PY], cwd=REPO,
                       capture_output=True, text=True, timeout=7200)
    with open(os.path.join(OUT, 'W8_any_machine.txt'), 'w') as f:
        f.write(c.stdout + c.stderr)
    last = [l for l in c.stdout.splitlines() if l.startswith('THE BAR')]
    verdict('W8', bool(last) and last[-1].startswith('THE BAR: MET (19 of 19'), last[-1] if last else (c.stdout + c.stderr).strip()[-300:])


def main():
    os.makedirs(OUT, exist_ok=True)
    say('# the bar for launch step 2, %s UTC%s' % (time.strftime('%F %T', time.gmtime()), '' if ONLY is None else ' (only %s)' % ','.join(sorted(ONLY))))
    for n, f in (('W1', w1), ('W2', w2), ('W3', w3), ('W4', w4), ('W5', w5), ('W6', w6), ('W7', w7), ('W8', w8)):
        if want(n):
            try:
                f()
            except Exception as e:                                      # a clause that cannot run has not passed
                verdict(n, False, 'could not run: %s: %s' % (type(e).__name__, str(e)[:300]))
    failed = [n for n, ok in RESULTS if not ok]
    say('')
    say('THE BAR%s: %s (%d of %d clauses pass%s)' % ('' if ONLY is None else ' (only %s)' % ','.join(sorted(ONLY)),
                                                     'MET' if not failed else 'NOT MET', len(RESULTS) - len(failed), len(RESULTS),
                                                     '' if not failed else '; failing: ' + ', '.join(failed)))


if __name__ == '__main__':
    main()
