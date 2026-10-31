# Experiment 1: executed protocol

This is a retrospective account of the experiment executed October 27, 2026, organized October 31, 2026. It does not replace or amend the [executed protocol](../../results/fixed-pilot-2026-10-27/protocol.md), [executed configuration](../../results/fixed-pilot-2026-10-27/config.toml), or [frozen procedure](../../results/fixed-pilot-2026-10-27/frozen_procedure.json). Those archived files and their recorded hashes establish the procedure frozen before final evaluation. See [results.md](results.md) for findings rather than design instructions.

## Question, data, and fixed membership

The experiment separated two possible uses of additional industry data: measuring common predictive signals and estimating their forecasting slopes. It compared fixed panel choices, not a learned donor-selection rule.

Inputs were the committed October 16, 2026 Kenneth R. French 48-industry daily return snapshot, spanning July 1, 1926 through August 31, 2026. Daily percentages had already been converted to decimal returns, with missing sentinels converted to empty cells and no imputation. The [input fingerprints](../../results/fixed-pilot-2026-10-27/metadata.json) identify the precise value-weighted/equal-weighted CSVs and preparation provenance. Value-weighted returns were primary; equal-weighted returns were a robustness check on the same dates, not an independent replication.

The six evaluation targets and the common small panel were fixed as

```
S = (Food, Mach, Banks, Oil, Util, Hlth)
```

The measurement set `M` was S or all 48 industries. The outcome set `O` was the focal target, S, or all 48, depending on the declared policy. Every target belonged to its measurement and outcome panels where applicable. S retained the displayed name order; all-industry panels retained the provider's original column order. Membership did not depend on target performance, random permutations, panel prefixes, or refit date.

## Weekly construction and common calendar

For industry `j` and Friday-ending calendar week `t`:

```
Q[j,t] = sum(r[j,d]^2 for previous Friday < d <= current Friday)
q[j,t] = log(Q[j,t] + 1e-8)
h[j,t] = (q[j,t], mean(q[j,t-3], ..., q[j,t]),
                    mean(q[j,t-11], ..., q[j,t]))
response[j,t] = q[j,t+1]
```

The weekly grid was `W-FRI`, right-closed and right-labeled. `Q` required at least three observed daily decimal returns for each industry/week. Insufficient-observation weeks remained missing; absent weeks remained on the calendar, with no filling or interpolation. The sum was not divided by the observed day count or annualized. Historical Saturday observations were included when present. `sqrt(Q)` is a weekly volatility proxy, but the experiment predicted **log variance `q`**, not volatility or signed returns. `Q` is a close-to-close return-variation proxy, not intraday realized variance or observed conditional variance.

Both history means were arithmetic means of weekly **logs**, including the current week, and required complete four- or twelve-week windows. They were not logs of mean variance. The own current-week control overlapped the target's current `q` measurement column; it was not an additional one-week lag. No macro variables or signed raw returns entered the predictors.

Features, histories, and the exactly seven-day next-calendar-week response were constructed using the full weekly history before selecting the experiment dates. A complete-case mask required finite current `q`, next-week `q`, and all three own-history controls for **every one of the 48 industries**. Eligible origin/response pairs were then intersected across both return weightings. Only afterward were origins restricted to January 1, 2000 onward and responses to December 31, 2024 or earlier. Missing weeks were never compressed before forming lags or the response shift.

The resulting [calendar audit](../../results/fixed-pilot-2026-10-27/calendar.json) records **1,290 pairs**: origins January 7, 2000 through December 20, 2024, and responses January 14, 2000 through December 27, 2024. Thirteen potential origins, September 7 through November 30, 2001, were excluded by shared response/history requirements. Every policy, target, and weighting used the same retained pairs. This controls sample differences across comparisons, while making the retrospective sample conditional on later response availability.

## The 18 policies actually evaluated

Each policy forecast every target. Both PCA and supervised PLS used exactly two components, with no component-count search.

| Family | M | O | Restriction | Number |
| --- | --- | --- | --- | ---: |
| Own-history OLS | None | Target | Intercept plus target's three `h` controls | 1 |
| Persistence | None | Target | Forecast current `q` | 1 |
| Direct ridge | S / all 48 | Target | Regularized direct predictor plus unpenalized own controls | 2 |
| Direct elastic net | S / all 48 | Target | Regularized direct predictor plus unpenalized own controls | 2 |
| PLS | S / all 48 | Target | Two supervised components plus own controls | 2 |
| PCA, separate slopes | S / all 48 | Target | Two PCs, target-specific slopes | 2 |
| PCA, common slopes | S / all 48 | S / all 48 | Common factor slopes, industry-specific nuisance coefficients | 4 |
| PCA, partial pooling | S / all 48 | S / all 48 | Factor slopes shrunk toward their cross-outcome mean | 4 |

The [policy inventory](../../results/fixed-pilot-2026-10-27/policies.json) supplies every exact ID, in the form `<method>__M-<S|all|none>__O-<target|S|all>`. Larger O sets were omitted for separate regression because other industries' independent regressions cannot change the focal target's fit. There were no oracle, random-panel, learned-membership, adaptive-factor-design, or factor-lasso policies in this experiment.

## Fitted transformations and coefficient sharing

At each fitting cutoff, PCA first standardized each measurement column using training means and population standard deviations (`StandardScaler`, `ddof=0`), fit two components with full SVD, then standardized the training component scores by the same scaling convention. The fitted scaling/PCA/score scaling was applied unchanged to later observations. A cached representation for a given weighting, cutoff, inner/outer fitting segment, and measurement membership was reused across targets, outcome panels, and sharing restrictions. Hence changing O did not also change the learned measurement representation.

For included outcome industry `j`, factor regression had the form

```
q[j,t+1] = a[j] + h[j,t]' gamma[j] + z[t]' beta[j] + error[j,t+1]
```

Every industry retained its own unpenalized intercept `a[j]` and own-history coefficients `gamma[j]`. Separate fitting estimated only the focal target's factor slopes. Common fitting imposed the same `beta` across O. Partial pooling minimized

```
(1 / (T*m)) * sum_t sum_j residual[j,t]^2
    + (lambda / m) * sum_j ||beta[j] - mean_beta||^2,
```

where `m = |O|` and `mean_beta` was the mean factor slope over those outcomes. The date/outcome averaging and penalty averaging avoided an implicit change in penalty strength when O grew. Intercepts and own-history slopes were partialled out separately for each industry and were not pooled. Validation and reporting used the focal target's unpenalized forecast error, not this multi-outcome fitting objective.

Ridge, elastic net, and PLS used the same current measurement panel as their factor comparison. Training-only least-squares projections removed the target intercept and own-history controls from both X and the target response. A column was removed from the residual predictor matrix when its training standard deviation was no greater than `1e-10 * max(original_training_std, 1)`; this prevented numerical residue from the duplicated target-current-week control being standardized into a predictor. The fitted training projections were also used for validation/test rows. Predictions added the nuisance component back to the predicted target residual.

Ridge standardized the retained training residual predictors and used scikit-learn `alpha = T * lambda`, equivalent to minimizing training MSE plus `lambda * ||beta||^2`. Elastic net used standardized training residual predictors, `l1_ratio = 0.5`, and scikit-learn's objective `SSE/(2*T) + lambda*0.5*||beta||_1 + lambda*0.5*||beta||^2/2`. Its solver used `tol = 1e-10` and `max_iter = 100000`. PLS used two components with training-only scaling (`PLSRegression(scale=True)`) on the residual predictors/target. No transformation was estimated on the full evaluation sample.

## Historical tuning and anchored refits

Index retained pairs from zero. The first **260 pairs** were initial history, distinct from 260 weekly feature observations. The first forecast was index 260: origin April 1, 2005, response April 8, 2005. Histories expanded and refit anchors were `260, 273, 286, ...`, every **13 retained origins**, not every 13 elapsed weeks.

At anchor `a`, execution was:

1. Keep historical pairs `[0:a)`, with every response no later than the refit origin.
2. Use inner training `[0:a-52)` and the last **52 historical pairs** `[a-52:a)` as validation.
3. Fit every candidate pipeline on inner training and hold it fixed over those validation origins.
4. For each target and policy separately, choose the penalty with the smallest **target validation MSE**. Exact ties use the first declared penalty.
5. Refit the selected pipeline on `[0:a)` and forecast `[a:min(a+13,n))`.

The exact ascending grids were ridge `(0.01, 0.1, 1, 10)`, elastic net `(0.001, 0.01, 0.1)`, and partial pooling `(0.01, 0.1, 1, 10, 100)`. Other policies had no searched penalty. There was no joint tuning of panel membership, component count, or policy using the next block's outcomes. [Development](../../results/fixed-pilot-2026-10-27/development/tuning.jsonl.gz) and [final tuning logs](../../results/fixed-pilot-2026-10-27/final/tuning.jsonl.gz) retain all candidate scores, choices, memberships, and cutoffs.

## Development selection, freeze, and final replay

Development comprised **874 forecast response dates** from April 8, 2005 through December 31, 2021. Final evaluation comprised **156 response dates** from January 7, 2022 through December 27, 2024. Date partitioning used the **response**, so the first final origin was December 31, 2021.

For each target and policy, compute held-out target MSE. The primary development score was

```
R[p] = (1/6) * sum_j MSE[value,j,p] / MSE[value,j,own_history].
```

This gives the six targets equal weight after their own-history normalization; it is not a pooled MSE or a ratio of pooled MSEs. Choose the single policy minimizing this primary value-weighted score, with lexicographic policy ID breaking ties. Also record a factor-family winner descriptively. Neither equal-weighted performance nor final performance selected either identity.

Development ran first. Both winner IDs were `factor_pooled__M-all__O-all`, with development score **0.9656675655**. Their identities, all 18 primary development scores, config/code/dependency/input hashes, and development artifact hashes were saved in the [freeze manifest](../../results/fixed-pilot-2026-10-27/frozen_procedure.json) and committed as `b2161f6` at October 27, 2026 **00:14:47 EDT**. The final execution log begins at **00:14:51.672943 EDT**, after that commit. The [final audit](../../results/fixed-pilot-2026-10-27/final_audit.json) verified this ordering and the unchanged frozen files.

Final execution evaluated all 18 declared policies. It continued the frozen within-policy historical tuning rule: already-realized final-period outcomes could enter a later scheduled fit/validation history. The global selected policy identity, model family, donor memberships, grids, and scoring rule could not change.

The refit schedule was not restarted at the boundary. First final pair **1134** replayed anchor **1131**, origin December 10, 2021, whose last fitted response was December 10, 2021. That block had already begun with the December 17 response; final execution recomputed its same historical fit/selection and predicted only the remaining final rows. The next refit stayed at **1144**. The independent audit confirmed identical anchor-1131 selections across stages.

## Evaluation, audits, and inferential scope

Primary per-date loss was `(actual_next_week_q - forecast_q)^2`; target MSE was its date mean, including any mean forecast error. Fitted errors, residual variances, donor-average errors, penalties, variance-scale losses, and QLIKE were not substitutes. Aggregate reporting used the equal-target mean of MSE ratios above. Percentage improvement was `100 * (1 - R)`, so positive values favored the policy. Log MAE and its analogous ratios were secondary descriptive measures.

There were **188,784 development** and **33,696 final** forecast records, representing 18 policies, six targets, and two weightings on their shared stage calendars. All cells, including unfavorable outcomes, are in the [target table](../../results/fixed-pilot-2026-10-27/reports/target_summary.csv) and [aggregate table](../../results/fixed-pilot-2026-10-27/reports/aggregate_summary.csv). The [development audit](../../results/fixed-pilot-2026-10-27/development_audit.json), [final audit](../../results/fixed-pilot-2026-10-27/final_audit.json), and [validation log](../../results/fixed-pilot-2026-10-27/validation.txt) checked the implementation and saved losses; [artifact hashes](../../results/fixed-pilot-2026-10-27/artifact_manifest.json) identify the completed outputs.

No bootstrap, confidence intervals, significance tests, or multiplicity-adjusted claims were produced. The optional bootstrap described in the original protocol was not executed. These are dependent industries and dates, a fixed six-target set, and a three-year final window in a retrospective revised data snapshot. The experiment does not identify causal effects, demonstrate a learned donor selector, establish a true factor dimension, or evaluate trading/economic utility. Reproduction instructions remain in the [archived run README](../../results/fixed-pilot-2026-10-27/README.md#reproduction) and use a new output directory.
