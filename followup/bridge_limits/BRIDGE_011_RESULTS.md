# BRIDGE-011 results: CABLE pseudo-fMRI as encoder training data (negative)

Closed 2026-10-25 by @cc-b011. Protocol and every amendment, registered before scoring:
`experiments/BRIDGE_011_PROTOCOL.md`. Code and raw outputs: `experiments/bridge011/` (`results/`).

## Question

Can the interpolator (CABLE, BRIDGE-009 A6) turn EEG recorded during movies into extra fMRI training labels for
Presonance's stimulus → fMRI encoder, so that EEG-only datasets (HBN and others) expand the encoder's data?

## Answer: no, on two datasets and at every resolution tested

| test | setup | result |
|---|---|---|
| Stage 2 (A3) | CineBrain, 7 regions, small linear encoder | pseudo hurts (B − A −.051 [−.092, −.006]); testbed underpowered |
| A6 | CineBrain, 5 rotated folds, 7 regions + Schaefer-1000 | FAIL with a working gate: real extra fMRI helps (top-200 C − A +.113), pseudo hurts (B − A −.066 [−.098, −.033]); self-labels beat pseudo everywhere |
| A7 | production encoder (Qwen L20 + head), Algonauts test | inconclusive (real CineBrain adds nothing, C − A −.0003); pseudo hurts (B − A −.0076, 64/70 episodes worse) |
| A8 Q1 | many-viewer averaging limit (CineBrain) | parcel level: shared pseudo tracks shared real BOLD at .21 vs the encoder's .36 (Qp − QE −.156 [−.194, −.116]); 7 regions .41 vs .25, not significant |
| A8 Q2 | use pseudo only in its best parcels | no gain over the matched baseline (top-200 −.017 [−.035, +.003]); always below self-labels |
| A9 | regress ocular / muscle / global-EEG time courses out of pseudo | killed: never beats mismatched-episode regressors (top-200 ΔQp −.055 [−.117, +.007]) |
| A10 | high-pass the pseudo (.01-.04 Hz) | quality falls at every cutoff (top-200 .206 → .143 at .02 Hz) |
| A11 | NATVIEW, clean EEG, ~20 viewers per movie | CABLE tracks each viewer's own BOLD (r .20) but almost nothing viewers share (ρp ≈ .01); Qp CI [0, ~1], production-encoder comparison cannot pass |

## What we learned

- CABLE's output is mostly **viewer-state BOLD** (arousal, vigilance, global fluctuations), which is what it was
  built and validated for. The stimulus-locked part a stimulus encoder needs is small.
- On CineBrain (noisy MB8 EEG) the pseudo-fMRI has a large component shared across viewers that is **not** BOLD-like
  and is not linear ocular, muscle or global-power contamination, and not separable by frequency. On NATVIEW
  (clean EEG) that component is absent, and so is most viewer-shared signal.
- Real extra fMRI does help a small encoder (A6 C − A), so the data-expansion idea is sound in principle; the
  interpolator is the wrong source of labels.
- Methods by-products: per-bin ridge α helps a linear encoder baseline by itself (A8, +.027 on top-200); the
  Spearman-Brown viewer-averaging model predicts observed n-viewer quality almost exactly (A8 model check).

## Promising, not validated

- At the 7 CABLE regions on CineBrain, a many-viewer average could carry stimulus signal the encoder lacks (Qp .41 vs
  QE .25, CI touching 0). Not pursued: NATVIEW does not support it, and a 7-region gain does not help a
  Schaefer-1000 encoder.

## Not done

HBN, SparrKULee, LPP and the other EEG-only pools (Stage 3) were never run: Stage 2 never passed.
