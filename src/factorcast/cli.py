"""Download industry data, run synthetic pilots, and evaluate local CSVs."""

import argparse
import json
from pathlib import Path
import tomllib

from .data import load_daily_returns
from .experiments import evaluate_panel, run_simulation, save_results
from .features import build_weekly_dataset
from .retrieval import download_french48


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    download = commands.add_parser("download-data", help="Retrieve and prepare French daily 48-industry returns")
    download.add_argument("--weighting", choices=("value", "equal"), default="value")
    download.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
    download.add_argument("--processed-dir", type=Path, default=Path("data/processed"))
    download.add_argument("--archive", type=Path, help="Prepare an already-downloaded official ZIP offline")
    download.add_argument("--json", action="store_true", help="Print snapshot paths and metadata as JSON")
    for name in ("simulate", "empirical"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True, help="New results directory")
        if name == "empirical":
            command.add_argument("--returns", type=Path, required=True)
            command.add_argument("--target", required=True)
    args = parser.parse_args(argv)
    if args.command == "download-data":
        try:
            snapshot = download_french48(raw_dir=args.raw_dir, processed_dir=args.processed_dir,
                                         weighting=args.weighting, archive_path=args.archive)
        except (OSError, ValueError, RuntimeError) as exc:
            parser.error(f"Data retrieval failed: {str(exc).rstrip('.')}. See docs/data.md for the local archive option.")
        paths = dict(raw_archive=str(snapshot.raw_archive_path), returns_csv=str(snapshot.processed_csv_path),
                     provenance=str(snapshot.provenance_path))
        if args.json:
            print(json.dumps(dict(paths, metadata=snapshot.metadata), indent=2, sort_keys=True))
        else:
            print(f"Raw archive: {paths['raw_archive']}")
            print(f"Prepared daily returns (decimal units): {paths['returns_csv']}")
            print(f"Provenance: {paths['provenance']}")
            print("Use the prepared CSV with configs/empirical.toml (units = decimal).")
        return
    if args.output.exists():
        parser.error("Output already exists; choose a new directory to preserve results")
    config = tomllib.loads(args.config.read_text())
    if args.command == "simulate":
        results, provenance = run_simulation(config), None
    else:
        daily = load_daily_returns(args.returns, units=config["data"]["units"])
        dataset = build_weekly_dataset(daily, target=args.target,
                                       log_offset=config["data"]["log_offset"],
                                       min_week_obs=config["data"]["min_week_obs"])
        index = dataset.asset_names.index(args.target)
        order = [index]+[i for i in range(len(dataset.asset_names)) if i != index]
        results = evaluate_panel(dataset.X[:, order], dataset.Y[:, order], config["experiment"],
                                 dict(target=args.target), local=dataset.local_all[:, order, :],
                                 dates=dataset.origin_dates, response_dates=dataset.response_dates)
        provenance = dict(dataset.report, nested_asset_order=[dataset.asset_names[i] for i in order])
    output = save_results(args.output, config, results, config_path=args.config, provenance=provenance)
    print(f"Saved forecasts, metrics, selections and provenance to {output}")


if __name__ == "__main__":
    main()
