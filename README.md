# Factor measurement and forecast sharing

This project studies two ways that additional asset data can improve a forecast: by measuring common signals more accurately, and by helping estimate how those signals predict a particular asset's future outcome. Those roles need not favor the same assets. The main research question is when choosing them separately improves prediction and economic decisions. Choosing the number or subset of predictive components is a supporting question.

The concise [research proposal PDF](proposal/proposal.pdf) develops the research motivation, testable hypotheses, economic relevance, and path toward theory. Its independent [LaTeX source](proposal/proposal.tex) and [bibliography](proposal/references.bib) are included. The detailed protocol is in [docs/experiment_plan.md](docs/experiment_plan.md). This repository contains an initial experiment package; its synthetic checks are pipeline validation, not research findings.

Factor forecasts restrict a direct linear predictor to a learned subspace. They may offer useful finite-sample regularization and combine noisy measurements, but cannot improve the unrestricted population optimum simply by transforming the inputs. Direct ridge, elastic net, and supervised PLS are therefore essential comparisons. Larger measurement panels at a fixed factor dimension do not inherently increase the number of target regression coefficients. Pooling outcomes adds a separate bias–variance decision when forecasting relationships differ.

## Run a reproducible simulation

Python 3.11 or later is required. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install -e .
factorcast simulate --config configs/smoke.toml --output results/smoke
python -m unittest discover -s tests -v
```

If the scientific dependencies are already installed, the source tree also runs without installation:

```bash
PYTHONPATH=src python -m factorcast simulate --config configs/smoke.toml --output results/smoke
PYTHONPATH=src python -m unittest discover -s tests -v
```

Use a new output directory for each run: the CLI refuses to overwrite existing results. The smoke configuration is small enough to check the full pipeline. [configs/pilot.toml](configs/pilot.toml) provides a larger exploratory grid; increase independent repetitions and predeclare the final design before drawing substantive conclusions. Setting `OPENBLAS_NUM_THREADS=1 OMP_NUM_THREADS=1` can improve performance for these small repeated fits.

`requirements-lock.txt` records the validated Python 3.12 environment; `pyproject.toml` declares broader compatible dependency ranges. GitHub Actions runs the unit checks and smoke simulation with those pinned versions and builds the proposal separately.

The simulator generates a stationary two-factor maximum panel once per seed and scenario. Smaller measurement and outcome panels are prefixes of that same panel, so targets, dates, and shocks stay fixed as asset counts change. Predictor quality and coefficient heterogeneity vary separately. Both factor coordinates are spanned by the initial measurement assets. The target's heterogeneous slope is a seeded draw, rather than being fixed at the donor population mean. It remains fixed across asset counts within a scenario. `measurement_correlation`, `outcome_correlation`, `noisy_multiplier`, and signed `donor_shift` can be changed in the `[simulation]` configuration for additional controlled comparisons.

The implemented models are:

| Method | Information and restriction |
| --- | --- |
| Historical mean / empirical persistence and local history | Simple reference forecasts |
| Shared PCA, separate coefficients | Measurement assets share predictors; outcomes are fitted separately |
| Shared PCA, common coefficients | Outcome donors share factor slopes; intercepts and local controls remain asset-specific |
| Shared PCA, partial pooling | Quadratic shrinkage of slopes toward their common mean |
| PCA followed by lasso | Select predictive coordinates from a declared candidate PC basis |
| Direct ridge and elastic net | Regularized forecasts from the same raw measurement panel |
| PLS | Training-response-guided dimension reduction for the target |
| Oracle factors | Simulation-only regression using true factors; not a feasible empirical forecast |
| Adaptive factor design | Historical validation chooses both donor counts, factor count, pooling rule, and penalty |

PCA and both predictor and score scaling use training observations only. Coefficient-sharing comparisons reuse the same representation. Partial-pooling penalties use normalized loss to avoid unintentionally changing shrinkage when more outcome donors enter. Lasso selection is basis-dependent and does not establish the market's true factor count. In the empirical runner, all fitted models include unpenalized target own-history controls; pooled factor models retain each donor's own controls. Direct and PLS models partial those controls out using training projections.

The current donor grid uses fixed nested prefixes, including the target. Joint selection minimizes historical validation loss over this finite candidate grid. Richer donor rankings, weighting, residual channels, and oracle guarantees are future research described in the experiment plan.

## Use the committed return data

The repository includes a dated snapshot of the official French daily 48-industry returns: the original ZIP, value- and equal-weighted decimal-return CSVs, and provenance. The [data catalog](data/README.md) identifies the source, coverage, files, and hashes. A fresh clone includes these inputs; no additional download is required. Use the value-weighted CSV for the first experiment:

```bash
factorcast empirical --config configs/empirical.toml \
  --returns data/processed/kenneth-french/48-industry-daily/2026-10-16/value_weighted_returns_decimal.csv --target Food \
  --output results/industry-food
```

This command is an example for a later forecast run; adding the data snapshot does not run an experiment. Adapt panel counts, split sizes, and the declared calendar sample to the supplied dataset. The prepared CSV uses `units = "decimal"` in the example configuration. For other local CSVs with a `date` column and named asset columns, explicitly declare decimal or percent units. The target is moved to the first position; other columns retain CSV order. This order determines the initial nested donor grid and is saved in provenance. Establish or randomize panel order before inspecting test performance. The current config evaluates a fixed block after its initial history, rather than automatically evaluating the latest dates; see the experiment plan before a substantive run.

To acquire an optional newer snapshot, run `python -m factorcast download-data --weighting value`. The downloader preserves the raw ZIP, prepares a decimal-return CSV, records provenance, and never replaces an existing snapshot. Its general output paths remain ignored until a snapshot is deliberately curated and added to the catalog. [docs/data.md](docs/data.md) provides setup, download, and offline preparation instructions.

Current empirical predictors are the current week's **log variance proxies across industries**, plus each outcome industry's own current, four-week, and twelve-week log-variance histories. The response is the next calendar week's log variance proxy. Signed raw returns and macro variables are not currently model inputs.

Saved [weekly feature panels](data/features/kenneth-french/48-industry-daily/2026-10-16/weekly-v1/README.md) now include variance, volatility, log variance, the two trailing means, and daily observation counts for both return weightings. Each panel has 5,228 calendar weeks by 48 industries. Volatility is `sqrt(sum(daily_decimal_return**2))`, without annualization; log variance is `log(sum(daily_decimal_return**2) + 1e-8)`. The empirical CLI still accepts daily returns and reconstructs the same features using the shared feature builder. Verify the saved exports with `python scripts/prepare_weekly_features.py --snapshot-date 2026-10-16 --verify`.

These are weekly close-to-close return-variation proxies, rather than intraday realized variance or observed latent conditional variance. Missing calendar weeks remain missing; no interpolation or future filling occurs. Every comparison uses the same complete-case dates from the full supplied panel. Report coverage loss and recognize that this conservative retrospective sample may depend on future response availability.

The initializer reports log-proxy MSE. Positive variance-scale forecasts, QLIKE, economic utility, variance targeting, transaction costs, and full covariance modeling remain planned analyses in the experiment plan. Exponentiating a log forecast alone does not estimate mean variance. Industry portfolios also require an investability assessment before a trading application.

## Evaluation and saved artifacts

Each outer refit uses only already-realized predictor/outcome pairs. A historical segment within that window evaluates candidate models, with transformations fitted before the validation segment. The selected pipeline is refitted on the full historical window and applied to later forecast origins. Earlier test outcomes may enter subsequent refits only after realization, as in operational forecasting. The implemented horizon is one nonoverlapping period; longer horizons require explicit outcome-interval purging and additional inference.

Each run saves:

- `predictions.csv`: target forecasts, realized outcomes, origin/response dates when available, donor counts, and per-date loss.
- `metrics.csv`: loss by method and fixed donor design, separately for each synthetic seed. Adaptive designs are aggregated as one policy, with donor counts marked `-1`.
- `simulation_summary.csv`: mean loss and Monte Carlo standard error across independent seeds for synthetic runs. A small smoke grid is insufficient for inference.
- `selections.jsonl`: historical validation loss, chosen configuration, fitted lasso support size, and training cutoffs at each refit.
- `diagnostics.csv`: held-out factor alignment error in simulation, using a mapping fitted on historical true factors only.
- `metadata.json`: exact configuration, dependency versions, code/configuration hashes, Git revision and dirty state, and local-data provenance.

Forecast-level records support later paired comparisons and date-block inference. The initializer does not supply empirical confidence intervals or multiple-model-search corrections. Oracle and conditional-mean losses exist only for synthetic data. Curated raw, processed, and weekly feature snapshots are committed to Git with their provenance. Uncurated downloader outputs, generated results, and temporary LaTeX build products remain ignored; the proposal PDF is committed for convenient reading.

## Repository layout and proposal build

```text
proposal/             Concise proposal PDF, independent LaTeX source, bibliography
src/factorcast/        Retrieval, simulation, data/features, models, evaluation, CLI
configs/              Smoke, exploratory simulation, and empirical TOML grids
tests/                Data timing, leakage, pooling, and paired-simulation checks
scripts/              Reproduce and verify curated daily and weekly feature snapshots
docs/data.md          Input schema, source preparation, and proxy interpretation
docs/experiment_plan.md  Detailed experimental protocol and planned extensions
data/README.md        Dataset catalog, snapshot coverage, and provenance links
data/raw/             Curated original source snapshots; other downloads ignored
data/processed/       Curated decimal-return inputs; other prepared files ignored
data/features/        Versioned weekly features, coverage, and provenance, tracked by Git
results/              Generated forecasts and provenance, ignored by Git
```

Build the independent proposal with a standard LaTeX installation:

```bash
cd proposal
pdflatex -interaction=nonstopmode -halt-on-error proposal.tex
bibtex proposal
pdflatex -interaction=nonstopmode -halt-on-error proposal.tex
pdflatex -interaction=nonstopmode -halt-on-error proposal.tex
```

The research sequence is to refine the proposal and literature map, run controlled simulations and a dated-data pilot, then formulate theoretical results around mechanisms that survive those experiments. Negative results about factors or selective sharing are meaningful outcomes.
