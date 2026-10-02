"""An ADES record (PSV, version 2022) for a comet position, and the sky position and time it needs.

The pixel position goes through the image's own WCS (astropy, origin 0: pixel centres on integers, as everywhere in
this package). What the record says comes from the header or from the user, never from a default: a record that cannot
be made honestly is refused with the reason, and the pixel answer stands without it
(the hardening round's record of 27 Sept 2026, not in this repository). The judge is the MPC's own validator (IAU-ADES/ades-master: psvtoxml,
valsubmit, xsd/submit.xsd); this module checks beforehand what it can: the schema's patterns (xsd/submit.xsd at
ades-master 39ae5a9b13c37f7256a39b457e04433c854ed4dd, read 27 Sept 2026) and the MPC's lists of modes and catalogues (ADESFieldValues.html, mode.json and
astCat_photCat.json, read 27 Sept 2026, 23:35 UTC), whose unlisted values "will cause a batch to be rejected".
Nothing here sends anything anywhere. (astropy's time arithmetic reads a local leap-second table, astropy-iers-data;
once that table expires, astropy itself may try to download a newer one.)
"""
import contextlib, logging, math, re, unicodedata, warnings

import numpy as np

__all__ = ['pixel_to_radec', 'celestial', 'sky_rms', 'mid_exposure', 'mid_exposure_iso', 'designation_field', 'ades_psv',
           'blank', 'card_value', 'MODES', 'AST_CATS', 'AST_CATS_DEPRECATED', 'NO_FIXED_POSITION', 'SOFTWARE']

VERSION = '2022'
# the schema's patterns (xsd/submit.xsd); an XML Schema pattern matches the whole value, hence fullmatch
PERMID = r'\d+([IPD](-[A-Z]{1,2})?)?|((Mars|Jupiter|Saturn|Uranus|Neptune) \d{1,3}|\(\d+\) \d{1,3})'
PROVID = (r'\d{4} [A-HJ-Y][A-HJ-Z]\d*|\d{4} (P-L|T-[123])|[ADCPX]/\d{4} [A-Z]{1,2}\d*(-[A-Z])?|'
          r'S/\d{4} ((M|J|S|U|N)|\((\d+|\d{4} [A-HJ-Y][A-HJ-Z]?\d+)\)) \d+',     # BaseProvIDType
          r'A[89]\d{2} [A-HJ-Y][A-HJ-Z]')                                        # OldProvIDType
STATION = r'[A-Za-z0-9_]{3,4}'
POSDEC = r'(0|([1-9][0-9]*))(\.[0-9]*)?'
OBSTIME = r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z'
# the MPC's lists: the current modes for an image (OCC, occultations, and the deprecated modes left out), and every
# listed catalogue (a deprecated one is accepted, with a note: the MPC lists it, and asks observers to move on)
MODES = ('CCD', 'CMO', 'VID', 'TDI')
AST_CATS = ('Gaia_Int', 'PS1_DR2', 'PS1_DR1', 'ATLAS2', 'Gaia3', 'Gaia3E', 'Gaia2', 'Gaia1', 'Gaia2016', 'URAT1', 'UCAC5',
            'UCAC4', 'PPMXL', 'NOMAD', '2MASS', 'UBSC')
AST_CATS_DEPRECATED = ('UCAC3', 'UCAC2', 'UCAC1', 'USNOB1', 'USNOA2', 'USNOSA2', 'USNOA1', 'USNOSA1', 'Tyc2', 'Tyc1', 'Hip2',
                       'Hip1', 'ACT', 'GSCACT', 'GSC2.3', 'GSC2.2', 'GSC1.2', 'GSC1.1', 'GSC1.0', 'GSC', 'SDSS8', 'SDSS7',
                       'CMC15', 'CMC14', 'SSTRC4', 'SSTRC1', 'MPOSC3', 'PPM', 'AC', 'SAO1984', 'SAO', 'AGK3', 'FK4', 'ACRS',
                       'LickGas', 'Ida93', 'Perth70', 'COSMOS', 'Yale', 'ZZCAT', 'IHW', 'GZ', 'UNK')
TIME_SCALES = {'UTC': 'utc', 'UT': 'utc', 'TT': 'tt', 'TDT': 'tt', 'TAI': 'tai', 'IAT': 'tai'}
# ADES, read at source (the ADES description of 16 Mar 2026 in ades-master 39ae5a9b13c37f7256a39b457e04433c854ed4dd;
# xsd/submit.xsd):
# - the MPC's observatory codes with no fixed position, space-based or roving (ObsCodesF.html, read 1 Oct 2026 11:55:11 UTC:
#   runs/MPC_OBSCODES_NO_POSITION_2026-10-01.json). For them ADES's Location Group "must be present", and this tool does not
#   write it, so they get no record. A code the MPC adds later is not here.
NO_FIXED_POSITION = ('245', '247', '249', '250', '258', '270', '273', '274', '275', '288', '289', '311', '313', '314', '315',
                     '332', '335', '336', '338', '339', 'C49', 'C50', 'C51', 'C52', 'C53', 'C54', 'C55', 'C56', 'C57', 'C58', 'C59')
# - ra and dec "DP = CEILING(1 - LOG10(SIGMA))" decimals from the uncertainty, at most the schema's 9; without one, a fixed
#   default far below any ground uncertainty: 6 decimals, 0.0036" (ADES's own example for 0.036-0.36")
DECIMALS_MAX, DECIMALS_DEFAULT = 9, 6
# - the software, in ADES's place for it (Table 18: software, astrometry, "Description of software used for astrometry"). ADES
#   has no place of its own for the plate solution's program, so the line says which part this tool did.
SOFTWARE = "domino-calibrator %s (zero-aperture position, through the image's own plate solution)"


class TimeRefused(ValueError):
    """A time that cannot be given, and what the user can give instead: helps holds 'obstime'
    and/or 'exptime', the values that would give the time; () when the user's own value is what is refused."""
    def __init__(self, msg, helps=('obstime',)):
        super().__init__(msg)
        self.helps = tuple(helps)


def blank(v):
    """True for a value that carries nothing: no value (astropy reads it as None, or as its Undefined), or a string of
    spaces. Such a card means what a missing card means, on both faces: in the frame, the WCS choice and the merge."""
    from astropy.io.fits.card import Undefined
    return v is None or isinstance(v, Undefined) or (isinstance(v, str) and v.strip() == '')


def card_value(header, key):
    """The header's value for key, or None when the card is missing or blank."""
    v = header.get(key) if key in header else None
    return None if blank(v) else v


# ---------------------------------------------------------------- the sky
class _Collect(logging.Handler):
    def __init__(self):
        super().__init__()
        self.msgs = []

    def emit(self, record):
        self.msgs.append(record.getMessage())


@contextlib.contextmanager
def _astropy_said():
    """Everything astropy says while the block runs, warnings and log lines alike, collected instead of printed
    (an earlier version silenced the warnings, and astropy's log printed its SIP message raw, ahead of the answer)."""
    from astropy import log
    saved, h, said, ws = log.handlers[:], _Collect(), [], []
    for x in saved:
        log.removeHandler(x)
    log.addHandler(h)
    try:
        with warnings.catch_warnings(record=True) as ws:
            warnings.simplefilter('always')
            yield said
    finally:
        log.removeHandler(h)
        for x in saved:
            log.addHandler(x)
        said += [str(w.message) for w in ws] + h.msgs


def celestial(header, fobj=None):
    """The header's celestial WCS, checked: (wcs, notes). Raises ValueError when it cannot be read as ICRS right
    ascension and declination: no celestial axes; not equatorial; a frame other than ICRS or FK5 at J2000 (RADESYS or
    RADECSYS, EQUINOX, with the FITS defaults: no RADESYS means ICRS without EQUINOX, FK4 below 1984, FK5 from 1984).
    notes: what astropy said while reading the header (its purely informational date fixes left out), and FK5 J2000
    taken as ICRS. fobj: the open HDUList, for a WCS with lookup-table distortion (CPDIS, D2IMDIS, as in HST's _flc
    frames), whose tables sit in the file's extensions; without it astropy refuses such a WCS.
    A card with no value is absent here too; a WCS
    without CRVAL, CRPIX or a pixel scale is refused, not filled with wcslib's defaults; a distortion the header
    declares and astropy would not apply is refused (a CPDIS or D2IMDIS that is not a lookup table; D2IM tables without
    the file, which astropy drops); and PV terms that astropy keeps on TAN (below index 5), which wcslib reads as the
    projection's reference point, are refused when they move a position in the image: a pre-2012 SCAMP first-order
    solution wrote its distortion there and landed 707,991" off, with no note."""
    from astropy.wcs import WCS
    for kind in ('CPDIS', 'D2IMDIS'):
        for j in (1, 2):
            v = card_value(header, '%s%d' % (kind, j))
            if v is None:
                continue
            if str(v).strip().lower() != 'lookup':
                raise ValueError('%s%d %r: a distortion astropy does not apply (it applies lookup tables only), so no sky '
                                 'position; re-solve the image with SIP or TPV distortion' % (kind, j, v))
            if kind == 'D2IMDIS' and fobj is None:
                raise ValueError('D2IMDIS%d: a lookup table held in the file itself (its D2IMARR extension), which astropy '
                                 'drops without the open file; give the file (fobj), as the command line does' % j)
    try:
        with _astropy_said() as said:
            wf = WCS(header, fobj=fobj)
            w = wf.celestial
    except Exception as e:           # astropy cannot build a WCS from these cards: a refusal, not a crash
        iraf = [str(card_value(header, k) or '').strip().upper()[5:8] for k in ('CTYPE1', 'CTYPE2')]
        for code in ('TNX', 'ZPX'):  # "Internal error in wcslib header parser" said nothing a user can act on
            if code in iraf:
                raise ValueError("IRAF's %s distortion (its WAT cards), which wcslib could not read here: re-solve the image "
                                 'with SIP or TPV distortion' % code)
        raise ValueError('the WCS could not be read: %s' % ' '.join(str(e).split())[:200])
    notes = [' '.join(m.split()) for m in said]
    notes = [m for m in notes if not re.match(r"'(datfix|obsfix)' made the change", m)]
    if w.naxis != 2 or w.wcs.lng < 0 or w.wcs.lat < 0:
        raise ValueError('no celestial WCS in the header')
    lng, lat = w.wcs.ctype[w.wcs.lng].upper(), w.wcs.ctype[w.wcs.lat].upper()
    if not (lng.startswith('RA--') and lat.startswith('DEC-')):
        raise ValueError('the WCS is not equatorial RA/Dec (CTYPE %s, %s)' % (w.wcs.ctype[0], w.wcs.ctype[1]))
    axes = (wf.wcs.lng + 1, wf.wcs.lat + 1)                  # the header's own axis numbers
    for i in axes:                                           # wcslib's defaults put a missing CRVAL at 0 and CRPIX at 0
        for k in ('CRVAL%d' % i, 'CRPIX%d' % i):
            if card_value(header, k) is None:
                raise ValueError('the WCS has no %s: a partial WCS gives no sky position' % k)
        scale = ['CDELT%d' % i] + ['%s%d_%d' % (m, i, j) for m in ('CD', 'PC') for j in range(1, wf.naxis + 1)]
        if all(card_value(header, k) is None for k in scale):
            raise ValueError('the WCS has no pixel scale for axis %d (no CD%d_j, CDELT%d or PC%d_j): a partial WCS gives no '
                             'sky position' % (i, i, i, i))
    rs = card_value(header, 'RADESYS')
    rs = rs if rs is not None else card_value(header, 'RADECSYS')
    eq = card_value(header, 'EQUINOX')
    eq = eq if eq is not None else card_value(header, 'EPOCH')
    if eq is not None:
        try:
            eq = float(str(eq).strip().lstrip('JjBb'))
        except ValueError:
            raise ValueError('EQUINOX %r is not a year' % (eq,))
    frame = str(rs).strip().upper() if rs is not None else ('ICRS' if eq is None else ('FK4' if eq < 1984.0 else 'FK5'))
    said_as = ('RADESYS %s' % frame) if rs is not None else ('no RADESYS' + ('' if eq is None else ', EQUINOX %g' % eq))
    if frame == 'FK5' and (eq is None or abs(eq - 2000.0) < 1e-6):
        notes.append('frame FK5 J2000 (%s), taken as ICRS' % said_as)
    elif frame != 'ICRS':
        raise ValueError('the WCS frame is %s%s (%s): only ICRS, or FK5 at J2000, can be written as ICRS; re-solve the '
                         'image against a current catalogue (Gaia) for an ICRS WCS' % (frame, '' if eq is None else ' at equinox %g' % eq, said_as))
    if lng[5:8] == 'TAN' and w.wcs.get_pv():                 # PV terms astropy kept on TAN or TAN-SIP (all below index 5)
        moved = _pv_move(header, w, fobj)
        if moved is None or moved > 1e-3:
            pv = sorted(k for k in header if re.fullmatch(r'PV\d+_\d+', k) and card_value(header, k) is not None)
            raise ValueError(
                "PV terms on a TAN header below index 5 (%s): the FITS standard reads PV1_1 and PV1_2 as the projection's "
                'reference point, which moves this image\'s positions %s, and SCAMP before 2012 wrote its first-order '
                "distortion there; the command line cannot tell which is meant. If SCAMP solved the image, set CTYPE1 = "
                "'RA---TPV' and CTYPE2 = 'DEC--TPV'; else re-solve it with SIP or TPV distortion"
                % (', '.join(pv), 'off the sky' if moved is None else 'by up to %.4g"' % moved))
    return w, notes


def _pv_move(header, w, fobj=None):
    """How far (arcsec) the PV terms move a position in the image, read as wcslib reads them, against the same header
    without them (rebuilt from its cards: once set, wcslib keeps the reference point PV1_1 and PV1_2 gave it): the core WCS
    alone, at the image's corners, centre and reference pixel. None when they put one off the sky."""
    from astropy.wcs import WCS
    h0 = header.copy()
    for k in [k for k in h0 if re.fullmatch(r'PV\d+_\d+', k)]:
        del h0[k]
    with _astropy_said():
        w0 = WCS(h0, fobj=fobj).celestial
    nx = card_value(header, 'NAXIS1') or 2 * w.wcs.crpix[0]
    ny = card_value(header, 'NAXIS2') or 2 * w.wcs.crpix[1]
    pts = [[0, 0], [nx - 1, 0], [0, ny - 1], [nx - 1, ny - 1], [(nx - 1) / 2, (ny - 1) / 2], [w.wcs.crpix[0] - 1, w.wcs.crpix[1] - 1]]
    a, b = w.wcs_pix2world(pts, 0), w0.wcs_pix2world(pts, 0)
    d = np.hypot(((a[:, 0] - b[:, 0] + 180.0) % 360.0 - 180.0) * np.cos(np.radians(b[:, 1])), a[:, 1] - b[:, 1]) * 3600.0
    return float(d.max()) if np.all(np.isfinite(d)) else None


def _radec(w, x, y):
    world = w.all_pix2world([[x, y]], 0)[0]
    return float(world[w.wcs.lng]), float(world[w.wcs.lat])


def pixel_to_radec(header, x, y, fobj=None):
    """(ra, dec) in degrees of 0-based pixel (x, y) through the header's celestial WCS (SIP and lookup tables included;
    the axes found by the WCS, not assumed). Raises ValueError when the WCS cannot be read as ICRS RA/Dec (see celestial,
    and its fobj)."""
    w, _ = celestial(header, fobj)
    return _radec(w, x, y)


def sky_rms(header, x, y, cov_px, h=0.5, fobj=None):
    """rmsRA (arcsec, the RA x cos(Dec) component), rmsDec (arcsec) and their correlation, for a position scatter given
    as a 2 x 2 pixel covariance (x, y), carried through the WCS's local Jacobian at (x, y) (central differences, +-h px)."""
    w, _ = celestial(header, fobj)
    ra0, de0 = _radec(w, x, y)
    c = math.cos(math.radians(de0))
    cols = []
    for dx, dy in ((h, 0.0), (0.0, h)):
        (rp, dp), (rm, dm) = _radec(w, x + dx, y + dy), _radec(w, x - dx, y - dy)
        cols.append([((rp - rm + 180.0) % 360.0 - 180.0) * c * 3600.0 / (2 * h), (dp - dm) * 3600.0 / (2 * h)])
    J = np.array(cols).T                   # rows: east (RA cos Dec), north (Dec); columns: x, y; arcsec per px
    S = J @ np.asarray(cov_px, float) @ J.T
    sra, sde = math.sqrt(max(S[0, 0], 0.0)), math.sqrt(max(S[1, 1], 0.0))
    cor = float(S[0, 1] / (sra * sde)) if sra > 0 and sde > 0 else 0.0
    return sra, sde, cor


# ---------------------------------------------------------------- the time
def mid_exposure(header, obstime=None, exptime=None):
    """Mid-exposure UTC as 'YYYY-MM-DDThh:mm:ss.ssZ', and a note naming what it came from. In order:
      the user's obstime (UTC, YYYY-MM-DDThh:mm:ss[.s]Z);
      DATE-AVG; then MJD-AVG;
      the start (EXPSTART, DATE-BEG, DATE-OBS with TIME-OBS, MJD-BEG, MJD-OBS) + half the exposure (the user's exptime,
        EXPTIME, EXPOSURE); then the middle of the start and DATE-END or MJD-END.
    TIMESYS UTC, UT or absent is UTC; TT, TDT, TAI are converted to UTC; anything else is refused. A card with no value
    is absent (astropy reads it as None, and the page read it as 0). A DATE-* value with a date and no time is
    refused (astropy reads it as midnight); DATE-OBS may take its time from TIME-OBS. Raises TimeRefused (a ValueError)
    with the reason when no rule applies, and what would give the time instead (an obstime that does
    not exist is refused as such; the remedy names only what helps; a time outside the years 0000-9999
    is refused; an exptime that DATE-AVG or MJD-AVG overrides is said)."""
    from astropy.time import Time, TimeDelta
    from astropy.io.fits.card import Undefined
    if obstime is not None:
        s = str(obstime).strip()
        if not re.fullmatch(OBSTIME, s):
            raise TimeRefused('obstime %r is not YYYY-MM-DDThh:mm:ss[.s]Z (UTC)' % s, helps=())
        if not _a_real_time(s):          # astropy's own refusal came on two lines
            raise TimeRefused('obstime %r is not a date and time that exist (UTC)' % s, helps=())
        return _iso(Time(s[:-1], format='isot', scale='utc')), 'obsTime given by the user'

    def has(key):
        if key not in header:
            return False
        v = header[key]
        return v is not None and not isinstance(v, Undefined) and str(v).strip() != ''

    tsys = str(header['TIMESYS']).strip().upper() if has('TIMESYS') else 'UTC'
    if tsys not in TIME_SCALES:
        raise TimeRefused("TIMESYS %s is not UTC, TT or TAI, so the header's times cannot be read as UTC" % tsys)
    scale = TIME_SCALES[tsys]

    def date(key):
        d = str(header[key]).strip()
        if 'T' not in d:
            if key != 'DATE-OBS' or not has('TIME-OBS'):
                raise TimeRefused('%s %r has a date and no time%s' % (key, d, ' (and there is no TIME-OBS)' if key == 'DATE-OBS' else ''))
            d = d + 'T' + str(header['TIME-OBS']).strip()
        d = d[:-1] if d.endswith('Z') else d
        try:
            return Time(d, format='isot', scale=scale)
        except ValueError:
            raise TimeRefused('%s %r is not a FITS date-time' % (key, str(header[key])))

    def mjd(key):
        try:
            v = float(header[key])
        except (TypeError, ValueError):
            raise TimeRefused('%s %r is not a number of days' % (key, header[key]))
        return Time(v, format='mjd', scale=scale)

    if has('DATE-AVG') or has('MJD-AVG'):
        t, used = (date('DATE-AVG'), 'DATE-AVG') if has('DATE-AVG') else (mjd('MJD-AVG'), 'MJD-AVG')
        if exptime is not None:          # the given exposure was dropped without a word
            used += ' (the given exposure is not used: %s is the mid-exposure)' % used
    else:
        for key, read in (('EXPSTART', mjd), ('DATE-BEG', date), ('DATE-OBS', date), ('MJD-BEG', mjd), ('MJD-OBS', mjd)):
            if has(key):
                start = read(key)
                used = key + (' + TIME-OBS' if key == 'DATE-OBS' and 'T' not in str(header[key]) else '') + ' (the start)'
                break
        else:
            raise TimeRefused('no time in the header (DATE-AVG, MJD-AVG, DATE-OBS, MJD-OBS, ...)')
        src = 'the given exposure' if exptime is not None else ('EXPTIME' if has('EXPTIME') else ('EXPOSURE' if has('EXPOSURE') else None))
        if src:
            exp = exptime if exptime is not None else header[src]
            try:
                exp = float(exp)
            except (TypeError, ValueError):
                exp = float('nan')
            if not (math.isfinite(exp) and exp >= 0):
                raise TimeRefused('%s %r is not a number of seconds' % ('the given exposure' if exptime is not None else src, exp),
                                  helps=('obstime',) if exptime is not None else ('obstime', 'exptime'))
            t, used = start + TimeDelta(exp / 2.0, format='sec'), used + ' + %s/2' % src
        elif has('DATE-END') or has('MJD-END'):
            ekey = 'DATE-END' if has('DATE-END') else 'MJD-END'
            try:
                end = date(ekey) if ekey == 'DATE-END' else mjd(ekey)
            except TimeRefused as e:     # the start stands: an exposure time would give the middle
                raise TimeRefused(str(e), helps=('obstime', 'exptime'))
            if end < start:                                  # halfway put it hours before the start, silently
                raise TimeRefused("%s %s is before the start (%s): the header's times disagree, so the mid-exposure is unknown"
                                  % (ekey, str(header[ekey]).strip(), used.replace(' (the start)', '')), helps=('obstime', 'exptime'))
            t, used = start + (end - start) * 0.5, used + ' and %s, halfway' % ekey
        else:
            raise TimeRefused('no exposure time (EXPTIME, EXPOSURE) and no DATE-AVG, MJD-AVG or DATE-END: the mid-exposure is unknown',
                              helps=('obstime', 'exptime'))
    y = int(t.utc.ymdhms['year'])
    if not 0 <= y <= 9999:               # written as '10072-08-06T00:00:30.0Z' and '-58-05-06T00:00:30.000Z'
        raise TimeRefused("the header's time (%s) falls in the year %d, outside the years 0000-9999 a record can hold" % (used, y))
    return _iso(t), 'obsTime from ' + used + ('' if scale == 'utc' else ', TIMESYS %s converted to UTC' % tsys)


def _iso(t):
    return t.utc.isot[:22] + 'Z'


def mid_exposure_iso(header):
    """Mid-exposure UTC from the header alone (mid_exposure without the user's values); raises ValueError."""
    return mid_exposure(header)[0]


# ---------------------------------------------------------------- the record
def designation_field(desig):
    """'permID' or 'provID', chosen by the schema's own patterns, in ASCII; ValueError if the designation is neither. The
    schema's \\d is any Unicode digit, so ３I and ٣I passed it and the MPC's validator: an ADES designation
    is ASCII letters and digits."""
    d = str(desig).strip()
    odd = next((ch for ch in d if not ch.isascii()), None)
    if odd is not None:
        raise ValueError('desig: %r holds a character outside ASCII (U+%04X): ADES designations are ASCII letters and digits'
                         % (d, ord(odd)))
    if re.fullmatch(PERMID, d, re.ASCII):
        return 'permID'
    if any(re.fullmatch(p, d, re.ASCII) for p in PROVID):
        return 'provID'
    raise ValueError("desig: %r is neither a permanent (permID, e.g. 3I, 1P) nor a provisional designation (provID, "
                     "e.g. C/2025 N1) by the ADES schema's patterns" % d)


def _unprintable(v):
    """Why a name cannot go into a record as it is, or None: a control character (Unicode's Cc, U+0000-001F and
    U+007F-009F), or bytes that were not UTF-8 (the surrogates Python decodes them to). ADES text is printable UTF-8, and
    such names broke the MPC's reader. The page says the same."""
    for ch in '' if v is None else str(v):
        cat = unicodedata.category(ch)
        if cat == 'Cs':
            return 'holds bytes that are not UTF-8 (U+%04X): ADES text is UTF-8' % ord(ch)
        if cat == 'Cc':
            return 'holds a control character (U+%04X): ADES names hold printable characters only' % ord(ch)
        if cat in ('Zl', 'Zp') or (ord(ch) & 0xFFFE) == 0xFFFE or 0xFDD0 <= ord(ch) <= 0xFDEF:   # line and paragraph separators and noncharacters break the MPC's tools
            return "holds U+%04X, a character the MPC's tools cannot read (a line or paragraph separator, or a noncharacter): remove it" % ord(ch)
    return None


def _text(v, width):
    """A StringType value: no '|' or line break, at least one character that is not a space, at most width."""
    s = '' if v is None else str(v).strip()
    return s if s and len(s) <= width and '|' not in s and '\n' not in s and '\r' not in s else None


def _two_figures(v, width=7):
    """An uncertainty at two significant figures, as ADES asks ("Submissions with more than two significant figures in
    reported uncertainties may be rejected by the MPC"), written as a positive decimal of at most width characters (no
    exponent); None when it cannot be. Rounded first, so that 0.0995 is 0.10, not 0.100."""
    if v is None or not (math.isfinite(v) and v > 0):
        return None
    m, e = ('%.1e' % v).split('e')
    e = int(e)
    s = '%.*f' % (max(1 - e, 0), float(m) * 10.0 ** e)
    return s if len(s) <= width and float(s) > 0 else None


def _decimals(sigma_deg):
    """ADES's DP = CEILING(1 - LOG10(SIGMA)), SIGMA in degrees, within the schema's 0-9 (ra's pattern, \\.[0-9]{0,9})."""
    if not (math.isfinite(sigma_deg) and sigma_deg > 0):
        return 0
    return min(max(math.ceil(1.0 - math.log10(sigma_deg)), 0), DECIMALS_MAX)


def _a_real_time(s):
    """True when s (OBSTIME's pattern) names a UTC date and time that exist: astropy refuses 30 February, month 13, hour 25."""
    from astropy.time import Time
    try:
        Time(s[:-1], format='isot', scale='utc')
        return True
    except ValueError:
        return False


def software():
    """The record's software line: this tool, its version, and the part it did (SOFTWARE)."""
    from . import __version__
    return SOFTWARE % __version__


def ades_psv(ra, dec, obs_time, stn, desig, mode, ast_cat, submitter, measurers, design, aperture, detector,
             observers=None, observatory_name=None, rms_ra=None, rms_dec=None, rms_corr=None,
             remarks='zero-aperture extrapolated position', header=True):
    """Return the PSV text (version 2022): the obsContext (observatory, submitter, observers, measurers, telescope) if
    header, then one keyword record and one data record. ra, dec in degrees; obs_time UTC 'YYYY-MM-DDThh:mm:ss[.s]Z';
    rms_ra (arcsec, includes cos Dec), rms_dec, rms_corr optional. Every value is checked against the schema's pattern or
    the MPC's list; every problem found is raised together, as one ValueError naming the fields."""
    errs = []
    try:
        ra, dec = float(ra), float(dec)
    except (TypeError, ValueError):
        ra = dec = float('nan')
    if not (math.isfinite(ra) and math.isfinite(dec) and -90.0 <= dec <= 90.0):
        errs.append('ra/dec: %r, %r is not a sky position' % (ra, dec))
    if not obs_time or not re.fullmatch(OBSTIME, str(obs_time)):
        errs.append('time: %r is not a mid-exposure time (UTC, YYYY-MM-DDThh:mm:ss[.s]Z)' % (obs_time,))
    elif not _a_real_time(str(obs_time)):         # the schema's pattern checks digits only: 2026-13-45 passed
        errs.append('time: %r is not a date and time that exist (UTC)' % (obs_time,))
    if not stn or not re.fullmatch(STATION, str(stn)):
        errs.append('stn: %r is not an observatory code (3-4 letters or digits)' % (stn,))
    elif str(stn).upper() in NO_FIXED_POSITION:             # space-based and roving stations need the observer's position
        errs.append("stn %s has no fixed position in the MPC's list of observatory codes (a space-based or roving observatory): "
                    "ADES then needs the observer's own position (its Location Group: sys, ctr, pos1-pos3), which this tool "
                    "does not write" % stn)
    field = None
    try:
        field = designation_field(desig) if desig else None
    except ValueError as e:
        errs.append(str(e))
    else:
        if field is None:
            errs.append('desig: none given')
    if mode not in MODES:
        errs.append("mode: %r is not one of the MPC's current modes for an image (%s); a CMOS camera is CMO" % (mode, ', '.join(MODES)))
    if ast_cat not in AST_CATS + AST_CATS_DEPRECATED:
        errs.append("astCat: %r is not on the MPC's catalogue list (e.g. %s)" % (ast_cat, ', '.join(AST_CATS[:6])))
    ms = [measurers] if isinstance(measurers, str) else list(measurers or [])
    obs = [observers] if isinstance(observers, str) else list(observers or [])
    odd = {k: next((b for b in map(_unprintable, v) if b), None)        # a control character, or bytes that are not UTF-8
           for k, v in (('submitter', [submitter]), ('measurers', ms), ('observers', obs), ('observatory name', [observatory_name]),
                        ('design', [design]), ('detector', [detector]))}
    for k, why in odd.items():
        if why:
            errs.append('%s: %s' % (k, why))
    if not odd['submitter'] and _text(submitter, 100) is None:
        errs.append('submitter: %r is not a name (1-100 characters, no |)' % (submitter,))
    if not odd['measurers'] and (not ms or any(_text(m, 100) is None for m in ms)):
        errs.append('measurers: %r is not a list of one or more names' % (measurers,))
    if not odd['observers'] and any(_text(m, 100) is None for m in obs):
        errs.append('observers: %r is not a list of names' % (observers,))
    if not odd['observatory name'] and observatory_name is not None and _text(observatory_name, 100) is None:
        errs.append('observatory name: %r is not a name' % (observatory_name,))
    if not odd['design'] and _text(design, 35) is None:
        errs.append('design: %r is not a telescope design (1-35 characters, no |)' % (design,))
    ap = None if aperture is None else str(aperture).strip()
    if not (ap and len(ap) <= 6 and re.fullmatch(POSDEC, ap) and 0.0 < float(ap) < 100000.0):
        errs.append('aperture: %r is not an aperture in metres (a positive decimal, at most 6 characters)' % (aperture,))
    if not odd['detector'] and _text(detector, 25) is None:
        errs.append('detector: %r is not a detector (1-25 characters, no |)' % (detector,))
    rms = []
    if rms_ra is not None or rms_dec is not None:           # two significant figures
        a = _two_figures(rms_ra) if rms_ra is not None else None
        b = _two_figures(rms_dec) if rms_dec is not None else None
        if a is None or b is None:
            errs.append('rmsRA/rmsDec: %r, %r cannot be written at two significant figures as positive decimals of 7 '
                        'characters' % (rms_ra, rms_dec))
        else:
            rms = [('rmsRA', a), ('rmsDec', b)]
            if rms_corr is not None:
                if not (math.isfinite(rms_corr) and -1.0 < rms_corr < 1.0):
                    errs.append('rmsCorr: %r is not a correlation strictly between -1 and 1' % (rms_corr,))
                else:
                    rms.append(('rmsCorr', '%.4f' % min(max(rms_corr, -0.9999), 0.9999)))
    rem = str(remarks).replace('|', '/').replace('\n', ' ')
    if len(rem) > 300:
        errs.append('remarks: longer than 300 characters')
    if errs:
        raise ValueError('; '.join(errs))
    if rms:                                     # the decimals the uncertainty supports: ra is
        c = math.cos(math.radians(dec))         # RA itself, so its uncertainty in degrees is rmsRA / cos Dec
        dra = _decimals(float(rms[0][1]) / 3600.0 / c) if c > 0 else 0
        dde = _decimals(float(rms[1][1]) / 3600.0)
    else:
        dra = dde = DECIMALS_DEFAULT
    r = round(ra % 360.0, dra)
    r = r - 360.0 if r >= 360.0 else r          # 359.9999999 is 0.000000, not 360.000000 (RAType: 0 <= ra < 360)
    fields = [(field, str(desig).strip()), ('mode', mode), ('stn', str(stn)), ('obsTime', str(obs_time)),
              ('ra', '%.*f' % (dra, r)), ('dec', '%+.*f' % (dde, dec))] + rms + [('astCat', ast_cat), ('remarks', rem)]
    names = [f[0] for f in fields]
    vals = [str(f[1]) for f in fields]
    width = [max(len(a), len(b)) for a, b in zip(names, vals)]
    lines = []
    if header:
        lines += ['# version=%s' % VERSION, '# observatory', '! mpcCode %s' % stn]
        if observatory_name:
            lines += ['! name %s' % _text(observatory_name, 100)]
        lines += ['# submitter', '! name %s' % _text(submitter, 100)]
        if obs:
            lines += ['# observers'] + ['! name %s' % _text(m, 100) for m in obs]
        lines += ['# measurers'] + ['! name %s' % _text(m, 100) for m in ms]
        lines += ['# telescope', '! design %s' % _text(design, 35), '! aperture %s' % ap, '! detector %s' % _text(detector, 25)]
        lines += ['# software', '! astrometry %s' % software()]                 # the software, in ADES's place for it
    lines += ['|'.join(a.ljust(w) for a, w in zip(names, width)), '|'.join(b.ljust(w) for b, w in zip(vals, width))]
    return '\n'.join(lines) + '\n'


# ---------------------------------------------------------------- the WCS at the comet
# A broken or degenerate WCS gave a sky position and a record, each accepted by the MPC's validator: an all-zero CD matrix
# (wcslib's cdfix put the identity in its place: about 1.2 deg off), a singular one (0.9" off), SIP A_2_0 = 1e300 (RA 61.5,
# Dec 0), CRPIX1 = 'abc' (read as a default, 11.7" off). Each value below was measured first: the singular matrix's axes, 1.8e-18 in the ratio of its singular values; the local pixel scale over the
# matrix's, 0.9996-0.9997 on the study's 30 frames (their lookup tables and SIP applied) and 0 under the broken SIP. The page
# applies the same rules, in the same words (page/zeroap.js, makeWCS and check).
WCS_NUMBER = re.compile(r'^(CRVAL|CRPIX|CDELT|CROTA)\d+$|^(CD|PC)\d+_\d+$|^(A|B|AP|BP)_(\d+_\d+|ORDER)$|^(LONPOLE|LATPOLE)$')
WCS_AXES_MIN = 0.01                  # the matrix's smaller singular value over its larger
WCS_SCALE = (0.67, 1.5)              # the local pixel scale at the position, over the matrix's


D_EXPONENT = re.compile(r'^[+-]?(\d+\.?\d*|\.\d+)[Dd][+-]?\d+$')   # FITS allows 1.50123D+02 for a real number


def wcs_header(header):
    """A copy of the header for the WCS, its WCS numbers written with a D exponent or in quotes written afresh from the
    value the header reads: astropy's header reads CRVAL1 = 1.50123D+02 as 150.123, and its WCS, from the card's text, as
    1.50123 (a record 148.6 deg off in RA); a number in quotes, '151.5', wcslib reads as 0
    (RA 359.9999). The page reads both as their numbers."""
    from astropy.io import fits
    h = header.copy()
    for i in range(len(h)):
        card = h.cards[i]
        if not WCS_NUMBER.match(str(card.keyword)):
            continue
        v, k, c = card.value, card.keyword, card.comment
        if isinstance(v, str):                                # a number in quotes: its number, when it is one
            try:
                v = float(v.strip())
            except ValueError:
                continue
            if not np.isfinite(v):
                continue
        elif not D_EXPONENT.match(card.image[10:].split('/')[0].strip()):
            continue
        del h[i]
        h.insert(i, fits.Card(k, v, c))
    return h


def wcs_as_read(header, w):
    """The first WCS number of the header that the WCS w holds otherwise, as (keyword, the header's value, w's), or None:
    the backstop of the rule that no record is written from a sky solution that differs from what the header says. CRVAL, CD and CDELT are compared on an axis in degrees only, since
    wcslib converts other units; PC and CDELT only where the WCS holds no CD matrix."""
    axis = {}
    for a in range(w.naxis):
        for i in range(1, 10):
            ct = card_value(header, 'CTYPE%d' % i)
            if ct is not None and str(ct).strip().upper()[:8] == str(w.wcs.ctype[a]).strip().upper()[:8]:
                axis[a] = i
                break
    if len(axis) != w.naxis:
        return None
    deg = {a: str(card_value(header, 'CUNIT%d' % i) or 'deg').strip().lower() in ('deg', 'degree', 'degrees')
           for a, i in axis.items()}
    pairs = []
    for a, i in axis.items():
        pairs.append(('CRPIX%d' % i, w.wcs.crpix[a]))
        if deg[a]:
            pairs.append(('CRVAL%d' % i, w.wcs.crval[a]))
        for b, j in axis.items():
            if w.wcs.has_cd():
                if deg[a]:
                    pairs.append(('CD%d_%d' % (i, j), w.wcs.cd[a][b]))
            else:
                pairs.append(('PC%d_%d' % (i, j), w.wcs.pc[a][b]))
        if not w.wcs.has_cd() and deg[a]:
            pairs.append(('CDELT%d' % i, w.wcs.cdelt[a]))
    pairs.append(('LONPOLE', w.wcs.lonpole))
    for name, m in (('A', 'a'), ('B', 'b'), ('AP', 'ap'), ('BP', 'bp')):
        arr = getattr(w.sip, m, None) if w.sip is not None else None
        if arr is None:
            continue
        for p in range(arr.shape[0]):
            for q in range(arr.shape[1]):
                pairs.append(('%s_%d_%d' % (name, p, q), arr[p][q]))
    for k, got in pairs:
        v = card_value(header, k)
        if v is None:
            continue
        if isinstance(v, bool):                               # a logical is no number (wcslib reads T as 0)
            return k, float('nan'), float(got)
        try:
            hv, wv = float(str(v).strip() if isinstance(v, str) else v), float(got)
        except ValueError:
            return k, float('nan'), float(got)
        if not abs(hv - wv) <= 1e-9 * max(abs(hv), abs(wv)):
            return k, hv, wv
    return None


def wcs_numbers(header):
    """Raises ValueError when a WCS card that should hold a number holds something else."""
    for k in header:
        if not WCS_NUMBER.match(str(k)):
            continue
        v = card_value(header, k)
        if v is None:
            continue
        if isinstance(v, bool):                               # a logical is no number: T, read by wcslib as 0
            raise ValueError("the WCS card %s = '%s' is not a number" % (k, 'T' if v else 'F'))
        try:
            ok = np.isfinite(float(str(v).strip() if isinstance(v, str) else v))
        except (TypeError, ValueError):
            ok = False
        if not ok:
            raise ValueError("the WCS card %s = '%s' is not a number" % (k, str(v).strip()))


def wcs_check(header, w, said, x, y, fobj=None):
    """Raises ValueError, in the page's words, when the WCS cannot be trusted at pixel (x, y): a card that is not a number,
    a matrix that is all zero, singular or degenerate, or a distortion that changes the pixel scale there beyond 0.67-1.5."""
    wcs_numbers(header)
    if any("'cdfix' made the change" in n for n in said):   # wcslib replaced an all-zero matrix with its own
        raise ValueError('the WCS matrix is all zero or cannot be inverted')
    off = wcs_as_read(header, w)                             # before the matrix's own checks: a misread card is the reason
    if off:
        raise ValueError("the WCS read %s as %.10g where the header says %.10g: no sky position from a WCS that is not "
                         "the header's" % (off[0], off[2], off[1]))
    m = np.asarray(w.pixel_scale_matrix, float)
    if not np.all(np.isfinite(m)) or np.linalg.det(m) == 0:
        raise ValueError('the WCS matrix is all zero or cannot be inverted')
    sv = np.linalg.svd(m, compute_uv=False)
    if sv[1] / sv[0] < WCS_AXES_MIN:
        raise ValueError('the WCS matrix is degenerate: its two axes are nearly parallel')
    lin = np.sqrt(abs(np.linalg.det(m))) * 3600.0
    p = [pixel_to_radec(header, x + dx, y + dy, fobj=fobj) for dx, dy in ((0.0, 0.0), (0.5, 0.0), (0.0, 0.5))]
    c = np.cos(np.radians(p[0][1]))
    dra = lambda a, b: ((a - b + 180.0) % 360.0) - 180.0
    jac = np.array([[dra(p[1][0], p[0][0]) * c, dra(p[2][0], p[0][0]) * c], [p[1][1] - p[0][1], p[2][1] - p[0][1]]]) * 3600.0 / 0.5
    loc = np.sqrt(abs(np.linalg.det(jac))) if np.all(np.isfinite(jac)) else float('nan')
    ratio = loc / lin
    if not (np.isfinite(ratio) and WCS_SCALE[0] <= ratio <= WCS_SCALE[1]):
        raise ValueError('the WCS distortion changes the pixel scale by a factor of %s at the measured position, outside '
                         '%g-%g: a broken distortion' % ('%.3g' % ratio if np.isfinite(ratio) else 'nan', WCS_SCALE[0], WCS_SCALE[1]))
