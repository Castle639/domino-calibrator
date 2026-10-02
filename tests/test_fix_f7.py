"""The fix room's F7: R1.1 from the second audit room's regression check (1 Oct 2026; the fix room's record of 1 Oct 2026, not in this repository,
section 20). Written before the fix, to fail on the command line as the third seal left it (004726d), and to pass once it is
fixed. A WCS card whose value cannot be read at all (A_2_0 = NAN, unquoted, which astropy cannot carry) was left out of the
header, and the WCS read without it: a SIP term silently dropped, a record 1.77" off in the audit room's confirmation, while the
page refuses the same file. His answer: the command line refuses the sky position too, in the page's words; a card that is
not a WCS number is still left out with a note, as before.
"""
import os, re, sys, subprocess, unittest

from tests.test_hardening import REC_ARGS, Tmp, comet, write, given

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SIP = dict(CTYPE1='RA---TAN-SIP', CTYPE2='DEC--TAN-SIP', A_ORDER=2, A_2_0=2.0e-6, A_1_1=0.0, A_0_2=0.0, B_ORDER=2, B_2_0=0.0,
           B_1_1=0.0, B_0_2=0.0, FOCUSPOS=1.5)


def cli_run(args):
    r = subprocess.run([sys.executable, '-m', 'domino_calibrator.cli'] + args, cwd=ROOT, capture_output=True, encoding='utf-8',
                       errors='replace', timeout=600, env=dict(os.environ, PYTHONUTF8='1'))
    return r.returncode, r.stdout + r.stderr


def unreadable(path, key):
    """The card `key` rewritten in place as `key = NAN`, unquoted: a value astropy cannot read."""
    b = bytearray(open(path, 'rb').read())
    i = b.find(('%-8s= ' % key).encode('ascii'))
    assert i >= 0 and i % 80 == 0, key
    b[i:i + 80] = ('%-8s= %20s' % (key, 'NAN')).ljust(80).encode('ascii')
    open(path, 'wb').write(bytes(b))
    return path


class F7_R1_1_AWcsCardThatCannotBeRead(Tmp):
    def frame(self, name, key=None):
        img, _ = comet()
        p = write(os.path.join(self.d, name), img, **SIP)
        return unreadable(p, key) if key else p

    def test_the_controls_a_readable_sip_and_a_card_outside_the_wcs(self):
        p = self.frame('ok.fits'); rc, out = cli_run([p] + given(p) + REC_ARGS)
        self.assertEqual(rc, 0, out[-400:]); self.assertIn('# version=2022', out)
        p = self.frame('focus.fits', 'FOCUSPOS'); rc, out = cli_run([p] + given(p) + REC_ARGS)     # not a WCS card: left out with a note, as before
        self.assertEqual(rc, 0, out[-400:]); self.assertIn('# version=2022', out)
        self.assertIn('header card FOCUSPOS could not be read, and was left out', out)

    def test_a_wcs_number_that_cannot_be_read_gives_no_sky_position_in_the_pages_words(self):
        for key in ('A_2_0', 'CRPIX1', 'CD1_1', 'B_ORDER'):
            with self.subTest(key):
                rc, out = cli_run([self.frame('nan_%s.fits' % key, key)] + REC_ARGS)
                self.assertEqual(rc, 2, out[-400:])
                self.assertNotIn('# version=2022', out)
                self.assertNotRegex(out, r'# sky \(ICRS\)')
                self.assertIn("needs a sky position (the WCS card %s = 'NAN' is not a number)" % key, out)
                self.assertIn('header card %s could not be read, and was left out' % key, out)


if __name__ == '__main__':
    unittest.main()
