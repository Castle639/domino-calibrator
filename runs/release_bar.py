#!/usr/bin/env python3
"""Launch step 6's bar: the public repository's files, curated, built as a folder (the launch list's step 6; the brief's §3,
calls 3-6). Written before the folder is built (30 Sept 2026, the calibrator's build room). It names no word it checks for:
the patterns, each with a file of the Castle's that must hit it, come from a file kept outside the folder (CHECKS), whose
content the room's report records.

The clauses:
  S0  control: every pattern in CHECKS hits its own control file (the Castle's original) at least once
  S1  the folder's files: every file git tracks in calibrator/, the records named in CHECKS in archive/, the two tools each
      naming its source and commit, the checksum list with exactly the positions file's 30 frames, the Horizons table, a
      .gitignore; and no other file
  S2  the package: every module byte-identical to calibrator/'s, but those CHECKS names as curated, whose differing lines are
      each a line that held a pattern
  S3  the name check: no pattern of CHECKS matches in the folder, byte-safe; beside it, each kept name's count
  S4  the suite, `python -m tests.strict`, in a copy of the folder with the frames linked into its data/hst-3i/ (the public
      arrangement), on the kit with the tested-versions flag: PASS, 0/0/0
  S5  from that copy, C1 bit for bit and C2 with 0 FITTED and the same 43 (the public repository's own science controls)

Amendment 1 (the bridge's catch, 30 Sept 2026, 1 of 2): the first patterns carried each name as a full path, and S0's
control never tested a bare stem, so bare names passed S3 unseen. CHECKS now carries every trimmed name's bare stem too, and
each pattern a "plant": a bare form, as it stands in a log's pattern string or in prose. S0 also plants every plant in a
copy of the folder, in a runs/ log and in a tools/ script, and asks that S3's own scan finds each pattern there twice more
than in the folder itself, and that each pattern hits its own plant. S3 counts through the same scan.

Amendment 2 (the fix room, 1 Oct 2026, 2 of 2; the fix room's record of 1 Oct 2026, not in this repository, section 8): his word on item
18 leaves files out of the folder, and item 22 names the tools' source in public words. S1 reads both from CHECKS: the files
it expects are calibrator/'s tracked files but CHECKS' "left_out", and the tools' line is CHECKS' "tools_phrase" (the old
phrase when CHECKS has none, so that the launch room's checks still read as they did).

Usage: python calibrator/runs/release_bar.py SCRATCH REPO TESTED_PYTHON FOLDER CHECKS.json [CLAUSES]
"""
import os, re, sys, json, time, shutil, hashlib, tempfile, subprocess

SCRATCH, REPO, PY, FOLDER, CHECKS = sys.argv[1:6]
ONLY = set(sys.argv[6].split(',')) if len(sys.argv) > 6 else None
CK = json.load(open(CHECKS, encoding='utf-8'))
PKG = os.path.join(REPO, 'calibrator')
OUT = os.path.join(SCRATCH, 'release_bar')
BINARY = ('.png', '.woff2', '.gz', '.fits', '.npz', '.ico', '.pdf')
STRICT = re.compile(r'^strict: (PASS|FAIL) \((\d+) run, (\d+) failures, (\d+) errors, (\d+) skipped: (\d+) allowed, (\d+) not\)', re.M)
RESULTS = {}


def verdict(name, ok, detail):
    RESULTS[name] = ok
    print('%-3s %s  %s' % (name, 'PASS' if ok else 'FAIL', detail), flush=True)


def want(name):
    return ONLY is None or name in ONLY


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


def rx(c):
    return re.compile(c['pattern'], re.I if 'i' in c.get('flags', '') else 0)


def scan(root, absent):
    """S3's count of each pattern in the folder at root, byte-safe: {what: matches}."""
    found = {}
    for rel, t in texts(root):
        for c in absent:
            n = len(rx(c).findall(t))
            if n:
                found[c['what']] = found.get(c['what'], 0) + n
    return found


def planted(absent):
    """Amendment 1: every pattern's plant, planted in a copy of the folder (a runs/ log's pattern strings and a tools/ script's
    comments); the patterns S3's scan does not find there twice more than in the folder, or that miss their own plant."""
    d = tempfile.mkdtemp(prefix='release_plant_', dir=OUT)
    try:
        cp = os.path.join(d, 'copy')
        shutil.copytree(FOLDER, cp)
        with open(os.path.join(cp, 'runs', 'PLANTED_RUNLOG_2026-09-30.txt'), 'w', encoding='utf-8') as f:
            f.write(''.join(' 1 Grep  ok  calibrator  pattern=%s| len 9\n' % c['plant'] for c in absent))
        with open(os.path.join(cp, 'tools', 'fetch_frames.py'), 'a', encoding='utf-8') as f:
            f.write('\n' + ''.join('# %s\n' % c['plant'] for c in absent))
        before, after = scan(FOLDER, absent), scan(cp, absent)
        return [c['what'] for c in absent if not rx(c).search(c.get('plant', '')) or after.get(c['what'], 0) - before.get(c['what'], 0) < 2]
    finally:
        shutil.rmtree(d, ignore_errors=True)


def main():
    os.makedirs(OUT, exist_ok=True)
    print('# release bar %s UTC | HEAD %s | the folder %s' % (time.strftime('%F %T', time.gmtime()), subprocess.run(
        ['git', '-C', REPO, 'log', '-1', '--format=%h'], capture_output=True, text=True).stdout.strip(), os.path.relpath(FOLDER, REPO)), flush=True)
    absent = CK['absent']

    if want('S0'):
        misses = []
        for c in absent:
            t = open(os.path.join(REPO, c['control']), encoding='utf-8').read()
            if not rx(c).search(t):
                misses.append(c['what'])
        unplanted = planted(absent)
        verdict('S0', not misses and not unplanted and len(absent) > 0, '%d patterns, each hitting its control: %s | each found '
                'where its bare form is planted, in a copy of the folder (a runs/ log and a tools/ script): %s' % (
                    len(absent), 'yes' if not misses else 'NO for ' + ', '.join(misses),
                    'yes' if not unplanted else 'NO for ' + ', '.join(unplanted)))

    if want('S1'):
        want_files = {f[len('calibrator/'):] for f in subprocess.run(['git', '-C', REPO, 'ls-files', 'calibrator'], capture_output=True,
                                                                     text=True).stdout.split('\n') if f}
        want_files -= set(CK.get('left_out', []))                          # amendment 2: his item 18, the files left out
        want_files |= {'archive/' + r for r in CK['records']} | {'tools/fetch_frames.py', 'tools/psfkit.py', 'data/hst-3i/CHECKSUMS.sha256',
                                                                 'data/hst-3i/horizons/3I_from_HST_psang_2026-09-27.txt', '.gitignore'}
        have = set()
        for dp, dn, fn in os.walk(FOLDER):
            for f in fn:
                have.add(os.path.relpath(os.path.join(dp, f), FOLDER))
        frames = [l.split()[0] for l in open(os.path.join(PKG, 'runs', 'H0_POSITIONS_2026-09-30.txt')) if l.strip() and not l.startswith('#')]
        sums = [l.split()[-1].lstrip('*') for l in open(os.path.join(FOLDER, 'data', 'hst-3i', 'CHECKSUMS.sha256')) if l.strip()] \
            if os.path.exists(os.path.join(FOLDER, 'data', 'hst-3i', 'CHECKSUMS.sha256')) else []
        phrase = CK.get('tools_phrase', r"copied from the Castle's own at [0-9a-f]{7}")        # amendment 2: item 22's words
        tools_named = all(os.path.exists(os.path.join(FOLDER, t)) and re.search(phrase,
                          open(os.path.join(FOLDER, t), encoding='utf-8').read()) for t in ('tools/fetch_frames.py', 'tools/psfkit.py'))
        ok = have == want_files and sorted(os.path.basename(s)[:-len('_flc.fits')] for s in sums) == sorted(frames) and tools_named
        verdict('S1', ok, '%d files, missing %d, extra %d%s | the checksum list: %d lines, the positions file\'s 30 frames: %s | the tools '
                'name their source and commit: %s' % (len(have), len(want_files - have), len(have - want_files),
                (' (extra: %s)' % ', '.join(sorted(have - want_files)[:4])) if have - want_files else '', len(sums),
                sorted(os.path.basename(s)[:-len('_flc.fits')] for s in sums) == sorted(frames), bool(tools_named)))

    if want('S2'):
        rows, ok = [], True
        pats = [rx(c) for c in absent]
        for f in sorted(os.listdir(os.path.join(PKG, 'domino_calibrator'))):
            if not f.endswith('.py'):
                continue
            a = open(os.path.join(PKG, 'domino_calibrator', f), encoding='utf-8').read().splitlines()
            b = open(os.path.join(FOLDER, 'domino_calibrator', f), encoding='utf-8').read().splitlines() \
                if os.path.exists(os.path.join(FOLDER, 'domino_calibrator', f)) else None
            if b == a:
                continue
            curated = f in CK.get('curated_modules', [])
            only_named = b is not None and len(a) == len(b) and all(x == y or any(p.search(x) for p in pats) for x, y in zip(a, b))
            ok = ok and curated and only_named
            rows.append('%s differs (%s)' % (f, 'each differing line held a pattern' if only_named else 'NOT only curated lines'))
        verdict('S2', ok, 'modules byte-identical but: %s' % ('; '.join(rows) or 'none'))

    if want('S3'):
        found = scan(FOLDER, absent)                                        # amendment 1: the same scan S0's plants go through
        kept = {}
        for rel, t in texts(FOLDER):
            for k in CK.get('kept', []):
                kept[k['what']] = kept.get(k['what'], 0) + len(re.findall(k['pattern'], t))
        verdict('S3', not found, 'patterns matching in the folder: %s | kept, for the record: %s' % (
            ', '.join('%s %d' % kv for kv in sorted(found.items())) or 'none', ', '.join('%s %d' % kv for kv in sorted(kept.items())) or 'none'))

    copy = os.path.join(OUT, 'public_copy')
    if want('S4') or want('S5'):
        shutil.rmtree(copy, ignore_errors=True)
        shutil.copytree(FOLDER, copy)
        for f in sorted(os.listdir(os.path.join(REPO, 'data', 'hst-3i'))):
            if f.endswith('_flc.fits') and os.path.basename(f)[:-len('_flc.fits')] in [l.split()[0] for l in open(os.path.join(copy, 'runs', 'H0_POSITIONS_2026-09-30.txt')) if l.strip() and not l.startswith('#')]:
                os.symlink(os.path.join(REPO, 'data', 'hst-3i', f), os.path.join(copy, 'data', 'hst-3i', f))

    if want('S4'):
        e = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'VIRTUAL_ENV')}
        e.update(ADES_PYLIB=os.path.join(SCRATCH, 'pylib'), ADES_MASTER=os.path.join(SCRATCH, 'ades-master'),
                 PLAYWRIGHT_MODULE='/opt/node22/lib/node_modules/playwright', DOMINO_CALIBRATOR_TESTED_VERSIONS='1',
                 PATH=os.path.dirname(PY) + os.pathsep + '/opt/node22/bin' + os.pathsep + os.environ.get('PATH', ''))
        t0 = time.time()
        c = subprocess.run([PY, '-m', 'tests.strict'], cwd=copy, env=e, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, timeout=5400)
        open(os.path.join(OUT, 'suite_S4.txt'), 'w').write(c.stdout)
        m = STRICT.search(c.stdout)
        verdict('S4', bool(m) and m.group(1) == 'PASS' and c.returncode == 0 and m.group(3) == m.group(4) == m.group(5) == '0',
                '%s | exit %d, %.0f s' % (m.group(0) if m else 'no strict summary', c.returncode, time.time() - t0))

    if want('S5'):
        t0 = time.time()
        p1 = subprocess.Popen([PY, os.path.join(copy, 'runs', 'hard_c1.py'), os.path.join(OUT, 'C1.txt')], cwd=copy, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        p2 = subprocess.Popen([PY, os.path.join(copy, 'runs', 'hard_c2.py'), os.path.join(OUT, 'C2.txt')], cwd=copy, stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)
        r1, r2 = p1.wait(), p2.wait()
        c1 = open(os.path.join(OUT, 'C1.txt')).read(); c2 = open(os.path.join(OUT, 'C2.txt')).read()
        bar = re.search(r'^# BAR .*: (PASS|FAIL)$', c1, flags=re.M)
        kinds = re.search(r'^# the differences: (\d+) REPORTING, (\d+) FITTED$', c2, flags=re.M)
        rep = lambda t: sorted(l for l in t.splitlines() if l.startswith('  REPORTING'))
        same43 = rep(c2) == rep(open(os.path.join(PKG, 'runs', 'ANY_C2_RUNLOG_2026-09-29.txt')).read()) and len(rep(c2)) == 43
        verdict('S5', r1 == 0 and r2 == 0 and bool(bar) and bar.group(1) == 'PASS' and bool(kinds) and kinds.group(2) == '0' and same43,
                'C1 %s | C2 %s REPORTING, %s FITTED, the same 43: %s | %.0f s' % (bar.group(1) if bar else '?', kinds.group(1) if kinds else '?',
                                                                                  kinds.group(2) if kinds else '?', same43, time.time() - t0))

    names = [n for n in ('S0', 'S1', 'S2', 'S3', 'S4', 'S5') if n in RESULTS]
    met = sum(1 for n in names if RESULTS[n])
    print('# release bar: %s, %d of %d%s' % ('MET' if met == len(names) else 'NOT MET', met, len(names),
                                              '' if met == len(names) else ' (failing: %s)' % ' '.join(n for n in names if not RESULTS[n])))


if __name__ == '__main__':
    main()
