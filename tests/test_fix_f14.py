"""The fix room's F14: his four answers of 2 Oct 2026, morning (the fix room's record of 1 Oct 2026, not in this repository, section 30).
Written before the fix, to fail on the tool as F13 left it, and to pass once it is fixed.
1  "Isolated" stays out of the words, since nothing checks it for a start the observer gives; one plain sentence instead,
   on every face that gives the rule: a star inside the measuring ring pulls the answer toward it.
2  Item 8's form, as F11b built it (no change here).
3  An unparsable CTYPE1: the page refuses the sky too, in the command line's words; the pixel answer stands on both faces.
   The page leaves out a card whose string is followed by text that is not a comment, as astropy cannot read it.
4  One credit everywhere, as the README has it: the package's and the page's own headers say it (the tools and the
   records, which the Castle keeps as written, are curated in the public copy, and checked there).
"""
import contextlib, io, os, re, sys, subprocess, unittest

from domino_calibrator import cli
from tests import test_release_words as W
from tests.test_hardening import REC_ARGS, Tmp, comet, write
from tests.test_hardening_page import js
from tests.test_fix_f3 import readme, page_visible, flat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STAR = 'A star inside the measuring ring pulls the answer toward it.'
CREDIT = "A Castle product from Domino Observatory. Built by Annie, the Castle's AI."
UNKNOWN = 'the WCS card CTYPE1 could not be read, so the WCS is unknown: fix the card, or plate-solve the image again'


def helptext():
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        try:
            cli.main(['--help'])
        except SystemExit:
            pass
    return ' '.join(buf.getvalue().split())


def junk_ctype1(path, tail):
    b = bytearray(open(path, 'rb').read())
    i = b.find(b'CTYPE1  = ')
    b[i:i + 80] = ("CTYPE1  = 'RA---TAN'" + tail).ljust(80).encode('ascii')
    open(path, 'wb').write(bytes(b))
    return path


def engine(path):
    return js("""
const fs = require('fs');
const hdus = Z.parseFITS(new Uint8Array(fs.readFileSync(D.p)).buffer), cur = hdus.find((u) => u.readable);
const o = Z.shrink(cur.data, cur.nx, cur.ny, 35, 35, { estimator: 'G', radii: Z.publishedRadii(), background: 'annulus' });
const r = Z.decide({ cur: cur, hdus: hdus, o: o, start: [35, 35], auto: false });
out = { need: r.need, rd: r.rd, x0: o.x0, dropped: cur.dropped };""", {'p': path})


class F14_1_TheStarSentence(unittest.TestCase):
    def test_every_face_that_gives_the_rule_says_it(self):
        for face, t in (('README.md', flat(readme())), ('the page', page_visible()), ('--help', helptext())):
            with self.subTest(face):
                self.assertIn(STAR, t)
                self.assertNotRegex(t, r'\bisolated\b')


class F14_3_AnUnparsableCtype1OnThePage(Tmp):
    def test_both_faces_refuse_the_sky_in_the_same_words_and_keep_the_pixel_answer(self):
        img, _ = comet()
        p = junk_ctype1(write(self.p('c.fits'), img), '  x')
        r = subprocess.run([sys.executable, '-m', 'domino_calibrator.cli', p, '--x', '35', '--y', '35'] + REC_ARGS, cwd=ROOT,
                           capture_output=True, encoding='utf-8', errors='replace', timeout=600)
        self.assertEqual(r.returncode, 2, r.stdout[-300:])
        self.assertIn('needs a sky position (%s)' % UNKNOWN, r.stdout)
        self.assertRegex(r.stdout, r'# zero aperture: x \S+ y \S+')
        pg = engine(p)
        self.assertIn('CTYPE1', pg['dropped'])
        self.assertIsNone(pg['rd'])
        self.assertIn('a sky position (%s)' % UNKNOWN, pg['need'])
        self.assertTrue(isinstance(pg['x0'], (int, float)) and pg['x0'] == pg['x0'], pg['x0'])

    def test_control_a_string_with_a_comment_after_it_is_read(self):
        img, _ = comet()
        p = junk_ctype1(write(self.p('ok.fits'), img), '  / the projection')
        pg = engine(p)
        self.assertNotIn('CTYPE1', pg['dropped'])
        self.assertIsNotNone(pg['rd'], pg['need'])


class F14_4_OneCredit(unittest.TestCase):
    def test_the_package_and_the_page_headers_give_the_readmes_credit(self):
        import domino_calibrator
        self.assertIn(CREDIT, ' '.join(domino_calibrator.__doc__.split()))
        head = W.read(os.path.join(ROOT, 'page', 'zeroap.js')).split('*/')[0]
        self.assertIn(CREDIT, ' '.join(head.split()))
        for face, t in (('README.md', flat(readme())), ('the page', page_visible())):
            with self.subTest(face):
                self.assertIn(CREDIT, t)


if __name__ == '__main__':
    unittest.main()
