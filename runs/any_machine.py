"""Launch step 1's bar: the tests pass on any machine (the launch list's first inside step; the issue list's entries 2, 3,
5 and 7, and the escape found on Python 3.14; the launch road of 27 Sept 2026, not in this repository, section 7). Written before the
tests change (29 Sept 2026, the calibrator's thirteenth room), to be run red on the calibrator as the twelfth room's pull
request merged it (f05c06d). His words: the bar [his words, not quoted in public]; Python 3.14 inside it, [his words, not quoted in public]; the escape
clause added, [his words, not quoted in public].

Amended after the red run (cdf0cec), at his yes ([his words, not quoted in public]): B0 failed there because this container reaches
PyPI directly (curl without the proxy: HTTP 200 from pypi.org's own address), so the proxy variables pointed at a closed
port cut pip but not the machine. B0 and B1 now cut the network with a fresh network namespace (`unshare -n`, as root):
inside it curl cannot resolve pypi.org. Nothing else changes.

"Any machine" is Python 3.11 to 3.14, with whatever pip picks, on Linux, macOS or Windows. On each, the whole suite ends
with 0 failures and 0 errors; a test that needs something the machine lacks (the frames, Node and Playwright, the MPC's
validator, the network, an Ubuntu system Python) skips and names it. This machine has all of them, so here nothing may
skip. Windows and macOS are the CI's (the launch list's step 2).

The tested versions are recorded once, in pyproject.toml (its minimums; it says they are the versions the suite was run
on). The environment variable DOMINO_CALIBRATOR_TESTED_VERSIONS=1 says "this job runs the tested versions".

The clauses:
  A0  the tested setup runs the record's versions (the Castle's kit; read from it, not assumed)
  A   the whole suite on four setups: 0 failures, 0 errors, 0 skipped; K13 (the running versions against the record) ran;
      K6's tested-versions install shows the record's Python and versions:
        tested   the Castle's kit, the tested-versions flag set
        pick311, pick313, pick314   what `pip install .` picks today on Python 3.11, 3.13 and 3.14
  B0  the cut is real: inside a fresh network namespace (`unshare -n`) neither curl (through the proxy as set, or without
      it) nor pip reaches PyPI; outside it, the control does
  B   the whole suite on the tested setup without what a machine may lack: 0 failures, 0 errors, and every skip names it
        B1  no network: the skipped are K6's and K8's, each naming PyPI
        B2  no MPC validator (ADES_PYLIB and ADES_MASTER unset): every skip names ADES_PYLIB, K6's judge among them
  C   the checks still catch what they are for, on copies of calibrator/ (runs/ without its RAW files):
        C0  control: on the unchanged copy every test below is green (K13 also on pick311 without the flag), and the scan
            of D finds nothing
        M1-M9  each mutant turns each of its tests red (a failure, not an error), or the scan lists its file
  D   every .py under calibrator/, and tools/fetch_frames.py (which the public repository copies), compiles on Python 3.14
      with SyntaxWarning and DeprecationWarning as errors
The science's own controls (C1 bit for bit, C2 with 0 FITTED and the same 43) run after the fix, outside this script.

Usage: python calibrator/runs/any_machine.py SCRATCH REPO TESTED_PYTHON [CLAUSES]
  CLAUSES, optional: a comma-separated choice of A0, A, B0, B1, B2, C, D (all when left out).
  SCRATCH holds pick311/, pick313/ and pick314/ (venvs from `pip install .`), pylib/, pylib313/ and pylib314/ (the MPC's
  validator for each Python), ades-master/ (IAU ADES-Master at 39ae5a9); REPO is the Castle's root; TESTED_PYTHON is the
  kit's python. The suites' full outputs go to SCRATCH/any_bar/; the report to stdout.
"""
import os, re, sys, glob, json, time, shutil, tomllib, subprocess, concurrent.futures

SCRATCH, REPO, TESTED_PY = sys.argv[1], sys.argv[2], sys.argv[3]
PKG = os.path.join(REPO, 'calibrator')
OUT = os.path.join(SCRATCH, 'any_bar')
FLAG = 'DOMINO_CALIBRATOR_TESTED_VERSIONS'
PW = '/opt/node22/lib/node_modules/playwright'
NETNS = ['unshare', '-n']                                # a fresh network namespace: no route out, no name lookup
ONLY = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else None
SETUPS = {'tested': (TESTED_PY, 'pylib', True),
          'pick311': (os.path.join(SCRATCH, 'pick311', 'bin', 'python'), 'pylib', False),
          'pick313': (os.path.join(SCRATCH, 'pick313', 'bin', 'python'), 'pylib313', False),
          'pick314': (os.path.join(SCRATCH, 'pick314', 'bin', 'python'), 'pylib314', False)}
T = 'calibrator.tests.'
K5 = T + 'test_release_package.TestPyproject.test_k5_pyproject_the_name_the_tested_minimums_and_hstpsf_left_out'
K7 = T + 'test_release_package.TestCI.test_k7_the_ci_runs_what_the_green_run_runs'
K13 = T + 'test_release_package.TestRunningVersions.test_k13_the_running_versions_against_the_record'
W4 = T + 'test_release_words.TestEveryNumber.test_w4_every_other_number_is_registered_and_true'
T18 = T + 'test_hardening_3b.TestTheGuard3b.test_t1_8_the_scatter_is_pinned'
T03 = T + 'test_hardening.TestFailureContract.test_03_G_amplitude_must_be_positive'
MUTANTS = {       # name: (file in calibrator/, old text (exactly once), new text, setup, flag, tests; or 'scan')
    'M1': ('README.md', 'numpy 2.2.6', 'numpy 2.2.7', 'tested', True, [K5, W4]),
    'M2': ('.github/workflows/tests.yml', 'numpy==2.2.6', 'numpy==2.2.7', 'tested', True, [K7]),
    'M3': ('.github/workflows/tests.yml', 'python-version: "3.11"', 'python-version: "3.12"', 'tested', True, [K7]),
    'M4': ('pyproject.toml', '"numpy>=2.2.6"', '"numpy>=2.2.5"', 'tested', True, [K5, K7, K13]),
    'M5': (None, None, None, 'pick311', True, [K13]),                  # the flag set on a kit that is not the tested one
    'M6': ('cli.py', 'rng = np.random.default_rng(seed)', 'rng = np.random.default_rng(seed + 1)', 'tested', True, [T18]),
    'M7': ('cli.py', 'oo = shrink(img + rng.normal(0.0, sig, img.shape), ',
           'oo = shrink(img + rng.normal(0.0, sig, img.shape[::-1]).T, ', 'tested', True, [T18]),
    'M8': ('estimators.py', 'if not q[0] > 0:', 'if False:', 'tested', True, [T03]),   # a dip accepted as a source
    'M9': ('__init__.py', '"""calibrator - open', '"""\\d calibrator - open', None, None, 'scan'),   # an invalid escape
}
DESCRIBE = {'M1': "the README's tested numpy changed", 'M2': "the CI's numpy pin changed",
            'M3': "the CI's Python changed", 'M4': "pyproject's numpy minimum changed alone",
            'M5': 'the tested-versions flag set on what pip picks on 3.11', 'M6': "the scatter's generator seeded one off",
            'M7': 'each noise redraw laid down transposed', 'M8': "G's amplitude check removed",
            'M9': "an invalid escape in __init__.py's docstring"}
RESULTS = []


def say(*a):
    print(*a, flush=True)


def verdict(name, ok, evidence):
    RESULTS.append((name, ok))
    say('%-10s %s  %s' % (name, 'PASS' if ok else 'FAIL', evidence))


def record():
    """The tested versions, as pyproject.toml records them."""
    with open(os.path.join(PKG, 'pyproject.toml'), 'rb') as f:
        proj = tomllib.load(f)['project']
    rec = {'Python': re.fullmatch(r'>=(\d+\.\d+)', proj['requires-python']).group(1)}
    for d in proj['dependencies']:
        n, v = re.fullmatch(r'([A-Za-z0-9_.-]+)>=([\w.]+)', d).groups()
        rec[n] = v
    return rec


def kit(py):
    c = subprocess.run([py, '-c', 'import sys, numpy, scipy, astropy; print("%d.%d.%d" % sys.version_info[:3], numpy.__version__,'
                        ' scipy.__version__, astropy.__version__)'], capture_output=True, text=True)
    v = c.stdout.split()
    return dict(zip(('Python', 'numpy', 'scipy', 'astropy'), v)) if len(v) == 4 else {'error': c.stderr[-300:]}


def env_for(lib, flag, drop=(), extra=None):
    e = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'VIRTUAL_ENV', FLAG)}
    e.update(PYTHONDONTWRITEBYTECODE='1', PYTHONUNBUFFERED='1', PLAYWRIGHT_MODULE=PW,
             ADES_MASTER=os.path.join(SCRATCH, 'ades-master'), ADES_PYLIB=os.path.join(SCRATCH, lib))
    if flag:
        e[FLAG] = '1'
    for k in drop:
        e.pop(k, None)
    e.update(extra or {})
    return e


def want(clause):
    return ONLY is None or clause in ONLY


def suite(name, py, env, prefix=()):
    t0 = time.time()
    c = subprocess.run(list(prefix) + [py, '-m', 'unittest', 'discover', '-s', 'calibrator/tests', '-t', '.', '-v'], cwd=REPO,
                       env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=3600)
    out = c.stdout
    with open(os.path.join(OUT, name + '.txt'), 'w') as f:
        f.write('# %s: %s%s, %s UTC, %.0f s\n\n' % (name, ' '.join(prefix) + ' ' if prefix else '', py,
                                                     time.strftime('%F %T', time.gmtime(t0)), time.time() - t0) + out)
    ran = re.findall(r'^Ran (\d+) tests? in', out, flags=re.M)
    tail = re.findall(r'^(OK|FAILED)(?: \((.*)\))?$', out, flags=re.M)
    counts = {'failures': 0, 'errors': 0, 'skipped': 0, 'expected failures': 0, 'unexpected successes': 0}
    if tail:
        for part in (tail[-1][1] or '').split(', '):
            if '=' in part:
                k, v = part.split('=')
                counts[k] = int(v)
    skips = [(a, r) for a, _, r in re.findall(r"^\s*(\S+)[^\n]*? \.\.\. skipped (['\"])(.*)\2$", out, flags=re.M)]
    skips += [('(after its own output)', r) for _, r in re.findall(r"^skipped (['\"])(.*)\1$", out, flags=re.M)]
    return dict(ran=int(ran[-1]) if ran else None, done=bool(tail), counts=counts, skips=skips, out=out,
                seconds=time.time() - t0)


def fmt(s):
    c = s['counts']
    return 'ran %s, failures %d, errors %d, skipped %d (%.0f s)' % (s['ran'], c['failures'], c['errors'], c['skipped'], s['seconds'])


def tested_leg(out):
    """K6's line for its tested-versions install: the Python it ran on and the versions it installed."""
    m = re.search(r'\[the tested versions\] installed: Python (\S+) \| domino-calibrator \S+ \| numpy scipy astropy: (\S+) (\S+) (\S+)', out)
    return m.groups() if m else None


def scan(py, roots):
    """Every .py under roots compiled by py with SyntaxWarning and DeprecationWarning as errors: the files that fail."""
    code = ('import sys, glob, os, warnings\nbad = []\n'
            'files = sorted(set(f for r in sys.argv[1:] for f in ([r] if r.endswith(".py") else glob.glob(os.path.join(r, "**", "*.py"), recursive=True))))\n'
            'for f in files:\n'
            '    with warnings.catch_warnings():\n'
            '        warnings.simplefilter("error", SyntaxWarning); warnings.simplefilter("error", DeprecationWarning)\n'
            '        try:\n'
            '            compile(open(f, encoding="utf-8").read(), f, "exec")\n'
            '        except SyntaxError as e:\n'
            '            bad.append("%s:%s %s" % (f, e.lineno, e.msg))\n'
            'print(len(files))\nfor b in bad: print(b)\n')
    c = subprocess.run([py, '-c', code] + roots, capture_output=True, text=True)
    lines = c.stdout.strip().splitlines()
    return (int(lines[0]) if lines else 0), lines[1:], c.stderr.strip()[-300:]


def copy_pkg(dest):
    shutil.copytree(PKG, os.path.join(dest, 'calibrator'), ignore=shutil.ignore_patterns('__pycache__', '*RAW*', '*.egg-info', 'build'))
    return os.path.join(dest, 'calibrator')


def one_test(py, env, cwd, test_id):
    c = subprocess.run([py, '-m', 'unittest', test_id], cwd=cwd, env=env, capture_output=True, text=True, timeout=900)
    out = c.stdout + c.stderr
    tail = re.findall(r'^(OK|FAILED)(?: \((.*)\))?$', out, flags=re.M)
    f = int((re.search(r'failures=(\d+)', tail[-1][1] or '') or [0, 0])[1]) if tail else 0
    e = int((re.search(r'errors=(\d+)', tail[-1][1] or '') or [0, 0])[1]) if tail else 0
    s = int((re.search(r'skipped=(\d+)', tail[-1][1] or '') or [0, 0])[1]) if tail else 0
    state = 'green' if tail and tail[-1][0] == 'OK' and s == 0 else ('red' if f and not e else ('error' if tail else 'no result'))
    return state, out


def main():
    os.makedirs(OUT, exist_ok=True)
    rec = record()
    say('# the bar for launch step 1, %s UTC' % time.strftime('%F %T', time.gmtime()))
    say('# the record (pyproject.toml): %s' % ', '.join('%s %s' % kv for kv in rec.items()))
    kits = {n: kit(p) for n, (p, _, _) in SETUPS.items()}
    for n, k in kits.items():
        say('# %-8s %s' % (n, ', '.join('%s %s' % kv for kv in k.items())))
    say('')

    # A0: the tested setup is the record's
    k = kits['tested']
    if want('A0'):
        verdict('A0', k.get('Python', '').rsplit('.', 1)[0] == rec['Python'] and all(k.get(n) == rec[n] for n in ('numpy', 'scipy', 'astropy')),
            'the tested setup: %s' % k)

    # A: the four setups, two at a time
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        futs = {n: ex.submit(suite, 'A_' + n, p, env_for(lib, flag)) for n, (p, lib, flag) in SETUPS.items() if want('A')}
        res = {n: f.result() for n, f in futs.items()}
    for n, s in res.items():
        leg = tested_leg(s['out'])
        leg_ok = bool(leg) and leg[0].rsplit('.', 1)[0] == rec['Python'] and list(leg[1:]) == [rec['numpy'], rec['scipy'], rec['astropy']]
        k13 = 'test_k13_the_running_versions_against_the_record' in s['out']
        c = s['counts']
        ok = s['done'] and c['failures'] == 0 and c['errors'] == 0 and c['skipped'] == 0 and k13 and leg_ok
        verdict('A.' + n, ok, '%s | K13 ran: %s | K6 tested leg: %s%s' % (
            fmt(s), k13, leg, '' if not s['skips'] else ' | skipped: ' + '; '.join('%s: %s' % (a, b[:70]) for a, b in s['skips'])))

    # B0: the cut is real
    if want('B0'):
        probe = subprocess.run(NETNS + ['curl', '-sS', '-m', '10', '-o', '/dev/null', '-w', '%{http_code}',
                                        'https://pypi.org/simple/pip/'], capture_output=True, text=True)
        bypass = subprocess.run(NETNS + ['curl', '-sS', '-m', '10', '--noproxy', '*', '-o', '/dev/null', '-w', '%{http_code}',
                                         'https://pypi.org/simple/pip/'], capture_output=True, text=True)
        tmpd = os.path.join(OUT, 'probe_dl'); shutil.rmtree(tmpd, ignore_errors=True)
        pip = subprocess.run(NETNS + [TESTED_PY, '-m', 'pip', 'download', '--no-deps', '--retries', '0', '--timeout', '10',
                                      '--disable-pip-version-check', '-q', '-d', tmpd, 'pip'], capture_output=True, text=True)
        live = subprocess.run(['curl', '-sS', '-m', '20', '-o', '/dev/null', '-w', '%{http_code}', 'https://pypi.org/simple/pip/'],
                              capture_output=True, text=True)
        verdict('B0', probe.returncode != 0 and bypass.returncode != 0 and pip.returncode != 0 and live.stdout == '200',
                'inside the namespace: curl through the proxy exit %d (%s), curl without it exit %d (%s), pip download exit %d | '
                'outside, the control: HTTP %s' % (probe.returncode, probe.stderr.strip()[-60:], bypass.returncode,
                                                  bypass.stderr.strip()[-60:], pip.returncode, live.stdout))

    # B1 and B2, side by side
    p, lib, flag = SETUPS['tested']
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as ex:
        f1 = ex.submit(suite, 'B1_no_network', p, env_for(lib, flag), NETNS) if want('B1') else None
        f2 = ex.submit(suite, 'B2_no_validator', p, env_for(lib, flag, drop=('ADES_PYLIB', 'ADES_MASTER'))) if want('B2') else None
        b1, b2 = (f1.result() if f1 else None), (f2.result() if f2 else None)
    if b1:
        report_b1(b1)
    if b2:
        report_b2(b2)
    if want('C'):
        clause_c()
    if want('D'):
        clause_d(kits)
    failed = [n for n, ok in RESULTS if not ok]
    say('')
    say('THE BAR%s: %s (%d of %d clauses pass%s)' % ('' if ONLY is None else ' (only %s)' % ','.join(sorted(ONLY)),
                                                     'MET' if not failed else 'NOT MET', len(RESULTS) - len(failed), len(RESULTS),
                                                     '' if not failed else '; failing: ' + ', '.join(failed)))


def report_b1(b1):
    c = b1['counts']
    names = {a for a, _ in b1['skips']}
    ok = (b1['done'] and c['failures'] == 0 and c['errors'] == 0 and c['skipped'] == len(b1['skips']) > 0
          and all('PyPI' in r for _, r in b1['skips']) and any('test_k6' in a for a in names) and any('test_k8' in a for a in names)
          and all('test_k6' in a or 'test_k8' in a for a in names))
    verdict('B1', ok, 'no network: %s | skipped: %s' % (fmt(b1), '; '.join('%s: %s' % (a, r[:70]) for a, r in b1['skips']) or 'none'))


def report_b2(b2):
    c = b2['counts']
    names = {a for a, _ in b2['skips']}
    ok = (b2['done'] and c['failures'] == 0 and c['errors'] == 0 and c['skipped'] == len(b2['skips']) > 0
          and all('ADES_PYLIB' in r for _, r in b2['skips']) and any('test_k6' in a for a in names))
    verdict('B2', ok, 'no validator: %s | K6 among the skipped: %s | reasons: %s' % (
        fmt(b2), any('test_k6' in a for a in names), sorted({r[:60] for _, r in b2['skips']})))


def clause_c():
    # C: the control copy, then each mutant
    cdir = os.path.join(OUT, 'mutants'); shutil.rmtree(cdir, ignore_errors=True)
    ctrl = os.path.join(cdir, 'control'); copy_pkg(ctrl)
    where = subprocess.run([TESTED_PY, '-c', 'import calibrator, os; print(os.path.dirname(calibrator.__file__))'], cwd=ctrl,
                           env=env_for('pylib', True), capture_output=True, text=True).stdout.strip()
    states = {}
    for tid in (K5, K7, K13, W4, T18, T03):
        states['tested ' + tid.rsplit('.', 1)[1][:8]] = one_test(TESTED_PY, env_for('pylib', True), ctrl, tid)[0]
    states['pick311 (no flag) test_k13'] = one_test(SETUPS['pick311'][0], env_for('pylib', False), ctrl, K13)[0]
    n, bad, err = scan(SETUPS['pick314'][0], [os.path.join(ctrl, 'calibrator')])
    states['scan'] = 'green' if n and not bad and not err else 'red: %s' % (bad or err)
    verdict('C0', where == os.path.join(ctrl, 'calibrator') and all(v == 'green' for v in states.values()),
            'imports the copy: %s | %s' % (where == os.path.join(ctrl, 'calibrator'), '; '.join('%s %s' % kv for kv in states.items())))
    for m, (fname, old, new, setup, flag, tests) in MUTANTS.items():
        d = os.path.join(cdir, m); pkg = copy_pkg(d)
        if fname:
            path = os.path.join(pkg, fname)
            t = open(path, encoding='utf-8').read()
            if t.count(old) != 1:
                verdict(m, False, '%s: the mutation text occurs %d times in %s' % (DESCRIBE[m], t.count(old), fname))
                continue
            open(path, 'w', encoding='utf-8').write(t.replace(old, new))
        if tests == 'scan':
            n, bad, err = scan(SETUPS['pick314'][0], [pkg])
            verdict(m, any(b.startswith(os.path.join(pkg, fname) + ':') for b in bad), '%s: the scan lists %s' % (DESCRIBE[m], bad or err))
            continue
        p, lib, _ = SETUPS[setup]
        got = {tid.rsplit('.', 1)[1][:8]: one_test(p, env_for(lib, flag), d, tid)[0] for tid in tests}
        verdict(m, all(v == 'red' for v in got.values()), '%s (%s%s): %s' % (
            DESCRIBE[m], setup, ', the flag set' if flag else '', ', '.join('%s %s' % kv for kv in got.items())))



def clause_d(kits):
    # D: the escape scan on 3.14, over the real folder
    n, bad, err = scan(SETUPS['pick314'][0], [PKG, os.path.join(REPO, 'tools', 'fetch_frames.py')])
    verdict('D', n > 0 and not bad and not err, '%d files compiled on %s | failing: %s' % (
        n, kits['pick314'].get('Python'), bad or err or 'none'))


if __name__ == '__main__':
    main()
