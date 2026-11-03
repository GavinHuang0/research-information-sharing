---
title: "Research progress: factor measurement and forecast sharing"
date: "November 3, 2026"
---

## Research question and initial plan

Industries can help measure common conditions or estimate how those conditions predict a target's future risk. Let $M$ denote measurement donors and $O$ coefficient-sharing donors. A useful measurement industry may have a different predictive relationship from the target. We ask when assigning these roles separately improves forecasts.

We hypothesize that informative measurement expansion helps at fixed dimension, while coefficient sharing helps with limited histories and similar slopes. Heterogeneity, correlated noise, or instability can offset those gains. Principal-component forecasting [1] and panel-composition evidence [2] motivate the design. A linear factor forecast restricts the predictor space: its possible finite-sample benefit balances reduced estimation variance against discarded predictive directions. It cannot improve the unrestricted population optimum with identical information.

## Completed foundation and first two experiments

We archived the French 48-industry daily returns, both weightings, downloads, labels, missingness, and hashes. Weekly features are $Q_{jt}=\sum_d r_{jd}^2$ and $v_{jt}=\log(Q_{jt}+10^{-8})$, requiring at least three daily returns. These are daily-return variation proxies, not intraday realized variance. Own controls are current $v$ and complete trailing four-/twelve-week means of weekly logs; the response is next calendar week's $v$.

Experiment 1 fixed Food, Mach, Banks, Oil, Util, and Hlth as targets and the small donor panel. Eighteen procedures compared measurement/outcome panels, separate/common/partial factor slopes, direct methods, own history, and persistence. Development selection was frozen before the 2022-2024 evaluation. The selected all-48/common-slope factor improved the equal-target MSE ratio by **4.27%** against own history; equal-weighted improvement was **1.66%**, including **2.95% worse Banks MSE**. Broadening measurement supplied most of the gain; common slopes added about 0.15 percentage points. No learned donor rule was established.

Experiment 2 added paired stationary-bootstrap inference [3] and coefficient histories 104/260/520/expanding, with PCA always expanding. In the 87-date 2025-August 2026 period, no history beat own history or ridge after Holm-19 adjustment. L=104 beat elastic net and PLS under the approximate rule (value gains 8.57% and 13.74%, each adjusted $p=0.0019$). No finite history showed an adjusted advantage over expanding coefficients. Exploratory inference on already inspected 2022-2024 losses favored value-weighted factor versus own history only (Holm-four $p=0.0028$).

## Experiment 3: completed November 3

We mapped **K=1-8 factors** against **L=52,78,...,520 coefficient pairs**, plus expanding-coefficient controls, for separate, common, and partially pooled slopes. Part A fitted PCA, its scalers, and coefficients on the same recent L rows. Part B repeated the grid with expanding PCA and identical coefficient windows. Measurement was all 48 industries; common/partial outcome sharing used all 48. Intercepts and own-history slopes stayed industry-specific. Partial-pooling penalties used target-specific historical validation only.

All cells shared the same 718 earlier dates through 2024 and 87 later dates through August 2026. Both periods were already inspected, so this is exploratory. There were 936 distinct factor configurations and 20 own-history references per weighting/period. The 9.23 million saved forecasts passed full window/loss/tuning audits; overlapping Experiment 2 forecasts and independent original-estimator checks agreed within numerical precision. All 118 implementation tests passed.

Each cell received a paired-bootstrap marginal interval from 9,999 draws, resampling complete date vectors in stationary blocks across targets, configurations, and weightings. Only 30 fixed later-period anchors received jointly Holm-adjusted p-values. **None passed the primary block-13 rule in either weighting.** Blocks 6/26 were sensitivities; two equal-weighted block-26 flags did not replace the primary result. Calibration and power studies were not run.

The table shows later value-weighted common-slope gains versus matching-history own regression at the fixed K=2 anchors:

| Coefficient pairs | Part A: matched PCA | Part B: expanding PCA |
| --- | ---: | ---: |
| 104 | 3.53% | 3.97% |
| 260 | -2.00% | -1.75% |
| 520 | -0.75% | -0.41% |

Expanding coefficients gave a shared common-slope gain of 1.23%, nominal interval [-1.12%, 4.16%], adjusted $p=1$. A larger gain against a weaker short-history baseline does not imply lower factor MSE. Gains did not decline monotonically with L; earlier-period improvements were much more widespread than later-period improvements.

High K was particularly costly with very short histories and separate slopes. At the declared L=52/K=8 corner, later value-weighted matched-PCA gains were -11.24% separate, +1.37% common, and -0.75% partial. Sharing cushioned deterioration, but partial pooling did not uniformly beat common slopes. Expanding PCA was not uniformly better across the grid. These descriptive patterns do not identify true factor dimension, causal slope heterogeneity, or a winning forecasting rule. Every unfavorable target remains included.

## Inference limits and pending work

**Bootstrap calibration remains unresolved.** The inherited 100-replication diagnostic rejected a nominal 5% null 11% of the time at 87 dates. Nominal 95% coverage was 90% at 87 dates and 81% at 156. Holm cannot repair marginal miscalibration; p-values remain approximate and intervals marginal, not simultaneous surface bands. Numerical audits verify computations, not coverage or full repeated-training validity. The short later period, dependence, nested models, fixed six targets, and source revisions constrain claims.

Calibration and power studies remain **deferred and pending**, as requested. Controlled simulations of measurement noise and slope heterogeneity, learned donor selection, adaptive dimension/history policies, and trading costs remain future work. Any empirical confirmation requires a newly designated uninspected period or market.

Detailed protocols, all targets/cells, intervals, sensitivities, graphs, and audited records are in [Experiment 1](../experiments/01-fixed-s6-pilot/README.md), [Experiment 2](../experiments/02-bootstrap-history/README.md), and [Experiment 3](../experiments/03-pca-history-surface/README.md). The original proposal remains archived separately.

## Selected references

1. Stock and Watson (2002), *Forecasting Using Principal Components from a Large Number of Predictors*. [DOI](https://doi.org/10.1198/016214502388618960).
2. Boivin and Ng (2006), *Are More Data Always Better for Factor Analysis?* [DOI](https://doi.org/10.1016/j.jeconom.2005.01.027).
3. Politis and Romano (1994), *The Stationary Bootstrap*. [DOI](https://doi.org/10.1080/01621459.1994.10476870).
