#!/usr/bin/env python3
"""The fix room's F6 bar: the CI's first run on the new history, on Windows (1 Oct 2026; his answers on the three findings,
in the room's report, section 16). Committed with tests/test_fix_f6.py before it runs: red on the code and the words as the
second seal left them, green after the fix. It runs in calibrator/, the Castle's own copy, never in release/.

  python runs/fix_f6_bar.py LOG      from calibrator/, with ADES_PYLIB, ADES_MASTER and PLAYWRIGHT_MODULE set

  U0  the controls, run first: the stand-in for Windows's stdout raises OSError EINVAL where the pipe is closed, and F2's
      closed pipe on this system ends quietly (exit 0); the recipe with its quotes plain, as the second seal wrote it, is a
      SyntaxError with C:\\Users\\... and another path with D:\\data\\new\\..., on both faces; the skip scan finds F1's
      raw-bytes test among the tests that skip on Windows
  U1  his answer 1: a closed pipe ends the same way through the stand-in as on this system: no traceback, nothing
      "ignored", the exit code the same (0 a measurement, 2 no comet, 1 cannot measure)
  U2  his answer 2: on both faces, the same recipe; a Windows path typed into its quotes is the path Python opens and
      writes; its words say why, with a Windows path in them
  U3  the recipe still works (F3's test runs it on a frame), the CI's skips still documented with its own values (F3's),
      and the CI as the green run runs it (K7)
  U4  his answer 3: every test that skips on Windows (or macOS) is allowed in that system's row; the raw-bytes skip in the
      Windows row only, and the README says why, with the value the CI uses
  U5  the whole suite, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
"""
import os, re, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # calibrator/
sys.path.insert(0, ROOT)
out = open(sys.argv[1], 'w', encoding='utf-8')
F6 = 'tests.test_fix_f6.'


def say(s):
    print(s, flush=True); out.write(s + '\n'); out.flush()


def tests(*names, env=None, timeout=1800):
    """unittest on the named tests: (all passed, the last line, the failing tests' names)."""
    c = subprocess.run([sys.executable, '-m', 'unittest', '-v'] + list(names), cwd=ROOT, capture_output=True,
                       encoding='utf-8', errors='replace', timeout=timeout, env=env or dict(os.environ))
    lines = [l for l in c.stderr.splitlines() if l.strip()]
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', c.stderr, re.M)))
    return c.returncode == 0, (lines[-1] if lines else 'no output'), bad


def main():
    from tests import test_fix_f6 as T
    say('# fix_f6_bar | HEAD %s' % subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], cwd=ROOT, capture_output=True,
                                                  encoding='utf-8').stdout.strip())
    res = []

    # U0: the controls
    s_ok, s_last, _ = tests(F6 + 'F6_1_ClosedPipeOnWindows.test_the_stand_in_raises_what_windows_raises')
    p_ok, p_last, _ = tests('tests.test_fix_f2.F2_11_ClosedPipe')
    plain = {}
    for face, code in (('README.md', T.readme_recipe()), ('the page', T.page_recipe())):
        old = re.sub(r"\br'(frame|cutout)\.fits'", r"'\1.fits'", code or '')
        a = old.replace('frame.fits', T.WINDOWS_PATHS[0])
        b = old.replace('frame.fits', T.WINDOWS_PATHS[1])
        try:
            T.paths_given(a); syn = False
        except SyntaxError:
            syn = True
        try:
            other = T.paths_given(b)[0] != T.WINDOWS_PATHS[1]
        except SyntaxError:
            other = False
        plain[face] = syn and other
    found = []
    for f in sorted(os.listdir(os.path.join(ROOT, 'tests'))):
        if f.endswith('.py'):
            src = open(os.path.join(ROOT, 'tests', f), encoding='utf-8').read()
            found += [n for c, n in re.findall(r"@unittest\.skip(?:If|Unless)\(([^\n]*)\)\s*\n\s*def (test_\w+)", src)
                      if "os.name == 'nt'" in c]
    scan = T.RAW_BYTES in found
    u0 = s_ok and p_ok and all(plain.values()) and scan
    say("U0 %s  the stand-in raises EINVAL: %s; F2's closed pipe here: %s; the plain-quoted recipe, a SyntaxError and "
        "another path: %s; the scan finds F1's skip on Windows: %s (%d found)" % (
            'PASS' if u0 else 'FAIL', s_ok, p_ok, ', '.join('%s %s' % kv for kv in plain.items()), scan, len(found)))
    res.append(u0)

    for label, names, what in (
            ('U1', [F6 + 'F6_1_ClosedPipeOnWindows.test_a_closed_pipe_ends_the_same_way_on_windows_exit_code_included'],
             'a closed pipe through the stand-in as here, exit codes 0, 2, 1'),
            ('U2', [F6 + 'F6_2_TheRecipeOnWindows'], 'the recipe on both faces, a Windows path typed into it, its words'),
            ('U3', ['tests.test_fix_f3.F3_23_Cutout', 'tests.test_fix_f3.F3_17_MaySkip',
                    'tests.test_release_package.TestCI.test_k7_the_ci_runs_what_the_green_run_runs'],
             "F3's recipe run on a frame, F3's skips documented, K7"),
            ('U4', [F6 + 'F6_3_EachSystemsSkipsAreNamed'], "each system's skips named in its row, the README's why")):
        ok, last, bad = tests(*names)
        say('%s %s  %s | %s%s' % (label, 'PASS' if ok else 'FAIL', what, last, (' | failing: ' + ', '.join(bad)) if bad else ''))
        res.append(ok)

    # U5: the whole suite, strict
    e = dict(os.environ, DOMINO_CALIBRATOR_TESTED_VERSIONS='1')
    c = subprocess.run([sys.executable, '-m', 'tests.strict'], cwd=ROOT, env=e, capture_output=True, encoding='utf-8',
                       errors='replace', timeout=5400)
    o = c.stdout + c.stderr
    line = (re.findall(r'^strict: .*$', o, re.M) or ['strict: no verdict'])[-1]
    m = re.match(r'strict: PASS \((\d+) run, 0 failures, 0 errors, 0 skipped', line)
    u5 = c.returncode == 0 and bool(m)
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', o, re.M)))
    say('U5 %s  %s%s' % ('PASS' if u5 else 'FAIL', line, (' | failing: ' + ', '.join(bad)) if bad else ''))
    res.append(u5)

    met = sum(res)
    say("# F6's bar: %s, %d of %d" % ('MET' if met == len(res) else 'NOT MET', met, len(res)))
    return 0 if met == len(res) else 1


if __name__ == '__main__':
    sys.exit(main())
