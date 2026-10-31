# Experiment 2: uncertainty and coefficient-history length

**Status: proposed protocol, not implemented or run.** No bootstrap replicates, p-values, confidence intervals, new forecasts, or history-length comparisons have been calculated. The [planning TOML](../../configs/experiment_02_plan.toml) is descriptive and must not be passed to the existing experiment runners.

The [completed first pilot](../../results/fixed-pilot-2026-10-27/README.md) leaves two questions open: how uncertain is the factor procedure's advantage over own history and direct methods, and does shortening its coefficient-training history change its accuracy? This study is allowed to find no reliable advantage. Smaller point-estimate MSE does not guarantee statistical significance.

| Part | Forecast observations | Purpose | Evidence status |
| --- | --- | --- | --- |
| A | Saved Experiment 1 forecasts, response years 2022–2024 | Paired uncertainty for the original frozen procedure versus own history, ridge, elastic net, and PLS | Exploratory: the evaluation results have already been inspected |
| B development | History-matched forecasts on common eligible pre-2025 dates | Validate timing/implementation and document every fixed cell | Development, including the previously inspected 2022–2024 period |
| B new final | Proposed responses January 3, 2025–August 28, 2026 | Evaluate four frozen coefficient-history rules on identical dates | Prospective protocol for an uninspected algorithm-evaluation interval, conditional on verification and a freeze before scoring; approximate inference |

The primary factor procedure is fixed throughout: **the Experiment 1 development-selected `factor_pooled__M-all__O-all`**, two PCs measured with all 48 industries and common factor slopes estimated across all 48 outcomes. There is no new factor-cell selection by history length. Industry intercepts and own-history coefficients remain separate. Primary direct comparators always use the same 48 current measurement variables.

Coefficient histories are **104, 260, 520, and expanding** eligible pairs. PCA uses expanding historical predictors, identically across the four history rules. Every supervised coefficient, nuisance projection, direct-model scaler, and supervised PLS direction uses its declared coefficient window. Outcome donors initially receive the same window as the target. The six targets remain `Food, Mach, Banks, Oil, Util, Hlth`. All 18 original policy labels are reported per history as secondary fixed-cell results, without selecting a new final winner.

The first common outer cutoff is **572 pairs: 520 inner coefficient-training pairs plus 52 historical validation pairs**. Refits occur at `572 + 13*k` for every history rule. Because `572 = 260 + 24*13`, this preserves the first pilot's refit phase. Evaluation excludes earlier first-pilot forecasts and never restarts the schedule at the new-final boundary.

For factor forecast F and reference R, the primary advantage is

`G(F,R) = 1 - (1/6) * sum_i [MSE_i(F) / MSE_i(R)]`.

Positive G favors F. Each bootstrap draw resamples the same date indices for all targets, methods, history rules, and both weightings and recomputes **both** MSEs in every target ratio. There are no fixed development denominators. The proposal uses a stationary bootstrap with 9,999 draws, expected block length 13 retained dates, seed 20261031, null-centered one-sided p-values, and basic two-sided 95% intervals. Expected lengths 6 and 26 are fixed sensitivities.

Part A has four exploratory comparisons and a Holm family of four. Part B has **one primary Holm family of 19**: four references times four histories, plus the three direct comparisons of each finite-history factor forecast with its expanding-history version. Different factor-versus-baseline p-values do not establish a history effect; the latter comparisons test it directly. Equal-weighted results form a separate 19-comparison robustness family and are not an independent replication.

The proposed new interval contains only about 87 weekly responses, so low power and inconclusive intervals are plausible. Dependence, expanding estimation, tuning, and nested predictors make this an approximate forecast-loss analysis, not a guaranteed finite-sample test or a proof of universal factor superiority. See the [full protocol](protocol.md) for exact hypotheses, bootstrap tail/interval conventions, chronology, limitations, and implementation gates. No runnable Experiment 2 command is provided.
