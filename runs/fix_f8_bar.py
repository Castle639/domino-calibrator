#!/usr/bin/env python3
"""The fix room's F8 bar: R1.1's family (1 Oct 2026, his word for the night, in the room's report, section 21): the command
line never writes a record from a sky solution that differs from what the header says. Committed with tests/test_fix_f8.py
before it runs. Its controls are the second audit room's three confirmations, each run unchanged from its branch: C_R1_1.py
whole (sha256 3c911895...), and confirm_wave1.py's preamble and its C6.1 and C6.2 blocks (its lines 1-69 and 94-127, the
script sha256 7e1b224a...; the other blocks need that room's own inputs), as c6_slice.py.

  python runs/fix_f8_bar.py LOG SCRATCH CONFIRM TARGET     from calibrator/, with ADES_PYLIB, ADES_MASTER, PLAYWRIGHT_MODULE
     CONFIRM: the folder holding C_R1_1.py and c6_slice.py (regress_engine.js at ../regression/)
     TARGET: the tree the confirmations run on, as git holds it: 'sealed' (release/domino-calibrator at 004726d, the third
             seal: today's public code) or 'head' (calibrator/ at HEAD)

  Q0  the controls: the confirmations are the audit room's; on the readable files the command line gives a record (sip_ok
      on the truth, rot.fits and eexp.fits accepted by the MPC's validator), sip_drop shows its dropped term (1.5-2.0"),
      and the page's engine refuses the three unreadable files and gives the three D-exponent files the E file's position
      (within 0.001")
  Q1  R1.1 on TARGET: sip_nan_raw refused at the sky, no record, in the engine's words
  Q2  F6.1 on TARGET: CD1_1 written NAN, and 1E400: exit 2, no record, "the WCS card CD1_1 = '<as written>' is not a number"
  Q3  F6.2 on TARGET: CRVAL1, CRPIX1 and CD1_1 written with a D exponent: exit 0, the sky line and the record line the E
      file's
  Q4  tests/test_fix_f7.py and tests/test_fix_f8.py, in calibrator/
  Q5  the whole suite in calibrator/, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
"""
import os, re, sys, json, shutil, hashlib, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # calibrator/
REPO = os.path.dirname(ROOT)
LOG, SCRATCH, CONFIRM, TARGET = sys.argv[1:5]
out = open(LOG, 'w', encoding='utf-8')
SHAS = {'C_R1_1.py': '3c911895a809983df33f888feff4a706b89789f6855bd6f40db001e0faf628cb',
        'c6_slice.py': '3d4e72d04f73f7fad43e460f7a50bbcbb97027710e930f451604a341abccb7de'}
TREES = {'sealed': '004726d5589694a1d987a892f5fde0575d8b2cab:release/domino-calibrator', 'head': 'HEAD:calibrator'}
REC = ['--stn', '568', '--desig', '3I', '--mode', 'CCD', '--astcat', 'Gaia3', '--submitter', 'A. N. Observer', '--measurer',
       'A. N. Observer', '--telescope-design', 'Reflector', '--telescope-aperture', '0.5', '--telescope-detector', 'CCD']


def say(s):
    print(s, flush=True); out.write(s + '\n'); out.flush()


def run(args, cwd=None, timeout=1800):
    c = subprocess.run(args, cwd=cwd, capture_output=True, encoding='utf-8', errors='replace', timeout=timeout,
                       env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
    return c.returncode, c.stdout, c.stderr


def cli(folder, path):
    rc, o, e = run([sys.executable, '-m', 'domino_calibrator.cli', path] + REC, cwd=folder, timeout=600)
    need = re.search(r'# no ADES record: needs (.*)', o)
    keep = [l for l in o.splitlines() if l.startswith('# sky (ICRS)') or l.startswith('3I ')]
    return rc, ('# version=2022' in o), (need.group(1) if need else None), keep


def main():
    head = run(['git', '-C', REPO, 'rev-parse', '--short', 'HEAD'])[1].strip()
    shas = {f: hashlib.sha256(open(os.path.join(CONFIRM, f), 'rb').read()).hexdigest() for f in SHAS}
    say('# fix_f8_bar | HEAD %s | TARGET %s (%s) | the confirmations %s' % (head, TARGET, TREES[TARGET], ', '.join(
        '%s %s' % (f, 'the audit room\'s' if shas[f] == SHAS[f] else 'OTHER') for f in SHAS)))
    room = os.path.join(SCRATCH, 'room')
    shutil.rmtree(room, ignore_errors=True); os.makedirs(os.path.join(room, 'folder'))
    tar = subprocess.run(['git', '-C', REPO, 'archive', '--format=tar', TREES[TARGET]], capture_output=True, check=True).stdout
    subprocess.run(['tar', '-x', '-f', '-', '-C', os.path.join(room, 'folder')], input=tar, check=True)
    folder = os.path.join(room, 'folder')

    # the confirmations, unchanged
    rc1, o1, e1 = run([sys.executable, os.path.join(CONFIRM, 'C_R1_1.py'), room, os.path.join(SCRATCH, 'r11')])
    r = {}
    for line in o1.splitlines():
        m = re.match(r'^(engine )?(sip_\w+) (\{.*\})$', line)
        if m:
            r[(m.group(1) or '') + m.group(2)] = json.loads(m.group(3))
    rc6, o6, e6 = run([sys.executable, os.path.join(CONFIRM, 'c6_slice.py'), room, os.path.join(SCRATCH, 'c6_log.txt')])
    for line in o1.splitlines() + o6.splitlines():
        if line.startswith(('sip_', 'engine ', 'C6.', '     engine')):
            say('    ' + line[:260])
    c6 = o6
    eng_raw = (r.get('engine sip_nan_raw', {}).get('need') or [''])[0]
    rot_eng = re.findall(r"^C6\.1 (rot_nan|rot_inf): .*\| engine: \[\"a sky position \(the WCS card CD1_1 = '([^']*)' is not a number\)\"\]",
                         c6, re.M)
    d_eng = re.findall(r'^     engine: need \[\] \| rd \[.*\] \| ([\d.]+)" from eexp', c6, re.M)
    q0 = (all(shas[f] == SHAS[f] for f in SHAS) and rc1 == 0 and rc6 == 0
          and r.get('sip_ok', {}).get('off_arcsec') == 0.0 and r.get('sip_ok', {}).get('judge') == 'submit is OK'
          and 1.5 <= (r.get('sip_drop', {}).get('off_arcsec') or 0) <= 2.0
          and eng_raw == "a sky position (the WCS card A_2_0 = 'NAN' is not a number)"
          and r.get('engine sip_nan_str', {}).get('rd') is None and r.get('engine sip_ok', {}).get('rd') is not None
          and bool(re.search(r'^C6\.1 rot\.fits \(CD1_1 readable\): exit 0 \| record True \| judge submit is OK', c6, re.M))
          and len(rot_eng) == 2 and 'C6.1 engine on rot.fits: need []' in c6
          and bool(re.search(r'^C6\.2 eexp\.fits \(E exponent\): exit 0 \| record True \| judge submit is OK', c6, re.M))
          and len(d_eng) == 3 and all(float(x) < 0.001 for x in d_eng))
    say('Q0 %s  the controls: the confirmations the audit room\'s and run whole (exit %d, %d); sip_ok on the truth, sip_drop %s" '
        'off; rot.fits and eexp.fits accepted; the engine refuses sip_nan_raw, rot_nan and rot_inf and places the three D files %s"'
        % ('PASS' if q0 else 'FAIL', rc1, rc6, r.get('sip_drop', {}).get('off_arcsec'), '/'.join(d_eng)))

    raw = r.get('sip_nan_raw', {})
    q1 = raw.get('rc') == 2 and not raw.get('record') and raw.get('sky') is None and bool(eng_raw) and raw.get('need') == eng_raw
    say('Q1 %s  R1.1, sip_nan_raw: exit %s, record %s, need %r' % ('PASS' if q1 else 'FAIL', raw.get('rc'), bool(raw.get('record')),
                                                              raw.get('need')))
    q2 = True
    for name, text in (('rot_nan', 'NAN'), ('rot_inf', '1E400')):
        rc, rec, need, _ = cli(folder, os.path.join(room, 'cw1', 'c61', name + '.fits'))
        want = "a sky position (the WCS card CD1_1 = '%s' is not a number)" % text
        ok = rc == 2 and not rec and need == want
        q2 = q2 and ok
        say('    F6.1 %s: exit %d, record %s, need %r' % (name, rc, rec, need))
    say('Q2 %s  F6.1: CD1_1 unreadable (NAN, 1E400) refused at the sky in the page\'s words, the value as written' % ('PASS' if q2 else 'FAIL'))
    rc_e, rec_e, _, keep_e = cli(folder, os.path.join(room, 'cw1', 'c62', 'eexp.fits'))
    q3 = rc_e == 0 and rec_e and len(keep_e) == 2
    for name in ('crval_dexp', 'crpix_dexp', 'cd_dexp'):
        rc, rec, need, keep = cli(folder, os.path.join(room, 'cw1', 'c62', name + '.fits'))
        ok = rc == 0 and rec and keep == keep_e
        q3 = q3 and ok
        say('    F6.2 %s: exit %d, record %s, the E file\'s lines %s%s' % (name, rc, rec, keep == keep_e, '' if ok else ' | need %r | %s' % (need, keep[:1])))
    say('Q3 %s  F6.2: the D exponents read as the header says, the E file\'s record' % ('PASS' if q3 else 'FAIL'))

    rc, o, e = run([sys.executable, '-m', 'unittest', '-v', 'tests.test_fix_f7', 'tests.test_fix_f8'], cwd=ROOT)
    last = ([l for l in e.splitlines() if l.strip()] or ['no output'])[-1]
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', e, re.M)))
    q4 = rc == 0
    say('Q4 %s  tests/test_fix_f7.py and tests/test_fix_f8.py | %s%s' % ('PASS' if q4 else 'FAIL', last, (' | failing: ' + ', '.join(bad)) if bad else ''))

    c = subprocess.run([sys.executable, '-m', 'tests.strict'], cwd=ROOT, env=dict(os.environ, DOMINO_CALIBRATOR_TESTED_VERSIONS='1'),
                       capture_output=True, encoding='utf-8', errors='replace', timeout=5400)
    o = c.stdout + c.stderr
    line = (re.findall(r'^strict: .*$', o, re.M) or ['strict: no verdict'])[-1]
    q5 = c.returncode == 0 and bool(re.match(r'strict: PASS \(\d+ run, 0 failures, 0 errors, 0 skipped', line))
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', o, re.M)))
    say('Q5 %s  %s%s' % ('PASS' if q5 else 'FAIL', line, (' | failing: ' + ', '.join(bad)) if bad else ''))

    met = sum((q0, q1, q2, q3, q4, q5))
    say("# F8's bar on %s: %s, %d of 6" % (TARGET, 'MET' if met == 6 else 'NOT MET', met))
    return 0 if met == 6 else 1


if __name__ == '__main__':
    sys.exit(main())
