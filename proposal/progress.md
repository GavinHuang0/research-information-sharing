---
title: "Research progress: factor measurement and forecast sharing"
date: "November 1, 2026"
---

## Research question and initial plan

Additional industries can help forecast a target by measuring common conditions or by estimating how those conditions predict its future risk. Let $M$ denote measurement donors and $O$ coefficient-sharing donors. An industry may measure the common state well while having a different predictive relationship from the target. We ask when assigning these roles separately improves forecasts.

We hypothesize that informative measurement expansion helps at fixed dimension, while sharing helps with limited histories and similar slopes. Heterogeneity, correlated noise, or instability can offset these gains. Principal-component forecasting [1] and panel-composition evidence [2] motivate the design. The first experiments fix two components; predictive dimension choice remains future work.

A linear factor forecast restricts the predictor space. Its possible finite-sample benefit balances reduced estimation variance against discarded predictive directions; it cannot improve the unrestricted population optimum with identical information. Ridge, elastic net, and supervised dimension reduction are essential comparisons. Economic value remains unevaluated.

## Completed data and first experiment

We archived the French 48-industry daily returns, both weightings, source downloads, labels, missingness, and hashes. Weekly features are $Q_{jt}=\sum_d r_{jd}^{2}$ and $v_{jt}=\log(Q_{jt}+10^{-8})$, requiring at least three daily observations. These are daily-return variation proxies, not intraday realized variance. Own controls are current $v$ and complete trailing four-/twelve-week means of weekly logs; the response is next calendar week's $v$.

Experiment 1 fixed Food, Mach, Banks, Oil, Util, and Hlth as targets and the small donor panel. Eighteen policies compared measurement/outcome panels, separate/common/partial factor slopes, direct methods, own history, and persistence. Pooling retained industry-specific intercepts and own-history coefficients. Procedures shared dates, historical validation, and expanding refits every 13 origins.

Development selection was frozen before the 156-date 2022-2024 evaluation. The selected all-48/common-slope factor improved the equal-target mean MSE ratio by **4.27%** against own history; equal-weighted improvement was **1.66%**, including **2.95% worse Banks MSE**. Separate factor slopes improved 1.79% with six measurement industries and 4.12% with 48, so broader measurement supplied most of this pilot's gain. Common outcome slopes added about 0.15 percentage points. Narrower outcome sharing did not improve the primary aggregate. These findings did not establish a selective donor rule.

## Experiment 2: completed November 1

Part A applied a joint-date stationary bootstrap [3] to the already inspected 2022-2024 losses. Value-weighted factor-versus-own-history improvement was 4.27%, nominal basic interval [1.71%, 6.92%], raw one-sided $p=0.0007$, Holm-four $p=0.0028$. No ridge/elastic-net/PLS comparison survived adjustment; no equal-weighted comparison did. This is exploratory inference on a seen period.

Part B fixed the selected factor specification and varied supervised histories: 104, 260, 520 pairs, or expanding. PCA remained expanding across factor history rules; supervised coefficients, direct scalers/nuisance fits, and PLS used the declared history. Audited development outputs were committed before scoring 87 dates from January 2025-August 2026. Expanding-history forecasts exactly reproduced Experiment 1 on overlapping dates. Refits continued across the final boundary.

Both parts used 9,999 paired stationary-bootstrap draws, primary expected block 13 and sensitivities 6/26. Resampling whole date vectors preserved cross-target/method dependence. Ratio numerators and denominators were recomputed per draw without model refitting. Part B applied Holm to 16 matched-reference and three history tests; equal weighting formed a separate robustness family. No new winner was selected.

| Coefficient history | Factor gain vs own | Gain vs ridge | Mean factor MSE |
| --- | ---: | ---: | ---: |
| 104 pairs | 3.97% | 2.80% | 0.74759 |
| 260 pairs | -1.75% | -0.28% | 0.72445 |
| 520 pairs | -0.41% | -0.94% | 0.72552 |
| Expanding | 1.23% | 1.96% | 0.71805 |

The table reports value-weighted final results; gains average target-specific candidate/reference MSE ratios. **No history beat own history or ridge after primary Holm-19 adjustment.** All own-history adjusted p-values were 1; ridge values were 1, 1, 1, and 0.7664. Value-weighted L=104 beat elastic net and PLS under the planned approximate tests (gains 8.57% and 13.74%, each adjusted $p=0.0019$). That comparison pattern persisted across block settings and both weightings. Other robustness rejections depended on block length.

No finite-history factor beat expanding after adjustment. Value-weighted direct gains versus expanding were -4.09%, -1.05%, and -1.08%, each adjusted $p=1$. The larger L=104 gain against own history reflects a weaker matched baseline, not lower absolute factor MSE. Expanding Banks and Mach worsened 2.39% and 3.02% against own history. At fixed all-48 measurement, descriptive pooled-versus-separate comparisons showed no uniform short-history pooling benefit. The primary tests fix $M=O=48$ and do not identify separate measurement/outcome roles.

## Inference limits and next steps

**Bootstrap calibration remains unresolved.** A pre-execution stationary synthetic loss diagnostic with 100 replications rejected a nominal 5% null 11% of the time at 87 dates. Nominal 95% basic-interval coverage was 90% at 87 dates and 81% at 156. These adverse results do not validate nominal coverage or full-pipeline inference. Holm cannot repair marginal miscalibration. Empirical p-values are approximate; intervals are marginal, not simultaneous. Passing 91 implementation tests and independent numerical audits does not remove this statistical limitation. The short final period, nested models, expanding estimation, fixed six targets, and source revisions also constrain claims.

Next, we will assess inference size/coverage under predeclared dependent and heavy-tailed loss processes and full forecasting simulations, before stronger significance claims. Controlled simulations varying measurement noise and slope heterogeneity will then test the central $M/O$ mechanism. Later empirical confirmation needs a newly designated period or market; 2022-2026 is now inspected. Learned donor selection, predictive dimension choice, and trading costs remain future work.

Detailed procedures, all comparisons, unfavorable targets, sensitivities, and audited artifacts are in [Experiment 1](../experiments/01-fixed-s6-pilot/README.md) and [Experiment 2](../experiments/02-bootstrap-history/README.md). The original proposal remains archived separately.

## Selected references

1. Stock and Watson (2002), *Forecasting Using Principal Components from a Large Number of Predictors*. [DOI](https://doi.org/10.1198/016214502388618960).
2. Boivin and Ng (2006), *Are More Data Always Better for Factor Analysis?* [DOI](https://doi.org/10.1016/j.jeconom.2005.01.027).
3. Politis and Romano (1994), *The Stationary Bootstrap*. [DOI](https://doi.org/10.1080/01621459.1994.10476870).
