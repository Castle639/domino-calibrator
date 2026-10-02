#!/usr/bin/env python3
"""The fix room's F7 bar: R1.1 from the second audit room's regression check (1 Oct 2026, his word for the night, in the room's
report, section 20). Committed with tests/test_fix_f7.py before it runs: red on the command line as the third seal left it,
green after the fix. Its control is the audit room's own confirmation of R1.1 (confirm/C_R1_1.py on its branch, sha256
3c911895...), run unchanged on a copy of calibrator/ at HEAD, writing only into the scratch folder it is given.

  python runs/fix_f7_bar.py LOG SCRATCH C_R1_1      from calibrator/, with ADES_PYLIB, ADES_MASTER and PLAYWRIGHT_MODULE set
                                                   (C_R1_1: the confirmation's path, its regress_engine.js at ../regression/)

  R0  the controls, from the confirmation's own run: sip_ok gives a record on the truth (0.000"); sip_drop, the card removed,
      gives a record 1.5-2.0" off (the dropped term is there to see); the page's engine refuses sip_nan_raw and sip_nan_str
      at the sky, and gives sip_ok and sip_drop a position; the command line refuses sip_nan_str (exit 2), as before
  R1  the finding, by the same run: sip_nan_raw (A_2_0 = NAN, unquoted) exit 2, no sky position, no record, and its need
      word for word the page's engine's
  R2  tests/test_fix_f7.py: A_2_0, CRPIX1, CD1_1 and B_ORDER unreadable each refused at the sky in the page's words, the
      note kept; a card outside the WCS (FOCUSPOS) still left out with a note and a record; a readable SIP still recorded
  R3  the whole suite, strict, on the kit with the tested versions' flag: PASS, 0 failures, 0 errors, 0 skipped
"""
import os, re, sys, json, shutil, hashlib, subprocess

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))       # calibrator/
LOG, SCRATCH, CONFIRM = sys.argv[1:4]
out = open(LOG, 'w', encoding='utf-8')
CONFIRM_SHA = '3c911895a809983df33f888feff4a706b89789f6855bd6f40db001e0faf628cb'


def say(s):
    print(s, flush=True); out.write(s + '\n'); out.flush()


def confirmation():
    """The audit room's C_R1_1.py on a copy of calibrator/ at HEAD: {name: its result}, {'engine ' + name: the engine's}."""
    room = os.path.join(SCRATCH, 'room')
    shutil.rmtree(room, ignore_errors=True); os.makedirs(os.path.join(room, 'folder'))
    tar = subprocess.run(['git', '-C', ROOT, 'archive', '--format=tar', 'HEAD'], capture_output=True, check=True).stdout
    subprocess.run(['tar', '-x', '-f', '-', '-C', os.path.join(room, 'folder')], input=tar, check=True)
    o = os.path.join(SCRATCH, 'out')
    shutil.rmtree(o, ignore_errors=True)
    c = subprocess.run([sys.executable, CONFIRM, room, o], capture_output=True, encoding='utf-8', errors='replace', timeout=1800)
    res = {}
    for line in c.stdout.splitlines():
        m = re.match(r'^(engine )?(sip_\w+) (\{.*\})$', line)
        if m:
            res[(m.group(1) or '') + m.group(2)] = json.loads(m.group(3))
    return res, c.returncode, c.stderr[-300:]


def main():
    head = subprocess.run(['git', '-C', ROOT, 'rev-parse', '--short', 'HEAD'], capture_output=True, encoding='utf-8').stdout.strip()
    me = hashlib.sha256(open(CONFIRM, 'rb').read()).hexdigest()
    say('# fix_f7_bar | HEAD %s | the confirmation %s (%s)' % (head, me[:12], 'the audit room\'s' if me == CONFIRM_SHA else 'OTHER'))
    res, rc, err = confirmation()
    for k in ('sip_ok', 'sip_nan_raw', 'sip_nan_str', 'sip_drop'):
        r = res.get(k, {})
        say('    %-12s rc %s | off %s | record %s | need %s | judge %s' % (k, r.get('rc'), r.get('off_arcsec'), bool(r.get('record')),
                                                                       r.get('need'), r.get('judge')))
    for k in ('sip_ok', 'sip_nan_raw', 'sip_nan_str', 'sip_drop'):
        say('    engine %-12s %s' % (k, json.dumps(res.get('engine ' + k), ensure_ascii=False)))
    ok_, drop, nstr = res.get('sip_ok', {}), res.get('sip_drop', {}), res.get('sip_nan_str', {})
    e = {k: res.get('engine ' + k, {}) for k in ('sip_ok', 'sip_nan_raw', 'sip_nan_str', 'sip_drop')}
    eng_words = (e['sip_nan_raw'].get('need') or [''])[0]
    r0 = (me == CONFIRM_SHA and rc == 0 and ok_.get('rc') == 0 and bool(ok_.get('record')) and ok_.get('off_arcsec') == 0.0
          and drop.get('rc') == 0 and bool(drop.get('record')) and 1.5 <= (drop.get('off_arcsec') or 0) <= 2.0
          and e['sip_nan_raw'].get('rd') is None and e['sip_nan_str'].get('rd') is None
          and eng_words == "a sky position (the WCS card A_2_0 = 'NAN' is not a number)"
          and e['sip_ok'].get('rd') is not None and e['sip_drop'].get('rd') is not None
          and nstr.get('rc') == 2 and not nstr.get('record'))
    say('R0 %s  the controls: the confirmation the audit room\'s and run whole; sip_ok on the truth; sip_drop %s" off; the engine '
        'refuses both NaN files and places the other two; sip_nan_str refused here' % ('PASS' if r0 else 'FAIL', drop.get('off_arcsec')))
    raw = res.get('sip_nan_raw', {})
    r1 = (raw.get('rc') == 2 and not raw.get('record') and raw.get('sky') is None and raw.get('judge') == 'no record'
          and bool(eng_words) and raw.get('need') == eng_words)
    say('R1 %s  sip_nan_raw: rc %s, record %s, sky %s, need %r (the engine: %r)' % ('PASS' if r1 else 'FAIL', raw.get('rc'),
        bool(raw.get('record')), raw.get('sky'), raw.get('need'), eng_words))

    c = subprocess.run([sys.executable, '-m', 'unittest', '-v', 'tests.test_fix_f7'], cwd=ROOT, capture_output=True,
                       encoding='utf-8', errors='replace', timeout=1800)
    last = ([l for l in c.stderr.splitlines() if l.strip()] or ['no output'])[-1]
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', c.stderr, re.M)))
    r2 = c.returncode == 0
    say('R2 %s  tests/test_fix_f7.py | %s%s' % ('PASS' if r2 else 'FAIL', last, (' | failing: ' + ', '.join(bad)) if bad else ''))

    env = dict(os.environ, DOMINO_CALIBRATOR_TESTED_VERSIONS='1')
    c = subprocess.run([sys.executable, '-m', 'tests.strict'], cwd=ROOT, env=env, capture_output=True, encoding='utf-8',
                       errors='replace', timeout=5400)
    o = c.stdout + c.stderr
    line = (re.findall(r'^strict: .*$', o, re.M) or ['strict: no verdict'])[-1]
    r3 = c.returncode == 0 and bool(re.match(r'strict: PASS \(\d+ run, 0 failures, 0 errors, 0 skipped', line))
    bad = sorted(set(re.findall(r'^(?:FAIL|ERROR): (\w+) \(', o, re.M)))
    say('R3 %s  %s%s' % ('PASS' if r3 else 'FAIL', line, (' | failing: ' + ', '.join(bad)) if bad else ''))

    met = sum((r0, r1, r2, r3))
    say("# F7's bar: %s, %d of 4" % ('MET' if met == 4 else 'NOT MET', met))
    return 0 if met == 4 else 1


if __name__ == '__main__':
    sys.exit(main())
