#!/usr/bin/env python3
"""The bar for the CI's first findings (the launch list's step 9; 30 Sept 2026, the calibrator's launch room).

The first run on GitHub (Castle639/domino-calibrator at 934ca629) was green on Linux and macOS and red on Windows, 4 of 229:
  #1 the curve's failure line showed its path in Python's quoted form, each backslash doubled;
  #2 the MPC's validator, run by the tests, read our UTF-8 record in the Windows code page and stopped;
  #3 the tests read Node's UTF-8 output in the code page ('x' as two characters);
  #4 git rewrote line endings on checkout, and the fonts' licence failed its checksum.
His two questions: does the tool name UTF-8 wherever it opens a file or reads another program's output; does the fix for #4
cover every file whose bytes a checksum checks. Windows cannot be run here, so two stand-ins: a CP1252 locale built with
localedef (LOCPATH; Python's default encoding CP1252, UTF-8 mode off), and a clone checked out with core.autocrlf=true,
as GitHub's Windows runner checks out. The one real proof is the next run on GitHub.

  python runs/ci1_bar.py LOCPATH LOG        from the repository's root, with ADES_PYLIB, ADES_MASTER, PLAYWRIGHT_MODULE set

  B0  the controls, run first: the stand-in locale is in force (CP1252, UTF-8 mode off); a clone with core.autocrlf=true
      rewrites a planted text file with no .gitattributes; Python's EncodingWarning names a planted open() with no encoding.
  B1  #1: K19, the curve's failure line ends with the path as given (a backslash in a folder's name).
  B2  #2, #3: the whole suite, strict, under the CP1252 locale: PASS, 0 failures, 0 errors, 0 skipped; or, by
      amendment 2, t4_6 alone failing, the stand-in's one limit (Linux encodes a child's arguments in the locale).
  B3  his first question: K20, no text open() and no subprocess reading text without its encoding, in domino_calibrator/
      and tests/ (with its planted control); and the command line with --curve under -X warn_default_encoding: no
      EncodingWarning from domino_calibrator/.
  B4  #4, his second question: K21, .gitattributes is `* -text`; the repository at HEAD, cloned with core.autocrlf=true:
      every file's bytes equal the commit's, and test_d4 (the fonts and their licence, by sha256) passes in that clone.
  B5  the whole suite, strict, as the Castle runs it (the kit, UTF-8, the tested versions' flag): PASS, 0/0/0.
"""
import os, re, sys, shutil, subprocess, tempfile, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)                                   # tests/ is imported from the repository's root
PY = sys.executable
LOCPATH, LOG = sys.argv[1], sys.argv[2]
CP1252 = dict(LOCPATH=LOCPATH, LANG='en_US.CP1252', LC_ALL='en_US.CP1252', PYTHONUTF8='0')
out = open(LOG, 'w', encoding='utf-8')


def say(s):
    print(s); out.write(s + '\n'); out.flush()


def run(args, env=None, cwd=ROOT, timeout=1800):
    e = dict(os.environ); e.update(env or {})
    r = subprocess.run(args, cwd=cwd, env=e, capture_output=True, encoding='utf-8', errors='replace', timeout=timeout)
    return r.returncode, r.stdout + r.stderr


def git(*a, cwd):
    return run(['git', '-C', cwd] + list(a), cwd=cwd)


def unit(test, env=None, cwd=ROOT):
    rc, o = run([PY, '-m', 'unittest', test], env=env, cwd=cwd)
    return rc == 0, (re.findall(r'^(OK.*|FAILED.*)$', o, re.M) or ['?'])[-1]


def strict(env=None):
    rc, o = run([PY, '-m', 'tests.strict'], env=env)
    line = (re.findall(r'^strict: .*$', o, re.M) or ['strict: no verdict line'])[-1]
    bad = re.findall(r'^(?:FAIL|ERROR): (\S+ \([^)]*\))', o, re.M)
    return rc == 0 and line.startswith('strict: PASS'), line, bad


def autocrlf_clone(src_repo, dst):
    shutil.rmtree(dst, ignore_errors=True)
    rc, o = run(['git', '-c', 'core.autocrlf=true', 'clone', '-q', src_repo, dst], cwd=os.path.dirname(dst))
    assert rc == 0, o
    rc, o = git('-c', 'core.autocrlf=true', 'config', 'core.autocrlf', 'true', cwd=dst)
    differ = []
    for line in git('ls-files', '-s', cwd=dst)[1].splitlines():
        mode, blob, _, path = line.split(None, 3)
        want = subprocess.run(['git', '-C', dst, 'cat-file', 'blob', blob], capture_output=True).stdout
        if open(os.path.join(dst, path), 'rb').read() != want:
            differ.append(path)
    return differ


def repo_of(tree_dir_files, dst):
    """A fresh repository holding the given {path: bytes}, one commit."""
    shutil.rmtree(dst, ignore_errors=True); os.makedirs(dst)
    for p, b in tree_dir_files.items():
        os.makedirs(os.path.dirname(os.path.join(dst, p)) or dst, exist_ok=True)
        open(os.path.join(dst, p), 'wb').write(b)
    git('init', '-q', '-b', 'main', cwd=dst); git('add', '-A', cwd=dst)
    git('-c', 'user.name=Castle', '-c', 'user.email=castle@local', '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'x', cwd=dst)
    return dst


def main():
    head = run(['git', 'rev-parse', '--short', 'HEAD'])[1].strip()
    say('# ci1_bar | HEAD %s | its sha256 %s' % (head, hashlib.sha256(open(__file__, 'rb').read()).hexdigest()))
    work = tempfile.mkdtemp(prefix='ci1_')
    verdicts = []
    try:
        # B0, the controls
        rc, o = run([PY, '-c', 'import locale,sys;print(locale.getpreferredencoding(False), sys.flags.utf8_mode)'], env=CP1252)
        c1 = o.split() == ['CP1252', '0']
        plain = repo_of({'t.txt': b'a\nb\n'}, os.path.join(work, 'plain'))
        c2 = autocrlf_clone(plain, os.path.join(work, 'plain_crlf')) == ['t.txt']
        pl = os.path.join(work, 'planted.py'); open(pl, 'w', encoding='utf-8').write("open(%r).read()\n" % pl)
        rc, o = run([PY, '-X', 'warn_default_encoding', pl])
        c3 = 'EncodingWarning' in o and 'planted.py' in o
        b0 = c1 and c2 and c3
        say('B0  %s  the CP1252 locale in force: %s | a planted text file rewritten by an autocrlf clone: %s | '
            'a planted open() named by EncodingWarning: %s' % ('PASS' if b0 else 'FAIL', c1, c2, c3))
        verdicts.append(b0)

        # B1, #1
        ok, v = unit('tests.test_launch_steps.TestCurvePath')
        say('B1  %s  K19, the curve\'s failure ends with the path as given: %s' % ('PASS' if ok else 'FAIL', v))
        verdicts.append(ok)

        # B2, #2 and #3: the whole suite under the code page
        ok, line, bad = strict(CP1252)
        # amendment 2: t4_6 runs the command line with 'Łukasz' in its arguments. On Linux, Python encodes a child's
        # arguments in the locale's encoding, and CP1252 has no 'Ł', so the test's own process raises before the tool runs
        # (measured, 18:14 UTC). Windows passes arguments as UTF-16, and its run passed t4_6. The stand-in's one limit.
        STAND_IN = 'test_t4_6_a_name_the_console_cannot_encode_keeps_the_record'
        rest = [b for b in bad if STAND_IN not in b]
        m = re.search(r'\((\d+) run, (\d+) failures, (\d+) errors, (\d+) skipped', line)
        ok = ok or (m is not None and not rest and int(m.group(2)) + int(m.group(3)) == 1 and m.group(4) == '0'
                    and any(STAND_IN in b for b in bad))
        say('B2  %s  the whole suite under CP1252: %s%s' % ('PASS' if ok else 'FAIL', line,
            ' (t4_6, the stand-in\'s limit, allowed by amendment 2)' if len(bad) != len(rest) else ''))
        for b in bad:
            say('        failed: %s' % b)
        verdicts.append(ok)

        # B3, his first question
        ok20, v20 = unit('tests.test_launch_steps.TestTextNamesItsEncoding')
        from tests.test_launch_steps import encoding_omissions
        paths = [os.path.join(ROOT, d, f) for d in ('domino_calibrator', 'tests')
                 for f in sorted(os.listdir(os.path.join(ROOT, d))) if f.endswith('.py')]
        n = len(encoding_omissions(paths))
        from tests.test_hardening import comet, write, REC_ARGS
        img, _ = comet()
        fp = write(os.path.join(work, 'c.fits'), img)
        rc, o = run([PY, '-X', 'warn_default_encoding', '-m', 'domino_calibrator.cli', fp, '--curve',
                     os.path.join(work, 'curve.csv')] + REC_ARGS, env=dict(PYTHONPATH=ROOT))
        ours = [l for l in o.splitlines() if 'EncodingWarning' in l and os.path.join(ROOT, 'domino_calibrator') in l]
        ok = ok20 and n == 0 and rc == 0 and not ours
        say('B3  %s  K20: %s, omissions %d | the command line with --curve under warn_default_encoding: exit %d, '
            'EncodingWarnings from domino_calibrator/ %d' % ('PASS' if ok else 'FAIL', v20, n, rc, len(ours)))
        for l in ours[:5]:
            say('        ' + l.strip()[:200])
        verdicts.append(ok)

        # B4, #4 and his second question
        ok21, v21 = unit('tests.test_launch_steps.TestTheCheckoutIsTheCommit')
        prefix = run(['git', 'rev-parse', '--show-prefix'])[1].strip()      # '' in the public repository, calibrator/ in the Castle
        top = run(['git', 'rev-parse', '--show-toplevel'])[1].strip()      # amendment 1: HEAD:<path> is read from the top level
        tar = subprocess.run(['git', '-C', top, 'archive', '--format=tar', 'HEAD:' + prefix], capture_output=True).stdout
        assert tar, 'git archive gave nothing'
        src = os.path.join(work, 'head'); os.makedirs(src)
        subprocess.run(['tar', '-x', '-f', '-', '-C', src], input=tar, check=True)
        files = {}
        for dp, dn, fn in os.walk(src):
            for f in fn:
                p = os.path.join(dp, f); files[os.path.relpath(p, src)] = open(p, 'rb').read()
        head_repo = repo_of(files, os.path.join(work, 'head_repo'))
        clone = os.path.join(work, 'head_crlf')
        differ = autocrlf_clone(head_repo, clone)
        okd4, vd4 = unit('tests.test_page_design.TestTheDesignOnDisk.test_d4_inter_beside_the_page_unchanged_with_its_licence',
                         env=dict(PYTHONPATH=clone), cwd=clone)
        ok = ok21 and not differ and okd4
        say('B4  %s  K21: %s | HEAD cloned with core.autocrlf=true: %d of %d files differ from the commit%s | test_d4 there: %s'
            % ('PASS' if ok else 'FAIL', v21, len(differ), len(files), (' (first: %s)' % ', '.join(differ[:4])) if differ else '', vd4))
        verdicts.append(ok)

        # B5, the whole suite as the Castle runs it
        ok, line, bad = strict(dict(DOMINO_CALIBRATOR_TESTED_VERSIONS='1'))
        say('B5  %s  the whole suite, UTF-8, the kit with the flag: %s' % ('PASS' if ok else 'FAIL', line))
        for b in bad:
            say('        failed: %s' % b)
        verdicts.append(ok)
    finally:
        shutil.rmtree(work, ignore_errors=True)
    met = sum(verdicts)
    say('# ci1 bar: %s, %d of %d' % ('MET' if met == len(verdicts) == 6 else 'NOT MET', met, 6))
    return 0 if met == 6 else 1


if __name__ == '__main__':
    sys.exit(main())
