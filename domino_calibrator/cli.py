"""Command line: a FITS image in; the photocentre-vs-aperture curve, the zero-aperture position and, from the user's own
values, an ADES record out.

    domino-calibrator image.fits ...     (installed with pip; the same as python -m domino_calibrator.cli image.fits ...)
    python -m domino_calibrator.cli image.fits [--x X --y Y] [--estimator G|M] [--radii 2.0:6.0:0.1]
                                        [--background annulus|VALUE] [--ext N] [--rms-noise N] [--curve out.csv]
                                        [--obstime YYYY-MM-DDThh:mm:ss.ssZ] [--exptime SECONDS]
                                        [--stn CODE --desig NAME --mode CCD|CMO|VID|TDI --astcat CATALOGUE
                                         --submitter NAME --measurer NAME [--measurer NAME ...] [--observer NAME ...]
                                         --telescope-design DESIGN --telescope-aperture METRES --telescope-detector DETECTOR
                                         [--observatory-name NAME]]

Coordinates are 0-based pixels (numpy: x = column, y = row; add 1 for ds9); without --x/--y the start is the brightest
5x5-smoothed pixel. A radius that does not converge has no position: the curve gives its reason, and the line is fitted
to the rest.
The tool writes an ADES record only from a start you give (--x and --y on the comet) and only when its checks pass: a
sound sky solution, every radius converged, and a bright, unclipped peak of more than one pixel well above the sky; a
star or a galaxy can pass these checks too, so telling a comet from a star is yours. A star inside the measuring ring pulls the answer toward it.

The ADES record (PSV, version 2022) needs a celestial WCS in the header (ICRS, or FK5 at J2000), a mid-exposure time
(from the header, or --obstime / --exptime) and every value in the record group; nothing defaults. Without them the
pixel answer still stands and the record is refused, with the reason. The record is a draft: check it with the MPC's
validator before submitting anything.
--rms-noise N: the zero-aperture scatter from N re-measurements with Gaussian noise drawn from the scatter of the comet's
own sky ring, 12-24 px from it (sky-limited approximation), carried through the WCS and printed beside the record in
arcsec at two significant figures, with how rough N redraws make it, and its correlation from 10 redraws on; the
estimated time is printed first. The record carries no rmsRA, rmsDec or rmsCorr from it: ADES defines rmsRA and rmsDec
as the random uncertainty of the whole reduction, and this scatter is the sky-noise part only, without the plate
solution's error. To report them, add your plate solution's random error to each in quadrature, write them at two
significant figures, and give ra and dec the decimals ADES's rule gives for them.
Exit codes: 0 when the measurement passed its gates (a record may still be refused for one of its values, with the
reason); 2 when a gate refused (no comet measured, or no sky position); 1 when it cannot measure at all.
"""
import argparse, csv, errno, os, re, sys, time, warnings
import numpy as np

from . import shrink, PUBLISHED_RADII
from .estimators import sigma_clipped_median
from .ades import ades_psv, celestial, pixel_to_radec, mid_exposure, sky_rms, blank, wcs_check, wcs_header, AST_CATS_DEPRECATED, WCS_NUMBER

REC_KEYS = ('stn', 'desig', 'mode', 'ast_cat', 'submitter', 'measurers', 'design', 'aperture', 'detector')
NOT_INHERITED = ("no WCS in the image's own HDU, and it does not say INHERIT = T, so the primary HDU's WCS is not taken for it "
                 "(the FITS convention): if the primary's WCS is the image's, add INHERIT = T to the image's header")
REC_FLAGS = dict(stn='--stn', desig='--desig', mode='--mode', ast_cat='--astcat', submitter='--submitter', measurers='--measurer',
                 design='--telescope-design', aperture='--telescope-aperture', detector='--telescope-detector')
CORR_MIN = 10        # redraws below which the scatter's correlation is not printed: from 3-5 it read -0.99
RMS_MAX = 1000       # noise redraws: 1e9 was a hang; one redraw of a 71-px cutout takes 0.1 s


def _line(s):
    """A reason as one line: astropy's message on two lines broke the output that the record is cut from."""
    return ' '.join(str(s).split())


def _r(v):
    """A radius as written: the fewest decimals, at least one, that give it back (2.05, not 2.0)."""
    v = float(v)
    for d in range(1, 11):
        s = '%.*f' % (d, v)
        if float(s) == v:
            return s
    return repr(v)


def _radii(s):
    """'FROM:TO:STEP' -> FROM, FROM + STEP, ..., TO; refused unless 0 < FROM <= TO, STEP > 0 and at most 1000 radii."""
    try:
        a, b, c = (float(v) for v in str(s).split(':'))
    except ValueError:
        raise ValueError('--radii %r is not FROM:TO:STEP' % (s,))
    words = '--radii %s: needs 0.5 <= FROM <= TO <= 1000 px, STEP >= 0.01 px and at most 1000 radii' % s
    if not (np.all(np.isfinite([a, b, c])) and 0.5 <= a <= b <= 1000 and c >= 0.01 and (b - a) / c <= 1000):
        raise ValueError(words)                      # tiny or huge radii, or a step that collapses them
    r = np.round(np.arange(a, b + 1e-9, c), 10)
    if r.size > 1000 or np.unique(r).size != r.size:
        raise ValueError(words)
    return r


def _start(img):
    """The automatic start, the page's rule (this averaged over every pixel with reflected edges, and read an
    infinity as 1.8e308): the brightest 5 x 5 sum among the pixels whose box lies inside the image, non-finite pixels counted
    as 0, summed in the page's order; the first in row order wins; (0, 0) when the image is smaller than 5 x 5."""
    v = np.where(np.isfinite(img), img, 0.0)
    ny, nx = v.shape
    if nx < 5 or ny < 5:
        return 0.0, 0.0
    s = np.zeros((ny - 4, nx - 4))
    for a in range(5):
        for b in range(5):
            s = s + v[a:a + ny - 4, b:b + nx - 4]
    iy, ix = np.unravel_index(np.argmax(s), s.shape)
    return float(ix + 2), float(iy + 2)


def _plane(h):
    """An HDU's pixels as a 2-D array, trivial leading axes squeezed (a one-plane cube is an image), or None."""
    d = getattr(h, 'data', None)
    if d is None or not hasattr(d, 'ndim') or d.ndim < 2 or getattr(d.dtype, 'names', None):
        return None
    if d.ndim > 2 and any(n != 1 for n in d.shape[:-2]):
        return None
    return d.reshape(d.shape[-2:])


def _cube(h, i):
    """': HDU i is a cube of N planes ...' when HDU i holds a cube (a colour image has 3 planes), else ''."""
    d = getattr(h, 'data', None)
    if d is None or not hasattr(d, 'ndim') or d.ndim < 3 or getattr(d.dtype, 'names', None):
        return ''
    return (': HDU %s is a cube of %d planes of %d x %d (a colour image?); save one plane as a 2-D image'
            % (i, int(np.prod(d.shape[:-2])), d.shape[-1], d.shape[-2]))


def _intact(h, i, size):
    """Raises ValueError, naming the fault, for an HDU whose header gives a size that is not a size (NAXIS, NAXISn, PCOUNT,
    GCOUNT: integers >= 0), or whose data the file ends before, as the page names them (astropy said
    "[Errno 22] Invalid argument", read PCOUNT -3100 as a 10 x 10 image of zeros, and "buffer is too small for requested
    array")."""
    from astropy.io import fits
    hh = h.header
    n = hh.get('NAXIS')
    keys = ['NAXIS'] + (['NAXIS%d' % a for a in range(1, n + 1)] if isinstance(n, int) and 0 <= n <= 999 else [])
    for k in keys + [k for k in ('PCOUNT', 'GCOUNT') if k in hh]:
        v = hh.get(k)
        if isinstance(v, bool) or not isinstance(v, (int, np.integer)) or v < 0 or (k == 'NAXIS' and v > 999):
            raise ValueError('HDU %d: %s = %s is not a size: the header is corrupt' % (i, k, v))
    if isinstance(h, fits.CompImageHDU):  # its header is the image's, not the compressed table's that the file holds
        return
    try:
        need = abs(int(hh.get('BITPIX', 8))) // 8 * int(hh.get('GCOUNT', 1)) * (
            int(hh.get('PCOUNT', 0)) + (int(np.prod([hh['NAXIS%d' % a] for a in range(1, n + 1)], dtype=np.int64)) if n else 0))
        loc = (h.fileinfo() or {}).get('datLoc')
    except (TypeError, ValueError, KeyError):
        return
    if need and loc is not None and size is not None and loc + need > size:
        raise ValueError('HDU %d: the file ends before its data does (%d of %d bytes): it is truncated' % (i, max(size - loc, 0), need))


PACKED = (b'\x1f\x8b', b'BZh', b'PK\x03\x04', b'\xfd7zXZ\x00')   # gzip, bzip2, zip, xz: astropy unpacks each as it reads


def _packed(path):
    """True for a file astropy decompresses as it reads it: its size on disk is not its data's, whose offsets are in the
    unpacked stream (every sound .fits.gz was refused as truncated, while the page sends one here)."""
    with open(path, 'rb') as f:
        head = f.read(6)
    return any(head.startswith(m) for m in PACKED)


def _raw_sizes(path):
    """The page's rules on the raw headers, for a file astropy fails to read: it seeks by NAXISn and PCOUNT while it reads
    the headers, so NAXIS3 = -100 raised "[Errno 22] Invalid argument" before any header could be checked.
    The first fault, named: a first header whose SIMPLE is not T; a BITPIX that is not one of FITS's six; a NAXIS, NAXISn,
    PCOUNT or GCOUNT that is not a size, an integer written as one (NAXIS1 = 64.0 is not: astropy's seek raised TypeError,
    as BITPIX 12 raised KeyError and SIMPLE = F AttributeError). None if every header read is sound."""
    with open(path, 'rb') as f:
        i, off = 0, 0
        while True:
            f.seek(off)
            cards, end = {}, False
            while not end:
                block = f.read(2880)
                if len(block) < 2880:
                    return None
                off += 2880
                for k in range(36):
                    c = block[80 * k:80 * k + 80].decode('ascii', 'replace')
                    if c[:8].strip() == 'END':
                        end = True
                        break
                    if c[8:10] == '= ':
                        cards.setdefault(c[:8].strip(), c[10:].split('/')[0].strip())
            if i == 0 and 'SIMPLE' not in cards:
                return None
            if i == 0 and cards['SIMPLE'] != 'T':                # the page's words (page/zeroap.js, parseFITS)
                return 'not a FITS file (it does not begin with SIMPLE = T)'
            if cards.get('BITPIX') not in ('8', '16', '32', '64', '-32', '-64'):
                return 'HDU %d: BITPIX %s, not a FITS pixel type (8, 16, 32, 64, -32 or -64)' % (i, cards.get('BITPIX', '(none)'))

            def size(k):
                v = cards.get(k, '')
                return int(v) if re.fullmatch(r'\+?[0-9]{1,18}', v) else None
            n = size('NAXIS')
            keys = ['NAXIS'] + ['NAXIS%d' % a for a in range(1, (n or 0) + 1)] + [k for k in ('PCOUNT', 'GCOUNT') if k in cards]
            for k in keys:
                if size(k) is None or (k == 'NAXIS' and size(k) > 999):
                    return 'HDU %d: %s = %s is not a size: the header is corrupt' % (i, k, cards.get(k, '(none)'))
            bitpix = abs(int(cards['BITPIX']))
            data = bitpix // 8 * (size('GCOUNT') if 'GCOUNT' in cards else 1) * (
                (size('PCOUNT') if 'PCOUNT' in cards else 0) + (int(np.prod([size('NAXIS%d' % a) for a in range(1, n + 1)], dtype=np.int64)) if n else 0))
            off += -(-data // 2880) * 2880
            i += 1


def _open(path, ext=None):
    """(image as float64 with BLANK pixels NaN, the image HDU's header, the primary header, notes); ValueError if the
    file holds no 2-D image, or if the HDU read is corrupt or cut short, naming the card where astropy's own
    error named none (KeyError, TypeError, AttributeError as the whole message)."""
    try:
        return _opened(path, ext)
    except (OSError, TypeError, KeyError, AttributeError, IndexError):
        why = _raw_sizes(path)
        if why:
            raise ValueError(why)
        raise


def _opened(path, ext=None):
    from astropy.io import fits
    notes = []
    size = None if _packed(path) else os.path.getsize(path)   # a packed file's end is found by unpacking it, not by its size
    with fits.open(path) as f:
        if ext is not None:
            try:
                h = f[ext]
            except (IndexError, KeyError):
                raise ValueError('the file has no HDU %r' % (ext,))
            _intact(h, ext, size)
            d = _plane(h)
            if d is None:
                raise ValueError('HDU %r holds no 2-D image' % (ext,) + _cube(h, ext))
        else:
            for i, h in enumerate(f):
                _intact(h, i, size)
                d = _plane(h)
                if d is not None:
                    break
            else:
                raise ValueError('no 2-D image in this file' + next((c for c in (_cube(h, i) for i, h in enumerate(f)) if c), ''))
        img = np.array(d, dtype=np.float64)
        hh = h.header
        # astropy turns BLANK into NaN when it converts integers to float, but keeps unsigned 16-bit (BZERO 32768),
        # the usual camera format, as integers: there a blank pixel read as 0.
        # A BLANK with no value is no BLANK, and one that is not an integer is none either, as astropy says: both crashed
        # the command line
        b = hh.get('BLANK') if 'BLANK' in hh else None
        if int(hh.get('BITPIX', 0)) > 0 and d.dtype.kind in 'iu' and not blank(b):
            if isinstance(b, (int, np.integer, float)) and not isinstance(b, bool) and float(b).is_integer():
                bv = int(b) * float(hh.get('BSCALE', 1.0)) + float(hh.get('BZERO', 0.0))
                m = d == bv
                if m.any():
                    img[m] = np.nan
                    notes.append('%d BLANK pixel%s: no data' % (int(m.sum()), '' if m.sum() == 1 else 's'))
            else:
                notes.append('BLANK %r is not an integer: no pixel is taken as blank' % (b,))
        return img, hh.copy(), f[0].header.copy(), notes


def _carried(card):
    """A fresh copy of a header card, as a merged header can hold it, or an exception: its value as astropy reads it
    (a card with no "= " in columns 1-10 is astropy's invalid card, whose raw text is no value: `EXPTIME =60.0` reads as
    the text '=60.0'), under a keyword a header can hold (not one with a NUL in it), and its comment only if that can be
    written too (a TAB in it cannot: the comment goes, the value stays, as the page reads it). The value is read before
    the image: reading card.image first makes astropy "fix" an unparsable card (`OBJECT  = C/2025 N1` became the value
    'C' and the comment '2025 N1', silently)."""
    from astropy.io import fits
    v = card.value
    if not card.image.startswith('HIERARCH') and not 0 <= card.image.find('= ') <= 8:
        raise ValueError('no value indicator')
    try:
        return fits.Card(card.keyword, v, card.comment)
    except Exception:
        return fits.Card(card.keyword, v)


def _merged(ihdr, phdr, notes=None, bad=None):
    """The primary header's cards under the image HDU's: where the time is read (as the page does). A card that cannot
    be carried (astropy cannot read it, reads it as invalid, or cannot write it back) is left out, from either header, and
    named in notes: one bad card once cost the whole answer, and once more through the write-back. A card with no value in the image HDU hides nothing of the primary's. bad: a list
    that receives the keywords left out."""
    from astropy.io import fits
    m, left = fits.Header(), []
    for hdr in (phdr, ihdr):
        for card in hdr.cards:
            k = card.keyword
            if k in ('', 'COMMENT', 'HISTORY', 'CONTINUE'):
                continue
            try:
                c = _carried(card)
            except Exception:
                left.append(k)
                if k in m:
                    m.remove(k, remove_all=True)
                continue
            if hdr is phdr:
                if k not in m:                               # the first of repeated cards, as astropy reads a header
                    m.append(c)
            elif not blank(c.value):
                if k in m:
                    m.remove(k, remove_all=True)
                m.append(c)
    left = sorted(set(left))
    if bad is not None:
        bad.extend(left)
    if left and notes is not None:
        said = [''.join(ch if ch.isprintable() else '\\x%02x' % ord(ch) for ch in k) for k in left]
        notes.append('header card%s %s could not be read, and %s left out' % ('s' if len(left) > 1 else '', ', '.join(said),
                                                                             'were' if len(left) > 1 else 'was'))
    return m


def _get(hdr, key, unreadable=None):
    """hdr.get(key), or `unreadable` when the card's text cannot be read (astropy's VerifyError)."""
    try:
        return hdr.get(key)
    except Exception:
        return unreadable


def _two_axes(hdr):
    """A copy of a cube's header with only its first two axes: NAXIS 2, and no card of a third or later axis."""
    h = hdr.copy()
    for k in list(h.keys()):
        m = re.match(r'^(NAXIS|CTYPE|CRPIX|CRVAL|CDELT|CUNIT|CROTA|CNAME|CRDER|CSYER)(\d+)$', k) or re.match(r'^(CD|PC)(\d+)_(\d+)$', k)
        if m and any(int(g) > 2 for g in m.groups()[1:]):
            h.remove(k, remove_all=True)
    h['NAXIS'] = 2
    if 'WCSAXES' in h:
        h['WCSAXES'] = 2
    return h


def _raw_value(hdr, key):
    """A card's value as written in the file, for a card astropy cannot read (its quotes and comment left out)."""
    for card in hdr.cards:
        if card.keyword == key:
            return card.image[10:].split('/')[0].strip().strip("'").strip()
    return ''


def load_image(path, ext=None):
    """The image to measure as float64 (a one-plane cube squeezed; BLANK pixels NaN), the header it is read with (the
    image HDU's cards over the primary's; a card that cannot be read left out) and notes. Raises ValueError if the file
    holds no 2-D image."""
    img, ihdr, phdr, notes = _open(path, ext)
    return img, _merged(ihdr, phdr, notes), notes

# ---------------------------------------------------------------- a comet measured
# No record unless a comet was measured: an audit found records written from a constant image, pure noise, a
# saturated or brighter star taken by the automatic start, and starts a few pixels off (a fit on 2 to 37 of 41 radii, up to
# 23 px away, and not repeatable from run to run: C1.25d). Each value below was measured before it was set, on the study's
# 30 frames with G and M: every radius converged; the fit ended 0.15-0.78 px from its
# start; the peak stood 60-94 times the sky's noise above the sky (pure noise: 3.8); one pixel held the peak's value (a
# saturated star: 15). The page applies the same rules, in the same words (page/zeroap.js, cometCheck).
START_MAX = 1.5          # px, from the start to the zero-aperture position
SNR_MIN = 10.0           # the peak over the sky, in units of the sky's noise
TIES_MAX = 3             # this many pixels sharing the peak's value is a clipped top
SINGLE_FRAC = 0.1                   # a peak whose four neighbours hold under this share of its height above the sky is one pixel
SKY_IN, SKY_OUT, SKY_MIN = 12.0, 24.0, 50    # the sky ring (px) about the position, and the fewest finite pixels in it
OTHER_FRAC = 0.2         # the automatic start: another source this bright, of the one taken, makes it ambiguous
DS9 = '0-based; add 1 for ds9'   # beside every printed position (0-based kept)


def _ceiling(hdr):
    """The data's largest value when its pixels are integers (BITPIX > 0), through BSCALE and BZERO; else None."""
    try:
        bp = int(hdr.get('BITPIX', 0))
    except (TypeError, ValueError):
        return None
    if bp <= 0:
        return None
    bs, bz = hdr.get('BSCALE', 1.0), hdr.get('BZERO', 0.0)
    try:
        bs, bz = float(bs if not blank(bs) else 1.0), float(bz if not blank(bz) else 0.0)
    except (TypeError, ValueError):
        return None
    top = 255 if bp == 8 else 2 ** (bp - 1) - 1
    return top * bs + bz if bs > 0 else None


def _level(hdr):
    """SATURATE or SATLEVEL, when the header gives one as a number."""
    for k in ('SATURATE', 'SATLEVEL'):
        v = hdr.get(k) if k in hdr else None
        try:
            v = float(v)
        except (TypeError, ValueError):
            continue
        if np.isfinite(v):
            return k, v
    return None


def _box5(v):
    """The 5 x 5 sums the automatic start compares (_start), over the pixels whose box lies inside the image."""
    ny, nx = v.shape
    s = np.zeros((ny - 4, nx - 4))
    for a in range(5):
        for b in range(5):
            s = s + v[a:a + ny - 4, b:b + nx - 4]
    return s


def comet_check(img, o, start, auto, hdr):
    """None when a comet was measured; else why not, in the page's words (page/zeroap.js, cometCheck)."""
    ok = np.asarray(o['ok'], bool)
    if not ok.all():
        return 'only %d of %d radii converged: the fit had too little to hold' % (int(ok.sum()), ok.size)
    x0, y0 = float(o['x0']), float(o['y0'])
    d = float(np.hypot(x0 - start[0], y0 - start[1]))
    if d > START_MAX:
        return 'the fit ended %.1f px from its start: start on the comet, within %.1f px of where the fit ends' % (d, START_MAX)
    ny, nx = img.shape
    i0, i1 = max(int(np.floor(y0 - SKY_OUT)), 0), min(int(np.ceil(y0 + SKY_OUT)) + 1, ny)
    j0, j1 = max(int(np.floor(x0 - SKY_OUT)), 0), min(int(np.ceil(x0 + SKY_OUT)) + 1, nx)
    win = img[i0:i1, j0:j1]
    yy, xx = np.mgrid[i0:i1, j0:j1]
    rr = np.hypot(xx - x0, yy - y0)
    fin = np.isfinite(win)
    core = win[fin & (rr <= max(o['radii']))]
    if core.size == 0:
        return 'no finite pixel within %g px of it: nothing was measured' % max(o['radii'])
    pk = float(core.max())
    ties = int(np.sum(core == pk))
    top, lev = _ceiling(hdr), _level(hdr)
    if top is not None and pk >= top:
        return "its peak is clipped (at the data's ceiling, %s): a saturated star or core is not measured" % ('%g' % top)
    if lev is not None and pk >= lev[1]:
        return 'its peak is clipped (at %s, %s): a saturated star or core is not measured' % (lev[0], '%g' % lev[1])
    if ties >= TIES_MAX:
        return 'its peak is clipped (%d pixels share its value): a saturated star or core is not measured' % ties
    sky = win[fin & (rr > SKY_IN) & (rr <= SKY_OUT)]
    if sky.size < SKY_MIN:
        return 'fewer than %d sky pixels %g-%g px from it: nothing to tell it from noise' % (SKY_MIN, SKY_IN, SKY_OUT)
    med = float(np.median(sky))
    sig = 1.4826 * float(np.median(np.abs(sky - med)))
    if sig == 0:                             # half the ring or more holds one value: the MAD is 0
        sig = float(np.std(sky))
        if sig == 0:
            return 'its sky ring is flat (every pixel %g-%g px from it holds one value): nothing to tell it from noise; measure the image as it came from the camera' % (SKY_IN, SKY_OUT)
    exc = pk - med
    if exc <= 0 or (sig > 0 and exc / sig < SNR_MIN):
        return ('its peak stands %.1f times the sky noise above the sky, under %g: too faint to take as measured'
                % ((exc / sig) if sig > 0 else 0.0, SNR_MIN))
    pi, pj = np.unravel_index(np.argmax(np.where(fin & (rr <= max(o['radii'])), win, -np.inf)), win.shape)
    nb = [win[pi + a, pj + b] for a, b in ((-1, 0), (1, 0), (0, -1), (0, 1))     # the peak pixel's four neighbours
          if 0 <= pi + a < win.shape[0] and 0 <= pj + b < win.shape[1] and np.isfinite(win[pi + a, pj + b])]
    if nb and float(np.mean(nb)) - med < SINGLE_FRAC * exc:
        return 'its peak is a single pixel (its four neighbours hold under a tenth of its height above the sky): a hot pixel or a cosmic ray, not a source; start on the comet'
    if auto and nx >= 5 and ny >= 5:
        s = _box5(np.where(np.isfinite(img), img, med) - med)     # s[i, j] is the box about pixel (j + 2, i + 2)
        a0, a1 = max(int(np.floor(y0 - SKY_IN)) - 2, 0), min(int(np.ceil(y0 + SKY_IN)) - 1, s.shape[0])
        b0, b1 = max(int(np.floor(x0 - SKY_IN)) - 2, 0), min(int(np.ceil(x0 + SKY_IN)) - 1, s.shape[1])
        sub = s[a0:a1, b0:b1]
        gy, gx = np.mgrid[a0:a1, b0:b1]
        here = np.hypot(gx + 2 - x0, gy + 2 - y0) <= SKY_IN
        taken = float(sub[here].max()) if here.any() else 0.0
        sub[here] = -np.inf
        iy, ix = np.unravel_index(np.argmax(s), s.shape)
        other = float(s[iy, ix])
        if taken > 0 and other >= OTHER_FRAC * taken and (sig == 0 or other / (5 * sig) >= SNR_MIN):
            return ("the automatic start took the brightest source, and another at least a fifth as bright is at (%d, %d; %s): "
                    "give the comet's x and y" % (ix + 2, iy + 2, DS9))
    return None


def _ring(img, x0, y0):
    """The finite pixels SKY_IN < r <= SKY_OUT px from (x0, y0): the comet's own sky ring, the same pixels comet_check reads
    as the sky (the scatter's noise came from the image's 5-px border, so a cutout of the same
    pixels wrote rmsRA ten times the whole frame's)."""
    ny, nx = img.shape
    i0, i1 = max(int(np.floor(y0 - SKY_OUT)), 0), min(int(np.ceil(y0 + SKY_OUT)) + 1, ny)
    j0, j1 = max(int(np.floor(x0 - SKY_OUT)), 0), min(int(np.ceil(x0 + SKY_OUT)) + 1, nx)
    win = img[i0:i1, j0:j1]
    yy, xx = np.mgrid[i0:i1, j0:j1]
    rr = np.hypot(xx - x0, yy - y0)
    return win[np.isfinite(win) & (rr > SKY_IN) & (rr <= SKY_OUT)]


def _duration(t):
    """A time in seconds, as a person reads it."""
    return '%.1f s' % t if t < 10 else ('%.0f s' % t if t < 90 else ('%.0f min' % (t / 60) if t < 5400 else '%.1f h' % (t / 3600)))


def measure_file(path, x=None, y=None, estimator='G', radii=PUBLISHED_RADII, background='annulus', ext=None,
                 rms_noise=0, seed=1, ades=None, obstime=None, exptime=None, progress=None):
    """Measure one image. The curve and the zero-aperture position always; the sky position, the time, the scatter and
    the ADES record when each can be made honestly, else its reason (sky_error, time_error, rms_error, ades_error).
    ades: the user's values for the record (stn, desig, mode, ast_cat, submitter, measurers, design, aperture,
    detector; observers and observatory_name optional). Raises ValueError only when the file holds no image, or when an
    argument is not one (a start that is not a finite position, say); every header stage has its own reason instead.
    progress: called with one line, the estimated time of the --rms-noise redraws, before they start."""
    from astropy.io import fits
    if (x is None) != (y is None):           # one of them fell silently to the automatic start
        raise ValueError('the start needs both x and y (--x and --y go together; give neither for the automatic start)')
    img, ihdr, phdr, notes = _open(path, ext)
    bad = []
    hdr = _merged(ihdr, phdr, notes, bad)
    auto = x is None
    if auto:
        x, y = _start(img)
    bk = background if background == 'annulus' else float(background)
    t0 = time.perf_counter()
    o = shrink(img, x, y, radii=radii, estimator=estimator, background=bk)
    t_fit = time.perf_counter() - t0
    res = dict(curve=o, x0=o['x0'], y0=o['y0'], x2=o['x2'], y2=o['y2'], start=(x, y), notes=notes)
    if np.isfinite(o['x0']) and np.isfinite(o['y0']):       # no record unless a comet was measured
        why = comet_check(img, o, (x, y), auto, hdr if _get(ihdr, 'INHERIT') is True else ihdr)   # the primary's SATURATE too
    else:
        why = 'only %d of %d radii converged: the fit had too little to hold' % (int(np.sum(o['ok'])), len(o['ok']))
    if why:
        res['comet_error'] = why
    own, inherit = not blank(_get(ihdr, 'CTYPE1', 'x')), _get(ihdr, 'INHERIT') is True   # a blank CTYPE1 is no WCS there
    whdr = (ihdr if own or not inherit else phdr).copy()     # the primary's WCS only with INHERIT = T
    src = ihdr if own or not inherit else phdr
    lost = [k for k in bad if WCS_NUMBER.match(k) and k in src]   # a WCS number that cannot be read is not left out silently:
    for k in bad:                                            # the WCS would be read without it
        if k in whdr:
            whdr.remove(k, remove_all=True)
    whdr = wcs_header(whdr)                                  # a D exponent read as the header reads it
    if img.ndim == 2 and int(_get(whdr, 'NAXIS', 2) or 2) > 2:   # a one-plane cube, squeezed: its WCS on the image's two axes
        whdr = _two_axes(whdr)
    ctype = [k for k in bad if k in ('CTYPE1', 'CTYPE2') and k in src]
    if ctype:                                    # its text is not a FITS value (exit 1, the pixel answer lost)
        res['sky_error'] = ('the WCS card %s could not be read, so the WCS is unknown: fix the card, or plate-solve the image again'
                            % ctype[0])
    elif blank(whdr.get('CTYPE1')) and not own and not inherit and not blank(phdr.get('CTYPE1')):
        res['sky_error'] = NOT_INHERITED
    elif blank(whdr.get('CTYPE1')):              # named no remedy
        res['sky_error'] = ('no WCS in the header: the image is not plate-solved; plate-solve it (with astrometry.net or '
                            'ASTAP, say) and measure the solved file')
    elif lost:                                   # the page's words (page/zeroap.js, makeWCS)
        res['sky_error'] = "the WCS card %s = '%s' is not a number" % (lost[0], _raw_value(src, lost[0]))
    else:
        try:                                             # a header stage never costs the pixel answer
            with fits.open(path) as f:                   # open while the WCS is read: lookup tables (HST's CPDIS, D2IMDIS) sit in its extensions (1.18)
                w, said = celestial(whdr, fobj=f)
                if np.isfinite(o['x0']) and np.isfinite(o['y0']):
                    wcs_check(whdr, w, said, o['x0'], o['y0'], fobj=f)   # a broken WCS gives no sky position
                    res['radec'] = pixel_to_radec(whdr, o['x0'], o['y0'], fobj=f)
            notes += ['WCS: ' + n for n in said]
            if 'radec' not in res:
                res['sky_error'] = 'no zero-aperture position (fewer than 2 radii converged)'
        except Exception as e:
            res['sky_error'] = _line(str(e) or type(e).__name__)
    try:
        res['time'], res['time_note'] = mid_exposure(hdr, obstime=obstime, exptime=exptime)
    except Exception as e:
        res['time_error'] = _line(str(e) or type(e).__name__)
        res['time_helps'] = getattr(e, 'helps', ('obstime',))   # what gives the time instead
    if rms_noise:
        try:
            nr = int(rms_noise)
            counted = nr == rms_noise and 3 <= nr <= RMS_MAX
        except (TypeError, ValueError, OverflowError):
            counted = False
        if not counted:     # -1 raised AxisError; 1 or 2 read as the image's fault, 1e9 was a hang
            res['rms_error'] = '--rms-noise %s: the scatter takes 3 to %d noise redraws (0 for none)' % (rms_noise, RMS_MAX)
        elif not np.isfinite(o['x0']):
            res['rms_error'] = 'no zero-aperture position to scatter'
        elif _ring(img, o['x0'], o['y0']).size < SKY_MIN:   # the comet's own sky ring, the gate's
            res['rms_error'] = 'fewer than %d finite sky pixels %g-%g px from the comet: no noise level' % (SKY_MIN, SKY_IN, SKY_OUT)
        else:
            sky = _ring(img, o['x0'], o['y0'])
            rng = np.random.default_rng(seed)
            med = sigma_clipped_median(sky)
            sig = 1.4826 * np.median(np.abs(sky - med))
            res['noise'] = (float(sig), int(sky.size))
            if not (np.isfinite(sig) and sig > 0):           # a constant sky gave rms 0, and the record was refused
                res['rms_error'] = ('the sky ring %g-%g px from the comet has no scatter (its pixels are all alike): no noise '
                                    'level to draw from' % (SKY_IN, SKY_OUT)
                                    if np.ptp(sky) == 0 else     # a MAD of 0 is not "all alike"
                                    "the sky ring's median absolute deviation is 0 (at least half its pixels share one value, "
                                    'as a quantised low sky gives): no noise level to draw from')
            else:
                if progress:                                 # the time first, before the redraws
                    t0 = time.perf_counter()
                    np.random.default_rng(0).normal(0.0, sig, img.shape)   # a throwaway draw: the scatter's own stream is untouched
                    each = t_fit + time.perf_counter() - t0
                    progress('# --rms-noise %d: about %s (%d redraws, each about %s), starting now' % (
                        nr, _duration(nr * each), nr, _duration(each)))
                pts = []
                for _ in range(nr):
                    oo = shrink(img + rng.normal(0.0, sig, img.shape), o['x0'], o['y0'], radii=radii, estimator=estimator, background=bk)
                    pts.append((oo['x0'], oo['y0']))
                pts = np.array(pts)
                fin = np.all(np.isfinite(pts), axis=1)
                if fin.sum() < 3:
                    res['rms_error'] = 'fewer than 3 of %d noise redraws gave a position' % len(pts)
                else:
                    cov = np.cov(pts[fin].T, ddof=1)
                    res['cov_px'], res['rms_n'] = cov, (int(fin.sum()), len(pts))
                    res['sd_px'] = (float(np.sqrt(cov[0, 0])), float(np.sqrt(cov[1, 1])))
                    if 'radec' in res:                       # x's scatter was written as rmsRA whatever the WCS
                        try:
                            with fits.open(path) as f:
                                res['rms'] = sky_rms(whdr, o['x0'], o['y0'], cov, fobj=f)
                        except Exception as e:
                            res['rms_error'] = _line('the scatter could not be carried to the sky: %s' % (str(e) or type(e).__name__))
    a = dict(ades or {})
    need = []
    if 'comet_error' in res:                 # first: without a comet, the rest does not matter
        need.append('a comet measured (%s)' % res['comet_error'])
    if 'radec' not in res:
        need.append('a sky position (%s)' % res.get('sky_error'))
    if 'time' not in res:                    # --exptime was offered for every time refusal
        h = res.get('time_helps', ('obstime',))
        need.append('a mid-exposure time (%s%s)' % (res.get('time_error'), '' if not h else '; give it with --obstime' + (
            ', or the exposure with --exptime' if 'exptime' in h else '')))
    if auto:                                 # a record only from a start the observer gives
        need.append('a start you give: give --x and --y on the comet to get a record (the automatic start takes the brightest source, which may be a star)')
    missing = ['%s (%s)' % ('astCat' if k == 'ast_cat' else k, REC_FLAGS[k]) for k in REC_KEYS if not a.get(k)]
    if missing:
        need.append("the record's values for %s" % ', '.join(missing))
    if need:
        res['ades_error'] = 'needs ' + '; '.join(need)
    else:
        fitted = np.asarray(o['radii'])[np.asarray(o['ok'], bool)]   # the radii the line went through, not those asked for (4.3)
        try:
            # no rmsRA, rmsDec or rmsCorr from the sky noise: ADES's are the whole reduction's random uncertainty, and the
            # record never presents the sky noise alone as that; _print prints it beside
            res['ades'] = ades_psv(res['radec'][0], res['radec'][1], res['time'],
                                   remarks='zero-aperture extrapolated (%s, %d of %d radii, r %s-%s px)' % (
                                       estimator, fitted.size, len(o['radii']), _r(fitted.min()), _r(fitted.max())), **a)
            if a['ast_cat'] in AST_CATS_DEPRECATED:
                notes.append("astCat %s is on the MPC's deprecated list" % a['ast_cat'])
        except ValueError as e:
            res['ades_error'] = _line(e)
    return res


def version_text():
    from . import __version__, __credit__
    return 'domino-calibrator %s\n%s' % (__version__, __credit__)


class _Parser(argparse.ArgumentParser):
    """argparse's parser, but a usage error exits 1, "cannot measure at all", not argparse's 2, which here means that the gates
    refused (0 when the measurement passed its gates, 2 when they refused, 1 when it cannot
    measure at all)."""
    def error(self, message):
        self.print_usage(sys.stderr)
        self.exit(1, '%s: error: %s\n' % (self.prog, message))


class _Version(argparse.Action):
    """--version: the version and the credit, as written (argparse's own version action re-wraps its text)."""
    def __init__(self, option_strings, dest, **kw):
        super().__init__(option_strings, dest, nargs=0, help='print the version and the credit, and exit')

    def __call__(self, parser, namespace, values, option_string=None):
        print(version_text())
        parser.exit(0)


def main(argv=None):
    ap = _Parser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter, epilog=version_text())
    ap.add_argument('--version', action=_Version)
    ap.add_argument('fits'); ap.add_argument('--x', type=float); ap.add_argument('--y', type=float)
    ap.add_argument('--estimator', default='G', choices=['G', 'M']); ap.add_argument('--radii', default='2.0:6.0:0.1')
    ap.add_argument('--background', default='annulus'); ap.add_argument('--ext', type=int)
    ap.add_argument('--rms-noise', type=int, default=0); ap.add_argument('--curve')
    ap.add_argument('--obstime', help='the mid-exposure, UTC (overrides the header)')
    ap.add_argument('--exptime', type=float, help='the exposure in seconds, when the header lacks it')
    g = ap.add_argument_group('the ADES record', 'every value is required for a record; nothing defaults')
    g.add_argument('--stn', help='the MPC observatory code'); g.add_argument('--desig', help='e.g. 3I, 1P or C/2025 N1')
    g.add_argument('--mode', help='CCD, CMO (CMOS), VID or TDI')
    g.add_argument('--astcat', help="the plate solution's catalogue as the MPC lists it, e.g. Gaia3")
    g.add_argument('--submitter', help='initials, then surname, as ADES asks: e.g. "A. N. Observer"')
    g.add_argument('--measurer', action='append', help='initials, then surname; once for each measurer')
    g.add_argument('--observer', action='append', help='initials, then surname; once for each observer')
    g.add_argument('--telescope-design', help='e.g. Reflector'); g.add_argument('--telescope-aperture', help='metres')
    g.add_argument('--telescope-detector', help='e.g. CCD or CMOS'); g.add_argument('--observatory-name')
    A = ap.parse_args(argv)
    enc = (getattr(sys.stdout, 'encoding', None) or '').lower().replace('-', '').replace('_', '')
    if enc and enc != 'utf8' and hasattr(sys.stdout, 'reconfigure'):
        try:                         # the record is UTF-8: a Windows code page lost it to a name outside ASCII
            sys.stdout.reconfigure(encoding='utf-8')
        except Exception:
            pass
    rec = dict(stn=A.stn, desig=A.desig, mode=A.mode, ast_cat=A.astcat, submitter=A.submitter, measurers=A.measurer,
               design=A.telescope_design, aperture=A.telescope_aperture, detector=A.telescope_detector)
    if A.observer:
        rec['observers'] = A.observer
    if A.observatory_name:
        rec['observatory_name'] = A.observatory_name
    try:
        radii = _radii(A.radii)
        if A.background == 'annulus':
            bk = 'annulus'
        else:
            try:
                bk = float(A.background)
            except ValueError:
                raise ValueError("--background %r is neither 'annulus' nor a number" % A.background)
        with warnings.catch_warnings(), np.errstate(all='ignore'):   # a start off the comet: its reasons, not numpy's
            warnings.simplefilter('ignore', RuntimeWarning)
            r = measure_file(A.fits, A.x, A.y, A.estimator, radii, bk, A.ext, A.rms_noise, ades=rec, obstime=A.obstime,
                             exptime=A.exptime, progress=lambda line: print(line, file=sys.stderr, flush=True))
    except Exception as e:           # a stranger's file gets a sentence, not a traceback
        why = str(e) or ('out of memory: the image (and any --rms-noise redraws of it) did not fit; a cutout around the comet '
                         'needs far less' if isinstance(e, MemoryError) else 'no message of its own')   # MemoryError has none
        return _say(lambda: print('# cannot measure: %s' % _line(why if isinstance(e, (ValueError, OSError)) else '%s: %s' % (type(e).__name__, why))), 1)
    # 2 when the gates refused (no comet measured, or the sky position refused), else 0
    return _say(lambda: _print(A, r), 2 if ('comet_error' in r or 'sky_error' in r) else 0)


def _say(printing, code):
    """Print, and return the exit code; a reader that closes the pipe early (| head) ends it quietly, with the same code
    (a BrokenPipeError traceback; the recipe is Python's own, in its signal module's documentation).
    Windows reports the closed pipe as OSError EINVAL, not BrokenPipeError (the CI's first run on Windows)."""
    try:
        printing()
        sys.stdout.flush()
    except OSError as e:
        if not isinstance(e, BrokenPipeError) and e.errno != errno.EINVAL:
            raise
        try:                         # Python flushes stdout again at exit: send what is left to devnull, not to the closed pipe
            os.dup2(os.open(os.devnull, os.O_WRONLY), sys.stdout.fileno())
        except (OSError, ValueError, AttributeError):
            pass
    return code


def _two(v):
    """v at two significant figures, as ADES asks for an uncertainty, written plainly (0.0012, 1.2, 12)."""
    if not (np.isfinite(v) and v > 0):
        return '%g' % v
    return '%.*f' % (max(0, 1 - int(np.floor(np.log10(float('%.2g' % v))))), float('%.2g' % v))


def _print(A, r):
    """The measurement as the command line prints it, the ADES record last."""
    o = r['curve']
    print('# start (%.2f, %.2f; %s) | estimator %s | radii %s-%s px (%d) | unconverged radii %d' % (
        r['start'] + (DS9, A.estimator, _r(o['radii'][0]), _r(o['radii'][-1]), len(o['radii']), o['nbad'])))
    for n in r['notes']:
        print(_line('# WCS note: %s' % n[5:] if n.startswith('WCS: ') else '# note: %s' % n))
    print('# r_px  x  y   (x and y %s; a radius that did not converge has no position; its reason follows)' % DS9)
    for rr, xx, yy, ok, why in zip(o['radii'], o['x'], o['y'], o['ok'], o['reason']):
        print('%.2f %.4f %.4f' % (rr, xx, yy) + ('' if ok else '  # unconverged: %s' % why))
    r2 = o['radii'][int(np.argmin(np.abs(np.asarray(o['radii']) - 2.0)))]   # shrink's x2: the radius nearest 2 px
    print('# zero aperture: x %.4f y %.4f (%s) | slope per px of radius: (%+.5f, %+.5f) | r=%s: (%.4f, %.4f; %s)' % (   # named
        o['x0'], o['y0'], DS9, o['sx'], o['sy'], '2' if abs(r2 - 2.0) < 1e-9 else _r(r2), o['x2'], o['y2'], DS9))   # when not 2 (D1.2)
    if 'radec' in r:                 # printed only inside a record before, and a record needs nine values
        print('# sky (ICRS): RA %.7f, Dec %+.7f deg, the zero-aperture position' % r['radec'])
    else:
        print('# no sky position: %s' % _line(r.get('sky_error')))
    if 'sd_px' in r:
        print('# zero-aperture scatter from %d of %d noise redraws: (%.4f, %.4f) px' % (r['rms_n'] + r['sd_px']))
    if 'rms' in r:                   # the sky scatter beside the record, not in it
        n = r['rms_n'][0]
        print('# sky-noise scatter on the sky, from %d of %d redraws: RA*cos(Dec) %s", Dec %s"' % (
            r['rms_n'] + (_two(r['rms'][0]), _two(r['rms'][1]))) + ', good to about %d%%' % round(100 / np.sqrt(2 * (n - 1))) + (
            ', correlation %+.2f' % r['rms'][2] if n >= CORR_MIN else ', no correlation from fewer than %d redraws' % CORR_MIN))
        print("# that is the sky noise only, not in the record: ADES's rmsRA and rmsDec are the whole reduction's random "
              "uncertainty. To report them, add your plate solution's random error to each in quadrature, write them at "
              "two significant figures, and give ra and dec the decimals ADES's rule gives for them")
    if 'rms_error' in r:
        print('# no scatter: %s' % _line(r['rms_error']))
    if 'time' in r:
        print('# time: %s (%s)' % (r['time'], _line(r['time_note'])))
    if A.curve:
        try:
            same = os.path.exists(A.curve) and os.path.samefile(A.curve, A.fits)
        except OSError:
            same = False
        if same:                     # the input's own path truncated the image into a CSV
            print('# no curve file: --curve %s is the input image itself, and it was not written over' % A.curve)
        else:
            try:                     # a traceback here cost the record, which prints after it
                with open(A.curve, 'w', newline='', encoding='utf-8') as f:
                    w = csv.writer(f, lineterminator='\n')
                    w.writerow(['r_px', 'x', 'y', 'ok', 'reason'])
                    for rr, xx, yy, ok, why in zip(o['radii'], o['x'], o['y'], o['ok'], o['reason']):
                        w.writerow(['%.2f' % rr, '%.6f' % xx, '%.6f' % yy, int(bool(ok)), why])
            except OSError as e:     # the path as the user gave it: an OSError quotes it, with Windows' backslashes doubled
                print('# no curve file: %s: %s' % (_line(e.strerror or type(e).__name__), A.curve))
    if 'ades' in r:                  # the record comes last, so that it can be cut from the output as it is
        print("# ADES (a draft: check it with the MPC's validator before submitting):")
        print(r['ades'], end='')
    else:
        print('# no ADES record: %s' % _line(r['ades_error']))


if __name__ == '__main__':
    sys.exit(main())
