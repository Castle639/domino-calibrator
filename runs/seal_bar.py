#!/usr/bin/env python3
"""Launch step 6's seal: the folder, rebuilt after its bar's run with the records written since (30 Sept 2026, the
calibrator's build room). Written before the folder is first built. The release bar (release_bar.py) runs S0-S5 on the
folder as first built, whose manifest is TESTED. The rebuild adds only records: the runs' logs and predictions written
after it, and the launch steps record with step 6. The seal shows that, and that the rebuilt folder still holds S0-S3.
Its own prediction and log go into the room's report, which is not in the folder: so the folder never waits on them.

The clauses:
  E0  control: E2's check turns red on the rebuilt folder's manifest with one module's hash changed, and with a file added
      under tests/; it stays green with a log added under runs/
  E1  release_bar.py S0-S3 on the rebuilt folder: MET, 4 of 4
  E2  against TESTED: every file added, removed or changed is a record (a runs/ .txt, or an archive/ .md); nothing else
  E3  the folder as committed: git tracks exactly the folder's files, and holds every byte of them (nothing ignored, nothing
      uncommitted)

Usage: python calibrator/runs/seal_bar.py SCRATCH REPO TESTED_PYTHON FOLDER CHECKS.json TESTED_MANIFEST [CLAUSES]
"""
import os, re, sys, hashlib, subprocess

SCRATCH, REPO, PY, FOLDER, CHECKS, TESTED = sys.argv[1:7]
ONLY = set(sys.argv[7].split(',')) if len(sys.argv) > 7 else None
RECORD = re.compile(r'^(runs/[^/]+\.txt|archive/[^/]+\.md)$')
RESULTS = {}


def verdict(name, ok, detail):
    RESULTS[name] = ok
    print('%-3s %s  %s' % (name, 'PASS' if ok else 'FAIL', detail), flush=True)


def want(name):
    return ONLY is None or name in ONLY


def manifest(root):
    out = {}
    for dp, dn, fn in os.walk(root):
        for f in fn:
            p = os.path.join(dp, f)
            with open(p, 'rb') as fh:
                out[os.path.relpath(p, root)] = hashlib.sha256(fh.read()).hexdigest()
    return out


def read_manifest(p):
    out = {}
    with open(p, encoding='utf-8') as fh:
        for line in fh:
            if line.strip():
                h, rel = line.rstrip('\n').split('  ', 1)
                out[rel] = h
    return out


def not_records(old, new):
    """The files added, removed or changed between two manifests that are not records."""
    moved = {f for f in set(old) | set(new) if old.get(f) != new.get(f)}
    return sorted(f for f in moved if not RECORD.match(f)), sorted(moved)


def main():
    print('# seal | HEAD %s | the folder %s | tested manifest %s' % (subprocess.run(
        ['git', '-C', REPO, 'log', '-1', '--format=%h'], capture_output=True, text=True).stdout.strip(),
        os.path.relpath(FOLDER, REPO), os.path.basename(TESTED)), flush=True)
    old, new = read_manifest(TESTED), manifest(FOLDER)

    if want('E0'):
        mod = next(f for f in sorted(new) if f.startswith('domino_calibrator/') and f.endswith('.py'))
        changed = dict(new); changed[mod] = '0' * 64
        added = dict(new); added['tests/test_planted.py'] = '1' * 64
        a_log = dict(new); a_log['runs/PLANTED_RUNLOG_2026-09-30.txt'] = '2' * 64
        r1, r2, r3 = not_records(new, changed)[0], not_records(new, added)[0], not_records(new, a_log)[0]
        verdict('E0', r1 == [mod] and r2 == ['tests/test_planted.py'] and r3 == [],
                'a module changed: %s | a test added: %s | a log added: %s' % (
                    'red' if r1 else 'GREEN', 'red' if r2 else 'GREEN', 'green' if not r3 else 'RED'))

    if want('E1'):
        c = subprocess.run([PY, os.path.join(REPO, 'calibrator', 'runs', 'release_bar.py'), SCRATCH, REPO, PY, FOLDER, CHECKS,
                            'S0,S1,S2,S3'], capture_output=True, text=True)
        lines = [l for l in c.stdout.splitlines() if re.match(r'^S[0-3] ', l)]
        for l in lines:
            print('    ' + l, flush=True)
        met = re.search(r'^# release bar: MET, 4 of 4$', c.stdout, flags=re.M)
        verdict('E1', c.returncode == 0 and bool(met), 'release_bar.py S0-S3: %s' % (met.group(0)[2:] if met else 'NOT MET'))

    if want('E2'):
        bad, moved = not_records(old, new)
        verdict('E2', not bad, '%d files differ from the tested folder, all records: %s%s' % (
            len(moved), not bad, (' (not records: %s)' % ', '.join(bad[:6])) if bad else ''))
        for f in moved:
            print('    %s %s' % ('added  ' if f not in old else 'removed' if f not in new else 'changed', f), flush=True)

    if want('E3'):
        rel = os.path.relpath(FOLDER, REPO)
        tracked = {f[len(rel) + 1:] for f in subprocess.run(['git', '-C', REPO, 'ls-files', '--', rel], capture_output=True,
                                                             text=True).stdout.splitlines() if f}
        status = subprocess.run(['git', '-C', REPO, 'status', '--porcelain', '--ignored', '--', rel], capture_output=True,
                                text=True).stdout.splitlines()
        ok = tracked == set(new) and not status
        verdict('E3', ok, 'git tracks %d files, the folder holds %d, the same: %s | uncommitted or ignored: %d%s' % (
            len(tracked), len(new), tracked == set(new), len(status), (' (%s)' % '; '.join(status[:4])) if status else ''))

    names = [n for n in ('E0', 'E1', 'E2', 'E3') if n in RESULTS]
    met = sum(1 for n in names if RESULTS[n])
    print('# seal: %s, %d of %d%s' % ('MET' if met == len(names) else 'NOT MET', met, len(names),
                                     '' if met == len(names) else ' (failing: %s)' % ' '.join(n for n in names if not RESULTS[n])))


if __name__ == '__main__':
    main()
