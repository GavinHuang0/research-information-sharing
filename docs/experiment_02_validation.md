# Experiment 2 validation and audit record

This record began on November 1, 2026, before any Experiment 2 empirical forecast or bootstrap execution. It distinguishes completed data-only checks from implementation gates and later output audits. The scientific specification is [the frozen-design protocol](../experiments/02-bootstrap-history/protocol.md); the [planning configuration](../configs/experiment_02_plan.toml) records the same decisions. Validation does not prove finite-sample calibration of the full learning pipeline.

## Finite-sample warning before empirical execution

**The implementation checks passed, but the bounded synthetic diagnostic did not establish nominal calibration.** Root ran the fixed diagnostic once with 100 independent synthetic datasets at each of T=87 and T=156, 499 bootstrap draws, expected block length 13, and the declared bootstrap seed. Under a nondegenerate equal-marginal-loss null, the unadjusted one-sided nominal-5% rejection rates were 11/100 at T=87 and 6/100 at T=156. Their 95% Wilson Monte Carlo intervals were approximately 0.063–0.186 and 0.028–0.125. Nominal-95% basic-interval coverage was only 90/100 and 81/100, respectively. These are adverse finite-sample diagnostics, not a calibration pass.

The positive control multiplies candidate losses by `exp(-0.15)`, giving a known population advantage `1-exp(-0.15)` (about 13.93%). Its rejection counts were 99/100 and 100/100, with the same 90/100 and 81/100 coverage. This is a relatively large synthetic effect; these power observations do not establish power for smaller empirical gains. The Monte Carlo run concerns a single raw comparison, not Holm's four-/nineteen-test family or the complete forecast-learning pipeline. It uses fewer bootstrap draws than the empirical protocol; increasing draws does not by itself establish correct finite-sample calibration.

Independent source review confirmed the diagnostic's truth and coverage logic. Every AR(1) component is initialized from its stationary Gaussian distribution. Candidate/reference model-specific components are independent with identical distributions, so each target has equal population mean losses under the null. The multiplicative positive shift changes G to `1-c+c*G_null`, where `c=exp(-0.15)`. The basic interval transforms in the same affine way; therefore identical null/positive coverage counts are expected, rather than evidence of a coverage-code error. Coverage checks the declared population G, and rejection uses the declared positive-effect/one-sided-p rule. No program error was identified in these calculations on source inspection; the diagnostic was not rerun or searched over seeds by the independent auditor.

The empirical procedure remains the prespecified ratio statistic, block length 13, 9,999 draws, seed, basic intervals, and Holm families. Do not present its p-values as established exact/nominal-5% tests or its intervals as demonstrated 95% coverage. Holm adjustment cannot repair marginal p-values whose finite-sample calibration is not established. Preserve this warning and the adverse diagnostic output with the run; all empirical inference must retain its approximate, limited status even if an adjusted p-value is small.

## Completed source and calendar preflight

An independent read-only check verified SHA256 and byte counts for 21 unique files referenced by the daily/weekly manifests: original archives, acquisition metadata, daily return panels, labels/missingness, weekly feature panels, coverage, and input provenance. Both ZIPs pass integrity checks. The original return member says it was created using the **202608 CRSP database**.

Both prepared daily panels were compared directly with independently parsed provider ZIP sections. Source dates/order and the 48 official labels agree. Every nonmissing provider return is divided by 100; source missing sentinels remain missing. Daily inputs contain 26,317 rows each and end August 31, 2026.

Weekly features were independently reconstructed without the forecast runner or feature builder: each daily date was assigned to the first Friday on or after it; observed returns were counted; squared decimal returns were summed; the minimum count of three was applied; then square roots, log offsets, and complete four-/twelve-week means were checked. All 12 saved panels agree within their declared 12-digit serialization precision, including exact missing-cell masks. The final September 4 label contains one daily observation per industry and is invalid for the variance proxy. August 28 is the last complete response week.

The provider's January 2025 CIZ adoption is a **release/vintage convention**. This fixed reconstructed history must not be described as FIZ before response-year 2025 and CIZ afterward. The archive/header and provenance identify the version used; they do not prove that economic relationships are stable or that the dataset was available unrevised at each historical origin.

The independently constructed intersection of both weightings' complete 48-industry predictors, next-calendar-week responses, and own histories gives:

| Item | Verified value |
| --- | --- |
| Retained pairs, origins from 2000 through response August 28, 2026 | 1,377 |
| First retained origin / response | January 7 / January 14, 2000 |
| Last retained origin / response | August 21 / August 28, 2026 |
| First common forecast index | 572 |
| First common forecast origin / response | March 25 / April 1, 2011 |
| Development forecast dates after the common initial history | 718 |
| New-final response dates | 87, January 3, 2025–August 28, 2026 |
| First new-final pair index | 1,290 |
| First new-final origin | December 27, 2024 |
| Scheduled refit for that first final pair | 1,287, origin December 6, 2024 |
| Last historical response at that refit | December 6, 2024 |
| Inner-training last response / validation first origin | December 8, 2023 |
| First response in the crossing block | December 13, 2024 |
| Crossing block's development / final forecasts | 3 / 10 |
| Next scheduled refit | 1,300, origin March 7, 2025 |

The same thirteen origin dates are absent as in Experiment 1: every Friday from September 7 through November 30, 2001. Gaps were retained while building features/responses and removed only by the common pair mask. No missing date was turned into a later “next week.” Refits are counted in retained pairs; `572 + 13*k` has the same phase as `260 + 13*k`.

These are data/timing checks, not forecast-accuracy results. With all 18 cells, six targets, four history rules, and two weightings, the expected forecast inventories are 620,352 development rows and 75,168 new-final rows. Unique refit inventories are 56 development anchors and seven new-final anchors, with the boundary anchor shared between stages.

## Evidence about the uninspected interval

Before implementation/execution, the current `results` directory contained only Experiment 1. Reading only the response-date columns of its saved forecasts found development responses ending December 31, 2021 and final responses ending December 27, 2024. The available local Git refs contain two saved forecast blobs under `results`, with the same date ranges:

- `c958b0d9a777cd7f605b45e1994bd7e688856b10`: Experiment 1 development predictions.
- `65a864b67f56783ff5ed6dccfb1479ffcb92805b`: Experiment 1 final predictions.

No saved forecast-score artifact for 2025–2026 was found in this current repository or its available local Git history. This is bounded artifact evidence: it cannot prove that no one inspected unsaved losses or artifacts elsewhere. The economic outcomes and returns are already observed public historical data. The execution freeze must retain this scope statement and record the team's uninspected-loss status before the new final stage.

## Implementation gates before empirical execution

The history runner must be checked against synthetic examples and the data-only calendar above. At anchor `a`, with `b=a-52`, inner PCA uses `[0:b)` and outer PCA uses `[0:a)`. Each representation is shared exactly across history rules and outcome restrictions. Finite supervised windows are `[b-L:b)` and `[a-L:a)` for every target and donor; expanding windows start at zero. Nuisance projections, direct-model scalers, supervised PLS directions, intercepts, and local slopes obey those supervised windows. Prebuilt causal features may use their earlier calendar observations. No validation response fits its candidate pipeline.

Independent tests should check at least the following behaviors:

- The first common cutoff really leaves 520 inner coefficient pairs and 52 validation pairs; nominal L is never silently shortened.
- New-final stage execution replays the crossing refit at 1,287 rather than refitting at 1,290. Its fit and historical penalty choices match the development-side replay.
- Perturbing responses after a scheduled refit cannot change that block's forecasts/tuning. Perturbing an observation outside a finite coefficient window cannot change that model's supervised fit while PCA inputs are held fixed.
- PCA is fit once per measurement/cutoff segment and reused across L/outcome rules; donor windows match the target's L exactly.
- Memberships use industry names, preserve the fixed S set, and do not become source-column prefixes.

The statistical implementation must pass numerical and synthetic stationary-loss controls before empirical resampling. Required checks are exact PCG64 index-generation order; one shared date-index matrix across targets, policies, histories, and both weightings; ratio numerator/denominator recomputation per replicate; the root `D_b=G_b-G_hat`; the one-sided tail `(1+count(D_b>=G_hat))/(B+1)` including ties; the basic interval formula; deterministic rejection of invalid denominators; and Holm family sizes four and nineteen. Null/positive-effect controls assess implementation behavior and approximate calibration in their stated synthetic setting, not universal finite-sample validity of the empirical generated-factor pipeline.

Part A remains exploratory on previously inspected losses. Part B's primary nineteen-test family applies only to the new-final interval. Its development output is descriptive. Marginal basic intervals are not simultaneous intervals, and separate value/equal families do not establish combined across-weighting error control.

## Independent output audit after authorized runs

The later audit must verify the frozen input/configuration/code fingerprints and that the freeze precedes new-final scoring; preserve Experiment 1 bytes; check exact forecast/tuning inventories; reconstruct realized responses directly from daily data; recompute squared errors and equal-target ratio effects; and inspect every recorded PCA/supervised/validation cutoff and donor membership.

For bootstrap outputs, independently reconstruct the shared index matrices from the recorded seed/settings and compare their fingerprints, then recompute the observed effects, null-root tail counts, basic interval endpoints, and Holm-adjusted values from saved losses. No model refitting is needed for that saved-output audit. Report every adverse target/reference/history, keep block-length sensitivities separate, and retain uncertainty and nested/expanding-estimation caveats. Do not interpret an unadjusted interval as a family-wise rejection, a different p-value across histories as a direct history test, or a non-rejection as proof of equivalence.

## Completed independent history-runner checks

The new history runner was read independently against the planned inner/outer slices. Its PCA cache keys omit L and outcome membership, so the expanding representation is shared across the corresponding fits; supervised input slices use the declared recent window. History labels are stable strings recorded with each forecast/tuning row. No change to the original pilot modules was needed for these checks.

`tests/test_history_timing.py` adds three independent checks, all passed before empirical execution: the extended committed calendar without fitting empirical models; a synthetic crossing-block perturbation showing that later development and final outcomes cannot change the scheduled fit/tuning for any history rule; and a synthetic pooled model compared with an independently stacked residual regression using exactly the same recent dates for every donor and industry-specific nuisance controls. The last check also confirms that PCA uses the longer expanding predictor segment.

## Completed algorithm and orchestration gates

The recorded full suite in `.venv/experiment_02_validation.txt` passed 91 tests, including history, bootstrap, reporting, original pipeline, and independent timing checks. The auditor separately ran the three new independent history tests and eighteen bootstrap tests on numerical/synthetic fixtures; all passed. The latter cover exact RNG order, joint resampling, recomputed denominators, root-tail direction, basic intervals, invalid denominator failure, Holm adjustment, family inventories, shared weighting indices, date/target consistency, and saved index fingerprints. Passing tests is evidence that the declared algorithm was implemented; the finite-sample warning above remains in force.

Read-only orchestration review confirmed that all scientific sections of the executable configuration match the immutable planning TOML exactly. The runner checks initial code/configuration/dependency/input fingerprints, requires the completed development manifest/freeze before final scoring, permits no new policy selection, refuses existing stage directories, and normalizes newly written text before stage hashes are recorded. All 36 files in Experiment 1's artifact manifest remained unchanged during this preflight.

At this point the source/calendar, implementation, and algorithm gates passed, with the adverse synthetic calibration limitation explicitly recorded. Empirical-output audits remained pending. No Experiment 2 empirical forecasts or empirical bootstrap draws were generated by these independent preflight checks.
