---
title: "Research progress: factor measurement and forecast sharing"
date: "November 2, 2026"
---

## Research question and initial plan

Industries can help measure common conditions or estimate how those conditions predict a target's future risk. Let $M$ denote measurement donors and $O$ coefficient-sharing donors. A useful measurement industry may have a different predictive relationship from the target. We ask when assigning these roles separately improves forecasts.

We hypothesize that informative measurement expansion helps at fixed dimension, while sharing helps with limited histories and similar slopes. Heterogeneity, correlated noise, or instability can offset these gains. Principal-component forecasting [1] and panel-composition evidence [2] motivate the design. The first experiments fix two components; predictive dimension choice remains future work.

A linear factor forecast restricts the predictor space. Its possible finite-sample benefit balances reduced estimation variance against discarded predictive directions; it cannot improve the unrestricted population optimum with identical information. Ridge, elastic net, and supervised dimension reduction are essential comparisons. Economic value remains unevaluated.

## Completed data and first experiment

We archived the French 48-industry daily returns, both weightings, source downloads, labels, missingness, and hashes. Weekly features are $Q_{jt}=\sum_d r_{jd}^{2}$ and $v_{jt}=\log(Q_{jt}+10^{-8})$, requiring at least three daily observations. These are daily-return variation proxies, not intraday realized variance. Own controls are current $v$ and complete trailing four-/twelve-week means of weekly logs; the response is next calendar week's $v$.

Experiment 1 fixed Food, Mach, Banks, Oil, Util, and Hlth as targets and the small donor panel. Eighteen policies compared measurement/outcome panels, separate/common/partial factor slopes, direct methods, own history, and persistence. Pooling retained industry-specific intercepts and own-history coefficients. Procedures shared dates, historical validation, and expanding refits every 13 origins.

Selection was frozen before the 156-date 2022-2024 evaluation. The all-48/common-slope factor improved the equal-target MSE ratio by **4.27%** against own history; equal-weighted improvement was **1.66%**, including **2.95% worse Banks MSE**. Separate slopes improved 1.79% with six measurement industries and 4.12% with 48: broader measurement supplied most of the gain, while common slopes added about 0.15 percentage points. Narrower outcome sharing did not improve the primary aggregate; no selective donor rule was established.

## Experiment 2: completed November 1

Part A bootstrapped the inspected 2022-2024 losses [3]. Only value-weighted factor versus own history passed the exploratory Holm-four rule ($p=0.0028$); no direct-method or equal-weighted comparison did.

Part B fixed the factor specification and varied supervised histories: 104, 260, 520 pairs, or expanding. PCA stayed expanding; supervised fits used the declared history. Audited development outputs were committed before scoring 87 dates in January 2025-August 2026. Overlapping expanding-history forecasts reproduced Experiment 1 exactly; refits continued across the boundary.

Both parts used 9,999 paired stationary-bootstrap draws, primary expected block 13 and sensitivities 6/26. Resampling whole date vectors preserved cross-target/method dependence. Ratio numerators and denominators were recomputed per draw without model refitting. Part B applied Holm to 16 matched-reference and three history tests; equal weighting formed a separate robustness family. No new winner was selected.

| Coefficient history | Factor gain vs own | Gain vs ridge | Mean factor MSE |
| --- | ---: | ---: | ---: |
| 104 pairs | 3.97% | 2.80% | 0.74759 |
| 260 pairs | -1.75% | -0.28% | 0.72445 |
| 520 pairs | -0.41% | -0.94% | 0.72552 |
| Expanding | 1.23% | 1.96% | 0.71805 |

The table reports value-weighted gains averaging target-specific MSE ratios. **No history beat own history or ridge after Holm-19 adjustment.** L=104 beat elastic net and PLS under the approximate tests (8.57% and 13.74%, each adjusted $p=0.0019$); this comparison pattern persisted across block settings and both weightings.

No finite-history factor showed an adjusted advantage over expanding. L=104's larger gain against own history reflects a weaker baseline, not lower factor MSE. Expanding Banks and Mach worsened 2.39% and 3.02%. Pooling's benefit over separate slopes did not uniformly increase with shorter histories. Fixed $M=O=48$ comparisons do not identify separate measurement/outcome roles.

## Experiment 3: planned, not run

We will map factor counts 1-8 against coefficient windows 52-520 pairs in increments of 26, comparing common, separate, and partially pooled slopes. Part A will fit PCA on the same rows as coefficients; Part B will repeat with expanding PCA and identical coefficient windows. Targets, donor panels, dates, and historical penalty validation remain fixed. Graphs will show relative gains, absolute MSE, and paired PCA-history changes. Saved-loss bootstrapping includes partial pooling: full-grid intervals remain approximate and marginal, with a smaller 30-comparison anchor family for adjusted p-values. No Experiment 3 forecasts have been run.

## Inference limits and deferred work

**Bootstrap calibration remains unresolved.** A 100-replication synthetic diagnostic rejected a nominal 5% null 11% of the time at 87 dates. Nominal 95% interval coverage was 90% at 87 dates and 81% at 156. Holm cannot repair marginal miscalibration; p-values remain approximate and intervals marginal. Implementation tests and numerical audits do not validate coverage. The short period, nested models, expanding estimation, fixed six targets, and source revisions also constrain claims.

Calibration and power studies are **deferred, pending work**, outside Experiment 3. They remain necessary before stronger statistical claims. Controlled simulations of measurement noise and slope heterogeneity, learned donor selection, and trading costs remain future work. Empirical confirmation needs a newly designated period or market; 2022-2026 is already inspected.

Detailed records are in [Experiment 1](../experiments/01-fixed-s6-pilot/README.md), [Experiment 2](../experiments/02-bootstrap-history/README.md), and the [Experiment 3 plan](../experiments/03-pca-history-surface/protocol.md). The original proposal remains archived separately.

## Selected references

1. Stock and Watson (2002), *Forecasting Using Principal Components from a Large Number of Predictors*. [DOI](https://doi.org/10.1198/016214502388618960).
2. Boivin and Ng (2006), *Are More Data Always Better for Factor Analysis?* [DOI](https://doi.org/10.1016/j.jeconom.2005.01.027).
3. Politis and Romano (1994), *The Stationary Bootstrap*. [DOI](https://doi.org/10.1080/01621459.1994.10476870).
