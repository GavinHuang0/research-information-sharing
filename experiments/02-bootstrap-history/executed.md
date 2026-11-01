# Experiment 2: execution record

**Completed November 1, 2026.** Part A inference, development/final forecasts, Part B inference, and reporting have completed. Independent audits passed for both forecast stages and both inference parts. This mutable account accompanies the unchanged October 31 [scientific protocol](protocol.md), without rewriting the frozen design. Interpretation and calibration caveats belong in [results.md](results.md).

## Frozen design and implementation

The run directory is `results/experiment-02-2026-11-01/`. Its [initial freeze](../../results/experiment-02-2026-11-01/protocol_freeze.json), [configuration copy](../../results/experiment-02-2026-11-01/config.toml), [protocol copy](../../results/experiment-02-2026-11-01/protocol.md), and [environment/input metadata](../../results/experiment-02-2026-11-01/metadata.json) identify the actual run. The original planning document still says proposed; execution status is maintained here and in the run artifacts.

The implementation comprises the dedicated [stage runner](../../scripts/run_experiment_02.py), [coefficient-history runner](../../src/factorcast/history.py), [saved-loss bootstrap](../../src/factorcast/bootstrap.py), and [reporting module](../../src/factorcast/history_reporting.py). The [executable configuration](../../configs/experiment_02.toml) preserves the planning configuration's scientific sections. Experiment 1's archived files and frozen implementation remain unchanged.

Part A evaluates the fixed first-pilot factor policy against own history, ridge, elastic net, and PLS using previously inspected 2022–2024 forecasts. It is exploratory post-pilot inference. Part B keeps the same common-slope, all-48 measurement/all-48 outcome factor policy across coefficient histories 104, 260, 520, and expanding. It evaluates all original 18 policy labels for each history, without selecting a new winner.

At scheduled cutoff `a = 572 + 13*k`, `b = a - 52`. Inner PCA uses expanding predictors `[0:b)` and outer PCA `[0:a)`, with the same representation shared across histories and outcome restrictions. For finite L, every supervised fit uses `[b-L:b)` for candidates and `[a-L:a)` for the refit. This includes intercepts, donor/target own-history slopes, factor coefficients, direct nuisance projections/scalers, and supervised PLS directions. Expanding controls start at zero. Prebuilt own-history features remain causal calendar features and are not truncated at the coefficient-window boundary.

Every candidate is scored using historical target validation MSE. The fixed penalty grids and first-declared tie rule remain unchanged. All targets, policies, histories, and weightings share one complete-case calendar. The final response interval is January 3, 2025–August 28, 2026. The scheduled crossing block must be replayed rather than refitted at that boundary. Persistence forecasts repeat across history labels and are not independent evidence.

## Validation completed before empirical execution

The [preflight record](../../results/experiment-02-2026-11-01/preflight.md) documents independent raw-source/feature/calendar checks, bounded evidence about the uninspected score interval, implementation-window tests, bootstrap numerical checks, and orchestration review. The [validation log](../../results/experiment-02-2026-11-01/validation.txt) and [synthetic diagnostics](../../results/experiment-02-2026-11-01/synthetic_validation.json) are preserved with the run.

**Passing implementation tests did not establish statistical calibration.** The bounded synthetic loss-process diagnostic showed adverse rejection and interval-coverage behavior. It was a single-comparison check, not calibration of Holm families or the entire expanding-PCA, tuned, rolling/expanding forecasting pipeline. Empirical p-values are approximate and the basic intervals are marginal, not demonstrated nominal-coverage or simultaneous intervals. Holm adjustment cannot fix a marginal calibration failure. This warning remains part of the completed findings even when a result is favorable.

The primary expected block length, draw count, seed, and sensitivity settings were retained rather than changed in response to these diagnostics. The preflight records their exact values, Monte Carlo uncertainty, and interpretation limits. No additional simulation or calibration claim is introduced by this document.

## Stage and audit record

| Stage | Current record |
| --- | --- |
| Source/calendar and implementation gates | Completed before empirical execution; see preflight and validation artifacts |
| Initial procedure/input/code freeze | Recorded before the development stage |
| Part A inference | Completed; [independent audit passed](../../results/experiment-02-2026-11-01/audit_part_a.json) |
| Part B development | Completed; [independent audit passed](../../results/experiment-02-2026-11-01/audit_development.json) |
| Development-output audit and pre-final freeze | [Pre-final freeze](../../results/experiment-02-2026-11-01/final_freeze.json) and audited development committed before final execution |
| Part B final | Completed; [independent audit passed](../../results/experiment-02-2026-11-01/audit_final.json) |
| Part B empirical inference | Completed; [all numerical comparisons independently audited](../../results/experiment-02-2026-11-01/audit_part_b.json) |
| Complete report | All history/policy/target tables and six PNG/PDF figure pairs saved; [report manifest](../../results/experiment-02-2026-11-01/reports/report_manifest.json) |

The initial freeze was committed as `c48482afbb6796b59519b9fad036415b4352b87b` at **00:43:10 EDT on November 1, 2026**, before Part A began at **00:43:14.148590 EDT**. The freeze identifies implementation commit `750dd8db936d98813f63a05400bda7bc834ec667`. Development began at **00:45:10.939113 EDT**. Its audit verified 620,352 forecasts, 718 dates per cell, 112 weighting/refit blocks, and 448 PCA fits. The expanding control reproduces 33,696 overlapping Experiment 1 forecasts with maximum absolute difference zero; this is an implementation check, not independent replication.

The audited development files and pre-final freeze were committed as `2c15048a230eaa6dfe2e3611c2d6e4606f18bcf7` at **00:53:01 EDT**, before final execution began at **00:53:07.718343 EDT**. Final forecasting completed at **00:54:02.208691 EDT**, and Part B inference at **00:54:29.035411 EDT**. These events preceded the independent saved-output audits. Times here are before the November 1 daylight-saving clock change; precise UTC records remain in stage manifests and audits.

The final audit verified **75,168 forecasts**, **87 dates per cell**, **14 weighting/refit blocks**, **56 PCA fits**, and **6,048 tuning records**. First final pair 1290 replayed refit 1287 with the same development-side selections; the next refit stayed at 1300. The final stage did not restart the schedule at its boundary. The Part B audit reconstructed all three shared index matrices and independently recalculated all **114** comparison/weighting/block rows, including numerator and denominator MSEs, null-centered tails, basic intervals, and Holm-19 adjustments. Part A's audit checked all **24** rows and Holm-4 families. Experiment 1's 36 manifest-listed artifacts remained unchanged.

Saved [development forecasts](../../results/experiment-02-2026-11-01/development/predictions.csv.gz), [final forecasts](../../results/experiment-02-2026-11-01/final/predictions.csv.gz), [development tuning](../../results/experiment-02-2026-11-01/development/tuning.jsonl.gz), and [final tuning](../../results/experiment-02-2026-11-01/final/tuning.jsonl.gz) retain explicit memberships, L/PCA windows, candidate scores, selected penalties, origin/response dates, and losses. [Part A](../../results/experiment-02-2026-11-01/part_a/bootstrap_results.csv) and [Part B](../../results/experiment-02-2026-11-01/part_b/bootstrap_results.csv) save every comparison, p-value, interval, and block setting. Their stage manifests and index manifests identify the saved inputs and joint draws. The numerical audits establish consistency with the declared computations, not nominal statistical calibration.

## Reproduction in a new output directory

Use the pinned environment and the frozen implementation/configuration. On Windows PowerShell, record the validation prerequisites before freezing a fresh run:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v *> .venv/experiment_02_validation.txt
.\.venv\Scripts\python.exe scripts/validate_bootstrap_synthetic.py --replications 100 --bootstrap-replicates 499 --output .venv/bootstrap_synthetic_validation.json
```

The diagnostic refuses to replace an existing output. Use a fresh checkout/environment or retain the verified existing prerequisite record rather than overwrite the archived experiment. Implementation checks and diagnostics are distinct; the latter's adverse calibration findings must be kept.

Choose a new experiment output directory and run the separate guarded stages:

```powershell
.\.venv\Scripts\python.exe scripts/run_experiment_02.py --config configs/experiment_02.toml --output results/reproduction-02 --stage freeze
.\.venv\Scripts\python.exe scripts/run_experiment_02.py --config configs/experiment_02.toml --output results/reproduction-02 --stage part-a
.\.venv\Scripts\python.exe scripts/run_experiment_02.py --config configs/experiment_02.toml --output results/reproduction-02 --stage development
.\.venv\Scripts\python.exe scripts/run_experiment_02.py --config configs/experiment_02.toml --output results/reproduction-02 --stage final
.\.venv\Scripts\python.exe scripts/run_experiment_02.py --config configs/experiment_02.toml --output results/reproduction-02 --stage inference
.\.venv\Scripts\python.exe scripts/run_experiment_02.py --config configs/experiment_02.toml --output results/reproduction-02 --stage report
```

Freeze refuses an existing experiment directory; subsequent stages refuse existing stage/report artifacts and verify frozen fingerprints. Independently audit saved development outputs and preserve the pre-final freeze before final scoring, then audit final and bootstrap outputs before interpretation. No stage may overwrite this completed run or use its losses to revise the declared design. On macOS/Linux, substitute the environment's `python` command and use `> .venv/experiment_02_validation.txt 2>&1` for validation-log redirection.
