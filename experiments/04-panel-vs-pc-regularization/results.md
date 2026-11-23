# Experiment 4 results

Completed November 23, 2026. All ten procedures used the same evaluation dates and the same five matched training histories. The 718 earlier and 87 later dates had already informed the project. These are descriptive comparisons of chronological forecasts. Calibration and power remain deferred.

## Full panel versus two PCs

Each entry is a percent reduction in MSE relative to the reference named in its column, calculated separately for each target and averaged across the six targets. Positive favors the first method. Here $L$ counts retained training pairs.

| Value-weighted period | $L$ | Two-PC OLS over panel OLS | Two-PC ridge over panel ridge | Panel ridge over panel OLS | Two-PC ridge over two-PC OLS |
| --- | ---: | ---: | ---: | ---: | ---: |
| Earlier | 52 | 99.16 | 2.58 | 99.16 | 2.19 |
| Earlier | 104 | 49.49 | -0.24 | 49.70 | 0.16 |
| Earlier | 260 | 20.11 | 1.85 | 18.60 | 0.00 |
| Earlier | 520 | 10.04 | 1.51 | 8.25 | -0.44 |
| Earlier | Expanding | 4.19 | 1.11 | 2.58 | -0.54 |
| Later | 52 | 99.04 | -0.88 | 99.04 | 0.23 |
| Later | 104 | 50.56 | 2.38 | 49.23 | 0.04 |
| Later | 260 | 19.83 | 1.39 | 20.58 | 2.27 |
| Later | 520 | 5.74 | 1.32 | 7.12 | 2.67 |
| Later | Expanding | 2.59 | 1.47 | 2.37 | 1.25 |

Two-PC OLS and full-panel ridge each improved on full-panel OLS in all 20 combinations of period, portfolio weighting and history. The full residual panel had rank 47 in every fit. At $L=52$, it had only one residual degree of freedom after the intercept and three own-history controls. Its largest condition number was about 6,588 at $L=52$, versus 34 at $L=104$. Later value-weighted mean target MSE at $L=52$ was 94.365 for full-panel OLS, 0.786 for full-panel ridge and 0.792 for own-history OLS.

Two-PC ridge improved on full-panel ridge in 16 of 20 settings. The four unfavorable cells were earlier value-weighted $L=104$, earlier equal-weighted expanding, and later $L=52$ under both portfolio weightings. Within the two-PC model, ridge improved on OLS in 13 of 20 settings. In the later value-weighted period it improved at all five histories, by 0.04% at $L=104$ and 2.67% at $L=520$. The $L=520$ improvement brought two-PC ridge to 0.67% below matching own-history OLS, from 2.22% above it with unpenalized PC slopes. At $L=260$ the two-PC ridge forecast still had higher MSE than same-history own-history OLS.

## Own-history shrinkage and pooling

Own-history ridge improved on own-history OLS in 8 of 20 settings. Own-history elastic net did so in 15 of 20. Adding the two-PC correction to own-history ridge helped in 14 of 20 settings. At later value-weighted $L=104$, own-history ridge lowered MSE by 0.49% relative to own-history OLS, and the PC correction lowered it by a further 3.00% relative to own-history ridge. At later value-weighted $L=260$ and $L=520$, the same correction raised MSE by 3.61% and 2.56%. Common factor slopes improved on separate PC OLS in 18 of 20 settings, with gains ranging from 0.10% to 4.14% in those favorable cells. The same dates and industries recur across settings.

## Audit and records

The independent audit checked 483,000 forecasts, 119,040 candidate validation scores and 620 pairs of fitting windows. The matched own-history OLS, separate PC OLS and common PC OLS forecasts reproduce 144,900 saved Experiment 3 forecasts. The legacy direct-ridge fit reproduces 38,640 Experiment 2 forecasts and their selected penalties. The maximum forecast difference in those comparisons was $6.13\times 10^{-14}$ in log-proxy units. Where tuning chose a zero penalty, forecasts matched the corresponding OLS forecasts exactly.

- [All signed paired comparisons](../../results/experiment-04-2026-11-23/reports/contrasts.csv)
- [All methods and absolute mean MSEs](../../results/experiment-04-2026-11-23/reports/summary.csv)
- [All six target-level results](../../results/experiment-04-2026-11-23/reports/target_summary.csv)
- [Audit and rank diagnostics](../../results/experiment-04-2026-11-23/audit.json)
- [Run manifest and source hashes](../../results/experiment-04-2026-11-23/manifest.json)
