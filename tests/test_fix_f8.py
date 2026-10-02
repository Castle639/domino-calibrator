"""The fix room's F8: R1.1's family, from the second audit room's wave 1 (F6.1 and F6.2; 1 Oct 2026, his word for the night,
the fix room's record of 1 Oct 2026, not in this repository, section 21). Written before the fix, to fail on the command line as F7 left
it, and to pass once it is fixed. His rule: the command line never writes a record from a sky solution that differs from
what the header says.

1  A WCS number in a form astropy cannot carry (1E400, a comma decimal), refused at the sky in the page's words, its
   value as written; F7 covered NAN.
2  A D exponent, which FITS allows (1.50123D+02): astropy's header reads 150.123 and its WCS 1.50123. The command line now
   reads it as the header says, as the page does: the same record as the file written with an E exponent.
3  The backstop: a WCS that disagrees with any WCS number of its header gives no sky position, whatever the cause.
"""
import os, sys, subprocess, unittest, warnings

from astropy.io import fits
from astropy.wcs import WCS

from domino_calibrator import ades as A
from tests.test_hardening import REC_ARGS, Tmp, comet, write, given

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
SIP = dict(CTYPE1='RA---TAN-SIP', CTYPE2='DEC--TAN-SIP', A_ORDER=2, A_2_0=2.0e-6, A_1_1=0.0, A_0_2=0.0, B_ORDER=2, B_2_0=0.0,
           B_1_1=0.0, B_0_2=0.0)


def cli_run(args):
    r = subprocess.run([sys.executable, '-m', 'domino_calibrator.cli'] + args, cwd=ROOT, capture_output=True, encoding='utf-8',
                       errors='replace', timeout=600, env=dict(os.environ, PYTHONUTF8='1'))
    return r.returncode, r.stdout + r.stderr


def written(path, key, text, dst):
    """The file at path with the card `key` rewritten, unquoted, as `text`, saved as dst."""
    b = bytearray(open(path, 'rb').read())
    i = b.find(('%-8s= ' % key).encode('ascii'))
    assert i >= 0 and i % 80 == 0, key
    b[i:i + 80] = ('%-8s= %20s' % (key, text)).ljust(80).encode('ascii')
    open(dst, 'wb').write(bytes(b))
    return dst


def lines(out):
    """The lines a record rests on: the sky position and the record's own line."""
    return [l for l in out.splitlines() if l.startswith('# sky (ICRS)') or l.startswith('3I ')]


class F8_1_OtherFormsANumberCannotTake(Tmp):
    def test_1e400_and_comma_decimals_refused_in_the_pages_words(self):
        img, _ = comet()
        base = write(os.path.join(self.d, 'base.fits'), img)
        for key, text in (('CD1_1', '1E400'), ('CRPIX1', '36,0'), ('CD1_1', '-2,7777777777778E-04')):
            with self.subTest(key=key, text=text):
                p = written(base, key, text, os.path.join(self.d, 'bad.fits'))
                rc, out = cli_run([p] + REC_ARGS)
                self.assertEqual(rc, 2, out[-400:])
                self.assertNotIn('# version=2022', out)
                self.assertIn("needs a sky position (the WCS card %s = '%s' is not a number)" % (key, text), out)


class F8_2_TheDExponent(Tmp):
    def test_a_d_exponent_gives_the_record_the_e_exponent_gives(self):
        img, _ = comet()
        for name, cards, key in (('tan', {}, 'CRVAL1'), ('tan', {}, 'CRPIX1'), ('tan', {}, 'CD1_1'), ('tan', {}, 'CD2_2'),
                                 ('sip', SIP, 'A_2_0')):
            with self.subTest(name, key=key):
                base = write(os.path.join(self.d, name + '.fits'), img, **cards)
                v = fits.getheader(base)[key]
                e = written(base, key, '%.15E' % v, os.path.join(self.d, 'e.fits'))
                d = written(base, key, ('%.15E' % v).replace('E', 'D'), os.path.join(self.d, 'd.fits'))
                rc_e, out_e = cli_run([e] + given(e) + REC_ARGS)
                rc_d, out_d = cli_run([d] + given(e) + REC_ARGS)
                self.assertEqual((rc_e, rc_d), (0, 0), out_d[-400:])
                self.assertEqual(len(lines(out_e)), 2, out_e[-400:])
                self.assertEqual(lines(out_d), lines(out_e))


class F8_3_TheBackstop(unittest.TestCase):
    def header(self, crval1_text):
        h = fits.Header()
        for k, v in (('NAXIS', 2), ('NAXIS1', 71), ('NAXIS2', 71), ('CTYPE1', 'RA---TAN'), ('CTYPE2', 'DEC--TAN'),
                     ('CRPIX1', 36.0), ('CRPIX2', 36.0), ('CRVAL1', 150.123), ('CRVAL2', 20.4559), ('CD1_1', -0.78 / 3600),
                     ('CD1_2', 0.0), ('CD2_1', 0.0), ('CD2_2', 0.78 / 3600), ('RADESYS', 'ICRS')):
            h[k] = v
        s = h.tostring()
        i = s.find('CRVAL1  = ')
        return fits.Header.fromstring(s[:i] + ('%-8s= %20s' % ('CRVAL1', crval1_text)).ljust(80) + s[i + 80:])

    def test_a_wcs_that_differs_from_its_header_gives_no_sky_position(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            h = self.header('1.501230000000000D+02')
            w = WCS(h).celestial                                  # read from the card's text: CRVAL1 1.50123
            self.assertAlmostEqual(float(w.wcs.crval[0]), 1.50123)
            with self.assertRaises(ValueError) as e:
                A.wcs_check(h, w, [], 36.0, 36.0)
            self.assertIn('CRVAL1', str(e.exception))
            h = self.header('1.501230000000000E+02')              # the control: the same WCS written plainly
            A.wcs_check(h, WCS(h).celestial, [], 36.0, 36.0)


if __name__ == '__main__':
    unittest.main()
