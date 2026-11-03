# Experiment 3: pre-execution implementation record

Recorded November 3, 2026, before empirical Experiment 3 forecasts or resampling. The original November 2 protocol and planning TOML are unchanged. The executable copy preserves all scientific sections and planned storage constraints; only authorization/implementation bookkeeping differs. Calibration and power studies remain deferred and are not run by any stage.

## Data and calendar

Read-only preparation verifies the archived October 16 French daily inputs against provenance and every one of the 107 manifest-listed files in Experiments 1 and 2 against its exact-byte hash. The inherited common calendar has 1,377 pairs, 718 evaluated earlier-seen dates and 87 later-seen dates. First evaluated response is April 1, 2011; first later response January 3, 2025; last response August 28, 2026. The crossing scheduled refit is 1,287 for first later pair 1,290. Both periods have already been inspected; no fresh holdout claim is made.

The canonical inventory has 936 factor cells and 20 matching-history own regressions. It contains 19 finite histories, eight PC counts, three slope rules, two PCA modes, and one deduplicated expanding-coefficient control per K/rule. There are 456 paired mode differences and 624 pooling differences per weighting/period. Only 30 predeclared later-seen anchors receive p-values, jointly adjusted per weighting/block setting.

## Numerical and software checks

The complete suite passed **118 tests in 42.122 seconds**. A focused six-test orchestration recheck passed after final independent-audit safeguards. The recorded validation log and its successful status/hash are required by the freeze stage; a failed or stale gate cannot be accepted merely because a file exists. The source checkout is provided through `PYTHONPATH=src`, and scientific BLAS thread counts are one.

Seven new surface tests compare the fast partial-pooling solver with the original full stacked estimator at K=1/2/8 and all five penalties, including slopes, predictions, and first-order conditions. They also check separate/common estimators including rank deficiency, actual K-prefix design dimensions, chronological PCA/coefficient windows, future-data perturbation invariance, boundary replay, penalty ties, and deterministic streamed artifact round trips.

Ten new bootstrap tests check scalar oracles for own gains and own-normalized mode/pooling differences; joint date indices and hashes; ratio denominator recomputation; basic intervals; centered one-sided tails; the whole 30-anchor Holm family; absence of earlier/nonanchor p-values; and invalid data/denominator failure without dropping draws. To match Experiment 2, the decision label uses a **strict** favorable-effect and adjusted-p < 0.05 threshold; an adjusted value exactly 0.05 is retained and does not cross that rule. Raw and adjusted p-values are always saved without display rounding affecting decisions.

Four reporting tests cover all 956 canonical cells, expected 22,944 target and 3,824 aggregate summary rows, equal-target ratio aggregation, bounded memory-mapped reads, missing/invalid baseline rejection, and 19 synthetic PNG/PDF figure pairs. These are implementation fixtures, not a Monte Carlo calibration or power study.

Six orchestration tests guard scientific settings, the fixed original plan path, storage limits, deferred-work authorization, output checksum integrity, and independent PCA-window audit logic.

A synthetic full-grid one-refit technical benchmark with 580 generated rows and eight evaluation origins took 3.37 seconds including streaming/hashing. It generated 45,888 raw predictions and 13,224 tuning-candidate records for one weighting and removed its temporary outputs. This checks feasibility only; it is not a promise about empirical runtime or total storage, nor a new empirical or calibration result.

## Independent review and post-run audits

Independent source review checked the exact matched/expanding PCA windows and all representation scalers, immutable K-prefix handling, coefficient/donor/nuisance windows, normalized partial-pooling objective, target-specific historical penalty selection, and the 572+13k refit phase. The Schur-system optimization preserves the original objective; it does not change penalty normalization or divide by K. The old estimator, features, original protocols, and archived results were not edited.

The frozen audit script will compare all streamed records against prediction arrays and daily-derived actuals, require exactly one record per date/cell/target, inspect every window and candidate argmin, and reproduce all overlapping Experiment 2 forecasts. It will independently rebuild all six bootstrap index matrices and recompute all 24,192 interval rows, 180 anchor tail counts, and six Holm families from saved forecasts. Semantic contrast identities, plot labels, anchor tables, index/loss hashes, and artifact inventories are audited as well. These empirical-output checks are pending at this pre-execution point.

## Statistical limitation retained

No new calibration or power simulation was run. The inherited Experiment 2 diagnostic remains adverse: 11/100 null rejections at nominal 5% for 87 dates, and 90/100 and 81/100 coverage for nominal 95% basic intervals at 87 and 156 dates. Passing software checks or independently reproducing computations does not establish nominal coverage, calibrated p-values, or full-pipeline validity. All Experiment 3 maps and anchor results remain approximate seen-period exploration, including partial pooling. The earlier diagnostic is copied into the archive solely as historical evidence, not recomputed.
