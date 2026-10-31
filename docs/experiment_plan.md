# First experiments: factor measurement and coefficient sharing

**Executed fixed pilot:** the authoritative first empirical design is [fixed_pilot_protocol.md](fixed_pilot_protocol.md), with [configs/fixed_pilot.toml](../configs/fixed_pilot.toml). It fixes S = {Food, Mach, Banks, Oil, Util, Hlth} as both evaluation targets and the common small panel, uses M in {S, all48} and O in {target, S, all48}, and excludes adaptive donor/factor-count search. The older initializer grids and prefix-panel discussion below describe the broader experimental toolkit, not the fixed pilot's memberships or calendar. The fixed protocol supersedes those starter choices for this run.

This earlier operational plan is retained as a broader research-toolkit reference. The [current experiment index](../experiments/README.md) separates the completed first experiment from the unrun second plan; the [current progress report](../proposal/progress.md) summarizes project status. The [original proposal](../proposal/archive/2026-10-09/proposal.pdf) is preserved separately. Existing Python functionality is identified below; the legacy grids are not the settings for Experiment 2.

## Objective and comparisons

Keep one target asset and its forecast dates fixed. Change two decisions independently:

1. **Measurement panel M:** whose observed predictors estimate the common factor representation?
2. **Outcome panel O:** whose historical outcomes contribute to the target's forecasting coefficients?

The target belongs to both initial nested panels. Membership need not agree: an asset can provide an informative measurement of common conditions while having a forecasting slope unlike the target's. More measurement assets at fixed factor dimension do not inherently create more target coefficients. Deterioration must be traced to the fitted representation, coefficient restrictions, finite-sample selection, or changed coverage.

First compare fixed designs to understand mechanisms; then evaluate a validation-selected policy. Keep factor estimation fixed when comparing coefficient-sharing rules, and keep target-only coefficient estimation fixed when comparing measurement-panel sizes. Compare factor methods with direct regularization using the same predictors and own-history controls.

## Stage 1: controlled, paired simulations

The implemented simulator generates two persistent stationary Gaussian factors, predictor measurements `X[t,j] = loading[j] @ factors[t] + noise[t,j]`, and next-period outcome pairs `Y[t,j] = theta[j] @ factors[t] + innovation[t,j]`. Row t always pairs an origin predictor with its t+1 outcome. Initial measurement assets span both directions. The first forecasting slope is shared; the second varies across assets with the configured heterogeneity. The target is a seeded draw from the same slope distribution, fixed within a scenario as asset count changes.

Generate the maximum panel once per seed and scenario, then slice it into nested prefixes. This preserves target outcomes, shocks, and dates for paired comparisons. Predictor-quality changes leave outcome coefficients unchanged; coefficient-heterogeneity changes leave predictor paths unchanged. Multiple seeds supply independent Monte Carlo replications; different designs within a seed are deliberately dependent.

The initial grids are design choices:

| Parameter | Pipeline check | Exploratory pilot |
| --- | --- | --- |
| Measurement counts | 4, 12 | 5, 20, 60 |
| Outcome counts, including target | 1, 12 | 1, 5, 20, 60 |
| Candidate PC counts | 1, 2 | 1, 2, 4 |
| Coefficient heterogeneity | 0, 1 | 0, 0.5, 1.5 |
| Added measurement quality | Informative | Informative, noisy, irrelevant |
| Independent seeds | 2 | 5 initially; expand before inference |
| First outer history length | 100 | 300 |
| Historical validation length | 25 | 60 |
| Outer test origins | 20 | 100 |
| Refit interval | 10 | 25 |

See [smoke.toml](../configs/smoke.toml) and [pilot.toml](../configs/pilot.toml) for exact penalty grids and generation settings. Treat the smoke output as a software check. Before substantive comparisons, increase independent repetitions until the Monte Carlo uncertainty of the paired loss differences is acceptably small, and freeze the grid before inspecting confirmatory results.

Run the initial experiments in this order:

1. **Measurement breadth:** informative independent measurements, target-only outcome regression, and fixed K=2. Compare small and large measurement panels. Assess forecast loss and held-out factor alignment error.
2. **Coefficient sharing:** hold a fitted PCA representation fixed and vary outcome donors and sharing strength. Compare homogeneous with heterogeneous slopes. A signed `donor_shift` creates a controlled systematic donor mismatch; zero shift remains a useful neutral comparison.
3. **Dependence and measurement quality:** vary measurement-noise and outcome-noise correlation independently. Use `added_predictor_quality` informative, noisy, irrelevant, or correlated (added loadings emphasize the first factor). Common shocks can limit the benefit of additional assets.
4. **Forecast dimension:** fix donor panels and compare PC counts and lasso support with ordinary factor regression, direct ridge/elastic net, and PLS. Extracted K and the number of active lasso coefficients are separate reported quantities.
5. **Joint policy:** `adaptive_factor` selects M count, O count, K, sharing rule, and penalty against historical target validation loss. Evaluate its future forecasts as a single policy, including its selection uncertainty.

The current runner searches fixed prefix panels. A constrained adaptive comparator that forces identical donor memberships, randomized or economically ordered prefixes, and equal search budgets are planned additions for a clean test of separate donor selection. Comparing different fixed M/O cells alone does not establish the value of a learned donor-selection rule.

## Models and diagnostics

| Implemented model | Purpose |
| --- | --- |
| Historical mean; empirical persistence and own-history regression | Basic reference forecasts |
| Shared PCA with separate slopes | Measurement sharing without response pooling |
| Shared PCA with common slopes | Full coefficient-sharing restriction |
| Shared PCA with partial pooling | Normalized quadratic shrinkage toward a common slope |
| PCA plus lasso | Predictive selection in a declared PC basis |
| Direct ridge and elastic net | Strong direct-predictor comparisons |
| Target PLS | Supervised dimension reduction |
| Regression using true factors | Simulation-only removal of representation-estimation error |

Factor models share the exact same training-window representation for coefficient comparisons. Predictor columns and PC scores are standardized on training rows. Intercepts and empirical own-history controls are asset-specific and unpenalized. Direct and PLS fits partial out the same target controls using historical projections. Outcome-pooling penalties use normalized loss so adding donors does not silently change regularization strength.

Record realized-outcome MSE and, in simulation, error against the known conditional mean. Align fitted scores to true factors using training rows only, then evaluate that map on later rows; this handles signs, scale, and rotations. It is a recovery diagnostic rather than identification of named economic forces. The fitted true-factor oracle is not a universal finite-sample lower bound. Comparing estimated and true slopes requires compatible coordinates, particularly if the fitted dimension differs from the true dimension.

The runner saves forecast-level losses, selected configurations and active slope counts, simulation diagnostics, exact settings, package versions, and code/configuration hashes. `simulation_summary.csv` reports Monte Carlo uncertainty across seeds for absolute MSE. Paired method-difference uncertainty and empirical date-block inference are subsequent analysis, not supplied by that summary.

## Stage 2: industry-return data pilot

Use a dated snapshot of the [French daily 48-industry portfolio data](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_48_ind_port.html). Retrieval and local setup instructions are in [data.md](data.md). Retain the raw ZIP, selected daily value- or equal-weighted table, conversion metadata, and hashes. The provider updates and revises histories, so describe this as a retrospective exercise on a fixed snapshot.

Default to value-weighted portfolios. The downloader converts source percentage returns to decimal returns and recognized missing sentinels to missing cells. Its prepared CSV requires `units = "decimal"`. A hand-prepared CSV still requires its units to be explicitly declared. Industry columns are observed predictors, rather than observed latent factors or independent asset replications.

At the end of Friday-ending week w, construct:

- `Q[i,w] = sum(daily_decimal_return[i,d]**2)` over that calendar week.
- `v[i,w] = log(Q[i,w] + c)`, with the fixed configured offset `c = 1e-8` initially.
- Target `v[i,w+1]` for the next calendar week.
- Own-history controls: current `v`, and trailing four- and twelve-week arithmetic means of `v`.
- Measurement panel: current weekly log proxies of the selected industries.

This close-to-close proxy is not intraday realized variance or the latent conditional variance. The initial minimum is three observed daily returns per asset/week. Missing calendar weeks remain on the grid; lags are formed before complete-case deletion. No forward fill or backward fill occurs. Audit partial weeks, missingness, and the exchange trading calendar before the substantive pilot.

Construct the full panel once and use the same conservative complete-case dates for all comparisons. This prevents panel size from changing the sample, but can lose coverage and conditions retrospective evaluation on response availability. Report that loss. Do not choose the date span after seeing forecast performance.

The initial empirical configuration uses 260 historical weekly pairs, 52 for inner validation, 104 outer test origins, and a 13-origin refit interval. It evaluates the first test block after the initial history; it does not automatically run to the latest observation. Before the substantive study, declare a modern calendar sample or explicit full-evaluation span and set the split sizes accordingly. Keep a final untouched terminal period if data coverage permits.

Start with a named target such as Food for pipeline validation, then freeze the evaluation target set and report all of it, including unfavorable outcomes. The CLI moves the selected target to column zero and preserves the remaining CSV order. That ordering is saved, but is not an economically optimized donor ranking. Planned comparisons include predetermined industry neighborhoods and training-only similarity rankings, with equal candidate budgets.

## Chronological fitting and inference

For each outer cutoff:

1. Use historical predictor/outcome pairs whose outcomes have already been realized.
2. Fit each candidate's transformations and model on the earlier inner training segment.
3. Predict the following historical validation segment without updating its transformations.
4. Choose the candidate using target validation MSE.
5. Refit the entire selected pipeline on the available outer history and predict the next outer block.

Earlier outer test outcomes may enter later refits after realization. No later response enters an earlier forecast. The implemented horizon is one nonoverlapping period. Longer-horizon targets require purging training origins whose response intervals cross a validation/test boundary and explicit overlap-aware inference.

For the empirical study, analyze paired loss differences on identical dates. Resample date blocks jointly across industries to preserve common shocks, or use dependence-robust forecast-comparison methods. Report block lengths, weights across targets, model-search scope, and sensitivity. Do not treat industry–week rows as independent observations. Multiple-model comparisons and repeated exploratory choices require separate inferential controls.

## Economic evaluation and possible extensions

The first economic test is scalar risk targeting for a predetermined industry proxy or fixed portfolio, after checking practical investability. Convert log forecasts to positive conditional-mean variance forecasts using a training-only smearing correction or a separately fitted positive model; exponentiation alone is insufficient. Evaluate variance-scale calibration and QLIKE only with stated proxy assumptions.

For a prespecified exposure rule, compare risk-targeting error, certainty-equivalent return, drawdown, turnover, and net performance across a transaction-cost grid. Declare financing/cash treatment, exposure caps, risk horizon, and the turnover convention. Marginal variance forecasts do not provide the covariance matrix needed for a changing multi-asset optimizer; that would be a separate model.

Add targeted or weighted PCA, weak predictive directions, strong irrelevant common factors, residual predictor channels, loadings/coefficient breaks, multi-output or hierarchical models, and modest nonlinear direct baselines only when a specific pilot failure motivates them. Later applications to macroeconomic or other panel time series need their own timing, vintages, outcomes, losses, and decisions.

## Deliverables before theory

The first meeting deliverable is a reproducible simulation table and plots separating measurement breadth from coefficient-sharing effects, with uncertainty across independent seeds. The next deliverable is the audited industry snapshot and retrospective forecast comparison. Explain whether simple partial pooling or direct regularization already absorbs the benefit before proposing a more complex method.

Only mechanisms that survive these checks motivate proofs: for example, a dependence-aware pooling threshold, a joint risk bound with generated-factor cross terms, or selection over a declared finite donor-design family. State factor-strength, stability, moments, dependence, and candidate-complexity assumptions explicitly. An interior panel-size optimum and universal factor superiority are not required outcomes.
