#!/usr/bin/env python3
"""The seventh room's mutants (the release room's record of 28 Sept 2026, not in this repository, section 2): a test that cannot fail is not a
test. Each mutant changes one thing in the new words, on a copy of the folder, and the words test must turn red on it;
the unchanged copy must stay green. The first four are the bar's; the fifth puts back the page's old sentence, lane 2's
first blocker.

    python calibrator/runs/rel_mutants.py LOG
"""
import os, sys, shutil, tempfile, subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
PKG = os.path.join(ROOT, 'calibrator')
MUTANTS = [
    (None, None, None, None),
    ("a box loses its seeing edge (README)", 'README.md',
     'helps in 20 of 20 cells at ≤ 1.0″ seeing and ≤ 0.44″/px', 'helps in 20 of 20 cells at ≤ 0.44″/px'),
    ('a count off by one (README)', 'README.md', 'fails in 42 of 45 cells', 'fails in 43 of 45 cells'),
    ('set-ups for cells (README)', 'README.md', 'in 45 of the 130 cells', 'in 45 of the 130 set-ups'),
    ("truth without HST's photocentre (README)", 'README.md', 'Look at the curve before trusting the intercept:',
     'The extrapolation brings the position closer to the truth. Look at the curve before trusting the intercept:'),
    ("the page's old sentence, lane 2's first blocker", 'page/index.html',
     'Look at the curve before trusting the intercept.\n</div>',
     'For 3I/ATLAS it helped on sharp images (&le; 0.44&Prime;/px). Look at the curve before trusting the intercept.\n</div>'),
]


def main():
    log = open(sys.argv[1], 'w', encoding='utf-8')
    def say(s):
        print(s, flush=True); log.write(s + '\n'); log.flush()
    head = subprocess.run(['git', '-C', ROOT, 'log', '-1', '--format=%h'], capture_output=True, text=True).stdout.strip()
    say('# the seventh room\'s mutants | calibrator/runs/rel_mutants.py | HEAD %s (the words as in the working tree)' % head)
    bad = 0
    for name, f, old, new in MUTANTS:
        tmp = tempfile.mkdtemp(prefix='relmut_')
        try:
            dst = os.path.join(tmp, 'calibrator')
            shutil.copytree(PKG, dst, ignore=shutil.ignore_patterns('__pycache__'))
            if f:
                p = os.path.join(dst, f)
                t = open(p, encoding='utf-8').read()
                assert t.count(old) == 1, (name, t.count(old))
                open(p, 'w', encoding='utf-8').write(t.replace(old, new))
            c = subprocess.run([sys.executable, '-m', 'unittest', 'calibrator.tests.test_release_words'], cwd=tmp,
                               capture_output=True, text=True)
            red = sorted({ln.split()[1] for ln in c.stderr.splitlines() if ln.startswith(('FAIL:', 'ERROR:'))})
            want_red = f is not None
            ok = (c.returncode != 0) == want_red
            bad += not ok
            say('%-52s %s | red: %s' % (name or 'the unchanged copy (control)', ('RED' if c.returncode else 'GREEN') +
                                        (' as it must' if ok else ' -- WRONG'), ', '.join(red) or '-'))
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    say('# %s' % ('PASS: every mutant red, the control green' if not bad else 'FAIL: %d wrong' % bad))
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
