#!/usr/bin/env python3
"""The fix room's F10 bar: B2's cure (1 Oct 2026, his word for the night's second part, in the room's report, section 25).
Committed with tests/test_fix_f10.py before it runs. Its controls are the second audit room's confirmations, each run
unchanged from its record, cut at the lines that hold the case: confirm_breaker.py's 1-86, 113-137 and 167-176 (C8.2, C8.3,
C8.7; with engine2.js), confirm_wave3.py's 1-81 (C9.1), confirm_wave1.py's 1-69, 133 and 135-147 (C3.1; with the regression's
own log at ../regression/).

  python runs/fix_f10_bar.py LOG SCRATCH CONFIRM TARGET     from calibrator/, with ADES_PYLIB, ADES_MASTER, PLAYWRIGHT_MODULE
     CONFIRM: the folder of the slices (c10_breaker.py, c10_w3.py, c10_w1.py, engine2.js; regress_engine.js and the
              regression's log at ../regression/)
     TARGET: the tree the confirmations run on: 'sealed' (release/domino-calibrator at 1fdc232, the fifth seal) or 'head'
             (calibrator/ at HEAD)

  X0  the controls: the slices are the audit room's and run whole; C3.1's lone star from a typed start gets a record on both
      faces (his cure keeps it: telling a comet from a star is the observer's); C8.3's star at 1.5, 3 and 4.9 times the
      comet is refused on both faces; C8.7's typed start gives the command line a record
  X1  no record from the automatic start, on either face: C9.1's star and blob (and the star with --desig 433, --stn ZZZ);
      C8.3's star at 5.1, 10 and 100 times; C8.7's automatic start on the page
  X2  a single pixel is no source (C8.2): the hot pixel, M from the automatic start, no record on either face; over 20 noise
      seeds, records for it 0 (M, automatic) and 0 (G, from a start on the pixel)
  X3  the words: "only when it has measured a comet" stands nowhere C9.1 looks; the README's Use section no longer says it
  X4  tests/test_fix_f10.py (the page in a browser among them: no click, no record; a start typed equal to the brightest box
      is a start given, F8.7), with F7's, F8's and F9's, in calibrator/
  X5  the whole suite in calibrator/, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
"""
import os, re, sys, ast, json, shutil, hashlib, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # calibrator/
REPO = os.path.dirname(ROOT)
LOG, SCRATCH, CONFIRM, TARGET = sys.argv[1:5]
out = open(LOG, 'w', encoding='utf-8')
SHAS = {'c10_breaker.py': '9012fa7fe9f7154263c169281a4f241bbc63a8df541a9487081585fa8a1ac8d4',
        'c10_w3.py': '05862d3de4d62ef5c4b481fe869f04e20b39f60717b93db9fdd68979d0e05bba',
        'c10_w1.py': 'aaa2cb2d94d6b2244728b4d9494c1635e8da29231b09f119d34d10f0fd20e5c6',
        'engine2.js': '94bcb1c84544110d293ac1d6873b69b69f81310faa8371c133b1eb5b181e95dd'}
TREES = {'sealed': '1fdc2326b7f80c935cf2d051889a673dfff26699:release/domino-calibrator', 'head': 'HEAD:calibrator'}


def say(s):
    print(s, flush=True); out.write(s + '\n'); out.flush()


def run(args, cwd=None, timeout=3600):
    c = subprocess.run(args, cwd=cwd, capture_output=True, encoding='utf-8', errors='replace', timeout=timeout,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return c.returncode, c.stdout, c.stderr


def main():
    head = run(['git', '-C', REPO, 'rev-parse', '--short', 'HEAD'])[1].strip()
    tree = TREES[TARGET]
    shas = {f: hashlib.sha256(open(os.path.join(CONFIRM, f), 'rb').read()).hexdigest() for f in SHAS}
    say('# fix_f10_bar | HEAD %s | TARGET %s (%s) | the slices %s' % (head, TARGET, tree, 'the audit room\'s' if all(
        shas[f] == SHAS[f] for f in SHAS) else 'OTHER: ' + str([f for f in SHAS if shas[f] != SHAS[f]])))
    room = os.path.join(SCRATCH, 'room')
    shutil.rmtree(room, ignore_errors=True); os.makedirs(os.path.join(room, 'folder'))
    tar = subprocess.run(['git', '-C', REPO, 'archive', '--format=tar', tree], capture_output=True, check=True).stdout
    subprocess.run(['tar', '-x', '-f', '-', '-C', os.path.join(room, 'folder')], input=tar, check=True)
    os.makedirs(os.path.join(SCRATCH, 'ground'), exist_ok=True)
    o, rcs = '', []
    for f in ('c10_breaker.py', 'c10_w3.py', 'c10_w1.py'):
        rc, so, se = run([sys.executable, os.path.join(CONFIRM, f), room, os.path.join(SCRATCH, f + '.log')])
        rcs.append(rc); o += so
        if rc:
            say('    %s exit %d: %s' % (f, rc, se.strip()[-300:]))
    for l in o.splitlines():
        if l.startswith(('C9.1', 'C3.1', 'C8.2', 'C8.3', 'C8.7')):
            say('    ' + l[:400])

    c31 = re.search(r'^C3\.1 a lone star .*: exit (\d+) \| record (True|False) \| judge (.*?) \| engine need (.*)$', o, re.M)
    c83 = dict(re.findall(r'([\d.]+)x: CLI (RECORD|refused) at \([^)]*\), page (RECORD|refused)', o) and
               [(k, (a, b)) for k, a, b in re.findall(r'([\d.]+)x: CLI (RECORD|refused) at \([^)]*\), page (RECORD|refused)', o)])
    c87 = re.search(r'^C8\.7 the brightest box (\[.*?\]); automatic: page need (\[.*?\]) \| CLI --x \S+ --y \S+: exit (\d+), '
                    r'(record|no record) \|', o, re.M)
    x0 = (all(shas[f] == SHAS[f] for f in SHAS) and not any(rcs) and c31 is not None and c31.group(2) == 'True'
          and c31.group(3) == 'submit is OK' and c31.group(4) == '[]' and all(c83.get(k) == ('refused', 'refused') for k in ('1.5', '3', '4.9'))
          and c87 is not None and c87.group(4) == 'record')
    say('X0 %s  the controls: the slices the audit room\'s, run whole (exit %s); C3.1\'s lone star from a typed start: %s; C8.3 at '
        '1.5/3/4.9x refused on both faces: %s; C8.7 typed on the command line: %s' % (
            'PASS' if x0 else 'FAIL', rcs, ('record, ' + c31.group(3) + ', page need ' + c31.group(4)) if c31 else '-',
            [c83.get(k) for k in ('1.5', '3', '4.9')], c87.group(4) if c87 else '-'))

    c91 = re.findall(r'^C9\.1 (a lone star|a galaxy-like blob).*?the automatic start: exit (\d+) \| (record|no record).*?\|\| engine need (.*?), sky', o, re.M)
    c91b = re.findall(r'^C9\.1 the star with (--desig 433|--stn ZZZ): exit (\d+) \| (record|no record)', o, re.M)
    x1 = (len(c91) == 2 and all(r == 'no record' and n not in ('[]', 'None') for _, _, r, n in c91) and len(c91b) == 2
          and all(r == 'no record' for _, _, r in c91b) and all(c83.get(k) == ('refused', 'refused') for k in ('5.1', '10', '100'))
          and c87 is not None and c87.group(2) != '[]')
    say('X1 %s  no record from the automatic start: C9.1 %s and %s; C8.3 at 5.1/10/100x %s; C8.7 the page, automatic, need %s' % (
        'PASS' if x1 else 'FAIL', [(a, r) for a, _, r, _ in c91], [(a, r) for a, _, r in c91b], [c83.get(k) for k in ('5.1', '10', '100')],
        'given' if c87 and c87.group(2) != '[]' else 'none'))

    c82 = re.search(r'^C8\.2 noise sd 5.*?CLI exit (\d+), RA/Dec .*?, (record|no record), .*?\| page need (.*?), sky', o, re.M)
    c82n = re.search(r'records for the single pixel: (\d+); G from a start on the pixel: (\d+)', o)
    x2 = (c82 is not None and c82.group(2) == 'no record' and c82.group(3) not in ('[]', 'None') and c82n is not None
          and c82n.groups() == ('0', '0'))
    say('X2 %s  a single pixel: the command line %s, the page need %s; over 20 seeds, records %s' % (
        'PASS' if x2 else 'FAIL', c82.group(2) if c82 else '-', 'given' if c82 and c82.group(3) not in ('[]', 'None') else 'none',
        c82n.groups() if c82n else '-'))

    w = re.search(r'^C9\.1 "only when it has measured a comet" at README\.md:37 (True|False), CHANGELOG\.md:17 (True|False), '
                  r'page/index\.html:99 (True|False)', o, re.M)
    u = re.search(r'^C3\.1 the README\'s Use section: .*\| the rule\'s words there: (True|False)', o, re.M)
    x3 = w is not None and w.groups() == ('False',) * 3 and u is not None and u.group(1) == 'False'
    say('X3 %s  the words: "only when it has measured a comet" where C9.1 looks %s; in the README\'s Use section %s' % (
        'PASS' if x3 else 'FAIL', w.groups() if w else '-', u.group(1) if u else '-'))

    rc, so, se = run([sys.executable, '-m', 'unittest', '-v', 'tests.test_fix_f7', 'tests.test_fix_f8', 'tests.test_fix_f9',
                      'tests.test_fix_f10'], cwd=ROOT)
    last = ([l for l in se.splitlines() if l.strip()] or ['no output'])[-1]
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', se, re.M)))
    x4 = rc == 0 and 'skipped' not in last
    say('X4 %s  tests F7-F10 | %s%s' % ('PASS' if x4 else 'FAIL', last, (' | failing: ' + ', '.join(bad)) if bad else ''))
    c = subprocess.run([sys.executable, '-m', 'tests.strict'], cwd=ROOT, env=dict(os.environ, DOMINO_CALIBRATOR_TESTED_VERSIONS='1'),
                       capture_output=True, encoding='utf-8', errors='replace', timeout=5400)
    so = c.stdout + c.stderr
    line = (re.findall(r'^strict: .*$', so, re.M) or ['strict: no verdict'])[-1]
    x5 = c.returncode == 0 and bool(re.match(r'strict: PASS \(\d+ run, 0 failures, 0 errors, 0 skipped', line))
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', so, re.M)))
    say('X5 %s  %s%s' % ('PASS' if x5 else 'FAIL', line, (' | failing: %d: ' % len(bad) + ', '.join(bad[:12])) if bad else ''))
    met = sum((x0, x1, x2, x3, x4, x5))
    say("# F10's bar on %s: %s, %d of 6" % (TARGET, 'MET' if met == 6 else 'NOT MET', met))
    return 0 if met == 6 else 1


if __name__ == '__main__':
    sys.exit(main())
