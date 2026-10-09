"""Reproducible pilot runner; no test loss participates in model selection."""

from hashlib import sha256
from importlib.metadata import version
from itertools import product
import json
from pathlib import Path
import platform
import subprocess
import sys

import numpy as np
import pandas as pd
from sklearn.linear_model import LinearRegression

from .evaluation import factor_diagnostics, forecast_blocks, mse
from .models import (
    DirectForecaster, FactorForecaster, OracleForecaster, PCARepresentation,
    PLSForecaster,
)
from .simulation import SimulationConfig, generate_panel


FACTOR_METHODS = ("factor_separate", "factor_pooled", "factor_partial", "factor_lasso")


class _InfeasibleCandidate(ValueError):
    pass


def candidates(settings, n_measurements, n_outcomes):
    """Finite, predeclared candidate grid, with donor sets as nested prefixes."""
    for method in FACTOR_METHODS:
        penalties = (settings["pooling_penalties"] if method == "factor_partial"
                     else settings["lasso_penalties"] if method == "factor_lasso" else [0.0])
        for k, penalty in product(settings["factor_counts"], penalties):
            yield dict(method=method, n_measurements=n_measurements,
                       n_outcomes=n_outcomes, k=k, penalty=penalty)
    if n_outcomes == settings["outcome_assets"][0]:
        for method, penalties in (("direct_ridge", settings["ridge_penalties"]),
                                 ("direct_elasticnet", settings["lasso_penalties"])):
            for penalty in penalties:
                yield dict(method=method, n_measurements=n_measurements,
                           n_outcomes=1, k=0, penalty=penalty)
        for k in settings["factor_counts"]:
            yield dict(method="pls", n_measurements=n_measurements,
                       n_outcomes=1, k=k, penalty=0.0)


def _fit(candidate, X, Y, local, rows, representations, stage):
    nm, no = candidate["n_measurements"], candidate["n_outcomes"]
    x, y = X[rows, :nm], Y[rows, :no]
    controls = None if local is None else local[rows, :no, :]
    method, k, penalty = candidate["method"], candidate["k"], candidate["penalty"]
    if method in FACTOR_METHODS:
        key = (stage, nm, k)
        if key not in representations:
            representations[key] = PCARepresentation(k).fit(x)
        pooling = {"factor_separate": "separate", "factor_lasso": "separate",
                   "factor_pooled": "pooled", "factor_partial": "partial"}[method]
        model = FactorForecaster(
            n_factors=k, pooling=pooling,
            penalty=penalty if method == "factor_partial" else 0.0,
            slope_penalty=penalty if method == "factor_lasso" else 0.0,
            representation=representations[key],
        ).fit(x, y, local=controls)
    else:
        model = (PLSForecaster(k) if method == "pls" else
                 DirectForecaster(method=method.removeprefix("direct_"), penalty=penalty))
        if controls is None:
            model.fit(x, y)
        else:
            # Apply the same unpenalized own-history controls as factor models.
            # FWL uses training projections, also for new raw predictor rows.
            design = np.column_stack([np.ones(len(x)), controls[:, 0, :]])
            x_projection = np.linalg.lstsq(design, x, rcond=None)[0]
            y_projection = np.linalg.lstsq(design, y[:, 0], rcond=None)[0]
            residual_x = x - design @ x_projection
            # Current target proxy is also an own-history control. Avoid
            # amplifying floating-point residue into a standardized predictor.
            mask = residual_x.std(axis=0) > 1e-10 * np.maximum(x.std(axis=0), 1.0)
            if method == "pls" and k > int(mask.sum()):
                raise _InfeasibleCandidate("PLS dimension exceeds nonconstant residual predictors")
            if mask.any():
                model.fit(residual_x[:, mask], y[:, 0] - design @ y_projection)
            model.local_only_ = not mask.any()
            model.local_feature_mask_ = mask
            model.local_x_projection_ = x_projection
            model.local_y_projection_ = y_projection
    return model


def _predict(candidate, model, X, local, rows):
    x = X[rows, :candidate["n_measurements"]]
    controls = None if local is None else local[rows, :candidate["n_outcomes"], :]
    if candidate["method"] in FACTOR_METHODS:
        return model.predict(x, local=controls)
    if controls is None:
        return model.predict(x)
    design = np.column_stack([np.ones(len(x)), controls[:, 0, :]])
    if model.local_only_:
        return design @ model.local_y_projection_
    return (design @ model.local_y_projection_
            + model.predict((x - design @ model.local_x_projection_)[:, model.local_feature_mask_]))


def evaluate_panel(X, Y, settings, context, *, local=None, factors=None,
                   conditional_mean=None, dates=None, response_dates=None):
    """Return forecasts, selection records and simulation-only diagnostics.

    Same target (column zero), calendar rows and generated maximum panel are
    used in every donor comparison. Joint selection searches both donor sets
    and the factor/penalty grid against historical target validation MSE.
    """
    validate_settings(settings, len(X), X.shape[1], Y.shape[1])
    forecasts, selections, diagnostics = [], [], []
    all_candidates = [c for nm, no in product(settings["measurement_assets"], settings["outcome_assets"])
                      for c in candidates(settings, nm, no)]
    blocks = forecast_blocks(len(X), settings["initial_train"], settings["validation_size"],
                             settings["test_size"], settings["refit_every"])
    for block in blocks:
        representations, winners, adaptive = {}, {}, None
        for candidate in all_candidates:
            try:
                model = _fit(candidate, X, Y, local, block.train, representations, "inner")
            except _InfeasibleCandidate:
                # A declared PLS candidate may be infeasible after local FWL.
                continue
            score = mse(Y[block.validation, 0], _predict(candidate, model, X, local, block.validation))
            key = (candidate["method"], candidate["n_measurements"], candidate["n_outcomes"])
            if key not in winners or score < winners[key][0]:
                winners[key] = (score, candidate)
            if candidate["method"] in FACTOR_METHODS and (adaptive is None or score < adaptive[0]):
                adaptive = (score, candidate)
        chosen = [(c["method"], score, c) for score, c in winners.values()]
        chosen.append(("adaptive_factor", adaptive[0], adaptive[1]))
        for label, score, candidate in chosen:
            model = _fit(candidate, X, Y, local, block.history, representations, "outer")
            predictions = _predict(candidate, model, X, local, block.test)
            selections.append(dict(context, method=label, refit_origin=block.test.start,
                                   validation_mse=score, **{k: v for k, v in candidate.items() if k != "method"},
                                   selected_method=candidate["method"],
                                   active_factor_slopes=int(np.count_nonzero(np.abs(model.slopes_[:, 0]) > 1e-8))
                                   if candidate["method"] in FACTOR_METHODS else None,
                                   inner_train_stop=block.train.stop, history_stop=block.history.stop))
            _append_forecasts(forecasts, context, label, candidate, block, predictions,
                              Y, conditional_mean, dates, response_dates)
            if factors is not None and candidate["method"] in FACTOR_METHODS:
                rep = representations[("outer", candidate["n_measurements"], candidate["k"])]
                nm = candidate["n_measurements"]
                diagnostic = factor_diagnostics(rep.transform(X[block.history, :nm]),
                                                factors[block.history], rep.transform(X[block.test, :nm]),
                                                factors[block.test])
                diagnostics.append(dict(context, method=label, refit_origin=block.test.start,
                                        n_measurements=nm, n_outcomes=candidate["n_outcomes"],
                                        k=candidate["k"], penalty=candidate["penalty"],
                                        selected_method=candidate["method"], aligned_factor_mse=diagnostic))
        if factors is not None:
            oracle = OracleForecaster().fit(factors[block.history], Y[block.history])
            c = dict(n_measurements=0, n_outcomes=1, k=factors.shape[1], penalty=0.0)
            _append_forecasts(forecasts, context, "oracle_factors", c, block,
                              oracle.predict(factors[block.test]), Y, conditional_mean, dates, response_dates)
        if local is not None:
            baseline = LinearRegression().fit(local[block.history, 0, :], Y[block.history, 0])
            predictions = baseline.predict(local[block.test, 0, :])
            label = "local_history"
        else:
            predictions = np.repeat(Y[block.history, 0].mean(), block.test.stop-block.test.start)
            label = "historical_mean"
        c = dict(n_measurements=0, n_outcomes=1, k=0, penalty=0.0)
        _append_forecasts(forecasts, context, label, c, block, predictions,
                          Y, conditional_mean, dates, response_dates)
        if local is not None:
            _append_forecasts(forecasts, context, "persistence", c, block,
                              local[block.test, 0, 0], Y, conditional_mean, dates, response_dates)
    return forecasts, selections, diagnostics


def _append_forecasts(records, context, label, candidate, block, predictions,
                      Y, conditional_mean, dates, response_dates):
    for index, prediction in zip(range(block.test.start, block.test.stop), predictions, strict=True):
        records.append(dict(context, method=label, origin=index,
                            origin_date=None if dates is None else str(dates[index]),
                            response_date=None if response_dates is None else str(response_dates[index]),
                            n_measurements=candidate["n_measurements"],
                            n_outcomes=candidate["n_outcomes"], k=candidate["k"],
                            penalty=candidate["penalty"], prediction=float(prediction),
                            actual=float(Y[index, 0]),
                            squared_error=float((Y[index, 0]-prediction)**2),
                            conditional_mean_squared_error=None if conditional_mean is None else
                            float((conditional_mean[index, 0]-prediction)**2)))


def validate_settings(settings, n_rows, n_measurements, n_outcomes):
    for key in ("measurement_assets", "outcome_assets", "factor_counts"):
        grid = settings[key]
        if not grid or any(not isinstance(v, int) or isinstance(v, bool) or v <= 0 for v in grid):
            raise ValueError(f"{key} must contain positive integers")
        if len(set(grid)) != len(grid):
            raise ValueError(f"{key} has duplicates")
    if max(settings["measurement_assets"]) > n_measurements or max(settings["outcome_assets"]) > n_outcomes:
        raise ValueError("Requested donor panel exceeds available assets")
    if max(settings["factor_counts"]) > min(min(settings["measurement_assets"]),
                                           settings["initial_train"]-settings["validation_size"]-1):
        raise ValueError("Factor grid exceeds smallest panel or inner training rank")
    for key in ("ridge_penalties", "lasso_penalties", "pooling_penalties"):
        if not settings[key] or any(not np.isfinite(v) or v < 0 for v in settings[key]):
            raise ValueError(f"{key} must contain finite nonnegative penalties")
    list(forecast_blocks(n_rows, settings["initial_train"], settings["validation_size"],
                         settings["test_size"], settings["refit_every"]))


def run_simulation(config):
    settings = config["experiment"]
    for key in ("seeds", "heterogeneity", "predictor_quality"):
        if not settings[key] or len(set(settings[key])) != len(settings[key]):
            raise ValueError(f"{key} must be a nonempty grid without duplicates")
    predictions, selections, diagnostics = [], [], []
    for seed, heterogeneity, quality in product(settings["seeds"], settings["heterogeneity"], settings["predictor_quality"]):
        simulation = SimulationConfig(**config["simulation"], seed=seed,
                                      heterogeneity=heterogeneity, added_predictor_quality=quality)
        panel = generate_panel(simulation)
        context = dict(seed=seed, heterogeneity=heterogeneity, predictor_quality=quality)
        out = evaluate_panel(panel.X, panel.Y, settings, context,
                             factors=panel.factors, conditional_mean=panel.conditional_mean)
        for records, target in zip(out, (predictions, selections, diagnostics), strict=True):
            target.extend(records)
    return predictions, selections, diagnostics


def save_results(output, config, results, *, config_path, provenance=None):
    output = Path(output)
    output.mkdir(parents=True, exist_ok=False)
    predictions, selections, diagnostics = results
    frame = pd.DataFrame(predictions)
    frame.to_csv(output / "predictions.csv", index=False)
    # Adaptive donor counts change at refits: aggregate as one policy per seed.
    metrics = frame.copy()
    adaptive = metrics["method"] == "adaptive_factor"
    metrics.loc[adaptive, ["n_measurements", "n_outcomes"]] = -1
    group = [c for c in ("seed", "heterogeneity", "predictor_quality", "method", "n_measurements", "n_outcomes") if c in metrics]
    per_run = metrics.groupby(group, dropna=False).agg(
        mse=("squared_error", "mean"), n_forecasts=("squared_error", "size"),
        conditional_mean_mse=("conditional_mean_squared_error", "mean"),
    ).reset_index()
    per_run.to_csv(output / "metrics.csv", index=False)
    if "seed" in per_run:
        summary = per_run.groupby([c for c in group if c != "seed"], dropna=False)["mse"].agg(
            mean_mse="mean", std_across_seeds="std", n_seeds="size").reset_index()
        summary["monte_carlo_se"] = summary["std_across_seeds"] / np.sqrt(summary["n_seeds"])
        summary.to_csv(output / "simulation_summary.csv", index=False)
    with (output / "selections.jsonl").open("w") as stream:
        for selection in selections:
            stream.write(json.dumps(selection, sort_keys=True) + "\n")
    pd.DataFrame(diagnostics).to_csv(output / "diagnostics.csv", index=False)
    root = Path(__file__).resolve().parents[2]
    code_files = sorted((root / "src").rglob("*.py"))
    code_hash = sha256(b"".join(p.relative_to(root).as_posix().encode()+p.read_bytes() for p in code_files)).hexdigest()
    git = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, capture_output=True, text=True)
    status = subprocess.run(["git", "status", "--porcelain"], cwd=root, capture_output=True, text=True)
    metadata = dict(config=config, python=sys.version, platform=platform.platform(),
                    versions={name: version(name) for name in ("numpy", "pandas", "scipy", "scikit-learn")},
                    config_sha256=sha256(Path(config_path).read_bytes()).hexdigest(), code_sha256=code_hash,
                    git_commit=git.stdout.strip() if git.returncode == 0 else None,
                    git_dirty=bool(status.stdout.strip()), data_provenance=provenance,
                    target_column=0, selection_loss="historical target validation MSE",
                    horizon="one period; rows are nonoverlapping origin/response pairs",
                    adaptive_donor_count_in_metrics=-1)
    (output / "metadata.json").write_text(json.dumps(metadata, indent=2, sort_keys=True)+"\n")
    return output
