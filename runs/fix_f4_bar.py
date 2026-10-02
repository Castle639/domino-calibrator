#!/usr/bin/env python3
"""The fix room's F4 bar: the public tree (1 Oct 2026; the fix room's record of 1 Oct 2026, not in this repository, the launch room's
should-fixes 18, 22, 27, 32, 33, 34, 35 and 36, with his answers). Committed before it runs: red on the tree as F3 left it,
its folder built by the curation as it stood, green after the fix. Its suite cases are tests/test_fix_f4.py. Its folder cases
build the public folder with the recipe they are given, in the scratchpad, never in release/. It names no string it looks for
in the folder: the placeholders, the machine paths and item 18's lists come from CHECKS, a file kept outside the folder,
whose content the room's report records.

  python runs/fix_f4_bar.py LOG SCRATCH CURATE DECISIONS CHECKS     from calibrator/, with ADES_PYLIB, ADES_MASTER and
                                                                    PLAYWRIGHT_MODULE set

  Q0  the controls, run first: each folder case finds its own fault, planted in a copy of the folder built (a placeholder in
      a runs/ log; a machine path in a record; an executable line of a runs/ script changed, while a changed comment and
      docstring pass), and fails on the Castle's own originals (the arcsec record unmarked; fetch_frames.py's examples on the
      public checksum list; psfkit.py's self-test, which reads a private file); the sdist case finds tests/ in an sdist built
      without MANIFEST.in; the workflow cases fail on a planted workflow (a push trigger, id-token for the whole workflow)
  Q1-Q4  the tests' classes, one per item: F4_32_Sdist, F4_33_PyPI, F4_35_Publish, F4_36_RunsReadme
  Q5  item 18: in the folder, no placeholder; none of CHECKS' files to leave out, every one of its files to keep; psfkit.py's
      self-test, without its inputs, says what it needs and exits 2, no traceback
  Q6  item 22: fetch_frames.py's docstring: each of its examples selects frames of the folder's checksum list (exit 0, the
      fetch itself stubbed); its exit line names PRESENT; none of CHECKS' private phrases
  Q7  item 27: the arcsec record in the folder, its three lines of advice kept and marked withdrawn until an outside check,
      the mark right before them
  Q8  item 34: no machine path in the folder; and the curation changed no executable line: every .py file in the folder
      parses to the same code as its source in the Castle, docstrings and comments aside, but CHECKS' named stand-ins
  Q9  the whole suite, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
A clause's class passes only when its tests ran and none failed, erred or was skipped.

Amendment 1 (1 of 2), before any green run: CHECKS' machine paths are the audit's C7.4 list again, with each session id's
last twelve digits (the room's report, section 8).
Amendment 2 (2 of 2), before any green run, at his word (1 Oct 2026, about 14:25 UTC: [his words, not quoted in public]): Q5 also asks that no text file of the folder names a file left out
(its name, whole, with or without its folder and extension), and Q0 plants such a pointer for it to find. CHECKS lists the
three hardening records too (his word) and rename_bar.py among the named stand-ins (its list of instruments names five of
the scripts left out, in code). And tests/test_fix_f4.py's three regexes read the workflow as written: two asked for a newline
before a job's first line, and one for the workflow's permissions as its first line, which no well-formed workflow has.
"""
import os, re, io, sys, ast, json, shutil, hashlib, tempfile, subprocess, unittest, warnings

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # calibrator/
REPO = os.path.dirname(ROOT)
sys.path.insert(0, ROOT)
LOG, SCRATCH, CURATE, DECISIONS, CHECKS = sys.argv[1:6]
CK = json.load(open(CHECKS, encoding='utf-8'))
out = open(LOG, 'w', encoding='utf-8')
CLASSES = ['F4_32_Sdist', 'F4_33_PyPI', 'F4_35_Publish', 'F4_36_RunsReadme']
BINARY = ('.png', '.woff2', '.gz', '.fits', '.npz', '.ico', '.pdf', '.svg')
ADVICE = '- **The advice, three lines, for a 3I-like coma**'
WITHDRAWN = re.compile(r'(?i)withdrawn until an outside check')
BAD_WORKFLOW = """name: publish
on:
  push:
  release:
    types: [published]
  workflow_dispatch:
permissions:
  contents: read
  id-token: write
jobs:
  build:
    runs-on: ubuntu-24.04
    steps:
      - run: python -m build
"""


def say(s):
    print(s, flush=True); out.write(s + '\n'); out.flush()


def texts(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d != '.git']
        for f in fn:
            if f.endswith(BINARY):
                continue
            p = os.path.join(dp, f)
            try:
                yield os.path.relpath(p, root), open(p, encoding='utf-8').read()
            except UnicodeDecodeError:
                continue


def count(root, strings):
    """{relpath: occurrences} of any of `strings` in the folder's text files."""
    hits = {}
    for rel, t in texts(root):
        n = sum(t.count(s) for s in strings)
        if n:
            hits[rel] = n
    return hits


def pointers_to(root, stems):
    """{relpath: occurrences} of a left-out file's name (its stem, whole) in the folder's text files (amendment 2)."""
    rx = re.compile(r'(?<![\w-])(?:%s)(?![\w-])' % '|'.join(re.escape(s) for s in sorted(stems, key=len, reverse=True)))
    hits = {}
    for rel, t in texts(root):
        n = len(rx.findall(t))
        if n:
            hits[rel] = n
    return hits


def code(src):
    """The code a .py source parses to, docstrings and comments aside."""
    tree = ast.parse(src)
    for node in ast.walk(tree):
        body = getattr(node, 'body', None)
        if isinstance(body, list) and body and isinstance(body[0], ast.Expr) and isinstance(getattr(body[0], 'value', None), ast.Constant) \
                and isinstance(body[0].value.value, str):
            node.body = body[1:] or [ast.Pass()]
    return ast.dump(tree, include_attributes=False)


def castle_source(rel):
    """The Castle's file a folder file is copied from: calibrator/'s, or the two tools' own."""
    return os.path.join(REPO, rel) if rel.startswith('tools/') else os.path.join(ROOT, rel)


def code_changed(folder):
    """The .py files of the folder whose code differs from their Castle source's (docstrings and comments aside)."""
    bad = []
    for rel, t in texts(folder):
        if not rel.endswith('.py'):
            continue
        src = castle_source(rel)
        if not os.path.exists(src):
            bad.append(rel + ' (no source)')
            continue
        try:
            if code(t) != code(open(src, encoding='utf-8').read()):
                bad.append(rel)
        except SyntaxError as e:
            bad.append('%s (does not parse: %s)' % (rel, e.msg))
    return bad


def psfkit_selftest(path, d):
    """psfkit.py's self-test with nothing it needs: (exit code, its last line, a traceback?)."""
    home = os.path.join(d, 'home'); os.makedirs(home, exist_ok=True)
    e = {k: v for k, v in os.environ.items() if k not in ('PSFKIT_REF', 'TINYTIM')}
    e['HOME'] = home
    c = subprocess.run([sys.executable, path], cwd=d, env=e, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600)
    o = c.stdout + c.stderr
    lines = [l for l in o.splitlines() if l.strip()]
    return c.returncode, (lines[-1] if lines else ''), 'Traceback' in o


def psfkit_ok(path, d):
    """Its verdict and why, in words that hold no path or placeholder (the log goes into runs/, and the folder with it)."""
    rc, last, tb = psfkit_selftest(path, d)
    err = re.match(r'(\w+(?:Error|Exception))\b', last)
    return rc == 2 and not tb and 'needs' in last, 'exit %d, a traceback: %s%s, its last line says what it needs: %s' % (
        rc, tb, ' (%s)' % err.group(1) if err else '', 'needs' in last)


DRIVER = r"""
import sys, re, json, importlib.util
spec = importlib.util.spec_from_file_location('ff', sys.argv[1]); ff = importlib.util.module_from_spec(spec); spec.loader.exec_module(ff)
ff.fetch = lambda name, want, rel: ('PRESENT', 0, 0.0)          # nothing fetched: the selection alone
doc = ff.__doc__
m = re.search(r'e\.g\.\s+(.+)', doc)
examples = [x.split() for x in re.split(r'\s+or\s+', m.group(1).strip())] if m else []
res = []
for ex in examples:
    rc = ff.main(ex)
    res.append([ex, rc])
print(json.dumps({'examples': res, 'exit_line': (re.search(r'Exit 0[^.]*\.', doc) or [''])[0]}))
"""


def fetch_examples(path, folder):
    """fetch_frames.py's docstring examples, run against the folder's checksum list: (all select frames, details)."""
    c = subprocess.run([sys.executable, '-c', DRIVER, path], cwd=folder, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=120)
    try:
        r = json.loads(c.stdout.strip().splitlines()[-1])
    except Exception:
        return False, 'the driver failed (exit %d)' % c.returncode, ''
    ok = bool(r['examples']) and all(rc == 0 for _, rc in r['examples'])
    return ok, ', '.join('%s -> %d' % (' '.join(ex), rc) for ex, rc in r['examples']), r['exit_line']


def advice_marked(path):
    """The arcsec record: its advice kept, three lines, and the withdrawn mark right before it."""
    if not os.path.exists(path):
        return False, 'the record is not in the folder'
    lines = open(path, encoding='utf-8').read().splitlines()
    k = next((i for i, l in enumerate(lines) if l.startswith(ADVICE)), None)
    if k is None:
        return False, 'the advice is not in the record'
    three = [l for l in lines[k + 1:k + 4] if re.match(r'\s+\d\. ', l)]
    marked = k > 0 and bool(WITHDRAWN.search(lines[k - 1]))
    return marked and len(three) == 3, 'the advice at line %d, its three lines kept: %s, the mark right before it: %s' % (
        k + 1, len(three) == 3, marked)


def build(recipe, decisions, dest):
    shutil.rmtree(dest, ignore_errors=True)
    man = dest + '.manifest'
    c = subprocess.run([sys.executable, recipe, REPO, dest, decisions, man], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=1800)
    return c.returncode == 0, c.stdout + c.stderr


def klass(name):
    warnings.simplefilter('ignore')
    suite = unittest.defaultTestLoader.loadTestsFromName('tests.test_fix_f4.' + name)
    res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    faults = []
    for t, tb in res.failures + res.errors:
        last = [l for l in tb.strip().splitlines() if l.strip()][-1]
        faults.append('%s: %s' % (t.id().split('.')[-1], last[:230]))
    faults += ['%s: skipped (%s)' % (t.id().split('.')[-1], why) for t, why in res.skipped]
    return res.wasSuccessful() and not res.skipped and res.testsRun > 0, res.testsRun, faults


def main():
    head = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True).stdout.strip()
    me = hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest()
    t = hashlib.sha256(open(os.path.join(ROOT, 'tests', 'test_fix_f4.py'), 'rb').read()).hexdigest()
    ck = hashlib.sha256(open(CHECKS, 'rb').read()).hexdigest()
    rc_ = hashlib.sha256(open(CURATE, 'rb').read()).hexdigest(); dc = hashlib.sha256(open(DECISIONS, 'rb').read()).hexdigest()
    say('# fix_f4_bar | HEAD %s | its sha256 %s | tests/test_fix_f4.py %s | CHECKS %s | the recipe %s, %s | its decisions %s, %s' % (
        head, me, t, ck[:12], os.path.basename(CURATE), rc_[:12], os.path.basename(DECISIONS), dc[:12]))
    met = []
    work = os.path.join(SCRATCH, 'fix_f4_bar')
    os.makedirs(work, exist_ok=True)
    folder = os.path.join(work, 'folder')
    ok_build, blog = build(CURATE, DECISIONS, folder)
    say('#   the folder built by the recipe: %s (%d files)' % ('yes' if ok_build else 'NO (the recipe failed)',
                                                            sum(len(f) for _, _, f in os.walk(folder)) if ok_build else 0))
    ph, mp = CK['placeholders'], [m['pattern'] for m in CK['machine_paths']]
    stems = [os.path.splitext(os.path.basename(f))[0] for f in CK['leave_out']]           # amendment 2
    d = tempfile.mkdtemp(dir=work)
    try:
        # Q0: the controls
        ctl = {}
        plant = os.path.join(d, 'plant'); shutil.copytree(folder, plant)
        logs = sorted(f for f in os.listdir(os.path.join(plant, 'runs')) if f.endswith('.txt'))
        base_ph, base_mp = sum(count(plant, ph).values()), sum(count(plant, mp).values())
        base_pt = sum(pointers_to(plant, stems).values())
        with open(os.path.join(plant, 'runs', logs[0]), 'a', encoding='utf-8') as f:
            f.write('\n' + ph[0] + '\n')
        with open(os.path.join(plant, 'README.md'), 'a', encoding='utf-8') as f:
            f.write('\n' + mp[0] + 'x\n')
            f.write('\nsee %s\n' % CK['leave_out'][0])                       # amendment 2: a pointer to a file left out
        ctl['a placeholder planted is found'] = sum(count(plant, ph).values()) == base_ph + 1
        ctl['a machine path planted is found'] = sum(count(plant, mp).values()) == base_mp + 1
        ctl['a pointer to a file left out, planted, is found'] = sum(pointers_to(plant, stems).values()) == base_pt + 1
        before = code_changed(plant)
        scripts = sorted(f for f in os.listdir(os.path.join(plant, 'runs')) if f.endswith('.py') and 'runs/' + f not in before)
        target = os.path.join(plant, 'runs', scripts[0])
        src = open(target, encoding='utf-8').read()
        with open(target, 'w', encoding='utf-8') as f:
            f.write(src + '\n# a comment planted\n')
        comment_passes = code_changed(plant) == before
        with open(target, 'w', encoding='utf-8') as f:
            f.write(src + '\n_PLANTED = 1\n')
        ctl['an executable line planted is found, a comment is not'] = comment_passes and 'runs/' + scripts[0] in code_changed(plant)
        ctl['the Castle\'s arcsec record is not marked'] = not advice_marked(os.path.join(REPO, 'archive', 'CALIBRATOR_ARCSEC_2026-09-27.md'))[0]
        own_ff = os.path.join(plant, 'tools', 'fetch_frames_castle.py'); shutil.copy(os.path.join(REPO, 'tools', 'fetch_frames.py'), own_ff)
        ctl["the Castle's fetch_frames.py examples select no frame of the public list"] = not fetch_examples(own_ff, plant)[0]
        own_pk = os.path.join(d, 'psfkit_castle.py'); shutil.copy(os.path.join(REPO, 'tools', 'psfkit.py'), own_pk)
        ctl["the Castle's psfkit.py self-test fails the case"] = not psfkit_ok(own_pk, d)[0]
        import tests.test_fix_f4 as T
        bad_src = os.path.join(d, 'nomanifest', 'checkout')
        shutil.copytree(ROOT, bad_src, ignore=shutil.ignore_patterns('__pycache__', '*.egg-info', 'build', 'dist', 'MANIFEST.in'))
        files, slog = T.sdist_files(bad_src, os.path.join(d, 'nomanifest'))
        ctl['an sdist without MANIFEST.in ships tests/'] = bool(files) and any(f.startswith('tests/') for f in files)
        bad_wf = os.path.join(d, 'publish.yml'); open(bad_wf, 'w', encoding='utf-8').write(BAD_WORKFLOW)
        saved = T.F4_35_Publish.PATH; T.F4_35_Publish.PATH = bad_wf
        try:
            ok_bad, _, _ = klass('F4_35_Publish')
        finally:
            T.F4_35_Publish.PATH = saved
        ctl['the workflow cases fail on a planted workflow'] = not ok_bad
        p0 = ok_build and all(ctl.values())
        say('Q0  %s  %s' % ('PASS' if p0 else 'FAIL', ' | '.join('%s: %s' % (k, v) for k, v in ctl.items())))
        met.append(p0)

        # Q1-Q4: the tests' classes
        for k, name in enumerate(CLASSES, 1):
            ok, n, faults = klass(name)
            say('Q%d  %s  tests.test_fix_f4.%s: %d run%s' % (k, 'PASS' if ok else 'FAIL', name, n,
                                                             '' if ok else ', %d fault%s' % (len(faults), '' if len(faults) == 1 else 's')))
            for f in faults[:5]:
                say('    ' + f)
            met.append(ok)

        # Q5: item 18
        hits = count(folder, ph)
        present = [f for f in CK['leave_out'] if os.path.exists(os.path.join(folder, f))]
        missing = [f for f in CK['keep'] if not os.path.exists(os.path.join(folder, f))]
        pk_ok, pk_why = psfkit_ok(os.path.join(folder, 'tools', 'psfkit.py'), d) if os.path.exists(os.path.join(folder, 'tools', 'psfkit.py')) \
            else (False, 'no tools/psfkit.py')
        pts = pointers_to(folder, stems)                                                    # amendment 2
        q5 = ok_build and not hits and not present and not missing and pk_ok and not pts
        say('Q5  %s  placeholders in the folder: %d in %d files | to leave out, still there: %d of %d | to keep, missing: %d of %d | '
            'psfkit.py\'s self-test: %s | pointers to a file left out: %d in %d files' % (
                'PASS' if q5 else 'FAIL', sum(hits.values()), len(hits), len(present), len(CK['leave_out']), len(missing),
                len(CK['keep']), pk_why, sum(pts.values()), len(pts)))
        for f in sorted(pts)[:6]:
            say('    pointers: %s %d' % (f, pts[f]))
        for f in sorted(hits)[:6]:
            say('    placeholders: %s %d' % (f, hits[f]))
        for f in present[:4] + missing[:4]:
            say('    %s' % f)
        met.append(q5)

        # Q6: item 22
        ff = os.path.join(folder, 'tools', 'fetch_frames.py')
        if os.path.exists(ff):
            ex_ok, ex_why, exit_line = fetch_examples(ff, folder)
            doc = open(ff, encoding='utf-8').read()
            doc = doc[:doc.index('"""', doc.index('"""') + 3)]
            phrases = [p for p in CK['fetch_frames_phrases'] if p in doc]
        else:
            ex_ok, ex_why, exit_line, phrases = False, 'no tools/fetch_frames.py', '', []
        q6 = ex_ok and 'PRESENT' in exit_line and not phrases
        say('Q6  %s  the examples: %s | the exit line names PRESENT: %s | private phrases left: %d of %d' % (
            'PASS' if q6 else 'FAIL', ex_why, 'PRESENT' in exit_line, len(phrases), len(CK['fetch_frames_phrases'])))
        met.append(q6)

        # Q7: item 27
        q7, why7 = advice_marked(os.path.join(folder, 'archive', 'CALIBRATOR_ARCSEC_2026-09-27.md'))
        say('Q7  %s  %s' % ('PASS' if q7 else 'FAIL', why7))
        met.append(q7)

        # Q8: item 34
        paths = count(folder, mp)
        changed = [f for f in code_changed(folder) if f not in CK['code_standins']]
        q8 = ok_build and not paths and not changed
        say('Q8  %s  machine paths in the folder: %d in %d files | .py files whose code the curation changed: %d%s' % (
            'PASS' if q8 else 'FAIL', sum(paths.values()), len(paths), len(changed), (' (%s)' % ', '.join(changed[:6])) if changed else ''))
        met.append(q8)

        # Q9: the whole suite, strict
        e = dict(os.environ, DOMINO_CALIBRATOR_TESTED_VERSIONS='1')
        c = subprocess.run([sys.executable, '-m', 'tests.strict'], cwd=ROOT, env=e, capture_output=True, encoding='utf-8', errors='replace', timeout=5400)
        o = c.stdout + c.stderr
        line = (re.findall(r'^strict: .*$', o, re.M) or ['strict: no verdict'])[-1]
        q9 = c.returncode == 0 and line.startswith('strict: PASS')
        say('Q9  %s  the whole suite: %s' % ('PASS' if q9 else 'FAIL', line))
        if not q9:
            for mm in re.findall(r'^(?:FAIL|ERROR): (\S+) \((\S+)\)', o, re.M)[:12]:
                say('    %s %s' % mm)
        met.append(q9)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    k = sum(met)
    say('# fix f4 bar: %s, %d of %d%s' % ('MET' if k == len(met) else 'NOT MET', k, len(met),
                                         '' if k == len(met) else ' (failing: %s)' % ' '.join('Q%d' % i for i, v in enumerate(met) if not v)))


if __name__ == '__main__':
    main()
