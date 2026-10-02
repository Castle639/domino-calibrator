/* zeroap.js - zero-aperture comet astrometry in the browser (and in Node, for its tests).
   A port of domino_calibrator (Python): exact circle-pixel overlaps, the moment photocentre M, the symmetric Gaussian fit G
   with the 2.5r-5r annulus background, the 2.0-6.0 px / 0.1 px sequence and its straight-line extrapolation to r = 0
   (Farnocchia et al. 2016, arXiv:1507.01980), a FITS reader, a TAN(-SIP) WCS and an ADES PSV record (version 2022).
   Coordinates 0-based, pixel centres on integers, x = column, y = row.
   A Castle product from Domino Observatory. Built by Annie, the Castle's AI. 27 Sept 2026.
   The failure contract, as in the Python: nothing here throws on a
   stranger's data. Every radius carries ok and a reason, and no position unless ok; the time, the WCS and the record
   are each an answer or a refusal with its reason ({error} or {unsupported}). Where the Python converts (TIMESYS TT or
   TAI; distortions astropy applies), the page refuses and says so. */
(function (root) {
  'use strict';

  // ---------------- FITS ----------------
  const MAX_PIXELS = 25e6;               // the page decodes images up to 25 Mpx (e.g. 5000 x 5000); bigger ones are refused
  const decoded = { pixels: 0 };         // pixels decoded so far: an image is decoded only when it is used
  // astropy's record-valued cards (DP1 = 'EXTVER: 1', D2IM1 = 'AXIS.1: 1'), read as DP1.EXTVER = 1 (its _rvkc patterns)
  const RVKC = /^([A-Za-z_]\w*(?:\.\d+)?(?:\.[A-Za-z_]\w*(?:\.\d+)?)*): +([-+]?(?:\.\d+|\d+(?:\.\d*)?)(?:[DE][-+]?\d+)?)$/;
  const COMMENTARY = ['', 'COMMENT', 'HISTORY', 'CONTINUE'];
  // what "the command line" is, wherever the page sends the user there (nine messages never said)
  const CL = 'the command line (python -m domino_calibrator.cli)';
  // the command line's words (cli.py): the primary's WCS is taken for an extension only with INHERIT = T, the FITS
  // convention
  const NOT_INHERITED = "no WCS in the image's own HDU, and it does not say INHERIT = T, so the primary HDU's WCS is not taken for it " +
    "(the FITS convention): if the primary's WCS is the image's, add INHERIT = T to the image's header";
  const DS9 = '0-based; add 1 for ds9';
  const WCS_AXES_MIN = 0.01, WCS_SCALE = [0.67, 1.5];   // the WCS's checks, the command line's (ades.py, wcs_check)
  function blankValue(v) { return v === undefined || v === null || (typeof v === 'string' && v.trim() === ''); }
  function decodeImage(dv, off, n, bitpix, blank, bs, bz) {
    const d = new Float64Array(n);
    for (let i = 0; i < n; i++) {
      let v;
      if (bitpix === -32) v = dv.getFloat32(off + 4 * i, false);
      else if (bitpix === -64) v = dv.getFloat64(off + 8 * i, false);
      else if (bitpix === 16) v = dv.getInt16(off + 2 * i, false);
      else if (bitpix === 32) v = dv.getInt32(off + 4 * i, false);
      else v = dv.getUint8(off + i);
      d[i] = v === blank ? NaN : v * bs + bz;
    }
    decoded.pixels += n;
    return d;
  }
  function parseFITS(buf) {
    const u8 = new Uint8Array(buf), dv = new DataView(buf);
    let off = 0; const hdus = [];
    const none = function (why) { return { header: {}, cards: [], dropped: [], unreadable: why }; };
    // a .fits.gz, a PNG or a text file was "no 2-D image in this file"
    if (u8.length >= 2 && u8[0] === 0x1f && u8[1] === 0x8b)
      return [none('a gzipped file (.gz), which the page does not read: gunzip it first, or use ' + CL + ', which reads it')];
    if (u8.length < 2880) return [none('not a FITS file (shorter than one 2880-byte FITS block)')];
    while (off + 2880 <= u8.length) {
      const hdr = {}, cards = [], dropped = [], written = {}; let end = false;   // written: a value's own text
      while (!end && off + 2880 <= u8.length) {
        for (let i = 0; i < 36; i++) {
          const c = String.fromCharCode.apply(null, u8.subarray(off + 80 * i, off + 80 * i + 80));
          cards.push(c);
          const kw = c.slice(0, 8).trim();
          if (kw === 'END') { end = true; break; }
          if (COMMENTARY.indexOf(kw) >= 0) continue;
          // a value card has "= " in columns 1-10, as astropy reads it; a card without is astropy's invalid card, whose raw
          // text is no value: `EXPTIME =60.0` was read from column 11 as 0. It is left out and named
          const eq = c.indexOf('= ');
          if (eq < 0 || eq > 8) { if (kw !== 'HIERARCH') dropped.push(kw); continue; }
          const key = c.slice(0, eq).trim();
          let v = c.slice(eq + 2); let val;
          // a string opens where its quote is, after spaces only, and '' inside it is one quote, as astropy reads it: a quote
          // at column 21 kept its quotes, and 'O''Brien' ended at O. A string never closed is a card astropy
          // cannot read: left out and named
          const s = /^ *'((?:[^']|'')*)'/.exec(v);
          if (s) {
            const after = v.slice(s[0].length).trim();   // after the string, only a comment: other text is a card astropy cannot read
            if (after !== '' && after[0] !== '/') { dropped.push(key); continue; }
            val = s[1].replace(/''/g, "'").trim();
          } else if (/^ *'/.test(v)) { dropped.push(key); continue; }
          else { v = v.split('/')[0].trim(); written[key] = v; val = v === '' ? undefined : (v === 'T') ? true : (v === 'F') ? false : Number(v.replace('D', 'E')); if (Number.isNaN(val)) val = v; }
          // a card with no value, or an empty string, is absent, as in the Python: not stored, so that it hides nothing
          // (a blank card in the image HDU hid the primary's TT)
          if (blankValue(val)) continue;
          const r = typeof val === 'string' ? RVKC.exec(val) : null;
          if (r) hdr[key + '.' + r[1]] = Number(r[2].replace('D', 'E'));
          else hdr[key] = val;
        }
        off += 2880;
      }
      const bitpix = hdr.BITPIX | 0, naxis = hdr.NAXIS | 0;
      const h = { header: hdr, cards: cards, dataOffset: off, dropped: dropped };
      if (!hdr.SIMPLE && !hdr.XTENSION) {           // not a FITS header (a text file, say): nothing further to read
        if (!hdus.length) h.unreadable = 'not a FITS file (it does not begin with SIMPLE = T)';
        hdus.push(h); break;
      }
      // a size that is not a size stops the read: a negative NAXISn or PCOUNT stepped the offset back over a header already
      // read, forever, and the rest of the file cannot be found without it
      const sizes = ['NAXIS'].concat(Array.from({ length: Math.max(0, Math.min(naxis, 999)) }, function (_, a) { return 'NAXIS' + (a + 1); }),
        hdr.PCOUNT !== undefined ? ['PCOUNT'] : []);
      // a size is an integer as written: NAXIS1 = 64.0 was read as 64 here, while astropy's seek failed on it
      const bad = sizes.find(function (k) { return !(Number.isInteger(hdr[k]) && hdr[k] >= 0 && (k !== 'NAXIS' || hdr[k] <= 999) && /^\+?[0-9]+$/.test(written[k] || '')); });
      if (bad) { h.unreadable = bad + ' = ' + (written[bad] !== undefined ? written[bad] : hdr[bad]) + ' is not a size: the header is corrupt'; hdus.push(h); break; }
      let n = naxis ? 1 : 0;
      for (let a = 1; a <= naxis; a++) n *= hdr['NAXIS' + a];
      const nb = n * Math.abs(bitpix) / 8 + (hdr.PCOUNT || 0);
      h.nbytes = nb;
      let flat = naxis >= 2;                            // a one-plane cube (NAXIS3 = 1, ...) is an image
      for (let a = 3; a <= naxis; a++) if (hdr['NAXIS' + a] !== 1) flat = false;
      const image = hdr.SIMPLE === true || hdr.XTENSION === 'IMAGE';
      if (flat && image) {
        const nx = hdr.NAXIS1, ny = hdr.NAXIS2, bz = hdr.BZERO || 0, bs = hdr.BSCALE === undefined ? 1 : hdr.BSCALE;
        const blank = bitpix > 0 && Number.isInteger(hdr.BLANK) ? hdr.BLANK : null;   // BLANK is no data, an integer
        h.nx = nx; h.ny = ny;
        if (nx * ny > MAX_PIXELS) h.tooBig = true;      // #10: decoding 16k x 16k froze the tab
        else if (off + nx * ny * Math.abs(bitpix) / 8 > u8.length) h.truncated = true;
        else if ([8, 16, 32, -32, -64].indexOf(bitpix) < 0)
          h.unreadable = bitpix === 64 ? '64-bit integer pixels (BITPIX 64), which the page does not read: ' + CL + ' does' : 'BITPIX ' + bitpix + ', not a FITS pixel type (8, 16, 32, 64, -32 or -64)';
        else {                                          // decoded when first used: an HST _flc holds SCI, ERR and DQ
          h.readable = true;
          const at = off; let d = null;
          Object.defineProperty(h, 'data', { enumerable: true, get: function () { return d || (d = decodeImage(dv, at, nx * ny, bitpix, blank, bs, bz)); } });
        }
      } else if (image && naxis >= 3) {                 // a colour image is a cube of 3 planes: named, not "no 2-D image"
        let planes = 1; for (let a = 3; a <= naxis; a++) planes *= hdr['NAXIS' + a];
        h.nx = hdr.NAXIS1; h.ny = hdr.NAXIS2;
        h.unreadable = 'a cube of ' + planes + ' planes (a colour image?): the page reads one 2-D image; save one plane on its own';
      } else if (hdr.XTENSION === 'BINTABLE' && hdr.ZIMAGE === true) {   // fpack's tile compression
        h.nx = hdr.ZNAXIS1; h.ny = hdr.ZNAXIS2;
        h.unreadable = 'a compressed (fpack) image, which the page does not read: run funpack on it first, or use ' + CL;
      }
      hdus.push(h);
      off += Math.ceil(nb / 2880) * 2880;
    }
    return hdus;
  }
  function radiusText(v) {              // a radius as written: the fewest decimals, at least one, that give it back
    for (let d = 1; d <= 10; d++) { const s = v.toFixed(d); if (Number(s) === v) return s; }
    return String(v);
  }

  // ---------------- WCS: TAN with CD (or CDELT/PC, CROTA2), optional SIP, and HST's lookup tables ----------------
  // null: no WCS. {unsupported: reason}: a WCS the page cannot read as it should, so it gives no sky position
  // rather than a wrong one: a projection other than TAN (TPV, ZPN, ...), PV distortion terms, SIP coefficients without
  // the -SIP suffix (astropy applies them, the page would not), a DEC-first or non-equatorial WCS, a frame other than
  // ICRS or FK5 at J2000 (RADESYS or RADECSYS, EQUINOX, with the FITS defaults, as the Python); a blank card is absent; a WCS without CRVAL, CRPIX or a pixel
  // scale is refused, and a PC matrix takes FITS's default CDELT of 1; CUNIT is read as astropy reads it;
  // and lookup-table distortion, CPDIS and D2IMDIS as in HST's _flc frames, is applied as astropy 6.1.7 applies
  // it (astropy/wcs/src/pipeline.c and distortion.c at v6.1.7): the D2IM tables at the pixel, then SIP and CPDIS at the
  // D2IM-corrected pixel, in 1-based pixels, each table bilinear and clamped to its edges. hdus: the file's HDUs
  // (parseFITS), whose WCSDVARR and D2IMARR extensions hold the tables; without them such a WCS is refused.
  const D2R = Math.PI / 180;
  const UNITS = { deg: 1, arcmin: 1 / 60, arcsec: 1 / 3600, mas: 1 / 3.6e6, rad: 180 / Math.PI };
  function lookupTable(t, transpose) {  // astropy's DistortionLookupTable: the table as read, or transposed by its AXIS cards
    const th = t.header, d = t.data, nx = t.nx, ny = t.ny;
    const num = function (k, dflt) { return blankValue(th[k]) ? dflt : Number(th[k]); };
    return { crpix: [num('CRPIX1', 0), num('CRPIX2', 0)], crval: [num('CRVAL1', 0), num('CRVAL2', 0)], cdelt: [num('CDELT1', 1), num('CDELT2', 1)],
      naxis: transpose ? [ny, nx] : [nx, ny], at: transpose ? function (x, y) { return d[x * nx + y]; } : function (x, y) { return d[y * nx + x]; } };
  }
  function lookupOffset(T, img) {        // astropy's get_distortion_offset, at a 1-based image position
    const f = [0, 0], w = [0, 0];
    for (let k = 0; k < 2; k++) {
      let c = ((img[k] - T.crval[k]) / T.cdelt[k] + T.crpix[k]) - 1.0;
      c = c < 0 ? 0 : (c > T.naxis[k] - 1 ? T.naxis[k] - 1 : c);
      f[k] = Math.floor(c); w[k] = c - f[k];
    }
    const g = function (x, y) { return T.at(x < 0 ? 0 : (x > T.naxis[0] - 1 ? T.naxis[0] - 1 : x), y < 0 ? 0 : (y > T.naxis[1] - 1 ? T.naxis[1] - 1 : y)); };
    const iw0 = 1.0 - w[0], iw1 = 1.0 - w[1];
    return g(f[0], f[1]) * iw0 * iw1 + g(f[0], f[1] + 1) * iw0 * w[1] + g(f[0] + 1, f[1]) * w[0] * iw1 + g(f[0] + 1, f[1] + 1) * w[0] * w[1];
  }
  function makeWCS(h, fallback, hdus) {
    const has = function (o, k) { return !!o && !blankValue(o[k]); };
    // a CTYPE the header holds but no one can read: the WCS is unknown, as the command line says (cli.py)
    const unread = function (o) {
      const u = (hdus || []).find(function (x) { return x.header === o; });
      return u ? ['CTYPE1', 'CTYPE2'].filter(function (k) { return (u.dropped || []).indexOf(k) >= 0; }) : [];
    };
    const lost = unread(h).length || has(h, 'CTYPE1') || !(h && h.INHERIT === true) ? unread(h) : unread(fallback);
    if (lost.length)
      return { unsupported: 'the WCS card ' + lost[0] + ' could not be read, so the WCS is unknown: fix the card, or plate-solve the image again' };
    const own = has(h, 'CTYPE1'), inherit = !!h && h.INHERIT === true;   // a blank CTYPE1 is none
    if (!own && !inherit && h !== fallback && has(fallback, 'CTYPE1')) return { unsupported: NOT_INHERITED };   // INHERIT = T, the FITS convention
    const H = own ? h : (inherit ? fallback : {});        // the image's own WCS, else the primary's with INHERIT = T (as the Python)
    if (!has(H, 'CTYPE1')) return null;
    const val = function (k) { return blankValue(H[k]) ? undefined : H[k]; };
    // Each refusal names what to do; the command line is named only where it reads the header right
    const c1 = String(H.CTYPE1).toUpperCase(), c2 = String(val('CTYPE2') || '').toUpperCase();
    if (c1.slice(0, 4) === 'DEC-' && c2.slice(0, 4) === 'RA--')
      return { unsupported: 'the WCS has Dec first (CTYPE ' + H.CTYPE1 + ', ' + H.CTYPE2 + '): the page reads RA first; ' + CL + ' reads either order' };
    if (c1.slice(0, 4) !== 'RA--' || c2.slice(0, 4) !== 'DEC-')
      return { unsupported: 'the WCS is not equatorial RA/Dec (CTYPE ' + H.CTYPE1 + ', ' + H.CTYPE2 + ')' };
    const proj = c1.slice(5).trim();
    if (proj === 'TNX' || proj === 'ZPX')   // IRAF's own: the command line fails on IRAF's usual shape
      return { unsupported: "IRAF's " + proj + ' distortion (its WAT cards), which the page does not read: re-solve the image with SIP or TPV distortion' };
    if (!/^RA---TAN(-SIP)?$/.test(c1.trim()) || !/^DEC--TAN(-SIP)?$/.test(c2.trim()))
      return { unsupported: 'projection ' + proj + ': the page reads TAN and TAN-SIP only; ' + CL + ' reads the other FITS projections' };
    const pv = Object.keys(H).filter(function (k) { return /^PV\d+_\d+$/.test(k) && val(k) !== undefined; });
    if (pv.length) {                      // astropy reads TAN's PV terms as SCAMP's TPV only from index 5; below, as the projection's reference point
      const scamp = pv.some(function (k) { return +k.split('_')[1] >= 5; });
      if (scamp && c1.indexOf('-SIP') >= 0)   // astropy keeps the SIP and drops SCAMP's terms (the page said "as TPV")
        return { unsupported: "SCAMP's PV terms beside SIP, which the page does not choose between: " + CL + ' applies the SIP and drops the PV terms, as astropy does' };
      return { unsupported: scamp ? "SCAMP's PV distortion terms, which the page does not apply: " + CL + ' does (as TPV)'
        : "PV terms below index 5 on a TAN header, which the FITS standard reads as the projection's reference point and SCAMP (before 2012) as its first-order distortion: if SCAMP solved the image, set CTYPE1 = 'RA---TPV' and CTYPE2 = 'DEC--TPV'; else re-solve it with SIP or TPV distortion" };
    }
    // astropy refuses A_ORDER above 1 without B_ORDER, and B_ORDER above 1 without A_ORDER above 1 (its _read_sip_kw, 6.1.7);
    // the page applied the one it had, silently
    const aOrd = val('A_ORDER') === undefined ? null : Number(H.A_ORDER), bOrd = val('B_ORDER') === undefined ? null : Number(H.B_ORDER);
    if ((aOrd > 1 && bOrd === null) || (bOrd > 1 && !(aOrd > 1)))
      return { unsupported: (aOrd > 1 ? 'A_ORDER without B_ORDER' : 'B_ORDER without A_ORDER') + ' for SIP distortion, a header astropy refuses too: complete the SIP cards, or re-solve the image' };
    const sipHere = val('A_ORDER') !== undefined || val('B_ORDER') !== undefined;
    if (sipHere && c1.indexOf('-SIP') < 0)
      return { unsupported: 'SIP coefficients without -SIP in CTYPE (astropy would apply them; the page would not): ' + CL + ' applies them' };
    const unit = [1, 2].map(function (i) { const u = val('CUNIT' + i); return u === undefined ? 1 : UNITS[String(u).trim().toLowerCase()]; });
    for (let i = 1; i <= 2; i++) if (unit[i - 1] === undefined)
      return { unsupported: 'CUNIT' + i + " '" + String(H['CUNIT' + i]).trim() + "', a unit the page does not read (it reads deg, arcmin, arcsec, mas and rad)" };
    // every WCS number is a number (CRPIX1 = 'abc' was read as a default, 11.7" off, with a warning only)
    for (const k of Object.keys(H)) {
      if (!/^(CRVAL|CRPIX|CDELT|CROTA)\d+$|^(CD|PC)\d+_\d+$|^(A|B|AP|BP)_(\d+_\d+|ORDER)$|^(LONPOLE|LATPOLE)$/.test(k) || val(k) === undefined) continue;
      if (typeof H[k] === 'boolean')    // a logical is no number (T was read as 1)
        return { unsupported: 'the WCS card ' + k + " = '" + (H[k] ? 'T' : 'F') + "' is not a number" };
      if (!Number.isFinite(Number(typeof H[k] === 'string' ? H[k].trim() : H[k])))
        return { unsupported: 'the WCS card ' + k + " = '" + String(H[k]).trim() + "' is not a number" };
    }
    // the page applies the native pole TAN's default gives, LONPOLE 180; any other it refuses (LONPOLE 0
    // once put its record 32.6\" from the command line's)
    if (val('LONPOLE') !== undefined && Number(typeof H.LONPOLE === 'string' ? H.LONPOLE.trim() : H.LONPOLE) !== 180)
      return { unsupported: "LONPOLE = '" + String(H.LONPOLE).trim() + "', a native pole the page does not apply (it applies 180, the default): " + CL + ' applies it' };
    for (const k of ['CRVAL1', 'CRVAL2', 'CRPIX1', 'CRPIX2']) if (val(k) === undefined)   // wcslib's defaults put them at 0
      return { unsupported: 'the WCS has no ' + k + ': a partial WCS gives no sky position' };
    for (let i = 1; i <= 2; i++) if (['CDELT' + i, 'CD' + i + '_1', 'CD' + i + '_2', 'PC' + i + '_1', 'PC' + i + '_2'].every(function (k) { return val(k) === undefined; }))
      return { unsupported: 'the WCS has no pixel scale for axis ' + i + ' (no CD' + i + '_j, CDELT' + i + ' or PC' + i + '_j): a partial WCS gives no sky position' };
    const tables = {}, applied = [];      // HST's lookup tables
    if (val('AXISCORR') !== undefined) return { unsupported: 'the old D2IM keyword AXISCORR, which the page does not read: ' + CL + ' does' };
    for (const s of [['D2IMDIS', 'D2IM', 'D2IMARR', 'D2IMERR'], ['CPDIS', 'DP', 'WCSDVARR', 'CPERR']]) {
      for (let i = 1; i <= 2; i++) {
        const v = val(s[0] + i);
        if (v === undefined) continue;
        if (String(v).trim().toLowerCase() !== 'lookup')
          return { unsupported: s[0] + i + " '" + String(v).trim() + "': a distortion astropy does not apply (it applies lookup tables only), and neither does the page; re-solve the image with SIP or TPV distortion" };
        if (!hdus) return { unsupported: 'lookup-table distortion (' + s[0] + ': as in HST frames), whose tables sit in the file\'s own extensions: the page reads them with the whole file; ' + CL + ' does too' };
        if (val(s[3] + i) !== undefined && Number(H[s[3] + i]) < 0) continue;   // astropy skips a table whose error is below its minimum, 0
        const ev = val(s[1] + i + '.EXTVER'), extver = ev === undefined ? 1 : Number(ev), axis = val(s[1] + i + '.AXIS.' + i);
        if (axis === undefined) return { unsupported: s[0] + i + ': its table\'s axes are not given (no ' + s[1] + i + '.AXIS.' + i + ')' };
        const t = hdus.find(function (u) { return String(blankValue(u.header.EXTNAME) ? '' : u.header.EXTNAME).trim().toUpperCase() === s[2] && (blankValue(u.header.EXTVER) ? 1 : Number(u.header.EXTVER)) === extver; });
        if (!t || !t.readable) return { unsupported: s[0] + i + ': its lookup table (' + s[2] + ', EXTVER ' + extver + ') is not in this file, or cannot be read' };
        tables[s[0] + i] = lookupTable(t, Number(axis) !== i); applied.push(s[0] + i);
      }
    }
    const notes = [];
    if (applied.length) notes.push('lookup tables applied as astropy does (' + applied.join(', ') + ')');
    let eq = val('EQUINOX') !== undefined ? H.EQUINOX : val('EPOCH');
    if (eq !== undefined) { eq = Number(String(eq).trim().replace(/^[JjBb]/, '')); if (!Number.isFinite(eq)) return { unsupported: 'EQUINOX is not a year' }; }
    const rs = val('RADESYS') !== undefined ? H.RADESYS : val('RADECSYS');
    const frame = rs !== undefined ? String(rs).trim().toUpperCase() : (eq === undefined ? 'ICRS' : (eq < 1984 ? 'FK4' : 'FK5'));
    if (frame === 'FK5' && (eq === undefined || Math.abs(eq - 2000) < 1e-6)) notes.push('frame FK5 J2000, taken as ICRS');
    else if (frame !== 'ICRS') return { unsupported: 'frame ' + frame + (eq === undefined ? '' : ' at equinox ' + eq) + ': only ICRS, or FK5 at J2000, can be written as ICRS; re-solve the image against a current catalogue (Gaia) for an ICRS WCS' };
    const num = function (k, d) { return val(k) === undefined ? d : Number(H[k]); };
    let cd;
    if (['CD1_1', 'CD1_2', 'CD2_1', 'CD2_2'].some(function (k) { return val(k) !== undefined; }))
      cd = [[num('CD1_1', 0), num('CD1_2', 0)], [num('CD2_1', 0), num('CD2_2', 0)]];   // a missing CDi_j is 0 beside the others, as wcslib
    else {
      const d1 = num('CDELT1', 1), d2 = num('CDELT2', 1);   // FITS defaults CDELT to 1 beside a PC matrix ("RA NaN")
      if (['PC1_1', 'PC1_2', 'PC2_1', 'PC2_2'].some(function (k) { return val(k) !== undefined; }))   // a missing PCi_j is 1 on the diagonal, 0 off it
        cd = [[d1 * num('PC1_1', 1), d1 * num('PC1_2', 0)], [d2 * num('PC2_1', 0), d2 * num('PC2_2', 1)]];
      else { const t = num('CROTA2', 0) * D2R; cd = [[d1 * Math.cos(t), -d2 * Math.sin(t)], [d1 * Math.sin(t), d2 * Math.cos(t)]]; }
    }
    cd = [[cd[0][0] * unit[0], cd[0][1] * unit[0]], [cd[1][0] * unit[1], cd[1][1] * unit[1]]];   // CUNIT: wcslib scales CRVALi and row i to degrees
    // the matrix, as the command line checks it (ades.py, wcs_check): not all zero, invertible, its axes not nearly parallel
    const det = cd[0][0] * cd[1][1] - cd[0][1] * cd[1][0];
    if (!cd.every(function (r) { return r.every(Number.isFinite); }) || !Number.isFinite(det) || det === 0)
      return { unsupported: 'the WCS matrix is all zero or cannot be inverted' };
    const S1 = cd[0][0] * cd[0][0] + cd[0][1] * cd[0][1] + cd[1][0] * cd[1][0] + cd[1][1] * cd[1][1];
    const S2 = Math.sqrt(Math.pow(cd[0][0] * cd[0][0] + cd[0][1] * cd[0][1] - cd[1][0] * cd[1][0] - cd[1][1] * cd[1][1], 2)
      + 4 * Math.pow(cd[0][0] * cd[1][0] + cd[0][1] * cd[1][1], 2));
    if (Math.sqrt(Math.max(S1 - S2, 0) / 2) / Math.sqrt((S1 + S2) / 2) < WCS_AXES_MIN)
      return { unsupported: 'the WCS matrix is degenerate: its two axes are nearly parallel' };
    const crval = [Number(H.CRVAL1) * unit[0], Number(H.CRVAL2) * unit[1]], crpix = [Number(H.CRPIX1), Number(H.CRPIX2)];
    const sip = c1.indexOf('SIP') >= 0 ? { A: H.A_ORDER | 0, B: H.B_ORDER | 0, H: H } : null;
    return {
      notes: notes,
      pixToSky: function (x, y) {           // 0-based pixel -> (ra, dec) degrees, through astropy's pipeline in 1-based pixels
        let X = x + 1, Y = y + 1;
        if (tables.D2IMDIS1 || tables.D2IMDIS2) {       // detector to image: both tables read at the pixel itself
          const p = [X, Y];
          if (tables.D2IMDIS1) X += lookupOffset(tables.D2IMDIS1, p);
          if (tables.D2IMDIS2) Y += lookupOffset(tables.D2IMDIS2, p);
        }
        let fx = X, fy = Y;
        if (sip) {                                     // SIP and CPDIS, both at the corrected pixel
          const u0 = X - crpix[0], v0 = Y - crpix[1];
          let du = 0, dv2 = 0;
          for (let p = 0; p <= sip.A; p++) for (let q = 0; p + q <= sip.A; q++) { const c = sip.H['A_' + p + '_' + q]; if (c) du += c * Math.pow(u0, p) * Math.pow(v0, q); }
          for (let p = 0; p <= sip.B; p++) for (let q = 0; p + q <= sip.B; q++) { const c = sip.H['B_' + p + '_' + q]; if (c) dv2 += c * Math.pow(u0, p) * Math.pow(v0, q); }
          fx += du; fy += dv2;
        }
        if (tables.CPDIS1) fx += lookupOffset(tables.CPDIS1, [X, Y]);
        if (tables.CPDIS2) fy += lookupOffset(tables.CPDIS2, [X, Y]);
        const u = fx - crpix[0], v = fy - crpix[1];
        const xi = (cd[0][0] * u + cd[0][1] * v) * D2R, eta = (cd[1][0] * u + cd[1][1] * v) * D2R;
        const a0 = crval[0] * D2R, d0 = crval[1] * D2R;
        const den = Math.cos(d0) - eta * Math.sin(d0);
        let ra = a0 + Math.atan2(xi, den);
        const dec = Math.atan2(Math.sin(d0) + eta * Math.cos(d0), Math.hypot(xi, den));
        ra = ((ra / D2R) % 360 + 360) % 360;
        return [ra, dec / D2R];
      },
      check: function (x, y) {             // the WCS at the measured position (ades.py, wcs_check): its local pixel scale over the matrix's
        const p = [this.pixToSky(x, y), this.pixToSky(x + 0.5, y), this.pixToSky(x, y + 0.5)];
        const c = Math.cos(p[0][1] * D2R), dra = function (a, b) { return ((a - b + 180) % 360 + 360) % 360 - 180; };
        const j = [[dra(p[1][0], p[0][0]) * c, dra(p[2][0], p[0][0]) * c], [p[1][1] - p[0][1], p[2][1] - p[0][1]]].map(function (r) { return r.map(function (v) { return v * 3600 / 0.5; }); });
        const loc = Math.sqrt(Math.abs(j[0][0] * j[1][1] - j[0][1] * j[1][0])), ratio = loc / this.scale;
        if (!(Number.isFinite(ratio) && ratio >= WCS_SCALE[0] && ratio <= WCS_SCALE[1]))
          return 'the WCS distortion changes the pixel scale by a factor of ' + (Number.isFinite(ratio) ? String(Number(ratio.toPrecision(3))) : 'nan') + ' at the measured position, outside ' + WCS_SCALE[0] + '-' + WCS_SCALE[1] + ': a broken distortion';
        return null;
      },
      scale: Math.sqrt(Math.abs(cd[0][0] * cd[1][1] - cd[0][1] * cd[1][0])) * 3600
    };
  }

  // ---------------- exact circle-pixel overlap ----------------
  function F0(u, r) { u = Math.max(-r, Math.min(r, u)); const h = Math.sqrt(Math.max(r * r - u * u, 0)); return 0.5 * (u * h + r * r * Math.asin(u / r)); }
  function F1(u, r) { u = Math.max(-r, Math.min(r, u)); const h = Math.sqrt(Math.max(r * r - u * u, 0)); return -h * h * h / 3; }
  function F2(u, r) { return r * r * u - u * u * u / 3; }
  function pixelOverlap(a0, a1, b0, b1, r) {
    const s0 = Math.sqrt(Math.max(r * r - b0 * b0, 0)), s1 = Math.sqrt(Math.max(r * r - b1 * b1, 0));
    const bp = [a0, a1, -r, r, -s0, s0, -s1, s1].map(function (t) { return Math.max(a0, Math.min(a1, t)); }).sort(function (a, b) { return a - b; });
    let A = 0, Mu = 0, Mv = 0;
    for (let k = 0; k < 7; k++) {
      const p = bp[k], q = bp[k + 1];
      if (!(q > p)) continue;
      const m = 0.5 * (p + q);
      if (Math.abs(m) >= r) continue;
      const h = Math.sqrt(r * r - m * m);
      const topH = h < b1, botH = -h > b0;
      const top = topH ? h : b1, bot = botH ? -h : b0;
      if (!(top > bot)) continue;
      const dq = q - p, d2 = 0.5 * (q * q - p * p), f0 = F0(q, r) - F0(p, r), f1 = F1(q, r) - F1(p, r), f2 = F2(q, r) - F2(p, r);
      A += (topH ? f0 : b1 * dq) - (botH ? -f0 : b0 * dq);
      Mu += (topH ? f1 : b1 * d2) - (botH ? -f1 : b0 * d2);
      Mv += (topH ? 0.5 * f2 : 0.5 * b1 * b1 * dq) - (botH ? 0.5 * f2 : 0.5 * b0 * b0 * dq);
    }
    return [A, Mu, Mv];
  }
  function circleMoments(xc, yc, r, nx, ny) {
    const j0 = Math.floor(xc - r + 0.5), j1 = Math.floor(xc + r + 0.5), i0 = Math.floor(yc - r + 0.5), i1 = Math.floor(yc + r + 0.5);
    if (j0 < 0 || i0 < 0 || j1 > nx - 1 || i1 > ny - 1) throw new Error('aperture leaves the image');
    const out = [];
    for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) {
      const o = pixelOverlap(j - 0.5 - xc, j + 0.5 - xc, i - 0.5 - yc, i + 0.5 - yc, r);
      if (o[0] > 0) out.push([i, j, o[0], o[1] + xc * o[0], o[2] + yc * o[0]]);
    }
    return out;
  }

  // ---------------- background ----------------
  function median(v) { const s = Float64Array.from(v).sort(); const n = s.length; return n ? (n % 2 ? s[(n - 1) / 2] : 0.5 * (s[n / 2 - 1] + s[n / 2])) : NaN; }
  function sigmaClippedMedian(v, nsig, iters) {
    nsig = nsig || 3; iters = iters || 5;
    v = v.filter(Number.isFinite);
    for (let it = 0; it < iters; it++) {
      if (v.length < 3) break;
      const med = median(v), mad = 1.4826 * median(v.map(function (x) { return Math.abs(x - med); }));
      if (!(mad > 0)) break;
      const keep = v.filter(function (x) { return Math.abs(x - med) < nsig * mad; });
      if (keep.length === v.length) break;
      v = keep;
    }
    return median(v);
  }
  function annulusBackground(img, nx, ny, xc, yc, r, fin, fout) {
    fin = fin || 2.5; fout = fout || 5.0;
    const ri = fin * r, ro = fout * r, v = [];
    const j0 = Math.max(0, Math.floor(xc - ro)), j1 = Math.min(nx - 1, Math.ceil(xc + ro)), i0 = Math.max(0, Math.floor(yc - ro)), i1 = Math.min(ny - 1, Math.ceil(yc + ro));
    for (let i = i0; i <= i1; i++) for (let j = j0; j <= j1; j++) { const d = Math.hypot(j - xc, i - yc); if (d >= ri && d < ro && Number.isFinite(img[i * nx + j])) v.push(img[i * nx + j]); }
    if (v.length < MIN_PIXELS) throw new Error('annulus ' + ri.toFixed(1) + '-' + ro.toFixed(1) + ' px has fewer than ' + MIN_PIXELS + ' finite pixels in the image');
    return sigmaClippedMedian(v);         // shrink catches the throw: the radius's reason, as in the Python
  }
  const MIN_PIXELS = 8;                 // lane 5's rule: an aperture (or annulus) needs 8 finite pixels
  function apertureReason(img, nx, cm) {
    if (cm.length < MIN_PIXELS) return 'fewer than ' + MIN_PIXELS + ' pixels in the aperture';
    for (const c of cm) if (!Number.isFinite(img[c[0] * nx + c[1]])) return 'non-finite pixel in the aperture';
    return '';
  }

  // ---------------- M ----------------
  function aitken(x0, x1, x2) {
    const d1 = x1 - x0, d2 = x2 - x1, den = d2 - d1;
    if (Math.abs(den) < 1e-15) return x2;
    const g = Math.abs(d1) > 1e-15 ? d2 / d1 : 0;
    if (!(g > 0 && g < 0.995)) return x2;
    return x2 - d2 * d2 / den;
  }
  function momentCentroid(img, nx, ny, x0, y0, r, bkg, tol, maxit) {
    tol = tol || 1e-6; maxit = maxit || 500; bkg = bkg === undefined ? 0 : bkg;
    let xc = x0, yc = y0, hist = [], F = NaN;
    const fail = function (it, why) { return { x: NaN, y: NaN, n: it, flux: F, ok: false, reason: why }; };
    if (!Number.isFinite(bkg)) return fail(0, 'background not finite');      // #4: a NaN background was read as 0
    for (let it = 1; it <= maxit; it++) {
      let cm;
      try { cm = circleMoments(xc, yc, r, nx, ny); } catch (e) { return fail(it, 'aperture leaves the image'); }   // #3
      const why = apertureReason(img, nx, cm);
      if (why) return fail(it, why);
      let f = 0, sx = 0, sy = 0;
      for (const c of cm) { const d = img[c[0] * nx + c[1]] - bkg; f += d * c[2]; sx += d * c[3]; sy += d * c[4]; }
      F = f;
      if (!(f > 0)) return fail(it, 'flux in the aperture is not above the background');
      const X = sx / f, Y = sy / f;
      if (Math.hypot(X - xc, Y - yc) < tol) return { x: X, y: Y, n: it, flux: F, ok: true, reason: '' };
      hist.push([X, Y]); xc = X; yc = Y;
      if (hist.length >= 3 && it % 3 === 0) {       // Aitken, with the Python's bound (the page's jump was unbounded)
        const h = hist.slice(-3), xn = aitken(h[0][0], h[1][0], h[2][0]), yn = aitken(h[0][1], h[1][1], h[2][1]);
        const step = Math.hypot(h[2][0] - h[1][0], h[2][1] - h[1][1]), jump = Math.hypot(xn - h[2][0], yn - h[2][1]);
        if (jump <= Math.max(10 * step, 1e-3) && jump <= r) { xc = xn; yc = yn; }
        hist = [];
      }
    }
    return fail(maxit, 'no convergence in ' + maxit + ' iterations');
  }

  // ---------------- G: circular pixel-integrated Gaussian, Levenberg-Marquardt ----------------
  function erf(x) {                       // |error| < 1e-14: series for |x| < 2.5, continued fraction beyond
    const ax = Math.abs(x), s = x < 0 ? -1 : 1;
    if (ax < 2.5) {
      let term = ax, sum = ax, n = 0;
      while (Math.abs(term) > 1e-17 * Math.abs(sum)) { n++; term *= -ax * ax / n; sum += term / (2 * n + 1); if (n > 200) break; }
      return s * 2 / Math.sqrt(Math.PI) * sum;
    }
    // erfc(x) = exp(-x^2)/sqrt(pi) * 1/(x + 1/2/(x + 1/(x + 3/2/(x + ...)))) (Lentz)
    let f = ax, C = ax, Dd = 0, tiny = 1e-300;
    for (let k = 1; k < 300; k++) {
      const a = k / 2;
      Dd = ax + a * Dd; if (Dd === 0) Dd = tiny; Dd = 1 / Dd;
      C = ax + a / C; if (C === 0) C = tiny;
      const del = C * Dd; f *= del;
      if (Math.abs(del - 1) < 1e-16) break;
    }
    const erfc = Math.exp(-ax * ax) / Math.sqrt(Math.PI) / f;
    return s * (1 - erfc);
  }
  const SQ2 = Math.SQRT2, SQ2PI = Math.sqrt(2 * Math.PI);
  function pigModel(q, xx, yy, wantJ) {
    const A = q[0], x0 = q[1], y0 = q[2], s = Math.exp(q[3]);
    const n = xx.length, m = new Float64Array(n), J = wantJ ? new Float64Array(4 * n) : null;
    for (let k = 0; k < n; k++) {
      const axp = (xx[k] + 0.5 - x0) / (SQ2 * s), axm = (xx[k] - 0.5 - x0) / (SQ2 * s);
      const ayp = (yy[k] + 0.5 - y0) / (SQ2 * s), aym = (yy[k] - 0.5 - y0) / (SQ2 * s);
      const gx = 0.5 * (erf(axp) - erf(axm)), gy = 0.5 * (erf(ayp) - erf(aym));
      m[k] = A * gx * gy;
      if (wantJ) {
        const exp_ = Math.exp(-axp * axp), exm = Math.exp(-axm * axm), eyp = Math.exp(-ayp * ayp), eym = Math.exp(-aym * aym);
        const dgx = -(exp_ - exm) / (SQ2PI * s), dgy = -(eyp - eym) / (SQ2PI * s);
        const dgxt = -((SQ2 * s * axp) * exp_ - (SQ2 * s * axm) * exm) / (SQ2PI * s);
        const dgyt = -((SQ2 * s * ayp) * eyp - (SQ2 * s * aym) * eym) / (SQ2PI * s);
        J[4 * k] = gx * gy; J[4 * k + 1] = A * gy * dgx; J[4 * k + 2] = A * gx * dgy; J[4 * k + 3] = A * (dgxt * gy + gx * dgyt);
      }
    }
    return { m: m, J: J };
  }
  function solve4(M, b) {                 // Gaussian elimination with partial pivoting, 4 x 4
    const a = M.map(function (r, i) { return r.concat([b[i]]); });
    for (let c = 0; c < 4; c++) {
      let p = c; for (let r = c + 1; r < 4; r++) if (Math.abs(a[r][c]) > Math.abs(a[p][c])) p = r;
      const t = a[c]; a[c] = a[p]; a[p] = t;
      if (Math.abs(a[c][c]) < 1e-300) return null;
      for (let r = c + 1; r < 4; r++) { const f = a[r][c] / a[c][c]; for (let k = c; k < 5; k++) a[r][k] -= f * a[c][k]; }
    }
    const x = [0, 0, 0, 0];
    for (let r = 3; r >= 0; r--) { let s = a[r][4]; for (let k = r + 1; k < 4; k++) s -= a[r][k] * x[k]; x[r] = s / a[r][r]; }
    return x;
  }
  function lmFit(q, xx, yy, d, w) {
    // Levenberg-Marquardt. Returns {q, ok}: ok when a step's relative size or the cost's fall is below tolerance, or
    // when no step, however damped, lowers the cost (the minimum, to rounding: MINPACK's xtol); not ok after 400
    // iterations (scipy's max_nfev: the Python's res.success is False there). #4: the page reported ok regardless.
    let lam = 1e-3;
    function cost(p) { const m = pigModel(p, xx, yy, false).m; let c = 0; for (let k = 0; k < d.length; k++) { const e = (m[k] - d[k]) * w[k]; c += e * e; } return c; }
    let c0 = cost(q);
    for (let it = 0; it < 400; it++) {
      const r = pigModel(q, xx, yy, true), JtJ = [[0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0], [0, 0, 0, 0]], g = [0, 0, 0, 0];
      for (let k = 0; k < d.length; k++) {
        const e = (r.m[k] - d[k]) * w[k];
        for (let a = 0; a < 4; a++) { const ja = r.J[4 * k + a] * w[k]; g[a] += ja * e; for (let b = 0; b <= a; b++) JtJ[a][b] += ja * r.J[4 * k + b] * w[k]; }
      }
      for (let a = 0; a < 4; a++) for (let b = a + 1; b < 4; b++) JtJ[a][b] = JtJ[b][a];
      let improved = false;
      for (let t = 0; t < 30; t++) {
        const M = JtJ.map(function (row, i) { return row.map(function (v, j) { return i === j ? v * (1 + lam) + 1e-300 : v; }); });
        const step = solve4(M, g.map(function (v) { return -v; }));
        if (!step) { lam *= 10; continue; }
        const qn = q.map(function (v, i) { return v + step[i]; });
        const cn = cost(qn);
        if (cn <= c0) {
          const rel = Math.max.apply(null, step.map(function (s, i) { return Math.abs(s) / (Math.abs(q[i]) + 1e-10); }));
          q = qn; lam = Math.max(lam / 10, 1e-12); improved = true;
          const conv = rel < 1e-10 || (c0 - cn) <= 1e-12 * c0; c0 = cn;
          if (conv) return { q: q, ok: true };
          break;
        }
        lam *= 10;
      }
      if (!improved) return { q: q, ok: true };
    }
    return { q: q, ok: false };
  }
  function gaussFit(img, nx, ny, x0, y0, r, bkg, s0, tol, maxit) {
    tol = tol || 1e-4; maxit = maxit || 60;
    let xa = x0, ya = y0, q = null;
    const fail = function (it, why, s, amp) { return { x: NaN, y: NaN, s: s === undefined ? NaN : s, amp: amp === undefined ? NaN : amp, n: it, ok: false, reason: why }; };
    if (!Number.isFinite(bkg)) return fail(0, 'background not finite');
    for (let it = 1; it <= maxit; it++) {
      let cm;
      try { cm = circleMoments(xa, ya, r, nx, ny); } catch (e) { return fail(it, 'aperture leaves the image'); }   // #3
      const why = apertureReason(img, nx, cm);          // the Python raised here; the page fitted 4 parameters to 1-5 pixels
      if (why) return fail(it, why);
      const xx = cm.map(function (c) { return c[1]; }), yy = cm.map(function (c) { return c[0]; });
      const d = cm.map(function (c) { return img[c[0] * nx + c[1]] - bkg; }), w = cm.map(function (c) { return Math.sqrt(c[2]); });
      if (!q) q = [Math.max(d.reduce(function (a, b) { return a + b; }, 0), 1e-6), xa, ya, Math.log(s0 || Math.max(0.6, 0.5 * r))];
      const lm = lmFit(q, xx, yy, d, w);
      q = lm.q;
      if (!q.every(Number.isFinite)) return fail(it, 'the fit went non-finite');
      const s = Math.exp(q[3]);
      if (s < 0.05 || s > 20 * r || Math.hypot(q[1] - xa, q[2] - ya) > r) return fail(it, 'the fit ran away (width ' + s.toPrecision(3) + ' px, or a jump beyond r)', s, q[0]);
      if (Math.hypot(q[1] - xa, q[2] - ya) < tol) {
        if (!lm.ok) return fail(it, 'the least-squares fit did not converge', s, q[0]);
        if (!(q[0] > 0)) return fail(it, 'amplitude not above 0: no source to centre on', s, q[0]);
        return { x: q[1], y: q[2], s: s, amp: q[0], n: it, ok: true, reason: '' };
      }
      xa = q[1]; ya = q[2];
    }
    return fail(maxit, 'no convergence in ' + maxit + ' re-centrings', Math.exp(q[3]), q[0]);
  }

  // ---------------- the sequence ----------------
  function publishedRadii() { const r = []; for (let k = 0; k <= 40; k++) r.push(Math.round((2 + 0.1 * k) * 1e10) / 1e10); return r; }
  function lineFit(r, v) {
    const n = r.length; let sr = 0, sv = 0, srr = 0, srv = 0;
    for (let k = 0; k < n; k++) { sr += r[k]; sv += v[k]; srr += r[k] * r[k]; srv += r[k] * v[k]; }
    const s = (n * srv - sr * sv) / (n * srr - sr * sr); return [(sv - s * sr) / n, s];
  }
  function shrink(img, nx, ny, x0, y0, opts) {
    // Every radius carries ok and a reason ('' when ok); a radius that is not ok has no position, as in
    // the Python. Arguments that are not data (an unknown estimator or background) still throw.
    opts = opts || {};
    const radii = opts.radii || publishedRadii(), est = opts.estimator || 'G', bgMode = opts.background === undefined ? 'annulus' : opts.background;
    if (est !== 'G' && est !== 'M') throw new Error("estimator must be 'G' or 'M'");
    if (typeof bgMode === 'string' && bgMode !== 'annulus') throw new Error("background must be 'annulus' or a number");
    const xs = [], ys = [], oks = [], why = [], bks = [];
    let sx = x0, sy = y0, sPrev = null;
    for (const r of radii) {
      let b, bwhy;
      if (bgMode === 'annulus') {
        try { b = annulusBackground(img, nx, ny, sx, sy, r); bwhy = 'background: no finite value in the annulus'; }
        catch (e) { b = NaN; bwhy = 'background: ' + e.message; }
      } else { b = Number(bgMode); bwhy = 'background is not a finite number'; }
      let o;
      if (!Number.isFinite(b)) o = { x: NaN, y: NaN, ok: false, s: NaN, reason: bwhy };
      else if (est === 'M') o = momentCentroid(img, nx, ny, sx, sy, r, b);
      else { o = gaussFit(img, nx, ny, sx, sy, r, b, sPrev); sPrev = o.ok && Number.isFinite(o.s) ? o.s : null; }
      const ok = !!o.ok && Number.isFinite(o.x) && Number.isFinite(o.y);
      xs.push(ok ? o.x : NaN); ys.push(ok ? o.y : NaN); oks.push(ok); why.push(ok ? '' : (o.reason || 'not converged')); bks.push(b);
      if (ok) { sx = o.x; sy = o.y; } else { sx = x0; sy = y0; }
    }
    const gr = [], gx = [], gy = [];
    for (let k = 0; k < radii.length; k++) if (oks[k]) { gr.push(radii[k]); gx.push(xs[k]); gy.push(ys[k]); }
    const lx = gr.length >= 2 ? lineFit(gr, gx) : [NaN, NaN], ly = gr.length >= 2 ? lineFit(gr, gy) : [NaN, NaN];
    const i2 = radii.reduce(function (b, r, k) { return Math.abs(r - 2) < Math.abs(radii[b] - 2) ? k : b; }, 0);
    const g2 = oks[i2];                                  // an unconverged radius reports NaN, as in the Python
    return { radii: radii, x: xs, y: ys, ok: oks, reason: why, bkg: bks, x0: lx[0], sx: lx[1], y0: ly[0], sy: ly[1], x2: g2 ? xs[i2] : NaN, y2: g2 ? ys[i2] : NaN, nbad: radii.length - gr.length };
  }
  function radiiFrom(r0, r1, step) {
    // FROM, FROM + STEP, ..., TO as the Python's --radii: {radii} or {error} (a zero or negative step froze the tab)
    r0 = Number(r0); r1 = Number(r1); step = Number(step);
    if (!(Number.isFinite(r0) && Number.isFinite(r1) && Number.isFinite(step)) || !(r0 > 0 && r1 >= r0 && step > 0) || (r1 - r0) / step > 1000)
      return { error: 'radii: needs 0 < from <= to, a step > 0, and at most 1000 radii' };
    const radii = [];
    for (let k = 0; r0 + k * step <= r1 + 1e-9; k++) radii.push(Math.round((r0 + k * step) * 1e10) / 1e10);
    return { radii: radii };
  }
  function stretch(data) {
    // The display's 5 % and 99.9 % levels from at most about 1e6 evenly strided pixels (every pixel was sorted on load)
    const n = data.length, step = Math.max(1, Math.floor(n / 1e6)), v = [];
    for (let i = 0; i < n; i += step) { const x = data[i]; if (Number.isFinite(x)) v.push(x); }
    v.sort(function (a, b) { return a - b; });
    if (!v.length) return { lo: 0, hi: 1 };
    return { lo: v[Math.floor(0.05 * v.length)], hi: v[Math.floor(0.999 * (v.length - 1))] };
  }
  function brightestStart(img, nx, ny) {
    let best = -Infinity, bx = 0, by = 0;
    for (let i = 2; i < ny - 2; i++) for (let j = 2; j < nx - 2; j++) {
      let s = 0; for (let a = -2; a <= 2; a++) for (let b = -2; b <= 2; b++) { const v = img[(i + a) * nx + j + b]; s += Number.isFinite(v) ? v : 0; }
      if (s > best) { best = s; bx = j; by = i; }
    }
    return [bx, by];
  }

  // ---------------- time and ADES ----------------
  // The Python's rules (domino_calibrator/ades.py mid_exposure), UTC only: DATE-AVG; MJD-AVG; the start (EXPSTART, DATE-BEG,
  // DATE-OBS with TIME-OBS, MJD-BEG, MJD-OBS) + EXPTIME/2 (or EXPOSURE); the middle of the start and DATE-END or MJD-END.
  // {time, note} or {error}; never a throw and never the start as the middle. TIMESYS other than UTC is
  // refused here (the Python converts TT and TAI): the user types the mid-exposure instead.
  function isoMs(s) {
    const m = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2}(?:\.\d+)?)Z?$/.exec(String(s).trim());
    if (!m) return NaN;
    const y = +m[1], mo = +m[2], sec = Number(m[6]);
    const days = [31, (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0 ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    if (mo < 1 || mo > 12 || +m[3] < 1 || +m[3] > days[mo - 1] || +m[4] > 23 || +m[5] > 59 || sec >= 61) return NaN;   // 31 February rolled into March
    const t = new Date(0); t.setUTCFullYear(y, mo - 1, +m[3]); t.setUTCHours(+m[4], +m[5], 0, 0);   // Date.UTC read years 0-99 as 1900-1999
    return t.getTime() + sec * 1000;
  }
  function midExposure(h) {
    const tsys = blankValue(h.TIMESYS) ? 'UTC' : String(h.TIMESYS).trim().toUpperCase();   // TIMESYS = '' is UTC, as in the Python
    if (tsys !== 'UTC' && tsys !== 'UT')      // the command line named for TDB too, which it refuses
      return { error: 'TIMESYS ' + tsys + ': the page reads UTC only' + (['TT', 'TDT', 'TAI', 'IAT'].indexOf(tsys) >= 0 ? '; ' + CL + ' converts TT and TAI' : '') };
    const mjd = function (k) { const v = Number(h[k]); return Number.isFinite(v) ? (v - 40587) * 86400e3 : NaN; };
    const date = function (k) {
      let s = String(h[k]).trim();
      if (k === 'DATE-OBS' && s.indexOf('T') < 0) {
        if (h['TIME-OBS'] === undefined) return { error: 'DATE-OBS ' + s + ' has a date and no time' };
        s += 'T' + String(h['TIME-OBS']).trim();
      }
      const ms = isoMs(s);
      return Number.isFinite(ms) ? { ms: ms } : { error: k + ' ' + String(h[k]) + ' is not a FITS date-time' };
    };
    const has = function (k) { return !blankValue(h[k]); };
    let t, used;
    if (has('DATE-AVG')) { const d = date('DATE-AVG'); if (d.error) return d; t = d.ms; used = 'DATE-AVG'; }
    else if (has('MJD-AVG')) { t = mjd('MJD-AVG'); used = 'MJD-AVG'; }
    else {
      let start, key;
      for (const k of ['EXPSTART', 'DATE-BEG', 'DATE-OBS', 'MJD-BEG', 'MJD-OBS']) {
        if (!has(k)) continue;
        if (k === 'DATE-BEG' || k === 'DATE-OBS') { const d = date(k); if (d.error) return d; start = d.ms; } else start = mjd(k);
        key = k + (k === 'DATE-OBS' && String(h[k]).indexOf('T') < 0 ? ' + TIME-OBS' : '') + ' (the start)'; break;
      }
      if (key === undefined) return { error: 'no time in the header (DATE-AVG, MJD-AVG, DATE-OBS, MJD-OBS, ...)' };
      const expKey = has('EXPTIME') ? 'EXPTIME' : (has('EXPOSURE') ? 'EXPOSURE' : null);
      if (expKey) {
        const e = Number(h[expKey]);
        if (!(Number.isFinite(e) && e >= 0)) return { error: expKey + ' ' + h[expKey] + ' is not a number of seconds' };
        t = start + e * 500; used = key + ' + ' + expKey + '/2';
      } else if (has('DATE-END') || has('MJD-END')) {
        let end;
        const ek = has('DATE-END') ? 'DATE-END' : 'MJD-END';
        if (ek === 'DATE-END') { const d = date('DATE-END'); if (d.error) return d; end = d.ms; } else end = mjd('MJD-END');
        if (end < start)                        // halfway put it hours before the start, silently
          return { error: ek + ' ' + String(h[ek]).trim() + ' is before the start (' + key.replace(' (the start)', '') + "): the header's times disagree, so the mid-exposure is unknown" };
        t = start + (end - start) / 2; used = key + ' and ' + ek + ', halfway';
      } else return { error: 'no exposure time (EXPTIME, EXPOSURE) and no DATE-AVG, MJD-AVG or DATE-END: the mid-exposure is unknown' };
    }
    if (!Number.isFinite(t)) return { error: 'the header time is not a number' };
    if (Math.abs(t) > 8.64e15) return { error: 'the header time (' + used + ') is out of range: not a date' };   // toISOString threw RangeError
    const year = new Date(Math.round(t)).getUTCFullYear();   // '+010072-...' went into the time box
    if (year < 0 || year > 9999) return { error: "the header's time (" + used + ') falls in the year ' + year + ', outside the years 0000-9999 a record can hold' };
    return { time: new Date(Math.round(t)).toISOString().slice(0, 22) + 'Z', note: 'obsTime from ' + used };
  }

  // The record: the Python's ades_psv (version 2022; every value the user's, checked against the schema's patterns and
  // the MPC's lists, read 27 Sept 2026). {psv, notes} or {error}, the error naming every field that is missing or wrong;
  // notes say what the user should know about a record that stands (a deprecated catalogue, as the command line says).
  const PERMID = /^(?:\d+(?:[IPD](?:-[A-Z]{1,2})?)?|(?:Mars|Jupiter|Saturn|Uranus|Neptune) \d{1,3}|\(\d+\) \d{1,3})$/;
  const PROVID = /^(?:\d{4} [A-HJ-Y][A-HJ-Z]\d*|\d{4} (?:P-L|T-[123])|[ADCPX]\/\d{4} [A-Z]{1,2}\d*(?:-[A-Z])?|S\/\d{4} (?:[MJSUN]|\((?:\d+|\d{4} [A-HJ-Y][A-HJ-Z]?\d+)\)) \d+|A[89]\d{2} [A-HJ-Y][A-HJ-Z])$/;
  const MODES = ['CCD', 'CMO', 'VID', 'TDI'];
  const AST_CATS_DEPRECATED = ['UCAC3', 'UCAC2', 'UCAC1', 'USNOB1', 'USNOA2', 'USNOSA2', 'USNOA1', 'USNOSA1', 'Tyc2', 'Tyc1', 'Hip2', 'Hip1', 'ACT', 'GSCACT', 'GSC2.3', 'GSC2.2', 'GSC1.2', 'GSC1.1',
    'GSC1.0', 'GSC', 'SDSS8', 'SDSS7', 'CMC15', 'CMC14', 'SSTRC4', 'SSTRC1', 'MPOSC3', 'PPM', 'AC', 'SAO1984', 'SAO', 'AGK3', 'FK4', 'ACRS', 'LickGas', 'Ida93', 'Perth70',
    'COSMOS', 'Yale', 'ZZCAT', 'IHW', 'GZ', 'UNK'];
  const AST_CATS = ['Gaia_Int', 'PS1_DR2', 'PS1_DR1', 'ATLAS2', 'Gaia3', 'Gaia3E', 'Gaia2', 'Gaia1', 'Gaia2016', 'URAT1', 'UCAC5', 'UCAC4', 'PPMXL', 'NOMAD', '2MASS', 'UBSC']
    .concat(AST_CATS_DEPRECATED);
  // The command line's own rules and words (ades.py): the package's version; the MPC's codes with
  // no fixed position (ObsCodesF.html, read 1 Oct 2026 11:55:11 UTC: runs/MPC_OBSCODES_NO_POSITION_2026-10-01.json), for which
  // ADES's Location Group must be present and this page does not write it; ADES's place for the software (Table 18: software,
  // astrometry); 6 decimals for ra and dec, his fixed default far below any ground uncertainty (the page has no rms).
  const VERSION = '0.1.0';
  const NO_FIXED_POSITION = ['245', '247', '249', '250', '258', '270', '273', '274', '275', '288', '289', '311', '313', '314', '315',
    '332', '335', '336', '338', '339', 'C49', 'C50', 'C51', 'C52', 'C53', 'C54', 'C55', 'C56', 'C57', 'C58', 'C59'];
  const SOFTWARE = 'domino-calibrator ' + VERSION + " (zero-aperture position, through the image's own plate solution)";
  const DECIMALS = 6;
  function hex4(c) { const h = c.toString(16).toUpperCase(); return h.length >= 4 ? h : ('000' + h).slice(-4); }   // Python's %04X
  function unprintable(v) {              // a control character, or a lone surrogate (bytes that were not UTF-8), as ades.py says
    const s = String(v === undefined || v === null ? '' : v);
    for (let i = 0; i < s.length; i++) {
      const c = s.charCodeAt(i);
      if (c >= 0xD800 && c <= 0xDBFF && i + 1 < s.length && s.charCodeAt(i + 1) >= 0xDC00 && s.charCodeAt(i + 1) <= 0xDFFF) { i++; continue; }
      if (c >= 0xD800 && c <= 0xDFFF) return 'holds bytes that are not UTF-8 (U+' + hex4(c) + '): ADES text is UTF-8';
      if (c < 0x20 || (c >= 0x7F && c <= 0x9F)) return 'holds a control character (U+' + hex4(c) + '): ADES names hold printable characters only';
      if (c === 0x2028 || c === 0x2029 || (c & 0xFFFE) === 0xFFFE || (c >= 0xFDD0 && c <= 0xFDEF))   // they break the MPC's tools
        return 'holds U+' + hex4(c) + ", a character the MPC's tools cannot read (a line or paragraph separator, or a noncharacter): remove it";
    }
    return null;
  }
  function designationField(desig) {
    const d = String(desig === undefined || desig === null ? '' : desig).trim();
    return PERMID.test(d) ? 'permID' : (PROVID.test(d) ? 'provID' : null);
  }
  function text(v, width) {
    const s = v === undefined || v === null ? '' : String(v).trim();
    return s && s.length <= width && s.indexOf('|') < 0 && !/[\r\n]/.test(s) ? s : null;
  }
  function mergeHeaders(primary, image) {   // the primary's cards under the image HDU's; a blank image card hides nothing
    const m = Object.assign({}, primary || {});
    Object.keys(image || {}).forEach(function (k) { if (!blankValue(image[k])) m[k] = image[k]; });
    return m;
  }
  function names(v) {                     // separated by semicolons or line breaks: "Smith, J." is one name
    const a = Array.isArray(v) ? v : String(v === undefined || v === null ? '' : v).split(/[;\r\n]/);
    return a.map(function (s) { return String(s).trim(); }).filter(function (s) { return s.length; });
  }
  function adesPSV(rec) {
    rec = rec || {};
    const errs = [];
    const ra = Number(rec.ra), dec = Number(rec.dec);
    if (!(Number.isFinite(ra) && Number.isFinite(dec) && dec >= -90 && dec <= 90)) errs.push('ra/dec: not a sky position');
    const time = String(rec.time === undefined || rec.time === null ? '' : rec.time).trim();
    if (!/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d{1,6})?Z$/.test(time))
      errs.push(time ? 'time: ' + time + ' is not a mid-exposure time in UTC (like 2025-12-27T16:05:29.00Z)' : 'time: no mid-exposure time (type it in UTC, like 2025-12-27T16:05:29.00Z)');
    else if (!Number.isFinite(isoMs(time))) errs.push('time: ' + time + ' is not a date and time that exist (UTC)');   // the pattern passed month 13
    const stn = String(rec.stn || '').trim();
    if (!/^[A-Za-z0-9_]{3,4}$/.test(stn)) errs.push('stn: not an observatory code (3-4 letters or digits)');
    else if (NO_FIXED_POSITION.indexOf(stn.toUpperCase()) >= 0)
      errs.push('stn ' + stn + " has no fixed position in the MPC's list of observatory codes (a space-based or roving observatory): " +
        "ADES then needs the observer's own position (its Location Group: sys, ctr, pos1-pos3), which this tool does not write");
    const field = designationField(rec.desig);
    const dtext = String(rec.desig === undefined || rec.desig === null ? '' : rec.desig).trim();
    const nonascii = Array.from(dtext).find(function (ch) { return ch.codePointAt(0) > 0x7F; });
    if (nonascii !== undefined)
      errs.push('desig: ' + dtext + ' holds a character outside ASCII (U+' + hex4(nonascii.codePointAt(0)) + '): ADES designations are ASCII letters and digits');
    else if (!field) errs.push("desig: neither a permanent (3I, 1P) nor a provisional designation (C/2025 N1) by the ADES schema's patterns");
    if (!rec.mode) errs.push('mode: choose one (CCD; CMO for a CMOS camera; VID; TDI)');
    else if (MODES.indexOf(rec.mode) < 0) errs.push("mode: not one of the MPC's current modes for an image (" + MODES.join(', ') + '); a CMOS camera is CMO');
    if (AST_CATS.indexOf(rec.astCat) < 0) errs.push("astCat: not on the MPC's catalogue list (e.g. Gaia3)");
    const ms = names(rec.measurers), obs = names(rec.observers);
    const first = function (vs) { for (const v of vs) { const b = unprintable(v); if (b) return b; } return null; };
    const odd = { submitter: first([rec.submitter]), measurers: first(ms), observers: first(obs), 'observatory name': first([rec.observatoryName]),
      design: first([rec.design]), detector: first([rec.detector]) };
    Object.keys(odd).forEach(function (k) { if (odd[k]) errs.push(k + ': ' + odd[k]); });
    const sub = text(rec.submitter, 100); if (!odd.submitter && !sub) errs.push('submitter: not a name (1-100 characters, no |)');
    if (!odd.measurers && (!ms.length || ms.some(function (m) { return !text(m, 100); }))) errs.push('measurers: not one or more names');
    if (!odd.observers && obs.some(function (m) { return !text(m, 100); })) errs.push('observers: not names');
    const oname = rec.observatoryName ? text(rec.observatoryName, 100) : null; if (!odd['observatory name'] && rec.observatoryName && !oname) errs.push('observatory name: not a name');
    const design = text(rec.design, 35); if (!odd.design && !design) errs.push('design: not a telescope design (1-35 characters, no |)');
    const ap = String(rec.aperture === undefined || rec.aperture === null ? '' : rec.aperture).trim();
    if (!(ap.length <= 6 && /^(0|[1-9][0-9]*)(\.[0-9]*)?$/.test(ap) && Number(ap) > 0)) errs.push('aperture: not an aperture in metres (a positive decimal, at most 6 characters)');
    const det = text(rec.detector, 25); if (!odd.detector && !det) errs.push('detector: not a detector (1-25 characters, no |)');
    const rem = String(rec.remarks || 'zero-aperture extrapolated position').replace(/\|/g, '/').replace(/[\r\n]/g, ' ');
    if (rem.length > 300) errs.push('remarks: longer than 300 characters');
    if (errs.length) return { error: errs.join('; ') };
    const unit = Math.pow(10, DECIMALS);
    let r = Math.round((((ra % 360) + 360) % 360) * unit) / unit;
    if (r >= 360) r -= 360;                            // 359.9999999 is 0.000000, not 360.000000
    const f = [[field, String(rec.desig).trim()], ['mode', rec.mode], ['stn', stn], ['obsTime', time], ['ra', r.toFixed(DECIMALS)],
      ['dec', (dec < 0 ? '-' : '+') + Math.abs(dec).toFixed(DECIMALS)], ['astCat', rec.astCat], ['remarks', rem]];
    const w = f.map(function (p) { return Math.max(p[0].length, String(p[1]).length); });
    const pad = function (s, n) { s = String(s); while (s.length < n) s += ' '; return s; };
    const lines = ['# version=2022', '# observatory', '! mpcCode ' + stn].concat(oname ? ['! name ' + oname] : [],
      ['# submitter', '! name ' + sub], obs.length ? ['# observers'].concat(obs.map(function (m) { return '! name ' + m; })) : [],
      ['# measurers'].concat(ms.map(function (m) { return '! name ' + m; })), ['# telescope', '! design ' + design, '! aperture ' + ap, '! detector ' + det],
      ['# software', '! astrometry ' + SOFTWARE],
      [f.map(function (p, i) { return pad(p[0], w[i]); }).join('|'), f.map(function (p, i) { return pad(p[1], w[i]); }).join('|')]);
    const notes = AST_CATS_DEPRECATED.indexOf(rec.astCat) >= 0 ? ['astCat ' + rec.astCat + " is on the MPC's deprecated list"] : [];   // round 2, 4.4
    ms.concat(obs).filter(function (m) { return m.indexOf(',') >= 0; }).forEach(function (m) {   // "A. N. Observer, B. Other" is one name
      notes.push("a comma does not separate names here: '" + m + "' is written as one name (separate names with ; or a new line)");
    });
    return { psv: lines.join('\n') + '\n', notes: notes };
  }


  // ---------------- a comet measured, the command line's rules in its words (cli.py, comet_check) ----
  const START_MAX = 1.5, SNR_MIN = 10, TIES_MAX = 3, SKY_IN = 12, SKY_OUT = 24, SKY_MIN = 50, OTHER_FRAC = 0.2;
  const SINGLE_FRAC = 0.1;             // a peak whose four neighbours hold under this share of its height above the sky is one pixel
  function g(v) { return String(Number(v.toPrecision(6))); }            // Python's %g, for the values these rules print
  function ceilingOf(h) {                // the data's largest value when its pixels are integers (BITPIX > 0), through BSCALE, BZERO
    const bp = Number(h.BITPIX); if (!(bp > 0)) return null;
    const bs = blankValue(h.BSCALE) ? 1 : Number(h.BSCALE), bz = blankValue(h.BZERO) ? 0 : Number(h.BZERO);
    if (!Number.isFinite(bs) || !Number.isFinite(bz) || !(bs > 0)) return null;
    return (bp === 8 ? 255 : Math.pow(2, bp - 1) - 1) * bs + bz;
  }
  function levelOf(h) {
    for (const k of ['SATURATE', 'SATLEVEL']) { if (blankValue(h[k])) continue; const v = Number(h[k]); if (Number.isFinite(v)) return [k, v]; }
    return null;
  }
  function cometCheck(img, nx, ny, o, start, auto, h) {
    const nok = o.ok.filter(Boolean).length;
    if (nok < o.ok.length) return 'only ' + nok + ' of ' + o.ok.length + ' radii converged: the fit had too little to hold';
    const x0 = o.x0, y0 = o.y0, d = Math.hypot(x0 - start[0], y0 - start[1]);
    if (d > START_MAX) return 'the fit ended ' + d.toFixed(1) + ' px from its start: start on the comet, within ' + START_MAX.toFixed(1) + ' px of where the fit ends';
    const rmax = Math.max.apply(null, o.radii);
    const i0 = Math.max(Math.floor(y0 - SKY_OUT), 0), i1 = Math.min(Math.ceil(y0 + SKY_OUT) + 1, ny);
    const j0 = Math.max(Math.floor(x0 - SKY_OUT), 0), j1 = Math.min(Math.ceil(x0 + SKY_OUT) + 1, nx);
    const core = [], sky = [];
    let pkv = -Infinity, pi = -1, pj = -1;   // the peak pixel, the first of its value in row order, as numpy's argmax
    for (let i = i0; i < i1; i++) for (let j = j0; j < j1; j++) {
      const v = img[i * nx + j]; if (!Number.isFinite(v)) continue;
      const r = Math.hypot(j - x0, i - y0);
      if (r <= rmax) { core.push(v); if (!(v <= pkv)) { pkv = v; pi = i; pj = j; } } else if (r > SKY_IN && r <= SKY_OUT) sky.push(v);
    }
    if (!core.length) return 'no finite pixel within ' + g(rmax) + ' px of it: nothing was measured';
    let pk = -Infinity; for (const v of core) if (v > pk) pk = v;
    let ties = 0; for (const v of core) if (v === pk) ties++;
    const top = ceilingOf(h || {}), lev = levelOf(h || {});
    if (top !== null && pk >= top) return "its peak is clipped (at the data's ceiling, " + g(top) + '): a saturated star or core is not measured';
    if (lev !== null && pk >= lev[1]) return 'its peak is clipped (at ' + lev[0] + ', ' + g(lev[1]) + '): a saturated star or core is not measured';
    if (ties >= TIES_MAX) return 'its peak is clipped (' + ties + ' pixels share its value): a saturated star or core is not measured';
    if (sky.length < SKY_MIN) return 'fewer than ' + SKY_MIN + ' sky pixels ' + g(SKY_IN) + '-' + g(SKY_OUT) + ' px from it: nothing to tell it from noise';
    const med = median(sky);
    let sig = 1.4826 * median(sky.map(function (v) { return Math.abs(v - med); }));
    if (sig === 0) {                       // half the ring or more holds one value: the MAD is 0
      const mean = sky.reduce(function (s, v) { return s + v; }, 0) / sky.length;
      sig = Math.sqrt(sky.reduce(function (s, v) { return s + (v - mean) * (v - mean); }, 0) / sky.length);
      if (sig === 0) return 'its sky ring is flat (every pixel ' + g(SKY_IN) + '-' + g(SKY_OUT) + " px from it holds one value): nothing to tell it from noise; measure the image as it came from the camera";
    }
    const exc = pk - med;
    if (exc <= 0 || (sig > 0 && exc / sig < SNR_MIN))
      return 'its peak stands ' + (sig > 0 ? exc / sig : 0).toFixed(1) + ' times the sky noise above the sky, under ' + g(SNR_MIN) + ': too faint to take as measured';
    const nb = [];                          // the peak pixel's four neighbours
    for (const [a, b] of [[-1, 0], [1, 0], [0, -1], [0, 1]]) {
      const i = pi + a, j = pj + b;
      if (i >= i0 && i < i1 && j >= j0 && j < j1 && Number.isFinite(img[i * nx + j])) nb.push(img[i * nx + j]);
    }
    if (nb.length && nb.reduce(function (s, v) { return s + v; }, 0) / nb.length - med < SINGLE_FRAC * exc)
      return 'its peak is a single pixel (its four neighbours hold under a tenth of its height above the sky): a hot pixel or a cosmic ray, not a source; start on the comet';
    if (auto && nx >= 5 && ny >= 5) {       // the automatic start's own 5 x 5 sums (brightestStart), over the sky
      let taken = 0, other = -Infinity, ox = 0, oy = 0;
      for (let i = 2; i < ny - 2; i++) for (let j = 2; j < nx - 2; j++) {
        let s = 0; for (let a = -2; a <= 2; a++) for (let b = -2; b <= 2; b++) { const v = img[(i + a) * nx + j + b]; s += (Number.isFinite(v) ? v : med) - med; }
        if (Math.hypot(j - x0, i - y0) <= SKY_IN) { if (s > taken) taken = s; }
        else if (s > other) { other = s; ox = j; oy = i; }
      }
      if (taken > 0 && other >= OTHER_FRAC * taken && (sig === 0 || other / (5 * sig) >= SNR_MIN))
        return 'the automatic start took the brightest source, and another at least a fifth as bright is at (' + ox + ', ' + oy + '; ' + DS9 + "): give the comet's x and y";
    }
    return null;
  }

  // ---------------- the page's decision, one place (the page's show() and the tests read the same) ----------------
  const NO_WCS = 'the image is not plate-solved; plate-solve it (with astrometry.net or ASTAP, say) and load the solved file';
  function decide(c) {                  // {cur, hdus, o, start, auto} -> {w, rd, need}: the sky position, and what the record needs
    const o = c.o, need = [];
    let rd = null;
    if (Number.isFinite(o.x0)) {
      const hh = c.cur.header && c.cur.header.INHERIT === true ? mergeHeaders(c.hdus[0].header, c.cur.header) : (c.cur.header || {});   // the primary's SATURATE too
      const why = cometCheck(c.cur.data, c.cur.nx, c.cur.ny, o, c.start, c.auto, hh);
      if (why) need.push('a comet measured (' + why + ')');
    } else need.push('a comet measured (only ' + o.ok.filter(Boolean).length + ' of ' + o.ok.length + ' radii converged: the fit had too little to hold)');
    const w = makeWCS(c.cur.header, c.hdus[0].header, c.hdus);
    if (!w) need.push('a sky position (no WCS in the header: ' + NO_WCS + ')');
    else if (w.unsupported) need.push('a sky position (' + w.unsupported + ')');
    else if (Number.isFinite(o.x0)) {
      const bad = w.check(o.x0, o.y0);
      if (bad) need.push('a sky position (' + bad + ')'); else rd = w.pixToSky(o.x0, o.y0);
    }
    if (c.auto) need.push('a start you give: click on the comet to get a record (the automatic start takes the brightest source, which may be a star)');   // a record only from a start the observer gives
    return { w: w, rd: rd, need: need };
  }

  const api = { cometCheck: cometCheck, decide: decide, parseFITS: parseFITS, makeWCS: makeWCS, mergeHeaders: mergeHeaders, pixelOverlap: pixelOverlap, circleMoments: circleMoments, sigmaClippedMedian: sigmaClippedMedian,
    annulusBackground: annulusBackground, momentCentroid: momentCentroid, gaussFit: gaussFit, erf: erf, shrink: shrink, publishedRadii: publishedRadii,
    lineFit: lineFit, brightestStart: brightestStart, midExposure: midExposure, adesPSV: adesPSV, radiiFrom: radiiFrom, stretch: stretch, radiusText: radiusText,
    designationField: designationField, MODES: MODES, AST_CATS: AST_CATS, AST_CATS_DEPRECATED: AST_CATS_DEPRECATED, MAX_PIXELS: MAX_PIXELS,
    VERSION: VERSION, NO_FIXED_POSITION: NO_FIXED_POSITION, SOFTWARE: SOFTWARE, DS9: DS9 };
  Object.defineProperty(api, 'decodedPixels', { enumerable: true, get: function () { return decoded.pixels; } });
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.ZeroAp = api;
})(this);
