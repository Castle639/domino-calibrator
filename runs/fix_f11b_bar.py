#!/usr/bin/env python3
"""The fix room's F11b bar: two of the second audit room's should-fixes, the record's uncertainty (1 Oct 2026, his yes to all
27, in the room's report, section 26): by its report's numbers, 7 (F2.1) and 8 (F2.2). Committed with tests/test_fix_f11b.py
before it runs. The audit's confirmations (C2.1, C2.2) ran from the automatic start, which since F10 gives no record, on
that room's own Hubble cutout, so they cannot fail on today's code for their own reason: this bar makes its own case, a
noisy comet from tests/test_hardening.py, from a start given, in a copy of TARGET.

  python runs/fix_f11b_bar.py LOG SCRATCH TARGET    from calibrator/, with ADES_PYLIB, ADES_MASTER, PLAYWRIGHT_MODULE
     TARGET: a commit whose calibrator/ is measured ('HEAD', or the F11 commit for the red run)

  Y0  the controls: without --rms-noise the record has no rms fields and the MPC's judge accepts it; with --rms-noise 5 the
      pixel scatter is printed, from 5 of 5 redraws
  Y1  8: with --rms-noise 5 and 30, the record carries no rmsRA, rmsDec or rmsCorr, no rms in its remarks, and is the record
      without --rms-noise, byte for byte; the MPC's judge accepts it
  Y2  7: the sky scatter printed beside the record in arcsec at two significant figures, with its redraws and how rough;
      no correlation from 5 redraws, a correlation from 30
  Y3  the words: --help and the README say the record carries no rmsRA, rmsDec or rmsCorr, and ask no hand edit of the record
  Y4  tests/test_fix_f11b.py, in calibrator/
  Y5  the whole suite in calibrator/, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
"""
import json, os, re, sys, shutil, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # calibrator/
REPO = os.path.dirname(ROOT)
LOG, SCRATCH, TARGET = sys.argv[1:4]
out = open(LOG, 'w', encoding='utf-8')

CASE = r'''
import json, os, sys, warnings
sys.path.insert(0, os.getcwd())
warnings.simplefilter('ignore')
import numpy as np
from tests.test_hardening import comet, write, run_main, given, REC_ARGS, mpc_judge
d = sys.argv[1]
img, _ = comet()
p = write(os.path.join(d, 'c.fits'), img + np.random.default_rng(3).normal(0, 3.0, img.shape))
res = {}
for n in (0, 5, 30):
    rc, o = run_main([p] + (['--rms-noise', str(n)] if n else []) + given(p) + REC_ARGS)
    rec = o[o.find('# version=2022'):] if '# version=2022' in o else ''
    j = os.path.join(d, 'j%d' % n); os.makedirs(j, exist_ok=True)
    ok, why = mpc_judge(rec, j) if rec else (False, 'no record')
    res[n] = dict(rc=rc, out=o, rec=rec, judge=bool(ok), why=str(why)[:200])
import contextlib, io, re
from domino_calibrator import cli
buf = io.StringIO()
with contextlib.redirect_stdout(buf):
    try:
        cli.main(['--help'])
    except SystemExit:
        pass
res['help'] = ' '.join(buf.getvalue().split())
res['readme'] = ' '.join(re.sub(r'```.*?```', ' ', open('README.md', encoding='utf-8').read(), flags=re.S).split())
json.dump(res, open(os.path.join(d, 'case.json'), 'w'))
'''


def say(s):
    print(s, flush=True); out.write(s + '\n'); out.flush()


def run(args, cwd=None, timeout=3600):
    c = subprocess.run(args, cwd=cwd, capture_output=True, encoding='utf-8', errors='replace', timeout=timeout,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return c.returncode, c.stdout, c.stderr


def row(rec):
    lines = [l for l in rec.splitlines() if l and not l.startswith(('#', '!'))]
    if len(lines) < 2:
        return {}
    return dict(zip([s.strip() for s in lines[-2].split('|')], [s.strip() for s in lines[-1].split('|')]))


def scatter(o):
    return re.search(r'^# sky-noise scatter on the sky, from (\d+) of (\d+) redraws: RA\*cos\(Dec\) (\S+)", Dec (\S+)"(.*)$', o, re.M)


def two(v):
    return bool(re.match(r'^0\.0*[1-9]\d?$|^[1-9]\.\d$|^[1-9]\d$', v))


def main():
    head = run(['git', '-C', REPO, 'rev-parse', '--short', 'HEAD'])[1].strip()
    tree = run(['git', '-C', REPO, 'rev-parse', '--short', TARGET])[1].strip()
    say('# fix_f11b_bar | HEAD %s | TARGET %s (%s:calibrator)' % (head, TARGET, tree))
    room = os.path.join(SCRATCH, 'room')
    shutil.rmtree(room, ignore_errors=True); os.makedirs(os.path.join(room, 'folder')); os.makedirs(os.path.join(room, 'case'))
    tar = subprocess.run(['git', '-C', REPO, 'archive', '--format=tar', tree + ':calibrator'], capture_output=True, check=True).stdout
    subprocess.run(['tar', '-x', '-f', '-', '-C', os.path.join(room, 'folder')], input=tar, check=True)
    open(os.path.join(room, 'case.py'), 'w').write(CASE)
    rc, o, e = run([sys.executable, os.path.join(room, 'case.py'), os.path.join(room, 'case')], cwd=os.path.join(room, 'folder'))
    if rc != 0:
        say('# the case did not run: %s' % e[-400:])
        r = {}
    else:
        r = json.load(open(os.path.join(room, 'case', 'case.json')))
    r0, r5, r30 = r.get('0', {}), r.get('5', {}), r.get('30', {})
    for n, x in (('0', r0), ('5', r5), ('30', r30)):
        rw = row(x.get('rec', ''))
        m = scatter(x.get('out', ''))
        say('    --rms-noise %-2s exit %s | record %s | rms fields %s | remarks %r | judge %s | scatter line %s' % (
            n, x.get('rc'), 'yes' if x.get('rec') else 'no', [k for k in ('rmsRA', 'rmsDec', 'rmsCorr') if k in rw],
            rw.get('remarks', '')[:90], x.get('judge'), (m.group(0)[:200] if m else None)))
    px5 = re.search(r'^# zero-aperture scatter from 5 of 5 noise redraws', r5.get('out', ''), re.M)
    y0 = bool(r0.get('rec')) and not any(k in row(r0['rec']) for k in ('rmsRA', 'rmsDec', 'rmsCorr')) and r0.get('judge') is True and bool(px5)
    say('Y0 %s  the controls: without --rms-noise a record, no rms fields, judge %s; with 5, the pixel scatter printed: %s' % (
        'PASS' if y0 else 'FAIL', r0.get('judge'), bool(px5)))
    y1 = all(bool(x.get('rec')) and not any(k in row(x['rec']) for k in ('rmsRA', 'rmsDec', 'rmsCorr'))
             and 'rms' not in row(x['rec']).get('remarks', '') and x['rec'] == r0.get('rec') and x.get('judge') is True for x in (r5, r30))
    say('Y1 %s  8: with --rms-noise 5 and 30 the record carries no rms, is the record without (%s, %s), judge (%s, %s)' % (
        'PASS' if y1 else 'FAIL', r5.get('rec') == r0.get('rec'), r30.get('rec') == r0.get('rec'), r5.get('judge'), r30.get('judge')))
    m5, m30 = scatter(r5.get('out', '')), scatter(r30.get('out', ''))
    y2 = bool(m5 and m30) and all(two(v) for v in (m5.group(3), m5.group(4), m30.group(3), m30.group(4))) \
        and (m5.group(1), m5.group(2), m30.group(1), m30.group(2)) == ('5', '5', '30', '30') \
        and 'good to about 35%' in m5.group(5) and 'good to about 13%' in m30.group(5) \
        and 'correlation' in m30.group(5) and 'no correlation from fewer than 10 redraws' in m5.group(5)
    say('Y2 %s  7: the scatter line, 5: %s | 30: %s' % ('PASS' if y2 else 'FAIL', m5.group(0)[44:] if m5 else None, m30.group(0)[44:] if m30 else None))
    faces = (('--help', r.get('help', '')), ('README.md', r.get('readme', '')))
    w = {f: (bool(re.search(r'record carries no rmsRA, rmsDec or rmsCorr', t)), not re.search(r'delete rmsCorr', t),
             not re.search(r"delete the remarks' rms clause", t)) for f, t in faces}
    y3 = all(all(v) for v in w.values())
    say('Y3 %s  the words (no rms in the record, no edit of rmsCorr, no edit of the remarks): %s' % ('PASS' if y3 else 'FAIL', w))
    rc, so, se = run([sys.executable, '-m', 'unittest', '-v', 'tests.test_fix_f11b'], cwd=ROOT)
    last = ([l for l in se.splitlines() if l.strip()] or ['no output'])[-1]
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', se, re.M)))
    y4 = rc == 0
    say('Y4 %s  tests/test_fix_f11b.py | %s%s' % ('PASS' if y4 else 'FAIL', last, (' | failing: ' + ', '.join(bad)) if bad else ''))
    c = subprocess.run([sys.executable, '-m', 'tests.strict'], cwd=ROOT, env=dict(os.environ, DOMINO_CALIBRATOR_TESTED_VERSIONS='1'),
                       capture_output=True, encoding='utf-8', errors='replace', timeout=5400)
    so = c.stdout + c.stderr
    line = (re.findall(r'^strict: .*$', so, re.M) or ['strict: no verdict'])[-1]
    y5 = c.returncode == 0 and bool(re.match(r'strict: PASS \(\d+ run, 0 failures, 0 errors, 0 skipped', line))
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', so, re.M)))
    say('Y5 %s  %s%s' % ('PASS' if y5 else 'FAIL', line, (' | failing: ' + ', '.join(bad[:14])) if bad else ''))
    met = sum((y0, y1, y2, y3, y4, y5))
    say("# F11b's bar on %s: %s, %d of 6" % (TARGET, 'MET' if met == 6 else 'NOT MET', met))
    return 0 if met == 6 else 1


if __name__ == '__main__':
    sys.exit(main())
