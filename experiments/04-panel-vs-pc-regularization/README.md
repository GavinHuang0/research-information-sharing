# Experiment 4: Panel compression and ridge regularization

This experiment crosses full-panel versus two-PC predictors with OLS versus ridge. It adds ridge and elastic net on the three own-history controls, a two-PC correction to own-history ridge, and a comparison of common versus separate factor slopes. The 718 earlier and 87 later evaluation dates were already inspected. Calibration and power remain deferred.

- [Design and comparisons](protocol.md)
- [Findings and numerical comparisons](results.md)
- [Run archive and all outputs](../../results/experiment-04-2026-11-23/README.md)
- [Executable configuration](../../configs/experiment_04.toml)

Reproduce from the repository root with the locked Python environment. The forecast runner creates a new archive and refuses to overwrite one.

```powershell
& .\.venv\Scripts\python.exe scripts/run_experiment_04.py --output build/experiment-04-replay
& .\.venv\Scripts\python.exe scripts/audit_experiment_04.py --output build/experiment-04-replay
& .\.venv\Scripts\python.exe scripts/report_experiment_04.py --output build/experiment-04-replay
```
