# Fixed S6 pilot: completed results

Implemented and executed October 27, 2026. The common small panel and six evaluation targets are **Food, Mach, Banks, Oil, Util, Hlth**. M is this fixed S6 set or all 48 industries; O is the target, S6, or all 48. There are two PCs throughout and 18 distinct procedures after removing equivalent separate-slope cells.

**The procedure selected on development data is PCA with all 48 measurement industries and common factor slopes across all 48 outcomes.** Industry intercepts and own current/four-/twelve-week coefficients remain separate. Its primary final equal-target mean MSE ratio is **0.957267**, a **4.2733% improvement** over own-history regression. The same frozen procedure improves the equal-weighted robustness ratio by **1.6562%**, with an unfavorable Banks result.

## Protocol and execution order

- [Declared protocol](protocol.md), [exact configuration](config.toml), and [18-policy inventory](policies.json). No random membership, factor-count search, learned donor selection, or adaptive factor-design policy was used.
- Archived October 16, 2026 daily inputs, weekly Q=sum(r^2), v=log(Q+1e-8), minimum three observations, own current/4/12-week means of logs, and next-calendar-week response. All methods, targets, and weightings use identical eligible dates. Features are built before calendar filtering and missing-case removal.
- [Calendar audit](calendar.json): 1,290 eligible predictor/outcome pairs, origins 2000-01-07 through 2024-12-20, responses 2000-01-14 through 2024-12-27. Initial history is 260 pairs, not 260 weekly feature observations. Thirteen calendar origins in September-November 2001 are excluded by the shared response/history requirements.
- First forecast: origin 2005-04-01, response 2005-04-08. Development has 874 response dates through 2021; final has 156 response dates in 2022-2024, for each target and procedure.
- Expanding history, last 52 historical pairs for inner validation, and refits every 13 eligible origins. Penalties are chosen on historical target validation MSE and the selected pipeline is refitted on all realized history.
- Implementation was committed as `07edc76`. Development forecasts ran first. [The frozen procedure](frozen_procedure.json), all 18 primary scores, code/config/input hashes, and development files were committed as `b2161f6` at 04:14:47 UTC, before the logged final start at 04:14:51.672943 UTC.
- Final replay begins with refit anchor 1131 for first final pair 1134; its last fitted response is 2021-12-10. There is no new refit at the holdout boundary. Scheduled tuning continues using already-realized outcomes only.
- [58-test validation](validation.txt), [independent development audit](development_audit.json), and [independent final audit](final_audit.json) passed. The audits checked memberships, every historical cutoff, candidate losses/choices, output hashes, and independent loss/aggregation recalculation.
- Fitting time: development 124.18 seconds; final 33.10 seconds, excluding serialization and plotting. There are 188,784 development and 33,696 final forecast records.

## Scoring and all prespecified comparisons

Target MSE is the mean of held-out weekly (actual log variance - forecast)^2. It includes the mean forecast error and excludes training errors, donor losses, and penalties. The headline score is (1/6) sum_i [MSE_i,method / MSE_i,own_history]. Improvement below is 100*(1-score), so positive favors the procedure. It is not a ratio of pooled MSEs. Every target has equal weight. Log MAE and its baseline ratios are secondary metrics in the CSVs.

All rows below were prespecified and are ordered by **primary development score**, never selected or reordered to emphasize final winners. S means the same fixed six names for every target and refit. The first row was frozen before final execution.

| Procedure | M | O | Value development improvement % | Value final improvement % | Equal development improvement % | Equal final improvement % |
| --- | --- | --- | ---: | ---: | ---: | ---: |
| PCA common slopes **[frozen]** | all | all | 3.433 | 4.273 | 3.203 | 1.656 |
| PCA common slopes | all | S | 3.312 | 4.115 | 3.203 | 1.409 |
| PCA partial pooling | all | all | 3.293 | 4.523 | 3.531 | 1.347 |
| PCA separate slopes | all | target | 3.213 | 4.120 | 3.397 | 1.191 |
| PCA partial pooling | all | S | 3.212 | 4.447 | 3.437 | 1.414 |
| PCA partial pooling | S | all | 2.674 | 1.669 | 2.634 | 0.721 |
| PCA common slopes | S | all | 2.664 | 2.010 | 2.668 | 0.709 |
| PCA common slopes | S | S | 2.591 | 1.893 | 2.659 | 0.641 |
| PCA partial pooling | S | S | 2.531 | 1.687 | 2.640 | 0.642 |
| PCA separate slopes | S | target | 2.338 | 1.788 | 2.355 | 0.596 |
| Ridge | all | target | 2.106 | 2.889 | 2.746 | 2.379 |
| PLS | S | target | 1.856 | 1.625 | 2.129 | 0.412 |
| Ridge | S | target | 1.735 | 1.322 | 1.612 | 0.964 |
| Elastic net | S | target | 1.735 | 1.419 | 1.682 | 1.531 |
| Elastic net | all | target | 1.665 | 2.477 | 2.051 | 2.263 |
| PLS | all | target | 0.717 | 3.088 | 2.134 | 1.492 |
| Own history | none | target | 0.000 | 0.000 | 0.000 | 0.000 |
| Persistence | none | target | -44.478 | -69.958 | -44.181 | -71.378 |

## Frozen procedure: all six final targets

Each row has 156 weekly forecasts. MSE and MAE are in log-variance units (MSE is squared). The final procedure was not selected separately by target or by equal-weighted performance.

| Target | Own-history MSE | Frozen MSE | Primary MSE improvement % | Own-history log MAE | Frozen log MAE | Equal-weighted MSE improvement % |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| Food | 0.761539 | 0.723284 | 5.023 | 0.678436 | 0.661774 | 4.527 |
| Mach | 0.638072 | 0.592737 | 7.105 | 0.618090 | 0.596419 | 3.153 |
| Banks | 0.841008 | 0.819850 | 2.516 | 0.725199 | 0.718631 | -2.954 |
| Oil | 0.674968 | 0.635091 | 5.908 | 0.628596 | 0.617505 | 0.993 |
| Util | 0.790041 | 0.754569 | 4.490 | 0.714678 | 0.697512 | 4.068 |
| Hlth | 0.900313 | 0.894931 | 0.598 | 0.724266 | 0.725602 | 0.151 |

For the frozen procedure, the primary final equal-target mean MAE ratio improves **1.8083%**; equal-weighted improvement is **1.0820%**. Primary Hlth MSE improves only 0.60%, and its MAE is slightly worse. Equal-weighted Banks MSE worsens **2.9541%**. These outcomes remain in all tables and figures.

## Interpretation

**Broader measurement supplies most of the observed gain.** With target-specific factor slopes, expanding M from S6 to all 48 raises primary final improvement from **1.7881% to 4.1197%**, relative to own history. This comparison holds the two-component dimension and coefficient rule fixed.

**Coefficient sharing adds a smaller increment.** At M=48, moving from separate slopes to common slopes across all 48 raises improvement from **4.1197% to 4.2733%** (0.1536 percentage points of the baseline-relative improvement). The corresponding development increment was 0.2200 points.

**This pilot does not establish an advantage for restricting outcome donors to S6.** At M=48, common O=S gives **4.1151%** final improvement versus **4.2733%** for O=48; partial O=S gives **4.4474%** versus **4.5225%** for O=48. Partial pooling had the lowest primary final point estimate, but it did not replace the development-selected common-slope procedure.

**Factor superiority is not uniform across weightings.** Primary final ridge, elastic net, and PLS with M=48 improve **2.8894%, 2.4775%, and 3.0882%** respectively. In the equal-weighted robustness check, broad-panel ridge improves **2.3789%**, exceeding the frozen factor procedure at **1.6562%**. Robustness therefore weakens a blanket claim that PCA is best.

These are descriptive out-of-sample point estimates for a fixed six-target set and a three-year final period. No confidence intervals or multiplicity-adjusted significance claims are supplied. The industries and forecast dates are dependent; the equal-weighted portfolios are not an independent replication. The fixed retrospective source can contain historical revisions. There is no causal identification, variance-scale QLIKE assessment, or trading/economic evaluation.

## Tables, predictions, tuning, and figures

- [Combined per-target table](reports/target_summary.csv): all 432 target/stage/weight/procedure cells, MSE, MAE, baseline ratios, and counts.
- [Combined equal-target aggregates](reports/aggregate_summary.csv): all 72 stage/weight/procedure cells.
- [Development predictions and per-week losses](development/predictions.csv.gz) and [final predictions and losses](final/predictions.csv.gz). Gzip CSV preserves full-precision forecasts while reducing repository storage.
- [Development tuning records](development/tuning.jsonl.gz) and [final tuning records](final/tuning.jsonl.gz), including every candidate score, explicit memberships, selections, and historical cutoffs.
- [Environment and input/code provenance](metadata.json), [development file hashes](development/stage_manifest.json), [final file hashes](final/stage_manifest.json), and [complete artifact hashes](artifact_manifest.json).
- [Aggregate comparison PNG](reports/aggregate_relative_improvement.png) / [PDF](reports/aggregate_relative_improvement.pdf).
- [All-target final comparison PNG](reports/final_target_improvement.png) / [PDF](reports/final_target_improvement.pdf).
- [Factor-mechanism comparison PNG](reports/factor_mechanisms.png) / [PDF](reports/factor_mechanisms.pdf).
- [Final cumulative paired losses PNG](reports/final_cumulative_paired_loss.png) / [PDF](reports/final_cumulative_paired_loss.pdf). The frozen overall and factor choices coincide, so those two figure rows represent the same procedure, not independent evidence. The black curve averages raw paired losses across targets and is a diagnostic, not the headline normalized-ratio score.

## Reproduction

Install the exact environment in `requirements-analysis-lock.txt`, then run from the repository root with a **new** output directory:

```bash
python scripts/run_fixed_pilot.py --config configs/fixed_pilot.toml --output results/reproduction --stage development
python scripts/run_fixed_pilot.py --config configs/fixed_pilot.toml --output results/reproduction --stage final
python scripts/run_fixed_pilot.py --config configs/fixed_pilot.toml --output results/reproduction --stage report
```

On Windows use `.\.venv\Scripts\python.exe` instead of `python`. The stage guards reject changed configuration, implementation, dependencies, inputs, or development artifacts after freezing. Archived stage outputs are not overwritten. Preparation is single-threaded for small repeated fits; no random panel or model-selection seed is involved.
