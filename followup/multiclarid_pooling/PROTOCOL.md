# Independent replication of frozen pooled CABLE training

User priority: replicate the earlier pooled66-versus-source22 gain on another
genuinely reserved cohort. This tests those existing models; it does not promote
the failed G90/G93 calibration or respiration augmentation. Reserve the same
34 MULTI-CLARID people at revision a225eb4608bd72e20a6aa6aa6fdda09692f77a7f.
All34 resting recordings are primary; the five learning recordings are not new
people and stay unopened in this execution. No subject is assigned to training.

## Models, endpoint and interpretation

Primary pair: the already frozen full12-member source22 and pooled66 CORE19
CABLE ensembles, exactly the state SHA256 identities in temple_dev_predict.lock.
Source22 trains on22NeuroBOLT people; pooled66 adds24ds006040 and20ds002739 people.
No new fit, member weighting, PCA selection, calibration, EEG/ECG addition or
selected lag. Full99 and its two fixed time origins are diagnostic references,
not a test-set-selected candidate. Retain provider offline artifact correction
and whole-record EEG-prediction normalization disclosures.

Score native measured original seven-target BOLD, mean signed Pearson r over
the six original regions plus measured global. Same support for both ensembles.
Do not residualize targets, select a region/sign/shift, or replace this endpoint
with a retargeted model. At least100eligible native rows per recording; retain
failed/missing cases, reasons and all34assigned people without replacements.

Replication means a positive paired person mean, positive person95%bootstrap
lower bound and two-sided paired test p<.05. A practically substantial upgrade
additionally requires mean gain>=+.03; the earlier +.017 is not renamed that.
The result is available-case if any input/QA fails; disclose its inferential
limits and never impute failures as zero. No population or full-cohort claim is
supported simply by a favorable quality-selected subset. Participant count,
labeled rows and dataset composition co-vary: do not call pooling a diversity
effect. Anonymous cross-release identity overlap remains unproven.

Use20000whole-person bootstrap draws(seed2026102696)and200000MonteCarlo paired
sign flips(seed2026102697; add-one p). Whole-person is the unit, not frames or
regions. Record every person and region. Conditional60/120second native-time
block sensitivity will use identical sampled rows for both predictions before
eligibility intersection; publish its source before scoring. No full-retraining
uncertainty claim. Freeze the exact statistical implementation before signals.

Fixed diagnostics are full99-versus-pooled66, pooled66-versus-existing MRI-origin
clock, and aligned pooled66-versus-mean signed r of circular native prediction
shifts±60/±120seconds. These three comparisons form Holm3; no favorable secondary
replaces the primary. No neural-specificity claim without adequate alignment,
clock and physiology controls. A fresh pooling result does not identify a ceiling.

## EEG frontend and release timing

Read multiplexed little-endian INT16,72channels at500Hz. Use VHDR per-channel
resolution exactly once to obtain microvolts; channels.tsv documents units despite
corrupted VHDR unit text. Select only the19 measured EEG CORE19 channels, in
fixed order; no reference, GSR, ECG, EOG or EMG channel enters new features.
Original500microvolt validity rule and original frozen14feature families remain.

Use an explicit401tap Hamming FIR,100Hzcutoff at500Hz, then decimate2 with
resample_poly and known200-input-sample delay compensation. Output sample0 is
EEGtime0, odd lengths round up, zero boundary padding. It uses±.4seconds of EEG
around an output sample and is offline; do not claim an end-to-end causal system.
Require synthetic parity to direct convolution, MNE units, impulse alignment,
1–45Hz passband, alias suppression, sensor exclusion and bounded future influence.
No resampling method or delay is chosen using reserved correlations.

Use functional event onset and paired EEG sample metadata to derive constant
EEG-minus-MRI offset; require residual<=2ms and |offset|<=2ms. All current source
tables imply0. Nominal TR is the JSON protocol2seconds, with NIfTI float rounding
checked within1microsecond. Native target centers are k*2+1seconds plus offset.
Preserve the two earlier strict-clock failures(sub12/sub26), first marker54ms,
and require max cumulative scanner-marker drift<=12ms/first-origin<=60ms.
Check that publisher-event, first-marker-grid and individual-marker midpoints
all choose identical original0.8second CABLE indices; do not search offsets or
remove the two people. This is a publisher-declared release map, not independent
hardware proof. Both ensembles use the same fixed clock/support.

## Acquisition gates still required

G96 freezes only metadata/synthetic frontend and this prospective specification.
It does NOT permit reserved signal acquisition. Before any waveform/BOLD payload,
publish a complete execution lock: source models, all input annex keys, frontend,
MRI processing/QA and independent replay, physiology time-column checks, failure
rules, runtime/atlas hashes and statistics. Source metadata contain34T1s and no
field maps; the MRI method must explicitly disclose that limitation and preserve
the original atlas/target operator. Anatomy/registration QA precedes targets.
The33available rest physiology files and one missing file are a separate census;
missing physiology must not remove that person's EEG-only primary recording.
ECG is not promoted. Any new physiology comparison requires its own frozen
analysis before outcomes; this execution initially verifies timing only.

Seal all completed native inputs, QA and input-only model predictions before
sole aggregate outcome opening. No model/clock/QA changes driven by scores.
Retain all failures and outcome-blind repairs explicitly. All protected Temple
people stay closed. No three-day/cap-replacement or true EEG-ceiling claim follows.
