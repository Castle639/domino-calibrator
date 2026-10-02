"""The fix room's F6: the CI's first run on the new history, on Windows (1 Oct 2026; the fix room's record of 1 Oct 2026, not in this repository,
section 16). Written before the fix, to fail on the code and the words as the second seal left them (43b82a2), and to pass
once they are fixed. Three findings, each with his answer:

1  A closed pipe on Windows: the flush raises OSError EINVAL there, not BrokenPipeError, and the command line printed a
   traceback (F2's test, red on Windows only). His answer: it ends the same way on Windows as on Linux, exit code included.
   Tested here on any system with a stand-in: stdout raising OSError EINVAL where the pipe is closed, as Windows does.
2  The cutout recipe with a Windows path: 'C:\\Users\\...' in a plain Python string is a SyntaxError (\\U), and a path such as
   'D:\\data\\new\\frame.fits' silently becomes another (\\n). His answer: the recipe's words change, in the README and on the
   page, and the test checks what a Windows user would do: type the path inside the recipe's quotes.
3  F1's test of raw bytes in argv skips on Windows, which hands Python its arguments as UTF-16; the CI's Windows row did not
   allow that skip. His answer: name it in the Windows row with its reason, as K8 and K10 are named.
"""
import os, re, sys, ast, html, errno, subprocess, unittest

from tests.test_hardening import REC_ARGS, Tmp, comet, write

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CI = os.path.join(ROOT, '.github', 'workflows', 'tests.yml')
RAW_BYTES = 'test_the_command_line_with_raw_bytes_in_argv'

# The stand-in for Windows's stdout: every write goes to the real stdout (fd 1); where the pipe is closed, the error is the
# one Windows gives, OSError EINVAL, instead of POSIX's BrokenPipeError. Then the command line runs as `python -m` runs it.
STAND_IN = r'''
import io, os, sys, errno, runpy
class WindowsPipe(io.RawIOBase):
    def writable(self):
        return True
    def fileno(self):
        return 1
    def write(self, b):
        try:
            return os.write(1, bytes(b))
        except BrokenPipeError:
            raise OSError(errno.EINVAL, 'Invalid argument')
sys.stdout = io.TextIOWrapper(io.BufferedWriter(WindowsPipe()), encoding='utf-8')
if sys.argv[1] == '--control':
    try:
        sys.stdout.write('x\n' * 100000); sys.stdout.flush()
    except OSError as e:
        sys.stderr.write('errno %d\n' % e.errno)
    os.dup2(os.open(os.devnull, os.O_WRONLY), 1)
    raise SystemExit(0)
sys.argv = ['domino-calibrator'] + sys.argv[1:]
runpy.run_module('domino_calibrator.cli', run_name='__main__', alter_sys=True)
'''


def closed_pipe(args, windows):
    """The command line with its stdout's reader gone before a line is read, as `| head -0` does: (exit code, stderr).
    With windows=True, through the stand-in for Windows's stdout."""
    cmd = [sys.executable, '-c', STAND_IN] if windows else [sys.executable, '-m', 'domino_calibrator.cli']
    proc = subprocess.Popen(cmd + args, cwd=ROOT, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                            env=dict(os.environ, PYTHONUTF8='1'))
    proc.stdout.close()
    err = proc.stderr.read().decode('utf-8', 'replace'); rc = proc.wait(timeout=600)
    proc.stderr.close()
    return rc, err


class F6_1_ClosedPipeOnWindows(Tmp):
    def test_the_stand_in_raises_what_windows_raises(self):
        rc, err = closed_pipe(['--control'], windows=True)
        self.assertIn('errno %d' % errno.EINVAL, err, err[-300:])

    def test_a_closed_pipe_ends_the_same_way_on_windows_exit_code_included(self):
        img, _ = comet()
        good = write(self.p('c.fits'), img)
        import numpy as np
        const = write(self.p('const.fits'), np.full((71, 71), 7.0))
        for name, a, want in (('a measurement', [good] + REC_ARGS, 0), ('no comet', [const] + REC_ARGS, 2),
                              ('cannot measure', [self.p('none.fits')], 1)):
            for system, windows in (('POSIX', False), ('Windows', True)):
                with self.subTest(name, system=system):
                    rc, err = closed_pipe(a, windows)
                    self.assertNotIn('Traceback', err); self.assertNotIn('Exception ignored', err)
                    self.assertNotIn('Invalid argument', err); self.assertNotIn('BrokenPipeError', err)
                    self.assertEqual(rc, want, err[-300:])


def readme_recipe():
    t = open(os.path.join(ROOT, 'README.md'), encoding='utf-8').read()
    for b in re.findall(r'```(?:python)?\n(.*?)```', t, flags=re.S):
        if 'Cutout2D' in b:
            return b
    return None


def page_recipe():
    t = open(os.path.join(ROOT, 'page', 'index.html'), encoding='utf-8').read()
    for b in re.findall(r'<pre><code>(.*?)</code></pre>', t, flags=re.S):
        b = html.unescape(b)
        if 'Cutout2D' in b:
            return b + ('' if b.endswith('\n') else '\n')
    return None


def paths_given(src):
    """The recipe's two paths, as Python reads them: (the frame fits.open opens, the file writeto writes)."""
    got = {}
    for node in ast.walk(ast.parse(src)):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute) and node.func.attr in ('open', 'writeto'):
            if node.args and isinstance(node.args[0], ast.Constant):
                got[node.func.attr] = node.args[0].value
    return got.get('open'), got.get('writeto')


WINDOWS_PATHS = (r'C:\Users\you\Pictures\frame.fits', r'D:\data\new\frame.fits')   # \U: a SyntaxError; \n and \f: another path


class F6_2_TheRecipeOnWindows(unittest.TestCase):
    def test_both_faces_give_the_same_recipe(self):
        self.assertIsNotNone(readme_recipe(), 'no recipe in the README')
        self.assertEqual(page_recipe(), readme_recipe())

    def test_a_windows_path_typed_into_the_recipe_is_the_path_python_opens(self):
        for face, code in (('README.md', readme_recipe()), ('the page', page_recipe())):
            for typed in WINDOWS_PATHS:
                with self.subTest(face, path=typed):
                    out = typed.replace('frame.fits', 'cutout.fits')
                    src = code.replace('frame.fits', typed).replace('cutout.fits', out)   # inside the quotes, as a user types it
                    try:
                        got = paths_given(src)
                    except SyntaxError as e:
                        self.fail('the recipe does not compile with %s: %s' % (typed, e))
                    self.assertEqual(got, (typed, out))

    def test_the_words_say_why(self):
        for face, code in (('README.md', readme_recipe()), ('the page', page_recipe())):
            with self.subTest(face):
                self.assertRegex(code, r"#.*Windows.*r'[A-Z]:\\")


def matrix_rows():
    t = open(CI, encoding='utf-8').read()
    return {m.group(1): m.group(2) for m in re.finditer(r'\{ os: ([\w.-]+), python: "[\d.]+"(?:, may_skip: "([^"]*)")? \}', t)}


class F6_3_EachSystemsSkipsAreNamed(unittest.TestCase):
    def test_every_test_that_skips_on_a_system_is_allowed_in_that_systems_row(self):
        rows = matrix_rows()
        self.assertTrue(rows, 'no matrix rows read')
        found = []
        for f in sorted(os.listdir(HERE)):
            if f.endswith('.py'):
                src = open(os.path.join(HERE, f), encoding='utf-8').read()
                for cond, name in re.findall(r"@unittest\.skip(?:If|Unless)\(([^\n]*)\)\s*\n\s*def (test_\w+)", src):
                    for system, marks in (('windows', ("os.name == 'nt'", "sys.platform == 'win32'")),
                                          ('macos', ("sys.platform == 'darwin'",))):
                        if any(m in cond for m in marks):
                            found.append((system, name))
        self.assertIn(('windows', RAW_BYTES), found)                               # the control: the scan sees F1's skip
        for system, name in found:
            for os_, skips in rows.items():
                if os_.startswith(system):
                    with self.subTest(name, row=os_):
                        self.assertIn('--may-skip %s' % name, skips or '')

    def test_the_raw_bytes_skip_is_windows_only_and_the_readme_says_why(self):
        rows = matrix_rows()
        for os_, skips in rows.items():
            with self.subTest(os_):
                self.assertEqual(RAW_BYTES in (skips or ''), os_.startswith('windows'))
        t = re.sub(r'\s+', ' ', open(os.path.join(ROOT, 'README.md'), encoding='utf-8').read())
        self.assertRegex(t, r'Windows[^.]*UTF-16[^.]*--may-skip %s' % RAW_BYTES)


if __name__ == '__main__':
    unittest.main()
