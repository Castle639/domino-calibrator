#!/usr/bin/env python3
"""The fix room's F11 bar: seven of the second audit room's should-fixes, the tool's own (1 Oct 2026, his yes to all 27, in the
room's report, section 26): by its report's numbers, 2 (F1.2), 9 (F2.3), 14 (F8.4), 15 (F8.5), 16 (F8.6), 18 (F8.9) and
19 (F8.10). Committed with tests/test_fix_f11.py before it runs. Its controls are the audit room's confirmations of the
breaker's 16, 18 and 19, run unchanged, cut at their lines: confirm_breaker.py's 1-112, 162-166 and 187-202 (c11_breaker.py).
The audit's C8.4 and C8.5 ran from the automatic start, which since F10 gives no record whatever the sky or the name, so
they cannot fail on today's code for their own reason: tests/test_fix_f11.py tests 14 and 15 from a start given, and 2 and 9,
whose confirmations need that room's own inputs.

  python runs/fix_f11_bar.py LOG SCRATCH CONFIRM TARGET    from calibrator/, with ADES_PYLIB, ADES_MASTER, PLAYWRIGHT_MODULE
     TARGET: 'sealed' (release/domino-calibrator at 1fdc232, the fifth seal) or 'head' (calibrator/ at HEAD)

  Z0  the controls: the slice is the audit room's, run whole; the published radii give 41 radii and exit 0
  Z1  16, on TARGET: a one-plane cube with a 2-axis WCS gives the command line a sky position
  Z2  18, on TARGET: --radii 1e-9:1e-9:1e-13, 3:3.0000001:1e-10 and 1e308:1e308:1 each refused at the start, exit 1, naming
      --radii, never "cannot measure: attempt to get argmin"
  Z3  19, on TARGET: CTYPE1 with junk after its quote: exit 2, not 1; the pixel answer stands (no "cannot measure")
  Z4  tests/test_fix_f11.py (all seven items), in calibrator/
  Z5  the whole suite in calibrator/, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
"""
import os, re, sys, hashlib, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # calibrator/
REPO = os.path.dirname(ROOT)
LOG, SCRATCH, CONFIRM, TARGET = sys.argv[1:5]
out = open(LOG, 'w', encoding='utf-8')
SHA = 'f0f598fc1695e1d93462ec951b83eace55ef545ad1be97bdc88455441be1a1cd'
TREES = {'sealed': '1fdc2326b7f80c935cf2d051889a673dfff26699:release/domino-calibrator', 'head': 'HEAD:calibrator'}


def say(s):
    print(s, flush=True); out.write(s + '\n'); out.flush()


def run(args, cwd=None, timeout=3600):
    c = subprocess.run(args, cwd=cwd, capture_output=True, encoding='utf-8', errors='replace', timeout=timeout,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return c.returncode, c.stdout, c.stderr


def main():
    head = run(['git', '-C', REPO, 'rev-parse', '--short', 'HEAD'])[1].strip()
    me = hashlib.sha256(open(os.path.join(CONFIRM, 'c11_breaker.py'), 'rb').read()).hexdigest()
    say('# fix_f11_bar | HEAD %s | TARGET %s (%s) | the slice %s' % (head, TARGET, TREES[TARGET], 'the audit room\'s' if me == SHA else 'OTHER'))
    room = os.path.join(SCRATCH, 'room')
    shutil.rmtree(room, ignore_errors=True); os.makedirs(os.path.join(room, 'folder'))
    tar = subprocess.run(['git', '-C', REPO, 'archive', '--format=tar', TREES[TARGET]], capture_output=True, check=True).stdout
    subprocess.run(['tar', '-x', '-f', '-', '-C', os.path.join(room, 'folder')], input=tar, check=True)
    rc, o, e = run([sys.executable, os.path.join(CONFIRM, 'c11_breaker.py'), room, os.path.join(SCRATCH, 'c11.log')])
    for l in o.splitlines():
        if l.startswith(('C8.6', 'C8.9', 'C8.10')):
            say('    ' + l[:300])
    rad = {m.group(1): m for m in re.finditer(r'^C8\.9 --radii (\S+)\s+exit (\d+) in \S+ s \| radii (.*?) \| zero aperture (.*?) \| '
                                              r'(record|no record) \| (.*)$', o, re.M)}
    z0 = me == SHA and rc == 0 and '2.0:6.0:0.1' in rad and rad['2.0:6.0:0.1'].group(2) == '0' and rad['2.0:6.0:0.1'].group(3).startswith('41 ')
    say('Z0 %s  the controls: the slice the audit room\'s, run whole (exit %d); the published radii: exit %s, radii %s' % (
        'PASS' if z0 else 'FAIL', rc, rad['2.0:6.0:0.1'].group(2) if '2.0:6.0:0.1' in rad else '-', rad['2.0:6.0:0.1'].group(3) if '2.0:6.0:0.1' in rad else '-'))
    c86 = re.search(r'^C8\.6 NAXIS3 = 1, a 2-axis WCS: CLI exit (\d+), (.*?) \| page', o, re.M)
    z1 = c86 is not None and c86.group(2).startswith('(')
    say('Z1 %s  16, the one-plane cube: the command line %s' % ('PASS' if z1 else 'FAIL', c86.group(2) if c86 else '-'))
    z2 = all(k in rad and rad[k].group(2) == '1' and rad[k].group(3) == 'None' and 'argmin' not in rad[k].group(6)
             and '--radii' in rad[k].group(6) for k in ('1e-9:1e-9:1e-13', '3:3.0000001:1e-10', '1e308:1e308:1'))
    say('Z2 %s  18, the radii: %s' % ('PASS' if z2 else 'FAIL', [(k, rad[k].group(2), rad[k].group(6)[:70]) for k in
                                                                  ('1e-9:1e-9:1e-13', '3:3.0000001:1e-10', '1e308:1e308:1') if k in rad]))
    c810 = re.search(r'^C8\.10 CTYPE1 with junk after its quote: CLI exit (\d+) \| (.*?) \| page', o, re.M)
    z3 = c810 is not None and c810.group(1) == '2' and c810.group(2) == 'None'
    say('Z3 %s  19, the unparsable CTYPE1: exit %s, %s' % ('PASS' if z3 else 'FAIL', c810.group(1) if c810 else '-', c810.group(2) if c810 else '-'))
    rc, so, se = run([sys.executable, '-m', 'unittest', '-v', 'tests.test_fix_f11'], cwd=ROOT)
    last = ([l for l in se.splitlines() if l.strip()] or ['no output'])[-1]
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', se, re.M)))
    z4 = rc == 0
    say('Z4 %s  tests/test_fix_f11.py | %s%s' % ('PASS' if z4 else 'FAIL', last, (' | failing: ' + ', '.join(bad)) if bad else ''))
    c = subprocess.run([sys.executable, '-m', 'tests.strict'], cwd=ROOT, env=dict(os.environ, DOMINO_CALIBRATOR_TESTED_VERSIONS='1'),
                       capture_output=True, encoding='utf-8', errors='replace', timeout=5400)
    so = c.stdout + c.stderr
    line = (re.findall(r'^strict: .*$', so, re.M) or ['strict: no verdict'])[-1]
    z5 = c.returncode == 0 and bool(re.match(r'strict: PASS \(\d+ run, 0 failures, 0 errors, 0 skipped', line))
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', so, re.M)))
    say('Z5 %s  %s%s' % ('PASS' if z5 else 'FAIL', line, (' | failing: ' + ', '.join(bad[:12])) if bad else ''))
    met = sum((z0, z1, z2, z3, z4, z5))
    say("# F11's bar on %s: %s, %d of 6" % (TARGET, 'MET' if met == 6 else 'NOT MET', met))
    return 0 if met == 6 else 1


if __name__ == '__main__':
    sys.exit(main())
