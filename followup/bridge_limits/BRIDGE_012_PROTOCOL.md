# BRIDGE-012 protocol: the EEG <-> fMRI ceiling, both directions

Registered 2026-10-27 by @cc-c12, before any BRIDGE-012 score was computed. Ledger:
`presonance/ledgers/20261027-experiment-cable-ceiling-and-outreach.md`. Amendments are appended at the bottom, dated,
and never edit the registered text.

## 1. Question (Guhan, 2026-10-27)

"Test the ceiling, both ways, fMRI to EEG and EEG to fMRI, an absolute test, in the most logical form. fMRI and EEG
encode the same thing, neural activity, so the ceiling should be high. Maybe not across the entire brain, but for the
regions EEG actually captures, record how much of that translates." Purpose: a clear target for CABLE.

## 2. Why the obvious test is not enough (what the literature and our own data already say)

- **Measurement ceiling is not the neural ceiling.** BRIDGE-008 C2 measured split-voxel reliability of the targets at
  ~.96 (r ceiling ~.98). That bound counts heartbeat, breathing and motion as "signal", and EEG can only reach those
  through artifacts or through arousal. The neural ceiling sits somewhere between our person-calibrated .52 (C1) and
  .98. BRIDGE-008 already said pinning it down needs physiological recordings.
- **"Same neural activity" does not imply a high single-recording ceiling.** An electrode inside monkey V1 predicts
  resting BOLD in the same spot at only r ~.2-.3 (~10% of variance), <.1 with eyes open; even strong block stimulation
  shares just over 50% (Scholvinck et al. 2010 PNAS, full text read). Both signals are noisy, partial views of the
  neural state, plus their own non-neural parts (vascular/autonomic for BOLD; artifacts for EEG).
- **Two estimands that must not be merged** (FIELD_SWEEP_20261015 section 2): (a) stimulus-locked coupling, measurable
  with repeats and noise correction (Haufe 2018: corrected ~.8 in occipito-parietal cortex at group level); (b)
  within-person moment-to-moment state coupling, where no published ceiling exists.
- **EEG predicts BOLD by three routes:** (1) local: the same neurons drive scalp EEG and local BOLD; (2) shared state:
  arousal changes both EEG rhythms and BOLD everywhere, partly through autonomic/vascular effects (Gu et al. 2022
  NeuroImage, on ds003768; Ozbay et al. 2019); (3) artifact: physiological artifacts in EEG track physiological noise
  in BOLD. CABLE predicts thalamus and putamen, which EEG cannot see, so route 2 is large. BRIDGE-011 A11 found CABLE
  output on NATVIEW is almost unshared across viewers (stimulus-locked part ~0). Guhan's question is about route 1 in
  EEG-visible regions.
- **Time resolution is not the asymmetry.** For slow targets (< .15 Hz) the shared variance is symmetric. EEG -> fMRI
  loses spatial specificity (volume conduction, deep and closed-field sources); fMRI -> EEG loses everything faster
  than the hemodynamic response (~.15 Hz) and the stochastic part of oscillation power.

## 3. Logic of the test

Each recording = stimulus-locked part + state part + body part (heart, breathing, motion) + measurement noise. With
the *same movie shown twice to the same person in the same session, recorded simultaneously in both modalities*, the
stimulus-locked part is the only thing the two repeats share. Then, for a mapping f fitted on other people:

- rel_Y = corr(Y1, Y2): how much of the target is stimulus-locked (repeat reliability).
- rel_P = corr(f(X1), f(X2)): how much of the prediction is stimulus-locked.
- cross = mean[corr(f(X1), Y2), corr(f(X2), Y1)]: shared through the stimulus only (no shared state or noise).
- **rho_stim = cross / sqrt(rel_P * rel_Y)**: correlation between the stimulus-locked part of the prediction and the
  stimulus-locked part of the target, with all noise and state removed. rho_stim = 1 means the reproducible signal in
  one modality is a perfect linear copy of the reproducible signal in the other ("they encode the same thing").
  rho_stim^2 = share of the target's stimulus-locked variance that crosses over. A fitted f gives a lower bound on
  the best possible f; noise correction makes it an estimate of signal translation, not of a noisy score.
- **Single-run ceiling of the stimulus route = sqrt(rel_Y)** (what a perfect, noise-free stimulus-locked predictor would
  score on one run).
- same = mean[corr(f(X1), Y1), corr(f(X2), Y2)]; **same - cross** = the simultaneous state coupling the stimulus does
  not explain.

Regions EEG can see are defined from physics, not from results: a forward model (MNE fsaverage, 3-layer BEM,
normal-oriented cortical sources, CABLE's 26 channels) gives each Schaefer-100 parcel a visibility score. If the
local route works, rho_stim should be high in high-visibility cortex and fall in low-visibility cortex.

## 4. Data

NATVIEW (Telesford et al. 2023, CC BY), on the desktop (`presonance/data/neural_datasets/eeg_primary/natview`):
simultaneous 3 T EEG-fMRI (TR 2.1 s, BrainProducts cap), within-session repeats run-01/run-02 of dme, dmh, tp,
monkey1, monkey2, monkey5; inscapes (no repeat) used for training only. Schaefer-100 7-network atlas time series
(`desc-sm0`, primary; `desc-sm0gsr`, secondary), respiration belt (62.5 Hz), QRS markers in the EEG events, EyeLink
pupil/gaze/blinks, motion parameters. Clocks: `alignment_segment/` (validated earlier); movie onset = BrainVision
`S  1` minus the first `R128`, as in BRIDGE-011 A11. NATVIEW was used in BRIDGE-004/005/011 (held-out-movie CABLE r
.20 in A11); no hold-out is claimed here. This is a measurement of the data, not a model benchmark.

Exclusions (fixed now): a run is used if it has >= 60% valid EEG bins and finite atlas data; a pair needs both runs
and an onset from the markers in both; NATVIEW's `dme` and `dmh` share video but not audio and are never paired with
each other.

## 5. Signals (0.8 s grid, as CABLE)

- **EEG features:** the frozen BRIDGE-009 A6 families (`b9feat2.frozen_families`), computed exactly as A11 does,
  from local files.
- **BOLD targets:** 100 parcels + 7 network means + global mean, `b9lib.target_lp` (< .15 Hz).
- **EEG targets (reverse direction):** 26 channels x 5 bands log power (`cb5_2`) + global alpha, low-passed < .15 Hz
  and z-scored like BRIDGE-010. Also a split-taper version: band power from DPSS tapers {0, 2} and {1, 3} (NW 2.5,
  2 s windows), giving two near-independent estimates of the same power for the EEG measurement ceiling.
- **Body signals:** respiration amplitude (RV, std in 6 s), respiration mean, heart rate from QRS intervals, pupil area,
  blink rate, gaze x/y, 6 motion parameters and their derivatives.
- **Movie time:** pairs are compared on movie time from 20 s after onset to the end of the shorter run. All repeat
  statistics use identical filtering on both runs and an extra 0.01 Hz high-pass to remove scanner drift.

## 6. Models (5 subject folds, as A11; the scored person is never in training)

- **M_sim, EEG -> BOLD:** frozen CABLE, the 4 A11 members (m01, m08, m04, m03), equal-weight ensemble, trained on all
  movie runs of training subjects (same run, simultaneous). This is CABLE as it is.
- **M_stim, EEG -> BOLD, stimulus route:** same features and ridge harness, but the target is the *other repeat's*
  BOLD on the movie clock, so only stimulus-locked association can be learned. Trained on training subjects' pairs.
- **R_sim, BOLD -> EEG:** the frozen BRIDGE-010 linear readout: fMRI leads 0-16 s, Schaefer-100 PCA-20 (fit on train)
  + global, inner-fold alpha. Targets as in section 5.
- **R_stim, BOLD -> EEG, stimulus route:** R_sim with cross-repeat targets.
- **B, body -> BOLD:** the body signals, lags 0-20 s, same ridge harness.
- **M_sim+B:** EEG and body together.

## 7. Outcomes

Groups: visibility tertiles over the 100 parcels (high / middle / low), the 7 networks, and global. Statistics are
computed per pair, averaged over pairs within subject, then over subjects; numerator and denominators are averaged
separately before the ratio (no per-pair ratios). 95% CIs by subject bootstrap (2,000).

**Primary**
- P1. rho_stim for EEG -> BOLD (M_stim) in high-visibility cortex.
- P2. rho_stim for BOLD -> EEG (R_stim) on posterior channels (O1, O2, Oz, POz, P3, P4, Pz, P7, P8) in the alpha
  (8-13 Hz) and beta (13-30 Hz) bands.
- P3. Visibility gradient: rho_stim(high) - rho_stim(low) for EEG -> BOLD.

Reading rules, fixed now: rho_stim >= .7 = "the reproducible signals largely match"; .3-.7 = "partial"; < .3 =
"mostly different". A ratio is reported as unmeasurable when the lower CI of rel_P or rel_Y is <= 0. P3 passes if its
CI excludes 0.

**Secondary**
- S1. Repeat reliability maps rel_Y (BOLD) and rel_E (EEG band power): how much of one run is stimulus-locked.
- S2. EEG measurement ceiling: split-taper reliability of band-power envelopes (Spearman-Brown corrected).
- S3. rho_stim for M_sim (CABLE as it is) and its rel_P.
- S4. State coupling: same - cross for M_sim and R_sim, by group.
- S5. Body route: r of B alone, r(M_sim) vs r(M_sim+B), and r(M_sim) after residualizing prediction and target on
  B's prediction. Caveat fixed now: arousal drives both neural and autonomic signals (Gu 2022), so removing body
  signals also removes some neural signal; this gives a bracket, not a point.
- S6. GSR targets: S3-S5 on `desc-sm0gsr` (the local, non-global part).
- S7. Learning curve: CABLE m01 trained on 4, 8, 12, 16 training subjects, same test folds; r(n) with a saturating
  fit, to say whether more data of this kind can close the gap.

**Controls**
- C1. Mismatched movies: run-01 of movie A against run-02 of movie B, same person and session, same movie-time
  window. Every repeat statistic must be ~0 here; if not, non-stimulus time-locked structure exists and is reported.
- C2. Circular time shift (>= 60 s) of one repeat: null distribution for cross.

## 8. What the result will and will not say

It will say, for stimulus-driven activity, how much of the reproducible BOLD signal is carried by EEG and vice
versa, region by region, after removing noise; how much of CABLE's current score comes from body/arousal routes; and
the measured ceilings for a single recording. It will not give a model-free ceiling for the moment-to-moment state
part: that needs an independent measurement of the neural state (intracranial recordings), and is reported as a
bracket. It is one dataset (22 adults, 3 T, movies); numbers are measurements of NATVIEW.

Compute: desktop CPU (no Modal). Code: `experiments/bridge012/`. Results: `BRIDGE_012_RESULTS.md`.

## Amendments

### A1 (2026-10-27 23:06 EDT, before any score was viewed)
The registered run rule (">= 60% valid EEG bins") kept 112 of 239 prepped runs and 28 pairs. The prep log shows why:
inside the validated clock segments (`alignment_segment`) 96-99% of EEG bins are valid (10th-90th percentile), but
the segments cover a median 59% of each run. The rule was meant to drop poor EEG; it was dropping runs with partial
clock validation. New rule: a run is used if it has >= 125 valid EEG bins (100 s); a pair statistic is computed only
on >= 75 jointly finite rows (60 s) inside the movie window. Model fits are rerun on the new run set. A first scoring
pass under the old rule (`b12_summary.json` written 23:02) was not opened and is overwritten.
