# Factor measurement and forecast sharing

This project asks when industries should play different roles in **measuring common conditions** and **estimating how those conditions predict a target's future risk**. A broad measurement panel may be useful even when forecast coefficients should remain target-specific. Separate donor selection is a research hypothesis, not an established result.

## Current progress: November 1, 2026

- Archived and labeled the French 48-industry daily data, in value- and equal-weighted forms, with raw downloads, industry definitions, coverage, units, and checksums.
- Constructed reproducible weekly variance/volatility features and causal own-history controls.
- **Completed Experiment 1:** a fixed six-target pilot with two PCs and 18 prespecified procedures. Development selection was frozen before the 2022-2024 evaluation. Its selected all-48/common-slope factor procedure improved the equal-target MSE ratio by **4.27%** versus own-history regression; equal-weighted robustness improvement was **1.66%**, including a **2.95% deterioration for Banks**.
- Broader measurement explains most of the main comparison: separate slopes improve 1.79% with six measurement industries and 4.12% with 48. Common slopes across all outcomes raise this to 4.27%. Narrower outcome sharing did not improve the primary aggregate; benefits differ by target.
- **Completed Experiment 2:** audited paired-bootstrap uncertainty and coefficient-history comparisons. At primary block length 13, no history establishes a factor advantage over matched own history or ridge in 2025–August 2026. L=104 passes the declared adjusted-p rule against elastic net (8.57% gain, p=0.0019) and PLS (13.74%, p=0.0019), while no finite history beats the expanding factor control. Bounded synthetic diagnostics showed adverse rejection/coverage behavior; nominal calibration is not established, so p-values and intervals remain approximate.

## Reading guide

| Reader's purpose | Document |
| --- | --- |
| Concise report for the professor | [Current progress in Markdown](proposal/progress.md), [synchronized PDF](proposal/proposal.pdf) |
| Report source, synchronization, and original proposal | [Proposal/progress folder](proposal/README.md), [original October 9 proposal](proposal/archive/2026-10-09/proposal.pdf) |
| All experiment records | [Experiment index](experiments/README.md) |
| What Experiment 1 actually did | [Overview](experiments/01-fixed-s6-pilot/README.md), [precise executed procedure](experiments/01-fixed-s6-pilot/protocol.md) |
| Experiment 1 findings and caveats | [Interpretation](experiments/01-fixed-s6-pilot/results.md), [full result archive and figures](results/fixed-pilot-2026-10-27/README.md) |
| Experiment 2 procedures and execution status | [Overview](experiments/02-bootstrap-history/README.md), [frozen design](experiments/02-bootstrap-history/protocol.md), [execution record](experiments/02-bootstrap-history/executed.md), [results record](experiments/02-bootstrap-history/results.md) |
| Inputs and feature definitions | [Data catalog](data/README.md), [input documentation](docs/data.md), [weekly features](data/features/kenneth-french/48-industry-daily/2026-10-16/weekly-v1/README.md) |
| Broader research toolkit and legacy grids | [Earlier experiment plan](docs/experiment_plan.md) |

The progress report summarizes the rationale, completed work, findings, and next steps. Detailed protocols belong under `experiments/`; the progress report is not a substitute for those records. Experiment 1's original frozen configuration/protocol and archived outputs remain unchanged.

## Experiment 1: completed fixed S6 pilot

The six evaluation targets and common small panel are exactly **Food, Mach, Banks, Oil, Util, Hlth**. Measurement membership is this named set or all 48 industries; outcome membership is the target, the named six, or all 48. The design uses explicit names rather than CSV prefixes. It excludes random donor selection, adaptive factor-design selection, and factor-count search.

The 18 distinct procedures include separate/common/partial factor slopes, direct ridge and elastic net, two-component PLS, own-history regression, and persistence. Separate-slope outcome cells that give identical target forecasts are counted once. Intercepts and own-history slopes remain industry-specific in pooled models; fitted PCA representations are shared within coefficient comparisons.

The common calendar contains 1,290 aligned predictor/outcome pairs: 260 initialization pairs, 874 development forecast dates, and 156 final forecast dates per target/procedure/weighting. The response-year boundary is 2022. Historical validation uses 52 pairs, and expanding fits update every 13 eligible origins without restarting at the final boundary. Final selection was not changed to the best terminal cell.

The archive includes all six targets and all prespecified comparisons, forecast-level losses, tuning records, code/input hashes, freeze timestamps, 58-test validation, and independent timing/aggregation audits. Its findings are descriptive point estimates, not proof of latent-factor recovery, universal factor superiority, or trading value.

## Experiment 2: completed uncertainty and history study

Part A applies the frozen stationary-bootstrap design to saved Experiment 1 losses. Because 2022-2024 results have been inspected, its p-values remain exploratory post-pilot inference.

Part B fixes Experiment 1's selected all-48/common-slope factor policy and varies supervised coefficient histories: **104, 260, 520 pairs, and expanding**. Predictor-only PCA history stays expanding and identical across these comparisons. Own-history, ridge, elastic net, and PLS references receive matched coefficient windows. A common 572-pair start permits 520 inner-training pairs plus 52 validation pairs.

The inference resamples joint date vectors across targets, methods, histories, and both weightings, recomputes target MSE ratios, and uses null-centered one-sided bootstrap p-values. A primary Holm family covers 16 factor-versus-reference comparisons and three direct history comparisons. The protocol fixes block lengths, draw count, seeds, intervals, hypotheses, validation gates, and interpretation limits. It permits unfavorable or inconclusive outcomes rather than requiring significance.

The new evaluation period is January 2025 through the last complete August 2026 week, with uninspected-loss evidence and procedure freezes recorded before scoring. A dedicated Experiment 2 runner and executable configuration implement the design; the original planning TOML and protocol remain unchanged. The [execution record](experiments/02-bootstrap-history/executed.md) documents completed gates, freezes, stage chronology, audits, and reproduction commands. Holm adjustment does not repair the unestablished marginal p-value calibration revealed by synthetic diagnostics.

The exploratory Part A analysis passes the declared primary Holm rule only for value-weighted factor versus own history, not the direct references; equal-weighted Part A has no adjusted rejection. The new-period primary Part B gains are selective, and shortening the coefficient window does not establish an improvement over the same factor procedure with expanding history. A larger gain over a weaker short-history baseline is not evidence of a better factor forecast. [All contrasts, target heterogeneity, and sensitivities](experiments/02-bootstrap-history/results.md) remain visible, with no final winner reselection or universal factor claim.

## Data and feature conventions

For each Friday-ending week, `Q = sum(daily_decimal_return**2)`, weekly volatility is `sqrt(Q)` without annualization, and `v = log(Q + 1e-8)`. At least three observed daily returns are required; insufficient weeks remain missing. Own controls are current v and its complete trailing 4- and 12-week means. The response is next calendar week's v. Calendar alignment precedes missing-case filtering, with no filling or interpolation.

These are daily-return variation proxies, not intraday realized variance or directly observed conditional volatility. Source snapshots can contain revised history. All original data, curated features, and the first result archive are tracked in Git; ad hoc downloads and uncurated generated results remain ignored.

## Setup and reproduction

Python 3.12 matches the pinned scientific environment. After creating a virtual environment:

```bash
python -m pip install -r requirements-analysis-lock.txt
python -m pip install --no-deps --no-build-isolation -e .
python -m unittest discover -s tests -v
```

Reproduce **Experiment 1 only** in a new output directory; the existing archive is never overwritten:

```bash
python scripts/run_fixed_pilot.py --config configs/fixed_pilot.toml --output results/reproduction-01 --stage development
python scripts/run_fixed_pilot.py --config configs/fixed_pilot.toml --output results/reproduction-01 --stage final
python scripts/run_fixed_pilot.py --config configs/fixed_pilot.toml --output results/reproduction-01 --stage report
```

The final/report stages verify the frozen code, configuration, inputs, and development artifacts. On Windows use `.\.venv\Scripts\python.exe` in place of `python`. These commands reproduce Experiment 1; Experiment 2 has its own [execution record](experiments/02-bootstrap-history/executed.md).

A small synthetic pipeline check remains available with `factorcast simulate --config configs/smoke.toml --output results/smoke-new`. Synthetic checks are software validation, not additional empirical findings. The legacy `factorcast empirical` starter still uses prefix panels and adaptive searches; the dedicated experiment runners implement the fixed scientific designs.

## Progress-report synchronization

`proposal/progress.md` is the single content source. Pandoc and PDFLaTeX generate the current LaTeX and PDF; the original proposal is preserved in an archive.

```bash
python scripts/build_progress_report.py
python scripts/build_progress_report.py --check
```

The verification checks source/template/builder/output fingerprints to prevent stale versions. PDF pages are visually reviewed after changes. GitHub Actions validates software and report synchronization and rebuilds the professor-facing PDF.

## Repository layout

```text
proposal/       Current progress Markdown, generated LaTeX/PDF, historical proposal
experiments/    Numbered experiment procedures, status, findings, and interpretations
results/        Curated experiment artifacts; uncurated generated runs ignored
configs/        Executable experiment settings and preserved pre-execution planning record
data/           Curated raw/daily/weekly snapshots, labels, coverage, provenance
docs/           Input reference and broader/legacy experimental toolkit
src/factorcast/ Shared feature, model, simulation, fitting, and reporting code
scripts/        Snapshot/feature preparation, fixed-pilot runner, progress-report build
tests/          Data, model, chronology, leakage, and aggregation checks
```
