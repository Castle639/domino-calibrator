#!/usr/bin/env python3
"""Call 6's bar: H0 from a positions file inside the repository (the launch list's step 6; his call 6: [his words, not quoted in public]; the build room's brief of 30 Sept 2026, not in this repository).
Written before H0 changes (30 Sept 2026, the calibrator's build room).

H0 read two files at the Castle's root: the log it took its reference positions from, and MAST's inventory it took its 30
frames from (measured this morning: the log's 30 frames are the inventory's 30 picks, in the same order). Both now come from
runs/H0_POSITIONS_2026-09-30.txt, the frames and their positions as first written (two decimals; the same floats as the old
reader's, measured before this bar). The positions feed only H0.1 and the per-frame lines of H0's log, not the sky images,
so C1 alone, bit for bit on the new images, cannot tell a wrong position from a right one: Q2 compares H0's log with the
ground's line by line.

The clauses:
  Q0  control: the log comparison finds the one line changed in a planted copy of the ground's log (a frame's peak-K0 value)
  Q1  H0's source builds no path above the repository (no ROOT, no '..', no literal tools or data folder), and the
      positions file holds 30 distinct frames, sorted, each with two positions of two decimals (its floats were measured
      equal to the old reader's before this bar; Q2 would show any that were not)
  Q2  H0 from the positions file ends 0, and its log's 30 per-frame lines and its checks line are the ground's, byte for byte
      (the ground: H0 at 11:00 UTC today, main's code)
  Q3  its 30 sky images are the ground's by content (every array's name, dtype, shape and bytes)
  Q4  runs/H0_FRAMES_2026-09-27.json unchanged; the Horizons table changed in its three known header lines only (the query
      time, two EOP lines), then restored from git outside this script
  Q5  C1 on the new images, bit for bit (the brief's proof), and C2 with 0 FITTED and the same 43, side by side

Usage: python calibrator/runs/positions_bar.py SCRATCH REPO TESTED_PYTHON GROUND_LOG GROUND_CONTENT_HASHES [CLAUSES]
"""
import os, re, sys, time, glob, hashlib, subprocess
import numpy as np

SCRATCH, REPO, PY, GROUND_LOG, GROUND_HASH = sys.argv[1:6]
ONLY = set(sys.argv[6].split(',')) if len(sys.argv) > 6 else None
PKG = os.path.join(REPO, 'calibrator')
RUNS = os.path.join(PKG, 'runs')
OUT = os.path.join(SCRATCH, 'positions_bar')
WORK = os.path.join(os.environ['HOME'], 'calib_work')
FRAME_LINE = re.compile(r'^ifle\w+ \w+ \| peak-K0 ')
CHECKS = re.compile(r'^# H0\.1 ')
RESULTS = {}


def verdict(name, ok, detail):
    RESULTS[name] = ok
    print('%-3s %s  %s' % (name, 'PASS' if ok else 'FAIL', detail), flush=True)


def want(name):
    return ONLY is None or name in ONLY


def frame_lines(text):
    return [l for l in text.splitlines() if FRAME_LINE.match(l) or CHECKS.match(l)]


def compare(a, b):
    la, lb = frame_lines(a), frame_lines(b)
    return len(la), len(lb), sum(1 for x, y in zip(la, lb) if x != y) + abs(len(la) - len(lb))


def content_hashes(folder):
    out = {}
    for p in sorted(glob.glob(os.path.join(folder, 'sky_*.npz'))):
        z = np.load(p); h = hashlib.sha256()
        for k in sorted(z.files):
            a = np.ascontiguousarray(z[k]); h.update(k.encode()); h.update(str(a.dtype).encode()); h.update(str(a.shape).encode()); h.update(a.tobytes())
        out[os.path.basename(p)] = h.hexdigest()
    return out


def main():
    os.makedirs(OUT, exist_ok=True)
    print('# positions bar %s UTC | HEAD %s' % (time.strftime('%F %T', time.gmtime()), subprocess.run(
        ['git', '-C', REPO, 'log', '-1', '--format=%h'], capture_output=True, text=True).stdout.strip()), flush=True)
    ground = open(GROUND_LOG).read()

    if want('Q0'):
        lines = ground.splitlines()
        i = next(k for k, l in enumerate(lines) if FRAME_LINE.match(l))
        planted = lines[:]
        planted[i] = re.sub(r'peak-K0 (\d+\.\d+) px', lambda m: 'peak-K0 %.2f px' % (float(m.group(1)) + 2.0), planted[i], count=1)
        n1, n2, diff = compare(ground, '\n'.join(planted))
        n1b, n2b, same = compare(ground, ground)
        verdict('Q0', diff == 1 and same == 0 and n1 == 31, 'the ground against itself: %d of %d lines differ; against the planted copy: %d'
                % (same, n1b, diff))

    if want('Q1'):
        src = open(os.path.join(RUNS, 'h0_prepare.py'), encoding='utf-8').read()
        above = [w for w in ("'..'", 'ROOT', "'tools'", "'data'") if w in src]
        pos, pf = [], os.path.join(RUNS, 'H0_POSITIONS_2026-09-30.txt')
        for ln in (open(pf, encoding='utf-8') if os.path.exists(pf) else []):
            if ln.strip() and not ln.startswith('#'):
                f = ln.split(); pos.append((f[0], f[1], f[2]))
        form = all(re.fullmatch(r'ifle\w{5}', r) and re.fullmatch(r'\d+\.\d\d', x) and re.fullmatch(r'\d+\.\d\d', y) for r, x, y in pos)
        roots = [r for r, _, _ in pos]
        verdict('Q1', not above and len(pos) == 30 and roots == sorted(set(roots)) and form,
                'paths above the repository in H0: %s | the file: %s, %d frames, sorted and distinct: %s, two decimals: %s'
                % (', '.join(above) or 'none', 'present' if os.path.exists(pf) else 'absent', len(pos), roots == sorted(set(roots)), form))

    if want('Q2'):
        log = os.path.join(OUT, 'H0_RUNLOG.txt')
        t0 = time.time()
        c = subprocess.run([PY, os.path.join(RUNS, 'h0_prepare.py'), log], cwd=REPO, capture_output=True, text=True, timeout=3600)
        new = open(log).read() if os.path.exists(log) else ''
        n1, n2, diff = compare(ground, new)
        verdict('Q2', c.returncode == 0 and n1 == n2 == 31 and diff == 0, 'H0 exit %d in %.0f s | per-frame and checks lines: the ground %d, '
                'the new %d, differing %d | %s' % (c.returncode, time.time() - t0, n1, n2, diff,
                                                   next((l for l in new.splitlines() if CHECKS.match(l)), 'no checks line')[:120]))

    if want('Q3'):
        want_h = dict(reversed(l.split()) for l in open(GROUND_HASH) if l.strip())
        got = content_hashes(WORK)
        diff = sorted(k for k in set(want_h) | set(got) if want_h.get(k) != got.get(k))
        verdict('Q3', len(got) == 30 and not diff, '%d images, %d differing from the ground by content%s' % (
            len(got), len(diff), (' (%s)' % ', '.join(diff[:4])) if diff else ''))

    if want('Q4'):
        fr = subprocess.run(['git', '-C', REPO, 'diff', '--stat', '--', 'calibrator/runs/H0_FRAMES_2026-09-27.json'], capture_output=True, text=True).stdout.strip()
        hz = subprocess.run(['git', '-C', REPO, 'diff', '-U0', '--', 'data/hst-3i/horizons/3I_from_HST_psang_2026-09-27.txt'],
                            capture_output=True, text=True).stdout
        changed = [l[1:] for l in hz.splitlines() if l[:1] in '+-' and not l.startswith(('+++', '---'))]
        known = all(re.match(r'(Ephemeris / API_USER|EOP file|EOP coverage)', l) for l in changed)
        verdict('Q4', not fr and known and len(changed) == 6, 'H0_FRAMES: %s | the Horizons table: %d lines changed, all three known header '
                'lines: %s' % ('unchanged' if not fr else fr, len(changed), known))

    if want('Q5'):
        t0 = time.time()
        p1 = subprocess.Popen([PY, os.path.join(RUNS, 'hard_c1.py'), os.path.join(OUT, 'C1.txt')], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        p2 = subprocess.Popen([PY, os.path.join(RUNS, 'hard_c2.py'), os.path.join(OUT, 'C2.txt')], cwd=REPO, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        r1, r2 = p1.wait(), p2.wait()
        c1 = open(os.path.join(OUT, 'C1.txt')).read(); c2 = open(os.path.join(OUT, 'C2.txt')).read()
        bar = re.search(r'^# BAR .*: (PASS|FAIL)$', c1, flags=re.M)
        kinds = re.search(r'^# the differences: (\d+) REPORTING, (\d+) FITTED$', c2, flags=re.M)
        ref = open(os.path.join(RUNS, 'ANY_C2_RUNLOG_2026-09-29.txt')).read()
        rep = lambda t: sorted(l for l in t.splitlines() if l.startswith('  REPORTING'))
        same43 = rep(c2) == rep(ref) and len(rep(ref)) == 43
        ok = r1 == 0 and r2 == 0 and bar and bar.group(1) == 'PASS' and kinds and kinds.group(2) == '0' and same43
        verdict('Q5', bool(ok), 'C1 %s | C2 %s REPORTING, %s FITTED, the same 43 as the thirteenth room\'s: %s | %.0f s' % (
            bar.group(1) if bar else 'no BAR line', kinds.group(1) if kinds else '?', kinds.group(2) if kinds else '?', same43, time.time() - t0))

    names = [n for n in ('Q0', 'Q1', 'Q2', 'Q3', 'Q4', 'Q5') if n in RESULTS]
    met = sum(1 for n in names if RESULTS[n])
    print('# positions bar: %s, %d of %d%s' % ('MET' if met == len(names) else 'NOT MET', met, len(names),
                                                '' if met == len(names) else ' (failing: %s)' % ' '.join(n for n in names if not RESULTS[n])))


if __name__ == '__main__':
    main()
