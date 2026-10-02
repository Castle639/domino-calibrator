"""The first release's words (the release room's record of 28 Sept 2026, not in this repository, the bar): what the README and the page's
"What it does" say about the study, checked against the study's own committed summaries. Written to fail on the
calibrator as the sixth room's pull request merged it (1e19288) and to pass once the words are fixed; every case is a
subTest, and the cases marked "control" stand before and after.

Lane 2's three blockers (the first refuters' record of 27 Sept 2026, not in this repository, lane 2, F3 and F10; the launch road's section 2)
are the first cases. None of them was a wrong number: each was a true number with its box cut off. So these tests
read clauses, not only numbers. The grammar the words keep, so that the test reads them as a stranger would:
- a tally is "N of M cells" or "N of the M cells" ("N of the M measurable cells" leaves out H4's NULL-FAILED cells);
  its box follows it as "at <seeing> and <pixel scale>" or "at <pixel scale> with <seeing>" ("any seeing" said
  aloud); the whole grid, 130 cells, needs no box. A property may follow: "all at >= X"/px";
- its verdict is the last one before it in its clause: "helps" (HELPS or WORKS), "fails" (FAILS), "further off than
  no correction" (|b0| > |b2|), "tailward" or "sunward" (b2 within 45 deg of PsAng, or of PsAng + 180 deg), or
  "measured in" (the cells a variant was measured in); its variant is the last named before it: the published radii
  with G and the background known (H3's own setting) unless "on the sky" (H4's ARC, fixed in arcsec), "units of the
  seeing" (H4's SEE), "background from the annulus" (H3's G-annulus, the tool's default) or "with M" (H3's M);
- a range, a count and every other number is registered below with where it is held; a number nobody registered is red.
A clause ends at ". ", "; ", ": " or a line break. The expected values are the records' own (H3_REPORT l. 139 and
142; H4_REAL_REPORT l. 137-138; "The answer" in the first room's record; lane 2's and lane 5's recounts in the
refuters' record), and the control recounts them from the summaries before any sentence is judged.

The release's refuter pass (the refuters' third record of 28 Sept 2026, not in this repository, D4.1) found the variant missing: the tallies
are G's with the background known, stated as the method's, while the tool's default takes the background from the
annulus (measured in 50 of the 130 cells) and the README's example ran M. The grammar gained the two variants and the
verdict "measured in", W3 the claims that name them, and W7 the variant's name on both faces; written to fail on the
calibrator as the seventh room left it (0e311b5).

The eleventh room (his pick, 29 Sept 2026, 16:37 UTC: the page's two paragraphs folded, [his words, not quoted in public] for their stars,
because [his words, not quoted in public]): W5 asks the page to name its in-house status in words, "checked by us, not
yet by anyone outside", and the README, which explains its stars, to keep "★★ in-house".

A9 (the audit, the audit's record of 29 Sept 2026, not in this repository; bar first, the eleventh room): the default's own result where it was
measured. The grammar gains "N of the M measured cells", counted over the cells its variant was measured in (the default's
50, which no box holds); W0 the records it must reproduce (H3's Ga tally, the fourth pass's recount); W3 the default's three
results on both faces; W8 the README's word on who recounted the default's and M's tallies, which the fifth pass outdated.

The twelfth room (his word, 29 Sept 2026: [his words, not quoted in public]; then [his words, not quoted in public]): the README says its stars in plain words, as the page does. Its
heading says "checked by us, not yet by anyone outside" for what was two stars; what was one star is "a first finding".
W3 reads the README's claims that way, W5 asks both faces for the page's words, W8 the default's line as first findings,
and W9 asks for no star on the README. Written to fail on the README as 724772e left it.

The thirteenth room (29 Sept 2026, the tests on any machine; the issue list's entry 2): W4 registered the tested versions
from the running kit, so on any other kit the README's own versions were numbers nobody registered. It reads them from
the record, pyproject.toml's minimums (test_release_package.RECORD); K13 compares the running versions with the record.

The fix room's F3 (1 Oct 2026, the fix room's record of 1 Oct 2026, not in this repository; the launch room's should-fixes 24 and 26):
two verdicts, "not measurable" (H4's NULL-FAILED, the cells the arcsec radii could not be measured in) and "further from
HST's photocentre than the r = 2 px one" (at SNR 20, H3's rms0_20 above its rms2_20; G's with the background known only);
W0 their records, W3 the claims that name them; the registry the new rule's numbers (the exit codes, ds9's "add 1", the
page's 25 Mpx, the record's 6 decimals, SNR 20, the sky ring's 12-24 px and the whole frame's measurement on record).
"""
import os, re, json, html, inspect, unittest, collections

import domino_calibrator
from domino_calibrator import ades, cli
from domino_calibrator.shrink import PUBLISHED_RADII, shrink
from tests.test_release_package import RECORD

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)                             # calibrator/: the folder that goes public, the README's own
RUNS = os.path.join(PKG, 'runs')
VISITS = ('22', '03', '04', '05', '06')                 # in time order: 12 Dec 2025 ... 22 Jan 2026
CREDIT = "A Castle product from Domino Observatory. Built by Annie, the Castle's AI."


def read(path):
    with open(path, encoding='utf-8') as f:
        return f.read()


# ---------------------------------------------------------------- the study's cells, from its committed summaries
def load_cells():
    h3 = json.loads(read(os.path.join(RUNS, 'H3_SUMMARY_2026-09-27.json')))
    h4 = json.loads(read(os.path.join(RUNS, 'H4_SUMMARY_2026-09-27.json')))
    cells = []
    for k, c in h3.items():
        g, g4, ga = c['G'], h4[k]['G'], c.get('Ga') or {}
        cells.append(dict(visit=c['visit'], see=float(c['fw']), pix=float(c['gs']), nframes=c['G']['nframes'],
                          b2=g['b2']['len'], b0=g['b0']['len'], tail=g['tail_b2'], sun=g['sun_b2'],
                          w20=g['rms0_20'] > g['rms2_20'],                       # F3: at SNR 20, b0 further from HST's than b2
                          PX=dict(cls=g['class'], ratio=g['ratio']),
                          ARC=dict(cls=g4['ARC']['class'], ratio=g4['ARC']['ratio']),
                          SEE=dict(cls=g4['SEE']['class'], ratio=g4['SEE']['ratio']),
                          Ga=dict(cls=ga.get('class'), ratio=ga.get('ratio')),        # G-annulus: measured in 50 cells only
                          M=dict(cls=c['M']['class'], ratio=c['M']['ratio'])))
    return cells


CELLS = load_cells()
SEEINGS = sorted({c['see'] for c in CELLS})
PIXELS = sorted({c['pix'] for c in CELLS})


def cond_ok(val, cond):
    if cond is None:
        return True
    op, a = cond[0], cond[1:]
    if op == '<=':
        return val <= a[0] + 1e-9
    if op == '>=':
        return val >= a[0] - 1e-9
    return a[0] - 1e-9 <= val <= a[1] + 1e-9


def in_box(see=None, pix=None, visits=None):
    return [c for c in CELLS if cond_ok(c['see'], see) and cond_ok(c['pix'], pix) and (visits is None or c['visit'] in visits)]


def verdict(c, key, variant):
    v = c[variant]
    return {'helps': v['cls'] in ('HELPS', 'WORKS'), 'fails': v['cls'] == 'FAILS',
            'worse': v['ratio'] is not None and v['ratio'] > 1, 'measured': v['cls'] is not None,
            'tailward': c['tail'] <= 45, 'sunward': c['sun'] <= 45,
            'nullfailed': v['cls'] == 'NULL-FAILED', 'worse20': variant == 'PX' and c['w20']}[key]   # F3: H3 ran SNR 20 for G only


def recount(key, variant, see=None, pix=None, measurable=False, visits=None):
    cs = [c for c in in_box(see, pix, visits) if not (measurable is True and c[variant]['cls'] == 'NULL-FAILED')
          and not (measurable == 'measured' and c[variant]['cls'] is None)]      # A9: 'measured', the cells the variant ran in
    hit = [c for c in cs if verdict(c, key, variant)]
    return len(hit), len(cs), hit


# ---------------------------------------------------------------- the two faces' words
def readme_text():
    t = read(os.path.join(PKG, 'README.md'))
    return re.sub(r'```.*?```', '\n', t, flags=re.S)                    # commands are not claims


def page_html():
    return read(os.path.join(PKG, 'page', 'index.html'))


def visible(h):
    h = re.sub(r'<(script|style)\b.*?</\1>', ' ', h, flags=re.S)
    return html.unescape(re.sub(r'<[^>]+>', ' ', h))


def page_what_it_does():
    h = re.sub(r'<code>(.*?)</code>', r'`\1`', page_html(), flags=re.S)     # code, as the README's backticks
    m = re.search(r'<h2>What it does</h2>(.*?)(?=<h2|<script|</body>)', h, flags=re.S)
    return visible(m.group(1)) if m else ''


def norm(t):
    t = t.replace('’', "'").replace('&Prime;', '″')
    return re.sub(r'[ \t]+', ' ', t)


FACES = (('README.md', lambda: norm(readme_text())), ("the page's What it does", lambda: norm(page_what_it_does())))

URL = re.compile(r'https?://\S+')
CODE = re.compile(r'`([^`]*)`')


def clauses(t):
    """The text cut into clauses: at '. ', '; ', ': ' and line breaks (a decimal point is not an end)."""
    t = URL.sub(' ', t)
    return [c.strip() for c in re.split(r'(?<=[.;:])\s+|\n', t) if c.strip()]


# ---------------------------------------------------------------- the grammar: tallies, boxes, verdicts, variants
NUM = r'\d+(?:\.\d+)?'
TALLY = re.compile(r'\b(?P<n>\d+) of (?:the )?(?P<m>\d+)(?P<meas> measurable| measured)? cells\b')   # A9: measured
ANY_OF = re.compile(r'\b(?P<n>\d+) of (?:the )?(?P<m>\d+)\b')
SEE_C = re.compile(r'(?P<op>≤|≥) ?(?P<v>' + NUM + r')″ seeing|seeing (?P<op2>≤|≥) ?(?P<v2>' + NUM + r')″|(?P<lo>' + NUM +
                   r')–(?P<hi>' + NUM + r')″ seeing|(?P<any>any seeing)')
PIX_C = re.compile(r'(?P<op>≤|≥) ?(?P<v>' + NUM + r')″/px|(?P<lo>' + NUM + r')–(?P<hi>' + NUM + r')″/px')
VERDICTS = ((r'further off than no correction', 'worse'), (r'\btailward\b', 'tailward'), (r'\bsunward\b', 'sunward'),
            (r'\bhelp(?:s|ed)?\b', 'helps'), (r'\bfail(?:s|ed)?\b', 'fails'), (r'\bmeasured in\b', 'measured'),
            (r"further from HST's photocentre than the r = 2 px one", 'worse20'), (r'\bnot measurable\b', 'nullfailed'))
VARIANTS = ((r'on the sky', 'ARC'), (r'units of the seeing', 'SEE'), (r'\bpublished\b', 'PX'),
            (r'background from the (?:2\.5r–5r )?annulus', 'Ga'), (r'\b[Ww]ith M\b', 'M'))
STUDY_WORDS = re.compile(r'″|extrapolat|sampling|set-up|cells|3I')


def cond_of(m):
    g = m.groupdict()
    if g.get('any'):
        return 'any'
    if g.get('lo'):
        return ('in', float(g['lo']), float(g['hi']))
    op = {'≤': '<=', '≥': '>='}[g.get('op') or g.get('op2')]
    return (op, float(g.get('v') or g.get('v2')))


def parse_box(rest):
    """The box right after a tally: ' at <cond> [and|with <cond>]'. Returns (seeing, pixel, text consumed)."""
    m = re.match(r'\s+at\s+', rest)
    if not m:
        return None, None, 0
    pos, see, pix = m.end(), None, None
    for _ in range(2):
        ms, mp = SEE_C.match(rest, pos), PIX_C.match(rest, pos)
        if ms and see is None:
            see, pos = cond_of(ms), ms.end()
        elif mp and pix is None:
            pix, pos = cond_of(mp), mp.end()
        else:
            break
        mc = re.match(r'\s+(?:and|with)\s+', rest[pos:])
        if not mc:
            break
        pos += mc.end()
    return see, pix, pos


def last_before(patterns, text):
    best, where = None, -1
    for pat, key in patterns:
        for m in re.finditer(pat, text):
            if m.start() > where:
                best, where = key, m.start()
    return best


def tallies(t):
    """Every tally on a face: dict(clause, n, m, measurable, see, pix, verdict, variant, prop, span)."""
    out = []
    for cl in clauses(t):
        for m in TALLY.finditer(cl):
            see, pix, used = parse_box(cl[m.end():])
            after = cl[m.end() + used:]
            prop = re.match(r',? all (?:of them )?at (?P<op>≤|≥) ?(?P<v>' + NUM + r')″/px', after)
            meas = 'measured' if m.group('meas') == ' measured' else bool(m.group('meas'))   # A9: the cells its variant was measured in
            out.append(dict(clause=cl, n=int(m.group('n')), m=int(m.group('m')), measurable=meas,
                            see=see, pix=pix, verdict=last_before(VERDICTS, cl[:m.start()]),
                            variant=last_before(VARIANTS, cl[:m.start()]) or 'PX',
                            prop=(({'≤': '<=', '≥': '>='}[prop.group('op')], float(prop.group('v'))) if prop else None),
                            span=(m.start(), m.end() + used + (prop.end() if prop else 0))))
    return out


# ---------------------------------------------------------------- the registry: every other number, and where it is held
def fmt_range(lo, hi, dec):
    return '%.*f–%.*f' % (dec, lo, dec, hi)


def rng(values, dec):
    return fmt_range(min(values), max(values), dec)


PROF = dict(see=('<=', 1.0), pix=('<=', 0.44))
AMAT = dict(see=('>=', 2.0), pix=('>=', 1.0))
# a range: its text, the words its clause must name (its box), and what it is, computed from the summaries or the code
RANGES = {   # the words its clause must name are patterns: "≤ 1″" and "≤ 1.0″" name the same edge
    '0.05–0.15″': ((r'≤ 1(?:\.0)?″ seeing', r'≤ 0\.44″/px', r'r = 2 px'), lambda: rng([c['b2'] for c in in_box(**PROF)], 2) + '″'),
    '0.12–0.64″': ((r'≥ 2(?:\.0)?″ seeing', r'≥ 1(?:\.0)?″/px', r'r = 2 px'), lambda: rng([c['b2'] for c in in_box(**AMAT)], 2) + '″'),
    '27–73 %': ((r'≤ 1(?:\.0)?″ seeing', r'≤ 0\.44″/px', r'removing'), lambda: rng([100 * (1 - c['PX']['ratio']) for c in in_box(**PROF)], 0) + ' %'),
    '4–42°': ((r'first four visits', r'antisolar'), lambda: rng([c['tail'] for c in in_box(visits=VISITS[:4])], 0) + '°'),
    '0.88–2.64″': ((r'on the sky',), lambda: fmt_range(PUBLISHED_RADII[0] * 0.44, PUBLISHED_RADII[-1] * 0.44, 2) + '″'),
    '2.0–6.0 px': ((), lambda: fmt_range(PUBLISHED_RADII[0], PUBLISHED_RADII[-1], 1) + ' px'),
    '0.7–4″': ((r'seeing',), lambda: '%g–%g″' % (SEEINGS[0], SEEINGS[-1])),
    '0.24–2.0″/px': ((r'pixel',), lambda: '%.2f–%.1f″/px' % (PIXELS[0], PIXELS[-1])),
    '2.5r–5r': ((r'annulus',), lambda: '%gr–%gr' % inspect.signature(shrink).parameters['annulus'].default),
    '12–24 px': ((r'sky ring',), lambda: '%g–%g px' % (cli.SKY_IN, cli.SKY_OUT)),         # F3: --rms-noise's noise, F2's ring
}


def visit_dates():
    """The first and last visit's dates, as H3's report states them (its header lines)."""
    d = {}
    for ln in read(os.path.join(RUNS, 'H3_REPORT_2026-09-27.txt')).splitlines():
        m = re.match(r'#\s+visit (\d\d) (\d{4})-(\w{3})-(\d\d)', ln)
        if m:
            d[m.group(1)] = '%d %s %s' % (int(m.group(4)), m.group(3), m.group(2))
    return d


DATES = {'12 Dec 2025 – 22 Jan 2026': lambda: visit_dates()['22'] + ' – ' + visit_dates()['06']}
WHOLE_FRAME = 'on a 26 Mpx frame, one run took about 42 s and 1.4 GB of memory'
# the method's own numbers, held by the code
EXACT = {
    '1e-4 px': lambda: inspect.signature(shrink).parameters['tol_g'].default == 1e-4,
    '1e-6 px': lambda: inspect.signature(shrink).parameters['tol_m'].default == 1e-6,
    '3×3': lambda: '3x3 pixels' in read(os.path.join(PKG, 'domino_calibrator', 'estimators.py')),
    # F3: the page's limit, the record's decimals without --rms-noise, H3's low-signal setting (its l. 8), and the whole
    # frame's time and memory as their record states them (runs/fix_f3_whole_frame.py)
    '25 Mpx': lambda: 'const MAX_PIXELS = 25e6;' in read(os.path.join(PKG, 'page', 'zeroap.js')),
    '6 decimals': lambda: ades.DECIMALS_DEFAULT == 6,
    'SNR 20': lambda: 'RMS0/RMS2 SNR100, SNR20' in read(os.path.join(RUNS, 'H3_REPORT_2026-09-27.txt')).splitlines()[7],
    WHOLE_FRAME: lambda: 'README: ' + WHOLE_FRAME in read(os.path.join(RUNS, 'FIX_F3_WHOLE_FRAME_2026-10-01.txt')).splitlines(),
}
IDENT = re.compile(r'\b(?:3I/ATLAS|3I|WFC3/UVIS|F350LP|UTF-8|H[0-4](?:–H[0-4])?|S[01]|arXiv:\d{4}\.\d{5})\b')
CITATION = {'2016', '1507.01980', '2.1', '3.1'}           # Farnocchia et al. 2016, arXiv:1507.01980, sections 2.1 and 3.1
# F12 (the fix room, item 24): the data's credit and the method's citation, as their sources give them: NASA's contract
# NAS 5-26555 in MAST's acknowledgement; Hubble programme 18152 (the frames' PROPOSID); C/2013 A1, Icarus 266, 279-287
# (Crossref, for the paper's DOI); Tholen & Chesley 2004, BAAS 36, 1151
CREDITS = {'5', '26555', '18152', '2013', '266', '279', '287', '2004', '36', '1151'}


def single_numbers():
    """A number standing alone: its value and why it is true (a check against the code, the tested versions or the
    summaries). The thirteenth room: the tested versions are pyproject.toml's record, not the running kit's; K13 compares
    the running versions with it."""
    kit = {v: k for k, v in RECORD.items()}
    reg = {
        '130': len(CELLS) == 130, '26': len({(c['see'], c['pix']) for c in CELLS}) == 26,
        '30': sum(next(c['nframes'] for c in CELLS if c['visit'] == v) for v in VISITS) == 30,
        '41': len(PUBLISHED_RADII) == 41, '0.1': abs(PUBLISHED_RADII[1] - PUBLISHED_RADII[0] - 0.1) < 1e-9,
        '2': PUBLISHED_RADII[0] == 2.0, '0': True,           # r = 2 px, the first radius; r = 0 and 0-based: conventions
        '2022': ades.VERSION == '2022', domino_calibrator.__version__: True,
        '16': 'phase-mean over 16 phases' in read(os.path.join(RUNS, 'H3_REPORT_2026-09-27.txt')).splitlines()[6],   # H3's setting, l. 7
        # F3: ds9's "add 1", and exit 1, "cannot measure at all" (tests/test_fix_f2.py pins the codes, test_fix_f3.py the words)
        '1': 'add 1 for ds9' in cli.DS9 and '1 when it cannot measure at all' in ' '.join(cli.__doc__.split()),
    }
    for v in kit:
        reg[v] = True
    return reg, kit


def grid_value(val, unit):
    vals = PIXELS if unit == '″/px' else SEEINGS
    return any(abs(val - v) < 1e-9 for v in vals)


def unregistered(t):
    """Every number on a face that no tally, range, date, identifier or registry entry accounts for, with its clause."""
    reg, _ = single_numbers()
    bad = []
    for cl in clauses(CODE.sub(' ', t)):
        rest = cl
        for tl in tallies(cl):
            a, b = tl['span']
            rest = rest.replace(cl[a:b], ' ')
        for k in list(RANGES) + list(DATES):
            rest = rest.replace(k, ' ')
        for k, f in EXACT.items():
            if k in rest and f():
                rest = rest.replace(k, ' ')
        rest = IDENT.sub(' ', rest)
        for m in re.finditer(r'(?:≤|≥) ?(' + NUM + r')(″/px|″)', rest):
            if grid_value(float(m.group(1)), m.group(2)):
                rest = rest.replace(m.group(0), ' ', 1)
        for m in re.finditer(r'(?<![\w.])\d+(?:\.\d+)*(?!\w|\.\d)', rest):
            tok = m.group(0)
            if tok in CITATION and 'Farnocchia' in t:
                continue
            if tok in CREDITS and ('MAST' in cl or 'Icarus' in cl or 'BAAS' in cl or 'programme 18152' in cl):
                continue
            if not reg.get(tok, False):
                bad.append((tok, cl[:160]))
    return bad


# ---------------------------------------------------------------- the control: the recount reproduces the records
class TestTheRecount(unittest.TestCase):
    """Control (green before and after): the test's recount gives the tallies the records already state."""

    def test_w0_the_recount_reproduces_the_records(self):
        cls3 = collections.Counter(c['PX']['cls'] for c in CELLS)
        arc = collections.Counter(c['ARC']['cls'] for c in CELLS)
        see = collections.Counter(c['SEE']['cls'] for c in CELLS)
        cases = [
            ('H3_REPORT l. 139: G 41 HELPS, 1 WORKS, 88 FAILS', dict(cls3), {'HELPS': 41, 'WORKS': 1, 'FAILS': 88}),
            ('H3_REPORT l. 142: tailward in 104 of 130', recount('tailward', 'PX')[:2], (104, 130)),
            ('H3_REPORT l. 142: sunward in 0', recount('sunward', 'PX')[:2], (0, 130)),
            ('The answer: helps in all 20 professional cells', recount('helps', 'PX', **PROF)[:2], (20, 20)),
            ('H3_REPORT l. 141 (A9): the default, Ga, 30 HELPS and 20 FAILS', dict(collections.Counter(c['Ga']['cls'] for c in CELLS if c['Ga']['cls'])),
             {'HELPS': 30, 'FAILS': 20}),
            ('D4.1 recount (A9): the default helps in 20 of 20 professional cells', recount('helps', 'Ga', **PROF)[:2], (20, 20)),
            ('D4.1 recount (A9): the default fails in 15 of 40 at <= 0.44"/px', recount('fails', 'Ga', pix=('<=', 0.44))[:2], (15, 40)),
            ('D4.1 recount (A9): the default further off than none in 0 of the 50 measured', recount('worse', 'Ga', measurable='measured')[:2], (0, 50)),
            ('The answer: fails in 42 of 45 amateur cells', recount('fails', 'PX', **AMAT)[:2], (42, 45)),
            ('The answer: 45 of 130 further off than none', recount('worse', 'PX')[:2], (45, 130)),
            ('The answer: all of them at >= 0.70"/px', min(c['pix'] for c in recount('worse', 'PX')[2]), 0.70),
            ('lane 2: 15 of 40 FAIL at <= 0.44"/px', recount('fails', 'PX', pix=('<=', 0.44))[:2], (15, 40)),
            ('lane 2: 7 of 30 FAIL at <= 0.44"/px, <= 1.5"', recount('fails', 'PX', see=('<=', 1.5), pix=('<=', 0.44))[:2], (7, 30)),
            ('lane 2: b0 at least as close in 20 of 60 at >= 1.0"/px', 60 - recount('worse', 'PX', pix=('>=', 1.0))[0], 20),
            ('H4_REAL_REPORT l. 137: ARC 57 FAILS, 49 HELPS, 23 NULL-FAILED, 1 WORKS', dict(arc),
             {'FAILS': 57, 'HELPS': 49, 'NULL-FAILED': 23, 'WORKS': 1}),
            ('H4_REAL_REPORT l. 138: SEE 82 FAILS, 48 HELPS', dict(see), {'FAILS': 82, 'HELPS': 48}),
            ('the ARC record: FAILS 21 of the 24 measurable amateur cells',
             recount('fails', 'ARC', measurable=True, **AMAT)[:2], (21, 24)),
            ('the ARC record: SEE amateur FAILS 38 of 45', recount('fails', 'SEE', **AMAT)[:2], (38, 45)),
            ('lane 5, 5.2: ARC helps in 24 of 25 at 0.70-1.0"/px, <= 1.5"',
             recount('helps', 'ARC', see=('<=', 1.5), pix=('in', 0.70, 1.0))[:2], (24, 25)),
            ('lane 5, 5.2: the published radii FAIL in 15 of those 25',
             recount('fails', 'PX', see=('<=', 1.5), pix=('in', 0.70, 1.0))[:2], (15, 25)),
            ('The answer: 0.05-0.15"', RANGES['0.05–0.15″'][1](), '0.05–0.15″'),
            ('The answer: 0.12-0.64"', RANGES['0.12–0.64″'][1](), '0.12–0.64″'),
            ('The answer: removing 27-73 %', RANGES['27–73 %'][1](), '27–73 %'),
            ('The answer: 4-42 deg from the antisolar direction in visits 22-05', RANGES['4–42°'][1](), '4–42°'),
            ('h4_arcsec.py: ARC 0.88-2.64"', RANGES['0.88–2.64″'][1](), '0.88–2.64″'),
            ('H3_REPORT l. 141: Ga 30 HELPS, 20 FAILS, in 50 cells', dict(collections.Counter(c['Ga']['cls'] for c in CELLS if c['Ga']['cls'])),
             {'HELPS': 30, 'FAILS': 20}),
            ('H3_REPORT l. 140: M 7 WORKS, 40 HELPS, 83 FAILS', dict(collections.Counter(c['M']['cls'] for c in CELLS)),
             {'WORKS': 7, 'HELPS': 40, 'FAILS': 83}),
            ('the audit room, C3.3 (F3): at SNR 20, b0 further from HST\'s than b2 in 9 of the 20 professional cells',
             recount('worse20', 'PX', **PROF)[:2], (9, 20)),
            ('the ARC record (F3): NULL-FAILED in 21 of the 45 amateur cells, the 24 measurable the rest',
             recount('nullfailed', 'ARC', **AMAT)[:2], (21, 45)),
        ]
        for name, got, want in cases:
            with self.subTest(name):
                self.assertEqual(got, want)


# ---------------------------------------------------------------- lane 2's three blockers, on both faces
class TestLaneTwosBlockers(unittest.TestCase):
    def test_w1_1_a_verdict_carries_its_tally_and_its_whole_box(self):
        # 1e19288: the page's "it helped on sharp images (<= 0.44"/px)" names no tally and drops the seeing (15 of those
        # 40 cells FAIL); the README's "helps at professional sampling (removing 27-73 %)" names no tally or edges
        for face, text in FACES:
            t = text()
            with self.subTest(face, what='the face has words'):
                self.assertGreater(len(t), 200)
            for cl in clauses(CODE.sub(' ', t)):
                if not (last_before(VERDICTS, cl) and STUDY_WORDS.search(cl)):
                    continue
                with self.subTest(face, clause=cl[:120]):
                    tl = tallies(cl)
                    self.assertTrue(tl, 'a verdict without a tally "N of M cells"')
                    for x in tl:
                        # A9 (amended after its words were first run): a tally over the cells its variant was measured in
                        # needs no box, as the whole grid needs none; W2 recounts it over exactly those cells
                        if x['m'] != len(CELLS) and x['measurable'] != 'measured':
                            self.assertTrue(x['see'] is not None and x['pix'] is not None,
                                            'a box needs its seeing and its pixel scale (or "any seeing")')

    def test_w1_2_truth_is_named_as_hsts_photocentre(self):
        # 1e19288: the README's "closer to the truth" (lane 2, F3: "truth" there is HST's photocentre)
        for face, text in FACES:
            for cl in clauses(text()):
                if 'truth' in cl:
                    with self.subTest(face, clause=cl[:120]):
                        self.assertRegex(cl, r"(?:HST|Hubble)'s (?:own )?(?:zero-aperture )?photocentre")

    def test_w1_3_cells_are_counted_as_cells(self):
        # 1e19288: the README's "42 of 45 set-ups" and "45 of 130 set-ups"; there are 26 set-ups (lane 2, F10)
        for face, text in FACES:
            t = text()
            with self.subTest(face):
                over = [m.group(0) for m in re.finditer(r'\b(\d+) of (?:the )?(\d+) set-ups', t) if int(m.group(2)) > 26]
                over += [m.group(0) for m in re.finditer(r'\b(\d+) set-ups', t) if int(m.group(1)) > 26]
                self.assertEqual(over, [])


# ---------------------------------------------------------------- every number: tallies recounted, the rest registered
REQUIRED = {   # the claims each face must state (our research notes' calibrator line, with lane 2's correction), with its
    # status in plain words (the twelfth room): 'checked', checked by us, not yet by anyone outside; 'first', a first finding
    'README.md': [
        ('tailward', 'PX', None, None, False, (104, 130), 'checked'),
        ('helps', 'PX', PROF['see'], PROF['pix'], False, (20, 20), 'checked'),
        ('fails', 'PX', AMAT['see'], AMAT['pix'], False, (42, 45), 'checked'),
        ('fails', 'PX', 'any', ('<=', 0.44), False, (15, 40), 'checked'),
        ('worse', 'PX', None, None, False, (45, 130), 'checked'),
        ('fails', 'ARC', AMAT['see'], AMAT['pix'], True, (21, 24), 'checked'),
        ('fails', 'SEE', AMAT['see'], AMAT['pix'], False, (38, 45), 'checked'),
        ('helps', 'ARC', ('<=', 1.5), ('in', 0.70, 1.0), False, (24, 25), 'first'),
        ('measured', 'Ga', None, None, False, (50, 130), 'first'),          # the refuter pass, D4.1: the default's coverage
        ('worse', 'M', None, None, False, (58, 130), 'first'),              # and M's
        ('helps', 'Ga', PROF['see'], PROF['pix'], False, (20, 20), 'first'),  # A9: the default's own result where it was measured
        ('fails', 'Ga', 'any', ('<=', 0.44), False, (15, 40), 'first'),
        ('worse', 'Ga', None, None, 'measured', (0, 50), 'first'),
        ('worse20', 'PX', PROF['see'], PROF['pix'], False, (9, 20), 'checked'),   # F3, item 26: "helps" with its low-signal limit
        ('nullfailed', 'ARC', AMAT['see'], AMAT['pix'], False, (21, 45), 'checked'),   # F3, item 24: the cells not measured
    ],
    "the page's What it does": [
        ('helps', 'PX', PROF['see'], PROF['pix'], False, (20, 20), 'checked'),
        ('fails', 'PX', AMAT['see'], AMAT['pix'], False, (42, 45), 'checked'),
        ('fails', 'PX', 'any', ('<=', 0.44), False, (15, 40), 'checked'),
        ('worse', 'PX', None, None, False, (45, 130), 'checked'),          # F3, item 28: G's own 45 beside M's 58
        ('worse20', 'PX', PROF['see'], PROF['pix'], False, (9, 20), 'checked'),   # F3, item 26, as the README says it
        ('measured', 'Ga', None, None, False, (50, 130), 'first'),
        ('worse', 'M', None, None, False, (58, 130), 'first'),
        ('helps', 'Ga', PROF['see'], PROF['pix'], False, (20, 20), 'first'),  # A9
        ('fails', 'Ga', 'any', ('<=', 0.44), False, (15, 40), 'first'),
        ('worse', 'Ga', None, None, 'measured', (0, 50), 'first'),
    ],
}


def line_of(t, clause):
    for ln in t.splitlines():
        if clause[:60] in ln:
            return ln
    return ''


class TestEveryNumber(unittest.TestCase):
    def test_w2_every_tally_is_the_recount_of_its_box(self):
        for face, text in FACES:
            t = CODE.sub(' ', text())
            for x in tallies(t):
                with self.subTest(face, tally=x['clause'][:120]):
                    self.assertIsNotNone(x['verdict'], 'a tally without a verdict')
                    see = None if x['see'] == 'any' else x['see']
                    n, m, hit = recount(x['verdict'], x['variant'], see, x['pix'], x['measurable'])
                    self.assertEqual((x['n'], x['m']), (n, m), 'the summaries give %d of %d' % (n, m))
                    if x['prop']:
                        self.assertTrue(all(cond_ok(c['pix'], x['prop']) for c in hit), 'the property "all at" fails')
            for m in ANY_OF.finditer(t):
                if not TALLY.match(t, m.start()):
                    with self.subTest(face, count=t[max(0, m.start() - 40):m.end() + 30]):
                        self.fail('a count the test cannot read: say "N of M cells" and its box')

    def test_w3_each_face_states_the_studys_tallies_with_their_boxes_and_stars(self):
        for face, text in FACES:
            t = CODE.sub(' ', text())
            found = tallies(t)
            for key, variant, see, pix, meas, nm, status in REQUIRED[face]:
                with self.subTest(face, claim='%s %s %s %s %s' % (key, variant, see, pix, nm)):
                    hits = [x for x in found if (x['verdict'], x['variant'], x['see'], x['pix'], x['measurable'], (x['n'], x['m']))
                            == (key, variant, see, pix, meas, nm)]
                    self.assertTrue(hits, 'not stated')
                    if face == 'README.md':            # the status in plain words, on the claim's own line (the twelfth room)
                        ln = line_of(t, hits[0]['clause'])
                        self.assertNotIn('★', ln)
                        if status == 'first':
                            self.assertIn('first finding', ln)
                        else:
                            self.assertNotIn('first finding', ln)

    def test_w4_every_other_number_is_registered_and_true(self):
        for face, text in FACES:
            t = text()
            with self.subTest(face, what='no number nobody registered'):
                self.assertEqual(unregistered(t), [])
            for k, (words, f) in RANGES.items():
                for cl in clauses(CODE.sub(' ', t)):
                    if k in cl:
                        with self.subTest(face, range=k):
                            self.assertEqual(f(), k)
                            for w in words:
                                self.assertRegex(cl, w)
            for k, f in DATES.items():
                if k in t:
                    with self.subTest(face, dates=k):
                        self.assertEqual(f(), k)


# ---------------------------------------------------------------- the stars, the limits, the invitation, the paths
# the stars in plain words: the page's since the eleventh room (his pick), the README's since the twelfth (his word)
PLAIN_STARS = ('checked by us, not yet by anyone outside', r'checked by us,? (?:and )?not yet by anyone outside')
LIMITS = (PLAIN_STARS, ('one comet', r'\bone comet\b'), ('five visits', r'\bfive visits\b'),
          ('one filter', r'\bone filter\b'), ("HST's photocentre as the reference",
                                              r"(?:HST|Hubble)'s (?:own )?(?:zero-aperture )?photocentre"),
          ('the boxes drawn after the data', r'boxes[^.]{0,80}drawn after the data'),
          ('the invitation to check it', r'[Cc]heck (?:it|the study|this)[^.]{0,80}your own (?:frames|images)'))


class TestTheVariant(unittest.TestCase):
    def test_w7_each_face_names_the_variant_its_tallies_were_measured_with(self):
        # the refuter pass, D4.1 (0e311b5): the tallies are H3's G with the background known, and neither face said so;
        # the README's own example ran M, further off than no correction in 58 of the 130 cells where G is in 45
        for face, text in FACES:
            with self.subTest(face):
                self.assertRegex(text(), r"\bG(?:'s)? (?:with|and) the background known")
        with self.subTest("the README's commands"):
            cmds = ' '.join(re.findall(r'```(.*?)```', read(os.path.join(PKG, 'README.md')), flags=re.S))
            self.assertNotRegex(cmds, r'--estimator\s+M\b')


class TestStarsLimitsInvitation(unittest.TestCase):
    def test_w5_each_face_names_its_stars_limits_and_the_invitation(self):
        # the invitation's list: one comet, five visits, one filter, HST's photocentre as the truth, the boxes drawn
        # after the data, and an invitation to check it on one's own frames; with its stars
        for face, text in FACES:
            t = text()
            for name, pat in LIMITS:
                with self.subTest(face, limit=name):
                    self.assertRegex(t, pat)


class TestWhoRecounted(unittest.TestCase):
    def test_w8_the_readme_says_who_recounted_the_defaults_and_ms_tallies(self):
        # A9: "no refuter has checked these two" predates the fifth pass, whose Fable recounted both
        # (the refuters' record of 29 Sept 2026, not in this repository, its lane's words against the records)
        r = norm(readme_text())
        self.assertNotIn('no refuter has checked', r)
        self.assertRegex(r, r'\*\*The tool.s default, and M\*\* \(first findings, [^)]*recounted[^)]*refuter[^)]*\)')


class TestPlainWords(unittest.TestCase):
    def test_w9_no_star_on_the_readme_the_plain_words_in_its_place(self):
        # his word (the twelfth room): [his words, not quoted in public]; the page has had none since the
        # eleventh room (the design test's D10)
        r = read(os.path.join(PKG, 'README.md'))
        with self.subTest('no star'):
            self.assertNotIn('★', r)
            self.assertNotIn('&#9733;', r)
        with self.subTest('what a first finding is, said once'):
            self.assertRegex(norm(readme_text()), r'a first finding was found but not yet checked as far as the rest')


FILE_EXT = re.compile(r'\.(?:md|py|json|txt|png|js|html|gz|cff|toml|yml)$')


def named_paths(face):
    """The paths a face names: code spans (the README's `...`, the page's <code>...</code>) and link targets that look
    like a file or a folder, relative to the folder that goes public (calibrator/)."""
    if face == 'README.md':
        t = read(os.path.join(PKG, 'README.md'))
        spans = CODE.findall(re.sub(r'```.*?```', ' ', t, flags=re.S)) + re.findall(r'\]\(([^)\s]+)\)', t)
    else:
        spans = [html.unescape(s) for s in re.findall(r'<code>(.*?)</code>', page_html(), flags=re.S)]
    out = []
    for s in spans:
        s = s.strip()
        if ' ' in s or URL.match(s) or s.endswith('.fits'):
            continue
        if FILE_EXT.search(s) or s.endswith('/'):
            out.append(s)
    return out


# the curation list's files, copied in beside the package when the public repository's folder is built (archive/
# the release room's record of 28 Sept 2026, not in this repository, section 6; the launch list's step 6): named by the README since step 4, present in that
# folder, not in the Castle's calibrator/
COPIED_IN = ('tools/fetch_frames.py', 'tools/psfkit.py', 'data/hst-3i/', 'data/hst-3i/CHECKSUMS.sha256')


class TestPaths(unittest.TestCase):
    def test_w6_every_path_is_inside_the_folder_that_goes_public(self):
        # 1e19288: the README and the page each point once into the Castle's archive/ (and the README into papers/)
        for face, raw in (('README.md', lambda: read(os.path.join(PKG, 'README.md'))), ('the page', page_html)):
            with self.subTest(face, what="no path into the Castle's archive/ or papers/"):
                self.assertEqual(re.findall(r'(?<![\w/])(?:archive|papers)/[\w./-]*', raw()), [])
            for p in named_paths(face):
                with self.subTest(face, path=p):
                    self.assertTrue(os.path.exists(os.path.join(PKG, p)) or p in COPIED_IN, 'not inside calibrator/: ' + p)


if __name__ == '__main__':
    unittest.main()
