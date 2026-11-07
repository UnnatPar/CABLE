# BRIDGE-013 results: the group-level (many-viewer) EEG <-> fMRI ceiling, both directions (NATVIEW)

Protocol: `experiments/BRIDGE_013_PROTOCOL.md` (registered 2026-10-28 before scoring, 9360cd5; scoring code committed
before any score was viewed, 19fc220). Code: `experiments/bridge013/b13group.py` (readout `b13show.py`). Results:
`experiments/bridge013/results/b13_summary.json`. Compute: desktop CPU, 17 minutes.

Data: NATVIEW, 7 movies in 6 units (dme + dmh are the same video, one unit), 15-20 viewers per movie, random halves of
~9 viewers. Every model is trained on the *other* movies. Numbers: point estimate (mean of 200 random viewer splits)
[95% CI, two-level bootstrap over movies and subjects]; "sub" = subject-only bootstrap (movies fixed).

## Verdict

Removing person-to-person variance, each person's own state and all measurement noise (the infinite-viewer limit of
the shared, stimulus-driven signal), **the ceiling depends on direction, and it is the reverse of what we expected:**

- **fMRI -> EEG is high.** Posterior alpha + beta power: **rho .72 [.57, 1.55]** (sub .59-.91). All channel-bands: .71
  [.52, 1.68]. About half (.72^2) of the stimulus-driven slow EEG power that people share is a linear readout of
  BOLD, and at least a third (.57^2) with 95% confidence.
- **EEG -> fMRI is lower and network-specific.** All cortex: .34 [.16, 1.15]. That is not measurable by the
  registered rule: EEG's predictions barely repeat across viewer halves. Using only the alpha and beta bands (no
  artifact-prone delta/gamma): **.38 [.22, 1.03]**, measurable. By network, the dorsal attention network reaches **.83
  [.63, 1.61]** (alpha + beta) and the visual network .64-.78. Default, control, limbic and somatomotor sit near 0.
- **Why the asymmetry:** BOLD has ~100 parcels of separate stimulus-driven signals. Slow EEG power is a blurred,
  low-dimensional mix of a few of them. Reading a blurred summary out of the detailed signal is easy. Recovering the
  detail from the summary is not (the inverse problem).
- **No visibility gradient again** (P3 fails). The middle-visibility third is best.
- **At the group level EEG carries information that body signals don't** (P4 passes): EEG + body beats body alone by
  +.08 [.02, .25] in cortex. EEG's and body's stimulus-driven predictions overlap only ~.24. Within one person
  (BRIDGE-012), heart rate and breathing swamped EEG. Averaging removes that arousal noise and exposes a real
  stimulus-driven EEG -> BOLD link.
- **Per viewer, the shared part is tiny:** 4% of cortical BOLD (visual 10%), and 0.4-1% of slow EEG band power.
  Measuring 90% of the ceiling directly would take about 500 (fMRI -> EEG) to 750 (EEG -> fMRI) viewers of the same
  film in each modality.

## Registered primary outcomes

| outcome | estimate [two-level 95% CI] | sub CI | reading (registered rule) |
|---|---|---|---|
| P1 EEG -> BOLD, high-visibility cortex | .32 [.15, 1.08] | [.18, .65] | not measurable (rel_P CI touches 0): **not resolved** |
| P2 BOLD -> EEG, posterior alpha + beta | **.72 [.57, 1.55]** | [.59, .91] | measurable; at least "partial", consistent with "largely the same"; band not resolved |
| P3 visibility gradient (high - low) | .07 [-.27, .31] | [-.05, .26] | **fails** (CI includes 0) |
| P4 EEG beyond body, all cortex (rho_EB - rho_B) | **+.08 [.02, .25]** | [.03, .12] | **passes** |

## Components (rho = cross / sqrt(rel_P x rel_T); halves of ~9 viewers)

| model, group | rel_T | rel_P | cross | rho [two-level CI] | measurable |
|---|---|---|---|---|---|
| EEG -> BOLD, high-vis cortex | .281 | .059 | .041 | .32 [.15, 1.08] | no |
| EEG -> BOLD, middle | .324 | .056 | .058 | .43 [.23, 1.43] | no |
| EEG -> BOLD, low | .250 | .054 | .029 | .25 [.05, .99] | no |
| EEG -> BOLD, all cortex | .285 | .056 | .042 | .34 [.16, 1.15] | no |
| EEG -> BOLD, visual | .513 | .053 | .130 | .78 [.30, 2.46] | no |
| EEG -> BOLD, dorsal attention | .501 | .101 | .192 | .85 [.56, 3.15] | no |
| EEG (alpha + beta) -> BOLD, all cortex | .285 | .069 | .053 | **.38 [.22, 1.03]** | yes |
| EEG (alpha + beta) -> BOLD, high-vis | .281 | .071 | .057 | .41 [.23, 1.18] | yes |
| EEG (alpha + beta) -> BOLD, dorsal attention | .501 | .160 | .236 | **.83 [.63, 1.61]** | yes |
| EEG (alpha + beta) -> BOLD, visual | .513 | .134 | .167 | .64 [.40, 1.87] | no |
| EEG -> BOLD after GSR, all cortex | .376 | .050 | .068 | .50 [.32, 1.49] | no |
| BOLD -> EEG, posterior alpha + beta | .075 | .550 | .147 | **.72 [.57, 1.55]** | yes |
| BOLD -> EEG, all channel-bands | .032 | .525 | .092 | .71 [.52, 1.68] | yes |
| BOLD -> EEG, beta (all channels) | .055 | .564 | .140 | .80 [.60, 1.56] | yes |
| BOLD -> EEG, global alpha | .082 | .554 | .163 | .77 [.51, 2.17] | no |

Default, control, limbic and somatomotor networks: EEG -> BOLD rho between -.55 and .01 (all EEG or alpha + beta), with
CIs spanning roughly -4 to +1.5 (nothing there).

## Secondary outcomes

**S1, how much is shared across viewers** (half = ~9 viewers; full group = ~18, Spearman-Brown; per viewer = implied
single-viewer share):

| signal | half | full group | per viewer | BRIDGE-012 within-person repeat |
|---|---|---|---|---|
| BOLD all cortex | .285 | .443 | .042 | .072 |
| BOLD visual | .513 | .678 | .104 | .124 |
| BOLD default | .180 | .306 | .024 | .044 |
| BOLD global | .184 | .311 | .024 | .026 |
| BOLD after GSR, cortex | .376 | .546 | .062 | .103 |
| EEG posterior alpha + beta | .075 | .139 | .009 | .033 |
| EEG global alpha | .082 | .151 | .010 | .058 |
| EEG all channel-bands | .032 | .063 | .004 | .021 |
| EEG gamma | .004 | .009 | .000 | |

For BOLD, the share common to all viewers is about 60% of the within-person repeat share (visual 84%). For EEG it
is only 20-30%. The difference is each person's own, reproducible stimulus response. Slow EEG band power is under 1%
shared per viewer.

**S2, per movie.** Single-movie rho is unstable: rel_P is near or below 0 for some movies (monkey1 EEG -> BOLD is
undefined). EEG -> BOLD all cortex: dm .22, inscapes .08, monkey2 .75, monkey5 .41, tp 1.01. BOLD -> EEG all
channel-bands: dm .55, tp .86, others .85-1.6. Only the pooled estimates are interpretable.

**S3, individual-trained model (CABLE-style training on single runs, simultaneous).** Averaged over viewers its
predictions barely carry the group signal: all cortex rho .18 [-.15, .84], cross .024 (CI includes 0). Training on
moment-to-moment coupling within people does not learn the shared stimulus mapping. This is the same lesson as
BRIDGE-011 and BRIDGE-012.

**S4, alpha + beta only.** Dropping delta, theta and gamma makes EEG's predictions more reliable (rel_P .069 vs
.056) and the estimates measurable. Most of the dropped bands' stimulus-locked content is noise or artifact for this
purpose.

**S5, GSR targets.** Group rel_T rises (.29 -> .38 cortex), and EEG -> BOLD rho is .50 [.32, 1.49] (not measurable).
The global signal is not what EEG explains at the group level.

**S6, body signals and EEG.** Body -> EEG posterior alpha + beta .67 [.29, .93]. BOLD + body -> EEG .80 [.61, 1.57]
vs BOLD alone .72. Movie-driven body signals (pupil, blinks, gaze) also track the shared EEG alpha/beta, because one
movie event (a luminance change, a cut) drives pupil, occipital alpha and visual cortex together.

**S7, overlap of the EEG and body routes to BOLD** (disattenuated correlation of their predictions): all cortex .24
[-.07, .89]; dorsal attention .67. At the group level, EEG and body predict largely different parts of BOLD.

Body -> BOLD for reference: all cortex .37 [.25, .45]; EEG + body .45 [.34, .64].

**S8, viewers needed** for the full-group r to reach 90% of rho (from the per-viewer shares): EEG -> BOLD cortex ~760,
high-vis ~740, visual ~730; BOLD -> EEG posterior alpha + beta ~520; body -> BOLD ~260.

**C1, mismatched movies.** Cross-correlation between one movie's prediction and another movie's target: between
-.016 and +.002 for every primary group, all CIs inside +-.045. The movie clocks are right, and nothing leaks across
movies.

## What this means

1. **The true ceiling, with person-to-person variance and noise removed:** about **.7 for fMRI -> EEG** (slow alpha/beta
   power; 95% lower bound .57) and about **.35-.4 for EEG -> fMRI across cortex**, reaching **~.8 in the dorsal attention
   network** and .6-.8 in visual cortex. These are lower bounds for a linear model trained on ~30 minutes of group
   data. A better model can only raise them.
2. **"EEG -> fMRI should be easier" is reversed for the shared signal.** fMRI contains most of what slow EEG power
   shares across people. EEG contains only part of what fMRI shares, outside attention and visual networks.
3. **For expanding fMRI data with EEG:** a group-averaged EEG cohort can stand in for an fMRI cohort mainly for dorsal
   attention and visual cortex, and only with hundreds of viewers per film. HBN (~1,400+ EEG viewers of *The
   Present*) is the dataset that fits this. Training CABLE on simultaneous single-person data does not learn this
   mapping (S3).
4. **CABLE's own task (one person, moment to moment) is a different estimand.** Its ceiling cannot be measured with
   repeats. BRIDGE-012 showed that, within a person, arousal and physiology dominate it.

## Limits

- **CI construction is conservative.** The bootstrap resamples subjects with replacement and splits the unique ones,
  so bootstrap halves hold ~6 unique viewers instead of ~9. Component CIs are shifted down (rel_T point estimates
  fall above their CIs), and rho CIs, especially their upper ends above 1, are wider than the data warrant. Kept as
  registered. Lower bounds are the trustworthy side.
- **Model-limited.** For EEG -> BOLD, inner CV chose the strongest shrinkage on the grid (alpha 1e7), which is near
  the plain cross-covariance limit. There are ~30 minutes of group data per training fold.
- One dataset (21 adults, 3 T, eyes open, 40 minutes of distinct content, 6 movie units); per-movie estimates are
  unstable.
- fMRI -> EEG is defined only for slow band-power envelopes (< .15 Hz). Faster EEG (ERPs, phase, millisecond timing)
  is invisible to BOLD by physics.
- The coupling measured is between stimulus-driven components. A shared movie driver (e.g. luminance) can couple
  them without a local, one-to-one neural copy (S6).
