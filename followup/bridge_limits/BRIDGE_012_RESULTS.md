# BRIDGE-012 results: the EEG <-> fMRI ceiling, both directions (NATVIEW)

Protocol: `experiments/BRIDGE_012_PROTOCOL.md` (registered 2026-10-27 before scoring; amendment A1, run inclusion,
before any score was viewed). Code: `experiments/bridge012/` (`b12prep.py`, `b12vis.py`, `b12run.py`,
`b12analyze.py`; exploratory `b12explore.py`). Results: `experiments/bridge012/results/b12_summary.json`,
`b12_explore.json`, `visibility.json`. Compute: desktop CPU, about 20 minutes in total.

Data: NATVIEW, 206 movie runs, 21 subjects, **67 within-session repeat pairs** (dme 14, dmh 13, monkey1 13, tp 12,
monkey2 8, monkey5 7). Of 260 movie runs, 21 failed prep (14 missing > 4 channels, 7 without a usable clock
segment) and 33 had < 100 s of valid EEG.
Numbers are subject-bootstrap means [95% CI]. All r values are single-person, single-run measurements.

## Verdict

The ceiling is high only in the trivial sense. **Measurement noise is not what limits translation in either
direction:** the measurement ceiling is r ~.98 for fMRI (split-voxel, BRIDGE-008 C2) and r ~.96 for slow EEG band
power (split-taper, measured here). What limits it is that **a single recording is mostly not the shared neural
signal**:

- Only **7%** of a run's cortical BOLD variance repeats when the same person watches the same movie again (visual
  network 12%). For EEG band power the figure is **2-6%**.
- The moment-to-moment part that EEG does predict is **largely the same thing heart rate and breathing predict**. On
  NATVIEW, autonomic signals alone predict cortical BOLD at r .27, against CABLE's .15. EEG adds +.008 on top of body
  signals, a difference not significant for cortex.
- **EEG -> BOLD accuracy does not follow where EEG can physically see.** CABLE does slightly *better* in the
  low-visibility third of cortex than in the high-visibility third (.17 vs .13; after GSR .085 vs .047).
- **Whether the stimulus-driven parts of EEG and BOLD are the same signal cannot be pinned down within one person at
  this sample size.** Point estimates are about .4 in both directions, but the CIs run from .1 to above 1.

So for CABLE's current task (one person, simultaneous recording) the predictable variance is dominated by
arousal/autonomic state, not local translation of neural activity. That is consistent with BRIDGE-011, where
pseudo-fMRI failed as encoder training data.

## Registered primary outcomes

**P1 / P2, stimulus-route translation (rho_stim = cross / sqrt(rel_P x rel_T)).** The cross-repeat models were
trained so that they can only learn stimulus-locked associations.

| direction, group | rel_T (target repeat reliability) | rel_P (prediction) | cross | rho_stim | measurable by rule |
|---|---|---|---|---|---|
| EEG -> BOLD, high-visibility cortex (P1) | .075 [.054, .094] | .030 [.005, .054] | .020 [.005, .037] | **.43 [.09, 1.36]** | yes |
| EEG -> BOLD, all cortex | .072 [.052, .091] | .022 [-.002, .046] | .018 [.005, .031] | .44 [.08, 1.62] | no |
| BOLD -> EEG, posterior alpha+beta (P2) | .033 [-.001, .070] | .124 [.075, .167] | .025 [.009, .044] | **.39 [.12, 1.12]** | no (rel_T CI touches 0) |
| BOLD -> EEG, global alpha | .058 [.002, .114] | .112 [.024, .193] | .027 [.000, .053] | .34 [-.01, 1.35] | yes |

Reading (registered rules): P1's point estimate is "partial" (.3-.7), but the CI spans "mostly different" to "largely
match". **P1 and P2 are not resolved by this data.**

**P3, visibility gradient:** rho_stim(high) - rho_stim(low) = -.19 [-2.41, +.10]. It **fails** (the CI includes 0).
The data gives no evidence that stimulus translation is better where EEG sees better. It also cannot rule that out.

**Controls.**
- C1, mismatched movies (130 pairs): rel_T .011, rel_P .007, cross .004, all with CIs including 0, against .07 /
  .02 / .018 for matched repeats. The repeat statistics are stimulus-specific, and the movie clocks are right.
- C2 (circular-shift null) was not implemented. C1 serves the same purpose and is cleaner.

## Registered secondary outcomes

**S1, how much of one run repeats (single-run stimulus ceiling = sqrt(rel_T)).**
- BOLD: cortex .072 (r ceiling .27), visual .124 (.35), dorsal attention .111 (.33), default .044 (.21), global
  .026 (.16).
- After GSR: cortex .103, visual .190.
- EEG: posterior alpha .038 (.20), global alpha .058 (.24), all channel-bands .021 (.15).

**S2, EEG measurement ceiling (split-taper, slow band-power envelopes).** Reliability of a single-taper estimate is
.90-.95 in every band (posterior alpha .927, ceiling r .963). Spectral-estimation noise is not the limit for fMRI ->
EEG. Caveat: artifacts common to both taper sets count as signal here.

**S3 / S4, CABLE as it is (M_sim, 4-member ensemble).**
- Simultaneous r: cortex .151 [.123, .179], visual .191, somatomotor .288, global .233.
- Its predictions **do not repeat across viewings** (rel_P ~.00 in every group), and cross-repeat r is .014 (CI
  includes 0).
- Essentially all of CABLE's skill is therefore state coupling (same - cross about .11-.25), not the stimulus. This
  repeats BRIDGE-011 A11 (across viewers) within person.
- Reverse direction (R_sim): simultaneous r .127 (all channel-bands), posterior alpha+beta .139, global alpha .182.
  These are well below NeuroBOLT's eyes-closed .34 / .45. Movies with eyes open have weaker slow alpha dynamics.

**S5, body route (B = heart rate, respiration amplitude and level, pupil, blinks, gaze, motion; lags 0-20 s).**

| cortex group | CABLE r | body r | r(CABLE pred, body pred) | CABLE partial r given body | EEG + body r |
|---|---|---|---|---|---|
| high visibility | .130 | .283 | .160 | .086 | .290 |
| middle | .153 | .309 | .187 | .098 | .315 |
| low visibility | .169 | .314 | .199 | .109 | .324 |
| all cortex | .151 | .302 | .182 | .098 | .310 |
| global | .233 | .416 | .229 | .153 | .433 |

About two thirds of CABLE's r survives removing the body prediction. The registered caveat applies: arousal drives
neural and autonomic signals together (Gu et al. 2022), so this is a bracket, not a clean neural/non-neural split.

**S6, GSR targets (the non-global part).** CABLE r drops to .067 cortex (high .047, low .085). Body r is .163 and
CABLE's partial r .045; EEG + body reaches .159. Most of what CABLE predicts is the global signal.

**S7, learning curve (m01, cortex r).** 4 subjects .094, 8 .114, 12 .130, 16 .140 (full fold .139). Each doubling of
training subjects adds about .02-.03, with no plateau visible. The registered saturating fit is not identifiable:
the exponent hit its bound and r_inf = .77 is an artifact of the fit. **No asymptote is claimed.**

## Exploratory (not registered; run after the registered results were seen)

`b12explore.py`:

| body part alone -> BOLD | cortex | visual | global |
|---|---|---|---|
| autonomic (heart rate, respiration amplitude/level) | **.273** [.237, .309] | .362 | .395 |
| ocular (pupil, blinks, gaze) | .152 | .124 | .175 |
| head motion (12 columns) | .062 | .056 | .089 |

- EEG over body, r(EEG + body) - r(body): cortex +.008 [-.001, +.016], visual +.019 [.001, .037], somatomotor +.029
  [.014, .044], global +.017 [.003, .032].
- CABLE alone - body alone: cortex -.151 [-.176, -.126].
- The body advantage is not a motion artifact: motion alone is .06. It is mostly heart rate and breathing.

## What this means for "the ceiling" and for CABLE

1. **The absolute (measurement) ceiling is ~.96-.98 in both directions.** That number is real but is not a useful
   target. No measured signal (EEG, body or both) gets near it on NATVIEW: the best is EEG + body at .31 for cortex
   and .43 for global.
2. **The ceiling of the route that matters for "expand the data" (stimulus-locked) is low per person:** r ~.27 for a
   single run of cortical BOLD (.35 visual). Today CABLE sits at ~0 on that route, because its predictions do not
   repeat.
3. **Per-viewer reliability is the binding constraint, so the lever is viewers, not model capacity.** By
   Spearman-Brown, a per-viewer reliability of .03-.07 becomes .44-.65 with 25 viewers and .76-.88 with 100. That is
   the HBN design (about 1,400 children, the same films) and the group-level regime where the literature finds
   corrected coupling ~.8 (Haufe 2018).
4. **On movie data, an EEG -> BOLD claim must beat a heart-rate/breathing baseline.** On NATVIEW, EEG barely adds to
   one. On NeuroBOLT's eyes-closed rest, BRIDGE-009 found physiology alone at .12-.27 and +.011 when stacked, so the
   balance depends on the dataset. CABLE's NeuroBOLT result is not touched by this.

## Limits

- One dataset: 21 adults, 3 T, TR 2.1 s, movies with eyes open, Schaefer-100 cortex only (no subcortex).
- The BOLD measurement ceiling is a proxy from ds006040 (atlas time series only here).
- Only 2 repeats per movie, so per-pair reliabilities are small and the rho ratios are unstable. A
  many-viewer, same-film design (HBN) or many repeats per person would pin them down.
- The visibility metric is a template-head forward model (fsaverage), not individual anatomy.
- Repeat statistics are within session. Day-to-day state differences are not tested.
