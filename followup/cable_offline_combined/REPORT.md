# Combined offline CABLE: one fixed test

October25,2026 (Pacific). Previously exposed NeuroBOLT:22people,29recordings. All12authentic A6 members completed. This is offline prediction, not real-time performance or fresh confirmation.

**Authentic A6 r=0.438077; combined offline r=0.456628; gain=+0.018550, paired-person95%CI[+0.010274,+0.027011].** 17/22people improved; two-sided sign-flip p=0.000530.

| Comparison | Reference r | Combined r | Paired gain [95% CI] | Improved |
|---|---:|---:|---|---:|
| Authentic A6 | 0.438077 | 0.456628 | +0.018550 [+0.010274,+0.027011] | 17/22 |
| Normalization only | 0.448098 | 0.456628 | +0.008529 [+0.004092,+0.012878] | 18/22 |
| Future EEG only | 0.447182 | 0.456628 | +0.009445 [+0.003402,+0.015538] | 16/22 |
| A6, drop final6volumes in both arms | 0.436378 | 0.454932 | +0.018555 [+0.010110,+0.027190] | 17/22 |

The separate normalization and future-EEG gains were +0.010021 and +0.009105. Their sum is not an expected gain: observed interaction (combined gain minus both separate gains)=-0.000576.

Fitting completed in 11.61 minutes elapsed, with at most4member processes/3numerical threads each. The900second cap was not exceeded. No retry, additional variant or incomplete-member score was used.

## What was fixed

Combined norm=offline,future=15,basis=0 using an exact SHA-pinned copy of the existing boost harness. The future design includes lags-14..30 on the.8second feature grid: up to11.2seconds future-bin displacement and24seconds past-bin displacement, plus underlying causal spectral histories. It is not a symmetric+/-12second window. Training-only PCA and original nested4subject-fold ridge alpha selection remain unchanged. No test BOLD fitted the model or normalizations. Whole-record EEG/PCA-score statistics are noncausal; final whole-record prediction standardization was already part of A6.

The primary result uses exactly original volumes12..574 and all seven targets. The inherited future design zero-pads unavailable future features near recording end. The prespecified final-six-volume exclusion is a sensitivity on identical rows in both arms, not a replacement primary score.

## Interpretation

The combined gain does not meet the+.03 useful-gain screen. This single offline combination does not establish a substantial CABLE improvement.
The combination was selected after observing its separate components on this already exposed cohort. Paired intervals resample participants conditional on fixed fits; they do not include training resampling or correct for all prior experiment selection. Comparisons beyond the primary are descriptive. No hard information ceiling, neural mechanism or online gain follows from this test.

## Verification and artifacts

Reconstructed all four12member ensembles and recomputed region correlations independently with scipy.stats.pearsonr. Largest person-score difference=2.11e-09. Canonical A6 parity, all source/input hashes, member-output hashes, finite563x7predictions and completion/deadline checks passed. This verifies saved computations, not an independent retraining. Raw member predictions/logs/alpha receipts remain private under validation/output/cable_offline_combined/private/.

Public:PROTOCOL.md,run.py,boost_harness_snapshot.py,protocol.lock.json,results.json,verification.json,completion.json and this report. Code:experiments/cable_offline_combined/. Results:validation/output/cable_offline_combined/. Requires existing private original A6 caches and prior variant outputs to rerun. No datasets were downloaded; no reserved cohort, MRI pipeline, ECG model, crashed future2 variant or arousal/foundation-model experiment was opened or started.

Stop after this one test. Do not automatically launch another sweep or call this real-time performance.
