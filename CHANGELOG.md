# Changes

## 0.1.0 — not yet released

*Not yet on PyPI, with no DOI, and its page not yet on GitHub Pages.*

The first release of domino-calibrator: open zero-aperture comet astrometry. It is the shrinking-aperture method (D. J. Tholen; published form in Farnocchia et al. 2016, Icarus, arXiv:1507.01980), as a Python package with a command line and a plain page: the same method, ported and checked against the Python.

**The package**, `domino_calibrator`: Python 3.11 or newer, with numpy, scipy and astropy at the versions it was tested with or newer (numpy 2.2.6, scipy 1.15.3 and astropy 6.1.7). Install it from a clone into a virtual environment, as `README.md` says.
- **The command line**, `domino-calibrator` (the same as `python -m domino_calibrator.cli`). It prints:
  - the photocentre at every radius of the published sequence (2.0–6.0 px in steps of 0.1 px);
  - the zero-aperture position, with its RA/Dec through the cutout's WCS;
  - the photocentre at r = 2 px and the trend per pixel of radius;
  - a **draft** ADES record (PSV, version 2022), written only from real values, to be checked with the MPC's validator before anything is submitted.

  `--rms-noise N` gives the sky-noise scatter of the zero-aperture position, drawn from the noise of the comet's own sky ring, 12–24 px from it, printed beside the record in arcsec at two significant figures and not written in it, since ADES's rmsRA and rmsDec are the whole reduction's uncertainty; the time it will take is printed first.
- **The record's rule**: The tool writes an ADES record only from a start you give, on the comet, and only when its checks pass: a sound sky solution, every radius converged, and a bright, unclipped peak of more than one pixel well above the sky; a star or a galaxy can pass these checks too, so telling a comet from a star is yours. Otherwise it says why, and the pixel answer stands. A star inside the measuring ring pulls the answer toward it. The record follows ADES's own description:
  - a station with no fixed position in the MPC's list (space-based or roving) gets no record, since ADES then needs the observer's own position;
  - ra and dec at 6 decimals, and no rmsRA or rmsDec from the sky noise alone;
  - the software named in ADES's `# software` block;
  - names asked as initials, then surname; a control character or bytes that are not UTF-8 in a name, and a designation outside ASCII, refused with the reason.
- **The command line's exit codes**: 0 when the measurement passed its gates, 2 when a gate refused (no comet measured, or no sky position), 1 when it cannot measure at all.
- **Its input and output**: a corrupt header is named at the header stage; a WCS number the header cannot read gives no sky position, one written with a D exponent is read as the header reads it, and no record is written from a WCS that differs from its header; the primary's WCS is read for an extension only with `INHERIT = T`; a closed pipe ends quietly; positions are 0-based, and the output says so beside each: "0-based; add 1 for ds9".
- **The estimators**: G, the symmetric fit, the command line's and the page's default; M, the moment photocentre (the library's `shrink()` defaults to M); P, the brightness peak, in the library as `peak_quadratic()` and not offered for the line, since a peak does not move with the aperture.
- **The page**, `page/index.html`, runs the same method, ported and checked against the Python, in a browser, with the same rules in the same words. It reads images up to 25 Mpx; the README gives a cutout recipe. Nothing is uploaded.

**The study**: a test of the method on Hubble's images of 3I/ATLAS, checked by us, not yet by anyone outside. Its findings, with their limits and the boxes they are counted in, are in `README.md`, and its scripts, logs and summaries are in `runs/`. No rule for which radii to use at a given pixel scale is given: that waits for an outside check.

**Tested** with the standard library's `unittest`, from the checkout's root, whatever it is called:
- exact apertures against geometry;
- the estimators on exact sources;
- the page's JavaScript against the Python;
- the MPC's own validator on the records;
- `pip install` into fresh environments;
- the README's words, recounted from the summaries.

The CI runs the suite on Linux (Python 3.11 to 3.14), Windows and macOS, on every push.

**On Windows**, the MPC's validator (ADES-Master's `psvtoxml` and `valsubmit`) reads files in the system's code page and stops on a record naming someone outside it (Łukasz, say). Run it with Python's UTF-8 mode on: set `PYTHONUTF8=1`. The record itself is always UTF-8.

**Known limits**: one comet, five visits, one filter. The reference is HST's own zero-aperture photocentre, not the nucleus. The boxes were drawn after the data. `README.md` says more.

A Castle product from Domino Observatory. Built by Annie, the Castle's AI.
