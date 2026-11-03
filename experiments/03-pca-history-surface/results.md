# Experiment 3: PCA dimension/history surfaces and interpretation

**Completed November 3, 2026.** Both forecast stages, all saved-loss bootstrap calculations, and the independent audits completed. **None of the 30 prespecified anchors passes the primary block-13 Holm rule in either weighting.** Dense point estimates show substantial dimension/history and period dependence; adding components or shortening history is not a general route to better forecasts. Calibration and power research remains **deferred**, and both evaluation periods were already seen.

The [execution record](executed.md), unchanged [scientific protocol](protocol.md), [source freeze](../../results/experiment-03-2026-11-03/source_freeze.json), and [preflight](../../results/experiment-03-2026-11-03/preflight.md) establish the procedure. This account interprets the complete fixed inventory; it does not choose a new K/L/rule winner.

## Evidence and inferential scope

The canonical grid contains 936 factor cells plus 20 matching-history own regressions per weighting/period. All 19 finite coefficient histories, K=1–8, three slope rules, and both PCA modes are retained. Expanding-coefficient controls are deduplicated across modes and shown as sidebands, not a twentieth finite coordinate. K=0 is the own-history reference, not a factor fit. The earlier period has 718 dates and the later period 87; **both have already informed the research**.

The [per-target table](../../results/experiment-03-2026-11-03/reports/target_summary.csv) has 22,944 cells and the [aggregate table](../../results/experiment-03-2026-11-03/reports/aggregate_summary.csv) 3,824. The [complete marginal interval table](../../results/experiment-03-2026-11-03/reports/bootstrap_summary.csv) retains all 24,192 own-gain, mode-difference, and pooling-difference rows, including both weightings, periods, and all three block settings. The [anchor table](../../results/experiment-03-2026-11-03/reports/anchor_table.csv) has all 180 later-seen anchor/block/weighting rows.

**These are approximate exploratory intervals and p-values.** Experiment 2's inherited single-comparison diagnostic had 11/100 null rejections at nominal 5% with 87 dates, and nominal-95% basic coverage of only 90/100 and 81/100 at 87/156 dates. No new calibration or power study was run. Reproducing calculations, changing K/L, or applying Holm does not establish valid marginal calibration, simultaneous surface coverage, or full-pipeline family-wise validity.

The bootstrap resamples saved scalar forecast losses; it does not refit PCA, coefficients, or historical lambda selection. Intervals are nominal-95% basic **marginal** intervals for those saved-loss statistics, not parameter intervals or simultaneous bands. Only the fixed 30 later-seen anchors receive one-sided p-values; the other surface and pooling cells have no significance stars or formal p-value family. A positive marginal interval endpoint is not a surface-wide rejection, and non-rejection is not proof of equivalence.

## Dimension, history, and sharing patterns

More PCs can worsen prediction, particularly separate-slope forecasts with the shortest histories. The following fixed grid endpoints illustrate that pattern without selecting the best cell. Entries are own-history-reference gains at **L=52, K=1 -> K=8**, in percent. Positive favors the factor cell; every baseline uses that same L.

| Period / weighting / PCA | Separate | Common | Partial |
| --- | ---: | ---: | ---: |
| earlier_seen / value / matched | 3.472 -> -7.489 | 6.127 -> 3.150 | 5.548 -> 1.046 |
| earlier_seen / value / expanding | 3.639 -> -12.492 | 6.248 -> 0.961 | 5.855 -> -0.539 |
| earlier_seen / equal / matched | 4.086 -> -5.208 | 6.032 -> 3.233 | 4.964 -> 1.144 |
| earlier_seen / equal / expanding | 4.427 -> -14.469 | 6.403 -> 0.160 | 5.324 -> -2.650 |
| later_seen / value / matched | 2.926 -> -11.240 | 3.395 -> 1.371 | 3.287 -> -0.752 |
| later_seen / value / expanding | 2.973 -> -17.440 | 3.565 -> -3.004 | 3.450 -> -2.847 |
| later_seen / equal / matched | -0.452 -> -11.261 | 2.550 -> 1.551 | 1.250 -> -1.057 |
| later_seen / equal / expanding | -0.108 -> -16.038 | 2.784 -> -1.004 | 1.356 -> -5.772 |

Pooling cushions the high-K, short-history deterioration in these examples, but partial pooling does not uniformly dominate common or separate slopes. Its lambda is historically tuned for each target/mode/L/K, rather than chosen from evaluation losses. The penalty averages over outcome industries and does not divide by K, so different K cells are a declared estimator family, not equal-total-shrinkage models.

History effects also depend on the period. In the later-seen value-weighted K=2/common/matched anchors, own-reference gains are 3.5266% at L=104, -2.0015% at L=260, and -0.7505% at L=520. Earlier-period common/partial maps are substantially more favorable over much of the grid. This is descriptive period dependence, not a newly identified structural break or proof that short windows generally help. Neighboring surface coordinates share data and fitted objects; they are not independent replications.

Matched versus expanding PCA has no universal winner. All nine value-weighted K=2 finite anchor mode differences are positive point estimates, yet none passes the primary adjusted rule. Elsewhere the high-K short-history examples show a larger deterioration under expanding PCA. Older predictor history changes the complete fitted representation and downstream regression; partial-pooling mode comparisons also include mode-specific historical lambda choices. These contrasts do not isolate a causal measurement mechanism, establish true factor recovery, or hold unknown coefficients fixed.

### Absolute accuracy and the moving own-history reference

Gain is `1 - mean_target(MSE_cell / MSE_own_L)`, not a ratio of pooled MSEs. Changing L also changes the own-history denominator. The later-seen value/common K=2 example makes the distinction explicit:

| PCA mode / coefficient history | Factor mean MSE | Own mean MSE | Equal-target own-reference gain |
| --- | ---: | ---: | ---: |
| matched / 104 | 0.751606 | 0.778176 | 3.5266% |
| expanding / 104 | 0.747593 | 0.778176 | 3.9702% |
| shared / expanding | 0.718053 | 0.724962 | 1.2290% |

The finite-104 models have larger gains against their weaker own-history reference, while the expanding-coefficient factor has lower absolute mean MSE. A larger baseline-relative surface value therefore does not by itself demonstrate a more accurate factor forecast or identify an optimal history. The absolute-MSE maps and own-baseline curves are part of the main evidence, not optional diagnostics.

### All six targets remain visible

At the fixed K=2/L=104/common anchor, later-seen gains differ by industry. Values below are relative to each target's matching own-history model. No target-specific policy was chosen using these results.

| Target | Value matched | Value expanding PCA | Equal matched | Equal expanding PCA |
| --- | ---: | ---: | ---: | ---: |
| Food | 2.7831% | 2.7448% | 1.8039% | 1.1817% |
| Mach | 4.7991% | 6.5452% | 2.8512% | 1.2667% |
| Banks | -0.5204% | 0.2871% | -2.9142% | -1.1017% |
| Oil | 6.3504% | 6.7677% | 4.2747% | 2.9466% |
| Util | -2.7830% | -3.7357% | -0.3581% | 2.0599% |
| Hlth | 10.5306% | 11.2121% | -0.1179% | 0.9170% |

Banks and Util have unfavorable matched-PCA estimates in both weightings here; Hlth supplies a large positive value-weighted gain but a slightly negative equal-weighted matched estimate. These differences limit any statement based solely on the six-target mean. All targets and every other grid cell remain in the complete CSVs.

## Every primary K=2 anchor: all 60 weighting/contrast rows

The following tables show **all** primary block-13 anchors: 21 own-gain and nine PCA-mode contrasts per weighting. The 21 own gains include three shared expanding-coefficient controls, counted once. Each weighting has **one Holm family of 30**, combining own and mode contrasts. No earlier-seen p-values or nonanchor p-values were produced.

For own gains, values and intervals are percentages relative to matching-L own history. For mode contrasts, values and intervals are **percentage-point differences** `G_expandingPCA_own - G_matchedPCA_own`; positive favors expanding PCA. This is not a new ratio of expanding-PCA to matched-PCA loss. All intervals below are nominal basic marginal intervals, and all p-values retain the calibration limitation above. Display rounding does not determine the strict adjusted-p < 0.05 decision.

### Value-weighted primary: own-history-reference gains

| PCA mode | L | Slope rule | Gain % | Basic interval % | Raw p | Holm p |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| matched | 104 | separate | 3.1481 | [-3.1930, 12.3379] | 0.1874 | 1.0000 |
| matched | 104 | common | 3.5266 | [-3.1794, 12.1786] | 0.1692 | 1.0000 |
| matched | 104 | partial | 3.0129 | [-3.7138, 12.2519] | 0.2042 | 1.0000 |
| expanding | 104 | separate | 3.8548 | [-2.8415, 13.7931] | 0.1551 | 1.0000 |
| expanding | 104 | common | 3.9702 | [-3.2043, 13.1434] | 0.1568 | 1.0000 |
| expanding | 104 | partial | 3.7148 | [-3.4473, 13.4082] | 0.1724 | 1.0000 |
| matched | 260 | separate | -2.8736 | [-6.4596, 1.5885] | 0.8946 | 1.0000 |
| matched | 260 | common | -2.0015 | [-5.5957, 2.3972] | 0.8123 | 1.0000 |
| matched | 260 | partial | -1.8920 | [-5.3696, 2.4675] | 0.7984 | 1.0000 |
| expanding | 260 | separate | -2.2803 | [-6.6822, 3.4385] | 0.7823 | 1.0000 |
| expanding | 260 | common | -1.7532 | [-6.3574, 3.7658] | 0.7236 | 1.0000 |
| expanding | 260 | partial | -1.7654 | [-6.2136, 3.8529] | 0.7277 | 1.0000 |
| matched | 520 | separate | -2.2160 | [-6.8474, 3.4496] | 0.7689 | 1.0000 |
| matched | 520 | common | -0.7505 | [-4.9203, 4.4955] | 0.6103 | 1.0000 |
| matched | 520 | partial | -0.8813 | [-5.1196, 4.4144] | 0.6182 | 1.0000 |
| expanding | 520 | separate | -1.6519 | [-6.0900, 3.7716] | 0.7172 | 1.0000 |
| expanding | 520 | common | -0.4070 | [-4.4942, 4.7279] | 0.5570 | 1.0000 |
| expanding | 520 | partial | -0.6528 | [-4.8705, 4.5738] | 0.5861 | 1.0000 |
| shared | expanding | separate | -0.0330 | [-2.8349, 3.3564] | 0.4967 | 1.0000 |
| shared | expanding | common | 1.2290 | [-1.1238, 4.1628] | 0.1596 | 1.0000 |
| shared | expanding | partial | 0.9066 | [-1.5843, 3.9440] | 0.2349 | 1.0000 |

### Value-weighted primary: expanding-PCA minus matched-PCA gain

| L | Slope rule | Difference, pp | Basic interval, pp | Raw p | Holm p |
| --- | --- | ---: | ---: | ---: | ---: |
| 104 | separate | 0.7068 | [-0.2839, 2.0336] | 0.0903 | 1.0000 |
| 104 | common | 0.4435 | [-0.3722, 1.4957] | 0.1582 | 1.0000 |
| 104 | partial | 0.7019 | [-0.1194, 1.7864] | 0.0510 | 1.0000 |
| 260 | separate | 0.5933 | [-1.5492, 2.8105] | 0.2894 | 1.0000 |
| 260 | common | 0.2484 | [-2.2327, 2.7447] | 0.4118 | 1.0000 |
| 260 | partial | 0.1266 | [-2.3115, 2.5607] | 0.4485 | 1.0000 |
| 520 | separate | 0.5640 | [0.0635, 0.9995] | 0.0134 | 0.4020 |
| 520 | common | 0.3434 | [-0.1679, 0.8074] | 0.0805 | 1.0000 |
| 520 | partial | 0.2286 | [-0.2781, 0.6745] | 0.1616 | 1.0000 |

### Equal-weighted robustness: own-history-reference gains

| PCA mode | L | Slope rule | Gain % | Basic interval % | Raw p | Holm p |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| matched | 104 | separate | -0.6029 | [-4.0905, 3.0308] | 0.6596 | 1.0000 |
| matched | 104 | common | 0.9233 | [-1.9982, 3.5008] | 0.2683 | 1.0000 |
| matched | 104 | partial | -1.5541 | [-4.8098, 1.6133] | 0.8254 | 1.0000 |
| expanding | 104 | separate | -1.0909 | [-4.6492, 2.5386] | 0.6927 | 1.0000 |
| expanding | 104 | common | 1.2117 | [-1.1321, 3.4223] | 0.1593 | 1.0000 |
| expanding | 104 | partial | -0.2139 | [-3.2771, 3.0411] | 0.5359 | 1.0000 |
| matched | 260 | separate | 1.2410 | [-1.1332, 4.2030] | 0.1362 | 1.0000 |
| matched | 260 | common | 1.7784 | [-0.3015, 3.9984] | 0.0469 | 1.0000 |
| matched | 260 | partial | 1.1698 | [-1.2724, 3.9969] | 0.1588 | 1.0000 |
| expanding | 260 | separate | -0.1105 | [-2.4657, 2.8058] | 0.4831 | 1.0000 |
| expanding | 260 | common | 1.3211 | [-0.6632, 3.3778] | 0.0870 | 1.0000 |
| expanding | 260 | partial | 0.4562 | [-2.0977, 3.1772] | 0.3218 | 1.0000 |
| matched | 520 | separate | 1.0124 | [-2.1113, 4.8664] | 0.2333 | 1.0000 |
| matched | 520 | common | 1.2063 | [-2.0514, 4.9457] | 0.2163 | 1.0000 |
| matched | 520 | partial | 1.8912 | [-1.0167, 5.2308] | 0.0881 | 1.0000 |
| expanding | 520 | separate | 1.1203 | [-2.3309, 5.1661] | 0.2423 | 1.0000 |
| expanding | 520 | common | 1.1786 | [-2.3100, 5.1597] | 0.2389 | 1.0000 |
| expanding | 520 | partial | 1.3837 | [-1.9882, 5.1507] | 0.1933 | 1.0000 |
| shared | expanding | separate | 2.7190 | [0.3657, 5.4765] | 0.0132 | 0.3564 |
| shared | expanding | common | 3.0071 | [0.7922, 5.5306] | 0.0058 | 0.1682 |
| shared | expanding | partial | 2.9886 | [0.6476, 5.6667] | 0.0075 | 0.2100 |

### Equal-weighted robustness: expanding-PCA minus matched-PCA gain

| L | Slope rule | Difference, pp | Basic interval, pp | Raw p | Holm p |
| --- | --- | ---: | ---: | ---: | ---: |
| 104 | separate | -0.4879 | [-1.5325, 1.4540] | 0.7054 | 1.0000 |
| 104 | common | 0.2884 | [-0.9125, 1.3044] | 0.2833 | 1.0000 |
| 104 | partial | 1.3401 | [0.4108, 2.5832] | 0.0039 | 0.1170 |
| 260 | separate | -1.3515 | [-2.7202, 0.4372] | 0.9350 | 1.0000 |
| 260 | common | -0.4573 | [-1.6741, 1.0843] | 0.7450 | 1.0000 |
| 260 | partial | -0.7136 | [-1.9905, 1.0827] | 0.8090 | 1.0000 |
| 520 | separate | 0.1079 | [-0.8854, 1.0830] | 0.4211 | 1.0000 |
| 520 | common | -0.0278 | [-0.6992, 0.7340] | 0.5413 | 1.0000 |
| 520 | partial | -0.5075 | [-1.5144, 0.5647] | 0.8252 | 1.0000 |

No row crosses the primary Holm threshold in either weighting. For example, the value separate-slope L=520 mode difference has a positive marginal interval and raw p=0.0134, but adjusted p=0.4020. Equal partial L=104 has mode difference +1.3401 pp and raw p=0.0039, but adjusted p=0.1170. Equal expanding-coefficient common slopes have positive own gain 3.0071%, but adjusted p=0.1682. Marginal intervals, raw tails, and family-adjusted decisions are different quantities.

### Every prescribed block setting

| Weighting | Block 6 | Primary block 13 | Block 26 |
| --- | --- | --- | --- |
| Value | No adjusted rejection | No adjusted rejection | No adjusted rejection |
| Equal | No adjusted rejection | No adjusted rejection | Two adjusted rejections, detailed below |

Only at block 26, equal-weighted partial L=104's PCA-mode contrast passes the declared approximate rule: +1.3401 pp, marginal interval [0.5709, 2.4132] pp, raw p=0.0010, Holm p=0.0300. The equal shared expanding/common own gain also passes there: 3.0071%, interval [1.1994%, 5.1249%], raw p=0.0010, Holm p=0.0300. These are prespecified sensitivities, not replacements for primary block 13. There is no minimum-p block selection or combined across-block/weighting error-control claim.

## What the experiment establishes, and what remains open

The completed maps show finite-sample prediction consequences of these fixed dimension, history, and sharing rules. Short-history high-dimensional separate regression can deteriorate sharply; pooling can reduce that deterioration, while partial pooling is not uniformly best. The relative performance of history lengths and representations changes across seen periods. None of the fixed primary anchors supplies an adjusted threshold crossing, and the later period is short. These results do not establish equivalence or a universally favorable K/L configuration.

The experiment does not select a future policy, demonstrate a learned donor selector, identify latent economic factors, or evaluate returns, intraday/latent variance, QLIKE, trading utility, or transaction costs. All measurement industries are fixed at 48; the design varies history/PC count/sharing rather than donor membership. Further mechanism, calibration, and power research remains deferred. Even the two sensitivity threshold crossings do not overcome the inherited finite-sample diagnostic or become confirmatory evidence on already-seen outcomes.

## Complete artifacts and all 19 figures

Every figure has PNG and PDF versions. Paired modes share color limits and zero references; controls appear as separate sidebands. Gain maps are normalized to matching-L own history, absolute-MSE maps use squared-log loss, and contrast maps show common-baseline percentage-point differences. Color is not an unadjusted significance marker.

| Period / weighting | Gain surfaces | Absolute MSE + own baselines | PCA-mode differences | Pooling differences |
| --- | --- | --- | --- | --- |
| earlier_seen / value | [PNG](../../results/experiment-03-2026-11-03/reports/earlier_seen_value_gain.png) / [PDF](../../results/experiment-03-2026-11-03/reports/earlier_seen_value_gain.pdf) | [PNG](../../results/experiment-03-2026-11-03/reports/earlier_seen_value_absolute_mse.png) / [PDF](../../results/experiment-03-2026-11-03/reports/earlier_seen_value_absolute_mse.pdf) | [PNG](../../results/experiment-03-2026-11-03/reports/earlier_seen_value_pca_mode_difference.png) / [PDF](../../results/experiment-03-2026-11-03/reports/earlier_seen_value_pca_mode_difference.pdf) | [PNG](../../results/experiment-03-2026-11-03/reports/earlier_seen_value_pooling_difference.png) / [PDF](../../results/experiment-03-2026-11-03/reports/earlier_seen_value_pooling_difference.pdf) |
| earlier_seen / equal | [PNG](../../results/experiment-03-2026-11-03/reports/earlier_seen_equal_gain.png) / [PDF](../../results/experiment-03-2026-11-03/reports/earlier_seen_equal_gain.pdf) | [PNG](../../results/experiment-03-2026-11-03/reports/earlier_seen_equal_absolute_mse.png) / [PDF](../../results/experiment-03-2026-11-03/reports/earlier_seen_equal_absolute_mse.pdf) | [PNG](../../results/experiment-03-2026-11-03/reports/earlier_seen_equal_pca_mode_difference.png) / [PDF](../../results/experiment-03-2026-11-03/reports/earlier_seen_equal_pca_mode_difference.pdf) | [PNG](../../results/experiment-03-2026-11-03/reports/earlier_seen_equal_pooling_difference.png) / [PDF](../../results/experiment-03-2026-11-03/reports/earlier_seen_equal_pooling_difference.pdf) |
| later_seen / value | [PNG](../../results/experiment-03-2026-11-03/reports/later_seen_value_gain.png) / [PDF](../../results/experiment-03-2026-11-03/reports/later_seen_value_gain.pdf) | [PNG](../../results/experiment-03-2026-11-03/reports/later_seen_value_absolute_mse.png) / [PDF](../../results/experiment-03-2026-11-03/reports/later_seen_value_absolute_mse.pdf) | [PNG](../../results/experiment-03-2026-11-03/reports/later_seen_value_pca_mode_difference.png) / [PDF](../../results/experiment-03-2026-11-03/reports/later_seen_value_pca_mode_difference.pdf) | [PNG](../../results/experiment-03-2026-11-03/reports/later_seen_value_pooling_difference.png) / [PDF](../../results/experiment-03-2026-11-03/reports/later_seen_value_pooling_difference.pdf) |
| later_seen / equal | [PNG](../../results/experiment-03-2026-11-03/reports/later_seen_equal_gain.png) / [PDF](../../results/experiment-03-2026-11-03/reports/later_seen_equal_gain.pdf) | [PNG](../../results/experiment-03-2026-11-03/reports/later_seen_equal_absolute_mse.png) / [PDF](../../results/experiment-03-2026-11-03/reports/later_seen_equal_absolute_mse.pdf) | [PNG](../../results/experiment-03-2026-11-03/reports/later_seen_equal_pca_mode_difference.png) / [PDF](../../results/experiment-03-2026-11-03/reports/later_seen_equal_pca_mode_difference.pdf) | [PNG](../../results/experiment-03-2026-11-03/reports/later_seen_equal_pooling_difference.png) / [PDF](../../results/experiment-03-2026-11-03/reports/later_seen_equal_pooling_difference.pdf) |

The remaining three figure pairs retain all 30 anchors and all sensitivity settings:

- Value anchor forest: [PNG](../../results/experiment-03-2026-11-03/reports/later_seen_value_anchor_forest.png) / [PDF](../../results/experiment-03-2026-11-03/reports/later_seen_value_anchor_forest.pdf).
- Equal anchor forest: [PNG](../../results/experiment-03-2026-11-03/reports/later_seen_equal_anchor_forest.png) / [PDF](../../results/experiment-03-2026-11-03/reports/later_seen_equal_anchor_forest.pdf).
- All-anchor block sensitivity: [PNG](../../results/experiment-03-2026-11-03/reports/later_seen_anchor_block_sensitivity.png) / [PDF](../../results/experiment-03-2026-11-03/reports/later_seen_anchor_block_sensitivity.pdf).

The [report manifest](../../results/experiment-03-2026-11-03/reports/report_manifest.json) records all table/figure counts and interpretation labels; the [report checksums](../../results/experiment-03-2026-11-03/reports/stage_manifest.json) identify the exact delivered files. The [earlier forecast audit](../../results/experiment-03-2026-11-03/audit_earlier_seen.json), [later forecast audit](../../results/experiment-03-2026-11-03/audit_later_seen.json), [original-estimator oracle checks](../../results/experiment-03-2026-11-03/audit_original_estimator_oracles.json), and [complete inference audit](../../results/experiment-03-2026-11-03/audit_inference.json) passed. Independent inference reconstruction checked all 24,192 rows, six joint index matrices, 180 anchor tail counts, and six Holm families, with maximum effect/interval difference 1.1103e-16. This verifies saved computations, not statistical calibration or economic generality.
