# Experiment 4: Full-panel and two-PC regression with and without ridge

Design recorded November 23, 2026, before computing Experiment 4 forecasts. The question is whether restricting the cross-industry predictors to two PCs improves forecasts at a given penalty rule, and whether shrinking the retained or own-history coefficients adds value. [Executable settings](../../configs/experiment_04.toml).

## Data and chronology

Use the same French 48-industry snapshot, six targets, weekly log variance proxy, own-history features and complete-case calendar as Experiment 3. Evaluate the same 718 earlier-seen and 87 later-seen dates, with value weighting primary and equal weighting as robustness. Both periods have informed the project. All comparisons are descriptive and out of sample in the chronological forecast sense. The calibration and power study stays deferred. This experiment produces point estimates of forecast accuracy.

Use supervised histories of 52, 104, 260 and 520 retained forecast pairs, plus an expanding control. The refit grid is `572 + 13k` and continues across the period boundary. At a refit index `a`, use the preceding 52 pairs for validation. Each validation fit uses the declared history ending immediately before that validation segment. Refit the chosen procedure using the declared history ending before `a` and make forecasts for the next up-to-13 origins. Every transformation, projection, and coefficient fit uses only its respective training window. Keep PCA history matched to the coefficient history. At an origin $t$, the inputs are the current-week panel and the target's 1-, 4-, and 12-week own-history controls through $t$. The outcome is the same proxy for the next calendar week.

## Primary two-by-two comparison

Fit an industry-column scaler on the raw current-week log-proxy panel. Use that same standardized panel for the full regressions and the two-PC score directions. For each target, fit training-only projections of the standardized predictors and the outcome on the intercept and its three own-history controls. Remove the target's redundant panel column from the full residualized regression. Project the standardized panel onto the top two full-SVD directions for the PC regressions and use the corresponding PC residuals after projecting on the controls. Retain the native PC scale. Ridge then uses a common penalty geometry in the full standardized industry coordinates and the orthonormal two-PC subspace. Apply the fitted transformations to new rows and add the predicted residual to the own-history forecast.

| Panel predictors in a target-only fit | Unpenalized OLS | Ridge |
| --- | --- | --- |
| Full standardized panel, net of own history | `panel_ols` | `panel_ridge` |
| First two PC scores, net of own history | `pc_ols` | `pc_ridge` |

Ridge minimizes mean squared residual plus $\lambda$ times the sum of squared slopes on the extra predictors. The intercept and own-history slopes are free of that penalty. The declared candidate grid includes zero so tuning can retain OLS. At 52 pairs, a full-rank panel regression has just one residual degree of freedom after estimating an intercept, three own-history slopes and 47 distinct current panel slopes. Record the numerical rank, condition number and residual degrees of freedom of the full fit.

## Additional comparisons

- `own_ols`, `own_ridge` and `own_elasticnet` use the same three $z_{it}$ predictors and the target's historical outcomes. Standardize the three inputs on the fitting window for the penalized fits. Leave the intercept free. Use a fixed 0.5 elastic-net mix in the scikit-learn normalized objective and allow zero to recover OLS.
- `own_ridge_plus_pcs` adds the unpenalized two-PC correction to the own-history ridge forecast. Use the exact own-history ridge penalty choice and project the PC scores on the intercept and own history before fitting their correction. This tests the contribution of the panel beyond the regularized own-history forecast without letting the PCs substitute for penalized own-history slopes.
- `pc_common` shares the two PC slopes across all 48 historical outcomes with separate intercepts and own-history slopes. Compare it with `pc_ols` using the same fitted PC directions and history to assess the contribution of outcome sharing.
- `panel_ridge_legacy` keeps the earlier direct-ridge scaling and positive penalty grid as a reference. It standardizes each panel column after residualizing it against own history. This reference links Experiment 4 to Experiment 2. The primary `panel_ridge` instead uses the common standardized original panel scale to match the geometry of `pc_ridge`.

For each tuned procedure, choose the penalty separately by target, history and refit on historical validation MSE, breaking exact ties toward the smallest penalty. Retain the complete candidate scores and selected penalties. Every procedure generates a forecast for every declared target, date, weighting and history.

## Scoring and interpretation

Save forecasts and realized losses. Report the equal-target mean of target-specific MSE ratios to matching own-history OLS, as well as absolute mean target MSE. Each paired contrast uses the named reference's MSE denominator separately for each target. The primary contrasts compare PC versus full panel within each column of the two-by-two, and ridge versus OLS within each row. Also report each own-history shrinkage contrast, the incremental PC correction over own-history ridge, common versus separate slopes, and the effect of the legacy direct-ridge scaling. Retain every history and both weightings. Neither a new winner selection nor significance testing is part of this experiment.
