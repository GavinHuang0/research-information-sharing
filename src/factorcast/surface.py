"""Experiment 3: streamed matched/expanding PCA and coefficient surfaces.

The normalized partial-pooling objective is solved through a K-dimensional
Schur system.  All 48 donor fits at a penalty are reused across targets; no
existing frozen model/experiment implementation is changed by this module.
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
import gzip
import hashlib
import io
import json
from pathlib import Path
from time import perf_counter

import numpy as np
import pandas as pd

from .models import PCARepresentation


TARGETS = ("Food", "Mach", "Banks", "Oil", "Util", "Hlth")
SHARING = ("separate", "common", "partial")
PREDICTION_COLUMNS = (
    "weighting", "stage", "cell_index", "cell_id", "mode", "history", "sharing", "K", "target",
    "target_index", "date_index", "origin_index", "origin_date", "response_date", "refit_index", "penalty", "prediction", "actual",
    "squared_error", "absolute_error", "coefficient_train_start", "coefficient_train_stop",
    "pca_train_start", "pca_train_stop",
)
TUNING_COLUMNS = (
    "weighting", "stage", "cell_index", "cell_id", "mode", "history", "sharing", "K", "target",
    "refit_index", "refit_origin", "inner_coef_start", "inner_coef_stop", "outer_coef_start", "outer_coef_stop",
    "inner_pca_start", "inner_pca_stop", "outer_pca_start", "outer_pca_stop", "validation_first_origin",
    "validation_last_response", "inner_coefficient_last_response", "outer_coefficient_last_response",
    "candidate_penalty", "validation_mse", "chosen", "chosen_penalty", "computed_components", "used_components",
)


def _positive_int(value, name):
    if isinstance(value, bool) or not isinstance(value, (int, np.integer)) or value <= 0:
        raise ValueError(f"{name} must be a positive integer")
    return int(value)


def _settings(config):
    targets = tuple(config.get("design", {}).get("targets", TARGETS))
    if targets != TARGETS or tuple(config.get("design", {}).get("sharing_rules", SHARING)) != SHARING:
        raise ValueError("Surface targets and sharing rules must preserve the declared order")
    grid = config["grid"]
    finite = [_positive_int(value, "history") for value in grid["finite_coefficient_pairs"]]
    factors = [_positive_int(value, "K") for value in grid["factor_counts"]]
    if not finite or finite != sorted(set(finite)) or not factors or factors != sorted(set(factors)):
        raise ValueError("Histories and dimensions must be nonempty, unique, and ascending")
    components = _positive_int(config.get("representation", {}).get("fit_components_once_per_window", 8), "PCA components")
    if max(factors) > components or min(finite) <= components:
        raise ValueError("PCA component count must span K and fit inside the smallest centered window")
    if not grid.get("include_expanding_coefficient_control", True):
        raise ValueError("The deduplicated expanding control is required")
    calendar = config["calendar"]
    initial = _positive_int(calendar["first_outer_cutoff_pairs"], "initial cutoff")
    validation = _positive_int(calendar["validation_pairs"], "validation length")
    refit = _positive_int(calendar["refit_every_pairs"], "refit interval")
    if initial < max(finite) + validation:
        raise ValueError("The common initial cutoff must supply max L plus validation")
    penalties = np.asarray(config["partial_pooling"]["penalties"], dtype=float)
    if (penalties.ndim != 1 or len(penalties) == 0 or not np.isfinite(penalties).all()
            or (penalties <= 0).any() or not np.all(np.diff(penalties) > 0)):
        raise ValueError("Partial penalties must be finite, positive, and strictly ascending")
    if config["partial_pooling"].get("divide_penalty_by_K", False):
        raise ValueError("The declared partial objective must not divide its penalty by K")
    return finite, factors, components, initial, validation, refit, penalties


def cell_inventory(config):
    """Return canonical cells; expanding controls are stored once, not per mode."""
    finite, factors, _, _, _, _, _ = _settings(config)
    records = []
    for history in [str(length) for length in finite] + ["expanding"]:
        records.append(dict(cell_id=f"local_history__L-{history}", mode="none", history=history,
                            sharing="own", K=0, n_factors=0, n_measurements=0, n_outcomes=1,
                            method="local_history", measurement_panel="none", outcome_panel="target"))
    groups = [(mode, str(length)) for mode in ("matched", "expanding") for length in finite]
    groups.append(("shared", "expanding"))
    for mode, history in groups:
        for k in factors:
            for sharing in SHARING:
                records.append(dict(
                    cell_id=f"factor_{sharing}__PCA-{mode}__L-{history}__K-{k}",
                    mode=mode, history=history, sharing=sharing, K=k, n_factors=k,
                    n_measurements=48, n_outcomes=1 if sharing == "separate" else 48,
                    method={"separate": "factor_separate", "common": "factor_pooled", "partial": "factor_partial"}[sharing],
                    measurement_panel="all", outcome_panel="target" if sharing == "separate" else "all",
                ))
    result = pd.DataFrame(records)
    result.insert(0, "cell_index", np.arange(len(result), dtype=int))
    return result


@dataclass(frozen=True)
class PrefixRepresentation:
    """Immutable score-prefix view; passing only n_factors would not truncate."""

    representation: PCARepresentation
    n_factors: int

    def __post_init__(self):
        if not hasattr(self.representation, "pca_"):
            raise ValueError("Prefix representation requires an already fitted basis")
        if not 1 <= self.n_factors <= self.representation.pca_.n_components_:
            raise ValueError("Requested prefix is outside the fitted PCA basis")

    @property
    def pca_(self):
        return self.representation.pca_

    def transform(self, values):
        return self.representation.transform(values)[:, :self.n_factors]

    def fit(self, values):
        raise RuntimeError("A frozen PCA prefix cannot be refitted")


class LocalWindow:
    """Industry-specific intercept/local fits reused across modes and K."""

    def __init__(self, outcomes, local):
        self.y = np.asarray(outcomes, dtype=float)
        local = np.asarray(local, dtype=float)
        if self.y.ndim != 2 or local.shape != (*self.y.shape, 3) or len(self.y) < 5:
            raise ValueError("Need n x J outcomes and n x J x 3 local controls")
        if not np.isfinite(self.y).all() or not np.isfinite(local).all():
            raise ValueError("Local fitting arrays must be finite")
        self.designs = np.concatenate([np.ones((*self.y.shape, 1)), local], axis=2)
        self.coefficients = np.stack([
            np.linalg.lstsq(self.designs[:, j], self.y[:, j], rcond=None)[0]
            for j in range(self.y.shape[1])
        ])
        self.residual_y = self.y - np.einsum("njp,jp->nj", self.designs, self.coefficients)

    def predict(self, local, targets):
        local = np.asarray(local, dtype=float)
        design = np.concatenate([np.ones((*local.shape[:2], 1)), local], axis=2)
        return np.einsum("njp,jp->nj", design[:, targets], self.coefficients[targets])


@dataclass
class FactorFit:
    slopes: np.ndarray  # K x included outcomes
    nuisance: np.ndarray  # included outcomes x four local coefficients
    outcomes: tuple[int, ...]

    def predict_scores(self, scores, local, targets=None):
        scores = np.asarray(scores, dtype=float)
        if scores.ndim != 2 or scores.shape[1] != self.slopes.shape[0]:
            raise ValueError("Prediction score width must equal the fitted K")
        targets = self.outcomes if targets is None else tuple(targets)
        positions = [self.outcomes.index(target) for target in targets]
        local = np.asarray(local, dtype=float)
        design = np.concatenate([np.ones((len(scores), len(targets), 1)), local[:, targets]], axis=2)
        return scores @ self.slopes[:, positions] + np.einsum("njp,jp->nj", design, self.nuisance[positions])


class FactorWindow:
    """Cached residual designs/normal equations for every prefix dimension."""

    def __init__(self, local: LocalWindow, scores):
        self.local = local
        scores = np.asarray(scores, dtype=float)
        if scores.ndim != 2 or len(scores) != len(local.y) or not np.isfinite(scores).all():
            raise ValueError("Scores must be finite and match the coefficient window")
        self.n_components = scores.shape[1]
        self.z_projection = np.stack([
            np.linalg.lstsq(local.designs[:, j], scores, rcond=None)[0]
            for j in range(local.y.shape[1])
        ])
        self.residual_z = np.stack([
            scores - local.designs[:, j] @ self.z_projection[j]
            for j in range(local.y.shape[1])
        ])
        self.grams = np.einsum("jnk,jnl->jkl", self.residual_z, self.residual_z, optimize=True) / len(scores)
        self.rhs = np.einsum("jnk,nj->jk", self.residual_z, local.residual_y, optimize=True) / len(scores)
        self._eigen = {}

    def _fitted(self, slopes, outcomes):
        outcomes = tuple(outcomes)
        k = slopes.shape[0]
        nuisance = self.local.coefficients[list(outcomes)] - np.einsum(
            "jpk,kj->jp", self.z_projection[list(outcomes), :, :k], slopes)
        return FactorFit(slopes, nuisance, outcomes)

    def separate(self, k, outcomes=None):
        self._check_k(k)
        outcomes = tuple(range(self.local.y.shape[1])) if outcomes is None else tuple(outcomes)
        slopes = np.column_stack([
            np.linalg.lstsq(self.residual_z[j, :, :k], self.local.residual_y[:, j], rcond=None)[0]
            for j in outcomes
        ])
        return self._fitted(slopes, outcomes)

    def common(self, k):
        self._check_k(k)
        shared = np.linalg.lstsq(self.grams[:, :k, :k].sum(axis=0), self.rhs[:, :k].sum(axis=0), rcond=None)[0]
        slopes = np.repeat(shared[:, None], self.local.y.shape[1], axis=1)
        return self._fitted(slopes, range(self.local.y.shape[1]))

    def partial(self, k, penalty):
        """Exact normalized partial pooling using a Schur K-system, not JK."""
        self._check_k(k)
        if not np.isfinite(penalty) or penalty < 0:
            raise ValueError("Partial penalty must be finite and nonnegative")
        if penalty == 0:
            return self.separate(k)
        if k not in self._eigen:
            values, vectors = np.linalg.eigh(self.grams[:, :k, :k])
            if np.min(values) < -1e-9 * max(1.0, float(np.max(values))):
                raise ValueError("Residual Gram matrix is not positive semidefinite")
            values = np.maximum(values, 0.0)  # Numerical roundoff of PSD Grams only.
            projected_rhs = np.einsum("jik,ji->jk", vectors, self.rhs[:, :k])
            self._eigen[k] = values, vectors, projected_rhs
        values, vectors, projected_rhs = self._eigen[k]
        inverse = 1 / (values + penalty)
        inverse_rhs = np.einsum("jik,jk->ji", vectors, inverse * projected_rhs)
        # mean_j G_j(G_j+lambda I)^-1 avoids subtracting near-equal I terms.
        schur = np.einsum("jik,jk,jlk->il", vectors, values * inverse, vectors, optimize=True) / len(values)
        mean_slope = np.linalg.lstsq(schur, inverse_rhs.mean(axis=0), rcond=None)[0]
        projected_mean = np.einsum("jik,i->jk", vectors, mean_slope)
        slopes = np.einsum("jik,jk->ji", vectors, inverse * (projected_rhs + penalty * projected_mean)).T
        return self._fitted(slopes, range(self.local.y.shape[1]))

    def _check_k(self, k):
        if isinstance(k, bool) or not isinstance(k, (int, np.integer)) or not 1 <= k <= self.n_components:
            raise ValueError("K is outside the cached score prefix")


def _sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _write_json(path, value):
    Path(path).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8", newline="\n")


class _CSVShards:
    """Deterministic bounded gzip CSV shards; all rows and candidate scores stay."""

    def __init__(self, root, kind, columns, limit):
        self.root, self.kind, self.columns = Path(root), kind, columns
        self.limit = min(_positive_int(limit, "shard byte limit"), 100000000)
        self.raw_limit = min(64 * 1024 * 1024, int(self.limit * 0.75))
        self.streams = {}
        self.completed = []

    def _open(self, key, number):
        weighting, mode, history = key
        path = self.root / self.kind / weighting / mode / f"L-{history}" / f"part-{number:05d}.csv.gz"
        path.parent.mkdir(parents=True, exist_ok=True)
        binary = path.open("xb")
        compressed = gzip.GzipFile(filename="", mode="wb", fileobj=binary, mtime=0, compresslevel=6)
        header = self._serialize([self.columns])
        compressed.write(header)
        return dict(path=path, binary=binary, compressed=compressed, rows=0, raw_bytes=len(header), number=number)

    @staticmethod
    def _serialize(rows):
        text = io.StringIO(newline="")
        csv.writer(text, lineterminator="\n").writerows(rows)
        return text.getvalue().encode("utf-8")

    def append(self, key, rows):
        if not rows:
            return
        body = self._serialize(rows)
        if len(body) + len(self._serialize([self.columns])) > self.raw_limit:
            if len(rows) == 1:
                raise ValueError("A single record exceeds the declared deterministic shard bound")
            middle = len(rows) // 2
            self.append(key, rows[:middle])
            self.append(key, rows[middle:])
            return
        stream = self.streams.get(key)
        if stream is None:
            stream = self._open(key, 0)
            self.streams[key] = stream
        if stream["raw_bytes"] + len(body) > self.raw_limit:
            self._close(stream)
            stream = self._open(key, stream["number"] + 1)
            self.streams[key] = stream
        stream["compressed"].write(body)
        stream["rows"] += len(rows)
        stream["raw_bytes"] += len(body)

    def _close(self, stream):
        stream["compressed"].close()
        stream["binary"].close()
        path = stream["path"]
        size = path.stat().st_size
        if size >= self.limit or size >= 100000000:
            raise ValueError(f"Completed shard violates the frozen size bound: {path}")
        self.completed.append(dict(path=path.relative_to(self.root).as_posix(), bytes=size,
                                   rows=stream["rows"], sha256=_sha256(path)))

    def close(self):
        for key in sorted(self.streams):
            self._close(self.streams[key])
        self.streams.clear()
        return sorted(self.completed, key=lambda item: item["path"])


def _pca(dataset, start, stop, components):
    representation = PCARepresentation(components).fit(dataset.X[start:stop])
    singular = representation.pca_.singular_values_
    tolerance = max(stop - start, dataset.X.shape[1]) * np.finfo(float).eps * singular[0]
    if singular[-1] <= tolerance or not np.isfinite(representation.score_scaler_.var_).all():
        raise ValueError("Declared eight-component basis lacks centered rank or finite score variance")
    if (representation.score_scaler_.var_ <= 0).any():
        raise ValueError("A declared score has zero variance")
    return representation


def _validate_datasets(datasets, initial):
    if not datasets:
        raise ValueError("At least one common-calendar weighting is required")
    if not set(datasets).issubset({"value", "equal"}):
        raise ValueError("Weightings must be value/equal")
    first = next(iter(datasets.values()))
    if initial >= len(first.X):
        raise ValueError("No origins remain after the common initial cutoff")
    for dataset in datasets.values():
        if len(dataset.asset_names) != 48 or len(set(dataset.asset_names)) != 48 or not set(TARGETS).issubset(dataset.asset_names):
            raise ValueError("The declared 48-industry panel and six targets are required")
        if tuple(dataset.asset_names) != tuple(first.asset_names):
            raise ValueError("All weightings must use the same source industry order")
        if not dataset.origin_dates.equals(first.origin_dates) or not dataset.response_dates.equals(first.response_dates):
            raise ValueError("All weightings must use identical date pairs")
        if dataset.origin_dates.has_duplicates or not dataset.origin_dates.is_monotonic_increasing:
            raise ValueError("Origins must be unique and chronological")
        if not ((dataset.response_dates - dataset.origin_dates) == pd.Timedelta(days=7)).all():
            raise ValueError("Responses must be next-calendar-week outcomes")
        n = len(dataset.origin_dates)
        if dataset.X.shape != (n, 48) or dataset.Y.shape != (n, 48) or dataset.local_all.shape != (n, 48, 3):
            raise ValueError("Forecast dataset arrays have inconsistent shapes")
        if not all(np.isfinite(array).all() for array in (dataset.X, dataset.Y, dataset.local_all)):
            raise ValueError("All complete-case fitting arrays must be finite")
    return first


def run_stage(datasets, config, stage, output: Path, progress=None):
    """Stream one seen-period surface into NPY memmaps and raw gzip CSV shards.

    Output may contain only an orchestration ``started.json`` beforehand.
    Returns a manifest; no full-grid forecast/tuning DataFrame is constructed.
    """
    started = perf_counter()
    if stage not in ("earlier_seen", "later_seen"):
        raise ValueError("stage must be earlier_seen or later_seen")
    finite, factors, components, initial, validation, refit, penalties = _settings(config)
    first = _validate_datasets(datasets, initial)
    output = Path(output)
    if output.exists() and any(path.name != "started.json" for path in output.iterdir()):
        raise FileExistsError("Stage artifacts already exist; use a new output directory")
    output.mkdir(parents=True, exist_ok=True)
    calendar = config["calendar"]
    earlier_end = pd.Timestamp(calendar["earlier_seen_response_end"])
    later_start = pd.Timestamp(calendar["later_seen_response_start"])
    later_end = pd.Timestamp(calendar["later_seen_response_end"])
    if not earlier_end < later_start <= later_end:
        raise ValueError("Seen-period response boundaries must be disjoint and ordered")
    phase = (first.response_dates <= earlier_end if stage == "earlier_seen" else
             first.response_dates.to_series(index=np.arange(len(first.X))).between(later_start, later_end).to_numpy())
    phase = np.asarray(phase, dtype=bool)
    phase[:initial] = False
    origin_indices = np.flatnonzero(phase)
    if len(origin_indices) == 0:
        raise ValueError("No forecast origins in the requested seen period")
    blocks = [(cut, np.arange(cut, min(cut + refit, len(first.X)))) for cut in range(initial, len(first.X), refit)]
    blocks = [(cut, rows[phase[rows]]) for cut, rows in blocks if phase[rows].any()]
    positions = {int(index): position for position, index in enumerate(origin_indices)}
    inventory = cell_inventory(config)
    inventory.to_csv(output / "cells.csv", index=False, lineterminator="\n")
    cells = {(row.mode, row.history, int(row.K), row.sharing): row._asdict()
             for row in inventory.itertuples(index=False)}
    refit_indices = [initial + ((int(index) - initial) // refit) * refit for index in origin_indices]
    dates = dict(stage=stage, target_order=list(TARGETS), n_dates=len(origin_indices),
                 origin_indices=origin_indices.tolist(), refit_indices=refit_indices,
                 origin_dates=first.origin_dates[origin_indices].strftime("%Y-%m-%d").tolist(),
                 response_dates=first.response_dates[origin_indices].strftime("%Y-%m-%d").tolist())
    _write_json(output / "dates.json", dates)
    _write_json(output / "memberships.json", dict(
        measurement_assets=list(first.asset_names), target_order=list(TARGETS),
        separate_outcomes={target: [target] for target in TARGETS},
        own_outcomes={target: [target] for target in TARGETS}, own_measurements=[],
        common_outcomes=list(first.asset_names), partial_outcomes=list(first.asset_names),
    ))
    execution = config.get("execution", {})
    file_limit = min(execution.get("completed_shard_bytes_must_be_less_than", 83886080),
                     execution.get("hard_file_bytes_must_be_less_than", 100000000))
    predictions_writer = _CSVShards(output, "predictions", PREDICTION_COLUMNS, file_limit)
    tuning_writer = _CSVShards(output, "tuning", TUNING_COLUMNS, file_limit)
    prediction_rows = tuning_rows = pca_fits = completed_blocks = 0
    per_weighting = {}
    groups = [(mode, str(length), length) for mode in ("matched", "expanding") for length in finite]
    groups.append(("shared", "expanding", None))
    for weighting in (weight for weight in ("value", "equal") if weight in datasets):
        weight_started = perf_counter()
        dataset = datasets[weighting]
        targets = [dataset.asset_names.index(name) for name in TARGETS]
        shape = (len(origin_indices), len(inventory), len(TARGETS))
        if np.prod(shape, dtype=np.int64) * 8 + 1024 >= file_limit:
            raise ValueError("Forecast NPY would exceed the declared per-file bound")
        forecasts = np.lib.format.open_memmap(output / f"predictions_{weighting}.npy", mode="w+", dtype="<f8", shape=shape)
        forecasts[:] = np.nan
        np.save(output / f"actual_{weighting}.npy", dataset.Y[origin_indices][:, targets], allow_pickle=False)
        for cut, rows in blocks:
            b = cut - validation
            if not (dataset.response_dates[:cut] <= dataset.origin_dates[cut]).all():
                raise AssertionError("An outer outcome is unavailable at its refit origin")
            if not (dataset.response_dates[:b] <= dataset.origin_dates[b]).all():
                raise AssertionError("An inner outcome is unavailable at validation start")
            validation_rows = np.arange(b, cut)
            position_rows = [positions[int(index)] for index in rows]
            local_cache = {}
            # Expanding PCA is shared by every finite coefficient window and
            # the one deduplicated expanding-coefficient control.
            representations = {}
            for mode, history, length in groups:
                inner_start, outer_start = (0, 0) if length is None else (b - length, cut - length)
                if history not in local_cache:
                    local_cache[history] = (
                        LocalWindow(dataset.Y[inner_start:b], dataset.local_all[inner_start:b]),
                        LocalWindow(dataset.Y[outer_start:cut], dataset.local_all[outer_start:cut]),
                    )
                    own_cell = cells[("none", history, 0, "own")]
                    own_inner, own_outer = local_cache[history]
                    own_validation = own_inner.predict(dataset.local_all[validation_rows], targets)
                    own_predictions = own_outer.predict(dataset.local_all[rows], targets)
                    own_scores = np.mean((dataset.Y[validation_rows][:, targets] - own_validation) ** 2, axis=0)
                    forecasts[np.asarray(position_rows), own_cell["cell_index"], :] = own_predictions
                    own_pred, own_tune = _records(dataset, weighting, stage, own_cell, rows, cut, b,
                                                  inner_start, outer_start, None, None, targets,
                                                  own_predictions, np.zeros(6), np.array([0.0]),
                                                  own_scores[None, :], 0, positions)
                    predictions_writer.append((weighting, "none", history), own_pred)
                    tuning_writer.append((weighting, "none", history), own_tune)
                    prediction_rows += len(own_pred)
                    tuning_rows += len(own_tune)
                inner_local, outer_local = local_cache[history]
                pca_inner_start = inner_start if mode == "matched" else 0
                pca_outer_start = outer_start if mode == "matched" else 0
                for window in ((pca_inner_start, b), (pca_outer_start, cut)):
                    if window not in representations:
                        representations[window] = _pca(dataset, *window, components)
                        pca_fits += 1
                inner_rep = representations[(pca_inner_start, b)]
                outer_rep = representations[(pca_outer_start, cut)]
                inner = FactorWindow(inner_local, inner_rep.transform(dataset.X[inner_start:b]))
                outer = FactorWindow(outer_local, outer_rep.transform(dataset.X[outer_start:cut]))
                validation_scores = inner_rep.transform(dataset.X[validation_rows])
                forecast_scores = outer_rep.transform(dataset.X[rows])
                prediction_records, tuning_records = [], []
                for k in factors:
                    for sharing in SHARING:
                        cell = cells[(mode, history, k, sharing)]
                        candidate_penalties = penalties if sharing == "partial" else np.array([0.0])
                        candidate_scores = []
                        for penalty in candidate_penalties:
                            fitted = (inner.separate(k, targets) if sharing == "separate" else
                                      inner.common(k) if sharing == "common" else inner.partial(k, penalty))
                            val_prediction = fitted.predict_scores(validation_scores[:, :k], dataset.local_all[validation_rows], targets)
                            candidate_scores.append(np.mean((dataset.Y[validation_rows][:, targets] - val_prediction) ** 2, axis=0))
                        candidate_scores = np.asarray(candidate_scores)
                        choices = np.argmin(candidate_scores, axis=0)  # First ascending penalty on ties.
                        chosen = candidate_penalties[choices]
                        prediction = np.empty((len(rows), 6))
                        for penalty in np.unique(chosen):
                            fitted = (outer.separate(k, targets) if sharing == "separate" else
                                      outer.common(k) if sharing == "common" else outer.partial(k, penalty))
                            values = fitted.predict_scores(forecast_scores[:, :k], dataset.local_all[rows], targets)
                            selected = chosen == penalty
                            prediction[:, selected] = values[:, selected]
                        if not np.isfinite(prediction).all() or not np.isfinite(candidate_scores).all():
                            raise ValueError("A declared surface cell has nonfinite forecasts or validation loss")
                        forecasts[np.asarray(position_rows), cell["cell_index"], :] = prediction
                        pred, tune = _records(dataset, weighting, stage, cell, rows, cut, b,
                                              inner_start, outer_start, pca_inner_start, pca_outer_start,
                                              targets, prediction, chosen, candidate_penalties,
                                              candidate_scores, components, positions)
                        prediction_records.extend(pred)
                        tuning_records.extend(tune)
                predictions_writer.append((weighting, mode, history), prediction_records)
                tuning_writer.append((weighting, mode, history), tuning_records)
                prediction_rows += len(prediction_records)
                tuning_rows += len(tuning_records)
            forecasts.flush()
            completed_blocks += 1
            if progress is not None:
                progress(dict(weighting=weighting, stage=stage, refit_index=cut, n_origins=len(rows),
                              completed_blocks=completed_blocks, total_blocks=len(blocks) * len(datasets),
                              pca_fits=pca_fits, prediction_rows=prediction_rows,
                              elapsed_seconds=perf_counter() - started))
        for start in range(0, len(forecasts), 64):
            if not np.isfinite(forecasts[start:start + 64]).all():
                raise ValueError("A canonical forecast cell was not filled")
        forecasts.flush()
        del forecasts
        per_weighting[weighting] = perf_counter() - weight_started
    records = predictions_writer.close() + tuning_writer.close()
    expected_predictions = len(origin_indices) * len(inventory) * 6 * len(datasets)
    if prediction_rows != expected_predictions or sum(item["rows"] for item in records if item["path"].startswith("predictions/")) != prediction_rows:
        raise AssertionError("Raw forecast row inventory is incomplete")
    if sum(item["rows"] for item in records if item["path"].startswith("tuning/")) != tuning_rows:
        raise AssertionError("Raw tuning row inventory is incomplete")
    timing = dict(prediction_rows=prediction_rows, tuning_rows=tuning_rows, pca_fits=pca_fits,
                  blocks=completed_blocks, elapsed_seconds=perf_counter() - started,
                  per_weighting_seconds=per_weighting)
    _write_json(output / "timing.json", timing)
    for path in output.rglob("*"):
        if path.is_file() and path.suffix.lower() in {".json", ".csv", ".txt", ".md", ".toml"}:
            original = path.read_bytes()
            normalized = original.replace(b"\r\n", b"\n").replace(b"\r", b"\n")
            if normalized != original:
                path.write_bytes(normalized)
        if path.is_file() and path.stat().st_size >= file_limit:
            raise ValueError(f"Stage artifact violates the declared size bound: {path}")
    files = {path.relative_to(output).as_posix(): _sha256(path)
             for path in sorted(output.rglob("*")) if path.is_file() and path.name != "stage_manifest.json"}
    manifest = dict(stage=stage, files=files, file_records=records, timing=timing,
                    n_dates=len(origin_indices), n_cells=len(inventory), target_order=list(TARGETS),
                    arrays={weight: dict(predictions=f"predictions_{weight}.npy", actual=f"actual_{weight}.npy")
                            for weight in ("value", "equal") if weight in datasets},
                    inventory="cells.csv", dates="dates.json")
    _write_json(output / "stage_manifest.json", manifest)
    return manifest


def _records(dataset, weighting, stage, cell, rows, cut, b, inner_start, outer_start,
             pca_inner_start, pca_outer_start, targets, prediction, chosen, penalties, scores, components, positions):
    """Bounded one-cell raw records; all historical candidate scores retained."""
    common = [weighting, stage, cell["cell_index"], cell["cell_id"], cell["mode"], cell["history"], cell["sharing"], cell["K"]]
    predictions, tuning = [], []
    for target_position, (target, target_index) in enumerate(zip(TARGETS, targets)):
        for row_position, index in enumerate(rows):
            actual, forecast = float(dataset.Y[index, target_index]), float(prediction[row_position, target_position])
            error = actual - forecast
            predictions.append(common + [target, target_position, positions[int(index)], int(index), dataset.origin_dates[index].date().isoformat(),
                               dataset.response_dates[index].date().isoformat(), cut, float(chosen[target_position]),
                               forecast, actual, error ** 2, abs(error), outer_start, cut,
                               pca_outer_start, cut if pca_outer_start is not None else None])
        for candidate_position, penalty in enumerate(np.asarray(penalties).reshape(-1)):
            tuning.append(common + [target, cut, dataset.origin_dates[cut].date().isoformat(),
                          inner_start, b, outer_start, cut, pca_inner_start,
                          b if pca_inner_start is not None else None, pca_outer_start,
                          cut if pca_outer_start is not None else None,
                          dataset.origin_dates[b].date().isoformat(), dataset.response_dates[cut - 1].date().isoformat(),
                          dataset.response_dates[b - 1].date().isoformat(), dataset.response_dates[cut - 1].date().isoformat(),
                          float(penalty), float(scores[candidate_position, target_position]),
                          bool(penalty == chosen[target_position]), float(chosen[target_position]), components, cell["K"]])
    return predictions, tuning
