# Proposed Experiment 3: PCA and coefficient-history surfaces

## Status, scope, and interpretation

This protocol is dated November 2, 2026. **Experiment 3 is documented only: no implementation, forecasts, bootstrap draws, surfaces, new tests, or results have been produced.** The [planning TOML](../../configs/experiment_03_plan.toml) is non-executable and must not be passed to an existing runner. The user has deferred calibration/power research; this plan does not authorize or schedule that work.

The experiment separates two previously linked questions. Part A limits both the factor-measurement fit and forecasting coefficients to the same recent L pairs. Part B repeats the identical coefficient-history/dimension grid with expanding predictor-only PCA. Comparing A and B at fixed L, K, and sharing rule isolates the forecast consequence of retaining older predictor observations for measurement, conditional on these estimators and dates. It does not identify latent factor recovery or a causal economic mechanism.

A dense surface can reveal nonmonotonic prediction patterns. It cannot establish that short histories necessarily give larger or more significant gains. Own-history regression is a small model; the usual dimension-reduction rationale against a large raw-predictor regression does not guarantee an advantage over that baseline. Larger gain against a short-history baseline can also reflect a worse baseline rather than a better factor forecast.

All proposed dates have already been inspected in Experiments 1 or 2. Earlier and later samples below are **seen-period exploratory evaluations**, not fresh development/holdout evidence. Freezing this computation before execution prevents undisclosed redesign but does not restore an untouched evaluation period.

## Data, dates, and common information

Retain the October 16, 2026 French 48-industry daily-return snapshot and its provenance/hashes. Value-weighted portfolios are primary; equal-weighted portfolios are separate robustness, not independent replication. The six targets remain

`S = (Food, Mach, Banks, Oil, Util, Hlth)`.

Measurement M is all 48 industries throughout. Separate factor slopes use target-only outcomes. Common and partial factor slopes use all 48 outcomes, including the target. There is no donor ranking, small-outcome-panel comparison, membership selection, or new target selection.

Keep weekly Q=sum of squared decimal daily returns, Friday labels, minimum three observed daily returns, `q=log(Q+1e-8)`, current/four-/twelve-calendar-week own-history means of q, and next-calendar-Friday responses. Build histories/responses on the full weekly calendar before filtering. No filling or interpolation is allowed. Prebuilt causal feature histories may begin before the coefficient window; L restricts estimation pairs rather than deleting already available observations used to construct a feature.

Use the same full-panel complete-case mask across all 48 industries and both weightings, requiring current predictors, own controls, and next-week responses. This preserves dates across the complete grid. It is a retrospective sample conditioned on response availability, not a claim that future responses can enter forecasts. Preserve source-vintage/revision documentation; the French-library CIZ source change is not assumed to create a January 2025 time-series breakpoint.

Keep origins from January 1, 2000 and responses through August 28, 2026. The first common outer cutoff is 572 aligned pairs. Split outputs by response date into:

- `earlier_seen`: from that common first forecast through December 31, 2024;
- `later_seen`: January 3, 2025 through August 28, 2026.

If the unchanged Experiment 2 calendar is reproduced, these periods have 718 and 87 dates respectively, with first evaluated response April 1, 2011. These are expected inherited audit checks, not newly generated Experiment 3 observations. All targets, modes, dimensions, sharing rules, and history lengths must use identical eligible dates within each period. Do not move endpoints after viewing the surface.

## Grid, policies, and duplicate accounting

The finite coefficient histories are the **19** values

`L = 52, 78, 104, 130, 156, 182, 208, 234, 260, 286, 312, 338, 364, 390, 416, 442, 468, 494, 520`.

Add one expanding-coefficient control. L counts retained predictor/response pairs; it approximates calendar weeks only when coverage is complete. Candidate factor dimensions are `K=1,...,8`. K=0 means only the own-history reference, fitted once per L; it is not an additional factor or pooling policy.

For every finite L and K, evaluate separate, common, and partially pooled factor slopes under both PCA modes:

| Mode | Part | PCA/scaler estimation history | Coefficient history |
| --- | --- | --- | --- |
| `matched` | A | Same L historical pair rows as coefficient fitting | Recent L |
| `expanding` | B | All historical predictor rows before the applicable cutoff | Same recent L |

The expanding-coefficient control uses expanding PCA in both parts and is identical across their labels. Evaluate and count that control once per K/sharing rule, with both labels mapped to one canonical identity. It is a representation/forecast duplication check, not an independent replication.

Per weighting and evaluation period, there are:

- 19 finite L x 8 K x 3 sharing rules x 2 PCA modes = **912 finite factor cells**;
- 8 K x 3 sharing rules = **24 distinct expanding-coefficient controls**;
- **936 distinct factor cells**, plus **20 distinct own-history references** shared across PCA modes, dimensions, and sharing rules.

Do not manufacture 960 independent factor cells by counting the 24 common expanding controls twice. Retain all cells, unfavorable targets, and references; do not select a new K, L, mode, or sharing-rule winner from the seen-period evaluation.

## Chronological fitting and representation sharing

Use zero-based retained pair indices. The first outer cutoff is `a0=572=520+52`, followed by anchors `a=572+13*k`. This preserves the old `260+13*k` schedule phase and supplies 520 inner coefficient-training pairs plus 52 validation pairs at the first anchor. Each fitted pipeline predicts the following at most 13 retained origins. Never restart refits at the earlier/later boundary; replay the scheduled crossing fit.

At anchor a, let `b=a-52`. Validation is `[b:a)`. For finite L:

| Fit | Part A: matched PCA | Part B: expanding PCA | Coefficient/nuisance fit in both |
| --- | --- | --- | --- |
| Inner candidate | X rows `[b-L:b)` | X rows `[0:b)` | Outcome pairs `[b-L:b)` |
| Outer refit | X rows `[a-L:a)` | X rows `[0:a)` | Outcome pairs `[a-L:a)` |

For the expanding-coefficient control, both parts use X/outcomes `[0:b)` and `[0:a)` respectively. Use only X rows corresponding to these declared historical pair slices, rather than adding extra unlabeled origin rows to the matched PCA window. Every historical fitted response must already have been realized at its applicable origin/cutoff.

**The complete representation obeys its PCA window:** predictor-column centering/scaling, PCA loadings, and score centering/scaling all fit on that window. Part B must not refit representation score scalers on the recent coefficient window. Ordinary coefficient-window FWL projection of the frozen scores on each industry's intercept/own controls remains required; it is not refitting the PCA representation. An unused recorded score mean is not a new scaling rule. No transformation may fit validation or future rows.

At each unique PCA window, fit one deterministic full-SVD representation with eight components. Freeze that fitted coordinate system; for K<8 use its first K components and their already fitted component-wise score transformations. Share the same first-K representation across targets, sharing rules, outcomes, and partial-pooling penalties. In Part B it is also common across finite L at a given cutoff. In Part A different L legitimately produces different PCA fits. This nesting avoids separate random rotations or sign choices across K; it does not identify economic factor names. Audit centered rank and finite score variances before using eight components; do not silently replace an unavailable component with a constant or change K for selected cells.

**Existing-code trap:** supplying an eight-component `PCARepresentation` to the existing `FactorForecaster` while labeling `n_factors=K` does not truncate its transformed design; it uses the supplied representation's scores. A future implementation must supply an explicit immutable K-prefix transform adapter, or equivalently select the first K frozen standardized score columns at **both training and prediction**, without refitting the representation. Merely changing the metadata/configuration K is insufficient. Require tests for transformed design width K, factor-slope dimension K, use of the same K prefix in validation/outer forecasts, and a nondegenerate example distinguishing K=1 from K=8. Record eight computed components separately from K used components. This requirement is one reason this plan needs new implementation rather than being passed unchanged to an existing runner.

Every target/donor intercept, own-history slope, nuisance projection, and factor coefficient uses the designated coefficient-window outcomes only. Own-history baseline intercept/slopes use the same L. All pooled outcome donors initially receive that same L as the target. Separate slopes use only the target response, though their PCA still measures all 48 predictor industries.

Local controls are industry-specific and unpenalized. Only factor slopes are constrained or shrunk across outcomes. There are no direct ridge, elastic-net, or PLS fits in this focused grid; those remain context from Experiment 2, not new same-period significance references in this plan.

## Partial pooling: exact objective and historical tuning

For n coefficient-training pairs, J outcome donors, K standardized PC scores f_t, industry controls h_jt, and factor slopes theta_j, minimize

`(1/(n*J))*sum_t,sum_j (y_jt - a_j - h_jt' beta_j - f_t' theta_j)^2`

`+ lambda*(1/J)*sum_j ||theta_j - theta_bar||_2^2`,

where `theta_bar=(1/J)*sum_j theta_j`. This matches the existing `FactorForecaster` normalization. The factor-slope penalty averages over industries but **does not divide by K**. Increasing K therefore changes the total number of penalized directions; the fixed grid describes a declared estimator family, not identical per-model total shrinkage. Zero lambda would reproduce separate slopes; very large lambda approaches common factor slopes, but those endpoints are already explicit policies.

Keep `lambda=(0.01,0.1,1,10,100)` in ascending order. Select lambda independently for each target/mode/L/K/refit cutoff by the target's MSE on the 52 historical validation pairs, with first-declared-penalty tie-breaking. Do not tune on donor-average validation error, the penalized training objective, the whole evaluation heatmap, or the favorable target subset. Refit the selected objective on its outer coefficient window using the outer PCA representation. The two PCA modes can select different lambdas; their partial-pooling contrast compares complete historically tuned procedures, not PCA loadings with a fixed penalty.

Common and separate slopes and own-history OLS have no searched penalty. K and L remain fixed grid axes, not validation-selected parameters in this experiment. A future adaptive K/L policy would be a separate procedure requiring its own prospective evaluation.

## Losses, surfaces, and contrasts

Use next-week realized squared log-proxy errors, including mean forecast error. For each target i, calculate MSE on identical evaluation dates. For factor cell C and the matching-L own-history reference O_L, the principal surface is

`G(C,O_L)=1-(1/6)*sum_i [MSE_i(C)/MSE_i(O_L)]`.

Positive G favors C. Report `100*G` as an equal-target own-history-reference gain, not a ratio of pooled MSEs or an average of per-week ratios. Also report target MSE/MAE and the descriptive mean of target MSEs in squared-log units so a changing baseline cannot disguise deteriorating factor accuracy.

At finite L, fixed K, and sharing rule r, define the direct PCA-mode contrast

`Delta_mode = G(C_expandingPCA,O_L) - G(C_matchedPCA,O_L)`

`= (1/6)*sum_i [(MSE_i(C_matchedPCA)-MSE_i(C_expandingPCA))/MSE_i(O_L)]`.

Positive Delta favors expanding PCA. Both gains use the **same** own-history denominator, so this is a common-baseline advantage difference. It is not `G(C_expandingPCA,C_matchedPCA)`, which uses a different reference. The treatment changes the complete fitted measurement representation, including predictor/score scaling, and its downstream fitted coefficients; partially pooled cells also retain mode-specific historical lambda choices. The expanding-coefficient mode contrast is identically zero and must not be counted as another test.

At fixed mode/L/K, also report descriptive pooling contrasts `G(C_common,O_L)-G(C_separate,O_L)` and `G(C_partial,O_L)-G(C_separate,O_L)`. Their denominators are again identical matched own-history MSEs. Positive favors the named sharing rule. These planned contrasts do not establish a formal interaction between window length and pooling.

## Joint bootstrap, uncertainty, and the anchor family

The existing calibration/power investigation is **pending and deferred**, rather than a prerequisite for a future separately authorized computation of these descriptive maps. Experiment 2's bounded diagnostic showed adverse rejection/coverage behavior, including 11% rejection of a nominal 5% null at 87 observations and nominal-95% coverage of 90%/81% at 87/156 dates. Repeating its computational conventions does not fix that problem. All uncertainty here remains approximate, marginal, and exploratory; no universal, confirmed-significance, or nominal-size guarantee follows.

The proposed resampling is a paired stationary bootstrap with **9,999 draws**, primary expected block length **13 retained dates**, sensitivities **6 and 26**, and NumPy `Generator(PCG64)` seed **20261102**. At each period/block setting, reset to that seed and generate exactly one date-index matrix. Reuse it across both weightings and every L/K/mode/sharing/baseline cell and contrast. Each replicate starts with an integer uniform index; each subsequent position draws a restart uniform, draws a new integer only on restart with probability 1/block_length, and otherwise advances circularly. Preserve each complete date vector; do not resample industries independently or treat equal weighting as independent evidence.

Recompute every target-specific numerator and reference MSE on the sampled dates. For a mode contrast, recompute all three means (both candidate modes and own baseline); for pooling contrasts recompute both sharing policies and their common baseline. No denominator is fixed to an original/development value. Models, PCA, and lambda selection are not refitted inside bootstrap draws. Zero/nonfinite denominators or nonfinite required losses cause deterministic failure, with no epsilon, target removal, or discarded draw.

These are intervals for saved forecast-loss gains and contrasts, including those from the historically selected partial-pooling procedure. They are not confidence intervals for lambda, loadings, factor coordinates, or regression coefficients. No factor-coordinate alignment is needed for scalar forecast losses. A future analysis of repeated-training uncertainty would need to regenerate data and rerun PCA and lambda selection under its own justified model; that work remains deferred.

For any scalar gain/contrast T_hat and its uncentered bootstrap replicates T_b, report the nominal basic 95% marginal interval

`[2*T_hat-q_0.975(T_b), 2*T_hat-q_0.025(T_b)]`,

using linear quantiles and no endpoint clipping. Every one of the **936 own-history gain cells** receives that descriptive interval. Also provide intervals for all **456 finite PCA-mode contrasts** and the **624** common-minus-separate/partial-minus-separate contrasts (608 finite plus 16 deduplicated expanding controls). These are marginal intervals, not simultaneous confidence bands; a positive endpoint cannot be used as an unadjusted significance star across the surface.

Formal approximate p-values are limited to **30 prespecified anchor contrasts** on `later_seen`. Earlier-seen surfaces/intervals are descriptive and receive no p-value family. The anchors retain the old K=2 and L=104/260/520 values to connect with Experiment 2, rather than selecting favorable dense-grid cells:

1. K=2 x three finite anchor L x two PCA modes x three sharing rules: **18** own-history-reference comparisons.
2. K=2 x three sharing rules with expanding coefficients/PCA, deduplicated across modes: **3** own-history-reference comparisons.
3. K=2 x three finite anchor L x three sharing rules: **9** paired PCA-mode Delta comparisons.

Together these are **one Holm family of 30** per weighting and block setting, not separate families for each mode or sharing rule. Value weighting/block 13 is the primary planned anchor setting; equal weighting is a separately adjusted robustness family, and blocks 6/26 are sensitivities. They do not supply combined across-weighting/block error control. Even these anchored tests are exploratory because their economic evaluation period is already seen.

For an anchor, the one-sided null is that its population analogue is <=0; the alternative is >0 in the declared favorable direction. Use the centered aggregate root `D_b=T_b-T_hat` and `p=(1+count(D_b>=T_hat))/(9999+1)`, including ties. Apply Holm step-down to all 30 together at alpha=0.05; report signed effects, raw/adjusted p-values, and both favorable and unfavorable comparisons. A favorable adjusted threshold crossing is described as a result of the planned approximate rule, not demonstrated finite-sample significance. Do not change the test direction after seeing a negative estimate.

Do **not** produce formal p-values for the other surface/pooling cells or select the smallest p-value on the map. A Holm family of all 936 own-history cells with 9,999 draws would have minimum possible adjusted p-value 0.0936, so it could never reject at 5%; this is one reason to separate complete exploratory maps from a small fixed anchor family. It is not a reason to hide tests or redesign anchors after execution. No dedicated formal pooling/history interaction family or future calibrated confirmatory family is supplied by this plan.

## Required visualizations and output records

For each weighting and seen period, show three-rule K-by-finite-L surfaces for Part A and Part B side by side. Share gain color limits/zero reference across paired modes; show expanding controls as clearly labeled side panels, not an extra finite L. Own history K=0 may be drawn as a visual reference only, with duplicated displays explicitly identified.

Provide separate absolute-MSE surfaces and mode-difference maps so matched-baseline changes are visible. Provide common-minus-separate and partial-minus-separate maps on their common own-history normalization. Complete CI tables accompany all surfaces. Do not add unadjusted significance stars, color-selected target subsets, or a best-cell recommendation. A separate anchor forest/table reports all 30 later-seen comparisons with marginal intervals and Holm-adjusted values; it must not imply that all heatmap cells are formally tested.

Save every target/weighting/period/mode/L/K/sharing prediction and actual; explicit predictor/outcome memberships; representation/scaler/score-window endpoints; coefficient-window endpoints; refit/validation dates; all partial-pooling candidate losses and selected lambdas; duplicates/canonical cell mappings; own-baseline MSEs; all aggregate/target summaries, bootstrap settings/index matrices/hashes, intervals, and anchor-family membership. Preserve inherited Experiments 1/2 unchanged.

Future raw prediction and tuning records must be streamed or written in deterministic compressed shards, partitioned by period/weighting/mode/L and a documented stable shard sequence. Do not hold the entire forecast/tuning grid in RAM or rely on one growing gzip file. Each completed shard must be **smaller than 80 MiB**, with a checked hard file-size ceiling below 100,000,000 bytes. Use canonical cell metadata and a single stored expanding-coefficient control rather than duplicated A/B records. Preserve every raw row, including all historical lambda-candidate scores; shard boundaries are storage decisions, not permission to discard outputs. Record an ordered inventory with paths, formats, row counts, byte sizes, SHA-256 hashes, and complete-record count checks. Freeze deterministic row ordering, numeric serialization, and compression metadata. No runtime or total-storage estimate has been benchmarked; the larger grid must be assessed before future execution without changing the scientific design.

## Feasibility, validation gates, and deferred work

No runtime benchmark or implementation has been performed. The surface is a much larger fit inventory than Experiment 2. A future implementation should cache one eight-PC representation per unique fitting window, reuse first-K scores across sharing rules, and reuse identical multi-output partial fits across targets where the same objective/penalty applies. Target-specific validation decisions still require their own recorded losses. Any faster solver must reproduce the stated normalized objective; computational pressure does not authorize changing the estimator or dropping unfavorable cells.

Bootstrap feasibility comes from resampling **saved losses**, not refitting 9,999 model grids. Generate each index matrix once and process loss means/contrasts in bounded L/K batches. Avoid allocating a draws x dates x all-cells x targets tensor. The common/separate/partial means for both modes and one baseline at a given L/K suffice to derive the own, mode, and pooling contrasts. Save exact joint-index matrices and canonical little-endian int64 shape/data hashes for independent reconstruction.

Before execution, validate exact matched/expanding PCA windows, column/score scaler placement, K-prefix reuse, no validation lookahead, coefficient/donor windows, lambda objective/target validation, 572+13k boundary replay, 936-cell deduplication, 30-anchor membership, target-normalized contrast algebra, joint resampling, basic interval/root tails, invalid denominators, and the absence of surface p-value selection. Record a code/configuration/data freeze before any new output; no analysis is currently executed by this document.

Software/numerical tests would verify implementation, not bootstrap calibration. Calibration and power studies, studentized/HAC alternatives, full-pipeline simulations, learned donor selection, adaptive K/L selection, new markets/periods, and economic utility are **explicitly deferred**. No automation, implementation, empirical run, bootstrap run, or calibration run is created or authorized by this planning artifact.
