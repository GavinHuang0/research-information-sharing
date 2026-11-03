# Experiment 3: PCA dimension and history surfaces

Completed November 3, 2026. This archive evaluates the unchanged November 2 design: **Part A fits PCA and coefficients on the same recent L pairs; Part B retains expanding PCA with the same coefficient windows.** Both compare separate, common, and partially pooled factor slopes, K=1-8, and L=52,78,...,520. Expanding-coefficient controls are counted once. Targets remain Food, Mach, Banks, Oil, Util, and Hlth; measurement donors are all 48 industries, and common/partial outcome donors are all 48.

**No primary block-13 Holm-30 anchor crosses the declared adjusted-p < 0.05 rule, in either weighting.** Full maps are descriptive point estimates with approximate marginal intervals. Neither the maps nor the fixed anchors are a new holdout: every evaluation period was already inspected. Calibration and power studies remain **deferred and pending**.

## Start with the graphs

Each gain graph has three rows (separate/common/partial slopes), Part A on the left, Part B in the middle, and a deduplicated expanding-coefficient control on the right. K increases vertically; finite coefficient history increases horizontally. Blue means lower MSE than the matching-history own regression and red means higher MSE. These colors depict point estimates, not significance. Expanding controls are sidebands, not another finite history coordinate.

| Period and weighting | Gain versus own history | Raw mean MSE and own baseline | Expanding-minus-matched PCA | Sharing-minus-separate |
| --- | --- | --- | --- | --- |
| Earlier, value | [PNG](reports/earlier_seen_value_gain.png), [PDF](reports/earlier_seen_value_gain.pdf) | [PDF](reports/earlier_seen_value_absolute_mse.pdf) | [PDF](reports/earlier_seen_value_pca_mode_difference.pdf) | [PDF](reports/earlier_seen_value_pooling_difference.pdf) |
| Earlier, equal | [PNG](reports/earlier_seen_equal_gain.png), [PDF](reports/earlier_seen_equal_gain.pdf) | [PDF](reports/earlier_seen_equal_absolute_mse.pdf) | [PDF](reports/earlier_seen_equal_pca_mode_difference.pdf) | [PDF](reports/earlier_seen_equal_pooling_difference.pdf) |
| Later, value | [PNG](reports/later_seen_value_gain.png), [PDF](reports/later_seen_value_gain.pdf) | [PDF](reports/later_seen_value_absolute_mse.pdf) | [PDF](reports/later_seen_value_pca_mode_difference.pdf) | [PDF](reports/later_seen_value_pooling_difference.pdf) |
| Later, equal | [PNG](reports/later_seen_equal_gain.png), [PDF](reports/later_seen_equal_gain.pdf) | [PDF](reports/later_seen_equal_absolute_mse.pdf) | [PDF](reports/later_seen_equal_pca_mode_difference.pdf) | [PDF](reports/later_seen_equal_pooling_difference.pdf) |

The [value anchor forest](reports/later_seen_value_anchor_forest.pdf), [equal anchor forest](reports/later_seen_equal_anchor_forest.pdf), and [all block sensitivities](reports/later_seen_anchor_block_sensitivity.pdf) show all declared formal comparisons. Every figure also has a PNG version. The 19 PDF exports were rendered and visually inspected.

## What the surfaces show

The results do **not** show a general monotonic disappearance of factor benefits as history grows. Earlier-period common-slope gains are widespread; later-period value-weighted gains are concentrated at shorter windows and often reverse sign at longer finite windows. For matched PCA, the value-weighted median gain across K=1-8 is:

| Coefficient pairs | Earlier common slopes | Later common slopes | Later separate slopes | Later partial pooling |
| --- | ---: | ---: | ---: | ---: |
| 52 | 4.50% | 1.97% | -4.69% | 1.57% |
| 104 | 4.75% | 2.76% | 1.45% | 2.38% |
| 260 | 5.24% | -1.87% | -2.98% | -2.16% |
| 520 | 5.23% | -1.43% | -3.31% | -0.95% |

These are descriptive summaries of dependent grid points, not new forecasting procedures, independent replications, or additional hypothesis tests. The complete [descriptive summaries](descriptive_summaries/) state their aggregation axes; underlying scores remain in the complete tables.

More PCs are particularly costly with very short coefficient histories and separate slopes. At the declared L=52/K=8 corner in the later value-weighted period, matched-PCA gains are -11.24% separate, +1.37% common, and -0.75% partial. Expanding-PCA gains there are -17.44%, -3.00%, and -2.85%. Sharing can therefore cushion instability without necessarily beating own history. This corner is an illustration, not a selected policy.

Partial pooling usually helps relative to separate slopes but is not uniformly preferable to common slopes. In later value weighting, common-minus-separate gains are positive at 132/152 matched-PCA coordinates and 149/152 expanding-PCA coordinates. Partial-minus-separate gains are positive at 136/152 and 146/152. Partial beats common at only 75/152 matched and 64/152 expanding coordinates. These counts are dependent descriptive grid summaries; no pooling/history interaction test was declared.

Longer PCA history is not uniformly helpful. Its effect depends on K, L, sharing, and period; higher-K expanding-PCA cells often perform worse than their matched-PCA counterparts. The treatment includes predictor/score standardization, PC loadings, downstream coefficients, and, for partial pooling, historically retuned penalties. It is not an isolated test of eigenvector noise or proof of changing economic factors.

## Fixed K=2 anchor snapshots

The table gives later value-weighted percentage MSE gains over the matching-history own regression. All six entries per finite history were declared anchors; no row is selected as a winner.

| L | Separate A | Common A | Partial A | Separate B | Common B | Partial B |
| --- | --- | --- | --- | --- | --- | --- |
| 104 | 3.148% | 3.527% | 3.013% | 3.855% | 3.970% | 3.715% |
| 260 | -2.874% | -2.002% | -1.892% | -2.280% | -1.753% | -1.765% |
| 520 | -2.216% | -0.750% | -0.881% | -1.652% | -0.407% | -0.653% |

With expanding coefficients, the shared K=2 controls have value-weighted gains -0.033% separate, 1.229% common, and 0.907% partial. Equal-weighted gains are 2.719%, 3.007%, and 2.989%. These forecasts reproduce the corresponding Experiment 2 cells; their new resampling seed/family changes uncertainty calculations, not the point forecasts or their status as previously inspected evidence.

Selected common-slope intervals illustrate the uncertainty:

| Weight | L | PCA | Gain | Nominal basic 95% interval | Raw p | Holm-30 p |
| --- | --- | --- | --- | --- | --- | --- |
| value | 104 | matched | 3.527% | [-3.179%, 12.179%] | 0.1692 | 1.0000 |
| value | 104 | expanding | 3.970% | [-3.204%, 13.143%] | 0.1568 | 1.0000 |
| value | expanding | shared | 1.229% | [-1.124%, 4.163%] | 0.1596 | 1.0000 |
| equal | 104 | matched | 0.923% | [-1.998%, 3.501%] | 0.2683 | 1.0000 |
| equal | 104 | expanding | 1.212% | [-1.132%, 3.422%] | 0.1593 | 1.0000 |
| equal | expanding | shared | 3.007% | [0.792%, 5.531%] | 0.0058 | 0.1682 |

All intervals are nominal basic 95% **marginal** intervals. A positive marginal interval is not a Holm-30 rejection. The [complete 180-row anchor table](inference/anchor_table.csv) retains every effect, interval, raw/adjusted p-value, and sensitivity setting. At primary block 13, there are zero adjusted threshold crossings for both weightings. Block 6 also has none. Block 26 flags only two equal-weighted anchors: partial pooling L=104 expanding-minus-matched PCA (+1.340 own-baseline percentage points, adjusted p=0.0300) and expanding-coefficient common slopes versus own history (+3.007%, p=0.0300). These secondary settings do not replace the primary analysis.

Unfavorable targets remain included. For example, later value-weighted matched-PCA K=2 common slopes at L=104 improve Food/Mach/Oil/Hlth but worsen Banks by 0.52% and Util by 2.78%. At L=260, only Hlth improves among the six. The [complete target table](reports/target_summary.csv) prevents favorable aggregate cells from concealing target-specific deterioration.

## Exact procedures and estimands

The [frozen protocol](protocol.md), [planning settings](planning_config.toml), [executed settings](config.toml), and [cell inventory](cells.csv) specify 936 distinct factors plus 20 own-history references per weighting/period. The original protocol/plan are historical declarations; the [execution account](../../experiments/03-pca-history-surface/executed.md) records the later authorization and completed run.

At a=572+13k, b=a-52. Inner/outer coefficient fits use [b-L:b)/[a-L:a), or start at zero for expanding. Matched PCA and all its column/score scalers use those same predictor rows; expanding PCA/scalers use [0:b)/[0:a). One eight-component representation is fitted per unique window and immutable first-K scores are used at both fit and prediction. Industry intercepts and own current/four-/twelve-week coefficients remain separate and unpenalized.

Partial pooling minimizes RSS/(nJ) + lambda/J sum_j ||theta_j-mean(theta)||^2, without dividing the penalty by K. Its five fixed penalties are 0.01,0.1,1,10,100. Each target/mode/L/K/refit chooses its penalty using target MSE on the 52 historical validation pairs, first declared penalty on ties. The fast solver was independently checked against the original full estimator; it changes computation, not the objective.

Own gain is G=1-(1/6)sum_i MSE_i(candidate)/MSE_i(own_L). Mode difference is G(expanding_PCA,own_L)-G(matched_PCA,own_L). Pooling differences similarly subtract separate-slope gains using the same own denominator. Gains are percentages; differences are own-baseline-relative percentage points. Neither is a pooled-loss ratio. Raw mean MSE is shown separately because changing own baselines can change relative gains without improving factor accuracy.

The saved-loss stationary bootstrap uses 9,999 draws, PCG64 seed 20261102, primary expected block 13 and fixed sensitivities 6/26. Every period/block has one date-index matrix shared across all cells, targets, and both weightings. Every draw recomputes all numerator and denominator MSEs; it does not refit models/PCA or reselect penalties. Basic endpoints are [2T_hat-q_0.975(T_b),2T_hat-q_0.025(T_b)], linear quantiles, no clipping. Zero/nonfinite denominators abort without epsilons or dropped draws.

All 936 own gains, 456 mode differences, and 624 pooling differences receive intervals for every weighting/period/block. Only the 30 later-seen anchors have p-values: 21 K=2 factor-versus-own comparisons and nine paired mode differences at finite L=104/260/520. For D_b=T_b-T_hat, p=(1+count[D_b>=T_hat])/10000. Holm adjusts all 30 jointly per weighting/block. The strict decision label requires a favorable effect and adjusted p<0.05. There is no simultaneous whole-surface coverage or combined across-weighting/block error-control claim.

## Execution, validation, and reproducibility

- Implementation `a1db310` and initial freeze `3586364` were committed before the earlier-stage start. [Source freeze](source_freeze.json) records code/tests/configuration/dependencies/input hashes and already-seen evidence status. All 107 earlier archive files remain unchanged.
- The inherited calendar has 1,377 pairs. Earlier seen: 718 dates, April 1, 2011-December 27, 2024. Later seen: 87 dates, January 3, 2025-August 28, 2026. First later index 1290 replays cutoff 1287 without restarting the schedule. The [later replay freeze](later_freeze.json) retains earlier file hashes; audited earlier outputs were committed as `583894a` before later execution.
- Earlier: 8,236,896 predictions, 1,481,088 candidate-tuning records, 112 weighting/refit blocks, 4,478 PCA fits, 290.806 seconds. Later: 998,064 predictions, 185,136 candidates, 14 blocks, 560 PCA fits, 38.145 seconds. Timings include the runner's streaming/closure work; stage logs retain exact events.
- [118-test validation](validation.txt) plus focused orchestration recheck and [preflight](preflight.md) precede execution. [Earlier](audit_earlier_seen.json) and [later](audit_later_seen.json) audits checked every raw record, calendar/window, target-specific penalty argmin, and actual reconstructed from daily inputs. All 137,856/16,704 overlapping Experiment 2 forecasts agree within 9e-14.
- [Independent original-estimator oracles](audit_original_estimator_oracles.json) reproduce 12 predeclared real-data groups, all six targets and five penalty candidates where applicable, with maximum prediction difference 4e-14. [Inference audit](audit_inference.json) independently rebuilt all six index matrices, checked all 24,192 interval rows, 180 exact tails and six Holm families, maximum effect/interval difference 1.11e-16.
- Compressed raw [earlier](earlier_seen/) / [later](later_seen/) prediction and tuning shards preserve every record. NPY arrays are read through disk memory maps; no full-grid prediction/tuning RAM buffer is used. Canonical memberships, scalers/window metadata, cell IDs, hash/row/byte manifests, [execution logs](logs/), and [artifact checksums](artifact_manifest.json) remain in Git. Every file is below the planned 80 MiB bound.
- [22,944 target summaries](reports/target_summary.csv), [3,824 aggregate summaries](reports/aggregate_summary.csv), [24,192 bootstrap rows](inference/bootstrap_results.csv), and [report inventory](reports/report_manifest.json) expose every prespecified cell, adverse result, and setting. Reproduction requires a fresh output directory and the [guarded stage commands](../../experiments/03-pca-history-surface/executed.md).

## Interpretation limits and pending work

The inherited [calibration diagnostic](inherited_calibration_diagnostics.json) remains adverse: 11/100 null rejections at nominal 5% for 87 dates, and 90%/81% coverage for nominal 95% basic intervals at 87/156 dates. It was not rerun. Mechanical correctness, a small p-value, or Holm adjustment does not repair that calibration problem. Partial pooling adds no special obstacle to resampling saved forecast losses, but these intervals do not cover coefficients, loadings, penalties, or the full repeated-training/selection pipeline.

Calibration and power studies remain deferred, as requested. The maps motivate later investigation of short-sample estimation error, slope sharing, regime sensitivity, and high-K measurement directions, but they do not establish a learned donor selector, latent-factor recovery, a universal history/factor-count optimum, or trading utility. Any empirical confirmation requires a newly designated uninspected period or market; none is claimed here.
