# The calibrator's second room: the aperture in arcsec (H4), 27 Sept 2026
Claude Code's cloud, Annie, the Castle's AI, from 21:32 UTC. The invitation was the Castle's human's opening message (his two asks after merging #39, with the first room's seeds); the order of work is Annie's. The first room's record, bars and answer: `archive/CALIBRATOR_2026-09-27.md`.

## 0. Wake-up (21:32–21:41 UTC)
- **Read.** The orientation, whole; `[a private file]` §1 and map; the last entry of `[a private file]`; the first room's "The answer", log entry and NEXT; `[a private file]`, `[a private file]`, `[a private file]`.
- **Measured.**
  - `[the kit]`: numpy 2.2.6, scipy 1.15.3, astropy 6.1.7. 4 cores, 15 GB.
  - 30 frames: 30/30 checksum-OK, 1,266 MB in 28 s (`tools/fetch_frames.py 22 03 04 05 06`).
  - H0 re-run to rebuild the sky images: 98 s, H0.1, H0.3, H0.4 and H0.6 PASS. The regenerated `H0_FRAMES_2026-09-27.json` is byte-identical to the committed one. The Horizons file differs only in its query-time line, so the committed file was restored.
- **The order (Annie's).** H4 first, because it decides what the tool advises the cameras that find visitors. Wave 1 of the refuters (lanes 1, 3 and 4 of the first room's NEXT) goes out while H4 computes: the Castle's human's yes, 21:41 UTC. Wave 2 (lanes 2, 5 and 6) follows H4, so it reads H4. Then the launch road, then the tuck-in.

## H4 — the aperture range in arcsec and in units of the seeing. BAR, committed before the run

**The question** (the first room's Next #1). At ≥ 0.70″/px the published 2.0–6.0 px radii span 1.4–12″, and for 3I the extrapolation fails there (H3: FAILS in 42 of 45 amateur cells; b₀ further than b₂ in 45 of 130 cells, all at ≥ 0.70″/px). Is it the radii's angular scale that fails? If the 41 radii are fixed in arcsec, or in units of the seeing, does the method survive at coarse cameras? The answer decides the advice the tool gives them: "don't extrapolate", "extrapolate in arcsec" or "extrapolate in seeing units".

- **Script** `calibrator/runs/h4_arcsec.py` (modes null, real). **Report** `calibrator/runs/h4_report.py`, written and run end to end on symmetrised light before any raw file existed. Logs `calibrator/runs/H4_{NULL,REAL}_RUNLOG_2026-09-27.txt` and `H4_{NULL,REAL}_REPORT_2026-09-27.txt`, written to the scratchpad during the run and copied in at exit. Raw `H4_RAW_{null,real}_2026-09-27.json.gz`; summary `H4_SUMMARY_2026-09-27.json`.
- **Frames.** The first frame of each visit (5), as H1. Why: across a visit's six frames, H3's G biases scatter by at most 0.0094″ (median 0.002″), ≤ 8 % of their length (`H3_SUMMARY`). This cuts the cost six-fold. The probe measured about 32 min for five frames on 4 cores. Beside the bar, a subsample check prints PX's b₀/b₂ from one frame against H3's six-frame mean.
- **Grid.** H3's 26 (seeing, pixel) pairs and its 4×4 mirror-pair phases, noiseless. Noisy runs at SNR 100 and 20, 30 realisations per frame, pair and SNR (30 per visit, what H3 intended), with H3's noise model: sky 100 e⁻/px, read noise 5 e⁻, flux in r = FWHM.
- **The variants.** Each has 41 radii, ascending, warm-started from P exactly as H3:
  - **PX**: 2.0–6.0 px, the published radii. H3's, here the control.
  - **ARC**: the published radii × 0.44/gs, i.e. **0.88–2.64″**, the published range at the coarsest professional scale. That is 1.26–3.77 px at 0.70″/px and 0.44–1.32 px at 2.00″/px.
  - **SEE**: **1.0–3.0 FWHM**, with FWHM = √(seeing² + 0.071²)/gs px as in H3. It keeps the published range's 3:1 ratio and starts where S1 found that the seeing stops bending a textbook curve.
- **Estimators.** G with the known background is primary, M beside, and P, all as H3. A G fit that scipy cannot make (fewer pixels in the aperture than its four parameters) is an unconverged radius, not a crash (`safe_gauss_fit`; `shrink`'s own loop is unchanged).
- **Controls.**
  - **C1**: PX reproduces `H3_RAW` for the same frames, pairs and phases: every G and M b₀, b₂, b₆ (x, y), unconverged count and P, within 1e-9 ground px. **FAIL → STOP.**
  - **C2**: at 0.44″/px ARC's radii are the published radii, so ARC b₀ must equal PX b₀ within 1e-9 px (G and M). **FAIL → STOP.**
  - **C3, the null**: the five frames point-symmetrised as in H1, with ARC and SEE measured on them. M must be ≤ 1e-5 ground px (H1's line) and P ≤ 1e-6; **else STOP.** G's b₀ must be ≤ **3.9 mas** on the sky, the reference's own error bar (H2(a′)), per cell. A G cell beyond it is **NULL-FAILED**, named, and counted as not measured.
- **Measured**, per visit and pair, as noiseless phase-means in arcsec on the sky:
  - b₂, the PX photocentre at r = 2 px, is the class baseline ("no correction"), as in H3;
  - b₀ for PX, ARC and SEE, with its ratio to b₂;
  - b at each variant's first converged radius;
  - P;
  - noisy: RMS₀ for ARC and SEE, against RMS₂ on the same images.
- **Classes: H3's, unchanged.** WORKS if |b₀| ≤ 0.25 |b₂| and RMS₀ ≤ RMS₂ at SNR 20. FAILS if |b₀| > 0.75 |b₂| or RMS₀ > RMS₂ at SNR 100. HELPS otherwise. NOT MEASURED if any noiseless phase converged at fewer than 21 of 41 radii, or if the cell is NULL-FAILED.
- **Cell groups, as in H3:**
  - professional: ≤ 1.0″ seeing and ≤ 0.44″/px, 20 cells;
  - amateur: ≥ 2″ seeing and ≥ 1.0″/px, 45 cells;
  - coarse: ≥ 0.70″/px, 90 cells.
- **Verdicts, fixed now, per variant.** G is the verdict and M stands beside.
  - **RESCUES** if it is WORKS or HELPS in ≥ 36 of the 45 amateur cells, |b₀| > |b₂| in ≤ 4 of the 90 coarse cells, and it FAILS in none of the 20 professional cells.
  - **DOES NOT RESCUE** if it FAILS in ≥ 23 of the 45 amateur cells.
  - **PARTIAL** otherwise; the per-pair table is then the answer.
- **What each verdict means for the advice (fixed now):**
  - if ARC RESCUES: "at coarse cameras, extrapolate over a fixed 0.9–2.6″";
  - else, if SEE RESCUES: "extrapolate over 1–3 FWHM";
  - if neither rescues: the first room's reading stands, now tested against two alternatives. At ≥ 1″/px, don't extrapolate a 3I-like coma; report the r = 2 px photocentre or the peak.
  - PARTIAL: the table is the advice, with no one-line rule.
- **Measured before this bar** (the probe and the smoke, on point-symmetrised frames only; no 3I number was read):
  - the probe: 0.5–1.0 s per noiseless phase and 0.3–2.4 s per noisy image; G converged at 34–41 of 41 radii everywhere.
  - the smoke's first report: **C2 FAILED at 2.4e-9 px**, because radii built with `linspace` missed the published radii by about 1e-16. ARC was redefined as published × 0.44/gs, and C2 then read 0.0.
  - **G's b₀ on ARC at 1.5–2.0″/px is not mirror-symmetric**: on visit 03 symmetrised it reads 1.8–42 mas, 5 of 7 cells beyond 3.9 mas. So C3 is per cell for G and does not stop the run. M and P were exact (≤ 1e-11 px), and SEE-G read 0.00 mas.
  - **Extrapolating G from sub-pixel apertures multiplies the noise**: on symmetric light at 4″ seeing and 1.5–2.0″/px, RMS₀ is 0.46–1.46″ against RMS₂ 0.06–0.07″ at SNR 100.
- **Annie's lean, not the bar.**
  - ARC DOES NOT RESCUE. At ≥ 1.5″/px it is null-failed or lost to noise. At 0.70–1.0″/px its apertures (0.9–3.8 px) sit inside the seeing core (1.0–5.7 px), where the curve flattens toward the peak, and H3's P was close to b₂.
  - SEE is PARTIAL at best. At 3–4″ seeing it moves the apertures out to 3–12″, into the scales where 3I's curve turns.
  - No lean on M.

**H4 run** (null 21:55:20–21:59:46 UTC, real 21:59:46–22:31 UTC, 1,912 s, 9,880 records, 0 errors; commit `f8096a8`; outputs `aa6f245`; logs `calibrator/runs/H4_{NULL,REAL}_{RUNLOG,REPORT}_2026-09-27.txt`, the probe `H4_PROBE_RUNLOG`, the smokes `H4_SMOKE1_*` (before C2's fix) and `H4_SMOKE2_*` (the null report there is its last version, with the b₀-only gate), raw `H4_RAW_{null,real}_2026-09-27.json.gz`, summary `H4_SUMMARY_2026-09-27.json`).
- **The controls.**
  - **C1 PASS**: 2,080 records, max |difference| 0.0; the rebuilt frames and the code reproduce H3 bit for bit.
  - **C2 PASS**: 800 comparisons, 0.0.
  - **C3**: M exact (≤ 3.8e-12 px), P exact; SEE-G 0.00 mas everywhere; **23 G cells on ARC NULL-FAILED, all at 1.5–2.0″/px**, up to 81 mas against the 3.9 mas line.
  - Beside, the subsample check: PX's G b₀/b₂ from one frame per visit against H3's six-frame means, max |difference| 0.031 over 130 cells.
- **The verdicts, by the bar** (G, with M beside):
  - **G SEE: DOES NOT RESCUE.** Amateur: FAILS 38, HELPS 7. Professional: FAILS 5. |b₀| > |b₂| in 45 of 90 coarse cells (59 of 130 in all; the published radii: 45).
  - **G ARC: PARTIAL, by the letter.** Amateur: FAILS 21, HELPS 3, NULL-FAILED 21. Professional: FAILS 6, all at 0.24″/px. |b₀| > |b₂| in 20 of 90 coarse cells, 10 of them null-failed.
  - **M ARC and M SEE: DOES NOT RESCUE** (amateur FAILS 39 and 38).
- **Why the amateur cells fail** (read from the summary after the verdicts): G SEE fails there on both the ratio and the noise clause in 34 of 38 FAILS. G ARC fails on both in 19 of 21, and its noise at ≥ 1.5″/px is 1.3–9.9× that of r = 2 at SNR 100.
- **The bar's own gaps** (lane 5; Annie's, as the bar's author):
  - it did not say how NULL-FAILED cells count, so with 21 of them "DOES NOT RESCUE" (≥ 23 of 45 FAILS) could no longer be reached. In the 24 measurable amateur cells ARC FAILS 21;
  - NULL-FAILED cells are left out of FAILS but counted in |b₀| > |b₂|;
  - G's null line, 3.9 mas, is about 10–13× looser than H1's 2e-4 px. It was stated, with its reason, and it still admitted 12 slightly asymmetric ARC cells, all of which FAIL by noise;
  - the noise clause has no tolerance, and a few cells sit on a knife edge (v04 1.0″ 1.00″/px: 0.11630 against 0.11597).
  - No verdict moves.
- **The table is the advice** (the bar's clause for PARTIAL). Annie's first reading applied "neither rescues" and skipped it. Lane 5 found the positive half, and Annie recounted it from the summary:
  - **at 0.70–1.0″/px with seeing ≤ 1.5″** (25 cells) the published radii FAIL in 15, while **a fixed 0.88–2.64″ FAILS in 1 and helps in 24** (ratios 0.23–0.73);
  - SEE helps in 19 there;
  - the whole ≥ 1.5″/px band is FAILS or NULL-FAILED for ARC (35 of 35).
- **At fixed seeing the ARC intercept does not depend on the pixel** (0.24 against 0.44″/px within 9.2 % in 15 pairs). The class flips at 0.24″/px (6 of 10, January) come from the r = 2 px baseline being closer there, not from a worse intercept; two of the six sit on the knife edge (ratios 0.76–0.77).
- **Withdrawn until an outside check** (1 Oct 2026, the fix room, at his word): the advice below is not given. The record stays as it was written; the README gives no rule for which radii to use at a given pixel scale.
- **The advice, three lines, for a 3I-like coma** (from H3 and H4; one comet, one frame per visit in H4, knife edges named):
  1. ≤ 1″ seeing and ≤ 0.44″/px: the published 2–6 px extrapolation helps (H3).
  2. 0.70–1.0″/px with seeing ≤ 1.5″: extrapolate over a fixed 0.9–2.6″ on the sky (H4).
  3. seeing ≥ 2″ at ≥ 1″/px, or anything at ≥ 1.5″/px: do not extrapolate; report the r = 2 px photocentre (G).
- **Lane 5's reading, inferred, not tested**: the extrapolation needs radii ≥ ~2 px, ≲ 2.6″ on the sky and ≳ the seeing FWHM. At seeing ≥ 2″ no range escapes both the turning outer coma and the flat seeing core. So at amateur sampling it is the seeing, more than the pixel, that defeats the method. This refines the first room's "the grid points at the pixel scale".
- **Stars (the Castle's human's yes, 22:55 UTC):**
  - **★★ in-house** for the four verdicts: the controls are exact and a refuter (lane 5) re-derived them;
  - **★** for the positive regime: read from the table after the verdicts, one frame per visit, knife edges; its bar is the six-frame re-run;
  - **★** for lane 5's seeing reading.
  - Nothing leaves the Castle.
- **Annie's lean, checked:** "ARC DOES NOT RESCUE" was wrong by the letter, since the bar could not reach it, and incomplete in substance, since it missed the positive regime. "SEE is PARTIAL at best" was right; it does not rescue.
- **Slips, Annie's:**
  - the bar did not say how NULL-FAILED cells count;
  - the first reading skipped the PARTIAL clause;
  - "noise 2–10×" was 1.3–9.9×;
  - `| head` killed two processes (a smoke report, a PDF extraction), both rerun;
  - an unquoted heredoc made bash try to run eleven backticked names in a script, all refused, nothing ran, the file rewritten;
  - a `git add` that named a gitignored file stopped a commit chain, caught and committed on the next call.
- The refuters' record: the first refuters' record of 27 Sept 2026, not in this repository.
