# Experiment 2: uncertainty and coefficient-history length

**Status: completed November 1, 2026.** Development/final forecasts and both bootstrap parts passed independent saved-output audits. See the [execution record and reproduction commands](executed.md) and [complete interpretation](results.md).

The primary block-13 value-weighted results do **not** establish a factor advantage over matched own history or ridge at any coefficient-history rule. L=104 passes the declared approximate Holm rule against elastic net (8.5696% gain, adjusted p=0.0019) and PLS (13.7401%, p=0.0019). None of the three finite-history factor variants passes against the expanding factor control; their primary point effects are all negative. The finite-sample calibration warning below applies even to the small p-values.

Part A's already-seen 2022–2024 comparison passes that rule only against value-weighted own history (4.2733%, adjusted p=0.0028), not the three direct references; no equal-weighted Part A comparison passes. All adverse targets, direct-method comparisons, and block sensitivities are retained in [results.md](results.md) and the full artifact tables. No new winner was selected.

The October 31 [protocol](protocol.md) and [planning TOML](../../configs/experiment_02_plan.toml) retain their original proposed-status wording as part of the frozen design record. The new [executable configuration](../../configs/experiment_02.toml) and [Experiment 2 runner](../../scripts/run_experiment_02.py) implement that design; the planning TOML itself is not executable. The [initial freeze](../../results/experiment-02-2026-11-01/protocol_freeze.json) and [preflight record](../../results/experiment-02-2026-11-01/preflight.md) identify the authorized run and validation gates.

The [completed first pilot](../../results/fixed-pilot-2026-10-27/README.md) leaves two questions open: how uncertain is the factor procedure's advantage over own history and direct methods, and does shortening its coefficient-training history change its accuracy? This study is allowed to find no reliable advantage. Smaller point-estimate MSE does not guarantee statistical significance.

| Part | Forecast observations | Purpose | Evidence status |
| --- | --- | --- | --- |
| A | Saved Experiment 1 forecasts, response years 2022–2024 | Paired uncertainty for the original frozen procedure versus own history, ridge, elastic net, and PLS | Exploratory: the evaluation results have already been inspected |
| B development | History-matched forecasts on common eligible pre-2025 dates | Validate timing/implementation and document every fixed cell | Development, including the previously inspected 2022–2024 period |
| B new final | Responses January 3, 2025–August 28, 2026 | Evaluate four frozen coefficient-history rules on identical dates | Frozen-procedure evaluation of a retrospectively observed interval; uninspected-loss evidence and pre-final freeze required; approximate inference |

The primary factor procedure is fixed throughout: **the Experiment 1 development-selected `factor_pooled__M-all__O-all`**, two PCs measured with all 48 industries and common factor slopes estimated across all 48 outcomes. There is no new factor-cell selection by history length. Industry intercepts and own-history coefficients remain separate. Primary direct comparators always use the same 48 current measurement variables.

Coefficient histories are **104, 260, 520, and expanding** eligible pairs. PCA uses expanding historical predictors, identically across the four history rules. Every supervised coefficient, nuisance projection, direct-model scaler, and supervised PLS direction uses its declared coefficient window. Outcome donors initially receive the same window as the target. The six targets remain `Food, Mach, Banks, Oil, Util, Hlth`. All 18 original policy labels are reported per history as secondary fixed-cell results, without selecting a new final winner.

The first common outer cutoff is **572 pairs: 520 inner coefficient-training pairs plus 52 historical validation pairs**. Refits occur at `572 + 13*k` for every history rule. Because `572 = 260 + 24*13`, this preserves the first pilot's refit phase. Evaluation excludes earlier first-pilot forecasts and never restarts the schedule at the new-final boundary.

For factor forecast F and reference R, the primary advantage is

`G(F,R) = 1 - (1/6) * sum_i [MSE_i(F) / MSE_i(R)]`.

Positive G favors F. Each bootstrap draw resamples the same date indices for all targets, methods, history rules, and both weightings and recomputes **both** MSEs in every target ratio. There are no fixed development denominators. The frozen procedure uses a stationary bootstrap with 9,999 draws, expected block length 13 retained dates, seed 20261031, null-centered one-sided p-values, and basic two-sided nominal-95% intervals. Expected lengths 6 and 26 are fixed sensitivities.

Part A has four exploratory comparisons and a Holm family of four. Part B has **one primary Holm family of 19**: four references times four histories, plus the three direct comparisons of each finite-history factor forecast with its expanding-history version. Different factor-versus-baseline p-values do not establish a history effect; the latter comparisons test it directly. Equal-weighted results form a separate 19-comparison robustness family and are not an independent replication.

The new interval contains only about 87 weekly responses, so low power and inconclusive intervals are plausible. More strongly, the bounded [synthetic diagnostic](../../results/experiment-02-2026-11-01/synthetic_validation.json) showed adverse rejection/coverage behavior; nominal finite-sample calibration was not established. It examined synthetic loss processes, not the complete learned forecast pipeline or the four-/nineteen-test families. Holm adjustment does not repair unestablished marginal p-value calibration. This limitation applies even when an adjusted p-value is small.

Dependence, expanding estimation, tuning, and nested predictors further limit inference. See the unchanged [full protocol](protocol.md) for exact design conventions and [executed.md](executed.md) for completed gates, freezes, and output audits. Audit success establishes reproducibility of the computations, not statistical calibration, causal mechanisms, learned donor selection, or universal factor superiority.
