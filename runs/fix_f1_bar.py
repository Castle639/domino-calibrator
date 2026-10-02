#!/usr/bin/env python3
"""The fix room's F1 bar: the record as an MPC reviewer would see it (1 Oct 2026; the fix room's record of 1 Oct 2026, not in this repository,
the launch room's should-fixes 1, 2, 3, 4, 6, 7 and 8 with his answers). Committed before it runs: red on the tool as the
launch room left it, green after the fix. Its cases are tests/test_fix_f1.py, whose docstring quotes ADES at source.

  python runs/fix_f1_bar.py LOG        from the repository's root, with ADES_PYLIB, ADES_MASTER and PLAYWRIGHT_MODULE set

  R0  the controls, run first: the fixture's record (the tool as it stands, a fixed station) is accepted by the MPC's judge and a
      planted bad one refused, so the judge can fail; the checkers read planted strings right (two significant figures and
      three, 6 and 7 decimals, ADES's DP at its edges); a control character and a character outside ASCII are seen as such;
      the record of the MPC's list holds 31 codes, 250 and 247 among them and 568 not
  R1  item 1, F1_1_Stations: a station with no fixed position gets no record, with the reason, on both faces
  R2  item 2, F1_2_RmsFigures: rmsRA and rmsDec at two significant figures
  R3  item 3, F1_3_Decimals: ra and dec decimals from the uncertainty; 6 without one, on both faces
  R4  item 4, F1_4_Names: initials, then surname, on the page and in the command line's help
  R5  item 6, F1_6_Software: # software, ! astrometry, with the version, on both faces; the page's version is the package's
  R6  item 7, F1_7_ControlCharacters: control characters and bytes that are not UTF-8 refused, on both faces
  R7  item 8, F1_8_AsciiDesignations: designations outside ASCII refused, on both faces
  R8  the page in Chromium, the face a user meets: a full record shows the software block, ra and dec at 6 decimals, and the
      MPC's judge accepts it; with station 250 the page names the reason and offers nothing to copy
  R9  the whole suite, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
A clause's class passes only when its tests ran and none failed, erred or was skipped.
"""
import os, re, sys, json, shutil, tempfile, subprocess, unittest, unicodedata, warnings, io, contextlib
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
LOG = sys.argv[1]
out = open(LOG, 'w', encoding='utf-8')
CLAUSES = [('R1', 'F1_1_Stations'), ('R2', 'F1_2_RmsFigures'), ('R3', 'F1_3_Decimals'), ('R4', 'F1_4_Names'),
           ('R5', 'F1_6_Software'), ('R6', 'F1_7_ControlCharacters'), ('R7', 'F1_8_AsciiDesignations')]


def say(s):
    print(s); out.write(s + '\n'); out.flush()


def run(args, env=None, timeout=3600):
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run(args, cwd=ROOT, env=e, capture_output=True, encoding='utf-8', errors='replace', timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def klass(name):
    """One class of tests/test_fix_f1.py: (passed, tests run, the first faults' lines)."""
    warnings.simplefilter('ignore')
    suite = unittest.defaultTestLoader.loadTestsFromName('tests.test_fix_f1.' + name)
    buf = io.StringIO()
    res = unittest.TextTestRunner(stream=buf, verbosity=0).run(suite)
    faults = []
    for t, tb in res.failures + res.errors:
        last = [l for l in tb.strip().splitlines() if l.strip()][-1]
        faults.append('%s: %s' % (t.id().split('.')[-1], last[:230]))
    faults += ['%s: skipped (%s)' % (t.id().split('.')[-1], why) for t, why in res.skipped]
    return res.wasSuccessful() and not res.skipped and res.testsRun > 0, res.testsRun, faults


def main():
    import numpy as np
    from domino_calibrator import __version__
    from tests import test_fix_f1 as F
    from tests.test_hardening import REC_ARGS, run_main, comet, write, mpc_judge, ADES_PYLIB, ADES_MASTER
    from tests.test_hardening_page import NODE, PW, PAGE, REC_PAGE, fits_bytes
    from domino_calibrator import synth
    head = os.popen('git -C %s rev-parse --short HEAD' % ROOT).read().strip()
    me = __import__('hashlib').sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest()
    t = __import__('hashlib').sha256(open(os.path.join(ROOT, 'tests', 'test_fix_f1.py'), 'rb').read()).hexdigest()
    say('# fix_f1_bar | HEAD %s | its sha256 %s | tests/test_fix_f1.py %s' % (head, me, t))
    met = []
    d = tempfile.mkdtemp()
    try:
        # R0: the controls
        warnings.simplefilter('ignore')
        img, _ = comet(); p = write(os.path.join(d, 'c.fits'), img)
        rc, o = run_main([p] + REC_ARGS)
        rec = o[o.index('# version='):] if '# version=' in o else ''
        ok_good, why_good = mpc_judge(rec, d) if rec and ADES_PYLIB and ADES_MASTER else (False, 'no record or no judge')
        bad = re.sub(r'\d{4}-\d{2}-\d{2}T(\d{2}:\d{2}:\d{2}(\.\d+)?Z)', r'2025-13-45 \1', rec)    # a time the schema refuses
        ok_bad, why_bad = mpc_judge(bad, d) if rec and ADES_PYLIB and ADES_MASTER else (True, '')
        checks = [F.sig_figs('0.012') == 2, F.sig_figs('0.0123') == 3, F.sig_figs('0.10') == 2, F.sig_figs('12') == 2,
                  F.sig_figs('0.00012') == 2, F.decimals('168.700000') == 6, F.decimals('168.7000000') == 7,
                  F.dp(0.036) == 6, F.dp(0.35) == 6, F.dp(0.37) == 5, F.dp(3.5) == 5]
        seen = [unicodedata.category('\x07') == 'Cc', unicodedata.category('\x85') == 'Cc', not '３I'.isascii(), '3I'.isascii()]
        lst = json.load(open(F.LIST, encoding='utf-8'))['no_fixed_position']
        codes = [c['code'] for c in lst]
        listed = len(codes) == 31 and '250' in codes and '247' in codes and '568' not in codes and tuple(codes) == F.NO_FIXED_POSITION
        r0 = bool(rec) and ok_good and not ok_bad and all(checks) and all(seen) and listed
        say('R0  %s  the fixture gets a record: %s | the judge accepts it: %s | refuses a planted bad time: %s | the checkers on planted '
            'strings: %d of %d | a control character and a character outside ASCII seen: %s | the MPC list: %d codes, 250 and 247 in, '
            '568 out: %s' % ('PASS' if r0 else 'FAIL', bool(rec), ok_good, not ok_bad, sum(checks), len(checks), all(seen), len(codes), listed))
        if not r0:
            say('    the judge: %s | planted: %s' % (why_good[:200], why_bad[:200]))
        met.append(r0)

        # R1-R7: the tests' classes
        for tag, name in CLAUSES:
            ok, n, faults = klass(name)
            say('%s  %s  tests.test_fix_f1.%s: %d run%s' % (tag, 'PASS' if ok else 'FAIL', name, n,
                                                            '' if ok else ', %d fault%s' % (len(faults), '' if len(faults) == 1 else 's')))
            for f in faults[:6]:
                say('    ' + f)
            met.append(ok)

        # R8: the page in Chromium
        pimg, _ = synth.render(71, 35.25, 34.85, flux_n=3e4, k=400.0, a=0.3, model='dipole', psf=('gauss', 2.5), sub=10)
        pimg = synth.add_noise(pimg, 150.0, 5.0, np.random.default_rng(5)).astype(np.float32)
        wcs = dict(CTYPE1='RA---TAN', CTYPE2='DEC--TAN', CRPIX1=36.0, CRPIX2=36.0, CRVAL1=168.7, CRVAL2=4.6,
                   CD1_1=-2.1e-4, CD1_2=0.0, CD2_1=0.0, CD2_2=2.1e-4, **{'DATE-OBS': '2025-12-27T16:04:29.000', 'EXPTIME': 120.0})
        good = fits_bytes(os.path.join(d, 'good.fits'), pimg, **wcs)
        cases = [dict(name='full', steps=[dict(file=good, x=35, y=35, set=dict(REC_PAGE), run=True)]),
                 dict(name='hubble', steps=[dict(file=good, x=35, y=35, set=dict(REC_PAGE, stn='250'), run=True)])]
        cp = os.path.join(d, 'cases.json'); json.dump(cases, open(cp, 'w', encoding='utf-8'))
        rc, o = run([NODE, os.path.join(PAGE, 'browser_cases.js'), cp], env=dict(PLAYWRIGHT_MODULE=PW), timeout=300)
        try:
            res = {c['name']: c for c in json.loads(o[o.index('[{'):o.rindex('}]') + 2])}
        except Exception:
            res = {}
        full = (res.get('full') or {}).get('steps', [{}])[0]
        hub = (res.get('hubble') or {}).get('steps', [{}])[0]
        a = full.get('ades', '')
        lines = a.splitlines()
        soft = '# software' in lines and ('! astrometry ' + F.SOFTWARE) in lines
        six = False
        if '# version=' in a:
            row = F.record_row(a)
            six = (F.decimals(row.get('ra', '')), F.decimals(row.get('dec', ''))) == (6, 6)
        ok_j, why_j = mpc_judge(a[a.index('# version='):], d) if '# version=' in a and ADES_PYLIB and ADES_MASTER else (False, 'no record or no judge')
        no250 = '# version=' not in hub.get('ades', '') and hub.get('copyDisabled') is True and \
            "has no fixed position in the MPC's list" in hub.get('text', '')
        r8 = soft and six and ok_j and no250 and not (res.get('full') or {}).get('errors') and not (res.get('hubble') or {}).get('errors')
        say('R8  %s  the page in Chromium: the full record holds the software block: %s, ra and dec at 6 decimals: %s, the judge: %s | '
            'station 250: no record, Copy disabled, the reason shown: %s' % ('PASS' if r8 else 'FAIL', soft, six, ok_j, no250))
        if not r8:
            say('    the page: %s | %s' % (' / '.join(lines[-4:])[:300], why_j[:150]))
        met.append(r8)

        # R9: the whole suite, strict
        rc, o = run([sys.executable, '-m', 'tests.strict'], env=dict(DOMINO_CALIBRATOR_TESTED_VERSIONS='1'))
        line = (re.findall(r'^strict: .*$', o, re.M) or ['strict: no verdict'])[-1]
        r9 = rc == 0 and line.startswith('strict: PASS')
        say('R9  %s  the whole suite: %s' % ('PASS' if r9 else 'FAIL', line))
        if not r9:
            for m in re.findall(r'^(?:FAIL|ERROR): (\S+) \((\S+)\)', o, re.M)[:12]:
                say('    %s %s' % m)
        met.append(r9)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    n = sum(met)
    say('# fix f1 bar: %s, %d of %d%s' % ('MET' if n == len(met) else 'NOT MET', n, len(met),
                                         '' if n == len(met) else ' (failing: %s)' % ' '.join('R%d' % k for k, v in enumerate(met) if not v)))


if __name__ == '__main__':
    main()
