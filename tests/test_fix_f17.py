"""The fix room's F17: his two questions of 2 Oct 2026, afternoon (the fix room's record of 1 Oct 2026, not in this repository, section 36).
1  summary_differences let infinity through: abs(inf - x) > inf is False, so +inf or -inf passed against any finite value, and
   +inf against -inf. Infinity now counts as a difference, but against the same infinity.
2  runs/README.md said bit for bit holds "against records written on the same machine, as these were". The committed H3
   summary was written on 27 Sept 2026 in the study's room and never rewritten; this machine reproduces it. Bit for bit holds
   where numpy takes the same arithmetic paths, not on one machine: his words.
Written before the fix, to fail on the tests as F16 left them, and to pass once it is fixed.
"""
import os, unittest

from tests.test_fix_f12 import summary_differences
from tests.test_fix_f16 import summary, replace

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
INF, NAN = float('inf'), float('nan')
WORDS = ('Bit for bit holds where numpy takes the same arithmetic paths as the machine that wrote these records; '
         "elsewhere, a float's last digits can differ.")


class F17_1_Infinity(unittest.TestCase):
    def test_infinity_against_anything_else_is_a_difference(self):
        for got, want in ((INF, 1.0), (-INF, 1.0), (1.0, INF), (1.0, -INF), (INF, -INF), (-INF, INF), (INF, 1e308),
                          (INF, NAN), (NAN, -INF)):
            with self.subTest(got=got, want=want):
                self.assertNotEqual(summary_differences(got, want), [])

    def test_the_same_infinity_and_nan_against_nan_are_not(self):
        for got, want in ((INF, INF), (-INF, -INF), (NAN, NAN), (1.0, 1.0)):
            with self.subTest(got=got, want=want):
                self.assertEqual(summary_differences(got, want), [])

    def test_an_infinity_planted_in_the_summary_is_found(self):
        want = summary()
        for v in (INF, -INF):
            with self.subTest(planted=v):
                seen = []
                got = replace(want, lambda x: (seen.append(x) or v) if not seen and abs(x) > 1 else x)
                self.assertEqual(len(summary_differences(got, want)), 1)


class F17_2_WhereBitForBitHolds(unittest.TestCase):
    def test_runs_readme_says_it_in_his_words(self):
        t = ' '.join(open(os.path.join(ROOT, 'runs', 'README.md'), encoding='utf-8').read().split())
        self.assertIn(WORDS, t)
        self.assertNotIn('as these were', t)
        self.assertNotIn('on the same machine', t)


if __name__ == '__main__':
    unittest.main()
