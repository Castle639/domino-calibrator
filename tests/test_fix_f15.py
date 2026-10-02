"""The fix room's F15: his addition of 2 Oct 2026, before the seal (the fix room's record of 1 Oct 2026, not in this repository, section
31): in the README only, at its foot, after the credit line and as its own sentence, "A human approves every release." The
credit line itself stays identical everywhere (item 27); nothing on the page or in CITATION.cff changes. Written before the
README changes, to fail on it as F14 left it, and to pass once it is changed.
"""
import os, re, unittest

import domino_calibrator
from tests import test_release_words as W

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CREDIT = "A Castle product from Domino Observatory. Built by Annie, the Castle's AI."
HUMAN = 'A human approves every release.'


def read(*p):
    return W.read(os.path.join(ROOT, *p))


class F15_AHumanApproves(unittest.TestCase):
    def test_the_readme_says_it_after_the_credit_line_as_its_own_sentence(self):
        t = read('README.md')
        foot = t[t.index('## Who made it'):]
        self.assertIn(CREDIT + ' ' + HUMAN, ' '.join(foot.split()))
        self.assertEqual(t.count(HUMAN), 1)

    def test_the_credit_line_stays_identical_and_nothing_else_changes(self):
        faces = {'README.md': read('README.md'), 'CHANGELOG.md': read('CHANGELOG.md'), 'CITATION.cff': read('CITATION.cff'),
                 'the page': read('page', 'index.html'), '__credit__': domino_calibrator.__credit__}
        for face, t in faces.items():
            with self.subTest(face):
                self.assertIn(CREDIT, ' '.join(t.split()))
                if face != 'README.md':
                    self.assertNotIn(HUMAN, t)
        self.assertEqual(domino_calibrator.__credit__, CREDIT)


if __name__ == '__main__':
    unittest.main()
