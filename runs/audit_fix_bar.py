#!/usr/bin/env python3
"""The bar for the audit room's blockers B1 and B2 (30 Sept 2026, night; the calibrator's launch room, at his word).
The findings: the audit room's record of 30 Sept 2026, not in this repository. The tests: tests/test_audit_blockers.py.

  python runs/audit_fix_bar.py AUDIT_INPUTS LOG      from the repository's root; AUDIT_INPUTS holds the audit room's own
                                                     inputs as its scripts made them (h/, h2/; mk_inputs.py, C1_mkwhole.py,
                                                     C1_mkcuts.py, read from its folder), with ADES_PYLIB, ADES_MASTER and
                                                     PLAYWRIGHT_MODULE set

  X0  the control: the tests' fixtures are what they say (the saturated frame peaks at the ceiling, 65535; the automatic
      start takes the brighter star; the good image gives 41 of 41 radii), so a pass below is not an empty fixture's
  X1  B1: tests/test_audit_blockers.py's B1 on the command line, the page's engine and the page in Chromium
  X2  B2: its B2 on the three
  X3  the audit room's own inputs, on the command line and the page's engine: its four broken WCS, no sky position and no
      record, the pixel answer standing; its constant image, its two whole frames from the automatic start (a saturated
      star), its cutout from starts 5 px off and from (40, 61) (C1.25d, the run-to-run spread), no record; its cutout on
      the comet and from the automatic start, and its good image, a record
  X4  the study: all 30 of its frames, G and M, from the study's own starts (runs/H0_POSITIONS_2026-09-30.txt): a record each
  X5  the whole suite, strict, on the kit with the tested versions' flag: PASS
"""
import os, re, sys, json, hashlib, subprocess, warnings
import numpy as np
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
A, LOG = sys.argv[1], sys.argv[2]
out = open(LOG, 'w', encoding='utf-8')


def say(s):
    print(s); out.write(s + '\n'); out.flush()


def run(args, env=None, timeout=3600):
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run(args, cwd=ROOT, env=e, capture_output=True, encoding='utf-8', errors='replace', timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def unit(test):
    rc, o = run([sys.executable, '-m', 'unittest', test])
    return rc == 0, (re.findall(r'^(OK.*|FAILED.*)$', o, re.M) or ['?'])[-1], o


def main():
    import warnings
    warnings.simplefilter('ignore')
    from tests.test_hardening import REC_ARGS, run_main
    from tests import test_audit_blockers as T
    from domino_calibrator import cli
    from domino_calibrator.hst import DATA          # amendment 1 (1 of 2): the frames where the package finds them
    from astropy.io import fits
    head = run(['git', 'rev-parse', '--short', 'HEAD'])[1].strip()
    say('# audit_fix_bar | HEAD %s | its sha256 %s' % (head, hashlib.sha256(open(__file__, 'rb').read()).hexdigest()))
    v = []
    # X0
    import tempfile, shutil
    d = tempfile.mkdtemp()
    try:
        f = T.make_images(d)
        fr = fits.getdata(f['a saturated star, automatic'][0])
        sat = int(fr.max()) == 65535
        s_star = cli._start(fits.getdata(f['a brighter star, automatic'][0]).astype(float))
        star = abs(s_star[0] - 20) <= 1 and abs(s_star[1] - 81) <= 1
        g = cli.measure_file(f['good'][0])
        g41 = int(np.sum(g['curve']['ok'])) == 41
    finally:
        shutil.rmtree(d, ignore_errors=True)
    ok = sat and star and g41
    say('X0  %s  the saturated frame peaks at 65535: %s | the automatic start takes the brighter star: %s %s | the good image 41 of 41: %s'
        % ('PASS' if ok else 'FAIL', sat, star, tuple(s_star), g41)); v.append(ok)
    # X1, X2
    ok1, t1, _ = unit('tests.test_audit_blockers.TestB1TheCommandLine')
    ok2, t2, _ = unit('tests.test_audit_blockers.TestB2TheCommandLine')
    oke, te, _ = unit('tests.test_audit_blockers.TestTheEngine')
    okp, tp, _ = unit('tests.test_audit_blockers.TestThePage')
    say('X1  %s  B1 on the command line: %s | the engine (B1 and B2, and the same words): %s | the page: %s' % ('PASS' if ok1 and oke and okp else 'FAIL', t1, te, tp))
    say('X2  %s  B2 on the command line: %s | the engine: %s | the page: %s' % ('PASS' if ok2 and oke and okp else 'FAIL', t2, te, tp))
    v += [ok1 and oke and okp, ok2 and oke and okp]
    # X3
    H, H2 = os.path.join(A, 'h'), os.path.join(A, 'h2')
    cases = {'cd_zero': (H + '/cd_zero.fits', None, 'sky'), 'cd_singular': (H + '/cd_singular.fits', None, 'sky'),
             'sip_huge': (H + '/sip_huge.fits', None, 'sky'), 'crpix_str': (H + '/crpix_str.fits', None, 'sky'),
             'const': (H + '/const.fits', None, 'comet'), 'w6248 automatic': (H2 + '/w6248.fits', None, 'comet'),
             'w4096 automatic': (H2 + '/w4096.fits', None, 'comet'), 'c101 +5 +0': (H2 + '/c101.fits', (55.35, 49.55), 'comet'),
             'c101 +0 -5': (H2 + '/c101.fits', (50.35, 44.55), 'comet'), 'c101 (40, 61)': (H2 + '/c101.fits', (40.0, 61.0), 'comet'),
             'c101 on the comet': (H2 + '/c101.fits', (50.35, 49.55), None), 'c101 automatic': (H2 + '/c101.fits', None, None),
             'good': (H + '/good.fits', None, None)}
    ref = None
    lines, ok = [], True
    for name, (p, s, want) in cases.items():
        rc, o = run_main([p] + ([] if s is None else ['--x', repr(s[0]), '--y', repr(s[1])]) + REC_ARGS)
        rec = '# version=2022' in o
        why = re.search(r'# no ADES record: needs (.*)', o)
        z = T.zero(o)
        if name == 'good':
            ref = z
        good = (rec if want is None else (not rec and why and why.group(1).startswith('a %s' % ('sky position (the WCS' if want == 'sky' else 'comet measured ('))))
        ok = ok and bool(good)
        lines.append('    %-4s %-18s %s' % ('ok' if good else 'BAD', name, 'record' if rec else (why.group(1)[:150] if why else 'no reason')))
    wz = [T.zero(run_main([cases[n][0]] + REC_ARGS)[1]) for n in ('cd_zero', 'cd_singular', 'sip_huge', 'crpix_str')]
    stands = all(z == ref for z in wz)
    try:
        pg = T.page_decide({n: (c[0], c[1]) for n, c in cases.items()})
        pok = all((pg[n]['need'] == []) if c[2] is None else any(x.startswith('a %s' % ('sky position (the WCS' if c[2] == 'sky' else 'comet measured (')) for x in pg[n]['need'])
                  for n, c in cases.items())
        pw = ', '.join('%s: %s' % (n, 'record' if not pg[n]['need'] else pg[n]['need'][0][:60]) for n in cases)
    except Exception as e:
        pok, pw = False, 'the engine failed: %s' % str(e)[:200]
    ok = ok and stands and pok
    say('X3  %s  the audit\'s own inputs, the command line: as wanted %s | the pixel answer stands on the four WCS: %s | the page\'s engine: %s'
        % ('PASS' if ok else 'FAIL', all(l.startswith('    ok') for l in lines), stands, pok))
    for l in lines:
        say(l)
    say('    the engine: ' + pw)
    v.append(ok)
    # X4
    pos = [l.split() for l in open(os.path.join(ROOT, 'runs', 'H0_POSITIONS_2026-09-30.txt'), encoding='utf-8') if l.strip() and not l.startswith('#')]
    got, miss = 0, []
    for root, x, y in pos:
        for est in ('G', 'M'):
            o = run_main([os.path.join(DATA, root + '_flc.fits'), '--x', x, '--y', y, '--estimator', est] + REC_ARGS)[1]   # amendment 1: hst.DATA
            if '# version=2022' in o:
                got += 1
            else:
                miss.append('%s %s: %s' % (root, est, (re.search(r'# no ADES record: (.*)', o) or re.search(r'(.{0,120})$', o)).group(1)[:120]))
    ok = got == 60
    say('X4  %s  the study\'s 30 frames, G and M, from its own starts: %d of 60 records' % ('PASS' if ok else 'FAIL', got))
    for m in miss[:6]:
        say('        ' + m)
    v.append(ok)
    # X5
    rc, o = run([sys.executable, '-m', 'tests.strict'], env=dict(DOMINO_CALIBRATOR_TESTED_VERSIONS='1'))
    line = (re.findall(r'^strict: .*$', o, re.M) or ['strict: no verdict'])[-1]
    bad = re.findall(r'^(?:FAIL|ERROR): (\S+ \([^)]*\))', o, re.M)
    ok = rc == 0 and line.startswith('strict: PASS')
    say('X5  %s  the whole suite: %s' % ('PASS' if ok else 'FAIL', line))
    for b in bad[:40]:
        say('        failed: ' + b)
    v.append(ok)
    met = sum(v)
    say('# audit fix bar: %s, %d of %d' % ('MET' if met == len(v) else 'NOT MET', met, len(v)))
    return 0 if met == len(v) else 1


if __name__ == '__main__':
    sys.exit(main())
