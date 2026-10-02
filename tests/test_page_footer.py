"""The page's credit line in a footer at its end (29 Sept 2026, the calibrator's tenth room), his word: [his words, not quoted in public] The credit moves from the page's top line to a footer after everything else it shows; the version stays at the
top. Written to fail on the page as the tenth room found it (90bfffc) and to pass once the footer is in; every case is a
subTest, and the cases marked "control" pass before and after. The credit on every face (K1) and one version everywhere
(K2) stay in test_release_package.py.
"""
import html, os, re, unittest

from domino_calibrator import __version__

HERE = os.path.dirname(os.path.abspath(__file__))
PAGE = os.path.join(os.path.dirname(HERE), 'page', 'index.html')
CREDIT = "A Castle product from Domino Observatory. Built by Annie, the Castle's AI."


def visible(fragment):
    h = re.sub(r'<(script|style)\b.*?</\1>', ' ', fragment, flags=re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', h))).strip()


class TestCreditFooter(unittest.TestCase):
    def test_the_credit_sits_in_a_footer_at_the_end_of_the_page(self):
        with open(PAGE, encoding='utf-8') as f:
            page = f.read()
        body = page[page.index('<body'):page.index('</body>')]
        top = body[:body.index('<h2')]                        # the page's head: its title and the lines under it
        with self.subTest('control: the credit is on the page, once'):
            self.assertEqual(visible(body).count(CREDIT), 1)
        with self.subTest('control: the version stays at the top'):
            self.assertIn('domino-calibrator %s' % __version__, visible(top))
        with self.subTest('the credit is in a footer'):
            m = re.search(r'<footer\b[^>]*>(.*?)</footer>', body, flags=re.S)
            self.assertIsNotNone(m, 'no <footer> on the page')
            self.assertIn(CREDIT, visible(m.group(1)))
        with self.subTest('the footer is last: only scripts follow it'):
            m = re.search(r'</footer>', body)
            self.assertIsNotNone(m, 'no <footer> on the page')
            rest = re.sub(r'<script\b.*?</script>', ' ', body[m.end():], flags=re.S)
            self.assertEqual(rest.strip(), '', 'the page shows something after its footer')
        with self.subTest('the top no longer carries it'):
            self.assertNotIn(CREDIT, visible(top))


if __name__ == '__main__':
    unittest.main()
