"""Round 3, Part B's mutant check (the third hardening round's record of 28 Sept 2026, not in this repository, Part B): T1.8's pin and T1.20's two browser
tests strengthen tests of code that is right, so they cannot be red on it. Each must fail on a mutant where the old tests
pass, as round 2 did for 1.13 (hard2_mutants.py). Copies of calibrator/ (runs/ left out) in the scratchpad:
  ctrl  unchanged: every test below passes;
  mutC  cli.py, the scatter's generator seeded one off (seed + 1);
  mutD  cli.py, each noise redraw laid down transposed (the same numbers, other pixels);
  mutF1 index.html, a record field disables Copy and leaves the old record on screen (the refuters' T1.20 case);
  mutF2 index.html, a new radius or background no longer clears the answer;
  mutF3 index.html, choosing another HDU no longer clears the answer.
Usage: python calibrator/runs/hard3b_mutants.py SCRATCH_DIR REPO_DIR (PATH with node, PLAYWRIGHT_MODULE set). Each test runs in
a fresh interpreter from its copy's folder, so `calibrator` is the copy (checked)."""
import os, shutil, subprocess, sys, time
SP, REPO = sys.argv[1], sys.argv[2]
MUT = {'mutC': ('cli.py', 'rng = np.random.default_rng(seed)', 'rng = np.random.default_rng(seed + 1)'),
       'mutD': ('cli.py', 'oo = shrink(img + rng.normal(0.0, sig, img.shape), ', 'oo = shrink(img + rng.normal(0.0, sig, img.shape[::-1]).T, '),
       'mutF1': ('page/index.html', "['input', 'change'].forEach((ev) => $(id).addEventListener(ev, renderRecord)));",
                 "['input', 'change'].forEach((ev) => $(id).addEventListener(ev, () => { $('copy').disabled = true; })));"),
       'mutF2': ('page/index.html', "['sx', 'sy', 'est', 'r0', 'r1', 'rs', 'bgm', 'bgv'].forEach((id) =>", "['sx', 'sy', 'est'].forEach((id) =>"),
       'mutF3': ('page/index.html', 'cur = hdus[i]; clearAnswer();', 'cur = hdus[i];')}
T = 'calibrator.tests.'
OLD_RMS = [T + 'test_hardening.TestSilentWrong.test_16_rms_through_the_wcs', T + 'test_hardening.TestSilentWrong.test_16b_nan_border_keeps_the_noise',
           T + 'test_hardening_2.TestLostAnswers2.test_1_2_a_zero_scatter_keeps_the_record',
           T + 'test_hardening_2.TestLostAnswers2.test_1_4_a_negative_rms_noise_keeps_the_answer',
           T + 'test_hardening_2.TestLostAnswers2.test_1_18_a_lookup_table_wcs_is_read_with_its_file',
           T + 'test_hardening_2.TestStrongerTests.test_1_13b_rms_corr_has_its_sign']
PIN = [T + 'test_hardening_3b.TestTheGuard3b.test_t1_8_the_scatter_is_pinned']
B2 = T + 'test_hardening_2_page.TestPageInBrowser2.'
B3 = T + 'test_hardening_3b_page.TestPageInBrowser3b.'
TESTS = {'mutC': OLD_RMS + PIN, 'mutD': OLD_RMS + PIN,
         'mutF1': [B2 + 'test_1_10_a_changed_field_never_leaves_a_stale_record', B3 + 'test_t1_20_a_changed_field_rewrites_the_live_record'],
         'mutF2': [B2 + 'test_1_10_a_new_start_or_method_clears_the_answer', B3 + 'test_t1_20_a_new_radii_background_or_hdu_clears_the_answer'],
         'mutF3': [B2 + 'test_1_10_4_9_another_file_clears_the_answer', B2 + 'test_1_10_a_new_start_or_method_clears_the_answer',
                   B3 + 'test_t1_20_a_new_radii_background_or_hdu_clears_the_answer']}
print('# Part B mutant check %s UTC | repo HEAD %s' % (time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime()),
      subprocess.run(['git', '-C', REPO, 'log', '-1', '--format=%h'], capture_output=True, text=True).stdout.strip()), flush=True)
for name in ['ctrl'] + list(MUT):
    root = os.path.join(SP, 'mut3b_' + name); shutil.rmtree(root, ignore_errors=True)
    shutil.copytree(os.path.join(REPO, 'calibrator'), os.path.join(root, 'calibrator'), ignore=shutil.ignore_patterns('runs', '__pycache__'))
    if name in MUT:
        f, old, new = MUT[name]; p = os.path.join(root, 'calibrator', f); s = open(p).read()
        assert s.count(old) == 1, (name, s.count(old)); open(p, 'w').write(s.replace(old, new))
        print('## %s: %s: %r -> %r' % (name, f, old.strip(), new.strip()), flush=True)
    for t in (sorted({t for ts in TESTS.values() for t in ts}) if name == 'ctrl' else TESTS[name]):
        r = subprocess.run([sys.executable, '-c', 'import calibrator, unittest, sys; print("# calibrator from", calibrator.__file__); '
                            'sys.exit(0 if unittest.main(module=None, argv=["x", %r], exit=False).result.wasSuccessful() else 1)' % t],
                           cwd=root, capture_output=True, text=True, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1', PYTHONPATH=''))
        src = [l for l in r.stdout.splitlines() if l.startswith('# calibrator from')][0].split('from ')[1]
        why = [l for l in r.stderr.splitlines() if l.startswith('AssertionError')]
        print('%-5s %-4s %-100s %s' % (name, 'PASS' if r.returncode == 0 else 'FAIL', t.split('.', 2)[2], ('| ' + why[-1][:110]) if why else ''), flush=True)
        assert src.startswith(root), src
