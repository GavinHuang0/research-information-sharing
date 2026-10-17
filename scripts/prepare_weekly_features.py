"""Build or verify causal weekly industry features from an archived daily snapshot.

python scripts/prepare_weekly_features.py --snapshot-date 2026-10-16
python scripts/prepare_weekly_features.py --snapshot-date 2026-10-16 --verify

All paths are relative to the repository, independent of the working directory.
"""

from __future__ import annotations

import argparse
from datetime import date, datetime, timezone
import hashlib
from importlib.metadata import version
import json
from pathlib import Path
import sys

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from factorcast.data import load_daily_returns
from factorcast.features import build_weekly_feature_panels

FEATURES = {
    "variance": ("weekly_variance.csv", "sum_daily_decimal_returns_squared", "decimal_return_squared"),
    "volatility": ("weekly_volatility.csv", "sqrt_weekly_variance", "decimal_return"),
    "log_variance": ("log_weekly_variance.csv", "log_weekly_variance_plus_offset", "log_decimal_return_squared"),
    "log_variance_mean_4w": ("mean_log_variance_4w.csv", "arithmetic_mean_log_variance_current_and_previous_3_weeks", "log_decimal_return_squared"),
    "log_variance_mean_12w": ("mean_log_variance_12w.csv", "arithmetic_mean_log_variance_current_and_previous_11_weeks", "log_decimal_return_squared"),
    "observed_daily_counts": ("observed_daily_counts.csv", "count_nonmissing_source_daily_returns", "observations"),
}


def digest(contents: bytes) -> str:
    return hashlib.sha256(contents).hexdigest()


def relative(path: Path) -> str:
    return path.relative_to(ROOT).as_posix()


def serialize(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=True, index_label="week_end", date_format="%Y-%m-%d",
                        na_rep="", float_format="%.12g", lineterminator="\n").encode("utf-8")


def first_last(mask: pd.Series) -> dict:
    dates = mask.index[mask.to_numpy(dtype=bool)]
    return dict(weeks=int(mask.sum()), first_week_end=None if dates.empty else dates[0].date().isoformat(),
                last_week_end=None if dates.empty else dates[-1].date().isoformat())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--snapshot-date", required=True, type=date.fromisoformat)
    parser.add_argument("--min-week-obs", type=int, default=3)
    parser.add_argument("--log-offset", type=float, default=1e-8)
    parser.add_argument("--feature-version", default="weekly-v1", help="New folder for a changed feature definition")
    parser.add_argument("--verify", action="store_true", help="Recompute and compare without writing")
    args = parser.parse_args()
    if not args.feature_version or any(char not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-_" for char in args.feature_version):
        parser.error("feature-version must contain only letters, digits, hyphens, or underscores")
    dataset_path = Path("kenneth-french/48-industry-daily") / args.snapshot_date.isoformat()
    input_root = ROOT / "data/processed" / dataset_path
    output_root = ROOT / "data/features" / dataset_path / args.feature_version
    if output_root.exists() and not args.verify:
        parser.error(f"Refusing to overwrite existing features: {output_root}")
    if args.verify and not output_root.is_dir():
        parser.error(f"Feature snapshot does not exist: {output_root}")

    daily_provenance_path = input_root / "provenance.json"
    daily_provenance_bytes = daily_provenance_path.read_bytes()
    daily_provenance = json.loads(daily_provenance_bytes)
    labels_path = input_root / "industry_labels.csv"
    labels_bytes = labels_path.read_bytes()
    label_record = next(item for item in daily_provenance["auxiliary_files"] if item["path"] == relative(labels_path))
    if digest(labels_bytes) != label_record["sha256"]:
        parser.error("Industry-label checksum differs from the daily snapshot")
    label_table = pd.read_csv(labels_path)
    names = dict(zip(label_table["industry_code"], label_table["industry_name"]))
    outputs: dict[str, bytes] = {}
    reports = {}
    input_records = []
    coverage = []
    for weighting in ("value", "equal"):
        source = daily_provenance["panels"][weighting]
        path = ROOT / source["path"]
        contents = path.read_bytes()
        if digest(contents) != source["sha256"] or len(contents) != source["bytes"]:
            parser.error(f"Input checksum or size mismatch: {relative(path)}")
        returns = load_daily_returns(path, units="decimal")
        if list(returns.columns) != list(label_table["industry_code"]):
            parser.error("Industry label order differs from return columns")
        panels = build_weekly_feature_panels(returns, min_week_obs=args.min_week_obs, log_offset=args.log_offset)
        input_records.append(dict(weighting=weighting, path=relative(path), sha256=digest(contents), bytes=len(contents)))
        for key, frame in panels.as_dict().items():
            filename = FEATURES[key][0]
            outputs[f"{weighting}_weighted/{filename}"] = serialize(frame)
        all_current = panels.variance.notna().all(axis=1)
        all_history = panels.log_variance_mean_12w.notna().all(axis=1)
        reports[weighting] = dict(calendar_weeks=len(panels.variance), industries=len(returns.columns),
                                 first_week_end=panels.variance.index[0].date().isoformat(),
                                 last_week_end=panels.variance.index[-1].date().isoformat(),
                                 source_first_date=returns.index[0].date().isoformat(),
                                 source_last_date=returns.index[-1].date().isoformat(),
                                 all_current_available=first_last(all_current),
                                 all_histories_available=first_last(all_history),
                                 first_calendar_week_daily_obs_min=int(panels.observed_daily_counts.iloc[0].min()),
                                 first_calendar_week_daily_obs_max=int(panels.observed_daily_counts.iloc[0].max()),
                                 last_calendar_week_daily_obs_min=int(panels.observed_daily_counts.iloc[-1].min()),
                                 last_calendar_week_daily_obs_max=int(panels.observed_daily_counts.iloc[-1].max()),
                                 observed_daily_counts_max=int(panels.observed_daily_counts.to_numpy().max()))
        for code in returns.columns:
            available = panels.variance[code].notna()
            coverage.append(dict(weighting=weighting, industry_code=code, industry_name=names[code],
                                 valid_variance_weeks=int(available.sum()), missing_variance_weeks=int((~available).sum()),
                                 first_valid_week=first_last(available)["first_week_end"],
                                 last_valid_week=first_last(available)["last_week_end"],
                                 valid_history_4w_weeks=int(panels.log_variance_mean_4w[code].notna().sum()),
                                 valid_history_12w_weeks=int(panels.log_variance_mean_12w[code].notna().sum())))
    outputs["coverage.csv"] = pd.DataFrame(coverage).to_csv(index=False, na_rep="", lineterminator="\n").encode("utf-8")

    code_paths = (Path(__file__).resolve(), ROOT / "src/factorcast/features.py", ROOT / "src/factorcast/data.py")
    metadata = dict(
        schema_version=1, dataset_id="kenneth-french/48-industry-daily", source_snapshot_date=args.snapshot_date.isoformat(),
        feature_version=args.feature_version, prepared_at_utc=datetime.now(timezone.utc).isoformat(),
        input_provenance=dict(path=relative(daily_provenance_path), sha256=digest(daily_provenance_bytes)),
        inputs=input_records, industry_labels=dict(path=relative(labels_path), sha256=digest(labels_bytes)),
        definitions=dict(frequency="W-FRI", interval="(previous_Friday,current_Friday]", available_at="after_origin_Friday_close_in_fixed_source_snapshot",
                         minimum_observed_daily_returns=args.min_week_obs, log_offset=args.log_offset,
                         logarithm="natural", history_windows_weeks=[1, 4, 12],
                         rolling_window="current_week_and_preceding_calendar_weeks_require_complete_window",
                         calendar_policy="retain_all_intervening_and_partial_endpoint_calendar_weeks",
                         endpoint_policy="same_minimum_count_rule_as_other_weeks; final_incomplete_week_may_have_only_counts",
                         missingness_policy="no_fill_no_interpolation; insufficient_count_measures_are_missing",
                         annualization="none", centering="none", scaling_or_fitted_transforms="none",
                         note="Close-to-close return-variation proxies, not intraday realized variance or latent conditional variance. Historic Saturday observations are included, so counts can exceed five.",
                         features={key: dict(filename=value[0], formula=value[1], units=value[2]) for key, value in FEATURES.items()}),
        forecast_usage=dict(measurement_predictors="current_log_weekly_variance_of_selected_industries",
                            own_history_controls="current_log_weekly_variance_and_trailing_4w_12w_means_for_each_outcome_industry",
                            forecast_target="next_calendar_week_log_variance_created_separately_by_build_weekly_dataset",
                            signed_return_predictors=False, future_outcomes_in_feature_files=False,
                            standardization_and_PCA="fit_on_training_observations_only_at_forecast_time"),
        reports=reports,
        preparation=dict(command=f"python scripts/prepare_weekly_features.py --snapshot-date {args.snapshot_date} --min-week-obs {args.min_week_obs} --log-offset {args.log_offset} --feature-version {args.feature_version}",
                         code=[dict(path=relative(path), sha256_lf=digest(path.read_bytes().replace(b"\r\n", b"\n"))) for path in code_paths],
                         python=sys.version.split()[0], packages={name: version(name) for name in ("numpy", "pandas")},
                         text_encoding="utf-8", line_ending="LF", float_format="%.12g"),
        files=[dict(path=relative(output_root / name), sha256=digest(contents), bytes=len(contents)) for name, contents in outputs.items()],
    )
    if args.verify:
        existing = json.loads((output_root / "provenance.json").read_bytes())
        metadata["prepared_at_utc"] = existing["prepared_at_utc"]
        if metadata != existing:
            parser.error("Feature provenance differs from inputs, definitions, outputs, code, or dependency versions")
        for name, contents in outputs.items():
            if (output_root / name).read_bytes() != contents:
                parser.error(f"Feature reproduction differs: {name}")
        print("Verified all weekly feature panels, counts, coverage, and provenance.")
        return
    outputs["provenance.json"] = (json.dumps(metadata, indent=2, sort_keys=True) + "\n").encode("utf-8")
    output_root.mkdir(parents=True, exist_ok=False)
    for name, contents in outputs.items():
        path = output_root / name
        path.parent.mkdir(exist_ok=True)
        with path.open("xb") as handle:
            handle.write(contents)
    print(json.dumps(dict(output=relative(output_root), bytes=sum(map(len, outputs.values())), reports=reports), indent=2))


if __name__ == "__main__":
    main()
