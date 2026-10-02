"""1.13's red, measured on mutants (round 2's bar): the code under test_15b and test_16 is right, so their strengthened
twins cannot be red on it. Each twin must fail on a mutant where the old test passes. Copies of calibrator/ (runs/ left
out) in the scratchpad: ctrl (unchanged), mutA (_merged: the primary's cards over the image HDU's), mutB (sky_rms: rmsCorr's
sign flipped). Usage: python calibrator/runs/hard2_mutants.py SCRATCH_DIR REPO_DIR. Each run in a fresh interpreter from its copy's folder, so `calibrator` is the copy (printed)."""
import os, shutil, subprocess, sys, time
SP, REPO = sys.argv[1], sys.argv[2]
MUT = {'mutA': ('cli.py', "    m = phdr.copy()\n    for card in ihdr.cards:", "    m = ihdr.copy()\n    for card in phdr.cards:"),
       'mutB': ('ades.py', "    cor = float(S[0, 1] / (sra * sde))", "    cor = float(-S[0, 1] / (sra * sde))")}
TESTS = {'mutA': ['calibrator.tests.test_hardening.TestSilentWrong.test_15b_the_two_headers_are_merged',
                  'calibrator.tests.test_hardening_2.TestStrongerTests.test_1_13a_the_image_hdu_wins_the_merge'],
         'mutB': ['calibrator.tests.test_hardening.TestSilentWrong.test_16_rms_through_the_wcs',
                  'calibrator.tests.test_hardening_2.TestStrongerTests.test_1_13b_rms_corr_has_its_sign']}
print('# 1.13 mutant check %s UTC | repo HEAD %s' % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
      subprocess.run(['git', '-C', REPO, 'log', '-1', '--format=%h'], capture_output=True, text=True).stdout.strip()))
for name in ('ctrl', 'mutA', 'mutB'):
    root = os.path.join(SP, 'mut_' + name); shutil.rmtree(root, ignore_errors=True)
    shutil.copytree(os.path.join(REPO, 'calibrator'), os.path.join(root, 'calibrator'), ignore=shutil.ignore_patterns('runs', '__pycache__'))
    if name in MUT:
        f, old, new = MUT[name]; p = os.path.join(root, 'calibrator', f); s = open(p).read()
        assert s.count(old) == 1, (name, s.count(old)); open(p, 'w').write(s.replace(old, new))
        print('## %s: %s: %r -> %r' % (name, f, old.strip(), new.strip()))
    for t in (TESTS['mutA'] + TESTS['mutB'] if name == 'ctrl' else TESTS[name]):
        r = subprocess.run([sys.executable, '-c', 'import calibrator, unittest, sys; print("# calibrator from", calibrator.__file__); '
                            'sys.exit(0 if unittest.main(module=None, argv=["x", %r], exit=False).result.wasSuccessful() else 1)' % t],
                           cwd=root, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=''))
        src = [l for l in r.stdout.splitlines() if l.startswith('# calibrator from')][0].split('from ')[1]
        why = [l for l in r.stderr.splitlines() if l.startswith('AssertionError')]
        print('%-5s %-4s %-90s %s' % (name, 'PASS' if r.returncode == 0 else 'FAIL', t.split('.', 2)[2], ('| ' + why[-1][:110]) if why else ''))
        assert src.startswith(root), src
