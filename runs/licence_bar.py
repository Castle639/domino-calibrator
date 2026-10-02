#!/usr/bin/env python3
"""The bar for the licence and the release notes' Windows line (30 Sept 2026, night; the calibrator's launch room, at his
word: "The credit line moves out of LICENSE (the audit's option (a)) and stays in the README, CITATION.cff, the page and
--version. K1 and K3 amended, bar first." and "the PYTHONUTF8=1 line for Windows users of the MPC's validator").
GitHub read LICENSE as "Other": the audit room measured licensee 10.1.0 at 92.54 % against MIT, under its 98 %, with the
credit line inside the notice, and 100 with it dropped (option (a); its C7.1c). licensee is not installed here (rubygems is
not in W6), so L1 asks for SPDX's MIT text exactly, which is what scored 100.

  python runs/licence_bar.py LOG        from the repository's root

  L0  the control: L1's check fails on the MIT text with the credit line planted in its notice, and passes on the plain text
  L1  LICENSE is SPDX's MIT, exactly: "MIT License", the copyright line, the body; nothing else
  L2  K1 and K3, amended, and K4: the credit in the README, the page, --version and CITATION.cff, and not in LICENSE
  L3  K25: the release notes tell Windows users of the MPC's validator to set PYTHONUTF8=1
  L4  the whole suite, strict, on the kit with the tested versions' flag: PASS
"""
import os, re, sys, hashlib, subprocess
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
LOG = sys.argv[1]
out = open(LOG, 'w', encoding='utf-8')


def say(s):
    print(s); out.write(s + '\n'); out.flush()


def run(args, env=None):
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run(args, cwd=ROOT, env=e, capture_output=True, encoding='utf-8', errors='replace', timeout=3600)
    return r.returncode, r.stdout + r.stderr


def exact_mit(text, copyright, body):
    return ' '.join(text.split()) == ' '.join(('MIT License ' + copyright + ' ' + body).split())


def unit(test):
    rc, o = run([sys.executable, '-m', 'unittest', test])
    return rc == 0, (re.findall(r'^(OK.*|FAILED.*)$', o, re.M) or ['?'])[-1]


def main():
    from tests.test_release_package import CREDIT, COPYRIGHT, MIT_BODY
    say('# licence_bar | HEAD %s | its sha256 %s' % (run(['git', 'rev-parse', '--short', 'HEAD'])[1].strip(),
                                                    hashlib.sha256(open(__file__, 'rb').read()).hexdigest()))
    v = []
    plain = 'MIT License\n\n%s\n\n%s\n' % (COPYRIGHT, MIT_BODY)
    planted = 'MIT License\n\n%s\n%s\n\n%s\n' % (COPYRIGHT, CREDIT, MIT_BODY)
    ok = exact_mit(plain, COPYRIGHT, MIT_BODY) and not exact_mit(planted, COPYRIGHT, MIT_BODY)
    say('L0  %s  the plain MIT text passes: %s | with the credit planted in its notice, it fails: %s'
        % ('PASS' if ok else 'FAIL', exact_mit(plain, COPYRIGHT, MIT_BODY), not exact_mit(planted, COPYRIGHT, MIT_BODY))); v.append(ok)
    lic = open(os.path.join(ROOT, 'LICENSE'), encoding='utf-8').read()
    ok = exact_mit(lic, COPYRIGHT, MIT_BODY)
    say('L1  %s  LICENSE is SPDX\'s MIT exactly: %s | the credit in it: %s' % ('PASS' if ok else 'FAIL', ok, CREDIT in ' '.join(lic.split())))
    v.append(ok)
    k1, t1 = unit('tests.test_release_package.TestCredit')
    k3, t3 = unit('tests.test_release_package.TestLicenseAndCitation')
    say('L2  %s  K1: %s | K3 and K4: %s' % ('PASS' if k1 and k3 else 'FAIL', t1, t3)); v.append(k1 and k3)
    k25, t25 = unit('tests.test_launch_steps.TestReleaseNotes')
    say('L3  %s  K25: %s' % ('PASS' if k25 else 'FAIL', t25)); v.append(k25)
    rc, o = run([sys.executable, '-m', 'tests.strict'], env=dict(DOMINO_CALIBRATOR_TESTED_VERSIONS='1'))
    line = (re.findall(r'^strict: .*$', o, re.M) or ['strict: no verdict'])[-1]
    bad = re.findall(r'^(?:FAIL|ERROR): (\S+ \([^)]*\))', o, re.M)
    ok = rc == 0 and line.startswith('strict: PASS')
    say('L4  %s  the whole suite: %s' % ('PASS' if ok else 'FAIL', line))
    for b in bad[:20]:
        say('        failed: ' + b)
    v.append(ok)
    say('# licence bar: %s, %d of %d' % ('MET' if all(v) else 'NOT MET', sum(v), len(v)))
    return 0 if all(v) else 1


if __name__ == '__main__':
    sys.exit(main())
