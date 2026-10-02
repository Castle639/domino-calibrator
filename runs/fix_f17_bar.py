#!/usr/bin/env python3
"""The fix room's F17 bar: his two questions (2 Oct 2026, afternoon; the room's report, section 36): summary_differences let
+inf and -inf through; runs/README.md said bit for bit holds on one machine, where it holds across machines that take the
same arithmetic paths. Committed with tests/test_fix_f17.py before the fix.

  python runs/fix_f17_bar.py LOG     from calibrator/, with ADES_PYLIB, ADES_MASTER, PLAYWRIGHT_MODULE

  X0  the controls: F12_5 passes here; F16's tolerance tests but its README words (re-pointed by the fix) pass
  X1  tests/test_fix_f17.py: infinity against anything but itself a difference; the same infinity, and NaN against NaN, not;
      an infinity planted in the summary found; runs/README.md in his words
  X2  the whole suite in calibrator/, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
"""
import os, re, sys, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
LOG = sys.argv[1]
out = open(LOG, 'w', encoding='utf-8')


def say(s):
    print(s, flush=True); out.write(s + '\n'); out.flush()


def run(args, env=None):
    c = subprocess.run(args, cwd=ROOT, capture_output=True, encoding='utf-8', errors='replace', timeout=5400,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', **(env or {})))
    return c.returncode, c.stdout + c.stderr


def main():
    head = subprocess.run(['git', '-C', REPO, 'rev-parse', '--short', 'HEAD'], capture_output=True, encoding='utf-8').stdout.strip()
    say('# fix_f17_bar | HEAD %s' % head)
    rc, o = run([sys.executable, '-m', 'unittest', 'tests.test_fix_f12.F12_5_TheStudysReportFromTheRoot', 'tests.test_fix_f16.F16_TheSummaryAcrossMachines'])
    x0 = rc == 0
    say('X0 %s  the controls: %s' % ('PASS' if x0 else 'FAIL', ([l for l in o.splitlines() if l.strip()] or ['?'])[-1]))
    rc, o = run([sys.executable, '-m', 'unittest', '-v', 'tests.test_fix_f17'])
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', o, re.M)))
    x1 = rc == 0
    say('X1 %s  tests/test_fix_f17.py | %s%s' % ('PASS' if x1 else 'FAIL', ([l for l in o.splitlines() if l.strip()] or ['?'])[-1],
                                                (' | failing: ' + ', '.join(bad)) if bad else ''))
    rc, o = run([sys.executable, '-m', 'tests.strict'], env=dict(DOMINO_CALIBRATOR_TESTED_VERSIONS='1'))
    line = (re.findall(r'^strict: .*$', o, re.M) or ['strict: no verdict'])[-1]
    x2 = rc == 0 and bool(re.match(r'strict: PASS \(\d+ run, 0 failures, 0 errors, 0 skipped', line))
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', o, re.M)))
    say('X2 %s  %s%s' % ('PASS' if x2 else 'FAIL', line, (' | failing: ' + ', '.join(bad)) if bad else ''))
    met = sum((x0, x1, x2))
    say("# F17's bar: %s, %d of 3" % ('MET' if met == 3 else 'NOT MET', met))
    return 0 if met == 3 else 1


if __name__ == '__main__':
    sys.exit(main())
