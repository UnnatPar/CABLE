# BRIDGE-010 results: fMRI → EEG benchmark on identical splits

Protocol: `experiments/BRIDGE_010_PROTOCOL.md` (+ amendment A1), registered 2026-10-18 before any score.
Ledger: `presonance/ledgers/20261018-experiment-eeg-fmri-bridge-010.md`. Raw rows: `experiments/bridge010/results/b10_S*.jsonl`;
summary: `experiments/bridge010/results/b10_summary.json` (`python b10analyze.py`). Compute: Modal (T4 for deep models, CPU for ours).

## Verdict
**Our frozen lagged ridge does not lead the fMRI → EEG direction.** On the primary set (S1, 20 fresh subject-disjoint
NeuroBOLT splits) it is significantly worse than all five implemented competitors. It is last or second to last on
the external within-site set (S2) and last zero-shot (S3). Under the registered decision rules no "better than every
model" or "state of the art" claim is made for fMRI → EEG. The leader is the temporal CNN on S1, the Transformer on S2,
and the adapted transcoder / GRU (tied) on S3.

## Primary metric: median r over channel × band targets

| Method | S1 (20 splits) | S2 ds003768 (33 subjects) | S3 zero-shot NB→ds003768 (33) |
|---|---|---|---|
| TCN | **.357** | .265 | .202 |
| MLP | .353 | .248 | .206 |
| GRU | .348 | .250 | .214 |
| Transformer | .340 | **.289** | .204 |
| Transcoder (adapted Liu-Tu-Sajda 2022) | .339 | .229 | **.215** |
| Ours (lagged ridge, frozen BRIDGE-008) | .327 | .238 | .187 |

Ours minus competitor (sign-flip p; wins; 95% bootstrap CI):

| vs | S1 | S2 | S3 |
|---|---|---|---|
| TCN | −.031 (p 2e-6; 0/20; [−.037, −.024]) | −.027 (p .003; 11/33) | −.015 (p .09; 11/33) |
| MLP | −.026 (p 4e-6; 1/20; [−.032, −.020]) | −.011 (p .31; 14/33) | −.019 (p .008; 14/33) |
| GRU | −.022 (p 4e-5; 2/20; [−.028, −.015]) | −.013 (p .29; 11/33) | −.028 (p .0004; 9/33) |
| Transformer | −.014 (p .004; 5/20; [−.022, −.006]) | −.052 (p < 1e-4; 5/33) | −.018 (p .007; 11/33) |
| Transcoder | −.012 (p .012; 6/20; [−.021, −.004]) | +.008 (p .44; 17/33) | −.028 (p .002; 8/33) |

S1 p-values treat splits as units; the 20 splits share people, so these are optimistic. The direction of every S1
comparison is consistent with S3, which has independent subjects.

## Secondary metric: global alpha (vigilance index) r

| Method | S1 | S2 | S3 |
|---|---|---|---|
| TCN | **.446** | .328 | .255 |
| MLP | .442 | .325 | .268 |
| GRU | .432 | .325 | .261 |
| Transcoder | .423 | .300 | .273 |
| Ours | .419 | .323 | .258 |
| Transformer | .403 | **.343** | **.274** |

On S1, ours is behind TCN, MLP and GRU (p ≤ .001), tied with the transcoder (p .52) and ahead of the Transformer
(+.017, p .014). On S2 and S3 no difference involving ours is significant.

## Interpretation (for the full paper)
- EEG → fMRI is close to linear after per-person alignment: CABLE (linear) beats NeuroBOLT and MEL (BRIDGE-009).
  fMRI → EEG gains about 0.01–0.03 r from nonlinearity and symmetric temporal context. The asymmetry is a finding,
  and the paper should report it as one.
- The deep models had symmetric context (fMRI before and after each bin, A1). Ours used only leads 0–16 s, so part
  of the gap may be context and part nonlinearity. We did not run an ablation to separate the two.
- Global alpha, the physiologically interpretable target, is close to tied across methods outside S1.

## Not implemented
- Zhang et al. 2026 (ICCCS 2025, CCIS, doi 10.1007/978-981-95-8978-4_27): full text paywalled. The architecture is
  not described in the abstract, so it is not implementable. It must be discussed in the full paper as an untested
  published competitor.
- The transcoder is an adaptation: no public code; widths, kernels and learning rate unreported and chosen on `val`
  from a fixed grid; regional series and band-power targets instead of voxels and raw EEG.

## Consequences for public claims
- COSYNE abstract: no SOTA or "beats every model" claim for fMRI → EEG. If the reverse direction is mentioned at all,
  it is described only as working on held-out people, with our numbers, without a comparison claim.
- DEV (spent LOSO) numbers are reproduction checks and are never reported as tests.
