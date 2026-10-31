# Experiment 1: results and interpretation

The development-selected procedure used **two PCA components measured with all 48 industries and common factor slopes across all 48 outcomes**, retaining industry-specific intercepts and own-history slopes. It improved the primary final equal-target mean MSE ratio over own-history regression by **4.2733%**. This was a completed fixed-membership pilot, not an experiment with learned donor selection.

This account summarizes the unchanged [completed run](../../results/fixed-pilot-2026-10-27/README.md). The [frozen procedure](../../results/fixed-pilot-2026-10-27/frozen_procedure.json), [full target table](../../results/fixed-pilot-2026-10-27/reports/target_summary.csv), [full aggregate table](../../results/fixed-pilot-2026-10-27/reports/aggregate_summary.csv), and [audited final results](../../results/fixed-pilot-2026-10-27/final_audit.json) are the source records. [protocol.md](protocol.md) explains exactly what was executed.

## Selection and headline scores

The same procedure, `factor_pooled__M-all__O-all`, was both the overall and factor-family winner on primary value-weighted development data. Its identity was frozen before final forecasts were scored; the two winner labels are the same procedure and do not provide two pieces of independent evidence.

| Frozen procedure | Value-weighted primary | Equal-weighted robustness |
| --- | ---: | ---: |
| Development equal-target MSE ratio | 0.965668 | 0.967967 |
| Development improvement | 3.4332% | 3.2033% |
| Final equal-target MSE ratio | 0.957267 | 0.983438 |
| Final improvement | 4.2733% | 1.6562% |
| Final equal-target MAE improvement, secondary | 1.8083% | 1.0820% |

Scores average six **target-specific ratios** to own-history regression, not the ratio of average MSEs. Final estimates use 156 weekly forecasts per target/policy/weighting. Development estimates use 874. Equal-weighted results did not select the primary policy.

## All six final targets for the frozen procedure

MSE is squared log-variance forecast error; MAE is absolute log-variance forecast error. Positive improvement favors the frozen procedure. Values are rounded here; full precision remains in the target CSV.

| Target | Own-history MSE | Frozen MSE | Primary MSE improvement | Own-history MAE | Frozen MAE | Equal-weighted MSE improvement |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Food | 0.761539 | 0.723284 | 5.0233% | 0.678436 | 0.661774 | 4.5266% |
| Mach | 0.638072 | 0.592737 | 7.1049% | 0.618090 | 0.596419 | 3.1530% |
| Banks | 0.841008 | 0.819850 | 2.5158% | 0.725199 | 0.718631 | **-2.9541%** |
| Oil | 0.674968 | 0.635091 | 5.9080% | 0.628596 | 0.617505 | 0.9928% |
| Util | 0.790041 | 0.754569 | 4.4899% | 0.714678 | 0.697512 | 4.0682% |
| Hlth | 0.900313 | 0.894931 | 0.5978% | 0.724266 | 0.725602 | 0.1510% |

Primary MSE improves for all six, but by very different amounts. Hlth has only a 0.60% MSE improvement and a slightly worse MAE. Equal-weighted Banks MSE is **2.9541% worse** than own history; Oil's robustness improvement is under 1%. The aggregate should not erase these unfavorable or small target results.

## All 18 policies

The table is ordered by **primary development score**, retaining the frozen winner first. It is not ranked by final outcomes. S is the same six fixed names for every target and refit; all means all 48 industries. Entries are percentage improvements over own history, calculated from equal-target mean MSE ratios.

| Policy | M | O | Value development | Value final | Equal development | Equal final |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| Common PCA slopes, frozen | all | all | 3.433 | 4.273 | 3.203 | 1.656 |
| Common PCA slopes | all | S | 3.312 | 4.115 | 3.203 | 1.409 |
| Partial pooling | all | all | 3.293 | 4.523 | 3.531 | 1.347 |
| Separate PCA slopes | all | target | 3.213 | 4.120 | 3.397 | 1.191 |
| Partial pooling | all | S | 3.212 | 4.447 | 3.437 | 1.414 |
| Partial pooling | S | all | 2.674 | 1.669 | 2.634 | 0.721 |
| Common PCA slopes | S | all | 2.664 | 2.010 | 2.668 | 0.709 |
| Common PCA slopes | S | S | 2.591 | 1.893 | 2.659 | 0.641 |
| Partial pooling | S | S | 2.531 | 1.687 | 2.640 | 0.642 |
| Separate PCA slopes | S | target | 2.338 | 1.788 | 2.355 | 0.596 |
| Ridge | all | target | 2.106 | 2.889 | 2.746 | 2.379 |
| PLS | S | target | 1.856 | 1.625 | 2.129 | 0.412 |
| Ridge | S | target | 1.735 | 1.322 | 1.612 | 0.964 |
| Elastic net | S | target | 1.735 | 1.419 | 1.682 | 1.531 |
| Elastic net | all | target | 1.665 | 2.477 | 2.051 | 2.263 |
| PLS | all | target | 0.717 | 3.088 | 2.134 | 1.492 |
| Own history | none | target | 0.000 | 0.000 | 0.000 | 0.000 |
| Persistence | none | target | -44.478 | -69.958 | -44.181 | -71.378 |

Partial pooling with M=48 and O=48 has the lowest primary final point estimate, **4.5225% improvement**, but it was not the development-selected winner and does not replace the frozen procedure. Broad ridge improves equal-weighted final MSE by **2.3789%**, exceeding the frozen factor policy's **1.6562%**. Therefore neither the best final cell nor this robustness check establishes universal factor superiority.

## Measurement breadth and coefficient sharing

Holding two PCs and target-specific factor slopes fixed, increasing M from S to all 48 raises primary final improvement from **1.7881% to 4.1197%**. This is the clearest fixed-policy evidence in the pilot that the broader panel helps through measurement. The comparison does not estimate a causal contribution or show that every additional industry is useful.

At M=48, changing from separate target slopes to common slopes across O=48 raises final improvement from **4.1197% to 4.2733%**. That is **0.1536 percentage points** in baseline-relative improvement, much smaller than the 2.3316-point measurement comparison. The corresponding development increment from separate to common slopes was 0.2200 points. These comparisons isolate declared restrictions with a shared fitted measurement representation, but they are descriptive contrasts rather than an additive decomposition of causal effects.

The small aggregate sharing increment conceals target heterogeneity. With M fixed at all 48, the primary final comparisons are:

| Target | Separate slopes, O=target | Common slopes, O=48 | Partial pooling, O=48 | Change from separate to common |
| --- | ---: | ---: | ---: | ---: |
| Mach | 9.2811% | 7.1049% | 9.1911% | -2.1762 percentage points |
| Banks | 1.1232% | 2.5158% | 2.3855% | +1.3926 percentage points |
| Oil | 4.0124% | 5.9080% | 5.6998% | +1.8956 percentage points |

Common slopes hurt Mach relative to separate slopes while helping Banks and Oil. Partial pooling preserves much of Mach's separate-fit gain and falls between separate/common for Banks and Oil. These realized differences motivate studying heterogeneous forecasting relationships; they do not justify choosing a favorable sharing rule separately for each target using these final results.

## Distinct donor roles and the limits of the result

At M=48, using only S for common outcome slopes gives **4.1151%** final improvement, versus **4.2733%** with O=48. For partial pooling the corresponding figures are **4.4474%** and **4.5225%**. This pilot therefore supplies no primary aggregate advantage for narrowing outcome donors to the fixed S group. The difference is small and lacks an uncertainty assessment; it should not be read as evidence that all-outcome pooling must be best in another sample.

The design did permit measurement and outcome membership to differ, such as M=48 with O=S. That makes the roles empirically distinguishable. It does **not** establish that a learned rule should select different industries for those roles, demonstrate a successful donor-ranking algorithm, or identify an optimal learned group. No such selector was trained or tested in Experiment 1. Planned Experiment 2 is a separate record and has not produced results.

## Evidence and inference

The [measurement/sharing figure](../../results/fixed-pilot-2026-10-27/reports/factor_mechanisms.png), [all-target figure](../../results/fixed-pilot-2026-10-27/reports/final_target_improvement.png), [aggregate figure](../../results/fixed-pilot-2026-10-27/reports/aggregate_relative_improvement.png), and [paired cumulative losses](../../results/fixed-pilot-2026-10-27/reports/final_cumulative_paired_loss.png) visualize the same archived forecasts. The cumulative raw-loss average is a diagnostic, not the normalized-ratio headline score. [Final predictions and losses](../../results/fixed-pilot-2026-10-27/final/predictions.csv.gz) and [historical tuning records](../../results/fixed-pilot-2026-10-27/final/tuning.jsonl.gz) retain the underlying dates, memberships, and choices.

These are descriptive out-of-sample point estimates for six fixed targets and a three-year final window. No bootstrap, confidence intervals, significance tests, or multiplicity adjustment were run. Industry and date observations are dependent; equal-weighted portfolios are not an independent experiment. The data are a retrospective revised snapshot, and the common complete-case sample depends on response availability. No causal identification, intraday realized-variance result, QLIKE evaluation, or trading/economic result follows from this pilot.
