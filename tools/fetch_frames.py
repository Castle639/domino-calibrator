#!/usr/bin/env python3
"""tools/fetch_frames.py (copied from its makers' private repository at b1da95b, curated for this one) - bring HST frames from MAST, each one checked against data/hst-3i/CHECKSUMS.sha256.

24 Sept 2026. A Castle product from Domino Observatory. Built by Annie, the Castle's AI. The frames are gitignored (the study's 30 are 42.2 MB each), so every new
machine fetches its own; a frame is believed only after its sha256 matches the committed list (the study's
data-integrity rule). Lessons carried: a download runs in the foreground only, lands under a temporary name,
and takes its real name only after the checksum matches; a mismatch is deleted, never kept.

    python3 tools/fetch_frames.py ROOTNAME|VISIT ...      e.g. ifle22f7q  or  22 03
    python3 tools/fetch_frames.py --all
    python3 tools/fetch_frames.py --self-test              the control, no network

A frame already on disk with the right checksum is not fetched again. Prints, per frame: OK / PRESENT /
MISMATCH (deleted) / FAILED, with bytes, seconds and MB/s. Exit 0 only if every requested frame ends OK or PRESENT.
"""
import hashlib, os, re, subprocess, sys, tempfile, time

DIR = 'data/hst-3i'
SUMS = os.path.join(DIR, 'CHECKSUMS.sha256')
URL = 'https://mast.stsci.edu/api/v0.1/Download/file?uri=mast:HST/product/{name}'

def sha256(path):
    h = hashlib.sha256()
    with open(path, 'rb') as f:
        for block in iter(lambda: f.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()

def listed():
    out = {}
    for line in open(SUMS, encoding='utf-8'):
        m = re.match(r'([0-9a-f]{64})\s+\*?(\S+)', line.strip())
        if m:
            out[os.path.basename(m.group(2))] = (m.group(1), m.group(2))
    return out

def settle(part, final, want):
    """The one gate: the temporary file becomes the frame only if its checksum matches; otherwise it is deleted."""
    got = sha256(part)
    if got == want:
        os.replace(part, final)
        return 'OK'
    os.remove(part)
    return 'MISMATCH'

def fetch(name, want, rel):
    final = os.path.join(DIR, rel)
    if os.path.exists(final) and sha256(final) == want:
        return 'PRESENT', 0, 0.0
    os.makedirs(os.path.dirname(final), exist_ok=True)
    part = final + '.part'
    if os.path.exists(part):
        os.remove(part)
    t0 = time.time()
    run = subprocess.run(['curl', '-sS', '-f', '-L', '--retry', '3', '--retry-delay', '2', '--max-time', '1800',
                          '-o', part, URL.format(name=name)], capture_output=True, text=True)
    dt = time.time() - t0
    if run.returncode != 0 or not os.path.exists(part):
        if os.path.exists(part):
            os.remove(part)
        return 'FAILED (curl ' + str(run.returncode) + ': ' + run.stderr.strip()[-120:] + ')', 0, dt
    size = os.path.getsize(part)
    return settle(part, final, want), size, dt

def self_test():
    ok = True
    with tempfile.TemporaryDirectory() as d:
        good = os.path.join(d, 'frame.fits'); open(good + '.part', 'wb').write(b'SIMPLE  = T' + b' ' * 2869)
        want = sha256(good + '.part')
        r1 = settle(good + '.part', good, want)
        bad = os.path.join(d, 'other.fits'); open(bad + '.part', 'wb').write(b'SIMPLE  = T' + b' ' * 2868 + b'!')
        r2 = settle(bad + '.part', bad, want)
        cases = [('right checksum', r1, 'OK', os.path.exists(good)), ('one byte off', r2, 'MISMATCH', not os.path.exists(bad) and not os.path.exists(bad + '.part'))]
        for name, got, expect, files_ok in cases:
            print(f'  {name:16s} -> {got:9s} want {expect:9s} files as they should be: {files_ok}  {"OK" if got == expect and files_ok else "FAIL"}')
            ok &= got == expect and files_ok
    print(f'  self-test: {"PASS" if ok else "FAIL"}')
    return 0 if ok else 1

def main(argv):
    if argv[:1] == ['--self-test']:
        return self_test()
    frames = listed()
    if argv[:1] == ['--all']:
        wanted = sorted(frames)
    else:
        wanted = sorted(n for n in frames for a in argv if n.startswith(a) or n.startswith('ifle' + a))
    if not wanted:
        print(__doc__); return 2
    total_b, total_t, bad = 0, 0.0, 0
    for n in wanted:
        verdict, size, dt = fetch(n, *frames[n])
        total_b += size; total_t += dt
        rate = f'{size / 1e6 / dt:6.1f} MB/s' if size and dt else '      -'
        print(f'  {n:24s} {verdict:10s} {size / 1e6:8.1f} MB {dt:7.1f} s {rate}')
        bad += not verdict.startswith(('OK', 'PRESENT'))
    print(f'  {len(wanted)} frames, {len(wanted) - bad} OK or present, {bad} not | fetched {total_b / 1e6:.1f} MB in {total_t:.1f} s')
    return 0 if not bad else 1

if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
