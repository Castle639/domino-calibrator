#!/usr/bin/env python3
"""The fix room's F18 bar: the re-check room's B3' finding (2 Oct 2026, evening; the room's report, section 41). Three rounds'
own bars and logs named what their trims took out; at his word they stay in our own records, whole and unedited, and leave
the public copy, with one sentence in runs/README.md saying so. Committed with tests/test_fix_f18.py before the fix.

At his condition, this bar names nothing it checks for: the patterns, the descriptions and the files left out are read from
CHECKS, kept in our own records, and every line it prints gives counts, clause names and pattern numbers only. Z5 checks that
of its own log.

  python runs/fix_f18_bar.py LOG SCRATCH CURATE DECISIONS CHECKS SWEEP     from calibrator/, with ADES_PYLIB, ADES_MASTER,
                                                                           PLAYWRIGHT_MODULE
  SCRATCH: a folder outside the Castle for the built copy; CURATE, DECISIONS, CHECKS: the curation tool, its decisions and the
  release bar's patterns; SWEEP: the room's sweep (a trim's description, a replaced original, a trim word beside a private
  category, a printed list of names), which prints file, line and pattern numbers.

  Z0  the controls: the sweep finds the re-check's rows in the Castle's own records (at least 11 lines in at least 6 files);
      every pattern of CHECKS hits its control, and its plant; the files CHECKS leaves out exist in the Castle
  Z1  the copy built by CURATE with DECISIONS (exit 0) holds none of the files CHECKS leaves out; no text file of it names one
      (its name whole, with or without its folder and extension); the sweep finds 0 lines in it
  Z2  the release bar's S0-S3 on that copy with CHECKS: MET, 4 of 4 (its output kept out of this log: verdicts only)
  Z3  runs/README.md says it, in the Castle and in the copy: his sentence of 2 Oct 2026
  Z4  the whole suite in calibrator/, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
  Z5  this log, Z0-Z4 as printed: no pattern of CHECKS matches in it, and it names no file CHECKS leaves out
"""
import json, os, re, sys, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO = os.path.dirname(ROOT)
LOG, SCRATCH, CURATE, DECISIONS, CHECKS, SWEEP = sys.argv[1:7]
SENTENCE = ('The bars and logs of three rounds that took private words out of this public copy (F9, F13 and F14) are kept '
            'in our own records too, because they name what was taken out; their tests and science-control logs are here.')
out = open(LOG, 'w', encoding='utf-8')
said = []


def say(s):
    said.append(s); print(s, flush=True); out.write(s + '\n'); out.flush()


def run(args, cwd=ROOT, env=None):
    c = subprocess.run(args, cwd=cwd, capture_output=True, encoding='utf-8', errors='replace', timeout=5400,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', **(env or {})))
    return c.returncode, c.stdout + c.stderr


def rx(c):
    return re.compile(c['pattern'], re.I if 'i' in c.get('flags', '') else 0)


def sweep(folder):
    """(lines, files) the sweep flags in folder."""
    rc, o = run([sys.executable, SWEEP, folder, CHECKS, DECISIONS], cwd=REPO)
    m = re.search(r'^# files (\d+), lines (\d+)$', o, re.M)
    return (int(m.group(2)), int(m.group(1))) if rc == 0 and m else (-1, -1)


def texts(root):
    for dp, dn, fn in os.walk(root):
        dn[:] = [d for d in dn if d != '.git']
        for f in fn:
            try:
                yield os.path.relpath(os.path.join(dp, f), root), open(os.path.join(dp, f), encoding='utf-8').read()
            except UnicodeDecodeError:
                pass


def main():
    CK = json.load(open(CHECKS, encoding='utf-8'))
    absent, left = CK['absent'], CK['left_out']
    head = run(['git', '-C', REPO, 'rev-parse', '--short', 'HEAD'])[1].strip()
    say('# fix_f18_bar | HEAD %s | CHECKS %d patterns, %d files left out | DECISIONS %s' % (
        head, len(absent), len(left), os.path.basename(DECISIONS)))
    # Z0
    lines, files = sweep(os.path.join(REPO, 'calibrator'))
    miss_c = [i for i, c in enumerate(absent) if not rx(c).search(open(os.path.join(REPO, c['control']), encoding='utf-8').read())]
    miss_p = [i for i, c in enumerate(absent) if not rx(c).search(c['plant'])]
    gone = [i for i, f in enumerate(left) if not os.path.exists(os.path.join(REPO, 'calibrator', f))
            and not os.path.exists(os.path.join(REPO, f))]
    z0 = lines >= 11 and files >= 6 and not miss_c and not miss_p and not gone
    say('Z0 %s  the controls: the sweep in the Castle\'s own records: %d lines in %d files | patterns missing their control: %s, '
        'their plant: %s | files left out not in the Castle: %s' % ('PASS' if z0 else 'FAIL', lines, files, miss_c or 'none',
                                                                    miss_p or 'none', gone or 'none'))
    # Z1
    built = os.path.join(SCRATCH, 'f18_copy')
    shutil.rmtree(built, ignore_errors=True)
    crc, _ = run([sys.executable, CURATE, REPO, built, DECISIONS, os.path.join(SCRATCH, 'f18_manifest.txt')], cwd=REPO)
    present = [i for i, f in enumerate(left) if os.path.exists(os.path.join(built, f))]
    names = []
    for i, f in enumerate(left):
        stem = os.path.splitext(os.path.basename(f))[0]
        name = re.compile(r'(?<![\w.-])%s(?:\.\w+)?(?![\w-])' % re.escape(stem))
        if any(name.search(t) for _, t in texts(built)):
            names.append(i)
    blines, bfiles = sweep(built) if crc == 0 else (-1, -1)
    z1 = crc == 0 and not present and not names and blines == 0
    say('Z1 %s  the copy: curation exit %d | files left out still in it (by number): %s | named in its text: %s | the sweep: '
        '%d lines in %d files' % ('PASS' if z1 else 'FAIL', crc, present or 'none', names or 'none', blines, bfiles))
    # Z2
    rc, o = run([sys.executable, os.path.join(ROOT, 'runs', 'release_bar.py'), SCRATCH, REPO, sys.executable, built, CHECKS,
                 'S0,S1,S2,S3'], cwd=REPO)
    clauses = re.findall(r'^(S[0-3])\s+(PASS|FAIL)', o, re.M)
    verdict = (re.findall(r'^# release bar: (MET|NOT MET), (\d) of (\d)', o, re.M) or [('none', '0', '0')])[-1]
    z2 = verdict[0] == 'MET' and len(clauses) == 4
    say('Z2 %s  the release bar on the copy: %s | %s, %s of %s (its detail kept out of this log)' % (
        'PASS' if z2 else 'FAIL', ' '.join('%s %s' % c for c in clauses) or 'no clauses', *verdict))
    # Z3
    flat = lambda p: ' '.join(open(p, encoding='utf-8').read().split()) if os.path.exists(p) else ''
    in_castle = SENTENCE in flat(os.path.join(ROOT, 'runs', 'README.md'))
    in_copy = SENTENCE in flat(os.path.join(built, 'runs', 'README.md'))
    z3 = in_castle and in_copy
    say('Z3 %s  runs/README.md says it: in the Castle %s, in the copy %s' % ('PASS' if z3 else 'FAIL', in_castle, in_copy))
    # Z4
    rc, o = run([sys.executable, '-m', 'tests.strict'], env=dict(DOMINO_CALIBRATOR_TESTED_VERSIONS='1'))
    line = (re.findall(r'^strict: .*$', o, re.M) or ['strict: no verdict'])[-1]
    z4 = rc == 0 and bool(re.match(r'strict: PASS \(\d+ run, 0 failures, 0 errors, 0 skipped', line))
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', o, re.M)))
    say('Z4 %s  %s%s' % ('PASS' if z4 else 'FAIL', line, (' | failing: ' + ', '.join(bad)) if bad else ''))
    # Z5
    text = '\n'.join(said)
    hit = [i for i, c in enumerate(absent) if rx(c).search(text)]
    named = [i for i, f in enumerate(left) if os.path.splitext(os.path.basename(f))[0] in text]
    z5 = not hit and not named
    say('Z5 %s  this log: patterns matching in it: %s | files left out named in it: %s' % (
        'PASS' if z5 else 'FAIL', hit or 'none', named or 'none'))
    met = sum((z0, z1, z2, z3, z4, z5))
    say("# F18's bar: %s, %d of 6" % ('MET' if met == 6 else 'NOT MET', met))
    return 0 if met == 6 else 1


if __name__ == '__main__':
    sys.exit(main())
