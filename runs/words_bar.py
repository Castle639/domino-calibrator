#!/usr/bin/env python3
"""Launch step 4's bar: the repository's words, with its name and owner (the launch list's step 4; the issue list's entries 4,
40 and 8's address; the build room's brief of 30 Sept 2026, not in this repository, section 1; his calls: domino-calibrator, under Castle639).
Written before the words change (30 Sept 2026, the calibrator's build room), to be run red on the calibrator as step 3 left
it.

Amendment 1, after the red run: run_tests read a failing test as absent. Its FAIL and ERROR patterns put a word boundary
after the name and a space (`name \b`), where the next character is '(' and no boundary can fall, so no failure line ever
matched; green, read by another pattern, was right. The patterns now ask for the space and the parenthesis. Nothing else
changes.

The page's links. The design record's constraint is that "the page makes no network request" (archive/CALIBRATOR_DESIGN_
2026-09-29.md, line 159); its test's control asked more, that every address in the page be relative, links included. A link
makes no request until someone follows it, and step 4 asks for two to the repository's README. So the control is narrowed
to what the page loads (src, srcset, url() and <link href>), and K16 allows the page's links to go to the repository's
README alone. W0 shows that both still catch what they are for.

The clauses:
  W0  control, on copies of the page: the narrowed D0 control fails on a planted <img> loaded from another site, K16 fails on
      a planted link to another site, and both pass on the copy with nothing planted
  W1  K15: the README's clone line and the folder it makes, before the install block; the test command, from the checkout's
      root whatever it is called (entry 4), with what its skips need named beside it (entry 40)
  W2  K16: the page's two README mentions, links to the repository's README, and no other link out of the page
  W3  K17: the repository's address in pyproject.toml (the repository and its issues) and in CITATION.cff (repository-code)
  W4  W6 (every path the README and the page name is in the folder that goes public, or among the curation list's files
      copied in beside the package at the build: tools/fetch_frames.py, tools/psfkit.py, data/hst-3i/ and its checksum
      list), and it still fails on a planted path that is neither
  W5  the whole suite, `python -m tests.strict` from calibrator/ on the kit with the tested-versions flag: PASS, 0/0/0
The science's own controls (C1 bit for bit, C2 with 0 FITTED and the same 43) run after the green run, outside this script
(W2 of the brief).

Usage: python calibrator/runs/words_bar.py SCRATCH REPO TESTED_PYTHON [CLAUSES]
"""
import os, re, sys, time, shutil, tempfile, subprocess

SCRATCH, REPO, TESTED_PY = sys.argv[1], sys.argv[2], sys.argv[3]
ONLY = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else None
PKG = os.path.join(REPO, 'calibrator')
OUT = os.path.join(SCRATCH, 'words_bar')
T = 'tests.'
D0 = T + 'test_page_design.TestTheDesignOnDisk.test_d0_controls'
K15 = T + 'test_launch_steps.TestRepositoryWords.test_k15_the_readme_says_where_the_repository_is_and_how_its_tests_run'
K16 = T + 'test_launch_steps.TestRepositoryWords.test_k16_the_pages_readme_mentions_are_links_to_the_repositorys_readme'
K17 = T + 'test_launch_steps.TestRepositoryWords.test_k17_the_repositorys_address_in_pyproject_and_citation'
W6 = T + 'test_release_words.TestPaths.test_w6_every_path_is_inside_the_folder_that_goes_public'
STRICT = re.compile(r'^strict: (PASS|FAIL) \((\d+) run, (\d+) failures, (\d+) errors, (\d+) skipped: (\d+) allowed, (\d+) not\)', re.M)
RESULTS = {}


def verdict(name, ok, detail):
    RESULTS[name] = ok
    print('%-3s %s  %s' % (name, 'PASS' if ok else 'FAIL', detail), flush=True)


def want(name):
    return ONLY is None or name in ONLY


def env():
    e = {k: v for k, v in os.environ.items() if k not in ('PYTHONPATH', 'VIRTUAL_ENV')}
    e.update(ADES_PYLIB=os.path.join(SCRATCH, 'pylib'), ADES_MASTER=os.path.join(SCRATCH, 'ades-master'),
             PLAYWRIGHT_MODULE='/opt/node22/lib/node_modules/playwright', DOMINO_CALIBRATOR_TESTED_VERSIONS='1',
             PATH=os.path.dirname(TESTED_PY) + os.pathsep + '/opt/node22/bin' + os.pathsep + os.environ.get('PATH', ''))
    return e


def run_tests(ids, cwd):
    """The named tests with unittest from cwd; returns {id: 'green' | 'red' | 'error' | 'absent'} and the output."""
    c = subprocess.run([TESTED_PY, '-m', 'unittest', '-v'] + ids, cwd=cwd, env=env(), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, timeout=900)
    out = c.stdout
    state = {}
    for i in ids:
        name = re.escape(i.rsplit('.', 1)[1])
        if re.search(r'^ERROR: %s \(' % name, out, flags=re.M):          # amendment 1: ' \(' where ' \b' could never match
            state[i] = 'error'
        elif re.search(r'^FAIL: %s \(' % name, out, flags=re.M):
            state[i] = 'red'
        elif re.search(r'^%s \(.*\) \.\.\. ok$' % name, out, flags=re.M):
            state[i] = 'green'
        else:
            state[i] = 'absent'
    return state, out


def copy_pkg(tag):
    d = os.path.join(OUT, tag)
    shutil.rmtree(d, ignore_errors=True)
    shutil.copytree(PKG, d, ignore=shutil.ignore_patterns('__pycache__', '*.egg-info', 'build', '.venv'))   # runs/ kept: W6 checks the README's paths into it
    return d


def plant(page_dir, old, new):
    p = os.path.join(page_dir, 'page', 'index.html')
    s = open(p, encoding='utf-8').read()
    assert old in s, old
    open(p, 'w', encoding='utf-8').write(s.replace(old, new, 1))


def main():
    os.makedirs(OUT, exist_ok=True)
    print('# words bar %s UTC | HEAD %s' % (time.strftime('%F %T', time.gmtime()), subprocess.run(
        ['git', '-C', REPO, 'log', '-1', '--format=%h'], capture_output=True, text=True).stdout.strip()), flush=True)

    if want('W0'):
        rows, ok = [], True
        clean = copy_pkg('w0_clean')
        st, _ = run_tests([D0, K16], clean)
        rows.append('clean: D0 %s, K16 %s' % (st[D0], st[K16]))
        img = copy_pkg('w0_img')
        plant(img, '</footer>', '<img src="https://example.org/x.png" alt=""></footer>')
        st1, _ = run_tests([D0], img)
        rows.append('an <img> from another site: D0 %s' % st1[D0])
        link = copy_pkg('w0_link')
        plant(link, '</footer>', '<a href="https://example.org/">elsewhere</a></footer>')
        st2, _ = run_tests([K16], link)
        rows.append('a link to another site: K16 %s' % st2[K16])
        ok = st[D0] == 'green' and st[K16] == 'green' and st1[D0] == 'red' and st2[K16] == 'red'
        verdict('W0', ok, ' | '.join(rows))

    for name, tid in (('W1', K15), ('W2', K16), ('W3', K17)):
        if want(name):
            st, out = run_tests([tid], PKG)
            fails = re.findall(r'^FAIL: \S+ \(%s\) \((.*)\)$' % re.escape(tid), out, flags=re.M)
            verdict(name, st[tid] == 'green', '%s: %s%s' % (tid.rsplit('.', 1)[1][:9], st[tid],
                    (' | failing subtests: ' + '; '.join(f[:70] for f in fails[:6])) if fails else ''))

    if want('W4'):
        st, _ = run_tests([W6], PKG)
        bad = copy_pkg('w4_path')
        p = os.path.join(bad, 'README.md')
        s = open(p, encoding='utf-8').read()
        open(p, 'w', encoding='utf-8').write(s.replace('## Limits', 'See `nowhere/at_all.py`.\n\n## Limits', 1))
        st2, _ = run_tests([W6], bad)
        verdict('W4', st[W6] == 'green' and st2[W6] == 'red', 'W6 on calibrator/: %s | on a copy naming nowhere/at_all.py: %s'
                % (st[W6], st2[W6]))

    if want('W5'):
        t0 = time.time()
        c = subprocess.run([TESTED_PY, '-m', 'tests.strict'], cwd=PKG, env=env(), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, timeout=5400)
        log = os.path.join(OUT, 'suite_W5.txt')
        open(log, 'w').write(c.stdout)
        m = STRICT.search(c.stdout)
        ok = bool(m) and m.group(1) == 'PASS' and c.returncode == 0 and m.group(3) == m.group(4) == m.group(5) == '0'
        verdict('W5', ok, '%s | exit %d, %.0f s | %s' % (m.group(0) if m else 'no strict summary', c.returncode, time.time() - t0,
                                                         os.path.relpath(log, SCRATCH)))

    names = [n for n in ('W0', 'W1', 'W2', 'W3', 'W4', 'W5') if n in RESULTS]
    met = sum(1 for n in names if RESULTS[n])
    print('# words bar: %s, %d of %d%s' % ('MET' if met == len(names) else 'NOT MET', met, len(names),
                                            '' if met == len(names) else ' (failing: %s)' % ' '.join(n for n in names if not RESULTS[n])))


if __name__ == '__main__':
    main()
