# Research data catalog

Curated daily inputs and versioned weekly feature snapshots are stored in this repository and GitHub. Keep original downloads unchanged, record their source and SHA-256 hashes, and add new acquisition dates instead of replacing older snapshots. Generated forecast results stay under the ignored `results/` directory.

## French 48-industry daily returns

| Field | Snapshot |
| --- | --- |
| Provider | Kenneth R. French Data Library; Eugene F. Fama and Kenneth R. French |
| Dataset | 48 industry portfolios, daily returns |
| Acquired | October 16, 2026, America/New_York; precise UTC times in the acquisition record |
| Provider release | August 2026 CRSP database, as stated in the source header |
| Coverage | July 1, 1926 through August 31, 2026 |
| Dimensions | 26,317 daily dates by 48 industries, for each weighting |
| Default | Value-weighted returns; equal-weighted returns retained for sensitivity analysis |
| Units | Raw source: percent; prepared CSVs: decimal returns (`0.01` means 1%) |
| Missing values | Source `-99.99` / `-999` become empty CSV cells; no filling or interpolation |
| Missingness | 56,325 missing cells per weighting in the full history; all 48 industries observed from July 1, 1969 onward |
| Storage | About 22.5 MB for the two raw ZIPs, acquisition record, prepared panels, labels, missingness, and provenance |

Official sources: [dataset construction](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/Data_Library/det_48_ind_port.html), [daily returns ZIP](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/48_Industry_Portfolios_Daily_CSV.zip), [industry definitions ZIP](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/ftp/Siccodes48.zip), and [data library methodology notes](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html). Provider attribution and notices are retained with the original archives; this repository does not relicense the source data.

### Files in the 2026-10-16 snapshot

| File | Contents |
| --- | --- |
| [Original returns ZIP](raw/kenneth-french/48-industry-daily/2026-10-16/48_Industry_Portfolios_Daily_CSV.zip) | Untouched provider archive containing both return weightings and source notes |
| [Original definitions ZIP](raw/kenneth-french/48-industry-daily/2026-10-16/Siccodes48.zip) | Untouched provider industry names and SIC classifications |
| [Acquisition record](raw/kenneth-french/48-industry-daily/2026-10-16/acquisition.json) | Source URLs, original acquisition timestamps, raw sizes, and SHA-256 hashes |
| [Value-weighted returns](processed/kenneth-french/48-industry-daily/2026-10-16/value_weighted_returns_decimal.csv) | Default panel; `date` plus the 48 original industry columns |
| [Equal-weighted returns](processed/kenneth-french/48-industry-daily/2026-10-16/equal_weighted_returns_decimal.csv) | Alternative panel with the same dates and column order |
| [Industry labels](processed/kenneth-french/48-industry-daily/2026-10-16/industry_labels.csv) | Industry number, source code, and full source name; for example, `Food` = Food Products |
| [Missingness and coverage](processed/kenneth-french/48-industry-daily/2026-10-16/missingness.csv) | Observed/missing counts and first/last observed dates by industry and weighting |
| [Preparation provenance](processed/kenneth-french/48-industry-daily/2026-10-16/provenance.json) | Exact file sizes and hashes, source notes, unit conversion, parser normalization, dependency versions, and code fingerprints |

The prepared files preserve every source date and the original industry order. Only headings and unrelated tables are removed, recognized missing sentinels are converted, and nonmissing percentage returns are divided by 100. The provider's CRCRLF line endings are normalized only in the decoded parsing copy; the original ZIP bytes remain untouched. Prepared text uses LF line endings, enforced by `.gitattributes` so recorded checksums survive Windows and Unix checkouts.

These daily portfolio returns have also been transformed into the saved weekly return-variation features below. No experiment date range, forecast model, or evaluation target has been selected by preparing the snapshots. The provider can revise history, and the current release uses CRSP CIZ methodology; this snapshot is a retrospective dataset rather than historical real-time vintages.

### Weekly features: weekly-v1

The [weekly feature specification](features/kenneth-french/48-industry-daily/2026-10-16/weekly-v1/README.md) documents formulas, units, calendar rules, and the reusable API. Both [value-weighted](features/kenneth-french/48-industry-daily/2026-10-16/weekly-v1/value_weighted/) and [equal-weighted](features/kenneth-french/48-industry-daily/2026-10-16/weekly-v1/equal_weighted/) directories contain these six files, each with 5,228 weekly rows and 48 industry columns plus `week_end`:

| File | Feature |
| --- | --- |
| `weekly_variance.csv` | Sum of squared daily decimal returns; at least three observed days required |
| `weekly_volatility.csv` | Square root of weekly variance; not annualized |
| `log_weekly_variance.csv` | Log of weekly variance plus `1e-8` |
| `mean_log_variance_4w.csv` | Arithmetic mean of current and previous three weeks' log variance; complete window required |
| `mean_log_variance_12w.csv` | Arithmetic mean of current and previous eleven weeks' log variance; complete window required |
| `observed_daily_counts.csv` | Nonmissing daily return count for each industry/week |

[Coverage](features/kenneth-french/48-industry-daily/2026-10-16/weekly-v1/coverage.csv) and [feature provenance](features/kenneth-french/48-industry-daily/2026-10-16/weekly-v1/provenance.json) record per-industry availability, source hashes, feature definitions, code fingerprints, and dependency versions. The exports add about 36.1 MB. All calendar weeks remain present without filling. The final week ending September 4, 2026 has one observed day and missing variance/volatility; the last valid measure week is August 28, 2026.

Current empirical predictors are the industry panel's current-week log variance plus each outcome industry's own current, four-week, and twelve-week log-variance histories; the response is next week's log variance. Signed raw returns and macro variables are not currently predictors. The empirical CLI continues to accept daily returns and reconstructs these features with the shared builder.

### Reproduction and use

With the pinned dependencies installed, verify the archived checksums and reproduce the committed prepared files without changing them:

```bash
python scripts/prepare_french48_snapshot.py --snapshot-date 2026-10-16 --verify
python scripts/prepare_weekly_features.py --snapshot-date 2026-10-16 --verify
```

On Windows use `.\.venv\Scripts\python.exe` in place of `python`. Verification also checks recorded preparation code and dependency versions. For a new curated snapshot, preserve the two official ZIPs and an `acquisition.json` with their URLs, original acquisition times, byte counts, and SHA-256 hashes under a new date in `data/raw/kenneth-french/48-industry-daily/`; then run the daily preparation script with that date, without `--verify`. It refuses to replace an existing processed snapshot and carries acquisition records forward without guessing download dates from checkout timestamps. Build the corresponding weekly features with `python scripts/prepare_weekly_features.py --snapshot-date 2026-10-16`, substituting the new date. That script also refuses to overwrite an existing feature snapshot; use a new `--feature-version` for changed feature definitions. Update this catalog after validating the new files.

Use the value-weighted CSV with `units = "decimal"`. Setup and empirical input details are in [docs/data.md](../docs/data.md); the experiment protocol is in [docs/experiment_plan.md](../docs/experiment_plan.md).
