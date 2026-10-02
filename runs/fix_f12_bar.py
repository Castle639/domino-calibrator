#!/usr/bin/env python3
"""The fix room's F12 bar: the second audit room's should-fixes that are words (1 Oct 2026, his yes to all 27, with his
choices for 21 and 22; in the room's report, section 28): by its report's numbers 1, 3, 4, 5, 6, 11, 20, 21, 22, 24, 25
and 27, in calibrator/. Committed with tests/test_fix_f12.py before it runs. Item 23, and 27's lines in the tools and the
archive, are in files the Castle keeps as written: the public copy's curation carries them, and the release bar checks
them there (F13).

  python runs/fix_f12_bar.py LOG TARGET     from calibrator/, with ADES_PYLIB, ADES_MASTER, PLAYWRIGHT_MODULE
     TARGET: a commit (its calibrator/ is compared with BASE's for V1)

  V0  the controls: the words' standing tests (test_release_words, test_fix_f3, test_fix_f6, test_fix_f10) pass
  V1  the package's code, docstrings aside, is BASE's, file for file (item 21 changes words, never code)
  V2  tests/test_fix_f12.py, in calibrator/
  V3  the whole suite in calibrator/, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
"""
import ast, os, re, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # calibrator/
REPO = os.path.dirname(ROOT)
LOG, TARGET = sys.argv[1:3]
BASE = 'ea49149'                                                         # F11b closed: the package's code before F12
out = open(LOG, 'w', encoding='utf-8')


def say(s):
    print(s, flush=True); out.write(s + '\n'); out.flush()


def run(args, cwd=None, env=None, timeout=5400):
    c = subprocess.run(args, cwd=cwd, capture_output=True, encoding='utf-8', errors='replace', timeout=timeout,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', **(env or {})))
    return c.returncode, c.stdout, c.stderr


def code_of(src):
    """A module's code without its docstrings: the AST, each docstring dropped."""
    t = ast.parse(src)
    for node in ast.walk(t):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and node.body \
                and isinstance(node.body[0], ast.Expr) and isinstance(getattr(node.body[0], 'value', None), ast.Constant) \
                and isinstance(node.body[0].value.value, str):
            node.body = node.body[1:] or [ast.Pass()]
    return ast.dump(t)


def main():
    head = run(['git', '-C', REPO, 'rev-parse', '--short', 'HEAD'])[1].strip()
    tree = run(['git', '-C', REPO, 'rev-parse', '--short', TARGET])[1].strip()
    say('# fix_f12_bar | HEAD %s | TARGET %s (%s) | BASE %s' % (head, TARGET, tree, BASE))
    rc, so, se = run([sys.executable, '-m', 'unittest', 'tests.test_release_words', 'tests.test_fix_f3', 'tests.test_fix_f6',
                      'tests.test_fix_f10'], cwd=ROOT)
    last = ([l for l in se.splitlines() if l.strip()] or ['no output'])[-1]
    v0 = rc == 0
    say('V0 %s  the controls: the standing word tests | %s' % ('PASS' if v0 else 'FAIL', last))
    names = run(['git', '-C', REPO, 'ls-tree', '--name-only', tree + ':calibrator/domino_calibrator'])[1].split()
    diff = []
    for n in sorted(x for x in names if x.endswith('.py')):
        a = run(['git', '-C', REPO, 'show', '%s:calibrator/domino_calibrator/%s' % (BASE, n)])[1]
        b = run(['git', '-C', REPO, 'show', '%s:calibrator/domino_calibrator/%s' % (tree, n)])[1]
        if code_of(a) != code_of(b):
            diff.append(n)
    v1 = not diff and len(names) > 0
    say('V1 %s  the package code, docstrings aside, against %s: %d modules, differing %s' % (
        'PASS' if v1 else 'FAIL', BASE, len([x for x in names if x.endswith('.py')]), diff or 'none'))
    rc, so, se = run([sys.executable, '-m', 'unittest', '-v', 'tests.test_fix_f12'], cwd=ROOT)
    last = ([l for l in se.splitlines() if l.strip()] or ['no output'])[-1]
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', se, re.M)))
    v2 = rc == 0
    say('V2 %s  tests/test_fix_f12.py | %s%s' % ('PASS' if v2 else 'FAIL', last, (' | failing (%d): ' % len(bad) + ', '.join(bad)) if bad else ''))
    rc, so, se = run([sys.executable, '-m', 'tests.strict'], cwd=ROOT, env=dict(DOMINO_CALIBRATOR_TESTED_VERSIONS='1'))
    so = so + se
    line = (re.findall(r'^strict: .*$', so, re.M) or ['strict: no verdict'])[-1]
    v3 = rc == 0 and bool(re.match(r'strict: PASS \(\d+ run, 0 failures, 0 errors, 0 skipped', line))
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', so, re.M)))
    say('V3 %s  %s%s' % ('PASS' if v3 else 'FAIL', line, (' | failing (%d): ' % len(bad) + ', '.join(bad[:16])) if bad else ''))
    met = sum((v0, v1, v2, v3))
    say("# F12's bar on %s: %s, %d of 4" % (TARGET, 'MET' if met == 4 else 'NOT MET', met))
    return 0 if met == 4 else 1


if __name__ == '__main__':
    sys.exit(main())
