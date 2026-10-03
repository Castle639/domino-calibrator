<picture>
  <source media="(prefers-color-scheme: dark)" srcset="https://raw.githubusercontent.com/Castle639/domino-calibrator/main/page/logo-dark.svg">
  <img alt="domino-calibrator" src="https://raw.githubusercontent.com/Castle639/domino-calibrator/main/page/logo.svg">
</picture>

# domino-calibrator: open zero-aperture comet astrometry

Version 0.1.0. MIT license (`LICENSE`); to cite it, `CITATION.cff`, or its DOI, https://doi.org/10.5281/zenodo.23112591 (all its versions, on Zenodo). The files named here are in its repository, https://github.com/Castle639/domino-calibrator; the installed package holds the code only.

A comet's photocentre is not its nucleus: an asymmetric coma pulls the centroid off, by an amount that depends on seeing, pixel scale, aperture and signal-to-noise. The *shrinking-aperture* method (D. J. Tholen; published form in Farnocchia et al. 2016, Icarus, arXiv:1507.01980, §2.1 and §3.1) measures the photocentre in synthetic apertures of radius 2.0–6.0 px in steps of 0.1 px, fits a straight line to x(r) and y(r), and takes its value at r = 0.

This package is an open, tested implementation of that method, with a command line and a plain page: the same method, ported and checked against the Python. The folder also holds the study that tested the method on Hubble's images of 3I/ATLAS: its scripts, logs and summaries are in `runs/`, and what it found is below, with how far each finding was checked and its limits, so that anyone can check it.

## Install

It needs Python 3.11 or newer. Get it with `git clone https://github.com/Castle639/domino-calibrator`, and go into the folder it makes: `cd domino-calibrator`. From there, install it into a virtual environment of its own, since a system's own Python may refuse a plain `pip install` (`externally-managed-environment`). On Debian or Ubuntu, `python3 -m venv` needs a package of its own first: `apt install python3-venv` (as root, or with `sudo`). Then:

```
python3 -m venv .venv
source .venv/bin/activate
pip install .
```

On Windows, no activation is needed: `py -m venv .venv`, then `.\.venv\Scripts\python.exe -m pip install .`, and the command is `.\.venv\Scripts\domino-calibrator.exe`. Elsewhere the command is then `domino-calibrator`, the same as `python -m domino_calibrator.cli`, in any shell where the environment is active; a new shell needs it activated again. It was tested with Python 3.11, numpy 2.2.6, scipy 1.15.3 and astropy 6.1.7, and it asks for at least those versions, because no older ones were tested.

## Use

```
domino-calibrator cutout.fits                              # G, the published radii, the 2.5r-5r annulus
domino-calibrator cutout.fits --x 35.2 --y 34.8 --radii 2:6:0.1 --rms-noise 50 \
    --stn 568 --desig 3I --mode CCD --astcat Gaia3 --submitter "A. N. Observer" --measurer "A. N. Observer" \
    --telescope-design Reflector --telescope-aperture 0.5 --telescope-detector CCD
```

It prints the photocentre at every radius (a radius that did not converge has no position, only its reason), the zero-aperture position (and its RA/Dec through the cutout's WCS, or why there is none), the photocentre at r = 2 px (at the radius nearest to it, named, when the radii leave 2 px out), the trend per pixel of radius, and a **draft** ADES (PSV, version 2022) record through the cutout's WCS and mid-exposure time. The record is written only from real values: the time from the header (or `--obstime`), and the station, designation, mode, catalogue, submitter, measurers and telescope from you; without them it is refused with the reason, and the pixel answer stands. Check it with the MPC's validator before submitting anything (below, *Checking a record*). Pixels are 0-based: x = column, y = row; add 1 for ds9.

The tool writes an ADES record only from a start you give, on the comet, and only when its checks pass: a sound sky solution, every radius converged, and a bright, unclipped peak of more than one pixel well above the sky; a star or a galaxy can pass these checks too, so telling a comet from a star is yours. Otherwise it says why, and the pixel answer stands. A star inside the measuring ring pulls the answer toward it.

**Where it helps.** Know your pixel scale and your seeing before you trust the intercept: in the study below, the published extrapolation helps in 20 of 20 cells at ≤ 1.0″ seeing and ≤ 0.44″/px (less at low signal, SNR 20) and fails in 42 of 45 cells at ≥ 2″ seeing and ≥ 1.0″/px, where many small telescopes work. Look at the curve, too.

The command line exits with 0 when the measurement passed its gates (a record may still be refused for one of its values, with the reason), 2 when a gate refused (no comet measured, or no sky position), and 1 when it cannot measure at all.

A whole camera frame is slow: on a 26 Mpx frame, one run took about 42 s and 1.4 GB of memory (`runs/FIX_F3_WHOLE_FRAME_2026-10-01.txt`), and each `--rms-noise` redraw adds to it. Cut out the comet first.

**A cutout.** The page reads images up to 25 Mpx, and the command line is fastest on a cutout, so cut one out around the comet, keeping its WCS and its time. With astropy, for a frame whose WCS is TAN or TAN-SIP (as astrometry.net and ASTAP write them):

```python
from astropy.io import fits
from astropy.nddata import Cutout2D
from astropy.wcs import WCS

x, y = 2345.6, 1234.5                       # the comet in the frame, in pixels (0-based)
# the r before each path keeps a Windows path as typed: r'C:\Users\you\frame.fits'
with fits.open(r'frame.fits') as f:
    i = next(k for k, u in enumerate(f) if u.is_image and u.data is not None and u.data.ndim == 2)
    h = f[i].header                         # the first 2-D image: HDU 0 for most cameras, 1 for Hubble's and many pipelines'
    c = Cutout2D(f[i].data, (x, y), (101, 101), wcs=WCS(h, fobj=f))
    out = c.wcs.to_header(relax=True)       # the WCS, SIP included, moved to the cutout
    for k in ('DATE-OBS', 'TIME-OBS', 'DATE-AVG', 'MJD-OBS', 'EXPTIME', 'EXPOSURE', 'TIMESYS', 'RADESYS', 'EQUINOX'):
        for g in (h, f[0].header):          # the image's own card first, then the file's first header
            if k in g:
                out[k] = g[k]               # the time and the frame, which the record needs
                break
    fits.PrimaryHDU(c.data, out).writeto(r'cutout.fits')
```

Then measure `cutout.fits`: its pixels are the cutout's, and its sky positions the frame's.

With `--rms-noise N`, the zero-aperture position is measured again over N redraws of the noise of the comet's own sky ring, 12–24 px from it, and its scatter is printed beside the record, in arcsec at two significant figures, with how rough that many redraws make it; its correlation is printed only from enough redraws. The time the redraws will take is printed first. The record carries no rmsRA, rmsDec or rmsCorr from it: ADES defines rmsRA and rmsDec as the random uncertainty of the whole reduction, and this scatter is the sky-noise part only, without the plate solution's error. To report them, add your plate solution's random error to each in quadrature, write them at two significant figures, as ADES asks, and give ra and dec the decimals ADES's rule gives for them, `DP = CEILING(1 − LOG10(SIGMA))` with SIGMA in degrees. The record writes ra and dec at 6 decimals.

In Python:

```python
from domino_calibrator import shrink
o = shrink(image, x_start, y_start, estimator='G')      # o['x0'], o['y0']: zero aperture; o['x'], o['y']: the curve;
                                                        # o['ok'], o['reason']: per radius
```

**The page:** `page/index.html` (with `page/zeroap.js` and its fonts, `page/fonts/`, beside it) runs the same method, ported and checked against the Python, in a browser: open the file, load a FITS cutout, click the comet, press *Measure*. Nothing is uploaded.

Look at the curve before trusting the intercept: the study below shows where a straight line to r = 0 helps and where it makes the position worse.

## The estimators

- **G, the symmetric fit.** A circular Gaussian integrated over each pixel (free amplitude, centre and width), fitted by least squares weighted by each pixel's exact overlap with the aperture; the aperture re-centres on the fit until it moves < 1e-4 px. Background: the sigma-clipped median of the 2.5r–5r annulus (the paper's default), or a known value. This is the reading closest to "a model designed to fit the symmetric light distribution from a point source" (Farnocchia et al. 2016, §2.1); the paper does not publish which function, weighting or re-centring Tholen's software uses.
- **M, the moment photocentre.** The first moment of (image − background) over exact circle–pixel overlaps, re-centred on itself until it moves < 1e-6 px. With exact moments its fixed point does not depend on any constant background.
- **P, the brightness peak.** The vertex of a quadratic fitted to the 3×3 pixels around the brightest pixel.

## What the study found (checked by us, not yet by anyone outside)

**Check it on your own frames.** Below, a first finding was found but not yet checked as far as the rest. If you have ground images of 3I/ATLAS, or of any comet whose nucleus was located another way, measure them with this tool and tell us, in an issue on this repository, where they agree and where they don't.

**What was measured:** one comet, 3I/ATLAS, in five visits of Hubble's WFC3/UVIS (12 Dec 2025 – 22 Jan 2026), one filter (F350LP, which passes gas and dust together), 30 frames. Each frame was degraded to 26 ground set-ups, seeing 0.7–4″ and pixel scales 0.24–2.0″/px; one visit at one set-up is a cell, 130 cells in all. Every tally below is G's with the background known, the study's setting, each offset the noiseless mean over 16 pixel phases, unless it names another variant. The reference is HST's own zero-aperture photocentre, not the nucleus: "closer" and "further off" below mean from HST's photocentre. The classes were fixed before the data: WORKS if the extrapolation removes at least three quarters of the r = 2 px offset and adds no noise at low signal, FAILS if it removes less than a quarter or adds noise at high signal, HELPS otherwise; `runs/h3_report.py` holds the exact rules, for the classes and for "tailward". The boxes the tallies are counted in were drawn after the data, so every tally below names its box, and `runs/H3_REPORT_2026-09-27.txt` gives every cell for any other box. `tests/test_release_words.py` recounts each tally from `runs/H3_SUMMARY_2026-09-27.json` and `runs/H4_SUMMARY_2026-09-27.json`.

- **Direction.** At r = 2 px the photocentre is tailward in 104 of the 130 cells, all 26 set-ups of the first four visits, 4–42° from the antisolar direction there; in the fifth visit, taken near opposition, it is not. It is sunward in 0 of the 130 cells.
- **Size.** At r = 2 px the photocentre is 0.05–0.15″ from HST's at ≤ 1.0″ seeing and ≤ 0.44″/px, and 0.12–0.64″ at ≥ 2″ seeing and ≥ 1.0″/px.
- **The published extrapolation** (41 radii, 2.0–6.0 px): it helps in 20 of 20 cells at ≤ 1.0″ seeing and ≤ 0.44″/px, removing 27–73 % of the r = 2 px offset without noise; at low signal, SNR 20, the zero-aperture position is further from HST's photocentre than the r = 2 px one in 9 of the 20 cells at ≤ 1.0″ seeing and ≤ 0.44″/px; it fails in 42 of 45 cells at ≥ 2″ seeing and ≥ 1.0″/px; and sharp pixels alone are not enough: it fails in 15 of 40 cells at ≤ 0.44″/px with any seeing.
- **Worse than none.** The zero-aperture position is further off than no correction in 45 of the 130 cells, all at ≥ 0.70″/px.
- **The tool's default, and M** (first findings, recounted from the same run's summary, and again by a refuter from the run's report, M's count there inferred from its printed ratios). With the background from the 2.5r–5r annulus, the tool's default, G was measured in 50 of the 130 cells, all at ≤ 0.70″/px, and in none at ≥ 1.0″/px (the study's footprint: the annulus had to fit inside its degraded images; not a finding about the tool), so every tally above at ≥ 1.0″/px is G's with the background known only. Where it was measured, G with the background from the annulus helps in 20 of 20 cells at ≤ 1.0″ seeing and ≤ 0.44″/px and fails in 15 of 40 cells at ≤ 0.44″/px with any seeing, as G with the background known does, and is further off than no correction in 0 of the 50 measured cells. With M, the moment photocentre, the zero-aperture position is further off than no correction in 58 of the 130 cells, all at ≥ 0.70″/px, more often than with G.
- **Radii in arcsec or in units of the seeing do not rescue it** at ≥ 2″ seeing and ≥ 1.0″/px (H4, from one frame per visit): radii fixed at 0.88–2.64″ on the sky fail in 21 of the 24 measurable cells at ≥ 2″ seeing and ≥ 1.0″/px; radii on the sky were not measurable in 21 of the 45 cells at ≥ 2″ seeing and ≥ 1.0″/px, where their symmetric null failed, so the verdict the study fixed before the data is PARTIAL, by the letter; and radii in units of the seeing fail in 38 of 45 cells at ≥ 2″ seeing and ≥ 1.0″/px.
- **One regime**, a first finding, read from the table after the verdicts, from one frame per visit, with a few cells on a knife edge (its own bar, a six-frame re-run, has not been run): radii fixed at 0.88–2.64″ on the sky help in 24 of 25 cells at 0.70–1.0″/px with seeing ≤ 1.5″, where the published radii fail in 15 of 25 cells at 0.70–1.0″/px with seeing ≤ 1.5″.

No rule for which radii to use at your pixel scale is given here: that waits for an outside check.

## Limits

- One comet, five visits, one filter. F350LP passes gas and dust together; a ground filter may weigh them differently.
- The reference is HST's own zero-aperture photocentre, not the nucleus. For model comae it sits within a few milliarcseconds of the nucleus (a first finding, model-dependent); whether 3I's coma is like the models is untested.
- The boxes were drawn after the data. `runs/H3_REPORT_2026-09-27.txt` and `runs/H4_REAL_REPORT_2026-09-27.txt` give every cell, so any other box can be counted.
- Seeing is Gaussian; there is no guiding, tracking or atmospheric dispersion, and the noise is a simple sky-plus-read-noise model.
- G is our reading of Tholen's unpublished fitting function; his own software may differ.

## How it was tested

- `tests/`, with the standard library's `unittest`, from the checkout's root, whatever it is called: `python -m unittest discover -s tests -t .` They cover exact apertures against geometry and brute force; the estimators on exact sources; the closed-form coma integrals against quadrature; the renderer, the sky map, the resampler and the degrader; the ADES layout, and the MPC's own validator (IAU ADES-Master) on the records; the command line end to end; the page's JavaScript against the Python through Node and headless Chromium; `pip install` into fresh environments; and these words, recounted from the summaries. A test that needs what a machine lacks skips and says why: Hubble's frames, the 30 of the study, which `python tools/fetch_frames.py 22 03 04 05 06` brings from MAST into `data/hst-3i/`, each checked against its committed checksum; Node and Playwright, for the page (`npm install playwright`, then `npx playwright install chromium`; `PLAYWRIGHT_MODULE` names Playwright's folder); the MPC's validator, IAU ADES-Master installed with `pip install --target` (`ADES_PYLIB` names that folder, `ADES_MASTER` the clone); PyPI, for the tests that install the package afresh; and a Debian or Ubuntu system Python, for the install block's own test. `python -m tests.strict` runs the same tests and fails on any skip it is not told to allow, as the CI does. Off Debian or Ubuntu, the install block's own tests need what only those systems have: allow their skips with `python -m tests.strict --may-skip test_k8_ --may-skip test_k10_`, as the CI does on Windows and macOS; on Windows, which hands Python its arguments as UTF-16 so that raw bytes cannot reach the tool, add `--may-skip test_the_command_line_with_raw_bytes_in_argv`, as the CI does there; without a Python 3.11, the tested one, add `--may-skip test_k6_`.
- **Checking a record.** The MPC's own validator is IAU ADES-Master (github.com/IAU-ADES/ades-master). Clone it beside this checkout, not inside it (the suite compiles every Python file inside the checkout, and one of ADES-Master's files is written for an older Python), and install its package into a folder of its own beside it too, with the Python you run it with; from the checkout's root: `pip install --target ../ades-lib ../ades-master`. Then, with `PYTHONPATH=../ades-lib`, `python -m ades.psvtoxml record.psv record.xml` and `python -m ades.valsubmit record.xml`: the first line of `valsubmit.file` says `submit is OK` when the MPC's schema and lists accept the record. On Windows, set `PYTHONUTF8=1` first, so that it reads the record as UTF-8.
- A refuter is an AI agent we sent to find errors in a run or a claim.
- S0, the controls: the pipeline against an analytic fixed point, and symmetric and noisy nulls (`runs/S0a_RUNLOG_2026-09-27.txt`, `runs/S0b_RUNLOG_2026-09-27.txt`, `runs/S0c_RUNLOG_2026-09-27.txt`).
- S1, a synthetic grid (`runs/S1_RUNLOG_2026-09-27.txt`): its readings are first findings and are not repeated here, because a refuter corrected two of them.
- H0–H4, Hubble's frames degraded to the ground: the scripts, logs and summaries in `runs/`, and the tallies above.

## Modules

| module | what it is |
|---|---|
| `domino_calibrator/apertures.py` | exact circle–pixel overlap: area and first moments in closed form |
| `domino_calibrator/estimators.py` | M, G, P and the annulus background |
| `domino_calibrator/shrink.py` | the published sequence and its extrapolation |
| `domino_calibrator/synth.py` | synthetic comets: a nucleus and a k/ρ coma with an asymmetry term (dipole, grow, fade), seeing, pixels, noise |
| `domino_calibrator/degrade.py` | a sharp north-up image to a ground telescope: seeing, ground pixels at any phase |
| `domino_calibrator/hst.py` | Hubble's frames: load, locate, clean against siblings, resample north-up through the full WCS |
| `domino_calibrator/hstpsf.py` | the study's TinyTim PSF for H2 (`runs/h2_injection.py`); not in the installed package, since it needs TinyTim and the Castle's psfkit recipe |
| `domino_calibrator/ades.py` | the ADES record |
| `domino_calibrator/cli.py` | the command line, `domino-calibrator` |
| `page/` | the plain page and its engine (`page/zeroap.js`), with a Node harness and a headless-browser check |

## Credits

- **The frames.** The study uses observations made with the NASA/ESA Hubble Space Telescope, obtained from the Mikulski Archive for Space Telescopes (MAST) at the Space Telescope Science Institute (STScI), which is operated by the Association of Universities for Research in Astronomy, Inc., under NASA contract NAS 5-26555. They are from Hubble programme 18152 (PI: Man-To Hui).
- **The method.** D. J. Tholen's shrinking-aperture method, in its published form: Farnocchia, D., Chesley, S. R., Micheli, M., et al. 2016, "High precision comet trajectory estimates: the Mars flyby of C/2013 A1 (Siding Spring)", Icarus 266, 279–287, `doi:10.1016/j.icarus.2015.10.035` (arXiv:1507.01980), §2.1 and §3.1. That paper cites an earlier account, Tholen & Chesley 2004, BAAS 36, 1151, an abstract.

## Who made it

A Castle product from Domino Observatory. Built by Annie, the Castle's AI. A human approves every release.

The Castle is Domino Observatory's private workspace, where its people and Annie work. Domino Observatory is a project, not an observing station. Questions, reports and findings: the repository's issues, https://github.com/Castle639/domino-calibrator/issues.

The page's typeface is Inter, by the Inter Project Authors, under the SIL Open Font License: its files are in `page/fonts/`, unchanged, with the licence as `page/fonts/OFL.txt`. Everything else here is under the MIT license (`LICENSE`).
