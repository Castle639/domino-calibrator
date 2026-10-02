"""The fix room's F2: inputs and failures (1 Oct 2026; the fix room's record of 1 Oct 2026, not in this repository). Written before the fix,
to fail on the tool as F1 left it (01ca235), and to pass once it is fixed. The launch room's should-fixes, as it numbered them,
with his answers (the launch room's report, section 11, and this room's section 4):

5   The noise the scatter draws from is the comet's own sky ring (12-24 px about the zero-aperture position, the gate's), not
    the image's 5-px border: a cutout of the same pixels wrote rmsRA ten times the whole frame's (the audit's F9.2). So a
    cutout and its whole frame give the same noise level, and rmsRA moves on every cutout, as expected.
9   The primary's WCS is read for an extension only when the extension says INHERIT = T, the FITS convention (the audit's F8.5).
10  The three corrupt headers (BITPIX 12, NAXIS1 = 64.0, SIMPLE = F) are named at the header stage, on both faces, in the
    same words, not as Python's internal error; and the exit codes, his answer 1: 2 when the gates refuse (no comet measured,
    or the sky position refused), 1 when it cannot measure at all, 0 when the measurement passed its gates.
11  A closed pipe (| head) ends quietly, with no traceback.
12  With --rms-noise, the estimated time is printed before the redraws start; the 3-1000 limit is kept (his answer 2).
14  Positions stay 0-based, and "0-based; add 1 for ds9" stands beside every printed position, on both faces.
The faces' count of converged radii is not made to agree (his yes to the "why not": the report, section 3).
"""
import os, re, sys, json, shutil, tempfile, subprocess, unittest, warnings
import numpy as np
from astropy.io import fits

from domino_calibrator import cli, synth
from tests.test_hardening import REC_ARGS, Tmp, run_main, comet, write, wcs_cards, given
from tests.test_hardening_page import js, NODE, PAGE

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
DS9 = '0-based; add 1 for ds9'


def gauss(n, x, y, peak, s, sky=100.0, noise=5.0, seed=7):
    yy, xx = np.mgrid[0:n, 0:n]
    img = sky + peak * np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * s * s))
    return img + np.random.default_rng(seed).normal(0, noise, (n, n)) if noise else img


def raw(path, cards, nbytes):
    """A FITS file written card by card (the audit room's mk_inputs.py), so that a header astropy refuses can be made."""
    s = ''.join(c.ljust(80) for c in cards + ['END'])
    s = s.ljust(((len(s) + 2879) // 2880) * 2880)
    open(path, 'wb').write(s.encode('ascii') + bytes(((nbytes + 2879) // 2880) * 2880))
    return path


def card(k, v):
    return '%-8s= %20s' % (k, v)


CORRUPT = {   # the audit's three (F8.6), each with the words both faces give
    'bitpix12': ([card('SIMPLE', 'T'), card('BITPIX', '12'), card('NAXIS', '2'), card('NAXIS1', '8'), card('NAXIS2', '8')], 128,
                 'BITPIX 12, not a FITS pixel type (8, 16, 32, 64, -32 or -64)'),
    'naxis1_float': ([card('SIMPLE', 'T'), card('BITPIX', '-32'), card('NAXIS', '2'), card('NAXIS1', '64.0'), card('NAXIS2', '64')],
                     64 * 64 * 4, 'NAXIS1 = 64.0 is not a size: the header is corrupt'),
    'simple_f': ([card('SIMPLE', 'F'), card('BITPIX', '-32'), card('NAXIS', '2'), card('NAXIS1', '8'), card('NAXIS2', '8')], 256,
                 'not a FITS file (it does not begin with SIMPLE = T)'),
}


def cli_run(args, **kw):
    """The command line as a user runs it: (exit code, stdout, stderr)."""
    r = subprocess.run([sys.executable, '-m', 'domino_calibrator.cli'] + args, cwd=ROOT, capture_output=True,
                       encoding='utf-8', errors='replace', timeout=600, env=dict(os.environ, PYTHONUTF8='1'), **kw)
    return r.returncode, r.stdout, r.stderr


class F2_5_SkyRing(Tmp):
    def frames(self):
        """A whole frame (201 px) with a comet at its centre, and a 61-px cutout of the same pixels about the comet."""
        img, (xt, yt) = synth.render(201, 100.3, 99.7, flux_n=2e4, k=600.0, a=0.3, model='dipole', psf=('gauss', 3.0), sub=10)
        img = img + 100.0 + np.random.default_rng(21).normal(0.0, 5.0, img.shape)
        whole = write(self.p('whole.fits'), img)
        cut = write(self.p('cut.fits'), img[70:131, 70:131])
        return whole, cut

    def test_a_cutout_and_its_whole_frame_draw_from_the_same_noise(self):
        whole, cut = self.frames()
        rw = cli.measure_file(whole, x=100.3, y=99.7, rms_noise=20)
        rc = cli.measure_file(cut, x=30.3, y=29.7, rms_noise=20)
        self.assertIn('noise', rw, rw.get('rms_error')); self.assertIn('noise', rc, rc.get('rms_error'))
        self.assertEqual(rw['noise'][1], rc['noise'][1])                           # the same ring, the same pixels,
        self.assertAlmostEqual(rw['noise'][0], rc['noise'][0], delta=1e-9 * rw['noise'][0])   # the same noise level
        ratio = rc['sd_px'][0] / rw['sd_px'][0]                                     # the audit's cutout: ten times
        self.assertTrue(0.5 < ratio < 2.0, (ratio, rc['sd_px'], rw['sd_px']))

    def test_too_few_sky_pixels_no_scatter_with_the_reason(self):
        img = gauss(21, 10.2, 9.8, 2000.0, 1.5)                                      # the ring 12-24 px leaves this image
        r = cli.measure_file(write(self.p('tiny.fits'), img), x=10.2, y=9.8, rms_noise=5, background=100.0)
        self.assertNotIn('rms', r); self.assertIn('sky pixels 12-24 px from', r.get('rms_error', ''))

    def test_control_the_record_still_carries_the_scatter(self):
        img, _ = comet(); p = write(self.p('c.fits'), img)
        rc_, out = run_main([p, '--rms-noise', '5'] + given(p) + REC_ARGS)
        self.assertIn('# version=', out, out[-500:])
        self.assertIn('# sky-noise scatter on the sky', out, out[-500:])     # F11b: the scatter beside the record, not in it


class F2_9_Inherit(Tmp):
    def mef(self, inherit):
        img = gauss(64, 30.3, 32.7, 1000.0, 2.0).astype(np.float32)
        h0 = wcs_cards(fits.Header(), n=64)
        h0['DATE-OBS'] = '2025-12-12T21:20:32.000'; h0['EXPTIME'] = 60.0
        e = fits.ImageHDU(img, name='CUTOUT')
        if inherit:
            e.header['INHERIT'] = True
        p = self.p('mef_%s.fits' % inherit)
        fits.HDUList([fits.PrimaryHDU(header=h0), e]).writeto(p, overwrite=True)
        return p

    def test_the_primarys_wcs_only_with_inherit(self):
        no, yes = self.mef(False), self.mef(True)
        r = cli.measure_file(no)
        self.assertNotIn('radec', r); self.assertIn('INHERIT', r.get('sky_error', ''))
        r = cli.measure_file(yes)
        self.assertIn('radec', r, r.get('sky_error'))
        page = js("""
const fs = require('fs'); out = {};
for (const [name, p] of Object.entries(D)) {
  const hdus = Z.parseFITS(new Uint8Array(fs.readFileSync(p)).buffer);
  const cur = hdus.find((u) => u.readable);
  const o = Z.shrink(cur.data, cur.nx, cur.ny, 30.3, 32.7, { estimator: 'G', radii: Z.publishedRadii(), background: 'annulus' });
  const r = Z.decide({ cur: cur, hdus: hdus, o: o, start: [30.3, 32.7], auto: false });
  out[name] = { need: r.need, rd: r.rd };
}""", {'no': no, 'yes': yes})
        self.assertIsNone(page['no']['rd']); self.assertTrue(any('INHERIT' in n for n in page['no']['need']), page['no'])
        self.assertIsNotNone(page['yes']['rd'], page['yes'])

    def test_control_an_extension_with_its_own_wcs_keeps_it(self):
        img = gauss(64, 30.3, 32.7, 1000.0, 2.0).astype(np.float32)
        e = fits.ImageHDU(img, header=wcs_cards(fits.Header(), n=64), name='SCI')
        p = self.p('own.fits'); fits.HDUList([fits.PrimaryHDU(), e]).writeto(p)
        self.assertIn('radec', cli.measure_file(p))


class F2_10_CorruptHeaders(Tmp):
    def test_each_is_named_at_the_header_stage_on_both_faces(self):
        paths = {k: raw(self.p(k + '.fits'), c, n) for k, (c, n, _) in CORRUPT.items()}
        for k, p in paths.items():
            with self.subTest(face='command line', file=k):
                rc, out = run_main([p])
                self.assertEqual(rc, 1, out)
                self.assertIn('# cannot measure:', out)
                self.assertIn(CORRUPT[k][2], out)
                self.assertNotRegex(out, r'KeyError|TypeError|AttributeError')
        page = js("""
const fs = require('fs'); out = {};
for (const [k, p] of Object.entries(D)) {
  const h = Z.parseFITS(new Uint8Array(fs.readFileSync(p)).buffer);
  out[k] = { unreadable: (h.find((u) => u.unreadable) || {}).unreadable || '', readable: h.some((u) => u.readable) };
}""", paths)
        for k in paths:
            with self.subTest(face='page', file=k):
                self.assertFalse(page[k]['readable'], page[k]); self.assertIn(CORRUPT[k][2], page[k]['unreadable'])


class F2_10_ExitCodes(Tmp):
    """His answer 1: 0 when the measurement passed its gates (a record may still be refused for a value), 2 when the gates
    refuse (no comet measured, or the sky position refused), 1 when it cannot measure at all."""
    def test_the_three_codes(self):
        img, _ = comet()
        good = write(self.p('c.fits'), img)
        nowcs = self.p('nowcs.fits'); fits.PrimaryHDU(img.astype(np.float32)).writeto(nowcs)
        const = write(self.p('const.fits'), np.full((71, 71), 7.0))
        h = wcs_cards(fits.Header(), n=71); h['CD1_1'] = h['CD1_2'] = h['CD2_1'] = h['CD2_2'] = 0.0
        broken = self.p('cd_zero.fits'); fits.PrimaryHDU(img.astype(np.float32), header=h).writeto(broken)
        bad = raw(self.p('bitpix12.fits'), *CORRUPT['bitpix12'][:2])
        cases = [('a record', [good] + REC_ARGS, 0), ('no record values asked', [good], 0),
                 ('a value refused, station 250', [good] + REC_ARGS[:1] + ['250'] + REC_ARGS[2:], 0),
                 ('no comet', [const] + REC_ARGS, 2), ('the WCS refused', [broken] + REC_ARGS, 2),
                 ('no WCS', [nowcs] + REC_ARGS, 2),
                 ('a corrupt header', [bad], 1), ('no such file', [self.p('none.fits')], 1),
                 ('radii that are not radii', [good, '--radii', '6:2:0.1'], 1), ('an unknown option', [good, '--no-such-option'], 1)]
        for name, a, want in cases:
            with self.subTest(name):
                rc, out, err = cli_run(a)
                self.assertEqual(rc, want, (name, out[-300:], err[-300:]))


class F2_11_ClosedPipe(Tmp):
    def test_a_closed_pipe_ends_quietly(self):
        img, _ = comet(); p = write(self.p('c.fits'), img)
        proc = subprocess.Popen([sys.executable, '-m', 'domino_calibrator.cli', p], cwd=ROOT, stdout=subprocess.PIPE,
                                stderr=subprocess.PIPE, env=dict(os.environ, PYTHONUTF8='1'))
        proc.stdout.close()                                                         # as `| head -0` would, before a line is read
        err = proc.stderr.read().decode('utf-8', 'replace'); rc = proc.wait(timeout=600)
        self.assertNotIn('Traceback', err); self.assertNotIn('BrokenPipeError', err)
        self.assertEqual(rc, 0, err[-300:])                                         # the measurement's own code


class F2_12_Estimate(Tmp):
    def test_the_estimate_comes_before_the_redraws(self):
        img, _ = comet(); p = write(self.p('c.fits'), img)
        calls, said = [], []
        real = cli.shrink

        def counting(*a, **k):
            calls.append(1)
            return real(*a, **k)
        cli.shrink = counting
        try:
            r = cli.measure_file(p, rms_noise=5, progress=lambda s: said.append((s, len(calls))))
        finally:
            cli.shrink = real
        self.assertEqual(len(said), 1, said)
        text, at = said[0]
        self.assertEqual(at, 1, said)                                               # only the measurement itself had run
        self.assertRegex(text, r'--rms-noise 5: about \d')
        self.assertEqual(r.get('rms_n'), (5, 5))

    def test_the_command_line_prints_it_and_the_limit_stands(self):
        img, _ = comet(); p = write(self.p('c.fits'), img)
        rc, out, err = cli_run([p, '--rms-noise', '5'])
        self.assertRegex(err, r'# --rms-noise 5: about \d', err[-300:])
        for n, ok in ((2, False), (3, True), (1000, None), (1001, False)):
            if ok is None:
                continue                                                            # 1000 redraws: allowed, and not run here
            with self.subTest(redraws=n):
                r = cli.measure_file(p, rms_noise=n)
                self.assertEqual('rms' in r or 'sd_px' in r, ok, r.get('rms_error'))
                if not ok:
                    self.assertIn('3 to 1000', r.get('rms_error', ''))


class F2_14_ZeroBased(Tmp):
    def test_the_command_line_says_it_beside_every_position(self):
        img, _ = comet(); p = write(self.p('c.fits'), img)
        rc, out = run_main([p])
        lines = out.splitlines()
        for start in ('# start (', '# r_px', '# zero aperture:'):
            with self.subTest(line=start):
                ln = next((l for l in lines if l.startswith(start)), '')
                self.assertIn(DS9, ln, ln)
        z = next((l for l in lines if l.startswith('# zero aperture:')), '')
        self.assertEqual(z.count(DS9), 2, z)                                        # the zero aperture's and r = 2 px's
        self.assertRegex(z, r'# zero aperture: x \d+\.\d{4} y \d+\.\d{4}')           # the numbers stay where scripts read them

    def two_sources(self):
        img = gauss(111, 30.0, 30.0, 3000.0, 1.5) + gauss(111, 80.0, 80.0, 1000.0, 1.5, sky=0.0, noise=0.0)
        return write(self.p('two.fits'), img)

    def test_the_automatic_starts_other_source_on_both_faces(self):
        p = self.two_sources()
        r = cli.measure_file(p)
        self.assertIn('another at least a fifth as bright is at (80, 80; %s)' % DS9, r.get('comet_error', ''), r.get('comet_error'))
        page = js("""
const fs = require('fs');
const hdus = Z.parseFITS(new Uint8Array(fs.readFileSync(D.p)).buffer), cur = hdus.find((u) => u.readable);
const s = Z.brightestStart(cur.data, cur.nx, cur.ny);
const o = Z.shrink(cur.data, cur.nx, cur.ny, s[0], s[1], { estimator: 'G', radii: Z.publishedRadii(), background: 'annulus' });
out = Z.decide({ cur: cur, hdus: hdus, o: o, start: s, auto: true }).need;""", {'p': p})
        self.assertTrue(any('is at (80, 80; %s)' % DS9 in n for n in page), page)

    def test_the_page_says_it_beside_every_position(self):
        page = open(os.path.join(PAGE, 'index.html'), encoding='utf-8').read()
        hint = re.search(r'<input type="number" id="sy"[^>]*>\s*<span class="hint">([^<]*)<', page)
        self.assertTrue(hint and DS9 in hint.group(1), hint and hint.group(1))
        show = page[page.index("const tab = $('tab')"):page.index("$('zero').textContent = txt")]
        self.assertIn(DS9, show[:show.index("<th>r (px)</th>") + 200])               # the table of positions
        zt = re.search(r"txt = 'Zero-aperture position:.*", show)
        self.assertTrue(zt and zt.group(0).count(DS9) >= 2, zt and zt.group(0)[:300])   # the zero aperture's and r = 2 px's


if __name__ == '__main__':
    unittest.main()
