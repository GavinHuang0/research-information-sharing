# Local data and weekly forecast samples

The empirical input is a local CSV with one `date` column and one daily close-to-close return column per asset or industry. Preserve a fixed asset order and use unique asset names. For example:

```csv
date,Agric,Food,Soda
2020-01-06,0.004,-0.002,0.001
2020-01-07,0.003,,0.002
```

Dates must be unique, strictly increasing, timezone-free calendar dates. ISO `YYYY-MM-DD` is recommended; compact `YYYYMMDD` also parses. The loader does not silently sort, deduplicate, impute, or identify return units. Call `load_daily_returns(path, units="decimal")` for values such as `0.01`, or `units="percent"` for values such as `1.0`; both return decimal returns. Empty or recognized missing numeric cells remain missing. Nonnumeric values, infinities, and the known `-99.99`/`-999` missing-value sentinels are rejected. Convert those sentinels explicitly to empty cells during preparation and document that conversion.

## French 48-industry manual adapter

One accessible starting point is the [Kenneth R. French Data Library](https://mba.tuck.dartmouth.edu/pages/faculty/ken.french/data_library.html), specifically the daily 48-industry portfolio returns. Download the original archive yourself, retain its documentation, and extract the intended daily return table into the schema above. State whether the selected portfolios are value-weighted or equal-weighted. Remove textual headings and any unrelated tables, rename the date column to `date`, convert sentinel values to empty cells, retain chronological daily rows, and record the exact first and last date. The source returns are typically reported in percent: verify the original documentation and explicitly pass `units="percent"`. The repository does not contain a live downloader or redistribute source returns; consult the source's use conditions before sharing data.

The industry portfolios are observable proxies for asset information; they are not the model's latent factors. Their squared daily returns supply a close-to-close weekly variance proxy, not intraday realized variance. Diversification within portfolios, industry composition changes, and coverage differences limit interpretation. A comparison across 48 industries measures panel composition and size in this particular proxy universe; extending it to individual stocks or other markets requires a separate source and experiment. The provider rebuilds historical files; record the downloaded version and hash rather than assume an unchanged history. French-library documentation also distinguishes the FIZ and CIZ source formats around January 2025; retain the accompanying methodology notes and identify any sample crossing that transition.

Store downloaded originals under `data/raw/` locally, and adapted inputs under `data/processed/`, or provide an external path to the runner. Data files should not be committed. In addition to the loader's source path, SHA-256 content hash, declared source units, row count, and asset missingness, retain a local provenance note with the source URL, download date, archive filename, portfolio weighting, manual conversion steps, source version, and any use restrictions. The runner should include the loader metadata and feature report in experiment outputs. A content hash identifies the supplied local CSV; it does not certify licensing or make an unrecorded preprocessing decision reproducible.

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
