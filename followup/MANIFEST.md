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

## Licence note

The source repository's LICENSE applies CC-BY-NC-4.0 only to the vendored `brain_encoder` component and
states that other original material in that repository is proprietary to Presonance. The files here are
original follow-up material, not `brain_encoder` code. They are contributed for inclusion in this
repository at the discretion of its maintainers; no licence for them is declared by this change. This
repository currently has no LICENSE file. The underlying datasets keep the licences on their OpenNeuro
pages and are not redistributed here.

## Excluded material

Raw EEG and MRI, per-participant anatomy and QA images, prediction matrices, model weights, private
caches, the follow-up adapter code, the manuscript, credentials and anything from the production
codebase. Other result files in the source packets (for example the 130 KB execution lock and the
cohort metadata) are not copied; only the files needed to read and check rows 1-4 are.
