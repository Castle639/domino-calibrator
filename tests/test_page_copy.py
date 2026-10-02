"""The page's Copy: the first click copies (29 Sept 2026, the calibrator's tenth room). His test on claude.ai: "It first said
could not copy then when I clicked it again it said copied. Let's make sure this is solved." The page asked the browser's
async clipboard only, which a host may refuse on a first click (a frame that has not taken focus yet) or refuse outright
(a frame without the clipboard permission); measured first on a toy in headless Chromium, the synchronous copy (a
selection and the copy command, inside the click) copied on the first click in every host tried. Written to fail on the
page as the tenth room found it (c2f75f3) and to pass once the page copies by selection first and asks the async clipboard
second; every case is a subTest, and the cases marked "control" pass before and after. Round 3's T4.2 (Copy says whether
it copied) stays in test_hardening_3_page.py, its stubs set for both ways.
"""
import os, re, json, shutil, tempfile, unittest, warnings, subprocess
import numpy as np

from domino_calibrator import synth
from tests.test_hardening_page import fits_bytes, PAGE, NODE, PW
from tests.test_hardening_2_page import TAN
from tests.test_hardening_3_page import REC3

# init scripts for browser_cases.js (run in the page before its own). What the copy command copied is the text selected
# when it ran: a textarea's selection, else the page's.
SELECTED = ("const a = document.activeElement; return a && typeof a.value === 'string' ? a.value.substring(a.selectionStart, a.selectionEnd)"
            " : String(window.getSelection());")
EXEC_REAL = ("(() => { const real = document.execCommand.bind(document); document.execCommand = function (c) {"
             " if (c === 'copy') window.__exec = (function () { " + SELECTED + " })(); return real.apply(null, arguments); }; })();")
EXEC_FALSE = "document.execCommand = function () { return false; };"
EXEC_THROWS = "document.execCommand = function () { throw new Error('the copy command is refused'); };"
ASYNC_OK = ("Object.defineProperty(navigator, 'clipboard', { value: { writeText: (t) => { window.__copied = t; return Promise.resolve(); } },"
            " configurable: true });")
ASYNC_FIRST_REFUSED = ("(() => { let n = 0; Object.defineProperty(navigator, 'clipboard', { value: { writeText: (t) => n++ === 0"
                       " ? Promise.reject(new Error('Document is not focused.')) : (window.__copied = t, Promise.resolve()) }, configurable: true }); })();")
ASYNC_REFUSED = ("Object.defineProperty(navigator, 'clipboard', { value: { writeText: () => Promise.reject(new Error('Write permission denied')) },"
                 " configurable: true });")
ASYNC_NONE = "Object.defineProperty(navigator, 'clipboard', { value: undefined, configurable: true });"
COPIED = "[window.__exec || null, window.__copied || null]"


@unittest.skipIf(NODE is None or PW is None, 'no node or no playwright')
class TestTheFirstClickCopies(unittest.TestCase):
    """Copy, clicked once, in the hosts a user may meet (page/browser_cases.js, with init scripts)."""
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore')
        cls.d = tempfile.mkdtemp()
        img, _ = synth.render(71, 35.25, 34.85, flux_n=3e4, k=400.0, a=0.3, model='dipole', psf=('gauss', 2.5), sub=10)
        img = synth.add_noise(img, 150.0, 5.0, np.random.default_rng(5)).astype(np.float32)
        good = fits_bytes(os.path.join(cls.d, 'good.fits'), img, **dict(TAN, **{'DATE-OBS': '2025-12-27T16:04:29.000', 'EXPTIME': 120.0}))
        first = dict(file=good, x=35, y=35, set=dict(REC3), run=True)
        cases = [dict(name='first_click', init=ASYNC_FIRST_REFUSED + EXEC_REAL, steps=[first, dict(copy=True, eval=COPIED)]),
                 dict(name='no_async_api', init=ASYNC_NONE + EXEC_REAL, steps=[first, dict(copy=True, eval=COPIED)]),
                 dict(name='exec_refused', init=ASYNC_OK + EXEC_FALSE, steps=[first, dict(copy=True, eval=COPIED)]),
                 dict(name='exec_throws', init=ASYNC_OK + EXEC_THROWS, steps=[first, dict(copy=True, eval=COPIED)]),
                 dict(name='every_way_refused', init=ASYNC_REFUSED + EXEC_FALSE,
                      steps=[first, dict(copy=True, eval='String(window.getSelection())')])]
        cp = os.path.join(cls.d, 'cases.json')
        with open(cp, 'w', encoding='utf-8') as f:
            json.dump(cases, f)
        r = subprocess.run([NODE, os.path.join(PAGE, 'browser_cases.js'), cp], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600,
                           env=dict(os.environ, PLAYWRIGHT_MODULE=PW))
        cls.err = r.stderr[-800:]
        try:
            cls.res = {c['name']: c for c in json.loads(r.stdout)}
        except Exception:
            cls.res = None

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def steps(self, name):
        self.assertIsNotNone(self.res, 'browser_cases.js gave no result: ' + self.err)
        c = self.res[name]
        self.assertEqual(len(c.get('steps', [])), 2, {k: v for k, v in c.items() if k != 'steps'})
        return c['steps']

    def test_the_first_click_copies_the_record(self):
        for name, control in (('first_click', False), ('no_async_api', False), ('exec_refused', True), ('exec_throws', True)):
            with self.subTest(('control: ' if control else '') + name):
                s0, s1 = self.steps(name)
                self.assertTrue(s0['ades'].startswith('# version=2022'), s0['ades'][:200])
                self.assertRegex(s1['text'], re.compile('Copied: the record above is on the clipboard'))
                self.assertNotRegex(s1['text'], re.compile('could not copy', re.I))
                self.assertIn(s0['ades'], [t for t in s1['eval'] if t], 'what went to the clipboard is not the record')
        with self.subTest('control: every way refused: "Could not copy", and the record selected for Ctrl+C'):
            s0, s1 = self.steps('every_way_refused')
            self.assertRegex(s1['text'], re.compile('Could not copy'))
            # the selection's text is the record without its final line break, which is what Ctrl+C copies (measured on
            # the page as found: the bar's one amendment, before any fix)
            self.assertEqual(s1['eval'], s0['ades'].rstrip('\n'))


if __name__ == '__main__':
    unittest.main()
