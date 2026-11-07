# Final reserved-cohort CABLE pooling validation

Completed 2026-10-26T09:33:20.303665+00:00. All 34 assigned attempts are terminal; 32 people are evaluable, and participants 21/22 remain preserved operational failures. All experiment jobs have ended. This completes the current frozen experiment. The user requested stopping here, with no further experiments or searches.

## Result

The unchanged 22-person source ensemble scored **r=0.331480**, and the prospectively selected 66-person pooled ensemble scored **r=0.368796**. The paired gain is **+0.037316**, participant 95% CI **[+0.020047,+0.056380]**, two-sided 200,000-draw sign-flip **p=0.00011000**. **24/32 people improved**. Both the positive-replication criterion and the prespecified +.03 substantial-gain screen passed.

This independently replicates a benefit from the larger training pool. It is a data-pooling result using existing CABLE ensembles, with no new architecture, per-person BOLD calibration or ECG inference input. It does not isolate participant diversity from labeled-data quantity or dataset composition. Earlier fixed-row/native-budget results and inconsistent transfer remain relevant. These correlations describe this cohort; they cannot be added to the original NeuroBOLT benchmark.

| Prespecified comparison | Reference r | Candidate r | Gain | Participant95%CI | p |
|---|---:|---:|---:|---|---:|
| Primary pooled66 versus source22 | 0.331480 | 0.368796 | +0.037316 | [+0.020047,+0.056380] | 0.00011000 |
| 99-person versus 66-person training pool | 0.368796 | 0.361920 | -0.006876 | [-0.020536,+0.006566] | 0.33555332 (Holm) |
| Pooled model versus fixed scan-time control | -0.010051 | 0.368796 | +0.378847 | [+0.311360,+0.448797] | 0.00001500 (Holm) |
| Pooled model versus shifted-EEG control | -0.015060 | 0.368796 | +0.383856 | [+0.322400,+0.446596] | 0.00001500 (Holm) |

The full99 ensemble gives r=.361920 and does not demonstrate an additional gain over pooled66. The fixed clock and shifted-EEG controls score near zero; neither their failure nor the positive EEG correlations establishes purely neural specificity.

## Uncertainty and participant variability

The 60-second native-block person/time sensitivity interval for the pooling gain is [+0.016242,+0.058550], with all 20,000 draws finite. The 120-second native-block person/time sensitivity interval for the pooling gain is [+0.017709,+0.059488], with all 20,000 draws finite. These are conditional on fixed models and recordings, not full-retraining uncertainty or a guarantee against all long-range dependencies.

| Frozen covariate versus pooled66 person score | Spearman rho | Holm-three p | Interpretation |
|---|---:|---:|---|
| alpha_flank_log_contrast | -0.409457 | 0.060000 | Suggestive negative association; misses adjusted .05 threshold. Spectral/state proxy, not established EEG SNR. |
| valid_native_fraction | undefined (constant) | 1.000000 | No variation across 32 people; cannot explain differences. Undefined uncertainty draws are retained. |
| mean_FD_mm | +0.208944 | 0.497028 | Uncertain positive association; no causal motion/coupling conclusion. |

Pooled66 person scores range from .055815 to .719307. The three tests do not identify what fraction of this variation is data quality, vigilance, vascular response, acquisition artifacts or individual EEG-to-BOLD coupling. No covariate changes predictions, targets or exclusions. No prediction ceiling is identified.

## Protocol and failures

The entire 34-person MULTI-CLARID resting-state cohort (ds005795, pinned a225eb4608bd72e20a6aa6aa6fdda09692f77a7f) was assigned before signal values. G96/G97 fixed the 500 Hz to 250 Hz frontend, CORE19 inputs, exact prior prediction-index convention, source22/pooled66/full99 states, native MRI processing, original six DiFuMo targets plus global BOLD, failure rules and statistics. G97C specified the three existing variability covariates before any cohort accuracy. Both cohort and covariate input seals were pushed in G98/df97b62 before the sole score opening. The specification is a committed prospective protocol, not a public registry preregistration.

All successful people have 300 native target volumes and 288 eligible rows: 9,600 native volumes / 9,216 scored rows total. These rows are autocorrelated; people are the inferential units. MRI processing included slice timing, motion correction, anatomical registration and actually viewed anatomy/EPI QA, then full original-target projection. Numerical spatial/filter/clock and source SHA/CRC checks passed. No retargeted neurofeedback endpoint or outcome-based exclusion was used.

Participants21/22 failed because I did not deliver the required anatomy QA approval within the frozen 1,800-second deadline. Their original EEG/T1 inputs, output hashes, anatomy montages and explicit failure records are preserved. The temporary RAM intermediates were absent on later inspection after both lifetime holders ended; an attempted archive could not recover them. No scratch cleanup or implicit rerun was performed, and no retroactive acceptance was issued. These are operational failures of this run, not evidence that those participants had poor data. The result is prespecified available-case inference on 32/34, not a complete 34-person accuracy result or proof that missingness is unbiased.

Provider MRI/CWL-corrected EEG and whole-record operations are offline. Field maps are absent; inferior/cerebellar field of view is incomplete and anterior/inferior signal loss occurs. Atlas coverage is geometric, not temporal signal quality. The 54 ms first-marker anomalies in 12/26 retain the frozen publisher clock; no lag/sign was selected from outcomes. Physiology export blocks remain ambiguously mapped to MRI; no synchronized physiology-control conclusion or ECG promotion is claimed. Anonymous identity overlap across releases is not fully verifiable. Neither this result nor the earlier ceiling studies establishes an EEG-conditioned prediction ceiling or genuine three-day/cap-replacement transfer.

## Verification and stopping decision

Independent replay verified 1,120 regional score cells (maximum error 7.77e-16), all 20,000 person draws and 200,000 sign flips per contrast, 1,024 explicit native time draws per person, Holm adjustments and both time-block intervals. The separate variability verifier independently recomputed native EEG/motion covariates and replayed all three permutation/uncertainty procedures. Both verification receipts pass. Original arrays/weights remain local; public reports and QA derivatives are the explicitly approved publication payload.

The final pooling result is useful and was worth validating. The broad architecture search took longer than its accuracy results justify. Keep this verified pooled checkpoint, preserve the negative results and stop here. No further model fitting, datasets, protected cohorts, ceiling searches or author contact are authorized by this stopping instruction. The overall ceiling/three-day goals remain incomplete; the persistent goal is to be paused at the user's request after final publication.

Source: experiments/cable_goal/. Machine-readable evidence: multiclarid_replication/results.json, results_verification.json, variability_results.json, variability_verification.json and both input seals. Broader experiment history and gains: FINAL_HANDOFF.md. Existing PR: https://github.com/Presonance/decode/pull/8. Final publication resolves through alternative_publication_G99.json.
