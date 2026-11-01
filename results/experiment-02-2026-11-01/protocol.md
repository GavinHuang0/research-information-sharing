# Proposed Experiment 2 protocol

## Status and purpose

This design is dated October 31, 2026. Experiment 2 has not been implemented or run. No new forecasts, bootstrap draws, p-values, intervals, or history-length comparisons are asserted. The [planning TOML](../../configs/experiment_02_plan.toml) is not a schema supported by an existing runner. Implementation, synthetic validation, independent auditing, and a written freeze must precede empirical execution.

The experiment first quantifies uncertainty in the saved first pilot, then varies coefficient-training history while fixing its primary factor procedure and factor-estimation history. The aim is to determine whether the evidence supports an advantage; significance is not a required outcome. Negative effects, large p-values, direct-method wins, and inconclusive intervals must be retained.

The outcome remains next-week log daily-return variation for six fixed industry portfolios. These tests cannot establish accuracy for latent variance, intraday realized variance, returns, a trading strategy, arbitrary future regimes, or factors as a universal forecasting class.

## Data and fixed information

Retain the October 16, 2026 French 48-industry snapshot and provenance used in Experiment 1. Value-weighted portfolios are primary; equal-weighted portfolios are a separate robustness analysis on identical dates, not independent replication. Keep the target/small-panel set

`S = (Food, Mach, Banks, Oil, Util, Hlth)`.

Weekly definitions are unchanged: decimal daily returns; Friday-ending `Q[j,t] = sum(r[j,d]^2)` with at least three observed daily returns; `q[j,t] = log(Q[j,t] + 1e-8)`; own controls consisting of current q and its trailing four- and twelve-calendar-week arithmetic means; and response q at the next Friday, exactly seven days later. Build features and responses on the full weekly grid before filtering. Do not fill or interpolate.

Use a common complete-case calendar requiring all 48 industries, both weightings, current predictors, next-week responses, and all own-history controls. Keep dates identical across targets, methods, and history rules. This retrospective evaluation sample depends on response availability; future outcomes define eligibility but must never enter forecast inputs or fitted transformations. The revised snapshot does not certify historical vendor-release availability.

Part B retains origins from January 1, 2000 and responses through August 28, 2026. A data-only audit must check coverage, exact next-week alignment, exclusions, and the source-release methodology before scoring new forecasts. The French library adopted CRSP CIZ starting with the January 2025 **release**; this fixed snapshot reconstructs historical returns and must not be assumed to contain FIZ observations before response-year 2025 and CIZ observations afterwards. Record the actual source/vintage conventions and assess any genuine discontinuity rather than asserting a calendar breakpoint. Do not move the endpoint after inspecting losses.

## Part A: saved first-pilot inference

Use saved forecasts under `results/fixed-pilot-2026-10-27/`. Before a future bootstrap, verify manifests, recompute squared errors from actuals/forecasts, reject duplicate keys, and enforce identical eligible dates for every target and reference. These are execution requirements, not newly completed checks in this document.

Fix F to the original development-selected `factor_pooled__M-all__O-all`: two PCs measured with all 48 industries, common factor slopes across all 48 outcomes, and separate industry intercepts/own-history coefficients. The four references are fixed:

| Reference | Policy ID | Information |
| --- | --- | --- |
| Own history | `local_history__M-none__O-target` | Intercept and own current/four-/twelve-week controls |
| Ridge | `ridge__M-all__O-target` | Same 48 current measurement variables and target own controls |
| Elastic net | `elasticnet__M-all__O-target` | Same 48 current measurement variables and target own controls |
| PLS | `pls__M-all__O-target` | Same 48 current measurement variables and target own controls; two supervised components |

The factor model additionally shares outcome information. The direct comparisons test these fixed feasible procedures, not an abstract information-theoretic advantage of PCA. Do not substitute the best 2022–2024 factor cell or a favorable direct comparator.

Use the already inspected 156 response dates in 2022–2024. Apply the ratio statistic and bootstrap below, with a four-comparison value-weighted Holm family and a separate four-comparison equal-weighted robustness family. All Part A p-values and intervals are **exploratory post-pilot inference**. Holm adjustment does not repair the retrospective choice of questions, and this period is not a new holdout.

## Part B: fixed procedure, different coefficient histories

### Policies and primary comparisons

The primary factor policy remains **`factor_pooled__M-all__O-all` for every history rule**. Do not choose a new factor cell per L, target, weighting, or final score. Holding policy identity fixed prevents a history effect from being confounded with changing pooling rules or panel memberships.

Coefficient histories are `L=104`, `L=260`, `L=520`, and `L=expanding`, measured in retained predictor/outcome pairs. Finite windows are approximately two, five, and ten years when the calendar is complete; report actual calendar spans across gaps. Donors initially receive the same L as the target. A short target with long-history donors is a separate experiment. The features of each selected pair retain their already-available calendar history, including twelve-week controls that can begin before the coefficient window; L restricts supervised estimation pairs, not the prior observations used to construct a causal feature.

For each L, compare the fixed factor policy with the four references in Part A, each fitted with that same L. Ridge/elastic net/PLS always use all 48 current measurement variables and the same target own controls. In addition, directly compare each finite-L factor forecast with the expanding-L factor forecast on identical dates. These three history comparisons are needed: significance against own history at L=104 but not at L=expanding would not itself demonstrate that 104 beats expanding.

Report the first pilot's complete 18-label family for every L as secondary descriptive cells: own history, persistence, ridge/elastic net/PLS at M=S or all, separate-slope PCA at either M with target-only outcomes, and common/partial factor slopes at either M with O=S or all. Fix K=2. Persistence is the same forecast across L, not four independent procedures. No membership search, factor-count search, new global winner selection, or minimum-p-value selection is allowed. Comparisons of pooling benefits across L are exploratory mechanism diagnostics, distinct from the primary direct history tests.

### One common chronology

Index aligned pairs from zero. Use first outer cutoff `a0=572=520+52`. At this cutoff, a nominal 520-pair model can fit exactly 520 inner-training pairs before 52 validation pairs; starting at 520 would leave only 468. Common refit anchors are `a=572+13*k`. Since `572=260+24*13`, the original pilot's schedule phase is preserved. Each fit forecasts the following at most 13 retained origins; never add a refit at an evaluation boundary.

Use identical forecast dates and this same schedule for all L, including the expanding control. Exclude first-pilot forecast dates before this common start. Reproduce the expanding control under the documented fitting rules; any reuse of saved overlapping forecasts would require an audit proving identical windows, transformations, tuning, and values. It would not be a new independent replication.

At anchor a, let `b=a-52`. Historical validation is `[b:a)`. For finite L:

| Operation | Inner candidate fit | Refit after historical tuning |
| --- | --- | --- |
| Predictor-only PCA centering/scaling, PCA, score scaling | Expanding predictor rows `[0:b)` | Expanding predictor rows `[0:a)` |
| Supervised coefficients/nuisance fits/direct-model scalers | Recent L pairs `[b-L:b)` | Recent L pairs `[a-L:a)` |
| Candidate evaluation | Fixed candidate predicts `[b:a)` | Fixed refit predicts the following block |

For expanding L, coefficient windows are `[0:b)` and `[0:a)`. Every fitted outcome must already have been realized by the relevant forecast/refit origin. No validation row may fit its candidate's PCA, scalers, nuisance projections, PLS directions, or coefficients.

Fit each M's PCA representation once per cutoff and reuse that exact fit across L and all corresponding outcome/pooling rules. Thus the primary experiment changes coefficient history while holding expanding factor measurement fixed. Intercepts, target/donor own-history slopes, factor slopes, direct nuisance projections, direct-model scaling, and response-dependent PLS directions must use only their designated coefficient window. Direct ridge/elastic net/PLS retain training-only partialling out of intercept/own controls. PLS cannot learn supervised directions from expanding outcomes when L is finite.

The methods have the same current measurement variables, but not identical transformation-training rules: PCA intentionally has long unsupervised X history, whereas direct coefficient/nuisance/scaling fits use L. Record this distinction rather than claiming that all transformed inputs use identical estimation histories. Long predictor-only PCA history with short outcome history is the treatment under study.

Retain Experiment 1's model definitions except for the explicitly changed estimation windows: two full-SVD PCs, the training-only PCA/score scalers, unpenalized local controls, normalized ridge/elastic-net/partial-pooling objectives, and target-specific penalty tuning. Retain grids: ridge `(0.01,0.1,1,10)`, elastic net `(0.001,0.01,0.1)` with `l1_ratio=0.5`, and partial pooling `(0.01,0.1,1,10,100)`. Elastic net retains `tol=1e-10` and `max_iter=100000`. Choose each target/policy/L penalty by historical target validation MSE, with first-declared-penalty tie-break. Penalties continue to update only by this frozen historical rule, not final-score redesign.

### Development and new final interval

All eligible Part B forecasts with response dates through December 31, 2024 are development. This explicitly includes the first pilot's inspected 2022–2024 evaluation. Use development for implementation checks and descriptive diagnostics, not to choose new factor cells, history lengths, references, or primary contrasts.

The proposed new final interval is response dates **January 3, 2025–August 28, 2026**, about 87 calendar Fridays before exclusions. Before scoring any forecast in that interval, freeze the procedure IDs, all 19 primary comparison definitions, training/validation rules, grids, bootstrap rules, calendar, data/source/code hashes, dependencies, and the complete development record. Verify and record that these forecast losses have not previously been examined.

This is a prospectively fixed analysis of a retrospectively observed but uninspected algorithm-evaluation interval, conditional on that verification. If its losses have been used for method development, label it exploratory rather than silently choosing another favorable interval. Existing economic outcomes are not future observations relative to the protocol date.

Evaluate all frozen cells and histories on identical new-final dates. Replay any scheduled fit crossing the boundary. Already realized new-final outcomes may enter subsequent refits by the frozen rolling/expanding rule, but cannot change policy identity, L choices, grids, panels, comparison families, or statistical conventions. No final winner selection is permitted.

## Ratio estimand and one-sided hypotheses

For target i, procedure P, and evaluation dates t, define `ell[i,P,t]=(actual_q[i,t+1]-forecast[i,P,t])^2` and `MSE_i(P)=mean_t ell[i,P,t]`. For a candidate factor forecast F and reference R, define

`G(F,R)=1-(1/6)*sum_i [MSE_i(F)/MSE_i(R)]`.

Targets receive equal weight after taking their individual ratios. This is not a ratio of pooled MSEs, an average of weekly loss ratios, a centered-error variance, or the penalized fitting objective. Positive G favors F; `100*G` is improvement in the equal-target mean reference-normalized MSE ratio. Mean forecast error remains part of MSE. All denominator MSEs must be positive and finite.

For own-history R this is exactly the first pilot's headline improvement functional. For ridge, elastic net, PLS, or an expanding-history factor reference, the denominator is that named reference's MSE on the same evaluation period. Do not label these different references as own-history improvement. There are **no fixed development denominators**.

For formal interpretation, let the population analogue replace each sample MSE by the evaluation loss process's mean squared loss. Each one-sided hypothesis is `H0:G(F,R)<=0` versus `H1:G(F,R)>0`. The boundary null is zero. A negative estimate retains its sign and original test direction. Report target MSE/MAE, target ratios, aggregate G, and raw error differences as distinct quantities.

For Part B's three history tests, F is the same fixed pooled policy with L=104,260,520 respectively, and R is that policy with expanding coefficient history. Their G values directly address average forecast accuracy of finite versus expanding histories. They do not by themselves identify whether drift, variance reduction, or coefficient heterogeneity causes an effect.

## Proposed joint stationary bootstrap

Resample the complete date vector of squared losses for all six targets, all procedures, all history rules, and **both weightings** within an evaluation stage. Generate one index matrix for each part/evaluation-stage/block-length setting and reuse it for every comparison and weighting. Assert that all applications have the same date order and index-matrix fingerprint. Weightings still have separate inferential families; common resampling does not make them independent. Do not resample targets independently or treat target-week rows as independent. The target population remains these fixed six industries.

For T ordered dates, draw an initial index uniformly from `0,...,T-1`. At each next position, restart at a uniform index with probability `1/b`; otherwise advance the previous index by one modulo T. Continue to exactly T draws. Geometric block lengths have expected length b; continuation is circular. Keep every date's entire loss vector together. Record calendar gaps because b counts retained dates rather than necessarily consecutive calendar weeks.

Use NumPy `Generator(PCG64)`, seed `20261031`, and `B=9999`. Primary b is 13; fixed sensitivities are 6 and 26. Reset that seed at the start of each recorded part/evaluation-stage/block-length setting, then reuse the resulting matrix across weightings. Generate replicates in increasing order, with an integer initial index, then one restart-uniform draw per subsequent position and an integer restart index only when a restart occurs. The following is planning pseudocode, not an implementation executed for this document:

```text
rng = Generator(PCG64(20261031))
for replicate in 0,...,9998:
    I[replicate,0] = rng.integers(0,T)
    for position in 1,...,T-1:
        if rng.random() < 1 / expected_block_length:
            I[replicate,position] = rng.integers(0,T)
        else:
            I[replicate,position] = (I[replicate,position-1] + 1) modulo T
```

Do not choose a block length by the smallest p-value. Models are not refitted or reselected inside this saved-loss bootstrap.

For every replicate bdraw, recompute target-specific numerator **and denominator** MSEs on the jointly sampled date indices and then calculate `G_b` with the same formula as G. Reusing the original reference denominator is not this bootstrap. If any original or resampled denominator is zero/nonfinite, or a required loss is nonfinite, abort that analysis deterministically and report the reason. Do not add epsilon, delete the target, discard the draw, or silently reduce the replicate count.

Let the observed estimate be `G_hat`. Use the centered bootstrap root `D_b=G_b-G_hat` as the approximate null distribution at zero:

`p=(1+count(D_b>=G_hat))/(B+1)`.

Include ties and keep this one-sided tail direction for every comparison. This centers the **aggregate smooth ratio statistic**, not individual target errors/losses. It is not the fraction of ordinary uncentered replicates where G_b is positive. Do not force a favorable direction after seeing G_hat.

The two-sided basic 95% marginal interval is

`[2*G_hat-q_0.975(G_b), 2*G_hat-q_0.025(G_b)]`,

with NumPy `method="linear"` quantiles. It is not a percentile interval, a studentized interval, or a simultaneous multiplicity-adjusted interval. Report 100 times endpoints if using percentage-point units. Do not clip endpoints to a convenient range, including the parameter bound, or confuse a marginal interval with an adjusted rejection decision. Record degenerate bootstrap distributions as a diagnostic, not numerical proof of certainty.

## Multiplicity and reporting decisions

For Part A, the four primary value-weighted p-values form one exploratory Holm family. Equal-weighted Part A uses a separate four-test exploratory robustness family.

For Part B, **one primary value-weighted family has 19 tests, evaluated only on the new final interval**: four factor-versus-reference tests (own history/ridge/elastic net/PLS) for each of four histories, plus three finite-history-factor versus expanding-factor tests. Part B development is descriptive and no development p-value family is planned. Equal-weighted robustness applies Holm separately to the same 19 new-final definitions. It is not independent evidence, and separate adjustment does not control a combined across-weightings claim.

At alpha=0.05, sort raw p-values `p_(1)<=...<=p_(m)`. Holm-adjusted values are `min(1,max_{k<=j}[(m-k+1)*p_(k)])`, restored to original comparison order. A particular advantage is supported by this planned approximate test only if its G_hat is positive and adjusted p<0.05. Report every raw/adjusted value and effect, including adverse or inconclusive comparisons. Sensitivity b values never replace the primary b=13 family; report them separately without minimum-p selection.

A claim that the fixed factor procedure beats all four references at a named L requires all four corresponding adjusted rejections. A claim that a finite history beats expanding requires that history's own adjusted direct test. Comparing p-values across L establishes neither. Per-target tests, other factor cells, histories beyond the fixed four, and pooling-by-history interactions are exploratory unless a new plan is frozen before their evaluation.

## Assumptions, limitations, and validation gates

The smooth-ratio bootstrap requires positive reference means, suitable moments of squared losses, and a sufficiently stable weakly dependent multivariate loss process for the stationary resampling approximation. Joint date resampling preserves observed common shocks but does not repair breaks, create more independent industries, or prove these assumptions. The new interval has about 87 observations and roughly seven expected 13-date blocks; 19-test adjustment can further limit power. No rejection is guaranteed. Failure to reject is insufficient evidence of improvement, not proof of equivalence.

Treat the p-values and intervals as **approximate conditional forecast-loss inference** for the frozen procedures and declared period. This protocol does not prove formal bootstrap size for the complete expanding-PCA, rolling/expanding-coefficient, penalty-tuned, nested-predictor learning pipeline. Saved-loss resampling does not regenerate the history, reselect methods across hypothetical development samples, or quantify every source of training/selection uncertainty. A new untouched evaluation interval improves design discipline but does not remove those theoretical limits.

The tested null concerns the actual loss of the estimated forecasting procedures, rather than zero population coefficients on additional predictors. Nested-model MSPE adjustments, such as Clark-West, address a different null/estimation issue and cannot be substituted for raw target MSE merely to obtain rejection. This loss-bootstrap plan does not automatically inherit their nested-model calibration results.

Holding factor measurement expanding isolates coefficient-history variation conditional on that long-history representation. It does not measure factor recovery, compare short versus long PCA histories, or establish that a window effect is caused by coefficient-estimation variance rather than drift. Those require distinct controlled experiments.

Before any empirical bootstrap implementation is allowed, require independently checked numerical and synthetic stationary-loss examples with known null direction and known positive effects. Validate paired joint indices, recomputed ratio denominators, the centered-root tail, basic interval formula, ties and finite-B correction, Holm families, invalid denominators, and block-length settings. Before any new forecasts, test exact coefficient/PCA/nuisance/PLS windows, common dates, no validation lookahead, and boundary replay. Passing these checks would validate implementation behavior, **not** establish full-pipeline finite-sample calibration. No such new statistical computation has been performed for this plan.

## Required artifacts and stopping rules

Use a new output directory and leave Experiment 1 immutable. Preserve plan/freeze/version/hash records; the source-transition/calendar audit; every target/weighting/history/policy forecast; actuals and squared losses; scheduled refit and fitting-window endpoints for PCA and every supervised stage; all historical tuning scores/penalties; bootstrap settings/index fingerprints; and all comparison estimates, interval endpoints, raw/adjusted p-values, and diagnostics.

Required tables show all fixed cells, target MSE/MAE and own-history ratios, the primary 19-comparison table, the three explicit history comparisons, block sensitivities, and equal-weighted robustness. Plots must identify each reference/normalization and keep unfavorable targets visible. No QLIKE, latent-variance inference, causal, or trading claim is part of this design.

If tests are inconclusive or unfavorable, retain the endpoint, target set, family, alpha, and all results. Do not keep changing windows, selecting panels, adding draws, extending the holdout, or replacing the block length until significance appears. A later redesign is a new stage with a separately justified evaluation period.

## Method references

- Politis, D. N., and Romano, J. P. (1994), [The Stationary Bootstrap](https://doi.org/10.1080/01621459.1994.10476870), motivates stationary resampling for weakly dependent stationary observations. Its assumptions still need checking for these losses and the smooth ratio.
- Holm, S. (1979), [A Simple Sequentially Rejective Multiple Test Procedure](https://www.jstor.org/stable/4615733), supplies the step-down family-wise adjustment. It does not repair the retrospective choice of questions in Part A.
- Giacomini, R., and White, H. (2006), [Tests of Conditional Predictive Ability](https://doi.org/10.1111/j.1468-0262.2006.00718.x), explains why estimation procedures matter in forecast evaluation. This saved-loss bootstrap is not their conditional predictive-ability test and does not inherit a theorem for this entire pipeline automatically.
- Clark, T. E., and West, K. D. (2005 working-paper version), [Approximately Normal Tests for Equal Predictive Accuracy in Nested Models](https://www.kansascityfed.org/documents/5368/pdf-RWP05-05.pdf), distinguishes MSPE-adjusted inference from an unadjusted comparison. Its adjustment is not applied to the raw-loss primary estimand here.
