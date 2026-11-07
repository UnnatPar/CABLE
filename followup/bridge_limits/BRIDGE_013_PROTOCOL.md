# BRIDGE-013 protocol: the group-level (many-viewer) EEG <-> fMRI ceiling, both directions

Registered 2026-10-28 by @cc-c12, before any BRIDGE-013 score was computed. Ledger:
`presonance/ledgers/20261028-experiment-cable-group-ceiling.md`. Amendments are appended at the bottom, dated, and
never edit the registered text.

## 1. Question (Guhan, 2026-10-28)

"I want to know the true ceiling for fMRI to EEG and EEG to fMRI. Removing the normal person to person variance and
other problems."

BRIDGE-012 asked this within one person (two viewings of the same movie). Its noise-corrected answer was about .4 in
both directions, but the CIs ran from .1 to above 1. That was because one viewing is only 2-7% stimulus-driven, so the
correction divided by almost nothing.

## 2. Estimand

The **true ceiling** here is the correlation between the noise-free, person-independent, stimulus-driven part of
EEG and the same part of BOLD, under the best mapping between them. Removed by design:

- measurement noise (scanner, electrodes, spectral estimation);
- each person's own state (arousal drifts, mind-wandering), which does not repeat across people;
- each person's own stimulus response (person-to-person variance);
- "other problems": body signals (heart rate, breathing, pupil, blinks, gaze, motion) as a separately measured
  stimulus-locked confound.

What remains is the response all viewers share. Literature anchors for this regime: single neurons in two patients
predict other people's auditory-cortex BOLD to the same movie at r = .75 (Mukamel et al. 2005 Science); EEG, ECoG and
fMRI cohorts watching the same clip correlate positively once averaged over subjects, ~.8 noise-corrected in
occipito-parietal cortex (Haufe et al. 2018 NeuroImage).

Not covered (and said so in the results): the within-person, moment-to-moment state coupling that does not repeat
across viewers (BRIDGE-012 "same - cross"). Its ceiling cannot be measured by repeats. Also, fMRI -> EEG is defined
only for slow band-power envelopes (< .15 Hz). Anything faster is invisible to BOLD by physics.

## 3. Logic

Per movie, split the viewers into random halves A and B, average each half (on the movie clock), and fit a mapping f
on *other movies* only. Then, per output:

- rel_T = corr(T_A, T_B), the reliability of a half-group average of the target;
- rel_P = corr(f(X_A), f(X_B)), the same for the prediction;
- cross = mean[corr(f(X_A), T_B), corr(f(X_B), T_A)], which shares no person, no state and no noise;
- **rho = cross / sqrt(rel_P * rel_T)** (Spearman's correction). It is the correlation that f would reach between
  infinitely many viewers' EEG and infinitely many viewers' BOLD. A fitted f gives a lower bound on the best possible
  f. rho^2 is the share of the shared stimulus-driven target variance that crosses over.
- same = mean[corr(f(X_A), T_A), corr(f(X_B), T_B)]; same - cross = coupling carried by the same people's
  non-stimulus activity, in averaged form.
- Spearman-Brown links it to viewers: per-viewer reliability rel_1 = rel_h / (n_h - (n_h - 1) rel_h) for halves of
  n_h viewers. Full-group r at N viewers = rho * sqrt(SB_N(rel_P,1) * SB_N(rel_T,1)).

Reliabilities are now group-level (half-groups of 7-10 viewers), so the correction no longer divides by ~.03.

## 4. Data

NATVIEW, BRIDGE-012 prep unchanged (`experiments/bridge012/derived/prep`, amendment-A1 run inclusion). Per movie,
subjects with at least one valid run: dme 20, dmh 17, inscapes 19, monkey1 18, monkey2 16, monkey5 15, tp 20. A
subject's runs of one movie are averaged first, so the subject is the unit. dme and dmh are the same video with
English vs Hungarian audio: they are separate test movies but **one fold and one bootstrap unit** ("dm"). Six units:
dm, inscapes, monkey1, monkey2, monkey5, tp.

## 5. Signals (movie clock, 0.8 s bins from movie time 0; scored window [20 s, end - 1 s], as BRIDGE-012)

- BOLD: Y (Schaefer-100 + 7 networks + global, BRIDGE-012 target), masked to fMRI-valid bins, high-pass 0.01 Hz
  (BRIDGE-012 `masked_hp`), z per run. Secondary: Yg (GSR).
- EEG: E (26 channels x 5 bands log power + global alpha, band-pass 0.01-0.15 Hz, BRIDGE-012), masked to valid EEG
  bins, z per run.
- Body: the 19 BRIDGE-012 body columns (rv, resp, hr, pupil, blink, gaze x/y, 12 motion), masked high-pass, z per run.
- Each run is sampled on its movie's grid (linear interpolation), runs averaged within subject, then subjects
  averaged within a half (weighted NaN-mean). A half-average bin is valid if >= 50% of that half's viewers are valid
  there.

## 6. Models (leave-one-unit-out: f never sees the test movie; dm folds hold out dme and dmh together)

Group-trained (G, primary). Fitted on the full-group averages of the 5 training units:
- features are z-scored within each movie, then projected on PCA-10 (fit on the training movies), with the scores
  z-scored within each movie;
- EEG -> BOLD: EEG at t - l, l = 0, 2, ..., 24 bins (0-19.2 s, 13 lags);
- BOLD -> EEG: BOLD (all 108 columns) at t + l, same l;
- ridge per output, alpha from the BRIDGE-012 grid by inner leave-one-training-unit-out (`b12lib.ridge`, inner = 5).
- Models: **G_E->Y** (primary), G_Eab->Y (EEG alpha + beta bands only, least artifact-prone; PCA-10), G_B->Y
  (body, 19 columns, no PCA), G_EB->Y (EEG PCA-10 + body), G_E->Yg, **G_Y->E** (primary), G_B->E, G_YB->E.

Individual-trained (I, secondary): the same EEG features and lags fitted on single runs of the training movies
(simultaneous, all subjects; inner 4 subject folds), applied per run on the test movie, then averaged like the data.
This is CABLE-style training without CABLE's alignment.

At test time each model is applied to the half-averages (it is linear, so this equals averaging predictions up to
NaN handling). Output rows are invalid where the current input bin is invalid.

## 7. Outcomes

Groups as BRIDGE-012: BOLD visibility tertiles (high / middle / low, `results/visibility.json`), all cortex, 7
networks, global. EEG: posterior alpha + beta, global alpha, all, each band.

Aggregation: per movie and split, components (rel_T, rel_P, cross, same) are averaged over a group's outputs and then
over movies, weighted by scored bins. rho is the ratio of the averaged components. The point estimate is the mean
over 200 random splits. **95% CIs come from a two-level bootstrap** (1,000): resample the 6 units with replacement,
resample subjects with replacement within each unit, split the unique subjects at random into halves, 4 splits per
replicate. A subject-only bootstrap (units fixed) is also reported. rho is **measurable** if the lower CI bounds of
rel_P and rel_T are both > 0.

Primary:
- **P1** EEG -> BOLD, high-visibility cortex: rho(G_E->Y).
- **P2** BOLD -> EEG, posterior alpha + beta: rho(G_Y->E).
- **P3** Visibility gradient: rho_high - rho_low (G_E->Y), CI by the two-level bootstrap.
- **P4** EEG beyond body, all cortex: rho(G_EB->Y) - rho(G_B->Y).

Reading, as BRIDGE-012: rho >= .7 "largely the same signal"; .3-.7 "partial"; < .3 "mostly different". A reading
needs its CI to sit inside one band. Otherwise it is reported as "not resolved". P3 passes if the CI excludes 0. P4
passes if the CI excludes 0.

Secondary:
- S1 group reliabilities: half-group rel, full-group rel (Spearman-Brown) and implied per-viewer rel, per group, next
  to BRIDGE-012's within-person repeat reliabilities.
- S2 per-unit rho (movie-to-movie spread).
- S3 I model: rho, rel_P, same - cross.
- S4 G_Eab->Y (EEG without delta/theta/gamma).
- S5 GSR target (G_E->Yg).
- S6 BOLD -> EEG with body: G_B->E and G_YB->E.
- S7 overlap of the EEG and body routes: disattenuated corr(G_E->Y prediction, G_B->Y prediction) = cross-half
  corr / sqrt(rel_PE * rel_PB), all cortex.
- S8 viewers needed: N at which the full-group r reaches 90% of rho, from the per-viewer reliabilities.

Control:
- C1 mismatched movies: the prediction for movie m against the half-average target of a different unit (truncated to
  the shorter window, never dme with dmh). Expected cross ~0.

## 8. What the result will and will not say

- rho is a lower bound on the true stimulus-driven ceiling for a linear, lag-limited, PCA-10 mapping trained on about
  30 minutes of group data (the other movies). A low rho could be a model limit. A high rho cannot be an artifact of noise, because
  neither the person, the state nor the noise is shared across halves. It can still reflect shared body signals and
  shared EEG artifacts (blinks at scene cuts). P4, S4 and S7 address that.
- It is the ceiling of the shared, stimulus-driven route, which is the route that matters for using EEG cohorts to
  stand in for fMRI cohorts. It is not the ceiling of single-person, moment-to-moment translation, CABLE's current
  task.
- One dataset: 21 adults, 3 T, about 40 minutes of distinct movie content, 15-20 viewers per movie.

## Amendments
