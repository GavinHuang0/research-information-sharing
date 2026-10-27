# Frozen S6 industry forecasting pilot

This document declares the first fixed industry-data pilot before its development forecasts and terminal evaluation are run. The executable settings are in `configs/fixed_pilot.toml`. The fixed protocol, configuration, source-data fingerprints, and implementation fingerprints belong in the frozen run manifest. Any later design change requires a new version and is exploratory relative to this pilot.

This is a retrospective forecasting exercise on the committed October 16, 2026 French 48-industry snapshot. It evaluates forecast accuracy, rather than trading performance or a causal effect of information sharing. Industry portfolios and dates are dependent observations.

## Data, targets, and information

Use both committed daily return panels and the shared weekly feature definitions. Value-weighted portfolios are the primary analysis; equal-weighted portfolios are a robustness analysis on exactly the same dates. The latter is not an independent replication. Keep all 48 original industry columns in the provider's order. The named set is fixed as

`S = (Food, Mach, Banks, Oil, Util, Hlth)`.

These six industries are the forecast targets and the small measurement/outcome panel. Membership is chosen before evaluating forecasts. There is no random ordering, data-driven donor ranking, or prefix of the provider's column order. Every target belongs to each measurement or outcome panel used for its forecast.

For industry `j` and Friday-ending calendar week `t`, define

```
Q[j,t] = sum(r[j,d] ** 2 for d in (previous Friday, current Friday])
q[j,t] = log(Q[j,t] + 1e-8)
h[j,t] = (q[j,t], mean(q[j,t-3:t]), mean(q[j,t-11:t]))
```

Returns `r` are decimal daily returns. Require at least three observed daily returns for `Q`; otherwise it is missing. The displayed means include both endpoints, and every week in a four- or twelve-week mean must be observed. Weeks remain on a fixed `W-FRI` grid before lags and responses are formed. No filling, interpolation, annualization, or full-sample fitted transformation is permitted. Historical Saturday trading is included, so observation counts can exceed five. Variable day counts imply variable exposure in this unnormalized return-variation proxy.

At origin Friday `t`, the response is `q[j,t+1]` at the next calendar Friday, exactly seven days later. Predictors are current `q` for the declared measurement industries, together with the target's own `h`. Pooling models also use each donor's own `h`. The own one-week control is the current week's `q`, so it overlaps the target column in the measurement panel; it is not an extra one-week lag. Signed returns, macro variables, and future outcomes are not predictors. Availability means that input source dates are no later than the origin Friday within this fixed revised snapshot; it does not assert point-in-time vendor publication or unrevised historical availability.

Construct responses and twelve-week histories using the entire weekly history, then retain one common complete-case mask across all 48 industries and both weightings. Require finite current measurement predictors, next-calendar-week responses, and all own-history controls in both panels. Only after alignment and warm-up, keep origins on or after January 1, 2000 and responses on or before December 31, 2024. Do not discard weeks before creating the response shift. This common mask holds the forecast sample fixed across every target and policy, but conditions this retrospective sample on response availability; record the resulting exclusions.

For the committed snapshot, an independent data-only audit gives 1,290 retained pairs. Origins run from January 7, 2000 through December 20, 2024; responses run from January 14, 2000 through December 27, 2024. Thirteen origins, September 7 through November 30, 2001, are excluded by the common response/history requirements. These counts are reproducibility checks, rather than choices made from forecast performance.

## Fixed policy family

There are exactly 18 distinct policies. Each policy forecasts each of the six targets. The measurement set `M` is `S` or all 48 industries; `O` is the target only, `S`, or all 48 as listed below.

| Family | Measurement sets | Outcome sets and restriction | Policy count |
| --- | --- | --- | --- |
| Own-history regression | None | Target only; intercept plus own current/four-/twelve-week controls | 1 |
| Persistence | None | Target only; forecast current `q` | 1 |
| Direct ridge | S, all 48 | Target only | 2 |
| Direct elastic net | S, all 48 | Target only | 2 |
| Target-supervised PLS | S, all 48 | Target only; two components | 2 |
| PCA with separate slopes | S, all 48 | Target only; two components | 2 |
| PCA with pooled slopes | S, all 48 | S or all 48 | 4 |
| PCA with partial pooling | S, all 48 | S or all 48 | 4 |

Policy IDs have the form `<method>__M-<S|all|none>__O-<target|S|all>`. Methods are `local_history`, `persistence`, `ridge`, `elasticnet`, `pls`, `factor_separate`, `factor_pooled`, and `factor_partial`. For example, `factor_partial__M-all__O-S` measures the two PCs with all 48 industries and partially pools slopes across the six named outcomes.

There are no separate-slope policies with larger outcome sets: adding unrelated outcome regressions changes neither the target's separate fit nor its predictions, so those duplicate cells are omitted. Fix the PC count at two; there is no PC-count search. Fit column scaling, PCA, and score scaling on the relevant training segment only. Hold the exact fitted measurement representation fixed across outcome panels and pooling restrictions at a given fitting cutoff.

All regressions retain an unpenalized intercept and the same three target own-history controls. Pooled and partially pooled factor models retain an industry-specific intercept and own-history slopes for every included outcome; only factor slopes are shared. For partial pooling, the objective is the mean squared residual over dates and outcome industries plus `lambda` times the mean squared deviation of each industry's factor slope vector from their mean. Normalize both terms so adding outcome donors does not silently change the penalty's scale. Evaluate forecasts using realized target error, not this penalized multi-outcome objective.

Direct ridge, elastic net, and PLS use the same current measurement predictors as their factor counterpart. Partial out the target intercept and own-history controls with training-only projections, fit the predictor model on the resulting training residuals, and recover predictions with the fitted nuisance component. Apply the historical training projections to validation/test inputs. Use no oracle factors, oracle slopes, target-only tuning from future dates, or outcome-donor validation loss.

## Historical tuning and refits

Index retained aligned pairs starting at zero. Use the first 260 pairs as the initial outer history. The first forecast has index 260. Each scheduled refit uses an expanding history; refit anchors are exactly

`260, 273, 286, ...`.

Each fitted model forecasts at most the following 13 retained pairs. The schedule is indexed by retained pairs, not elapsed calendar weeks, and is never restarted at the development/final boundary. With this snapshot, the first forecast origin is April 1, 2005 and its response is April 8, 2005. A history of 260 consecutive one-week pairs needs at least 261 observed weekly feature dates before allowing for feature warm-up. Missing-week gaps can lengthen its calendar span further.

At refit anchor `a`:

1. Outer history is pairs `[0:a)`. Every historical response must be no later than the refit origin date.
2. Inner training is `[0:a-52)` and validation is `[a-52:a)`.
3. Fit every candidate's transformations, nuisance projections, and coefficients on inner training only. Keep that fit fixed over the 52 validation pairs.
4. Select each target/policy's penalty by its historical target validation MSE. For equal validation losses, use the first penalty in the fixed ascending grid.
5. Refit the selected full pipeline on `[0:a)` and forecast the block `[a:min(a+13,n))`.

The declared grids are ridge penalties `(0.01, 0.1, 1, 10)`, elastic-net penalties `(0.001, 0.01, 0.1)` with `l1_ratio = 0.5`, and partial-pooling penalties `(0.01, 0.1, 1, 10, 100)`. The pilot's elastic-net solver uses `tol = 1e-10` and `max_iter = 100000` for reproducible convergence of that same objective. Persistence, own-history OLS, pooled/separate two-PC regression, and two-component PLS have no searched hyperparameter. Record every selected penalty, validation loss, refit anchor, and last training response date. Training-only transformations are refitted when the model is refitted.

## Development freeze and terminal evaluation

Development forecasts have response dates no later than December 31, 2021. Terminal forecasts have response dates from January 1, 2022 through December 31, 2024. These are response-date boundaries: the first terminal origin can lie in 2021. For this snapshot there are 874 development forecast dates and 156 terminal forecast dates after the 260-pair initial history.

The runner must first execute a development-only stage. For each target `j` and policy `p`, calculate development MSE over identical dates and form

`R[j,p] = MSE[j,p] / MSE[j,local_history]`.

The primary development score is the arithmetic mean of the six value-weighted target ratios, giving each target equal weight. It is not a pooled error across targets or a ratio of pooled MSEs. Select one global policy by the smallest score, with a lexicographic `policy_id` tie-break. Also record the winner restricted to factor policies as a descriptive comparison; it does not replace the global selection. Freeze the selected IDs, all candidate scores, exact protocol/configuration/code fingerprints, data fingerprints, and tuning rule in a written manifest before terminal forecasts are scored. A final-stage command must verify this manifest rather than silently select a new winner. Do not use equal-weighted development or terminal performance to choose the primary policy.

All 18 policies are reported on the terminal period, including unfavorable cells and the development-selected global/factor policies. Within-policy tuning follows the frozen historical rule throughout: already-realized terminal outcomes may enter a later scheduled refit's historical validation/training data. This is an adaptive forecast rule fixed in advance, not an assertion that fitted parameters never update. Terminal outcomes cannot redesign the policy family, penalty grids, donor sets, scoring rule, or selected global policy.

The first terminal pair has index 1,134: origin December 31, 2021, response January 7, 2022. Its scheduled refit anchor is index 1,131, origin December 10, 2021, whose last fitted historical response is December 10, 2021. That block begins with the December 17 response. The terminal stage must replay the same anchor-1,131 fit and historical penalty selection for the remaining block; it must not introduce a new fit at index 1,134. The next refit remains at index 1,144. This boundary replay is a required timing audit.

## Losses, aggregation, and declared comparisons

The sole primary loss is realized squared error of next-week log variance: `(actual q - forecast q)^2`. Its date mean is target MSE. Include forecast mean error in that MSE; do not center prediction errors or substitute residual variance, training loss, donor-averaged loss, the partial-pooling objective, variance-scale error, or QLIKE. Report target-level MSE, target-level MSE ratios to own-history regression, their equal-target mean, and paired date-level losses. Use the same dates for every paired comparison and keep value/equal-weighted results separate.

Prescribed mechanism comparisons are:

- **Measurement breadth:** `factor_separate__M-all__O-target` versus `factor_separate__M-S__O-target`, holding target-only coefficient estimation and PC count fixed.
- **Coefficient pooling:** for each fixed measurement set and each outcome set S/all, compare pooled and partial policies with the separate target-only policy using that same measurement representation.
- **Broad measurement with narrower outcome sharing:** compare `factor_pooled__M-all__O-S` and `factor_partial__M-all__O-S` with their respective `O-all` policies, then compare the narrower policies with `M-S, O-S` policies.
- **Factor restriction versus direct prediction:** compare each measurement set's factor policies with its same-information ridge, elastic-net, and PLS policies, alongside own-history regression and persistence.
- **Frozen selection:** report the development-selected global policy and descriptive factor winner on the terminal period, without replacing them with the best terminal cell.

These comparisons describe fixed choices; they do not demonstrate the value of a learned donor-ranking or donor-membership rule. Industry-specific results matter, including disagreement across the six targets. Do not select a subset of favorable targets, change target weights, or claim that the best among 18 terminal cells is an untouched single-policy test.

An optional exploratory uncertainty summary may resample 13-week date blocks jointly across all six targets and all policies, using 2,000 bootstrap replicates and a recorded seed. Resample paired losses together so common shocks and policy dependence are preserved; do not resample industry-week rows independently. Document the exact block construction and finite-sample convention. These intervals are exploratory and are not multiplicity-adjusted confirmatory claims. Equal-weighted results and bootstrap replicates do not increase the count of independent economic experiments.

## Required audit artifacts

Save forecast-level origin/response dates, target and weighting, policy ID, actual outcome, forecast, squared loss, selected penalty, scheduled refit anchor, and training/validation cutoffs. Save development and terminal summaries for every declared cell, the freeze manifest, selection logs, and the paired comparisons. Hash the input return/feature panels and source provenance, configuration, implementation, and output artifacts; record dependency versions and Git state. Reproduction should either verify the same artifacts or write a new output directory, never overwrite a frozen run silently.

Before interpreting results, check the 18-policy inventory and S membership; shared complete-case dates and equal target/date weights; exact next-calendar-week response alignment across gaps; training-only transformations and target validation; unchanged refit schedule through the terminal boundary; winner frozen before terminal scoring; and output/input fingerprint consistency. Software smoke checks use synthetic inputs and are not additional empirical experiments. No trading result or substantive forecast finding is asserted by this protocol.
