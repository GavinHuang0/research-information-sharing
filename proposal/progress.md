---
title: "Research progress: factor measurement and forecast sharing"
date: "October 31, 2026"
---

## Research question

Additional industries can help forecast a target in two distinct ways: measuring common conditions and estimating how those conditions predict its future risk. Let $M$ denote measurement donors and $O$ coefficient-sharing donors. An industry may measure the common state well while having a different forecasting relationship from the target. The question is when assigning these roles separately improves forecasts, rather than assuming one group serves both purposes.

The conditional hypotheses are that informative measurement expansion helps at fixed dimension; coefficient sharing helps most with short histories and similar predictive slopes; and heterogeneous slopes, correlated noise, or instability can offset those gains. Homogeneous panels may offer little reason to separate donor roles. Predictive component selection remains a supporting question; these pilots fix two components to isolate sharing roles. Principal-component forecasting provides the starting point [1]; evidence that panel composition matters motivates testing these conditions [2].

Factors impose a finite-sample restriction: a linear forecast through a low-dimensional factor space remains a restricted linear forecast of the original predictors. Compression cannot improve the unrestricted population optimum with the same information. Its potential benefit is lower estimation variance, balanced against discarded predictive directions. Tuned ridge, elastic net, and supervised dimension reduction are therefore essential comparisons. Economically, better risk forecasts could support volatility targeting, but trading value, turnover, and transaction costs remain future evaluations.

## Completed foundation and Experiment 1

The repository now archives the French 48-industry daily returns in both value- and equal-weighted forms, original downloads, labels, missingness, hashes, and preparation provenance. Weekly features use $Q_{jt}=\sum_d r_{jd}^{2}$ and $v_{jt}=\log(Q_{jt}+10^{-8})$, requiring at least three daily observations. These are close-to-close return-variation proxies, not intraday realized variance. Own controls are current $v$ and complete trailing four- and twelve-week means of weekly logs. The forecast response is next calendar week's $v$.

The first pilot fixed six targets and the small panel as Food, Mach, Banks, Oil, Util, and Hlth. Eighteen distinct policies compared small/all-48 measurement panels, target/six/all-48 outcome panels where applicable, separate/common/partially pooled factor slopes, ridge, elastic net, PLS, own-history regression, and persistence. PCA and PLS dimensions were fixed at two. Pooled models retained industry-specific intercepts and own-history coefficients.

One common complete-case calendar covered all 48 industries and both weightings, after feature warm-up. Within origins from 2000 and responses through 2024, 1,290 pairs remained. An initial 260-pair history, last-52-pair historical validation, and expanding refits every 13 retained origins produced 874 development and 156 final forecast dates. Transformations and penalty choices used historical data only. The refit schedule continued across the response-date boundary in 2022.

## What the pilot shows

Value-weighted development scores selected all-48 measurement with common factor slopes across all 48 outcomes. The procedure and selection rule were frozen before final scoring. Its final equal-target mean MSE ratio to own-history regression was 0.9573: a **4.27% improvement**. Equal-weighted robustness improvement was **1.66%**, including **2.95% worse Banks MSE**. The score averages target-specific MSE ratios, giving each target equal weight; it is not a ratio of pooled MSEs.

| Factor rule | M | O | Final gain |
| --- | --- | --- | ---: |
| Separate | 6 | Target | 1.79% |
| Separate | 48 | Target | 4.12% |
| Common, frozen choice | 48 | 48 | 4.27% |
| Partial, prespecified comparison | 48 | 48 | 4.52% |

Broader measurement supplies most of this comparison's gain. Sharing common slopes adds only about 0.15 percentage points beyond broad measurement with target-specific slopes. Restricting outcome donors to the fixed six did not improve primary aggregate performance. Partial pooling's favorable final point estimate did not replace the development-selected procedure. Broad ridge outperformed the frozen factor policy in the equal-weighted check, weakening a general claim of factor superiority.

Sharing effects differ across targets. At fixed all-48 measurement, Mach's improvement falls from **9.28% with separate slopes to 7.10% with common slopes**; Banks rises from **1.12% to 2.52%**, and Oil from **4.01% to 5.91%**. These contrasts motivate investigating heterogeneity. They do not establish a learned donor selector: membership was fixed throughout. No confidence intervals, significance tests, or p-values have been produced.

## Experiment 2: planned, not run

Part A proposes a joint-date stationary bootstrap [3] of paired forecast losses from the already-seen 2022-2024 period. It will resample whole date vectors across targets and methods to preserve their dependence. This is exploratory uncertainty analysis, not a new untouched test.

Part B will hold the Experiment 1 common-slope factor specification, $M=48$ and $O=48$, fixed while varying coefficient-estimation histories: 104, 260, 520 pairs, or expanding history. Unsupervised PCA will remain expanding and identical across those history comparisons, separating coefficient-history effects from measurement estimation. Own-history, ridge, elastic net, and PLS comparators will use matched coefficient histories. One-sided, null-centered paired-bootstrap p-values and multiple-comparison adjustment are proposed; a factor advantage is a hypothesis, not an assumed result.

Responses from 2025 through August 2026 are proposed as a not-yet-scored final period, to be evaluated only after freezing the procedure. Earlier outcomes have already informed the research. Stationarity assumptions, nested-model comparisons, and the short final period limit inference. Controlled simulations varying measurement noise and slope heterogeneity are still needed before developing theory or claiming mechanisms generalize.

Full executed procedures and interpretations are in [Experiment 1](../experiments/01-fixed-s6-pilot/protocol.md); the [Experiment 2 protocol](../experiments/02-bootstrap-history/protocol.md) records its separate planned design and unrun status.

## Selected references

1. Stock and Watson (2002), *Forecasting Using Principal Components from a Large Number of Predictors*. [DOI](https://doi.org/10.1198/016214502388618960).
2. Boivin and Ng (2006), *Are More Data Always Better for Factor Analysis?* [DOI](https://doi.org/10.1016/j.jeconom.2005.01.027).
3. Politis and Romano (1994), *The Stationary Bootstrap*. [DOI](https://doi.org/10.1080/01621459.1994.10476870).
