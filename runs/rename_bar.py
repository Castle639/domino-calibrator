#!/usr/bin/env python3
"""Launch step 3's bar: the import rename to domino_calibrator (the launch list's step 3; the issue list's entry 9;
the build room's brief of 30 Sept 2026, not in this repository, section 1). Written before any file of the package moves (30 Sept 2026, the
calibrator's build room), to be run red on calibrator/ as main left it (a23ede6). The layout was read first
(the build room's record of 30 Sept 2026, not in this repository, section 3): the folder stays the repository's root, the package moves inside
it as domino_calibrator/, and the tests stay beside it as tests/, run from inside the checkout whatever it is called. His
words: [his words, not quoted in public].

The clauses:
  R0  control: the name scan finds the old name in each of the eight forms planted in a file, and in none of the four
      planted lines that hold the new name or the word in prose
  R1  the layout: calibrator/domino_calibrator/ holds the ten modules; calibrator/ holds no .py at its top; tests/, page/,
      runs/, pyproject.toml, README.md, LICENSE, CITATION.cff and .github/workflows/tests.yml sit at its top
  R2  the science's bytes: apertures, estimators, shrink, degrade, synth and ades in domino_calibrator/, each with the
      sha256 of its a23ede6 self in calibrator/
  R3  the old name gone: the scan over calibrator/'s .py, .js, .html, .toml, .yml, .cff and .md files finds none. Left out:
      runs/'s logs and raws, and the rooms' instruments in INSTRUMENTS (records of bars already met, and this script)
  R4  the Castle's arrangement: from calibrator/, `python -m tests.strict` on the kit with the tested-versions flag, with the
      frames beside calibrator/ (the Castle's data/hst-3i/): PASS, 0 failures, 0 errors, 0 skipped
  R5  a stranger's arrangement: a copy of calibrator/ in a folder not named calibrator, with the frames inside it
      (data/hst-3i/: the Castle's checksum list copied, the 30 frames linked); the same command from inside it, on the kit
      with the flag: PASS, 0/0/0
  R5m its mutant: the same copy with the checksum list inside and the frames beside it, not inside. The rule keeps to the
      repository's own data/hst-3i/, where there are no frames, so the strict runner FAILS, and every skip it refuses
      names the frames' fetcher
  R6  what pip picks: R4's command from calibrator/ on pick311, pick313 and pick314 (venvs from `pip install` of a copy of
      calibrator/ as main left it, each with the MPC's validator for its Python), without the flag: each PASS, 0/0/0
  R7  installed: a fresh venv made by the kit's Python, `pip install` of a copy of calibrator/ (runs/ left out) with the
      tested versions as constraints, and every command run in an empty folder. domino_calibrator imports from the venv;
      `import calibrator` and `import domino_calibrator.hstpsf` both fail; the distribution's top-level names (its RECORD)
      are domino_calibrator alone; the package's installed .py files are its nine modules; `domino-calibrator --version`
      and `python -m domino_calibrator.cli --version` both print "domino-calibrator 0.1.0"
  R8  the CI file: actionlint 1.7.12, with ShellCheck 0.11.0 on its PATH, reports nothing. The checkout's path is not
      calibrator. The run lines include `python -m tests.strict`, `python -m pip install .`, `python tests/readme_install.py`
      and `python tools/fetch_frames.py 22 03 04 05 06`, and none names calibrator/ as a path
Amendment 1, after the red run (a2d7b90): R8 matched its four commands as substrings, and found `python -m pip install .`
inside main's `python -m pip install ./calibrator`. Each command must now stand whole at the start of a run line, followed
by a space or the line's end. Nothing else changes.

The suites run one after another: each one's K6 and K8 install from PyPI, and the brief's W6 asks for one request at a time
per host. The science's own controls (C1 bit for bit, C2 with 0 FITTED and the same 43) run after the green run, outside
this script (W2). R4's suite runs the MPC's judge's tests: the validator is set, and nothing may skip.

Usage: python calibrator/runs/rename_bar.py SCRATCH REPO TESTED_PYTHON [CLAUSES]
  SCRATCH holds pick311/, pick313/, pick314/, pylib/, pylib313/, pylib314/, ades-master/ (IAU ADES-Master at 39ae5a9),
  actionlint/actionlint and shellcheck/bin/shellcheck. REPO is the Castle's root. TESTED_PYTHON is the kit's python.
  CLAUSES, optional: a comma-separated choice of R0-R8 and R5m (all when left out). The suites' full outputs go to
  SCRATCH/rename_bar/, and the report to stdout.
"""
import os, re, sys, json, time, shutil, hashlib, tempfile, subprocess

SCRATCH, REPO, TESTED_PY = sys.argv[1], sys.argv[2], sys.argv[3]
ONLY = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else None
PKG = os.path.join(REPO, 'calibrator')
NEW = os.path.join(PKG, 'domino_calibrator')
OUT = os.path.join(SCRATCH, 'rename_bar')
FLAG = 'DOMINO_CALIBRATOR_TESTED_VERSIONS'
MAIN = 'a23ede6'
MODULES = ['__init__.py', 'ades.py', 'apertures.py', 'cli.py', 'degrade.py', 'estimators.py', 'hst.py', 'hstpsf.py',
           'shrink.py', 'synth.py']
SCIENCE = ['apertures.py', 'estimators.py', 'shrink.py', 'degrade.py', 'synth.py', 'ades.py']
TOP = ['tests', 'page', 'runs', 'pyproject.toml', 'README.md', 'LICENSE', 'CITATION.cff',
       os.path.join('.github', 'workflows', 'tests.yml')]
INSTRUMENTS = ['any_machine.py', 'ci_bar.py', 'hard2_hst_lookup.py', 'hard2_mutants.py', 'hard2_probe.py',
               'hard2_pv_probe.py', 'hard3_lookup_check.py', 'hard3b_mutants.py', 'rel_mutants.py', 'rename_bar.py']
# (and five scripts of the refuter and audit waves, which ran beside these and are not in this repository)
EXT = ('.py', '.js', '.html', '.toml', '.yml', '.cff', '.md')
MODS = 'tests|cli|ades|apertures|degrade|estimators|hst|hstpsf|shrink|synth'
OLD = [('import', re.compile(r'(?<![\w.-])(?:from\s+calibrator(?=[\s.])|import\s+calibrator(?![\w-]))')),
       ('dotted', re.compile(r'(?<![\w/-])calibrator\.(?:%s|__\w+__)\b' % MODS)),
       ('quoted', re.compile(r'''(?<![\w-])['"]calibrator['"]''')),
       ('path', re.compile(r'(?<![\w-])\.?/?calibrator/(?:tests|tools|data|runs|page|(?:__init__|%s)\.py)\b' % MODS)),
       ('ci', re.compile(r'path:\s*calibrator\b|(?<![\w/-])\./calibrator\b'))]
PLANT_HIT = ['from calibrator import shrink', 'import calibrator', 'python -m calibrator.cli image.fits',
             'python -m calibrator.tests.strict', 'domino-calibrator = "calibrator.cli:main"',
             "os.path.join(ROOT, 'calibrator', 'runs')", '          path: calibrator',
             'python -m unittest discover -s calibrator/tests -t .']
PLANT_MISS = ['from domino_calibrator import shrink; python -m domino_calibrator.cli', 'pip install domino-calibrator',
              "the calibrator's eleventh room", 'DOMINO_CALIBRATOR_TESTED_VERSIONS: "1"']
STRICT = re.compile(r'^strict: (PASS|FAIL) \((\d+) run, (\d+) failures, (\d+) errors, (\d+) skipped: (\d+) allowed, (\d+) not\)',
                    re.M)
RESULTS = {}


def verdict(name, ok, detail):
    RESULTS[name] = ok
    print('%-4s %s  %s' % (name, 'PASS' if ok else 'FAIL', detail), flush=True)


def want(name):
    return ONLY is None or name in ONLY


def sha(path):
    with open(path, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def scan_lines(path):
    """The lines of one file where the old name stands, as (line number, form)."""
    out = []
    with open(path, encoding='utf-8', errors='replace') as f:
        for i, line in enumerate(f, 1):
            for form, rx in OLD:
                if rx.search(line):
                    out.append((i, form))
                    break
    return out


def scan_tree(root):
    """Every hit under root, with runs/'s records and the instruments left out."""
    hits = {}
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d not in ('__pycache__', 'fonts', 'node_modules', '.git')]
        for f in fn:
            if not f.endswith(EXT):
                continue
            p = os.path.join(dp, f)
            rel = os.path.relpath(p, root)
            if rel.startswith('runs' + os.sep) and (not f.endswith('.py') or f in INSTRUMENTS):
                continue
            h = scan_lines(p)
            if h:
                hits[rel] = h
    return hits


def env_for(python, pylib, flag):
    e = {k: v for k, v in os.environ.items() if k not in (FLAG, 'PYTHONPATH', 'VIRTUAL_ENV')}
    e.update(ADES_PYLIB=os.path.join(SCRATCH, pylib), ADES_MASTER=os.path.join(SCRATCH, 'ades-master'),
             PLAYWRIGHT_MODULE='/opt/node22/lib/node_modules/playwright',
             PATH=os.path.dirname(python) + os.pathsep + '/opt/node22/bin' + os.pathsep + os.environ.get('PATH', ''))
    if flag:
        e[FLAG] = '1'
    return e


def suite(label, python, cwd, pylib, flag, args=()):
    """`python -m tests.strict` from cwd; returns (parsed summary or None, the full output's path)."""
    os.makedirs(OUT, exist_ok=True)
    log = os.path.join(OUT, 'suite_%s.txt' % label)
    t0 = time.time()
    c = subprocess.run([python, '-m', 'tests.strict'] + list(args), cwd=cwd, env=env_for(python, pylib, flag),
                       stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=5400)
    with open(log, 'w') as f:
        f.write('# %s: %s -m tests.strict in %s, %s UTC, %.0f s, exit %d\n\n' % (
            label, python, cwd, time.strftime('%F %T', time.gmtime(t0)), time.time() - t0, c.returncode) + c.stdout)
    m = STRICT.search(c.stdout)
    s = None if m is None else dict(zip(('verdict', 'run', 'fail', 'err', 'skip', 'allowed', 'not'),
                                        [m.group(1)] + [int(x) for x in m.groups()[1:]]))
    return s, log, c.stdout, c.returncode, time.time() - t0


def summary(s, rc, dt):
    if s is None:
        return 'no strict summary (exit %d, %.0f s)' % (rc, dt)
    return '%s: %d run, %d failures, %d errors, %d skipped (%d not allowed); exit %d; %.0f s' % (
        s['verdict'], s['run'], s['fail'], s['err'], s['skip'], s['not'], rc, dt)


def green(s, rc):
    return s is not None and s['verdict'] == 'PASS' and rc == 0 and s['fail'] == 0 and s['err'] == 0 and s['skip'] == 0 \
        and s['run'] > 0


def stranger_copy(name, frames_inside):
    """A copy of calibrator/ at OUT/stranger_<name>/not-calibrator/ with the checksum list inside it, and the 30 frames
    linked inside it (frames_inside) or beside it, in the parent's data/hst-3i/."""
    base = os.path.join(OUT, 'stranger_' + name)
    shutil.rmtree(base, ignore_errors=True)
    dst = os.path.join(base, 'not-calibrator')
    shutil.copytree(PKG, dst, ignore=shutil.ignore_patterns('__pycache__', '*.egg-info', 'build', '.venv'))
    data = os.path.join(dst, 'data', 'hst-3i')
    os.makedirs(data)
    shutil.copy(os.path.join(REPO, 'data', 'hst-3i', 'CHECKSUMS.sha256'), data)
    where = data if frames_inside else os.path.join(base, 'data', 'hst-3i')
    os.makedirs(where, exist_ok=True)
    frames = sorted(f for f in os.listdir(os.path.join(REPO, 'data', 'hst-3i')) if f.endswith('_flc.fits'))
    for f in frames:
        os.symlink(os.path.join(REPO, 'data', 'hst-3i', f), os.path.join(where, f))
    return dst, len(frames)


def main():
    print('# rename bar %s UTC | HEAD %s | tree %s' % (
        time.strftime('%F %T', time.gmtime()), subprocess.run(['git', '-C', REPO, 'log', '-1', '--format=%h'],
                                                              capture_output=True, text=True).stdout.strip(),
        'clean' if not subprocess.run(['git', '-C', REPO, 'status', '--short', '--', 'calibrator'], capture_output=True,
                                      text=True).stdout.strip() else 'MODIFIED under calibrator/'), flush=True)

    if want('R0'):
        d = tempfile.mkdtemp(prefix='rename_r0_')
        p = os.path.join(d, 'plant.py')
        with open(p, 'w') as f:
            f.write('\n'.join(PLANT_HIT + PLANT_MISS) + '\n')
        got = scan_lines(p)
        hit = sorted(i for i, _ in got)
        ok = hit == list(range(1, len(PLANT_HIT) + 1))
        verdict('R0', ok, 'planted old forms hit %d of %d; new-name and prose lines hit %d of %d; forms seen: %s' % (
            sum(1 for i in hit if i <= len(PLANT_HIT)), len(PLANT_HIT), sum(1 for i in hit if i > len(PLANT_HIT)),
            len(PLANT_MISS), ' '.join(sorted({f for _, f in got}))))
        shutil.rmtree(d, ignore_errors=True)

    if want('R1'):
        have = sorted(f for f in os.listdir(NEW) if f.endswith('.py')) if os.path.isdir(NEW) else []
        top_py = sorted(f for f in os.listdir(PKG) if f.endswith('.py'))
        missing = [t for t in TOP if not os.path.exists(os.path.join(PKG, t))]
        ok = have == sorted(MODULES) and not top_py and not missing
        verdict('R1', ok, 'domino_calibrator/: %d of 10 modules%s | .py at the top: %d%s | missing at the top: %s' % (
            len(set(have) & set(MODULES)), (' (others: %s)' % ' '.join(sorted(set(have) - set(MODULES)))) if set(have) - set(MODULES) else '',
            len(top_py), (' (%s)' % ' '.join(top_py[:6])) if top_py else '', ' '.join(missing) or 'none'))

    if want('R2'):
        rows, ok = [], True
        for m in SCIENCE:
            old = subprocess.run(['git', '-C', REPO, 'show', '%s:calibrator/%s' % (MAIN, m)], capture_output=True).stdout
            p = os.path.join(NEW, m)
            now = sha(p) if os.path.exists(p) else None
            same = now is not None and now == hashlib.sha256(old).hexdigest()
            ok = ok and same and len(old) > 0
            rows.append('%s %s' % (m, 'same' if same else ('absent' if now is None else 'CHANGED')))
        verdict('R2', ok, '; '.join(rows))

    if want('R3'):
        hits = scan_tree(PKG)
        n = sum(len(v) for v in hits.values())
        forms = {}
        for v in hits.values():
            for _, f in v:
                forms[f] = forms.get(f, 0) + 1
        first = sorted(hits.items())[:4]
        verdict('R3', n == 0, '%d lines in %d files%s%s' % (
            n, len(hits), (' | by form: %s' % ' '.join('%s %d' % kv for kv in sorted(forms.items()))) if n else '',
            (' | first: ' + '; '.join('%s:%s' % (r, ','.join(str(i) for i, _ in v[:3])) for r, v in first)) if n else ''))

    if want('R4'):
        s, log, _, rc, dt = suite('R4_castle_kit', TESTED_PY, PKG, 'pylib', True)
        verdict('R4', green(s, rc), '%s | %s' % (summary(s, rc, dt), os.path.relpath(log, SCRATCH)))

    if want('R5'):
        dst, nf = stranger_copy('R5', True)
        s, log, _, rc, dt = suite('R5_stranger_kit', TESTED_PY, dst, 'pylib', True)
        verdict('R5', green(s, rc), 'the copy %s, %d frames linked inside | %s | %s' % (
            os.path.relpath(dst, SCRATCH), nf, summary(s, rc, dt), os.path.relpath(log, SCRATCH)))

    if want('R5m'):
        dst, nf = stranger_copy('R5m', False)
        s, log, out, rc, dt = suite('R5m_frames_beside', TESTED_PY, dst, 'pylib', True)
        refused = re.findall(r'^skipped, NOT allowed: (.+?): (.*)$', out, flags=re.M)
        named = [t for t, why in refused if 'fetch_frames' in why]
        ok = s is not None and s['verdict'] == 'FAIL' and rc != 0 and s['fail'] == 0 and s['err'] == 0 \
            and len(refused) > 0 and len(refused) == s['not'] and len(named) == len(refused)
        verdict('R5m', ok, '%d frames linked beside the copy | %s | refused skips %d, naming the fetcher %d | %s' % (
            nf, summary(s, rc, dt), len(refused), len(named), os.path.relpath(log, SCRATCH)))

    if want('R6'):
        oks, rows = [], []
        for pick, pylib in (('pick311', 'pylib'), ('pick313', 'pylib313'), ('pick314', 'pylib314')):
            py = os.path.join(SCRATCH, pick, 'bin', 'python')
            s, log, _, rc, dt = suite('R6_' + pick, py, PKG, pylib, False)
            oks.append(green(s, rc))
            rows.append('%s %s' % (pick, summary(s, rc, dt)))
        verdict('R6', all(oks), ' | '.join(rows))

    if want('R7'):
        tmp = tempfile.mkdtemp(prefix='rename_r7_', dir=SCRATCH)
        src, venv, run = os.path.join(tmp, 'src', 'checkout'), os.path.join(tmp, 'venv'), os.path.join(tmp, 'run')
        shutil.copytree(PKG, src, ignore=shutil.ignore_patterns('runs', '__pycache__', '*.egg-info', 'build', '.venv'))
        os.makedirs(run)
        con = os.path.join(tmp, 'constraints.txt')
        with open(con, 'w') as f:
            f.write('numpy==2.2.6\nscipy==1.15.3\nastropy==6.1.7\n')
        steps = []
        c = subprocess.run([TESTED_PY, '-m', 'venv', venv], capture_output=True, text=True)
        py = os.path.join(venv, 'bin', 'python')
        c2 = subprocess.run([py, '-m', 'pip', 'install', '--disable-pip-version-check', '-q', src, '-c', con], cwd=run,
                            capture_output=True, text=True, timeout=900)
        installed = c.returncode == 0 and c2.returncode == 0
        steps.append(('pip install', installed, (c.stderr + c2.stdout + c2.stderr)[-300:].strip().replace('\n', ' ')))
        def q(code):
            r = subprocess.run([py, '-c', code], cwd=run, capture_output=True, text=True, timeout=300)
            return r.returncode, (r.stdout + r.stderr).strip()
        rc, where = q('import domino_calibrator; print(domino_calibrator.__file__)')
        steps.append(('domino_calibrator from the venv', rc == 0 and where.startswith(venv), where[-120:]))
        rc, out = q('import calibrator')
        steps.append(('import calibrator fails', rc != 0 and "No module named 'calibrator'" in out, out[-80:]))
        rc, out = q('import domino_calibrator.hstpsf')
        steps.append(('hstpsf not installed', rc != 0 and "No module named 'domino_calibrator.hstpsf'" in out, out[-80:]))
        rc, out = q('import json, importlib.metadata as m; d = m.distribution("domino-calibrator"); '
                    'print(json.dumps([str(f) for f in d.files]))')
        files = json.loads(out) if rc == 0 else []
        tops = sorted({f.split('/')[0] for f in files if not f.startswith('..') and '.dist-info' not in f.split('/')[0]})
        steps.append(('top-level names: domino_calibrator alone', tops == ['domino_calibrator'], ' '.join(tops) or out[-80:]))
        pys = sorted(f.split('/')[1] for f in files if f.startswith('domino_calibrator/') and f.endswith('.py') and f.count('/') == 1)
        steps.append(('the nine modules installed', pys == sorted(set(MODULES) - {'hstpsf.py'}), ' '.join(pys)))
        for cmd in ([os.path.join(venv, 'bin', 'domino-calibrator'), '--version'], [py, '-m', 'domino_calibrator.cli', '--version']):
            r = subprocess.run(cmd, cwd=run, capture_output=True, text=True, timeout=120) if os.path.exists(cmd[0]) else None
            txt = '' if r is None else (r.stdout + r.stderr)
            steps.append(('%s --version' % os.path.basename(cmd[0]) if len(cmd) == 2 else '-m domino_calibrator.cli --version',
                          r is not None and r.returncode == 0 and 'domino-calibrator 0.1.0' in txt, txt.strip().splitlines()[0][:60] if txt.strip() else 'absent'))
        verdict('R7', all(ok for _, ok, _ in steps), ' | '.join('%s: %s (%s)' % (n, 'yes' if ok else 'NO', d) for n, ok, d in steps))
        shutil.rmtree(tmp, ignore_errors=True)

    if want('R8'):
        import yaml
        wf = os.path.join(PKG, '.github', 'workflows', 'tests.yml')
        al = os.path.join(SCRATCH, 'actionlint', 'actionlint')
        e = dict(os.environ, PATH=os.path.join(SCRATCH, 'shellcheck', 'bin') + os.pathsep + os.environ.get('PATH', ''))
        c = subprocess.run([al, '-no-color', wf], capture_output=True, text=True, env=e)
        lint_ok = c.returncode == 0 and not c.stdout.strip()
        w = yaml.safe_load(open(wf)) or {}
        steps = [s for j in (w.get('jobs') or {}).values() for s in (j.get('steps') or [])]
        paths = [str((s.get('with') or {}).get('path', '')) for s in steps if str(s.get('uses', '')).startswith('actions/checkout@')]
        runs = '\n'.join(str(s.get('run', '')) for s in steps)
        need = ['python -m tests.strict', 'python -m pip install .', 'python tests/readme_install.py',
                'python tools/fetch_frames.py 22 03 04 05 06']
        lacking = [n for n in need if not re.search(r'(?m)^\s*%s(?:\s|$)' % re.escape(n), runs)]     # amendment 1
        named = re.findall(r'(?<![\w-])calibrator/', runs)
        ok = lint_ok and paths and all(p.strip('./') != 'calibrator' for p in paths) and not lacking and not named
        verdict('R8', ok, 'actionlint: %s | checkout paths: %s | run lines lacking: %s | naming calibrator/: %d' % (
            'clean' if lint_ok else 'exit %d, %d lines' % (c.returncode, len(c.stdout.splitlines())),
            ', '.join(paths) or 'none', ', '.join(lacking) or 'none', len(named)))

    names = [n for n in ('R0', 'R1', 'R2', 'R3', 'R4', 'R5', 'R5m', 'R6', 'R7', 'R8') if n in RESULTS]
    met = sum(1 for n in names if RESULTS[n])
    print('# rename bar: %s, %d of %d%s' % ('MET' if met == len(names) else 'NOT MET', met, len(names),
                                             '' if met == len(names) else ' (failing: %s)' % ' '.join(n for n in names if not RESULTS[n])))


if __name__ == '__main__':
    main()
