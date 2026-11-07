# Manifest for `followup/`

| Field | Value |
|---|---|
| Source repository | Presonance `decode` (private) |
| Source branch | `codex/cable-followup-validation` |
| Immutable source commit | `0c107207b9b020e87db6c3f285290d029c63084b` |
| Original CABLE source (canonical) | Presonance `encode`, branch `cable-interpolator`, commit `3c7aaf7b0c7753a058eebda7ef1132d69df096ec` |
| Destination path | `followup/` in this repository |
| Verification | SHA-256 of each file below equals SHA-256 of the git blob at the source commit (checked when the files were copied) |

## Files

| Destination | Source path in `decode` | SHA-256 |
|---|---|---|
| `followup/cable_original/REPORT.md` | `benchmarks/cable_original/validation/output/cable_original/REPORT.md` | `c0b42f15289b8d574547f0387bfc6a29b507868b178954d5285ae1a2604ca905` |
| `followup/cable_original/results.json` | `benchmarks/cable_original/validation/output/cable_original/results.json` | `baddd5086eab7a199405233466d0b0c5820780dba153ae17afd0a5349d589525` |
| `followup/cable_original/protocol.lock.json` | `benchmarks/cable_original/validation/output/cable_original/protocol.lock.json` | `c5168acd27d4c12d78cea0ad6585d3b70d2d589db67e6d9f42989efb5fde4a95` |
| `followup/cable_offline_combined/REPORT.md` | `benchmarks/cable_goal/validation/output/cable_offline_combined/REPORT.md` | `4d9fa58a2f4ff27fb70f390cc6ff2fc20f2baeeccbc10a135553442e2b087323` |
| `followup/cable_offline_combined/results.json` | `benchmarks/cable_goal/validation/output/cable_offline_combined/results.json` | `701809d8a45f987d8e977e1e7002d31077c06e14504f4ba99e0fc669d269c511` |
| `followup/cable_offline_combined/verification.json` | `benchmarks/cable_goal/validation/output/cable_offline_combined/verification.json` | `085d55ef9db9c64a644643cd72fc61866cf03d23d154983c6e9f837ff1389661` |
| `followup/cable_offline_combined/PROTOCOL.md` | `benchmarks/cable_goal/experiments/cable_offline_combined/PROTOCOL.md` | `81b4debd972d8dfe05598aa841145cc658748186294deea76caf97f7c22aace5` |
| `followup/multiclarid_pooling/REPORT.md` | `benchmarks/cable_goal/validation/output/cable_goal/MULTICLARID_FINAL_REPORT.md` | `a8bbacfe4384c874384b3855f409a11bc6c024bc620eb28fe63fc61b3e1a47f9` |
| `followup/multiclarid_pooling/results.json` | `benchmarks/cable_goal/validation/output/cable_goal/multiclarid_replication/results.json` | `8d5487ce8b43452bf18ad6236d5a6439e3c6d0b44a836a8c1be187af9b7409c0` |
| `followup/multiclarid_pooling/variability_results.json` | `benchmarks/cable_goal/validation/output/cable_goal/multiclarid_replication/variability_results.json` | `5f610520a39ca92c567032090402e8a14f81096c4058931013cd7f630cad57a1` |
| `followup/multiclarid_pooling/PROTOCOL.md` | `benchmarks/cable_goal/experiments/cable_goal/MULTICLARID_POOL_REPLICATION_SPEC.md` | `beb755ca9533fa94dbfa96a28fb2b64c7fa852101f33cd944bcdd82d0c439e02` |

Reports are copied verbatim. Where they use first person, it refers to the run that executed the
protocol.

## Files from `encode` (later bridge experiments)

| Field | Value |
|---|---|
| Source repository | Presonance `encode` (private) |
| Source branch | `cable-interpolator` |
| Immutable source commit | `0b9676bb338b8b7de01751e96d69f724a32940ad` |
| Destination path | `followup/bridge_limits/` |
| Verification | SHA-256 of each file equals SHA-256 of the git blob at the source commit (checked when copied) |

| Destination | Source path in `encode` | SHA-256 |
|---|---|---|
| `followup/bridge_limits/BRIDGE_010_RESULTS.md` | `presonance/fmri-eeg-interpolator/BRIDGE_010_RESULTS.md` | `1182ee2ec05b768df60ccfe911213354c7fc1ff4e3075fe08d4ba7bd8fb60832` |
| `followup/bridge_limits/BRIDGE_011_RESULTS.md` | `presonance/fmri-eeg-interpolator/BRIDGE_011_RESULTS.md` | `72cf93f30224d272f8a695ddee9294029aa0eb309939df79a0c7be5acf08c50e` |
| `followup/bridge_limits/BRIDGE_012_RESULTS.md` | `presonance/fmri-eeg-interpolator/BRIDGE_012_RESULTS.md` | `1f65543bf5747eaa3b091cc0e4b17d60b028dd97562090ff88a1d5457330b651` |
| `followup/bridge_limits/BRIDGE_013_RESULTS.md` | `presonance/fmri-eeg-interpolator/BRIDGE_013_RESULTS.md` | `1500c3849dce15e10d5142d1b4a7c17ed5fe5bfd88f7725f8541ab34ff81a3b2` |
| `followup/bridge_limits/BRIDGE_010_PROTOCOL.md` | `presonance/fmri-eeg-interpolator/experiments/BRIDGE_010_PROTOCOL.md` | `f287ffd92b18dbed20f4cfc05413a72b76c80263eeb9b9399efb31fb463156f0` |
| `followup/bridge_limits/BRIDGE_012_PROTOCOL.md` | `presonance/fmri-eeg-interpolator/experiments/BRIDGE_012_PROTOCOL.md` | `15360251cad2ba297922f45b0a73b69a9125ae3dc9e50c89943ff826e922eefd` |
| `followup/bridge_limits/BRIDGE_013_PROTOCOL.md` | `presonance/fmri-eeg-interpolator/experiments/BRIDGE_013_PROTOCOL.md` | `b9a03cd2bbbb7fc7dcd7d560f3b161d4113d2f46c121b91212bcefed40112388` |
| `followup/bridge_limits/b10_summary.json` | `presonance/fmri-eeg-interpolator/experiments/bridge010/results/b10_summary.json` | `bb6736e33283270ee0d10ad8ad30b42dc7d0af357e89832feb3573e29ed0ecfc` |
| `followup/bridge_limits/b12_summary.json` | `presonance/fmri-eeg-interpolator/experiments/bridge012/results/b12_summary.json` | `24c89082ac862a3b398d809dcea29f1834a99f00a81fdebaada95c8481a3d383` |
| `followup/bridge_limits/b13_summary.json` | `presonance/fmri-eeg-interpolator/experiments/bridge013/results/b13_summary.json` | `6b9b310e6763ff1b791b050d6eeb666099d3eea99e7a0057113d05aabe78eb19` |

The BRIDGE-011 protocol, its code and its raw outputs, the BRIDGE-010 to 013 code, the outreach material and
all other files on that branch are not copied. The BRIDGE-011 numbers quoted in `FOLLOWUP.md` come from its
results document only.

## Licence note

The source repository's LICENSE applies CC-BY-NC-4.0 only to the vendored `brain_encoder` component and
states that other original material in that repository is proprietary to Presonance. The files here are
original follow-up material, not `brain_encoder` code. They are contributed for inclusion in this
repository at the discretion of its maintainers; no licence for them is declared by this change. This
repository currently has no LICENSE file, and no LICENSE file was found at the `encode` source path either. The underlying datasets keep the licences on their OpenNeuro
pages and are not redistributed here.

## Excluded material

Raw EEG and MRI, per-participant anatomy and QA images, prediction matrices, model weights, private
caches, the follow-up adapter code, the manuscript, credentials and anything from the production
codebase. Other result files in the source packets (for example the 130 KB execution lock and the
cohort metadata) are not copied; only the files needed to read and check rows 1-4 are.
