"""The suite as the CI runs it (the launch list's step 2; the issue list's entry 6: "nothing skipped" was a step's name, not
a check). The same discovery as the README's `-s tests -t .`, run from the checkout's root whatever it is called, and it
fails on any skip the job does not name. A test that needs what a machine lacks skips and says why (the frames, Node and Playwright, the
MPC's validator, the network, an Ubuntu system Python); the CI's jobs have every tool, so there a skip is a finding. Windows
and macOS name K8 and K10's Debian records, which are Linux's by design.

    python -m tests.strict [--may-skip TEXT ...] [-s START] [-t TOP]

A skip is allowed when its test's id holds one of the TEXTs. Every skip is printed, allowed or not. Exit 0 only when every
test ran green and every skip is allowed. Written 29 Sept 2026 (the calibrator's thirteenth room); run from the checkout's
root since the import rename (30 Sept 2026, the launch list's step 3).
"""
import sys, argparse, unittest


def main(argv=None):
    ap = argparse.ArgumentParser(prog='python -m tests.strict',
                                 description='The suite, failing on any skip this job does not name.')
    ap.add_argument('--may-skip', action='append', default=[], metavar='TEXT',
                    help='a skip is allowed when its test id holds TEXT (may be given more than once)')
    ap.add_argument('-s', '--start', default='tests', help='where discovery starts (default: tests)')
    ap.add_argument('-t', '--top', default='.', help="the top-level folder, the checkout's root (default: .)")
    a = ap.parse_args(argv)
    suite = unittest.defaultTestLoader.discover(a.start, top_level_dir=a.top)
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    allowed, not_allowed = [], []
    for test, why in result.skipped:
        (allowed if any(t in test.id() for t in a.may_skip) else not_allowed).append((test.id(), why))
    err = sys.stderr
    print('', file=err)
    for label, items in (('skipped, allowed on this job', allowed), ('skipped, NOT allowed', not_allowed)):
        for tid, why in items:
            print('%s: %s: %s' % (label, tid, why), file=err)
    ok = result.wasSuccessful() and not not_allowed
    print('strict: %s (%d run, %d failures, %d errors, %d skipped: %d allowed, %d not)' % (
        'PASS' if ok else 'FAIL', result.testsRun, len(result.failures), len(result.errors), len(result.skipped),
        len(allowed), len(not_allowed)), file=err)
    return 0 if ok else 1


if __name__ == '__main__':
    sys.exit(main())
