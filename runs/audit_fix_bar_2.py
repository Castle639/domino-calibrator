#!/usr/bin/env python3
"""The small new bar for the audit room's blockers B1 and B2 (1 Oct 2026, morning; the calibrator's launch room, at his word).
The first bar, runs/audit_fix_bar.py, stays NOT MET, 5 of 6, on record (runs/AUDITFIX_GREEN_RUNLOG_2026-09-30.txt): its X3
asked the page's engine for an answer on the audit's 26 Mpx frame (w6248), which the page refuses at loading by design (its
25 Mpx limit, page/zeroap.js MAX_PIXELS), and the harness read data that was never decoded. His answer: a new small bar whose
harness respects the page's limit, with its own clause for the frame the page refuses at loading.

  python runs/audit_fix_bar_2.py AUDIT_INPUTS LOG      from the repository's root; AUDIT_INPUTS holds the audit room's inputs
                                                       (h/, h2/), with ADES_PYLIB, ADES_MASTER and PLAYWRIGHT_MODULE set

  Z0  the control, run first: the harness's own loading, through the page's parseFITS, marks w6248 too big (nx * ny over
      MAX_PIXELS, no readable image) and w4096 readable; so a frame the harness skips is one the page itself refuses
  Z1  the clause for the refused frame: the page in Chromium, loading w6248, says "too big for the page", offers no record
      (Copy disabled, no ADES line) and no zero-aperture position; the command line on w6248 writes no record
  Z2  the audit's other 12 inputs (its four broken WCS, its constant image, w4096 from the automatic start, its cutout from
      three starts off the comet, on the comet and from the automatic start, and its good image), on the command line and
      the page's engine: the same decision on both (no sky position for the four WCS; no comet measured for the six;
      a record for the three), and the pixel answer stands on the four WCS
  Z3  the whole suite, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
"""
import os, re, sys, json, shutil, hashlib, tempfile, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
A, LOG = sys.argv[1], sys.argv[2]
out = open(LOG, 'w', encoding='utf-8')
SKY, COMET = 'a sky position (the WCS', 'a comet measured ('


def say(s):
    print(s); out.write(s + '\n'); out.flush()


def run(args, env=None, timeout=3600):
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run(args, cwd=ROOT, env=e, capture_output=True, encoding='utf-8', errors='replace', timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def loading(paths):
    """The page's own loading of each file: {path: {'tooBig', 'readable', 'nx', 'ny'}}, through parseFITS alone."""
    from tests.test_audit_blockers import js
    return js("""
const fs = require('fs'); out = {};
for (const p of D) {
  const hdus = Z.parseFITS(new Uint8Array(fs.readFileSync(p)).buffer);
  const big = hdus.find((u) => u.tooBig), cur = hdus.find((u) => u.readable);
  out[p] = { tooBig: !!big, readable: !!cur, nx: (big || cur || {}).nx, ny: (big || cur || {}).ny, max: Z.MAX_PIXELS };
}""", paths, timeout=600)


def engine(files):
    """The page's engine on each file the page loads, as its page decides: {name: {need, rd}}; a file the page refuses at
    loading is not measured (the harness respects the 25 Mpx limit): {name: {'refused': True}}."""
    from tests.test_audit_blockers import js
    return js("""
const fs = require('fs'); out = {};
for (const [name, c] of Object.entries(D)) {
  const hdus = Z.parseFITS(new Uint8Array(fs.readFileSync(c.path)).buffer);
  const cur = hdus.find((u) => u.readable);
  if (!cur) { out[name] = { refused: true }; continue; }
  const auto = c.start === null;
  const s = auto ? Z.brightestStart(cur.data, cur.nx, cur.ny) : c.start;
  const o = Z.shrink(cur.data, cur.nx, cur.ny, s[0], s[1], { estimator: 'G', radii: Z.publishedRadii(), background: 'annulus' });
  const r = Z.decide({ cur: cur, hdus: hdus, o: o, start: s, auto: auto });
  out[name] = { need: r.need, rd: r.rd };
}""", {n: {'path': p, 'start': s} for n, (p, s) in files.items()}, timeout=900)


def main():
    import warnings
    warnings.simplefilter('ignore')
    from tests.test_hardening import REC_ARGS, run_main
    from tests import test_audit_blockers as T
    head = run(['git', 'rev-parse', '--short', 'HEAD'])[1].strip()
    say('# audit_fix_bar_2 | HEAD %s | its sha256 %s' % (head, hashlib.sha256(open(__file__, 'rb').read()).hexdigest()))
    H, H2 = os.path.join(A, 'h'), os.path.join(A, 'h2')
    W6248, W4096 = os.path.join(H2, 'w6248.fits'), os.path.join(H2, 'w4096.fits')
    v = []
    # Z0, the control
    try:
        ld = loading([W6248, W4096])
        a, b = ld[W6248], ld[W4096]
        ok = a['tooBig'] and not a['readable'] and a['nx'] * a['ny'] > a['max'] and b['readable'] and not b['tooBig']
        say('Z0  %s  the harness\'s loading, the page\'s parseFITS: w6248 %dx%d = %.1f Mpx, too big %s, readable %s | '
            'w4096 %dx%d, readable %s, too big %s | the limit %.0f Mpx'
            % ('PASS' if ok else 'FAIL', a['nx'], a['ny'], a['nx'] * a['ny'] / 1e6, a['tooBig'], a['readable'],
               b['nx'], b['ny'], b['readable'], b['tooBig'], a['max'] / 1e6))
    except Exception as e:
        ok = False
        say('Z0  FAIL  the harness\'s loading failed: %s' % str(e)[:300])
    v.append(ok)
    # Z1, the clause for the refused frame
    d = tempfile.mkdtemp(prefix='afb2_')
    try:
        cases = [{'name': 'w6248', 'steps': [{'file': W6248, 'set': dict(T.REC_PAGE), 'wait': 60000}]}]
        cp = os.path.join(d, 'cases.json'); json.dump(cases, open(cp, 'w', encoding='utf-8'))
        r = subprocess.run([T.NODE, os.path.join(T.PAGE, 'browser_cases.js'), cp], capture_output=True, encoding='utf-8',
                           errors='replace', timeout=900, env=dict(os.environ, PLAYWRIGHT_MODULE=T.PW))
        st = json.loads(r.stdout)[0]['steps'][-1]
        refused = 'too big for the page' in st['info']
        nothing = st['copyDisabled'] and '# version=2022' not in st['ades'] and 'Zero-aperture position' not in st['zero']
        page = 'info "%s" | Copy disabled %s | ADES "%s" | zero "%s"' % (st['info'][:120], st['copyDisabled'], st['ades'][:60], st['zero'][:60])
    except Exception as e:
        refused = nothing = False
        page = 'the page failed: %s' % str(e)[:300]
    finally:
        shutil.rmtree(d, ignore_errors=True)
    rc, o = run_main([W6248] + REC_ARGS)
    cli_none = '# version=2022' not in o
    why = re.search(r'# no ADES record: needs (.*)', o)
    ok = refused and nothing and cli_none
    say('Z1  %s  the page refuses w6248 at loading: %s, and offers nothing: %s | the command line writes no record: %s (%s)'
        % ('PASS' if ok else 'FAIL', refused, nothing, cli_none, why.group(1)[:120] if why else 'no reason line'))
    say('    the page: ' + page)
    v.append(ok)
    # Z2, the other 12 inputs on both faces
    cases = {'cd_zero': (H + '/cd_zero.fits', None, SKY), 'cd_singular': (H + '/cd_singular.fits', None, SKY),
             'sip_huge': (H + '/sip_huge.fits', None, SKY), 'crpix_str': (H + '/crpix_str.fits', None, SKY),
             'const': (H + '/const.fits', None, COMET), 'w4096 automatic': (W4096, None, COMET),
             'c101 +5 +0': (H2 + '/c101.fits', (55.35, 49.55), COMET), 'c101 +0 -5': (H2 + '/c101.fits', (50.35, 44.55), COMET),
             'c101 (40, 61)': (H2 + '/c101.fits', (40.0, 61.0), COMET), 'c101 on the comet': (H2 + '/c101.fits', (50.35, 49.55), None),
             'c101 automatic': (H2 + '/c101.fits', None, None), 'good': (H + '/good.fits', None, None)}
    try:
        pg = engine({n: (c[0], c[1]) for n, c in cases.items()})
    except Exception as e:
        pg, perr = {}, str(e)[:300]
    else:
        perr = None
    lines, okc, okp = [], True, perr is None
    zs = {}
    for name, (p, s, want) in cases.items():
        rc, o = run_main([p] + ([] if s is None else ['--x', repr(s[0]), '--y', repr(s[1])]) + REC_ARGS)
        zs[name] = T.zero(o)
        rec = '# version=2022' in o
        m = re.search(r'# no ADES record: needs (.*)', o)
        c_ok = rec if want is None else (not rec and bool(m) and m.group(1).startswith(want))
        e = pg.get(name)
        if e is None or e.get('refused'):
            p_ok, pw = False, ('refused at loading' if e else 'no answer')
        else:
            p_ok = (e['need'] == []) if want is None else any(x.startswith(want) for x in e['need'])
            if want == SKY:
                p_ok = p_ok and e['rd'] is None
            pw = 'record' if not e['need'] else e['need'][0][:70]
        okc, okp = okc and c_ok, okp and p_ok
        lines.append('    %-3s %-3s %-18s cli: %-70s | engine: %s' % ('ok' if c_ok else 'BAD', 'ok' if p_ok else 'BAD', name,
                     'record' if rec else (m.group(1)[:70] if m else 'no reason'), pw))
    stands = all(zs[n] == zs['good'] and zs[n] is not None for n in ('cd_zero', 'cd_singular', 'sip_huge', 'crpix_str'))
    ok = okc and okp and stands
    say('Z2  %s  the audit\'s other 12 inputs: the command line as wanted %s | the page\'s engine as wanted %s | '
        'the pixel answer stands on the four WCS %s' % ('PASS' if ok else 'FAIL', okc, okp, stands))
    if perr:
        say('    the engine failed: ' + perr)
    for l in lines:
        say(l)
    v.append(ok)
    # Z3, the suite
    rc, o = run([sys.executable, '-m', 'tests.strict'], env=dict(DOMINO_CALIBRATOR_TESTED_VERSIONS='1'))
    line = (re.findall(r'^strict: .*$', o, re.M) or ['strict: no verdict'])[-1]
    bad = re.findall(r'^(?:FAIL|ERROR): (\S+ \([^)]*\))', o, re.M)
    ok = rc == 0 and line.startswith('strict: PASS')
    say('Z3  %s  the whole suite: %s' % ('PASS' if ok else 'FAIL', line))
    for b in bad[:40]:
        say('        failed: ' + b)
    v.append(ok)
    met = sum(v)
    say('# audit fix bar 2: %s, %d of %d' % ('MET' if met == len(v) == 4 else 'NOT MET', met, 4))
    return 0 if met == 4 else 1


if __name__ == '__main__':
    sys.exit(main())
