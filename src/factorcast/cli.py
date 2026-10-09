"""Command line entry points for synthetic pilots and researcher-supplied CSVs."""

import argparse
from pathlib import Path
import tomllib

from .data import load_daily_returns
from .experiments import evaluate_panel, run_simulation, save_results
from .features import build_weekly_dataset


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("simulate", "empirical"):
        command = commands.add_parser(name)
        command.add_argument("--config", type=Path, required=True)
        command.add_argument("--output", type=Path, required=True, help="New results directory")
        if name == "empirical":
            command.add_argument("--returns", type=Path, required=True)
            command.add_argument("--target", required=True)
    args = parser.parse_args(argv)
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
