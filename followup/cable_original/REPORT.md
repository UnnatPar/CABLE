# Original CABLE A6 reproduction

2026-10-22, @cc-cab. Source: Presonance/encode, cable-interpolator, `3c7aaf7b0c7753a058eebda7ef1132d69df096ec`.

**Original CABLE was located and retrained. This supersedes the earlier missing-source status.** The reviewed abstract corresponds to BRIDGE-009 amendment A6. Earlier BRIDGE-008 results were corrected by the authors for motion-loop contamination and future-EEG filtering; they are not the reproduction target.

| Original protocol | Committed score | Independently retrained | Splits |
|---|---:|---:|---:|
| C1a | 0.438077368 | 0.438077367 | 22 |
| C1b | 0.410362451 | 0.410362450 | 20 |

Maximum regional score difference from the committed original: **6.48e-08**. Every one of the 42 frozen splits met the prospectively fixed 1e-4 numerical agreement threshold. The 12-member first-split smoke run used unchanged original functions; a cached PCA acceleration then matched its full member predictions within 2.1e-10 before scale-up. No model, feature, alpha grid or split was selected from the reproduced outcomes.

## What was actually reproduced

The original 26-channel, 0.8-second-grid feature pipeline, 2/4-second spectral histories, Euclidean/frequency alignment, seven-band log-covariance re-centring, training-only PCA before 30 lags, causal running statistics, winsorization, nested four-subject-fold ridge penalties and 12-readout prediction averaging. The original scoring volumes12..574, region order and scan/fold weighting were retained. All non-test runs train the ridge, as in the original confirmation code; the separate val lists are not excluded from its nested ridge fit.

Twenty-two folds leave out one person (C1a); 20 frozen grouped resamples form C1b. C1a averages the person-fold scores, while each fold itself averages scans. C1b averages scan-macro scores across splits. This is numerical reproduction on existing known data, not fresh confirmation. NeuroBOLT and MEL neural baselines were not independently retrained again in this run.

Original scientific functions are loaded directly from the pinned source; only Modal decorators/orchestration are excluded. Raw inputs are the previously pinned public release. Local target/cache adapters reproduce the source interpolation, float32 boundaries and target filters. The source environment used Python3.12/SciPy1.18.1; this run used Python3.13/SciPy1.18.0 and the same NumPy2.2.6. The observed numerical differences are reported rather than claiming identical environments.

## Authentic baseline on the earlier model-comparison split

A separate fixed comparison used exactly the previous 16 training and six held-out people and 4,504 test rows. Authentic A6 reached **r=0.4692** under that table's subject-balanced metric, versus **0.4230** for the independent reconstruction. Paired difference **+0.0462**, 95% subject-bootstrap interval [+0.0298, +0.0620]. The original A6 scan-macro score on those rows was 0.4737. Maximum original-versus-previous target discrepancy after region reordering was 2.38e-07.

The older NATVIEW readouts, temporal networks and calibration variants retain their previously reported scores. Their earlier CABLE reference was a labelled reconstruction with different members and preprocessing. Use authentic A6 as the canonical CABLE reference from this point. Differences across C1a/C1b and the earlier six-person split are not model improvements by themselves.

## Participant variability with authentic CABLE

Original A6 LOSO scores range from **0.016 to 0.676** across all22 people. Reusing the earlier fixed quality descriptors, alpha/theta ratio has Spearman rho=-0.698 (BH-FDR q=0.001593) and BOLD lag-one smoothness rho=0.688 (q=0.001593). All descriptors and their multiplicity correction are retained in original_participant_variability.json. These remain descriptive associations; source motion/tSNR is unavailable, and stable person-specific artifacts cannot be separated from neurovascular coupling.

## Causality qualification

All frozen feature families passed the future-perturbation check after warm-up. The original Euclidean alignment initializes a scalar using the first eight seconds; the scored windows begin later. However, the original ensemble z-scores each member prediction over the entire evaluated scan before averaging. Changing future predictions changes earlier ensemble outputs in an explicit synthetic check. This uses no held-out BOLD, but it is an offline output normalization, so the full reported ensemble is not a strictly online procedure. It was preserved unchanged for faithful reproduction.

## Revised data and ceiling provenance

- The original authors had already explored ds006040 in development and rejected pooled training. Our earlier frozen reconstruction evaluation still measured transfer to different participants, but ds006040 cannot be described as an untouched validation cohort for original CABLE.
- The source's near-0.9 number is a **0.964 spatial split-voxel reliability proxy** on ds006040 (40 runs, 25 people), using block halves and Spearman-Brown correction. Shared physiology, motion, spatial noise dependence and proxy-dataset assumptions limit its interpretation. It does not measure attainable EEG-conditioned prediction accuracy.
- The earlier BRIDGE-008 source also reports a same-session calibration result near0.52, predating the A6 feature-integrity fixes. Supervised calibration supplies extra information and cannot serve as a lower bound on the strict new-person EEG-only ceiling or a clean-A6 performance guarantee.
- Spatial measurement reliability, repeat-stimulus reliability and EEG-conditioned predictability are different estimands. The earlier weak NATVIEW repeat component and this high spatial reliability need not conflict. The full momentary EEG-to-BOLD ceiling remains unidentified.

## External results retained from source artifacts

The original source includes ds003768 C3 and the less favorable ds000116 C4 result. These are artifact audits here, not new external model fits. Full records remain linked to the pinned Encode source, including the negative comparisons.

| Dataset | Source method | Source scan-macro r |
|---|---|---:|
| ds003768 (C3) | mel_mlpv26_ | 0.3242 |
| ds003768 (C3) | mel_ridgev26_ | 0.3062 |
| ds003768 (C3) | oursv26_ | 0.3692 |
| ds003768 (C3) | neurobolt_v26 | 0.2796 |
| ds000116 (C4) | mel_mlpv26_ | 0.1846 |
| ds000116 (C4) | mel_ridgev26_ | 0.1960 |
| ds000116 (C4) | oursv26_ | 0.1963 |
| ds000116 (C4) | neurobolt_v26 | 0.1547 |

No new original-model accuracy claim on those cohorts follows from reading their stored results.

## Verification and assets

1050 original-split regional scores and 504 member summary scores were independently replayed from newly generated predictions; source and result hashes remained unchanged. The additional matched-split scores were independently calculated on the old table targets. Large feature/PCA/prediction caches stay on D:. Source/data manifests, all42 split results, the direct smoke run, optimization parity, causality audit and complete split comparison CSV are retained.

Canonical scientific source: https://github.com/Presonance/encode/tree/3c7aaf7b0c7753a058eebda7ef1132d69df096ec/presonance/fmri-eeg-interpolator/experiments/bridge009

No source code or results were modified in Encode. No Modal/cloud job or production change was made. The Decode package references the immutable original source; earlier missing-source statements remain preserved as dated history, superseded by this report.
