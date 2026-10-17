# Weekly industry volatility features

These features use the [2026-10-16 French daily 48-industry snapshot](../../../../../README.md). Each panel preserves all **5,228 Friday-ending calendar weeks** from **1926-07-02 through 2026-09-04**, in chronological order, with `week_end` followed by the same 48 industry codes as the daily source. Both [value-weighted](value_weighted/) and [equal-weighted](equal_weighted/) versions are retained. Value-weighted is the initial default.

## Feature definitions

Let `r[i,d]` be industry `i`'s daily decimal return, and let week `w` contain dates strictly after the preceding Friday through the current Friday. At least **three observed daily returns** are required per industry/week.

| CSV, inside each weighting folder | Definition | Units / interpretation |
| --- | --- | --- |
| `weekly_variance.csv` | `Q[i,w] = sum(r[i,d]^2)` | Uncentered close-to-close return-variation proxy; decimal returns squared |
| `weekly_volatility.csv` | `sqrt(Q[i,w])` | Weekly volatility proxy in decimal return units; `0.02` means 2% |
| `log_weekly_variance.csv` | `v[i,w] = log(Q[i,w] + 1e-8)` | Natural log of the variance proxy plus a fixed offset |
| `mean_log_variance_4w.csv` | `(v[i,w] + ... + v[i,w-3]) / 4` | Trailing mean of weekly log variance, including the current week |
| `mean_log_variance_12w.csv` | `(v[i,w] + ... + v[i,w-11]) / 12` | Trailing mean of weekly log variance, including the current week |
| `observed_daily_counts.csv` | Count of nonmissing daily source returns in the week | Integer observations; retained even if insufficient for a valid variance proxy |

The rolling features are **means of log variance**, rather than logs of mean variance, and are not volatility over a combined four- or twelve-week holding period. No annualization, sample-mean subtraction, fitted standardization, factor estimation, interpolation, or missing-value filling is applied.

The current predictor representation is the selected industries' current-week `v` values. Each outcome industry also has its own current `v`, trailing four-week mean, and trailing twelve-week mean as local controls. The forecasting code creates **next calendar week's log variance** as the response separately; none of these feature CSVs contains future outcomes or signed-return predictors. The target's current `v` can appear in both the measurement panel and its local history controls. Scaling, PCA, and model fitting remain inside each chronological training window.

## Coverage and timing

Missing calendar weeks remain on the grid. An industry/week with fewer than three returns has empty variance, volatility, and log-variance cells. Rolling features require all four or twelve calendar weeks to be valid, so an internal missing week also invalidates subsequent windows until it leaves the window. The feature files do not apply the later forecast runner's common-case sample selection.

The first calendar week has at most two daily observations, and the final week labeled **2026-09-04** has only the **2026-08-31** observation; their measures remain missing under the same three-observation rule. Do not interpret the final label as an observed complete September week. The latest valid weekly measures end **2026-08-28**. All 48 industries first have valid measures together in the week ending **1969-07-04**, and complete twelve-week histories together in **1969-09-19**. Some later holiday/closure weeks also fail the count rule; see [coverage.csv](coverage.csv).

The original historical data includes Saturday trading. Friday-ending bins therefore include Saturday observations after the preceding Friday, and counts can reach six. Holiday-short and historical six-day weeks have different observed-day exposure; this version preserves their sum-of-squares definition and reports counts instead of silently normalizing them.

Features at week `w` use source dates at or before its Friday label. This is a fixed retrospective source snapshot and does not claim that the provider's revised historical data was available in real time. The measures are proxies based on daily returns, not intraday realized variance or directly observed latent conditional volatility.

## Provenance and verification

[provenance.json](provenance.json) records input hashes, exact definitions, thresholds, source dates, output checksums and sizes, code fingerprints, and dependency versions. [coverage.csv](coverage.csv) reports per-industry availability for both weightings. Industry labels remain in the [source snapshot's industry map](../../../../../processed/kenneth-french/48-industry-daily/2026-10-16/industry_labels.csv).

From the repository root, with the pinned dependencies installed:

```bash
python scripts/prepare_weekly_features.py --snapshot-date 2026-10-16 --verify
```

On Windows, use `.\.venv\Scripts\python.exe` in place of `python`. The command reproduces and compares all panels without writing changes. To prepare a new feature snapshot, omit `--verify`; existing output folders are never overwritten. Give changed feature definitions a new `--feature-version` and update the catalog after validation.
