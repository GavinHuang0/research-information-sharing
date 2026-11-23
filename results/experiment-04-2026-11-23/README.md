# Experiment 4 forecast archive

November 23, 2026. The experiment evaluated ten methods over five histories, six targets, two portfolio weightings and the 805 previously inspected forecast dates. See the [protocol](../../experiments/04-panel-vs-pc-regularization/protocol.md) and [results](../../experiments/04-panel-vs-pc-regularization/results.md) for definitions and interpretation.

| File | Contents |
| --- | --- |
| [predictions.csv.gz](predictions.csv.gz) | 483,000 chronological forecasts with outcomes, selected penalties and losses |
| [tuning.csv.gz](tuning.csv.gz) | 119,040 historical validation scores and selection flags |
| [windows.jsonl](windows.jsonl) | Fitting windows and rank diagnostics |
| [calendar.json](calendar.json) | Input alignment and common calendar report |
| [config.toml](config.toml) and [manifest.json](manifest.json) | Exact run settings, inputs, source fingerprints and output hashes |
| [audit.json](audit.json) | Independent audit of forecasts, chronology, choices and inherited references |
| [reports/summary.csv](reports/summary.csv) | Absolute mean MSE and gain versus matching own-history OLS |
| [reports/contrasts.csv](reports/contrasts.csv) | Paired gains with each named reference as denominator |
| [reports/target_summary.csv](reports/target_summary.csv) and [reports/manifest.json](reports/manifest.json) | All target MSEs and report checksums |

The manifest retains the original source hashes from the execution host and separately records the same source hashes after normalizing line endings to LF for cross-platform checks.
