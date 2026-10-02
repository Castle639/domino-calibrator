"""The page's design, his picks (29 Sept 2026, the calibrator's eleventh room; the design room's record of 29 Sept 2026, not in this repository).
Four web scouts brought options, checked at source; his picks (16:07 UTC): the tool first with a short box before it; Inter
beside the page, the record in the system's monospace; today's colours, refined; the logo C, the tile. His amendment (16:28
UTC), after seeing the build: no box ([his words, not quoted in public]), so D1 asks for the tool first with nothing before it
but the one-line purpose, and D5's link case, whose only link was in the box, asks that any link the page has pass. His
second (16:30 UTC): [his words, not quoted in public], so D6 asks for the page dark whatever
the system asks, with no switch (the favicon and the README's logos still follow the browser's and GitHub's own themes). The README's credit
moves to a closing section, the designers' call (his word in the tenth room: [his words, not quoted in public]).
Written to fail on the page as the eleventh room found it (2949721) and to pass once the design is built; every case is a
subTest, and the cases marked "control" pass before and after. The words keep the words test's grammar
(test_release_words.py).
- D0 controls: every id the page's script and the tests use is on the page once; the words test's face is whole (its
  literal heading, the study paragraph and the footer after it); every address the page uses is relative (no network).
- D1 the structure: the tile, the title and the version, then the tool's first part, with no box between (his amendment).
- D2 the record's twelve fields in three labelled groups: the observation, the people, the telescope.
- D3 hints beside the boxes where the format matters; status lines announced; text alternatives for the image and plot.
- D4 Inter 4.1's own Regular and SemiBold, unchanged (the OFL FAQ 2.2), with its licence, beside the page.
- D5 in a browser, light and dark, desktop and phone: text (and any link) 4.5:1, borders and the plot's zero line 3:1 (WCAG 2.2,
  1.4.3 and 1.4.11); every control at least 24 by 24 px (2.5.8) and named (1.3.1, 4.1.2); a visible focus (2.4.7).
- D6 dark whatever the system asks, with no switch; the plot in the page's colours (his amendment).
- D7 the tile on the page, the favicon (its dark mode inside), and the README's two logos.
- D8 the README: the logo on top in light and dark; the credit in a closing section, with the fonts' licence named.
- D9 the layout: at desktop the image beside the method and the plot beside the table; at phone width one column and no
  sideways scroll (1.4.10).
- D10 (his pick, 16:37 UTC: [his words, not quoted in public]): the method and the findings in two folded sections under "What it
  does", closed until opened, each with a one-line title; no star on the page, the plain words in its place (the words test's
  W5 amended to match; the README keeps its stars).
"""
import hashlib, html, json, os, re, shutil, tempfile, unittest, warnings, subprocess
import numpy as np

from domino_calibrator import synth
from tests.test_hardening_page import fits_bytes, PAGE, NODE, PW
from tests.test_hardening_2_page import TAN
from tests.test_hardening_3_page import REC3

PKG = os.path.dirname(PAGE)
HTML = os.path.join(PAGE, 'index.html')
README = os.path.join(PKG, 'README.md')
CREDIT = "A Castle product from Domino Observatory. Built by Annie, the Castle's AI."
# the ids the page's script reads (index.html at 2949721), with #about and #study, which the tests read
IDS = ('file hdu info hdrnote img sx sy est r0 r1 rs bgm bgv stn desig mode astcat submitter measurers observers design '
       'aperture detector obsname tobs cats run status plot tab zero ades adesnote copy copynote about study').split()
GROUPS = (('stn', 'desig', 'mode', 'astcat', 'tobs'), ('submitter', 'measurers', 'observers'), ('design', 'aperture', 'detector', 'obsname'))
HINTED = ('stn', 'desig', 'astcat', 'measurers', 'observers', 'tobs')
# Inter 4.1's own files (rsms/inter, tag v4.1, docs/font-files/; the same bytes from jsDelivr and from GitHub, 16:11 UTC)
INTER = {'Inter-Regular.woff2': 'e06f6b1bc553aaea4e4668023ed0ab0a147129c3107f511bc7d03d361b0ae085',
         'Inter-SemiBold.woff2': '5cb7103e4e605989afebc03d989c79201e54b21b5183db33981f70db9178a301'}
OFL = '262481e844521b326f5ecd053e59b98c8b2da78c8ee1bdbb6e8174305e54935a'    # its LICENSE.txt, at the same tag
VERDICT = re.compile(r'\b(?:helps?|fails?|further off|tailward|sunward|measured in|truth|closer|WORKS|HELPS|FAILS)\b', re.I)


def read(p):
    with open(p, encoding='utf-8') as f:
        return f.read()


def sha(p):
    with open(p, 'rb') as f:
        return hashlib.sha256(f.read()).hexdigest()


def visible(h):
    h = re.sub(r'<(script|style)\b.*?</\1>', ' ', h, flags=re.S)
    return re.sub(r'\s+', ' ', html.unescape(re.sub(r'<[^>]+>', ' ', h))).strip()


def tag_of(page, id_):
    m = re.search(r'<[a-z0-9]+\b[^>]*\bid="%s"[^>]*>' % re.escape(id_), page)
    return m.group(0) if m else ''


def inner_text(page, id_):
    """The visible text of the element with this id ('' if there is none)."""
    m = re.search(r'<([a-z0-9]+)\b[^>]*\bid="%s"[^>]*>(.*?)</\1>' % re.escape(id_), page, flags=re.S)
    return visible(m.group(2)) if m else ''


def rgb(c):
    """A CSS colour as computed (rgb(...), rgba(...)) or a hex token, as (r, g, b, a)."""
    c = (c or '').strip()
    m = re.match(r'rgba?\(([^)]*)\)', c)
    if m:
        v = [float(x) for x in re.split(r'[,\s/]+', m.group(1).strip()) if x]
        return (v[0], v[1], v[2], v[3] if len(v) > 3 else 1.0)
    m = re.match(r'#([0-9a-f]{6})$', c, re.I)
    if m:
        h = m.group(1)
        return (int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16), 1.0)
    return None


def lum(c):
    v = [x / 255 for x in c[:3]]
    v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
    return 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]


def contrast(a, b):
    """WCAG 2.x contrast of two colours; a transparent one is read as the other's background (None if either is unknown)."""
    a, b = rgb(a), rgb(b)
    if a is None or b is None:
        return None
    la, lb = sorted((lum(a), lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


class TestTheDesignOnDisk(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.page = read(HTML)
        cls.body = cls.page[cls.page.index('<body'):cls.page.index('</body>')]

    def test_d0_controls(self):
        for i in IDS:
            with self.subTest('control: the id is on the page once', id=i):
                self.assertEqual(len(re.findall(r'\bid="%s"' % re.escape(i), self.page)), 1)
        with self.subTest("control: the words test's face is whole"):
            self.assertEqual(self.page.count('<h2>What it does</h2>'), 1)
            m = re.search(r'<h2>What it does</h2>(.*?)(?=<h2|<script|</body>)', self.page, flags=re.S)
            self.assertIn('id="study"', m.group(1)); self.assertIn('<footer', m.group(1))
        # the launch list's step 4 (30 Sept 2026, the build room): the design record's constraint is that the page makes no
        # network request; a link makes none until someone follows it, and the page's two README mentions link to the
        # repository's README (test_launch_steps K16 keeps its links to that one address). So this control reads what the
        # page loads: src, srcset, url() and <link href>
        with self.subTest('control: every address the page loads is relative (no network request)'):
            refs = re.findall(r'\b(?:src|srcset)="([^"]*)"', self.page) + re.findall(r'<link\b[^>]*\bhref="([^"]*)"', self.page) \
                + re.findall(r'url\(\s*[\'"]?([^\'")]+)', self.page)
            self.assertEqual([r for r in refs if '://' in r or r.startswith('//')], [])
            self.assertNotIn('@import', self.page)

    def test_d1_the_tool_first_with_no_box(self):
        # his amendment (16:28 UTC): the box before the tool is gone; the page opens on its head, a one-line purpose and the tool
        pos = {k: self.body.find(s) for k, s in (('the tile', 'id="logo"'), ('the title', '<h1'), ('the version', 'id="about"'),
                                                 ("the tool's first part", '<h2>1. '))}
        with self.subTest('each is on the page', missing=[k for k, v in pos.items() if v < 0]):
            self.assertTrue(all(v >= 0 for v in pos.values()))
        with self.subTest('in that order'):
            self.assertEqual(sorted(pos, key=pos.get), list(pos))
        with self.subTest("no box: the page's first heading after its title is the tool's first part"):
            self.assertEqual(self.body.find('<h2'), self.body.find('<h2>1. '))
            self.assertNotIn('<aside', self.body[:max(self.body.find('<h2>1. '), 0)])
            self.assertNotIn('id="trust"', self.page)

    def test_d2_the_record_in_three_labelled_groups(self):
        sets = re.findall(r'<fieldset\b[^>]*>(.*?)</fieldset>', self.body, flags=re.S)
        with self.subTest('three groups, each with its legend'):
            self.assertEqual(len(sets), 3)
            for s in sets:
                self.assertTrue(re.search(r'<legend\b[^>]*>\s*\S', s))
        for want in GROUPS:
            with self.subTest('one group holds these, and nothing else of the record', fields=want):
                hit = [s for s in sets if all('id="%s"' % i in s for i in want)]
                self.assertEqual(len(hit), 1)
                others = [i for g in GROUPS if g is not want for i in g]
                self.assertFalse(any('id="%s"' % i in hit[0] for i in others))

    def test_d3_hints_status_lines_and_text_alternatives(self):
        for i in HINTED:
            with self.subTest('a hint beside the box', id=i):
                m = re.search(r'aria-describedby="([^"]+)"', tag_of(self.page, i))
                self.assertIsNotNone(m)
                self.assertTrue(inner_text(self.page, m.group(1)) if m else False)
        with self.subTest("control: the names' box still says how names are separated (round 2, 1.14)"):
            ph = re.search(r'id="measurers"[^>]*placeholder="([^"]*)"', self.page)
            self.assertIsNotNone(ph); self.assertIn(';', ph.group(1))
        for i in ('status', 'copynote', 'info'):
            with self.subTest('a status line announced (WCAG 4.1.3)', id=i):
                self.assertIn('role="status"', tag_of(self.page, i))
        for i in ('img', 'plot'):
            with self.subTest('a text alternative (WCAG 1.1.1)', id=i):
                t = tag_of(self.page, i)
                self.assertIn('role="img"', t); self.assertRegex(t, r'aria-label="[^"]{12,}"')

    def test_d4_inter_beside_the_page_unchanged_with_its_licence(self):
        for f, h in INTER.items():
            p = os.path.join(PAGE, 'fonts', f)
            with self.subTest("Inter 4.1's own file", file=f):
                self.assertTrue(os.path.exists(p)); self.assertEqual(sha(p), h)
        with self.subTest('its licence beside it (the OFL FAQ 1.10, 1.11)'):
            p = os.path.join(PAGE, 'fonts', 'OFL.txt')
            self.assertTrue(os.path.exists(p)); self.assertEqual(sha(p), OFL)
        faces = re.findall(r'@font-face\s*\{([^}]*)\}', self.page)
        for f, w in (('Inter-Regular.woff2', '400'), ('Inter-SemiBold.woff2', '600')):
            with self.subTest('declared, relative', file=f):
                hit = [x for x in faces if re.search(r"font-family:\s*['\"]?Inter['\"]?\s*;", x) and ("url('fonts/%s')" % f in x or 'url("fonts/%s")' % f in x)]
                self.assertEqual(len(hit), 1); self.assertRegex(hit[0], r'font-weight:\s*%s\b' % w)

    def test_d7_the_tile_the_favicon_and_the_readmes_logos(self):
        with self.subTest('the tile on the page, named, without the credit'):
            t = tag_of(self.page, 'logo')
            self.assertTrue(t.startswith('<svg')); self.assertIn('role="img"', t); self.assertIn('aria-label="domino-calibrator"', t)
            m = re.search(r'<svg\b[^>]*\bid="logo".*?</svg>', self.page, flags=re.S)
            self.assertNotIn(CREDIT, visible(m.group(0)) if m else CREDIT)
        with self.subTest('the favicon, relative, its dark mode inside'):
            self.assertRegex(self.page, r'<link rel="icon" href="favicon\.svg" type="image/svg\+xml">')
            p = os.path.join(PAGE, 'favicon.svg')
            self.assertTrue(os.path.exists(p)); self.assertIn('prefers-color-scheme: dark', read(p))
        for f in ('logo.svg', 'logo-dark.svg'):
            with self.subTest("the README's logo", file=f):
                p = os.path.join(PAGE, f)
                self.assertTrue(os.path.exists(p)); self.assertTrue(read(p).lstrip().startswith('<svg'))

    def test_d8_the_readme_logo_on_top_credit_in_a_closing_section(self):
        r = read(README)
        lines = r.split('\n')
        # the fix room's F4 (item 33): at absolute URLs into the repository, since PyPI resolves no relative path
        raw = 'https://raw.githubusercontent.com/Castle639/domino-calibrator/main/'
        with self.subTest('it opens with the logo, light and dark (GitHub: a picture element)'):
            head = r[:r.index('\n# ')] if '\n# ' in r else ''
            self.assertTrue(r.startswith('<picture>'))
            self.assertIn('<source media="(prefers-color-scheme: dark)" srcset="%spage/logo-dark.svg">' % raw, head)
            self.assertRegex(head, r'<img alt="domino-calibrator" src="%spage/logo\.svg">' % re.escape(raw))
        heads = [k for k, ln in enumerate(lines) if ln.startswith('## ')]
        with self.subTest('its last section is "Who made it", and the credit is there, once'):
            self.assertTrue(heads and lines[heads[-1]] == '## Who made it')
            self.assertEqual(r.count(CREDIT), 1)
            self.assertIn(CREDIT, '\n'.join(lines[heads[-1]:]) if heads else '')
        with self.subTest("the fonts' licence named there"):
            self.assertIn('`page/fonts/OFL.txt`', '\n'.join(lines[heads[-1]:]) if heads else '')

    def test_d10_the_method_and_the_findings_folded_in_plain_words(self):
        m = re.search(r'<h2>What it does</h2>(.*?)(?=<h2|<script|</body>)', self.page, flags=re.S)
        face = m.group(1) if m else ''
        folds = re.findall(r'<details\b([^>]*)>\s*<summary\b[^>]*>(.*?)</summary>(.*?)</details>', face, flags=re.S)
        # the fix room's F3 (item 23, his answer): a third fold between the two, the cutout recipe (#cutout)
        with self.subTest('three folded sections, closed until opened, each with a one-line title'):
            self.assertEqual(len(folds), 3)
            for attrs, title, _ in folds:
                self.assertNotIn('open', attrs); self.assertTrue(0 < len(visible(title)) <= 60, visible(title))
        with self.subTest('the method in the first, the cutout (#cutout) in the second, the findings (#study) in the third'):
            self.assertTrue(len(folds) == 3 and 'Photocentres in circular apertures' in folds[0][2] and 'id="cutout"' in folds[1][2]
                            and 'id="study"' in folds[2][2])
        with self.subTest('no star on the page, the plain words in its place'):
            self.assertNotIn('★', visible(self.page)); self.assertNotIn('&#9733;', self.page)
            self.assertRegex(visible(face), r'checked by us,? (?:and )?not yet by anyone outside')
        with self.subTest('the footer follows them, outside the folds'):
            self.assertRegex(face, r'</details>\s*<footer')


@unittest.skipIf(NODE is None or PW is None, 'no node or no playwright')
class TestTheDesignInABrowser(unittest.TestCase):
    """page/design_check.js: desktop 1280x900 and phone 390x844, light and dark, with a Measure on the suite's comet."""
    @classmethod
    def setUpClass(cls):
        warnings.simplefilter('ignore')
        cls.d = tempfile.mkdtemp()
        img, _ = synth.render(71, 35.25, 34.85, flux_n=3e4, k=400.0, a=0.3, model='dipole', psf=('gauss', 2.5), sub=10)
        img = synth.add_noise(img, 150.0, 5.0, np.random.default_rng(5)).astype(np.float32)
        good = fits_bytes(os.path.join(cls.d, 'good.fits'), img, **dict(TAN, **{'DATE-OBS': '2025-12-27T16:04:29.000', 'EXPTIME': 120.0}))
        cp = os.path.join(cls.d, 'cfg.json')
        with open(cp, 'w', encoding='utf-8') as f:
            json.dump(dict(file=good, x=35, y=35, set=dict(REC3)), f)
        r = subprocess.run([NODE, os.path.join(PAGE, 'design_check.js'), cp], capture_output=True, text=True, encoding='utf-8', errors='replace', timeout=600,
                           env=dict(os.environ, PLAYWRIGHT_MODULE=PW))
        cls.err = r.stderr[-800:]
        try:
            cls.res = json.loads(r.stdout)['views']
        except ValueError:
            cls.res = {}

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def view(self, k):
        v = self.res.get(k) or {}
        self.assertFalse(v.get('error') or v.get('errors'), (k, v.get('error'), v.get('errors'), self.err))
        return v

    def test_d5_contrast_targets_names_focus_and_fonts(self):
        for k in ('desktop_light', 'desktop_dark', 'phone_light', 'phone_dark'):
            with self.subTest('control: it loads, measures and draws', view=k):
                v = self.view(k)
                self.assertEqual(v.get('status'), 'done'); self.assertGreater((v.get('plot') or {}).get('circles', 0), 0)
            v = self.res.get(k) or {}
            b = v.get('before') or {}
            bg = b.get('bg')
            for what, fg, need in (('text', b.get('fg'), 4.5), ('muted text', b.get('muted'), 4.5)):
                with self.subTest('%s against the page, at least %s:1 (1.4.3)' % (what, need), view=k):
                    c = contrast(fg, bg); self.assertIsNotNone(c, (fg, bg)); self.assertGreaterEqual(c, need)
            with self.subTest('any link against the page, at least 4.5:1 (1.4.3); his amendment: the only link was in the box', view=k):
                if b.get('link') is None:
                    self.assertNotIn('<a ', read(HTML))            # none to measure: the page has no link
                else:
                    c = contrast(b.get('link'), bg); self.assertIsNotNone(c); self.assertGreaterEqual(c, 4.5)
            with self.subTest("an input's text against its own box, at least 4.5:1 (1.4.3)", view=k):
                # amended before any fix (the red run's first reading): against the box's own background when it has one
                i = b.get('input') or {}
                back = i.get('bg') if (rgb(i.get('bg')) or (0, 0, 0, 0))[3] > 0 else bg
                c = contrast(i.get('color'), back); self.assertIsNotNone(c); self.assertGreaterEqual(c, 4.5)
            with self.subTest("Measure's label against its button, at least 4.5:1", view=k):
                run = b.get('run') or {}
                back = run.get('bg') if (rgb(run.get('bg')) or (0, 0, 0, 0))[3] > 0 else bg
                c = contrast(run.get('color'), back); self.assertIsNotNone(c); self.assertGreaterEqual(c, 4.5)
            with self.subTest("an input's border against the page, at least 3:1 (1.4.11)", view=k):
                c = contrast((b.get('input') or {}).get('border'), bg); self.assertIsNotNone(c); self.assertGreaterEqual(c, 3)
            with self.subTest("the plot's zero line against the page, at least 3:1 (1.4.11)", view=k):
                p = v.get('plot') or {}
                c = contrast(p.get('zero'), p.get('bg')); self.assertIsNotNone(c); self.assertGreaterEqual(c, 3)
            small = [(c['id'], round(c['box']['w'], 1), round(c['box']['h'], 1)) for c in b.get('controls', [])
                     if c['shown'] and (c['box']['w'] < 24 or c['box']['h'] < 24)]
            with self.subTest('every control at least 24 by 24 px (2.5.8)', view=k, small=small[:8]):
                self.assertTrue(b.get('controls')); self.assertEqual(small, [])
            unnamed = [c['id'] for c in b.get('controls', []) if c['shown'] and not c['named']]
            with self.subTest('every control named (1.3.1, 4.1.2)', view=k, unnamed=unnamed):
                self.assertEqual(unnamed, [])
            with self.subTest('the first Tab shows a focus outline of 2 px or more (2.4.7)', view=k, focus=v.get('focus')):
                f = v.get('focus') or {}
                self.assertNotEqual(f.get('outlineStyle'), 'none'); self.assertGreaterEqual(f.get('outlineWidth', 0), 2)
            with self.subTest('Inter for the text, the system monospace for the record', view=k, fonts=b.get('fonts')):
                fo = b.get('fonts') or {}
                self.assertRegex(fo.get('body', ''), r'^"?Inter"?\s*,'); self.assertRegex(fo.get('pre', ''), r'^ui-monospace\s*,')

    def test_d6_dark_whatever_the_system_asks(self):
        # his amendment (16:30 UTC): [his words, not quoted in public]
        page = read(HTML)
        with self.subTest('no theme switch and no second theme in the page'):
            self.assertNotIn('id="theme"', page); self.assertNotIn('data-theme', page); self.assertNotIn('prefers-color-scheme', page)
        for v in ('desktop', 'phone'):
            bl, bd = (self.view(v + '_light').get('before') or {}), (self.view(v + '_dark').get('before') or {})
            with self.subTest('the same colours when the system asks for light as for dark', view=v):
                self.assertEqual((bl.get('bg'), bl.get('fg'), bl.get('muted'), bl.get('tokens')),
                                 (bd.get('bg'), bd.get('fg'), bd.get('muted'), bd.get('tokens')))
            with self.subTest('and they are dark', view=v, bg=bl.get('bg')):
                self.assertLess(lum(rgb(bl.get('bg'))), 0.05); self.assertGreater(lum(rgb(bl.get('fg'))), 0.5)
        for k in ('desktop_light', 'desktop_dark', 'phone_light', 'phone_dark'):
            p = self.view(k).get('plot') or {}
            tk = p.get('tokens') or {}
            with self.subTest("the plot drawn in the page's colours: its points, its zero line and its words", view=k):
                self.assertEqual(rgb(p.get('point'))[:3], rgb(tk.get('accent'))[:3])
                self.assertEqual(rgb(p.get('zero'))[:3], rgb(tk.get('line'))[:3])
                self.assertEqual(rgb(p.get('text'))[:3], rgb(tk.get('fg'))[:3])

    def test_d9_the_layout_at_desktop_and_phone(self):
        for k in ('desktop_light', 'desktop_dark'):
            v = self.view(k); b = v.get('before') or {}; p = v.get('plot') or {}
            with self.subTest('the image beside the method', view=k):
                c, e = b.get('canvas'), b.get('est')
                self.assertTrue(c and e)
                self.assertLessEqual(c['x'] + c['w'], e['x'] + 1)
                self.assertTrue(c['y'] < e['y'] + e['h'] and e['y'] < c['y'] + c['h'])
            with self.subTest('control: the plot beside the table', view=k):
                self.assertGreaterEqual(p['tab']['x'], p['plot']['x'] + p['plot']['w'] - 1)
        for k in ('phone_light', 'phone_dark'):
            v = self.view(k); b = v.get('before') or {}; p = v.get('plot') or {}
            with self.subTest('no sideways scroll at phone width (1.4.10)', view=k, widths=(b.get('scrollWidth'), b.get('innerWidth'))):
                self.assertLessEqual(b.get('scrollWidth', 1e9), b.get('innerWidth', 0))
            with self.subTest('control: the table under the plot', view=k):
                self.assertGreaterEqual(p['tab']['y'], p['plot']['y'] + p['plot']['h'] - 1)


if __name__ == '__main__':
    unittest.main()
