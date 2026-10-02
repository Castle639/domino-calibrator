"""The README's install, run as written on this machine (the launch list's step 2: on Windows and macOS the CI runs the
README's own lines; on Linux, K8 runs them in Ubuntu's own shell). The lines are read from the README when this runs, not
copied into the CI: on Windows, the code spans of its sentence that begins "On Windows", in Windows PowerShell (the first two
run, the third is the command, asked for --version); elsewhere, the first fenced block under "## Install", in bash, then
`domino-calibrator --version`. They run in a fresh copy of the folder (runs/ and caches left out), as a stranger's checkout
holds it, and the command must answer with the version and the credit.

    python tests/readme_install.py [--print windows|posix]         (from the checkout's root)

--print shows the lines one system would run, and runs nothing. Exit 0 only when the lines ran to their end and the command
answered. Written 29 Sept 2026 (the calibrator's thirteenth room).
"""
import os, re, sys, shutil, argparse, tempfile, subprocess

PKG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = 'domino-calibrator'
CREDIT = "A Castle product from Domino Observatory. Built by Annie, the Castle's AI."


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


def install_section():
    m = re.search(r'^## Install\n(.*?)(?=^## )', read(os.path.join(PKG, 'README.md')), flags=re.S | re.M)
    return m.group(1) if m else ''


def posix_lines():
    """The first fenced block under '## Install', line by line."""
    b = re.search(r'```[^\n]*\n(.*?)```', install_section(), flags=re.S)
    return [l for l in (b.group(1) if b else '').splitlines() if l.strip()]


def windows_lines():
    """The code spans of the sentence that begins 'On Windows', in order: the sentence ends at the first full stop outside a
    code span that is followed by a space or the end of the line."""
    t = install_section()
    i = t.find('On Windows')
    if i < 0:
        return []
    spans, inside, cur = [], False, ''
    for k in range(i, len(t)):
        ch = t[k]
        if ch == '`':
            if inside:
                spans.append(cur)
                cur = ''
            inside = not inside
        elif inside:
            cur += ch
        elif ch == '.' and (k + 1 == len(t) or t[k + 1] in ' \n'):
            break
    return spans


def version():
    return re.search(r"^__version__ = '([^']+)'", read(os.path.join(PKG, 'domino_calibrator', '__init__.py')), flags=re.M).group(1)


def main(argv=None):
    ap = argparse.ArgumentParser(prog='readme_install.py', description="The README's install lines, run as written.")
    ap.add_argument('--print', dest='show', choices=('windows', 'posix'), help='print the lines one system would run')
    a = ap.parse_args(argv)
    if a.show:
        print('\n'.join(windows_lines() if a.show == 'windows' else posix_lines()))
        return 0
    windows = sys.platform == 'win32'
    lines = windows_lines() if windows else posix_lines()
    if (windows and len(lines) != 3) or not lines:
        print('readme_install: FAIL (the README gives no install lines for this system: %r)' % lines)
        return 1
    tmp = tempfile.mkdtemp(prefix='readme_install_')
    try:
        src = os.path.join(tmp, 'checkout')
        shutil.copytree(PKG, src, ignore=shutil.ignore_patterns('runs', '__pycache__', '*.egg-info', 'build', '.venv'))
        env = {k: v for k, v in os.environ.items() if k not in ('VIRTUAL_ENV', 'PYTHONPATH', 'PYTHONHOME')}
        if windows:
            steps = lines[:2] + [lines[2] + ' --version']
            script = '\n'.join('%s\nif ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }' % s for s in steps)
            cmd = ['powershell', '-NoProfile', '-NonInteractive', '-Command', script]
        else:
            script = '\n'.join(lines + ['%s --version' % NAME]) + '\n'
            cmd = ['bash', '-e', '-c', script]
        print('readme_install: running in %s, as %s:\n%s' % (src, cmd[0], script), flush=True)
        c = subprocess.run(cmd, cwd=src, env=env, capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=1200)
        out = c.stdout + c.stderr
        print(out[-3000:], flush=True)
        answered = ('%s %s' % (NAME, version())) in c.stdout and CREDIT in re.sub(r'\s+', ' ', c.stdout)
        ok = c.returncode == 0 and answered
        print('readme_install: %s (exit %d; the command %s)' % ('PASS' if ok else 'FAIL', c.returncode,
                                                               'answered with the version and the credit' if answered else 'did not answer'))
        return 0 if ok else 1
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


if __name__ == '__main__':
    sys.exit(main())
