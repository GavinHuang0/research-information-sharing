# Experiment 2: bootstrap inference and coefficient history

Completed November 1, 2026. The factor policy remains the Experiment 1 development-selected two-PC, common-slope model with all 48 measurement and outcome industries. Food, Mach, Banks, Oil, Util, and Hlth are the six fixed evaluation targets. No new policy or history was selected using final results.

**The new 2025-2026 period does not establish an advantage over own-history regression or ridge under the primary block-13, Holm-19 analysis.** The 104-pair factor has favorable adjusted comparisons against elastic net and PLS, but no finite coefficient history has a favorable adjusted comparison against the expanding factor. All statements concern these fixed targets' squared log-variance forecast losses.

## Statistical limitation

**Nominal finite-sample calibration was not established.** Before empirical execution, a bounded stationary synthetic loss-process diagnostic used 100 Monte Carlo replications per setting and 499 bootstrap draws. At T=87 it rejected the equal-marginal null in 11/100 cases at a nominal 5% level (Wilson interval 6.25%-18.63%). Nominal 95% basic interval coverage was 90/100 at T=87 and 81/100 at T=156. At T=156 null rejection was 6/100. These are material adverse diagnostics, not evidence that all empirical tests are calibrated.

The diagnostic did not calibrate Holm families or the full generated-factor, tuned, rolling/expanding forecast pipeline. Holm adjustment cannot repair miscalibrated marginal p-values. Consequently, the p-values below are **planned approximate evidence** and the intervals are nominal marginal basic intervals, not demonstrated 95%-coverage or simultaneous intervals. More bootstrap draws reduce resampling noise, not this calibration problem. The declared empirical seed, block length, and procedures were retained; no favorable setting was selected in response to the diagnostic. See the complete [synthetic record](synthetic_validation.json) and [preflight](preflight.md).

## Frozen procedures and execution evidence

- [Original protocol](protocol.md), [original planning configuration](planning_config.toml), [executed configuration](config.toml), and [18-policy inventory](policies.json). The executable configuration preserves every scientific section of the original plan.
- Implementation commit `750dd8d` preceded the initial [code/configuration/input freeze](protocol_freeze.json), committed as `c48482a` before empirical execution. The freeze records LF-normalized source fingerprints and pinned package versions.
- Part A resampled the already inspected Experiment 1 final losses; it is exploratory. All 36 files in that original archive remained unchanged.
- Part B development contains 718 response dates, April 1, 2011-December 27, 2024. Its 620,352 predictions and 48,384 tuning records were audited and committed with the [pre-final freeze](final_freeze.json) as `2c15048` at 04:53:01 UTC, before final-stage start at 04:53:07.718 UTC. All 33,696 overlapping 2022-2024 expanding-history forecast records reproduce Experiment 1 exactly, maximum absolute difference zero.
- Part B final contains 87 response dates, January 3, 2025-August 28, 2026; 75,168 predictions and 6,048 tuning records. First final index 1290 reuses anchor 1287, whose last fitted response is December 6, 2024. Boundary tuning is identical to the development replay; refits never restart at the final boundary.
- The archived [daily inputs](metadata.json) are the original October 16, 2026 snapshot. The common calendar has 1,377 eligible pairs after causal features, calendar bounds, and joint complete-case filtering. Weekly Q is the sum of daily decimal return squares, with at least three observations; the response is next calendar week's log(Q+1e-8). Current/four-/twelve-week own-history log controls remain fixed.
- At anchor a=572+13k, b=a-52. Inner PCA uses X[0:b), outer PCA X[0:a), shared across factor histories and outcome restrictions. Supervised inner/outer windows are [b-L:b) and [a-L:a), or start at zero for expanding. Every donor/target nuisance coefficient, direct-model scaler/projection, and supervised PLS fit follows L. The last 52 historical pairs choose penalties by target validation MSE, with the original grids and first-declared tie rule.
- The final period was unscored in the inspected repository and Git history at freeze. This is bounded repository evidence, not proof that nobody inspected unsaved or external results. The source's January 2025 CIZ change is a data-vintage limitation, not an assumed time-series breakpoint.

The [91-test validation log](validation.txt), [Part A audit](audit_part_a.json), [development audit](audit_development.json), [final audit](audit_final.json), and [Part B audit](audit_part_b.json) are preserved. Audits reconstructed actuals from daily data, checked windows/memberships/penalty choices, recomputed losses and summaries, and independently rebuilt every bootstrap index matrix and inferential result. Fitting took 404.88 seconds for development and 52.48 seconds for final, excluding serialization/reporting. There were 448 and 56 PCA fits respectively, shared across coefficient histories.

## Statistic and inference

For candidate F and the named reference R, G = 1 - (1/6) sum_i [MSE(F_i)/MSE(R_i)]. Positive favors F. It is an equal-target mean of ratios, not a ratio of pooled losses or the difference between improvements against another baseline. Absolute mean MSEs below are descriptive and can rank histories differently because the primary statistic weights target-specific reference ratios.

The paired stationary bootstrap resamples complete date vectors jointly across all targets, policies, histories, and both weightings. Each part/block setting has one shared PCG64 index matrix, seed 20261031, 9,999 draws. Expected block length 13 is primary; 6 and 26 are fixed sensitivities. Both numerator and denominator MSEs are recomputed per draw. No models are refitted inside bootstrap draws.

With D_b=G_b-G_hat, the one-sided p-value is (1+count[D_b>=G_hat])/(9999+1), including ties. Basic interval endpoints are [2G_hat-q_0.975(G_b), 2G_hat-q_0.025(G_b)], using linear quantiles without clipping. Zero/nonfinite denominators cause deterministic failure, not epsilon substitution or dropped draws. No such failures occurred.

Part A adjusts four fixed reference comparisons per weighting/block setting. Part B adjusts all 16 factor-versus-matched-history-reference tests and three finite-versus-expanding factor tests together: Holm family 19. Equal weighting is a separate robustness family; there is no combined across-weighting or block-setting error-control claim. Confidence intervals are marginal, so a positive interval does not imply an adjusted rejection.

## Part A: exploratory 2022-2024 inference

| Weighting | Reference | G % | Nominal basic 95% interval | Raw p | Holm-4 p |
| --- | --- | --- | --- | --- | --- |
| value | Own history | 4.273 | [1.714, 6.917] | 0.0007 | 0.0028 |
| value | Ridge | 1.417 | [-0.068, 2.940] | 0.0305 | 0.0915 |
| value | Elastic net | 1.848 | [-0.196, 3.926] | 0.0393 | 0.0915 |
| value | PLS | 1.179 | [-0.948, 3.554] | 0.1407 | 0.1407 |
| equal | Own history | 1.656 | [-0.135, 3.867] | 0.0372 | 0.1488 |
| equal | Ridge | -0.770 | [-2.170, 0.712] | 0.8429 | 1.0000 |
| equal | Elastic net | -0.636 | [-2.409, 1.200] | 0.7436 | 1.0000 |
| equal | PLS | 0.030 | [-1.880, 2.005] | 0.4822 | 1.0000 |

Only the value-weighted own-history comparison passes the planned adjusted threshold. No direct-method advantage survives Holm adjustment; no equal-weighted comparison does. Blocks 6 and 26 preserve that adjusted conclusion. These losses already informed the research; the bootstrap does not turn them into a fresh holdout.

## Part B: all primary new-period comparisons

The candidate is the same fixed factor policy throughout. References use the candidate's coefficient history, except the dedicated history tests whose reference is the expanding factor. The following tables retain every primary contrast in declared order. G and interval endpoints are percentages; pH is Holm-19 adjusted.

### Value weighting

| Candidate history | Reference | G % | Nominal basic 95% interval | Raw p | pH |
| --- | --- | --- | --- | --- | --- |
| 104 | Own history | 3.970 | [-3.381, 13.233] | 0.1564 | 1.0000 |
| 104 | Ridge | 2.799 | [-0.987, 7.269] | 0.0764 | 1.0000 |
| 104 | Elastic net | 8.570 | [4.398, 13.410] | 0.0001 | 0.0019 |
| 104 | PLS | 13.740 | [8.108, 20.446] | 0.0001 | 0.0019 |
| 260 | Own history | -1.753 | [-6.407, 3.982] | 0.7262 | 1.0000 |
| 260 | Ridge | -0.281 | [-3.710, 3.643] | 0.5513 | 1.0000 |
| 260 | Elastic net | -0.163 | [-4.231, 4.028] | 0.5121 | 1.0000 |
| 260 | PLS | 7.504 | [2.102, 12.965] | 0.0037 | 0.0629 |
| 520 | Own history | -0.407 | [-4.501, 4.807] | 0.5615 | 1.0000 |
| 520 | Ridge | -0.937 | [-3.503, 2.173] | 0.7141 | 1.0000 |
| 520 | Elastic net | 1.217 | [-1.108, 4.130] | 0.1301 | 1.0000 |
| 520 | PLS | 3.385 | [-1.684, 8.997] | 0.0965 | 1.0000 |
| expanding | Own history | 1.229 | [-1.092, 4.215] | 0.1623 | 1.0000 |
| expanding | Ridge | 1.963 | [-0.327, 4.301] | 0.0479 | 0.7664 |
| expanding | Elastic net | 0.796 | [-1.856, 3.617] | 0.2708 | 1.0000 |
| expanding | PLS | 2.209 | [-1.525, 6.052] | 0.1200 | 1.0000 |
| 104 | Expanding factor | -4.090 | [-10.034, 2.367] | 0.9051 | 1.0000 |
| 260 | Expanding factor | -1.045 | [-5.527, 4.684] | 0.6608 | 1.0000 |
| 520 | Expanding factor | -1.082 | [-3.683, 2.065] | 0.7606 | 1.0000 |

### Equal weighting

| Candidate history | Reference | G % | Nominal basic 95% interval | Raw p | pH |
| --- | --- | --- | --- | --- | --- |
| 104 | Own history | 1.212 | [-1.105, 3.424] | 0.1569 | 1.0000 |
| 104 | Ridge | 2.086 | [0.620, 3.644] | 0.0040 | 0.0640 |
| 104 | Elastic net | 9.914 | [4.714, 15.039] | 0.0002 | 0.0036 |
| 104 | PLS | 19.921 | [13.568, 25.752] | 0.0001 | 0.0019 |
| 260 | Own history | 1.321 | [-0.676, 3.384] | 0.0876 | 0.9636 |
| 260 | Ridge | 1.007 | [-0.832, 2.770] | 0.1417 | 1.0000 |
| 260 | Elastic net | 2.091 | [0.010, 4.516] | 0.0247 | 0.3211 |
| 260 | PLS | 9.097 | [3.976, 13.285] | 0.0007 | 0.0119 |
| 520 | Own history | 1.179 | [-2.443, 5.109] | 0.2391 | 1.0000 |
| 520 | Ridge | -0.104 | [-2.190, 2.714] | 0.4951 | 1.0000 |
| 520 | Elastic net | 1.966 | [-0.118, 4.818] | 0.0326 | 0.3912 |
| 520 | PLS | 4.009 | [0.827, 7.503] | 0.0076 | 0.1064 |
| expanding | Own history | 3.007 | [0.751, 5.527] | 0.0062 | 0.0930 |
| expanding | Ridge | 0.445 | [-1.224, 2.631] | 0.2584 | 1.0000 |
| expanding | Elastic net | 0.858 | [-1.426, 3.498] | 0.1995 | 1.0000 |
| expanding | PLS | 0.990 | [-1.479, 3.978] | 0.2004 | 1.0000 |
| 104 | Expanding factor | -2.229 | [-7.273, 2.848] | 0.8288 | 1.0000 |
| 260 | Expanding factor | 0.490 | [-2.044, 3.223] | 0.3480 | 1.0000 |
| 520 | Expanding factor | -1.200 | [-3.449, 1.282] | 0.8276 | 1.0000 |

At block 13, favorable adjusted comparisons are L=104 versus elastic net and PLS in both weightings, plus equal-weighted L=260 versus PLS. No own-history or ridge comparison passes in either weighting. In particular, value-weighted expanding versus ridge has raw p=0.0479 but adjusted p=0.7664. Non-rejection does not establish equivalence, or prove the reverse superiority claim.

## History effects and target heterogeneity

| Weighting | History | Mean factor MSE | Mean own-history MSE | Factor gain vs own % |
| --- | --- | --- | --- | --- |
| value | 104 | 0.747593 | 0.778176 | 3.970 |
| value | 260 | 0.724454 | 0.711489 | -1.753 |
| value | 520 | 0.725519 | 0.720809 | -0.407 |
| value | expanding | 0.718053 | 0.724962 | 1.229 |
| equal | 104 | 0.857791 | 0.866615 | 1.212 |
| equal | 260 | 0.833710 | 0.845367 | 1.321 |
| equal | 520 | 0.849136 | 0.862775 | 1.179 |
| equal | expanding | 0.838642 | 0.866879 | 3.007 |

The value-weighted L=104 gain against its own-history reference is 3.97%, greater than expanding's 1.23%, but its factor mean MSE is higher: 0.74759 versus 0.71805. Its own-history reference also worsens, from 0.72496 expanding to 0.77818 at L=104. A larger gain against a weaker matched reference does not show that discarding history improves factor forecasts. The direct factor comparisons give value-weighted G=-4.09%, -1.05%, and -1.08% for L=104/260/520 versus expanding, all adjusted p=1. Equal-weighted effects are -2.23%, +0.49%, and -1.20%, also adjusted p=1. No dedicated history test rejects under any block setting.

### Every target: factor gain versus matching own history

**Value weighting**

| Target | L=104 % | L=260 % | L=520 % | Expanding % |
| --- | --- | --- | --- | --- |
| Food | 2.745 | 1.045 | 3.312 | 1.355 |
| Mach | 6.545 | 0.338 | -3.341 | -3.017 |
| Banks | 0.287 | -6.447 | -5.139 | -2.389 |
| Oil | 6.768 | -0.361 | 0.295 | 4.497 |
| Util | -3.736 | -6.960 | -1.334 | 0.599 |
| Hlth | 11.212 | 1.866 | 3.765 | 6.329 |

**Equal weighting**

| Target | L=104 % | L=260 % | L=520 % | Expanding % |
| --- | --- | --- | --- | --- |
| Food | 1.182 | 4.121 | 6.499 | 6.380 |
| Mach | 1.267 | 0.815 | 3.982 | 2.654 |
| Banks | -1.102 | -0.164 | 1.220 | 2.386 |
| Oil | 2.947 | 2.721 | -2.835 | 2.452 |
| Util | 2.060 | 0.818 | -2.139 | 0.285 |
| Hlth | 0.917 | -0.384 | 0.344 | 3.887 |

Adverse primary outcomes include expanding-history Banks and Mach, with 2.39% and 3.02% higher MSE than own history. Every equal-weighted expanding target improves in point estimate, but the aggregate own-history comparison still lacks a primary Holm-19 rejection.

## What this says about the research question

The primary history tests hold measurement donors and outcome donors at all 48. They assess coefficient-history sensitivity of a fixed representation/sharing rule, not whether separate donor selection improves forecasts. Factor-versus-own-history differences combine representation and sharing; attributing them specifically to pooling would require a same-M, same-L pooled-versus-separate contrast.

The complete descriptive grid provides that comparison without a new formal test: value-weighted pooling's extra own-baseline-relative gain over separate all-48 factor slopes is 0.12 percentage points at L=104, versus 1.26 points expanding. Equal weighting shows a larger increment at L=104 (2.30 points) than expanding (0.29 points). Thus there is no uniform result that shorter histories make pooling more useful. These are differences of scores against the same baseline, not the directly normalized G statistic used for the formal reference tests. Fixed-six outcome restriction does not improve the pooled primary aggregate over all-48 sharing at any history in either weighting. No learned donor selector or mechanism has been established.

Block-6 adjusted rejection sets match block 13. Block 26 additionally flags value L=260 versus PLS (pH=0.0170), equal L=104 versus ridge (0.0165), equal L=520 versus PLS (0.0224), and equal expanding versus own history (0.0160). These secondary sensitivities cannot replace the primary block-13 analysis. The [complete uncertainty tables](reports/part_b_inference.csv) and [sensitivity figure](reports/block_length_sensitivity.pdf) retain them all.

The next statistical experiment should calibrate size and coverage under several dependent/heavy-tailed loss processes and full forecasting simulations before stronger significance claims. A controlled design varying measurement noise and slope heterogeneity can then address the central M/O mechanism. Any later empirical confirmation needs a newly designated period or market; 2022-2026 has now been inspected. Trading utility, costs, and latent conditional-variance accuracy remain unevaluated.

## Artifact guide and reproduction

- [Complete 1,728-row target table](reports/target_summary.csv) and [288-row aggregate table](reports/aggregate_summary.csv): every history, policy, weighting, and stage; MSE/MAE and matched-baseline ratios. Persistence is duplicated across history labels and is not four independent procedures.
- [Part A inference](part_a/bootstrap_results.csv), [Part B inference](part_b/bootstrap_results.csv), plus compressed resampling matrices and index manifests inside each folder. All 24 Part A and 114 Part B rows are retained.
- Compressed [development predictions](development/predictions.csv.gz) / [tuning](development/tuning.jsonl.gz), and [final predictions](final/predictions.csv.gz) / [tuning](final/tuning.jsonl.gz). [Execution logs](logs/) and stage manifests retain the chronological record.
- Figures, each in PNG and PDF: [Part A](reports/part_a_fixed_forecast_uncertainty.pdf), [Part B references](reports/part_b_factor_vs_references.pdf), [direct history tests](reports/part_b_finite_vs_expanding.pdf), [all history curves](reports/history_loss_curves.pdf), [every target](reports/final_target_history_improvement.pdf), [block sensitivity](reports/block_length_sensitivity.pdf).
- [Artifact checksums](artifact_manifest.json), [metadata](metadata.json), and [precise execution/reproduction instructions](../../experiments/02-bootstrap-history/executed.md). Original plans/protocols and Experiment 1 outputs remain unchanged. Reproductions use a new output directory; no original stage is overwritten.
