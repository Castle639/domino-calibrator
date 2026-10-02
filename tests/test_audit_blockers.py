"""The audit room's blockers B1 and B2 (30 Sept 2026, the calibrator's launch room; the audit room's report,
the audit room's record of 30 Sept 2026, not in this repository). Written before the fix, to fail on the tool as the audit found it.

B1: a broken or degenerate WCS gave a sky position and a record (an all-zero CD matrix put the comet about 1.2 deg off, a
singular one 0.9", SIP A_2_0 = 1e300 wrote RA 61.5, Dec 0, CRPIX1 = 'abc' 11.7" off; each accepted by the MPC's validator).
Now: no sky position and no record, with the reason, on the command line and on the page; the pixel answer stands.

B2: a record was written where no comet was measured: a constant image, pure noise, a saturated or brighter star taken by
the automatic start, a start a few pixels off (a fit on 2 to 37 of 41 radii, up to 23 px away, and not repeatable from run to
run). Now: no record unless a comet was measured, on both faces. The gate, the same on both, each value measured before it
was set (the launch room's report, section 9): every radius converged; the fit ends within 1.5 px of its start (the study's
60 fits: at most 0.78); no clipped peak (a pixel at the data's ceiling or SATURATE, or 3 or more sharing the peak's value;
the study's: 1); the peak at least 10 times the sky's noise above the sky (12-24 px out; the study's: 60 to 94, pure noise
3.8); and, with the automatic start, no other source at least a fifth as bright. When in doubt, refuse, with the reason. A
real comet from the study still gets its record: the first frame of each of its five visits, from the study's own start.
"""
import os, re, json, shutil, tempfile, subprocess, unittest, warnings
import numpy as np
from astropy.io import fits

from domino_calibrator import cli
from tests.test_hardening import REC_ARGS, run_main, comet, write, start
from tests.test_hardening_page import js, NODE, PW, PAGE, REC_PAGE

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
from domino_calibrator.hst import DATA                           # amendment 1: the package's own ground rule finds the frames
POSITIONS = os.path.join(ROOT, 'runs', 'H0_POSITIONS_2026-09-30.txt')
FIRSTS = ('ifle03geq', 'ifle04pdq', 'ifle05qlq', 'ifle06tjq', 'ifle22f7q')


def header(extra=None, cd=(-1e-4, 0.0, 0.0, 1e-4), n=64):
    h = fits.Header()
    for k, v in (('CTYPE1', 'RA---TAN'), ('CTYPE2', 'DEC--TAN'), ('CRPIX1', n / 2 + 0.5), ('CRPIX2', n / 2 + 0.5),
                 ('CRVAL1', 151.5), ('CRVAL2', 10.4), ('CD1_1', cd[0]), ('CD1_2', cd[1]), ('CD2_1', cd[2]), ('CD2_2', cd[3]),
                 ('RADESYS', 'ICRS'), ('DATE-OBS', '2025-12-12T10:00:00.000'), ('EXPTIME', 60.0), ('TIMESYS', 'UTC')):
        h[k] = v
    for k, v in (extra or {}).items():
        h[k] = v
    return h


def gauss(n, x, y, peak, s, sky=100.0, noise=5.0, seed=7):
    yy, xx = np.mgrid[0:n, 0:n]
    img = sky + peak * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * s * s))
    return img + np.random.default_rng(seed).normal(0, noise, (n, n)) if noise else img


WCS_CASES = {                                  # the breaker's four (F8.1), on the same image as `good`
    'cd_zero': dict(cd=(0.0, 0.0, 0.0, 0.0)),
    'cd_singular': dict(cd=(-1e-4, -2e-4, 1e-4, 2e-4)),
    'sip_huge': dict(extra={'CTYPE1': 'RA---TAN-SIP', 'CTYPE2': 'DEC--TAN-SIP', 'A_ORDER': 2, 'B_ORDER': 2, 'A_2_0': 1e300}),
    'crpix_str': dict(extra={'CRPIX1': 'abc'}),
}


def make_images(d):
    """The cases, written into d: {name: (path, start or None)}. start None is the automatic start."""
    f = {}
    good = gauss(64, 30.3, 32.7, 1000.0, 2.0).astype(np.float32)
    fits.PrimaryHDU(good, header()).writeto(os.path.join(d, 'good.fits')); f['good'] = (os.path.join(d, 'good.fits'), None)
    for name, kw in WCS_CASES.items():
        p = os.path.join(d, name + '.fits'); fits.PrimaryHDU(good, header(**kw)).writeto(p); f[name] = (p, None)
    p = os.path.join(d, 'const.fits'); fits.PrimaryHDU(np.full((64, 64), 7.0, np.float32), header()).writeto(p); f['const'] = (p, None)
    p = os.path.join(d, 'noise.fits')
    fits.PrimaryHDU((100 + np.random.default_rng(3).normal(0, 5, (64, 64))).astype(np.float32), header()).writeto(p)
    f['noise'] = (p, None)
    # a 101-px cutout: a comet (FWHM 3 px, peak about 2400 over sky 1000, read noise 10), and the same with a brighter star
    cut = gauss(101, 50.35, 49.55, 2400.0, 3.0 / 2.3548, sky=1000.0, noise=10.0, seed=11)
    p = os.path.join(d, 'cut.fits'); fits.PrimaryHDU(cut.astype(np.float32), header(n=101)).writeto(p)
    f['cutout, on the comet'] = (p, (50.35, 49.55)); f['cutout, automatic'] = (p, None)
    for dx, dy in ((5, 0), (0, -5), (3, 3)):
        f['cutout, start %+d %+d px off' % (dx, dy)] = (p, (50.35 + dx, 49.55 + dy))
    star = cut + gauss(101, 20.2, 80.6, 6000.0, 1.3, sky=0.0, noise=0.0)
    p = os.path.join(d, 'star.fits'); fits.PrimaryHDU(star.astype(np.float32), header(n=101)).writeto(p)
    f['a brighter star, automatic'] = (p, None); f['a brighter star, on the comet'] = (p, (50.35, 49.55))
    # a small uint16 frame (BZERO 32768), its brightest a saturated star clipped at 65535
    fr = gauss(201, 120.35, 80.55, 2400.0, 3.0 / 2.3548, sky=1000.0, noise=10.0, seed=12)
    fr += gauss(201, 50.4, 150.6, 400000.0, 1.5, sky=0.0, noise=0.0)
    fr = np.clip(np.round(fr), 0, 65535).astype(np.uint16)
    p = os.path.join(d, 'frame.fits')
    fits.PrimaryHDU(fr, header(n=201)).writeto(p)                   # astropy writes uint16 as BITPIX 16 with BZERO 32768
    f['a saturated star, automatic'] = (p, None); f['frame, on the comet'] = (p, (120.35, 80.55))
    return f


GOOD = ('good', 'cutout, on the comet', 'cutout, automatic', 'a brighter star, on the comet', 'frame, on the comet')
NO_COMET = ('const', 'noise', 'cutout, start +5 +0 px off', 'cutout, start +0 -5 px off', 'cutout, start +3 +3 px off',
            'a brighter star, automatic', 'a saturated star, automatic')


def args(start):
    return ([] if start is None else ['--x', repr(start[0]), '--y', repr(start[1])]) + REC_ARGS


def zero(out):
    m = re.search(r'# zero aperture: x ([-\d.]+) y ([-\d.]+)', out)
    return (float(m.group(1)), float(m.group(2))) if m else None


class Cases(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.d = tempfile.mkdtemp()
        cls.f = make_images(cls.d)
        for n in GOOD:                       # F10: a record only from a start given; a good case without one gives the automatic
            p, s = cls.f[n]                  # start's own position, so that it measures what it measured before
            if s is None:
                cls.f[n] = (p, start(p))

    @classmethod
    def tearDownClass(cls):
        shutil.rmtree(cls.d, ignore_errors=True)

    def cli(self, name):
        p, s = self.f[name]
        rc, out = run_main([p] + args(s))
        self.assertEqual(rc, 0 if name in GOOD else 2, out[-400:])   # his exit codes (the fix room's F2): 2 when a gate refused
        return out


class TestB1TheCommandLine(Cases):
    def test_b1_a_broken_wcs_gives_no_sky_position_and_no_record(self):
        ref = zero(self.cli('good'))
        self.assertIsNotNone(ref)
        self.assertIn('# version=2022', self.cli('good'))                       # control: the good WCS writes its record
        for name in WCS_CASES:
            with self.subTest(name):
                out = self.cli(name)
                self.assertNotIn('# version=2022', out, out[-600:])
                self.assertNotIn('# sky (ICRS)', out)
                self.assertRegex(out, r'# no ADES record: needs a sky position \(the WCS', out[-600:])
                self.assertEqual(zero(out), ref)                                # the pixel answer stands


class TestB2TheCommandLine(Cases):
    def test_b2_no_record_unless_a_comet_was_measured(self):
        for name in NO_COMET:
            with self.subTest(name):
                out = self.cli(name)
                self.assertNotIn('# version=2022', out, out[-600:])
                self.assertIn('# no ADES record: needs a comet measured (', out, out[-600:])
                if name != 'const':
                    self.assertIsNotNone(zero(out) or re.search(r'fewer than 2 radii', out), out[-400:])

    def test_b2_a_comet_still_gets_its_record(self):
        for name in GOOD:
            with self.subTest(name):
                out = self.cli(name)
                self.assertIn('# version=2022', out, out[-600:])

    def test_b2_the_studys_comet_still_gets_its_record(self):
        pos = {l.split()[0]: (float(l.split()[1]), float(l.split()[2])) for l in open(POSITIONS, encoding='utf-8')
               if l.strip() and not l.startswith('#')}
        for root in FIRSTS:
            p = os.path.join(DATA, root + '_flc.fits')
            if not os.path.exists(p):
                self.skipTest('the study\'s frames are not here: tools/fetch_frames.py 22 03 04 05 06')
            with self.subTest(root):
                rc, out = run_main([p, '--x', repr(pos[root][0]), '--y', repr(pos[root][1])] + REC_ARGS)
                self.assertIn('# version=2022', out, out[-600:])


def page_decide(files):
    """The page's engine on each file, as its page decides: {name: {x0, y0, need}}."""
    return js("""
const fs = require('fs'); out = {};
for (const [name, c] of Object.entries(D)) {
  const hdus = Z.parseFITS(new Uint8Array(fs.readFileSync(c.path)).buffer);
  const cur = hdus.find((u) => u.readable);
  const auto = c.start === null;
  const s = auto ? Z.brightestStart(cur.data, cur.nx, cur.ny) : c.start;
  const o = Z.shrink(cur.data, cur.nx, cur.ny, s[0], s[1], { estimator: 'G', radii: Z.publishedRadii(), background: 'annulus' });
  const r = Z.decide({ cur: cur, hdus: hdus, o: o, start: s, auto: auto });
  out[name] = { x0: o.x0, y0: o.y0, need: r.need, rd: r.rd };
}""", {n: {'path': p, 'start': s} for n, (p, s) in files.items()}, timeout=600)


@unittest.skipIf(NODE is None, 'no node')
class TestTheEngine(Cases):
    def test_b1_b2_the_page_decides_as_the_command_line(self):
        r = page_decide(self.f)
        for name in WCS_CASES:
            with self.subTest('B1 ' + name):
                self.assertIsNone(r[name]['rd'])
                self.assertTrue(any(n.startswith('a sky position (the WCS') for n in r[name]['need']), r[name]['need'])
        for name in NO_COMET:
            with self.subTest('B2 ' + name):
                self.assertTrue(any(n.startswith('a comet measured (') for n in r[name]['need']), r[name]['need'])
        for name in GOOD:
            with self.subTest('good ' + name):
                self.assertEqual(r[name]['need'], [])
        for name in tuple(WCS_CASES) + NO_COMET:                          # the same reason on both faces, but its numbers
            with self.subTest('the same words ' + name):
                out = self.cli(name)
                m = re.search(r'# no ADES record: needs (.*)', out)
                strip = lambda t: re.sub(r'[-\d.]+', '#', t)
                page = '; '.join(r[name]['need'])
                self.assertEqual(strip(m.group(1)).split('; ')[0], strip(page).split('; ')[0])


@unittest.skipIf(NODE is None or PW is None, 'no node or no playwright')
class TestThePage(Cases):
    def test_b1_b2_the_page_offers_no_record_to_copy(self):
        cases = []
        for name in ('good', 'cd_zero', 'const', 'a brighter star, automatic'):
            p, s = self.f[name]
            st = {'file': p, 'set': dict(REC_PAGE), 'run': True}     # amendment 2: a step, so that no start means the page's own
            if s is not None:
                st['x'], st['y'] = s
            cases.append({'name': name, 'steps': [st]})
        cp = os.path.join(self.d, 'cases.json'); json.dump(cases, open(cp, 'w', encoding='utf-8'))
        r = subprocess.run([NODE, os.path.join(PAGE, 'browser_cases.js'), cp], capture_output=True, text=True, encoding='utf-8',
                           errors='replace', timeout=600, env=dict(os.environ, PLAYWRIGHT_MODULE=PW))
        res = {c['name']: c['steps'][-1] for c in json.loads(r.stdout)}
        self.assertFalse(res['good']['copyDisabled'], res['good'])                  # control: a comet's record is offered
        self.assertIn('# version=2022', res['good']['ades'])
        for name, need in (('cd_zero', 'needs a sky position (the WCS'), ('const', 'needs a comet measured ('),
                           ('a brighter star, automatic', 'needs a comet measured (')):
            with self.subTest(name):
                self.assertTrue(res[name]['copyDisabled'], res[name])
                self.assertIn('No ADES record: ' + need, res[name]['ades'])
                self.assertIn('Zero-aperture position', res[name]['zero'])         # the pixel answer stands


if __name__ == '__main__':
    unittest.main()
