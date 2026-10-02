#!/usr/bin/env python3
"""The fix room's F3 bar: the words (1 Oct 2026; the fix room's record of 1 Oct 2026, not in this repository, his rule's words and exit
codes, and the launch room's should-fixes 13, 15, 16, 17, 20, 21, 23, 24, 25, 26, 28, 29, 30 and 40, with the README's rms
words after items 3 and 5). Committed before it runs: red on the words as F2 left them, green after the fix. Its cases are
tests/test_fix_f3.py.

  python runs/fix_f3_bar.py LOG        from the repository's root, with ADES_PYLIB, ADES_MASTER and PLAYWRIGHT_MODULE set

  P0  the controls, run first: the summaries give the records' recounts (the arcsec radii not measurable in 21 of the 45
      amateur cells, 21 FAILS and 3 HELPS: PARTIAL; at SNR 20, 9 of the 20 professional cells further from HST's photocentre
      than r = 2 px, all 20 helping noiseless; G worse than none in 45 of 130); the README's registry flags a planted number
      nobody registered; the jargon and the person's-name patterns catch planted forms; the MPC's judge accepts the tool's
      record with the validator and fails without it; and Chromium reads a placeholder's own colour
  P1-P15  the tests' classes, one per item (F3_Rule, F3_ExitCodes, F3_13_WholeFrame, F3_15_Judge, F3_16_CheckARecord,
      F3_17_MaySkip, F3_20_Jargon, F3_21_Changelog, F3_23_Cutout, F3_24_26_Study, F3_28_PageComparison, F3_29_SameMethod,
      F3_30_Credit, F3_40_Hints, F3_3_5_RmsWords)
  P16 the page in Chromium: every placeholder at least 4.5:1 against its own box (WCAG 1.4.3, the audit's F6.3: 3.62:1)
  P17 the whole suite, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
A clause's class passes only when its tests ran and none failed, erred or was skipped.
"""
import os, re, sys, json, shutil, tempfile, subprocess, unittest, warnings, io
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
LOG = sys.argv[1]
out = open(LOG, 'w', encoding='utf-8')
CLASSES = ['F3_Rule', 'F3_ExitCodes', 'F3_13_WholeFrame', 'F3_15_Judge', 'F3_16_CheckARecord', 'F3_17_MaySkip', 'F3_20_Jargon',
           'F3_21_Changelog', 'F3_23_Cutout', 'F3_24_26_Study', 'F3_28_PageComparison', 'F3_29_SameMethod', 'F3_30_Credit',
           'F3_40_Hints', 'F3_3_5_RmsWords']
PLACEHOLDERS = r"""
const { chromium } = require(process.env.PLAYWRIGHT_MODULE || 'playwright');
(async () => {
  const b = await chromium.launch(); const p = await b.newPage();
  await p.goto('file://' + process.argv[2]);
  const r = await p.evaluate(() => Array.from(document.querySelectorAll('input[placeholder]')).map((e) => {
    const box = getComputedStyle(e);
    return { id: e.id, placeholder: getComputedStyle(e, '::placeholder').color, bg: box.backgroundColor,
             page: getComputedStyle(document.body).backgroundColor };
  }));
  process.stdout.write(JSON.stringify(r)); await b.close();
})();
"""


def say(s):
    print(s); out.write(s + '\n'); out.flush()


def run(args, env=None, timeout=3600):
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run(args, cwd=ROOT, env=e, capture_output=True, encoding='utf-8', errors='replace', timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def klass(name):
    warnings.simplefilter('ignore')
    suite = unittest.defaultTestLoader.loadTestsFromName('tests.test_fix_f3.' + name)
    res = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    faults = []
    for t, tb in res.failures + res.errors:
        last = [l for l in tb.strip().splitlines() if l.strip()][-1]
        faults.append('%s: %s' % (t.id().split('.')[-1], last[:230]))
    faults += ['%s: skipped (%s)' % (t.id().split('.')[-1], why) for t, why in res.skipped]
    return res.wasSuccessful() and not res.skipped and res.testsRun > 0, res.testsRun, faults


def placeholder_contrasts(d):
    """Each placeholder's colour against its own box, as Chromium computes them: {id: contrast}."""
    from tests.test_page_design import contrast, rgb
    from tests.test_hardening_page import NODE, PW, PAGE
    sp = os.path.join(d, 'ph.js'); open(sp, 'w', encoding='utf-8').write(PLACEHOLDERS)
    rc, o = run([NODE, sp, os.path.join(PAGE, 'index.html')], env=dict(PLAYWRIGHT_MODULE=PW), timeout=120)
    try:
        rows = json.loads(o[o.index('['):o.rindex(']') + 1])
    except Exception:
        return None, o[-300:]
    res = {}
    for r in rows:
        back = r['bg'] if (rgb(r['bg']) or (0, 0, 0, 0))[3] > 0 else r['page']
        res[r['id']] = contrast(r['placeholder'], back)
    return res, ''


def main():
    import hashlib, json as _json
    import numpy as np
    from tests import test_fix_f3 as F, test_release_words as W
    from tests.test_hardening import REC_ARGS, comet, write, mpc_judge, ADES_PYLIB, ADES_MASTER
    import tests.test_hardening as H
    from domino_calibrator import cli
    head = os.popen('git -C %s rev-parse --short HEAD' % ROOT).read().strip()
    me = hashlib.sha256(open(os.path.abspath(__file__), 'rb').read()).hexdigest()
    t = hashlib.sha256(open(os.path.join(ROOT, 'tests', 'test_fix_f3.py'), 'rb').read()).hexdigest()
    say('# fix_f3_bar | HEAD %s | its sha256 %s | tests/test_fix_f3.py %s' % (head, me, t))
    met = []
    d = tempfile.mkdtemp()
    try:
        warnings.simplefilter('ignore')
        # P0: the controls
        h3 = _json.load(open(os.path.join(ROOT, 'runs', 'H3_SUMMARY_2026-09-27.json')))
        h4 = _json.load(open(os.path.join(ROOT, 'runs', 'H4_SUMMARY_2026-09-27.json')))
        amat = [k for k, c in h3.items() if float(c['fw']) >= 2.0 - 1e-9 and float(c['gs']) >= 1.0 - 1e-9]
        prof = [c for c in h3.values() if float(c['fw']) <= 1.0 + 1e-9 and float(c['gs']) <= 0.44 + 1e-9]
        arc = [h4[k]['G']['ARC']['class'] for k in amat]
        recounts = (arc.count('NULL-FAILED'), len(amat), arc.count('FAILS'), arc.count('HELPS'),
                    sum(c['G']['rms0_20'] > c['G']['rms2_20'] for c in prof), len(prof),
                    sum(c['G']['class'] in ('HELPS', 'WORKS') for c in prof),
                    sum(c['G']['ratio'] is not None and c['G']['ratio'] > 1 for c in h3.values()), len(h3))
        rec_ok = recounts == (21, 45, 21, 3, 9, 20, 20, 45, 130)
        planted = W.unregistered('The tool ran 987 times on 3I.')
        reg_ok = any(tok == '987' for tok, _ in planted)
        jar_ok = bool(re.search(r'(?i)\b(its|two|one|three) stars?\b', 'with its stars and its limits')) and \
            bool(re.search(r'(?i)\b(?:given|family)-names\b', 'family-names: X'))      # F4: no name spelled in code
        img, _ = comet(); p = write(os.path.join(d, 'c.fits'), img)
        buf = io.StringIO()
        import contextlib
        with contextlib.redirect_stdout(buf):
            cli.main([p] + REC_ARGS)
        o = buf.getvalue(); psv = o[o.index('# version='):] if '# version=' in o else ''
        ok_real, why_real = mpc_judge(psv, d) if psv and ADES_PYLIB and ADES_MASTER else (False, 'no record or no judge')
        empty = os.path.join(d, 'empty'); os.makedirs(empty)
        saved = H.ADES_PYLIB; H.ADES_PYLIB = empty
        try:
            ok_empty, why_empty = H.mpc_judge(psv, d) if psv else (True, '')
        finally:
            H.ADES_PYLIB = saved
        judge_ok = ok_real and not ok_empty
        ph, why_ph = placeholder_contrasts(d)
        chrome_ok = bool(ph) and all(v is not None for v in ph.values())
        p0 = rec_ok and reg_ok and jar_ok and judge_ok and chrome_ok
        say('P0  %s  the summaries\' recounts %s: %s | the registry flags a planted number: %s | the jargon and name patterns catch '
            'planted forms: %s | the judge accepts the record with the validator: %s, fails without it: %s | Chromium reads the '
            'placeholders\' colours: %s (%d inputs)' % ('PASS' if p0 else 'FAIL', recounts, rec_ok, reg_ok, jar_ok, ok_real,
                                                           not ok_empty, chrome_ok, len(ph or {})))
        if not p0:
            say('    judge: %s | %s | chromium: %s' % (why_real[:120], why_empty[:120], why_ph[:160]))
        met.append(p0)

        # P1-P15: the tests' classes
        for k, name in enumerate(CLASSES, 1):
            ok, n, faults = klass(name)
            say('P%d  %s  tests.test_fix_f3.%s: %d run%s' % (k, 'PASS' if ok else 'FAIL', name, n,
                                                              '' if ok else ', %d fault%s' % (len(faults), '' if len(faults) == 1 else 's')))
            for f in faults[:5]:
                say('    ' + f)
            met.append(ok)

        # P16: the page in Chromium, each placeholder against its own box
        ph, why_ph = placeholder_contrasts(d)
        low = {k: round(v, 2) for k, v in (ph or {}).items() if v is None or v < 4.5}
        p16 = bool(ph) and not low
        say('P16 %s  the placeholders against their own boxes, at least 4.5:1: %s%s' % (
            'PASS' if p16 else 'FAIL', 'all %d' % len(ph) if p16 else 'below: %s' % low,
            '' if ph else ' (%s)' % why_ph[:160]))
        met.append(p16)

        # P17: the whole suite, strict
        rc, o = run([sys.executable, '-m', 'tests.strict'], env=dict(DOMINO_CALIBRATOR_TESTED_VERSIONS='1'))
        line = (re.findall(r'^strict: .*$', o, re.M) or ['strict: no verdict'])[-1]
        p17 = rc == 0 and line.startswith('strict: PASS')
        say('P17 %s  the whole suite: %s' % ('PASS' if p17 else 'FAIL', line))
        if not p17:
            for mm in re.findall(r'^(?:FAIL|ERROR): (\S+) \((\S+)\)', o, re.M)[:12]:
                say('    %s %s' % mm)
        met.append(p17)
    finally:
        shutil.rmtree(d, ignore_errors=True)
    k = sum(met)
    say('# fix f3 bar: %s, %d of %d%s' % ('MET' if k == len(met) else 'NOT MET', k, len(met),
                                         '' if k == len(met) else ' (failing: %s)' % ' '.join('P%d' % i for i, v in enumerate(met) if not v)))


if __name__ == '__main__':
    main()
