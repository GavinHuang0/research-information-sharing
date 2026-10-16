# Data retrieval and weekly forecast samples

## Included data snapshot

A checkout includes the curated **2026-10-16 French daily 48-industry snapshot**. The [data catalog](../data/README.md) records coverage, file sizes, hashes, and provenance. Files are organized by provider, dataset, and acquisition date:

| File | Purpose |
| --- | --- |
| `data/raw/kenneth-french/48-industry-daily/2026-10-16/48_Industry_Portfolios_Daily_CSV.zip` | Unmodified source archive, including provider notes |
| `data/raw/kenneth-french/48-industry-daily/2026-10-16/Siccodes48.zip` | Original industry names and SIC classifications |
| `data/raw/kenneth-french/48-industry-daily/2026-10-16/acquisition.json` | Original download timestamps, source URLs, and raw hashes |
| `data/processed/kenneth-french/48-industry-daily/2026-10-16/value_weighted_returns_decimal.csv` | Default input for the first experiment |
| `data/processed/kenneth-french/48-industry-daily/2026-10-16/equal_weighted_returns_decimal.csv` | Alternative weighting for a later sensitivity check |
| `data/processed/kenneth-french/48-industry-daily/2026-10-16/industry_labels.csv` | Industry codes and full provider names |
| `data/processed/kenneth-french/48-industry-daily/2026-10-16/missingness.csv` | Per-industry coverage and missingness for both weightings |
| `data/processed/kenneth-french/48-industry-daily/2026-10-16/provenance.json` | Acquisition, preparation, validation, and content hashes |

These curated files are tracked in Git and stored in GitHub. General downloader output remains ignored until deliberately selected for inclusion; generated experiment results remain ignored. Preserve older curated snapshots when adding a new one because the provider can revise history. The catalog provides the offline preparation and verification commands; `.gitattributes` preserves prepared text line endings for stable checksums across operating systems.

## Setup and optional fresh downloads

The downloader retrieves the official [French daily 48-industry CSV archive](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/48_Industry_Portfolios_Daily_CSV.zip). It selects value-weighted returns by default, writes a validated **decimal-return** CSV, preserves the original ZIP, and records provenance. The source is the [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html); its [industry definitions and construction](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_48_ind_port.html) describe the portfolio universe. Retain the provider's accompanying documentation and use conditions.

For a new checkout on macOS or Linux, with Python 3.11 or later:

```bash
git clone https://github.com/GavinHuang0/research-information-sharing.git
cd research-information-sharing
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements-lock.txt
python -m pip install --no-deps --no-build-isolation -e .
```

If the repository requires authentication, Git must already be authenticated to your GitHub account. If you already have a checkout, update it with `git pull --ff-only` and continue with setup. Python 3.12 matches the pinned dependency environment. The committed snapshot is ready to use after installation; downloading again is optional.

On Windows PowerShell, after cloning and entering the repository:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-lock.txt
.\.venv\Scripts\python.exe -m pip install --no-deps --no-build-isolation -e .
```

No virtual-environment activation is required with these explicit Windows paths. To acquire a newer source snapshot, run:

```bash
python -m factorcast download-data --weighting value
```

The downloader prints the raw ZIP path, prepared CSV path, and provenance JSON path. Each invocation creates a new snapshot; an existing snapshot is never replaced. Raw files are stored beneath `data/raw/` and prepared files beneath `data/processed/`. These general output paths are ignored by Git; the curated paths listed above are explicit exceptions. Set `--raw-dir` and `--processed-dir` to choose another destination, and `--weighting equal` for the equal-weighted daily table. `--json` prints machine-readable paths and metadata. To curate another snapshot, retain the raw archive and provenance, use a provider/dataset/acquisition-date folder, add explicit Git ignore exceptions, and update the data catalog.

If your network blocks automatic retrieval, download the [official ZIP](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/48_Industry_Portfolios_Daily_CSV.zip) through your browser, then prepare it without a network request:

```bash
python -m factorcast download-data --archive "/path/to/48_Industry_Portfolios_Daily_CSV.zip" --weighting value
```

On Windows, use `.\.venv\Scripts\python.exe -m factorcast` and your downloaded ZIP's Windows path. The offline adapter performs the same selection, validation, and unit conversion. This is also the way to prepare an archived source snapshot later without downloading a revised history.

When ready to run an experiment, use the committed value-weighted input:

```bash
python -m factorcast empirical --config configs/empirical.toml \
  --returns data/processed/kenneth-french/48-industry-daily/2026-10-16/value_weighted_returns_decimal.csv \
  --target Food --output results/industry-food
```

For a newer download, substitute the prepared CSV path printed by the downloader. On Windows PowerShell, call `.\.venv\Scripts\python.exe -m factorcast` and put the command on one line. Prepared inputs already contain decimal returns: retain `units = "decimal"` in this configuration. Review [experiment_plan.md](experiment_plan.md), select the intended calendar sample, and adjust split sizes before interpreting a run as research evidence. Downloading or committing data does not itself run the forecast experiment.

## Retrieval validation and provenance

The adapter distinguishes daily value- and equal-weighted sections, validates 48 unique industry columns and chronological daily rows, and converts the source's `-99.99` and `-999` missing-value sentinels into missing cells **before** converting percentage returns to decimal units. It leaves missing observations missing. A missing or malformed table produces an error rather than a guessed dataset. It records source URL, acquisition mode, timestamps, raw and prepared hashes, ZIP member name, weighting, source notes, units, date span, and missingness. Preserve that provenance JSON alongside the CSV; experiment outputs separately record the exact supplied CSV hash and units.

The raw archive and CSV decoding have explicit size bounds, and CSV members are read directly without extracting archive paths. Network retrieval preserves standard proxy settings and TLS certificate verification. Code checks use realistic test fixtures and mocked downloads; accessing the live source still depends on the network where you run the command.

## Other local CSV inputs

The empirical input is a local CSV with one `date` column and one daily close-to-close return column per asset or industry. Preserve a fixed asset order and use unique asset names. For example:

```csv
date,Agric,Food,Soda
2020-01-06,0.004,-0.002,0.001
2020-01-07,0.003,,0.002
```

Dates must be unique, strictly increasing, timezone-free calendar dates. ISO `YYYY-MM-DD` is recommended; compact `YYYYMMDD` also parses. The loader does not silently sort, deduplicate, impute, or identify return units. Call `load_daily_returns(path, units="decimal")` for values such as `0.01`, or `units="percent"` for values such as `1.0`; both return decimal returns. Empty or recognized missing numeric cells remain missing. Nonnumeric values, infinities, and the known `-99.99`/`-999` missing-value sentinels are rejected. Convert those sentinels explicitly to empty cells during preparation and document that conversion.

## French 48-industry manual adapter (alternative)

The automatic adapter is recommended. If preparing a CSV manually instead, retain the original archive and its documentation, identify the daily value- or equal-weighted table, remove headings and unrelated tables, rename the date column to `date`, explicitly replace sentinels with empty cells, and record the date span. A manually prepared CSV retaining the provider's percentage units requires `units="percent"`; use `units="decimal"` only after conversion.

The industry portfolios are observable proxies for asset information; they are not the model's latent factors. Their squared daily returns supply a close-to-close weekly variance proxy, not intraday realized variance. Diversification within portfolios, industry composition changes, and coverage differences limit interpretation. A comparison across 48 industries measures panel composition and size in this particular proxy universe; extending it to individual stocks or other markets requires a separate source and experiment. The provider rebuilds historical files; record the downloaded version and hash rather than assume an unchanged history. French-library documentation also distinguishes the FIZ and CIZ source formats around January 2025; retain the accompanying methodology notes and identify any sample crossing that transition.

Store downloaded originals under `data/raw/` and adapted inputs under `data/processed/`, or provide an external path to the runner. Curated snapshots are committed with provenance and a catalog entry; ad hoc downloads and generated experiment outputs remain ignored. In addition to the loader's source path, SHA-256 content hash, declared source units, row count, and asset missingness, retain the source URL, download date, archive filename, portfolio weighting, conversion steps, source version, and any use restrictions. The runner should include the loader metadata and feature report in experiment outputs. A content hash identifies the supplied CSV; it does not certify licensing or make an unrecorded preprocessing decision reproducible.

## Calendar and target construction

`weekly_variance(returns, min_week_obs=3)` sums squared **decimal** daily returns in Friday-ending calendar weeks (`W-FRI`). Each asset needs at least the configured number of observed daily returns; a three-day holiday week can therefore be retained with the default. The threshold is a measurement choice and should be reported and checked in sensitivity analysis. A week with too few returns remains missing, and completely absent weeks remain in the calendar grid. There is no forward or backward fill. Partial endpoint weeks are treated by the same count rule; the input period should be chosen and reported deliberately.

`build_weekly_dataset(returns, target="Food", log_offset=1e-8, min_week_obs=3)` forms `q = log(V + c)` using the declared fixed positive offset `c`. This initializer uses `1e-8` in decimal-return-squared units. It is a convention, not a value estimated from the test period; alternate offsets should be declared in sensitivity runs. The three own-history controls are `q_t`, the mean of `q` over the last four calendar weeks through `t`, and the mean over the last twelve weeks through `t`. These are arithmetic means of **log** proxies, not logs of mean variance. Every week in a history must be observed.

The dataset has the following API:

| Attribute | Shape or content |
| --- | --- |
| `X` | `(T, N)` origin-week panel log proxies |
| `Y` | `(T, N)` next-calendar-week panel log proxies |
| `local_all` | `(T, N, 3)` each asset's trailing 1/4/12-week controls |
| `local` | `(T, 3)` controls for the named target |
| `y` | `(T,)` next-week log proxy for the named target |
| `origin_dates`, `response_dates` | Friday labels, with responses exactly seven days after origins |
| `asset_names`, `target_name`, `target_index` | Stable input names and the target's position |
| `report` | JSON-serializable configuration, source metadata and sample-loss counts |

All methods share one explicit complete-case sample: every asset must have a finite current predictor, finite next-week response, and complete own histories. This permits pooled own-history controls and prevents method comparisons from accidentally using different dates. It is deliberately conservative and may reduce coverage sharply in sparse panels. A missing target or panel week can remove its preceding forecast origin and later origins whose histories include that hole. Calendar lags are formed **before** deleting incomplete rows, so a missing week can never make a two-week outcome look like a one-week forecast. Missingness counts overlap and should not be added as if they were disjoint reasons. Construct the full panel once before comparing asset subsets so that changing panel size cannot silently change the sample.

Weekly target construction and histories use only daily returns at or before their origin. The next-week response is stored separately. Any estimated imputation, standardization, factor extraction, regression, panel selection, or tuning belongs inside the training portion of a chronological experiment. The dataset's current-week values presuppose an end-of-Friday forecasting origin after that week's closing returns are available. With sparse observed weeks, adjacent retained rows may be more than a week apart; their responses still refer to exactly the next calendar week.
