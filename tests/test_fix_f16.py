"""The fix room's F16: the study's summary compared across machines (2 Oct 2026; the fix room's record of 1 Oct 2026, not in this repository,
section 34). The CI's first run on the public repository failed on one test only, F12_5, which compared runs/h3_report.py's
regenerated summary with the committed one exactly: on GitHub's runners a few floats differed in their last digits.
Measured: the runners' logs show 1.7e-16, 1.5e-16 and 2.1e-15 relative (1, 1 and 10 ulps); here, numpy without AVX-512
gives the Linux runners' value and moves 10 of the 9,070 floats, by at most 8.9e-16 relative and 5.7e-14 absolute.
Amendment 1 (1 of 2): the summary holds no 0.0, so the absolute part is checked on its float nearest zero.
The tolerance: each float within 1e-9 relative plus 1e-12 absolute; every other value, key and length equal.
Written before the fix, to fail on the tests as F15 left them, and to pass once it is fixed.
"""
import copy, json, os, re, unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SUMMARY = os.path.join(ROOT, 'runs', 'H3_SUMMARY_2026-09-27.json')
# the committed values, and the runners' own for them, as the CI's logs printed them (run 37007743140)
RUNNERS = {164.47257018636247: 164.47257018636245,      # the Linux jobs
           2.931631253339266: 2.9316312533392663,       # macOS and Windows
           -0.03349389813611967: -0.0334938981361196}   # macOS and Windows


def summary():
    return json.load(open(SUMMARY, encoding='utf-8'))


def floats(o):
    if isinstance(o, dict):
        for v in o.values():
            yield from floats(v)
    elif isinstance(o, list):
        for v in o:
            yield from floats(v)
    elif isinstance(o, float):
        yield o


def replace(o, f):
    """o with every float x replaced by f(x)."""
    if isinstance(o, dict):
        return {k: replace(v, f) for k, v in o.items()}
    if isinstance(o, list):
        return [replace(v, f) for v in o]
    return f(o) if isinstance(o, float) else o


def first(o, pred):
    """o with the first float that pred accepts replaced by pred's value, and that float."""
    seen = []

    def f(x):
        if not seen and pred(x) is not None:
            seen.append(x)
            return pred(x)
        return x
    return replace(o, f), (seen[0] if seen else None)


class F16_TheSummaryAcrossMachines(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_fix_f12 import summary_differences, REL, ABS
        cls.diff, cls.REL, cls.ABS = staticmethod(summary_differences), REL, ABS
        cls.want = summary()

    def test_the_tolerance_is_the_one_measured_for(self):
        self.assertEqual((self.REL, self.ABS), (1e-9, 1e-12))

    def test_the_committed_summary_matches_itself(self):
        self.assertEqual(self.diff(copy.deepcopy(self.want), self.want), [])

    def test_the_runners_own_numbers_pass(self):
        n = sum(1 for x in floats(self.want) if x in RUNNERS)
        self.assertGreaterEqual(n, 3)
        got = replace(self.want, lambda x: RUNNERS.get(x, x))
        self.assertNotEqual(got, self.want)               # the exact comparison fails on them, as on the runners
        self.assertEqual(self.diff(got, self.want), [])

    def test_a_float_moved_beyond_the_tolerance_fails(self):
        for k in (2.0, 10.0, 1e3):
            with self.subTest(times_the_tolerance=k):
                got, x = first(self.want, lambda v: v + k * (self.REL * abs(v) + self.ABS) if abs(v) > 1 else None)
                self.assertIsNotNone(x)
                self.assertEqual(len(self.diff(got, self.want)), 1)

    def test_a_float_moved_within_the_tolerance_passes(self):
        got, x = first(self.want, lambda v: v + 0.5 * (self.REL * abs(v) + self.ABS) if abs(v) > 1 else None)
        self.assertIsNotNone(x)
        self.assertEqual(self.diff(got, self.want), [])

    def test_the_float_nearest_zero_is_held_by_the_absolute_part(self):
        # amendment 1: the summary holds no 0.0; its float nearest zero (about 1.9e-4) is where the absolute part rules
        z = min(floats(self.want), key=abs)
        self.assertLess(self.REL * abs(z), self.ABS)
        for move, n in ((1e-11, 1), (5e-13, 0)):
            with self.subTest(move=move):
                got = replace(self.want, lambda v: v + move if v == z else v)
                self.assertEqual(len(self.diff(got, self.want)), n * sum(1 for v in floats(self.want) if v == z))

    def test_any_other_change_fails(self):
        cases = {'a string': lambda o: _first_leaf(o, str, lambda v: v + 'x'),
                 'an integer': lambda o: _first_leaf(o, int, lambda v: v + 1),
                 'a key removed': lambda o: _first_leaf(o, (str, int, float), None),
                 'a NaN': lambda o: first(o, lambda v: float('nan'))[0]}
        for name, mutate in cases.items():
            with self.subTest(name):
                got = mutate(copy.deepcopy(self.want))
                self.assertNotEqual(got, self.want)
                self.assertNotEqual(self.diff(got, self.want), [])

    def test_f12_5_compares_through_the_tolerance(self):
        src = open(os.path.join(HERE, 'test_fix_f12.py'), encoding='utf-8').read()
        body = src[src.index('class F12_5_'):src.index('class F12_6_')]
        self.assertIn('summary_differences(got, want)', body)
        self.assertNotIn('self.assertEqual(got, want)', body)


def _first_leaf(o, kind, f):
    """o with its first leaf of this kind (not a bool) changed by f, or its key removed when f is None."""
    def walk(x):
        items = list(x.items()) if isinstance(x, dict) else list(enumerate(x)) if isinstance(x, list) else []
        for k, v in items:
            if isinstance(v, kind) and not isinstance(v, bool):
                if f is None:
                    del x[k]
                else:
                    x[k] = f(v)
                return True
            if walk(v):
                return True
        return False
    assert walk(o)
    return o


class F16_WhereBitForBitHolds(unittest.TestCase):
    def test_runs_readme_says_where_it_holds(self):
        t = ' '.join(open(os.path.join(ROOT, 'runs', 'README.md'), encoding='utf-8').read().split())
        # F17: his words (the summary was written in the study's room, not on this machine)
        self.assertIn('Bit for bit holds where numpy takes the same arithmetic paths as the machine that wrote these records; '
                      "elsewhere, a float's last digits can differ.", t)


if __name__ == '__main__':
    unittest.main()
