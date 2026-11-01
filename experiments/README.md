# Experiments

This directory contains detailed experimental records, separate from the concise [research progress report](../proposal/progress.md). Protocols specify what is fitted, which information is available, how evaluation is performed, and what claims the results permit.

| Experiment | Status | Procedures | Findings or planned outputs |
| --- | --- | --- | --- |
| [01: Fixed S6 industry pilot](01-fixed-s6-pilot/README.md) | Completed October 27, 2026 | [Executed procedure account](01-fixed-s6-pilot/protocol.md) | [Interpretation](01-fixed-s6-pilot/results.md), [immutable full run archive](../results/fixed-pilot-2026-10-27/README.md) |
| [02: Bootstrap inference and coefficient history](02-bootstrap-history/README.md) | Completed November 1, 2026; forecasts and inference independently audited | [Frozen scientific protocol](02-bootstrap-history/protocol.md), [execution/reproduction record](02-bootstrap-history/executed.md), [executable settings](../configs/experiment_02.toml) | [Findings and all primary contrasts](02-bootstrap-history/results.md): limited wins versus short-history elastic net/PLS, no primary own-history/ridge win, no finite-history advantage over expanding; adverse calibration caveat retained |

Experiment 1's archived configuration, protocol, predictions, freeze record, and hashes remain unchanged. Its new folder is a retrospective account with explicit links to those authoritative records. Experiment 2 treats the already inspected 2022-2024 losses as exploratory; it cannot retroactively make them an untouched test.

Experiment 2's pre-execution synthetic diagnostics did not establish nominal calibration and showed adverse rejection/coverage behavior. That limitation applies to its empirical p-values and intervals even when implementation checks pass or an adjusted p-value is small. Its October 31 protocol retains its original planning-status text as a frozen record; the execution account records the later authorized work.

New experiments should receive new numbered folders, record design changes before execution, and preserve unfavorable as well as favorable results. A progress-report update is not a substitute for a versioned experimental protocol.
