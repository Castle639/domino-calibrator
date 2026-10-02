#!/usr/bin/env python3
"""The fix room's F2 bar: inputs and failures (1 Oct 2026; the fix room's record of 1 Oct 2026, not in this repository, the launch room's
should-fixes 5, 9, 10, 11, 12 and 14 with his answers). Committed before it runs: red on the tool as F1 left it, green after
the fix. Its cases are tests/test_fix_f2.py.

  python runs/fix_f2_bar.py LOG        from the repository's root, with ADES_PYLIB, ADES_MASTER and PLAYWRIGHT_MODULE set

  Q0  the controls, run first: astropy itself fails on each of the audit's three corrupt headers (so they are its cases); the
      extension of the two-HDU file has no WCS and no INHERIT, and its primary has a WCS; the scatter depends on its draws
      (seed 1 against seed 2 differ, so a pin on them can fail); the automatic start takes the brighter of the two sources on
      both faces; and the harness's closed pipe makes a child's print raise BrokenPipeError
  Q1  item 5, F2_5_SkyRing: the noise from the comet's own sky ring, the same for a cutout and its whole frame
  Q2  item 9, F2_9_Inherit: the primary's WCS for an extension only with INHERIT = T, on both faces
  Q3  item 10, F2_10_CorruptHeaders: the three headers named at the header stage, on both faces, in the same words
  Q4  item 10, his exit codes, F2_10_ExitCodes: 0 passed its gates, 2 the gates refused, 1 cannot measure at all
  Q5  item 11, F2_11_ClosedPipe: a closed pipe ends quietly, with the measurement's own code
  Q6  item 12, F2_12_Estimate: the estimated time before the redraws; the 3-1000 limit kept
  Q7  item 14, F2_14_ZeroBased: "0-based; add 1 for ds9" beside every printed position, on both faces
  Q8  the page in Chromium: a corrupt header named on loading; the two-HDU file without INHERIT gives no sky position, with the
      reason, and nothing to copy; a measured comet's zero-aperture line carries the words twice and its table once
  Q9  the whole suite, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
A clause's class passes only when its tests ran and none failed, erred or was skipped.
"""
import os, re, sys, json, shutil, tempfile, subprocess, unittest, warnings, io
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
LOG = sys.argv[1]
out = open(LOG, 'w', encoding='utf-8')
CLAUSES = [('Q1', 'F2_5_SkyRing'), ('Q2', 'F2_9_Inherit'), ('Q3', 'F2_10_CorruptHeaders'), ('Q4', 'F2_10_ExitCodes'),
           ('Q5', 'F2_11_ClosedPipe'), ('Q6', 'F2_12_Estimate'), ('Q7', 'F2_14_ZeroBased')]


def say(s):
    print(s); out.write(s + '\n'); out.flush()


def run(args, env=None, timeout=3600):
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run(args, cwd=ROOT, env=e, capture_output=True, encoding='utf-8', errors='replace', timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def klass(name):
    """One class of tests/test_fix_f2.py: (passed, tests run, the first faults' lines)."""
    warnings.simplefilter('ignore')
    suite = unittest.defaultTestLoader.loadTestsFromName('tests.test_fix_f2.' + name)
    buf = io.StringIO()
    res = unittest.TextTestRunner(stream=buf, verbosity=0).run(suite)
    faults = []
    for t, tb in res.failures + res.errors:
        last = [l for l in tb.strip().splitlines() if l.strip()][-1]
        faults.append('%s: %s' % (t.id().split('.')[-1], last[:230]))
    faults += ['%s: skipped (%s)' % (t.id().split('.')[-1], why) for t, why in res.skipped]
    return res.wasSuccessful() and not res.skipped and res.testsRun > 0, res.testsRun, faults


def main():
    import hashlib
    import numpy as np
    from astropy.io import fits
    from domino_calibrator import cli
    from tests import test_fix_f2 as F
    from tests.test_hardening import REC_ARGS, comet, write, wcs_cards
    from tests.test_hardening_page import NODE, PW, PAGE, REC_PAGE, js
    head = os.popen('git -C %s rev-parse --short HEAD' % ROOT).read().strip()
    me = hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest()
    t = hashlib.sha256(open(os.path.join(ROOT, 'tests', 'test_fix_f2.py'), 'rb').read()).hexdigest()
    say('# fix_f2_bar | HEAD %s | its sha256 %s | tests/test_fix_f2.py %s' % (head, me, t))
    met = []
    d = tempfile.mkdtemp()
    try:
        warnings.simplefilter('ignore')
        # Q0: the controls
        corrupt = {k: F.raw(os.path.join(d, k + '.fits'), c, n) for k, (c, n, _) in F.CORRUPT.items()}
        astro = {}
        for k, p in corrupt.items():
            try:
                with fits.open(p) as f:
                    f[0].data, f[0].fileinfo()
                astro[k] = 'read'
            except Exception as e:
                astro[k] = type(e).__name__
        fails = all(v != 'read' for v in astro.values())
        img = F.gauss(64, 30.3, 32.7, 1000.0, 2.0).astype(np.float32)
        h0 = wcs_cards(fits.Header(), n=64)
        mef = os.path.join(d, 'mef.fits'); fits.HDUList([fits.PrimaryHDU(header=h0), fits.ImageHDU(img, name='CUTOUT')]).writeto(mef)
        with fits.open(mef) as f:
            mef_ok = 'CTYPE1' in f[0].header and 'CTYPE1' not in f[1].header and 'INHERIT' not in f[1].header
        n = 71
        yy, xx = np.indices((n, n))
        rot = 100.0 + 3e3 * np.exp(-0.5 * (((xx - 35.1) / 4.0) ** 2 + ((yy - 34.9) / 1.2) ** 2))
        rot = rot + np.random.default_rng(3).normal(0.0, 3.0, rot.shape)
        rp = write(os.path.join(d, 'rot.fits'), rot)
        s1 = cli.measure_file(rp, estimator='M', rms_noise=30, seed=1).get('sd_px')
        s2 = cli.measure_file(rp, estimator='M', rms_noise=30, seed=2).get('sd_px')
        draws = bool(s1 and s2) and abs(s1[0] - s2[0]) > 1e-9 * s1[0]
        two = F.gauss(111, 30.0, 30.0, 3000.0, 1.5) + F.gauss(111, 80.0, 80.0, 1000.0, 1.5, sky=0.0, noise=0.0)
        tp = write(os.path.join(d, 'two.fits'), two)
        py_start = cli._start(cli.load_image(tp)[0])
        js_start = js("const fs = require('fs'); const h = Z.parseFITS(new Uint8Array(fs.readFileSync(D.p)).buffer).find((u) => u.readable);"
                      " out = Z.brightestStart(h.data, h.nx, h.ny);", {'p': tp})
        starts = tuple(py_start) == (30.0, 30.0) and list(js_start) == [30, 30]
        proc = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(0.5); print("x" * 100000)'], stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE)
        proc.stdout.close()
        perr = proc.stderr.read().decode('utf-8', 'replace'); proc.wait(timeout=60)
        pipe = 'BrokenPipeError' in perr
        q0 = fails and mef_ok and draws and starts and pipe
        say('Q0  %s  astropy fails on the three corrupt headers: %s | the two-HDU file: the extension has no WCS and no INHERIT, its '
            'primary a WCS: %s | the scatter depends on its draws (seed 1 against 2): %s | the automatic start takes the brighter '
            'source on both faces: %s | a closed pipe raises BrokenPipeError in a child: %s' % (
                'PASS' if q0 else 'FAIL', ', '.join('%s %s' % kv for kv in astro.items()), mef_ok, draws, starts, pipe))
        met.append(q0)

        # Q1-Q7: the tests' classes
        for tag, name in CLAUSES:
            ok, nrun, faults = klass(name)
            say('%s  %s  tests.test_fix_f2.%s: %d run%s' % (tag, 'PASS' if ok else 'FAIL', name, nrun,
                                                            '' if ok else ', %d fault%s' % (len(faults), '' if len(faults) == 1 else 's')))
            for f in faults[:6]:
                say('    ' + f)
            met.append(ok)

        # Q8: the page in Chromium
        h0t = wcs_cards(fits.Header(), n=64); h0t['DATE-OBS'] = '2025-12-12T21:20:32.000'; h0t['EXPTIME'] = 60.0
        mef2 = os.path.join(d, 'mef_time.fits')
        fits.HDUList([fits.PrimaryHDU(header=h0t), fits.ImageHDU(img, name='CUTOUT')]).writeto(mef2)
        cimg, _ = comet(); cp_ = write(os.path.join(d, 'c.fits'), cimg)
        cases = [dict(name='corrupt', steps=[dict(file=corrupt['naxis1_float'])]),
                 dict(name='mef', steps=[dict(file=mef2, x=30.3, y=32.7, set=dict(REC_PAGE), run=True)]),
                 dict(name='comet', steps=[dict(file=cp_, x=35.05, y=34.95, set={}, run=True)])]
        cpath = os.path.join(d, 'cases.json'); json.dump(cases, open(cpath, 'w', encoding='utf-8'))
        rc, o = run([NODE, os.path.join(PAGE, 'browser_cases.js'), cpath], env=dict(PLAYWRIGHT_MODULE=PW), timeout=300)
        try:
            res = {c['name']: c for c in json.loads(o[o.index('[{'):o.rindex('}]') + 2])}
        except Exception:
            res = {}
        step = lambda k: ((res.get(k) or {}).get('steps') or [{}])[0]
        a_ = step('corrupt').get('info', '') or ''
        named = 'NAXIS1 = 64.0 is not a size' in a_
        m = step('mef')
        mef_page = '# version=' not in (m.get('ades') or '') and m.get('copyDisabled') is True and 'INHERIT' in (m.get('text') or '')
        z = step('comet')
        ztext = z.get('zero') or ''
        ztab = (z.get('text') or '')
        zero_ok = ztext.count(F.DS9) == 2 and ztab.count(F.DS9) >= 3
        errs = [e for k in res for e in (res[k].get('errors') or [])]
        q8 = named and mef_page and zero_ok and not errs
        say('Q8  %s  the page in Chromium: the corrupt header named on loading: %s | the two-HDU file without INHERIT: no record, '
            'Copy disabled, INHERIT named: %s | the zero-aperture line carries the words twice and the page at least three times: '
            '%s%s' % ('PASS' if q8 else 'FAIL', named, mef_page, zero_ok, '' if not errs else ' | page errors: %s' % errs[:2]))
        if not q8:
            say('    corrupt: %s | zero: %s' % (a_[:160], ztext[:200]))
        met.append(q8)

        # Q9: the whole suite, strict
        rc, o = run([sys.executable, '-m', 'tests.strict'], env=dict(DOMINO_CALIBRATOR_TESTED_VERSIONS='1'))
        line = (re.findall(r'^strict: .*$', o, re.M) or ['strict: no verdict'])[-1]
        q9 = rc == 0 and line.startswith('strict: PASS')
        say('Q9  %s  the whole suite: %s' % ('PASS' if q9 else 'FAIL', line))
        if not q9:
            for mm in re.findall(r'^(?:FAIL|ERROR): (\S+) \((\S+)\)', o, re.M)[:12]:
                say('    %s %s' % mm)
        met.append(q9)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    k = sum(met)
    say('# fix f2 bar: %s, %d of %d%s' % ('MET' if k == len(met) else 'NOT MET', k, len(met),
                                         '' if k == len(met) else ' (failing: %s)' % ' '.join('Q%d' % i for i, v in enumerate(met) if not v)))


if __name__ == '__main__':
    main()
