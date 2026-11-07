# Independent follow-up validation of CABLE

This note adds results from an independent re-run and extension of CABLE (October 2026) and states
how they change the reading of the numbers in the paper and README. Every figure below is taken from a
machine-readable file in [`followup/`](followup/), except the "Other held-out cohorts" table, which cites
reports that are not copied. Nothing here was re-estimated for this note.
Provenance and file hashes are in [`followup/MANIFEST.md`](followup/MANIFEST.md).

## Headline results

| # | What was run | Test data | Mean r |
|---|---|---|---:|
| 1 | Original CABLE (amendment A6), retrained from the pinned source code | NeuroBOLT, leave one person out: 22 people, 29 recordings (**C1a**) | **0.4381** |
| 2 | Same CABLE plus an **offline** variant: whole-recording normalization and future EEG | the same 22 people | **0.4566** |
| 3 | Unchanged 12-member CABLE trained on **22** people (NeuroBOLT) | independent cohort: MULTI-CLARID (OpenNeuro ds005795), 32 evaluable of 34 people | **0.3315** |
| 4 | The same 12-member CABLE trained on **66** people (22 NeuroBOLT + 24 ds006040 + 20 ds002739) | the same 32 people | **0.3688** |

Rows 1-2 and rows 3-4 use different test sets (different cohort, scanner, EEG channel mapping and
preprocessing). Do not compare the levels across the two pairs, and do not add rows 3-4 to the NeuroBOLT
benchmark table. Each pair is a paired comparison on the same people.

| Comparison | Gain | 95% CI (people resampled) | People improved | Sign-flip p | Pre-set +0.03 screen |
|---|---:|---|---:|---:|---|
| 2 vs 1 (offline variant) | +0.0186 | [+0.0103, +0.0270] | 17 / 22 | 0.00053 | not met |
| 4 vs 3 (66 vs 22 training people) | +0.0373 | [+0.0200, +0.0564] | 24 / 32 | 0.00011 | met |

Sources: `followup/cable_original/results.json`, `followup/cable_offline_combined/results.json`,
`followup/multiclarid_pooling/results.json`. The four means were recomputed from the per-person scores
(0.43808, 0.45663, 0.33148, 0.36880) and agree with the stored summaries.

## What this changes

**1. The published CABLE numbers reproduce.** Retraining from the pinned source gives C1a 0.438077
(repository value 0.438077) and C1b 0.410362 (repository value 0.410362). The largest regional
difference from the committed scores is 6.5e-8, and all 42 frozen splits (22 + 20) agree within the
prespecified 1e-4. This is a numerical reproduction on data already used in the paper, not a fresh
confirmation. NeuroBOLT and MEL were not retrained again in this run.

**2. "Causal" applies to the features, not to the final scored ensemble.** All frozen feature families
pass a future-perturbation check after warm-up (the Euclidean alignment is initialised from the first
8 s). However, the ensemble z-scores each member's prediction over the whole evaluated scan before
averaging, so earlier outputs change when later predictions change (shown with a synthetic
perturbation; no held-out BOLD is involved). The reported 0.4381 is therefore an offline-normalised
score, and statements that CABLE "can run online" describe the feature pipeline. A strictly online
score is reported in this note.

**3. The offline variant gains little and is not a deployable result.** Row 2 normalises features and
predictions with whole-recording statistics and adds future EEG (lags -14 to +30 on the 0.8 s grid:
up to 11.2 s ahead, 24 s behind). Normalization alone gives +0.0100 and future EEG alone +0.0091; the
combination gives +0.0186 (interaction -0.0006). It misses the +0.03 screen, it was assembled after
its components were seen on this already-exposed cohort, and the paired intervals do not include
training resampling. Treat it as an offline upper-bound-style diagnostic, not as real-time performance.

**4. Pooling training people helps on one independent cohort, with caveats.** Row 4 vs row 3 was
prespecified, run once, and replicated a positive gain (+0.0373). Qualifications:

- It uses existing CABLE ensembles with no new architecture. It cannot separate participant diversity
  from the amount of labelled data or from dataset composition.
- A larger 99-person training pool is not better than the 66-person pool on this cohort
  (0.3619 vs 0.3688, Holm p = 0.34).
- Fixed clock and shifted-EEG controls score near zero (-0.010 and -0.015), but positive EEG
  correlations alone do not establish purely neural specificity.
- Two of the 34 assigned participants (21 and 22) failed operationally (a missed manual QA deadline)
  and are excluded; the result is available-case on 32/34, and their records are preserved.
- Person-level scores range from 0.056 to 0.719, so the mean hides large individual differences. None
  of the three frozen quality covariates is significant after Holm correction (closest: alpha-flank
  contrast, rho = -0.41, p = 0.06), and the data cannot say what drives the spread.
- Earlier work on the original CABLE reports that pooled training was explored on ds006040 in
  development and rejected, so ds006040 is not an untouched cohort for the original model.

### Other held-out cohorts (summarised here; the source reports are not copied)

| Cohort | People | 22-person r | 66-person r | Gain [95% CI] | Reads as |
|---|---:|---:|---:|---|---|
| Reserved 7T cohort | 8 | 0.1801 | 0.1919 | +0.0118 [-0.0264, +0.0498] | interval includes zero |
| ds002336 | 10 | 0.0137 | 0.0216 | +0.0080 [-0.0296, +0.0442] | interval includes zero |
| Independent EEG-only cohort | 17 | 0.394 | 0.411 | +0.017 [+0.007, +0.027] | positive, below the +0.03 bar |

Source packets: `cable_goal/CONCLUSION.md`, `cable_next/REPORT.md`, `cable_fresh/REPORT.md` in the
private decode repository at the commit listed in the manifest. Across the four held-out cohorts the
pooling gain is positive in every point estimate, its interval excludes zero in two (32 and 17 people)
and includes zero in the two smallest (8 and 10 people), and only the 32-person cohort clears +0.03.

## What is not claimed

- No EEG-conditioned prediction ceiling has been identified. A near-0.9 "ceiling" figure in earlier
  project notes is a spatial split-voxel reliability proxy on ds006040 (0.964), which measures BOLD
  reliability, not attainable EEG-to-BOLD accuracy.
- No causal explanation of why pooling helps, and no neural-specificity claim.
- No fresh confirmation of the original CABLE protocol (row 1 reuses known data).
- No strictly online CABLE score, and no promotion of the offline variant.

## Provenance and scope

- Source of rows 1-4: Presonance `decode`, branch `codex/cable-followup-validation`, commit
  `0c107207b9b020e87db6c3f285290d029c63084b`. Original CABLE source: Presonance `encode`, branch
  `cable-interpolator`, commit `3c7aaf7b0c7753a058eebda7ef1132d69df096ec`.
- ds005795 is pinned at `a225eb4608bd72e20a6aa6aa6fdda09692f77a7f`. Dataset licenses are those on each
  OpenNeuro dataset page.
- Included: reports, result files, verification receipts and protocol text for rows 1-4. Excluded: raw
  EEG/MRI, per-participant anatomy images, prediction arrays, model weights and the follow-up adapter
  code. The adapters live in the source repository; they can be proposed in a separate PR if the
  authors want them here. Re-running rows 2-4 needs private caches that are not part of this repository.
- Reports are copied verbatim. Where they use first person ("I did not deliver the required anatomy QA
  approval"), it refers to the run that executed the protocol.
