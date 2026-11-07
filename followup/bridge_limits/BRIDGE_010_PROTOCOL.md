# BRIDGE-010 protocol: fMRI → EEG benchmark on identical splits

Registered 2026-10-18 (EDT) by @cc-b9x, before any BRIDGE-010 score is computed. Amendments are appended, dated,
and marked as made before or after scoring. Ledger: `presonance/ledgers/20261018-experiment-eeg-fmri-bridge-010.md`.

## Question
Does our linear lagged readout predict a held-out person's EEG from fMRI better than published and strong deep
fMRI→EEG models, trained and tested on identical splits and targets? A "state of the art in both directions" claim is
made only if the answer is yes against every competitor below that could be implemented.

## Data (public)
- **NB:** NeuroBOLT simultaneous EEG-fMRI, 29 eyes-closed rest scans, 22 people (`/evidence/bridge005/nb`).
- **EXT:** OpenNeuro ds003768, 33 adults, rest runs (`/evidence/bridge009/ds003768/cache`), preprocessed in BRIDGE-009
  with licence-free tools; reverse direction never scored on it.

## Predictors and targets (fixed)
- Grid 0.8 s. **fMRI predictors:** 64 DiFuMo regions + global signals, low-passed 0.15 Hz, z-scored per run.
- **EEG targets:** 5-band log power (1-4, 4-8, 8-13, 13-30, 30-45 Hz) per scalp channel (NB: 26 common channels; EXT:
  its 30 scalp channels; NB→EXT: the shared channel set), band-passed 0.01-0.15 Hz, z-scored per run; plus **global
  alpha** = z-scored mean alpha log power over channels (vigilance index).
- Bins with any non-finite EEG are excluded from training and scoring. Prediction of bin t may use fMRI from any time
  in the same run (offline mapping), as in BRIDGE-005/008.

## Metrics
- Per scan: Pearson r per target; **primary = median over channel × band targets**; secondary = global-alpha r.
- Per split: mean over test scans. Unit of inference: split (S1), subject (S2, S3).
- Paired tests: sign-flip (10,000 draws, or exact when small) on per-unit differences; 95% bootstrap CI.

## Splits
- **S1 (primary):** the 20 fresh subject-disjoint splits registered in BRIDGE-009 (`results/confirm_splits.json`, key
  `C1b`); each split's `val` scans are the only data any model may use for early stopping/model selection. LOSO is
  spent (BRIDGE-005/008 development) and is not a test here.
- **S2:** EXT within-site, the BRIDGE-009 C3 subject-grouped folds (`results/c3_folds.json`).
- **S3:** zero-shot NB → EXT (train on all NB scans, test on every EXT run).

## Methods
1. **Ours (frozen = BRIDGE-008 `difumo_k20`):** PCA (k = 20, fit on training runs) of the fMRI predictors, leads
   0-16 s (21 bins), ridge, α from {1 … 1e7} chosen by 4 inner subject folds of the training runs. No change after
   registration.
2. **Liu-Tu-Sajda transcoder (adapted from arXiv 2212.02226; no public code):** cyclic convolutional transcoder trained
   with all four sum-of-squared-error losses (fMRI→EEG, EEG→fMRI, both cycles); 5 conv layers per encoder/decoder,
   ReLU, batch norm; fMRI decoder = temporal (transposed) convolution, EEG encoder = channel-mixing convolution;
   Adam, 32 epochs. Unreported hyperparameters (widths, kernels, learning rate) chosen on `val` scans from a fixed
   grid. Adapted from voxels to the 66 regional series and from raw EEG to band-power targets.
3. **Zhang et al. 2026 (ICCCS 2025, CCIS; doi 10.1007/978-981-95-8978-4_27):** fMRI→EEG band power from regional BOLD
   over consecutive windows. Implemented from the paper only if the full text is obtained; otherwise reported as not
   implementable (abstract-level description is insufficient).
4. **Deep baselines (same inputs, same targets, same val-only selection):** (a) MLP on the 0-16 s lead window;
   (b) temporal CNN; (c) GRU; (d) Transformer encoder over the lead window. Each: AdamW, early stopping on `val`
   median r, hyperparameter grid fixed in code before scoring; 3 seeds averaged.

## Decision rules
- Ours is "better than X" if mean S1 gain > 0 with sign-flip p < .05 and the CI excludes 0.
- **SOTA claim for fMRI→EEG** requires: better than every implemented competitor on S1 **and** not worse on S2/S3
  (gain ≥ 0). If any competitor wins, it is reported as the leader.
- All scored numbers are reported, including losses.

## Amendment A1 (2026-10-18, before any S1/S2/S3 score)
Implementation details fixed in `bridge010/b10lib.py` / `b10run.py` before scoring:
- **Ours:** ridge targets and the alpha-selection criterion use Y = [channel × band power, global alpha]
  (BRIDGE-008 also carried 5 fine-spectra PCs in Y; dropped). Global alpha is z-scored over valid bins.
  Reproduction on the spent LOSO folds (DEV): median r .3421, alpha .4513 (BRIDGE-008: .343 / .451).
- **Deep models:** inputs are the same 66 regional series; generic models may use symmetric context (fMRI before and
  after each bin; at least as much information as ours). Config chosen on `val` with seed 0 (grids in
  `b10lib.GRIDS`); final = 3 seeds retrained on train + val for the selected epoch count, predictions averaged.
  Generic: AdamW (wd 1e-2), batch 16 crops of 128 bins, 50 steps/epoch, early stopping patience 8, max 60 epochs,
  dropout 0.2. Transcoder: Adam, batch 1, 4 SSE losses, 32 epochs, kernel 9; grid widths {32, 128} × lr {1e-3, 1e-4}.
- **S3 val** = the `val` scans of C1b split 0 (NB); final S3 models retrain on all NB scans.
- DEV smoke tests (one LOSO fold) check runtime and convergence only; DEV numbers are never reported as tests.
