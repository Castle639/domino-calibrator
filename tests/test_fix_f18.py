"""The fix room's F18: the re-check room's B3' finding (2 Oct 2026, evening). Three rounds' own bars and logs named what their
trims took out; at his word they stay in our own records and leave the public copy, and runs/README.md says so, in his
sentence. Written before the fix, to fail on runs/README.md as F17 left it, and to pass once it is fixed. What the copy holds
is checked by runs/fix_f18_bar.py, on the copy itself.
"""
import os, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SENTENCE = ('The bars and logs of three rounds that took private words out of this public copy (F9, F13 and F14) are kept '
            'in our own records too, because they name what was taken out; their tests and science-control logs are here.')


class F18_TheRecordsKeptInOurOwn(unittest.TestCase):
    def test_runs_readme_says_it_in_his_sentence_once_among_the_checks(self):
        t = ' '.join(open(os.path.join(ROOT, 'runs', 'README.md'), encoding='utf-8').read().split())
        self.assertEqual(t.count(SENTENCE), 1)
        checks = t[t.index('**The checks**'):]
        self.assertIn(SENTENCE, checks)

    def test_the_rounds_tests_named_in_it_are_here(self):
        for n in (9, 13, 14):
            with self.subTest(round=n):
                self.assertTrue(os.path.exists(os.path.join(HERE, 'test_fix_f%d.py' % n)))


if __name__ == '__main__':
    unittest.main()
