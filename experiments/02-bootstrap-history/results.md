# Experiment 2: results and interpretation

**Status: completed November 1, 2026.** Part A, development/final forecasts, and all Part B bootstrap comparisons passed independent saved-output audits. The main finding is limited: the short-history factor procedure beats some direct references under the declared approximate rejection rule, but no history beats matched own history or ridge in the primary final analysis, and no finite history beats the expanding factor control. The adverse calibration limitation below remains essential. See the [execution account](executed.md), unchanged [scientific protocol](protocol.md), and [run preflight](../../results/experiment-02-2026-11-01/preflight.md).

## Inferential limitation that applies to every result

The bounded synthetic diagnostic did **not** establish nominal finite-sample calibration. It showed adverse null rejection and basic-interval coverage behavior even in a stationary synthetic loss setting. Those checks did not calibrate the four-/nineteen-comparison Holm families or the complete learned forecasting pipeline. Implementation tests and a reproducible bootstrap do not remove this limitation. Holm adjustment cannot repair unestablished marginal p-value calibration.

All p-values and intervals below are therefore approximate, with adverse calibration evidence, not validated exact tests or demonstrated nominal-coverage intervals. The already inspected Part A period remains exploratory. A small adjusted p-value does not justify suppressing this warning, claiming universal factor superiority, or interpreting a statistical result as a latent-variance or trading result.

In the bounded diagnostic, single-comparison nominal-5% null rejection was 11/100 at 87 dates and 6/100 at 156 dates; nominal-95% basic-interval coverage was only 90/100 and 81/100. These Monte Carlo rates have uncertainty, concern stationary synthetic loss processes rather than learned models, and use fewer bootstrap draws than the empirical run. More empirical draws do not establish calibration. The complete [diagnostic and its uncertainty](../../results/experiment-02-2026-11-01/synthetic_validation.json) remain part of the evidence.

## Part A: saved first-pilot forecast uncertainty

The factor candidate remains the first pilot's development-selected common-slope policy with all 48 measurement and outcome industries. Comparators are the fixed all-48 ridge, elastic-net, and PLS policies and own history. The independent [Part A audit](../../results/experiment-02-2026-11-01/audit_part_a.json) reconstructed the joint bootstrap indices and checked all 24 saved comparison/block/weighting rows, both ratio denominators, centered-root tail counts, basic intervals, and Holm adjustments.

Primary expected block length is 13 dates. Positive effects favor the factor procedure relative to the **named reference**. Intervals below are marginal nominal-95% basic intervals; raw p-values are one-sided, and adjusted p-values use a separate four-comparison Holm family for each weighting. The calibration warning above applies to every entry.

| Weighting | Reference | Gain | Basic interval | Raw p | Holm p |
| --- | --- | ---: | ---: | ---: | ---: |
| Value | Own history | 4.2733% | [1.7137%, 6.9169%] | 0.0007 | 0.0028 |
| Value | Ridge | 1.4167% | [-0.0683%, 2.9399%] | 0.0305 | 0.0915 |
| Value | Elastic net | 1.8485% | [-0.1964%, 3.9263%] | 0.0393 | 0.0915 |
| Value | PLS | 1.1789% | [-0.9482%, 3.5543%] | 0.1407 | 0.1407 |
| Equal | Own history | 1.6562% | [-0.1352%, 3.8675%] | 0.0372 | 0.1488 |
| Equal | Ridge | -0.7702% | [-2.1704%, 0.7123%] | 0.8429 | 1.0000 |
| Equal | Elastic net | -0.6361% | [-2.4089%, 1.2004%] | 0.7436 | 1.0000 |
| Equal | PLS | 0.0300% | [-1.8804%, 2.0047%] | 0.4822 | 1.0000 |

Only the value-weighted comparison with own history passes the declared Holm-0.05 rejection rule. None of the three primary direct-method comparisons, and none of the equal-weighted comparisons, passes. This adjusted-rejection pattern is unchanged at the fixed block-length sensitivities 6 and 26. Marginal intervals can exclude zero while the Holm family does not reject; they are not interchangeable criteria. See the [complete saved inference](../../results/experiment-02-2026-11-01/part_a/bootstrap_results.csv) for every sensitivity row.

No new forecasts or winner selection were used for Part A. Its saved 2022–2024 losses had already been examined, so this remains exploratory post-pilot inference rather than an untouched holdout or a demonstrated nominal-size test. Gains versus ridge/elastic net/PLS are recomputed target-wise ratios to those methods, not differences between their own-history improvement percentages.

## Part B: coefficient histories and fixed references

The primary factor procedure is held fixed across all four supervised history rules. Each own-history/ridge/elastic-net/PLS reference uses the factor candidate's coefficient history. Predictor-only PCA remains expanding and common across **factor history/outcome-restriction variants**. Direct models do not use that PCA: their nuisance fits, scalers, and supervised PLS directions use their own matched L. The [complete target table](../../results/experiment-02-2026-11-01/reports/target_summary.csv) contains all 1,728 stage/weighting/history/policy/target cells, and the [aggregate table](../../results/experiment-02-2026-11-01/reports/aggregate_summary.csv) all 288 corresponding aggregate cells, without reselection.

The primary final family comprises factor-versus-reference contrasts at each history and direct comparisons of each finite-history factor with its expanding-history version. Different p-values against own history do not by themselves show that one history is better than another. The dedicated finite-versus-expanding contrasts address that question directly. Negative estimates retain their signs and original one-sided directions; non-rejection is not evidence of equivalence.

The signed effect is one minus the equal-target mean candidate/reference MSE ratio. Each named reference supplies its own evaluation-period denominator; it is not always own history. Both numerator and denominator are re-estimated in every joint-date bootstrap draw. Intervals are marginal rather than simultaneous, and separate equal-weighted robustness families are not independent replications or combined across-weighting error control.

The primary history study fixes both M and O at all 48, so it does not identify the separate contribution of measurement breadth or outcome sharing, and it does not evaluate a learned donor selector. A claim that pooling helps with short histories would require the secondary common-versus-separate comparisons holding M and L fixed, rather than factor-versus-own-history alone. Those mechanism comparisons have no dedicated formal test family in this experiment.

### Primary block-13 comparisons: all four references and histories

Each entry is **gain in percent / Holm-adjusted p-value**. All 19 contrasts, including the three direct history tests below, share one Holm family per weighting. These gains use the named reference, not differences of baseline-improvement percentages. All final comparisons use the same 87 response dates, January 3, 2025–August 28, 2026. The [Part B audit](../../results/experiment-02-2026-11-01/audit_part_b.json) independently reconstructed every statistic in all 114 weighting/block/comparison rows.

| Value-weighted history | Own history | Ridge | Elastic net | PLS |
| --- | ---: | ---: | ---: | ---: |
| 104 | 3.9702 / 1.0000 | 2.7985 / 1.0000 | 8.5696 / 0.0019 | 13.7401 / 0.0019 |
| 260 | -1.7532 / 1.0000 | -0.2810 / 1.0000 | -0.1625 / 1.0000 | 7.5042 / 0.0629 |
| 520 | -0.4070 / 1.0000 | -0.9374 / 1.0000 | 1.2168 / 1.0000 | 3.3846 / 1.0000 |
| Expanding | 1.2290 / 1.0000 | 1.9628 / 0.7664 | 0.7956 / 1.0000 | 2.2090 / 1.0000 |

| Equal-weighted history | Own history | Ridge | Elastic net | PLS |
| --- | ---: | ---: | ---: | ---: |
| 104 | 1.2117 / 1.0000 | 2.0858 / 0.0640 | 9.9137 / 0.0036 | 19.9214 / 0.0019 |
| 260 | 1.3211 / 0.9636 | 1.0069 / 1.0000 | 2.0914 / 0.3211 | 9.0970 / 0.0119 |
| 520 | 1.1786 / 1.0000 | -0.1037 / 1.0000 | 1.9658 / 0.3912 | 4.0091 / 0.1064 |
| Expanding | 3.0071 / 0.0930 | 0.4445 / 1.0000 | 0.8580 / 1.0000 | 0.9900 / 1.0000 |

In the primary value-weighted family, only L=104 versus elastic net and PLS passes the declared Holm-0.05 rule. Their marginal basic intervals are **[4.3977%, 13.4099%]** and **[8.1084%, 20.4463%]**; each raw p-value is 0.0001 and adjusted p-value 0.0019. The Monte Carlo resolution is finite; p-values are not zero. No history passes against matched own history or ridge. In equal-weighted robustness, L=104 passes against elastic net/PLS and L=260 against PLS; again no own-history or ridge comparison passes at the primary block length.

This is evidence about fixed fitted procedures under an approximate, imperfectly calibrated inference rule. It is not a general demonstration that factors outperform direct regularization. Short-history elastic net and PLS are less accurate references here; ridge remains competitive. The comparatively weak own-history and ridge results are part of the main conclusion, not exceptions to omit.

### Direct finite-versus-expanding history tests

The reference in this table is the **same factor policy with expanding coefficients**. Positive gain would favor the finite candidate. These are the three additional contrasts in each 19-test family, not a comparison between p-values from different baselines.

| Weighting | Finite L | Gain | Basic interval | Raw p | Holm p |
| --- | ---: | ---: | ---: | ---: | ---: |
| Value | 104 | -4.0900% | [-10.0344%, 2.3668%] | 0.9051 | 1.0000 |
| Value | 260 | -1.0450% | [-5.5267%, 4.6844%] | 0.6608 | 1.0000 |
| Value | 520 | -1.0820% | [-3.6833%, 2.0645%] | 0.7606 | 1.0000 |
| Equal | 104 | -2.2289% | [-7.2727%, 2.8478%] | 0.8288 | 1.0000 |
| Equal | 260 | 0.4904% | [-2.0444%, 3.2235%] | 0.3480 | 1.0000 |
| Equal | 520 | -1.1995% | [-3.4490%, 1.2825%] | 0.8276 | 1.0000 |

None passes the declared rule. All three primary value-weighted point estimates favor expanding history, while equal L=260 has a small favorable but inconclusive point estimate. These one-sided tests do not establish the reverse superiority of expanding history, and non-rejection does not establish equivalence.

### Larger improvement over a weak baseline is not a better factor forecast

The mean target MSE below is descriptive squared log-variance loss, distinct from the headline equal-target mean of MSE ratios. Own-history baselines change with L.

| History | Value factor mean MSE | Value own mean MSE | Value gain vs own | Equal factor mean MSE | Equal gain vs own |
| --- | ---: | ---: | ---: | ---: | ---: |
| 104 | 0.747593 | 0.778176 | 3.9702% | 0.857791 | 1.2117% |
| 260 | 0.724454 | 0.711489 | -1.7532% | 0.833710 | 1.3211% |
| 520 | 0.725519 | 0.720809 | -0.4070% | 0.849136 | 1.1786% |
| Expanding | 0.718053 | 0.724962 | 1.2290% | 0.838642 | 3.0071% |

Value L=104 has the largest gain against its matching own-history baseline, but its factor MSE is worse than the expanding factor's 0.718053. The own-history baseline itself is much worse at L=104. Thus the 3.97% versus 1.23% baseline-relative gains do not show that shorter coefficient history improves the factor forecast. The direct history contrasts above address that question without changing the reference.

### Target heterogeneity and secondary sharing diagnostics

These are each target's final gains against its matching-history own model. Adverse targets remain visible; the factor policy was not selected separately by target.

| Weighting / target | 104 | 260 | 520 | Expanding |
| --- | ---: | ---: | ---: | ---: |
| Value Food | 2.7448% | 1.0448% | 3.3117% | 1.3550% |
| Value Mach | 6.5452% | 0.3378% | -3.3406% | -3.0175% |
| Value Banks | 0.2871% | -6.4466% | -5.1388% | -2.3885% |
| Value Oil | 6.7677% | -0.3613% | 0.2948% | 4.4971% |
| Value Util | -3.7357% | -6.9598% | -1.3339% | 0.5991% |
| Value Hlth | 11.2121% | 1.8661% | 3.7647% | 6.3286% |
| Equal Food | 1.1817% | 4.1210% | 6.4993% | 6.3803% |
| Equal Mach | 1.2667% | 0.8146% | 3.9823% | 2.6538% |
| Equal Banks | -1.1017% | -0.1640% | 1.2200% | 2.3858% |
| Equal Oil | 2.9466% | 2.7206% | -2.8352% | 2.4516% |
| Equal Util | 2.0599% | 0.8178% | -2.1393% | 0.2848% |
| Equal Hlth | 0.9170% | -0.3835% | 0.3444% | 3.8865% |

Holding M=48 and L fixed, the secondary increase in own-history-relative improvement from separate to common slopes is **0.1154, 0.5271, 1.2449, and 1.2620 percentage points** for value L=104/260/520/expanding. The equal-weighted increments are **2.3026, 1.4316, 0.0582, and 0.2882 points**. These are descriptive differences on a common own-history normalization, not the primary named-reference ratio statistic or a formal pooling-history interaction test. Their differing patterns do not establish a general claim that sharing helps most with short histories.

### Every fixed block-length setting

The table lists all comparisons passing the declared adjusted-0.05 rule at each setting. It does not choose a favorable block length. Point effects are unchanged; resampling uncertainty and p-values vary. All 114 Part B rows and 24 Part A rows, including non-rejections, remain in their [Part B](../../results/experiment-02-2026-11-01/part_b/bootstrap_results.csv) and [Part A](../../results/experiment-02-2026-11-01/part_a/bootstrap_results.csv) CSVs.

| Part / weighting | Block 6 | Primary block 13 | Block 26 |
| --- | --- | --- | --- |
| A value | Own history | Own history | Own history |
| A equal | None | None | None |
| B value | L104 vs EN, PLS | L104 vs EN, PLS | L104 vs EN, PLS; L260 vs PLS |
| B equal | L104 vs EN, PLS; L260 vs PLS | L104 vs EN, PLS; L260 vs PLS | L104 vs ridge, EN, PLS; L260 vs PLS; L520 vs PLS; expanding vs own |

The additional block-26 outcomes are sensitivities, not replacements for the block-13 primary conclusions. No direct finite-versus-expanding history contrast passes under any setting. Marginal interval exclusion of zero can coexist with a Holm non-rejection; only the declared adjusted rule determines those labels. Neither that rule nor block sensitivity fixes the adverse calibration evidence.

## What follows, and what does not

The completed experiment supports a narrow descriptive result: the fixed factor procedure can outperform short-history elastic net or PLS on this period, while failing to establish an advantage over matched own history or ridge at the primary setting. It does not demonstrate that truncating coefficient history improves the factor procedure itself, or that its best final cell should be selected for future use. All four histories and all fixed policies remain reported.

M and O are held at 48 in the primary history comparisons, so the result does not identify their separate contributions or validate learned donor membership. The inherited fixed-policy secondary cells permit descriptive sharing comparisons, but no new formal pooling-interaction family was declared. Further mechanism simulations and carefully designed replication are needed before theory or stronger generality claims. No latent-variance, causal, or trading conclusion follows.

The [final forecast audit](../../results/experiment-02-2026-11-01/audit_final.json) and [Part B numerical audit](../../results/experiment-02-2026-11-01/audit_part_b.json) verify saved output calculations, timing, and bootstrap reconstruction. These are reproducibility audits, not statistical calibration proofs. Figures show [Part A uncertainty](../../results/experiment-02-2026-11-01/reports/part_a_fixed_forecast_uncertainty.png), [all history/reference contrasts](../../results/experiment-02-2026-11-01/reports/part_b_factor_vs_references.png), [direct history tests](../../results/experiment-02-2026-11-01/reports/part_b_finite_vs_expanding.png), [history curves](../../results/experiment-02-2026-11-01/reports/history_loss_curves.png), [all targets](../../results/experiment-02-2026-11-01/reports/final_target_history_improvement.png), and [block sensitivity](../../results/experiment-02-2026-11-01/reports/block_length_sensitivity.png). PDF counterparts and the complete tables are preserved alongside them.
