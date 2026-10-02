# runs/

The study's records, and the checks made by the rooms that hardened, audited and released the tool. A date in a name is the
day of the run (UTC). Each of the study's scripts names, in its docstring, the bar it was run against, written and committed
before it ran.

**To reproduce the study:** `python tools/fetch_frames.py --all` brings Hubble's 30 frames of 3I/ATLAS from MAST into
`data/hst-3i/`, each checked against its committed checksum; then run a study's script from the repository's root, and
compare its log and summary with the ones here. H2 also needs TinyTim 7.5 (`tools/psfkit.py`).

**How these records speak**: these files are the working records of the rooms that built, hardened, audited and
released the tool, and they keep their own shorthand. A *room* is one working session, and a *round* one round of
hardening; a *bar* is a run's pass condition, written and committed before the run, and a *prediction* its expected
outcome, stamped before it ran; a *refuter* is an AI agent sent, read-only, to find errors. Findings are named by the
record that found them and their number (B1′ a blocker, F8.4 an auditor's report 8, finding 4, T1.19 a round's test, R1.1
a regression), and a commit by its short hash. "His word", "his yes" and "his call" are the maintainer's decisions. The
package's own code and comments use none of this.

**The study**
- `S0*`, `s0*`: S0, the controls on synthetic comets: the pipeline against an analytic fixed point, and symmetric and
  noisy nulls.
- `S1_*`, `s1_*`: S1, a synthetic grid; its readings are first findings, not repeated in the README.
- `H[0-4]*`, `h[0-4]_*`: Hubble's frames, degraded to the ground. H0 prepares the 30 frames and the comet's positions
  (`h0_prepare.py`); H1 is the null, each frame made symmetric (`h3_grid.py null`); H2 asks how far HST's own
  zero-aperture position is from a known nucleus (`h2_injection.py`); H3 measures the frames on 26 ground set-ups
  (`h3_grid.py`: `H3_SUMMARY_*.json` holds every cell, `H3_REPORT_*` its table); H4 fixes the radii in arcsec and in
  units of the seeing (`h4_arcsec.py`, `H4_SUMMARY_*.json`). The README's tallies are recounted from the two summaries.
- `MPC_OBSCODES_*`: the MPC's observatory codes with no fixed position, read on 1 Oct 2026: the stations the record
  refuses.
- `FIX_F3_WHOLE_FRAME_*`, `fix_f3_whole_frame.py`: a whole camera frame's time and memory, as the README gives them.

**The checks**
- `hard_c*.py`, `*_C1_*`, `*_C2_*`: the science controls, run after every change to the code: C1 replays H4's first
  frames and must agree bit for bit; C2 re-runs H3's noisy cells, where every zero-aperture position must agree bit for
  bit, and the only differences allowed are the 43 known ones, where a radius that did not converge now reports no
  position. Bit for bit holds where numpy takes the same arithmetic paths as the machine that wrote these records;
  elsewhere, a float's last digits can differ.
- `*_bar*.py`, `*_PREDICTION_*`: each check's bar, committed before its run, and its prediction, stamped before it ran.
- `*_RUNLOG_*`, `*_SUITES_*`, `*_MEASURE_*`: their logs.
- `*_CAMERA_*`, `AUDIT_FACTS_*`: what the refuters (AI agents sent to find errors) read and ran. These logs, and the
  scripts that scanned them, are kept in our own records and left out of the public repository.
- The bars and logs of three rounds that took private words out of this public copy (F9, F13 and F14) are kept in
  our own records too, because they name what was taken out; their tests and science-control logs are here.
- `*.py`, `*.js`: the other scripts the checks ran: mutants, probes and lookups.
