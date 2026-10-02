#!/usr/bin/env python3
"""Launch step 5's bar: GitHub Pages' publishing workflow (the launch list's step 5; the build room's brief of 30 Sept 2026, not in this repository,
section 1). Written before the workflow exists (30 Sept 2026, the calibrator's build room), to be run red on the calibrator
as step 4 left it. Read at source first: GitHub serves a site from a branch's root, from its /docs folder, or through a
workflow, and the page is in page/ (docs.github.com, "Configuring a publishing source for your GitHub Pages site" and "Using
custom workflows with GitHub Pages"); the artifact "should not contain any symbolic or hard links" and its tar "must be
under 10GB"; the deploy job needs pages: write and id-token: write; the actions' newest majors run on Node 24 (their
action.yml). Its first run is his key (the launch list's step 10).

The clauses:
  P0  control: actionlint reports a planted fault in a copy of pages.yml (the deploy step's id removed, so steps.deployment
      is undefined)
  P1  actionlint 1.7.12, with ShellCheck 0.11.0 on its PATH, reports nothing on .github/workflows/pages.yml, nor on tests.yml
  P2  K18 (the workflow's content) is green, and red on a copy whose trigger adds pull_request
  P3  the artifact: page/ archived as upload-pages-artifact v5 archives it on Linux (tar --dereference --hard-dereference;
      .git, .github and hidden files left out): index.html at its root; every address the page loads (src, srcset, url(),
      <link href>) a regular file in it; no symbolic or hard link; under 10 GB
  P4  the whole suite, `python -m tests.strict` from calibrator/ on the kit with the tested-versions flag: PASS, 0/0/0
The science's own controls run after the green run, outside this script.

Usage: python calibrator/runs/pages_bar.py SCRATCH REPO TESTED_PYTHON [CLAUSES]
"""
import os, re, sys, time, shutil, tarfile, tempfile, subprocess

SCRATCH, REPO, TESTED_PY = sys.argv[1], sys.argv[2], sys.argv[3]
ONLY = set(sys.argv[4].split(',')) if len(sys.argv) > 4 else None
PKG = os.path.join(REPO, 'calibrator')
OUT = os.path.join(SCRATCH, 'pages_bar')
WF = os.path.join(PKG, '.github', 'workflows')
AL = os.path.join(SCRATCH, 'actionlint', 'actionlint')
K18 = 'tests.test_launch_steps.TestPagesWorkflow.test_k18_github_pages_publishes_page_on_a_push_to_main'
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
             PATH=os.path.join(SCRATCH, 'shellcheck', 'bin') + os.pathsep + os.path.dirname(TESTED_PY) + os.pathsep
             + '/opt/node22/bin' + os.pathsep + os.environ.get('PATH', ''))
    return e


def lint(path):
    c = subprocess.run([AL, '-no-color', path], capture_output=True, text=True, env=env())
    return c.returncode, c.stdout.strip()


def test_state(tid, cwd):
    c = subprocess.run([TESTED_PY, '-m', 'unittest', '-v', tid], cwd=cwd, env=env(), stdout=subprocess.PIPE,
                       stderr=subprocess.STDOUT, text=True, timeout=600)
    name = re.escape(tid.rsplit('.', 1)[1])
    if re.search(r'^ERROR: %s \(' % name, c.stdout, flags=re.M):
        return 'error'
    if re.search(r'^FAIL: %s \(' % name, c.stdout, flags=re.M):
        return 'red'
    return 'green' if re.search(r'^%s \(.*\) \.\.\. ok$' % name, c.stdout, flags=re.M) else 'absent'


def main():
    os.makedirs(OUT, exist_ok=True)
    print('# pages bar %s UTC | HEAD %s' % (time.strftime('%F %T', time.gmtime()), subprocess.run(
        ['git', '-C', REPO, 'log', '-1', '--format=%h'], capture_output=True, text=True).stdout.strip()), flush=True)
    pages = os.path.join(WF, 'pages.yml')

    if want('P0'):
        if os.path.exists(pages):
            s = open(pages, encoding='utf-8').read()
            planted = os.path.join(OUT, 'pages_planted.yml')
            open(planted, 'w').write(re.sub(r'^\s*id: deployment\n', '', s, flags=re.M))
            rc, out = lint(planted)
            verdict('P0', rc != 0 and 'property "deployment" is not defined' in out,
                    'the planted copy: exit %d, %d lines; the undefined step named: %s' % (rc, len(out.splitlines()),
                                                                                    'property "deployment" is not defined' in out))
        else:
            verdict('P0', False, 'no pages.yml to plant in')

    if want('P1'):
        r1 = lint(pages) if os.path.exists(pages) else (None, 'absent')
        r2 = lint(os.path.join(WF, 'tests.yml'))
        verdict('P1', r1[0] == 0 and not r1[1] and r2[0] == 0 and not r2[1],
                'pages.yml: %s | tests.yml: %s' % ('absent' if r1[0] is None else ('clean' if r1[0] == 0 and not r1[1] else 'exit %d: %s' % (r1[0], r1[1][:120])),
                                                     'clean' if r2[0] == 0 and not r2[1] else 'exit %d' % r2[0]))

    if want('P2'):
        st = test_state(K18, PKG)
        mut = os.path.join(OUT, 'p2_copy')
        shutil.rmtree(mut, ignore_errors=True)
        shutil.copytree(PKG, mut, ignore=shutil.ignore_patterns('__pycache__', 'runs', '*.egg-info', 'build', '.venv'))
        mp = os.path.join(mut, '.github', 'workflows', 'pages.yml')
        st2 = 'no file'
        if os.path.exists(mp):
            s = open(mp, encoding='utf-8').read()
            open(mp, 'w').write(s.replace('  workflow_dispatch:\n', '  workflow_dispatch:\n  pull_request:\n', 1))
            st2 = test_state(K18, mut)
        verdict('P2', st == 'green' and st2 == 'red', 'K18: %s | on a copy that adds pull_request: %s' % (st, st2))

    if want('P3'):
        tmp = tempfile.mkdtemp(prefix='pages_p3_', dir=OUT)
        tar = os.path.join(tmp, 'artifact.tar')
        c = subprocess.run(['tar', '--dereference', '--hard-dereference', '--directory', os.path.join(PKG, 'page'), '-cf', tar,
                            '--exclude=.git', '--exclude=.github', '--exclude=.[^/]*', '.'], capture_output=True, text=True)
        members = {}
        if c.returncode == 0:
            with tarfile.open(tar) as t:
                for m in t.getmembers():
                    members[os.path.normpath(m.name)] = m
        html = open(os.path.join(PKG, 'page', 'index.html'), encoding='utf-8').read()
        loads = re.findall(r'<(?:img|script|source|iframe|audio|video|embed)\b[^>]*\bsrc="([^"]*)"', html)
        loads += [u.strip().split(' ')[0] for s in re.findall(r'\bsrcset="([^"]*)"', html) for u in s.split(',')]
        loads += re.findall(r'<link\b[^>]*\bhref="([^"]*)"', html) + re.findall(r'url\(\s*[\'"]?([^\'")]+)', html)
        loads = sorted({l for l in loads if not l.startswith(('data:', '#'))})
        missing = [l for l in loads if not (os.path.normpath(l) in members and members[os.path.normpath(l)].isfile())]
        links = [n for n, m in members.items() if m.issym() or m.islnk()]
        size = os.path.getsize(tar) if os.path.exists(tar) else 0
        ok = c.returncode == 0 and 'index.html' in members and members['index.html'].isfile() and loads and not missing \
            and not links and size < 10 * 10 ** 9
        verdict('P3', ok, 'tar exit %d; %d members, index.html at the root: %s; the page loads %d addresses, %d missing%s; links %d; '
                '%.1f MB' % (c.returncode, len(members), 'index.html' in members, len(loads), len(missing),
                             (' (%s)' % ', '.join(missing[:4])) if missing else '', len(links), size / 1e6))
        shutil.rmtree(tmp, ignore_errors=True)

    if want('P4'):
        t0 = time.time()
        c = subprocess.run([TESTED_PY, '-m', 'tests.strict'], cwd=PKG, env=env(), stdout=subprocess.PIPE,
                           stderr=subprocess.STDOUT, text=True, timeout=5400)
        log = os.path.join(OUT, 'suite_P4.txt')
        open(log, 'w').write(c.stdout)
        m = STRICT.search(c.stdout)
        ok = bool(m) and m.group(1) == 'PASS' and c.returncode == 0 and m.group(3) == m.group(4) == m.group(5) == '0'
        verdict('P4', ok, '%s | exit %d, %.0f s | %s' % (m.group(0) if m else 'no strict summary', c.returncode, time.time() - t0,
                                                         os.path.relpath(log, SCRATCH)))

    names = [n for n in ('P0', 'P1', 'P2', 'P3', 'P4') if n in RESULTS]
    met = sum(1 for n in names if RESULTS[n])
    print('# pages bar: %s, %d of %d%s' % ('MET' if met == len(names) else 'NOT MET', met, len(names),
                                            '' if met == len(names) else ' (failing: %s)' % ' '.join(n for n in names if not RESULTS[n])))


if __name__ == '__main__':
    main()
