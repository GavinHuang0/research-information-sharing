# Experiments

This directory contains detailed experimental records, separate from the concise [research progress report](../proposal/progress.md). Protocols specify what is fitted, which information is available, how evaluation is performed, and what claims the results permit.

| Experiment | Status | Procedures | Findings or planned outputs |
| --- | --- | --- | --- |
| [01: Fixed S6 industry pilot](01-fixed-s6-pilot/README.md) | Completed October 27, 2026 | [Executed procedure account](01-fixed-s6-pilot/protocol.md) | [Interpretation](01-fixed-s6-pilot/results.md), [immutable full run archive](../results/fixed-pilot-2026-10-27/README.md) |
| [02: Bootstrap inference and coefficient history](02-bootstrap-history/README.md) | Proposed October 31, 2026; not implemented or run | [Precise planned protocol](02-bootstrap-history/protocol.md), [non-executable planning settings](../configs/experiment_02_plan.toml) | Paired bootstrap effects, intervals and p-values; matched coefficient-window comparisons; no results yet |

Experiment 1's archived configuration, protocol, predictions, freeze record, and hashes remain unchanged. Its new folder is a retrospective account with explicit links to those authoritative records. Experiment 2 treats the already inspected 2022-2024 losses as exploratory; it cannot retroactively make them an untouched test.

New experiments should receive new numbered folders, record design changes before execution, and preserve unfavorable as well as favorable results. A progress-report update is not a substitute for a versioned experimental protocol.
