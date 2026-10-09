"""Stationary synthetic panels with forecast pairs aligned as ``X_t -> Y_{t+1}``.

Generate the largest panel once and slice its columns to compare asset counts.
Independent random streams also preserve existing columns if ``max_assets`` is
increased. Predictor quality and outcome coefficient heterogeneity are separate
design choices; none of the regimes assumes that factor forecasts will win.
"""

from dataclasses import dataclass

import numpy as np
from numpy.typing import NDArray

FloatArray = NDArray[np.float64]


@dataclass(frozen=True)
class SimulationConfig:
    """Parameters for a two-factor panel.

    The first ``anchor_assets`` span both factors. Added predictors can be
    informative, noisy, correlated (all load on factor one), or irrelevant.
    ``heterogeneity`` varies the second outcome slope across all assets;
    the first slope is shared. Target-0 coefficients remain fixed as the
    asset count changes, but follow the same heterogeneous distribution as
    donor coefficients. Correlations refer to equicorrelated innovation noise
    and lie in [0, 1).

    ``donor_shift`` optionally offsets donor second slopes by
    ``heterogeneity * donor_shift`` while leaving the target distribution
    unchanged. The default zero shift imposes no directional donor mismatch.
    """

    n_periods: int = 360
    max_assets: int = 60
    seed: int = 0
    factor_rho: float = 0.5
    measurement_noise: float = 1.0
    measurement_correlation: float = 0.0
    outcome_noise: float = 1.0
    outcome_correlation: float = 0.0
    heterogeneity: float = 0.5
    donor_shift: float = 0.0
    anchor_assets: int = 5
    added_predictor_quality: str = "informative"
    noisy_multiplier: float = 4.0

    def __post_init__(self) -> None:
        for name in ("n_periods", "max_assets", "anchor_assets", "seed"):
            if not isinstance(getattr(self, name), (int, np.integer)):
                raise ValueError(f"{name} must be an integer")
        if self.seed < 0:
            raise ValueError("seed must be nonnegative")
        if self.n_periods < 3 or self.max_assets < 2:
            raise ValueError("n_periods must be >= 3 and max_assets must be >= 2")
        if not 2 <= self.anchor_assets <= self.max_assets:
            raise ValueError("anchor_assets must lie between 2 and max_assets")
        if not -1 < self.factor_rho < 1:
            raise ValueError("factor_rho must lie strictly between -1 and 1")
        for name in ("measurement_correlation", "outcome_correlation"):
            if not 0 <= getattr(self, name) < 1:
                raise ValueError(f"{name} must lie in [0, 1)")
        for name in ("measurement_noise", "outcome_noise", "heterogeneity"):
            if getattr(self, name) < 0 or not np.isfinite(getattr(self, name)):
                raise ValueError(f"{name} must be finite and nonnegative")
        if self.noisy_multiplier < 1 or not np.isfinite(self.noisy_multiplier):
            raise ValueError("noisy_multiplier must be finite and at least 1")
        if not np.isfinite(self.donor_shift):
            raise ValueError("donor_shift must be finite")
        if self.added_predictor_quality not in {
            "informative", "noisy", "correlated", "irrelevant"
        }:
            raise ValueError("Unknown added_predictor_quality")


@dataclass(frozen=True)
class SyntheticPanel:
    """Aligned arrays: X/Y/conditional_mean are T x N, factors are T x 2.

    ``loadings`` and ``theta`` are N x 2. Row t of ``Y`` is the outcome at
    t+1, whose conditional mean given the latent factor at t is stored in
    ``conditional_mean``. Factors are known only to simulation diagnostics.
    """

    X: FloatArray
    Y: FloatArray
    factors: FloatArray
    conditional_mean: FloatArray
    loadings: FloatArray
    theta: FloatArray


def _rng(seed: int, stream: int, asset: int = 0) -> np.random.Generator:
    return np.random.default_rng(np.random.SeedSequence([seed, stream, asset]))


def generate_panel(config: SimulationConfig) -> SyntheticPanel:
    """Generate a stationary two-factor panel with nested asset prefixes."""
    c = config
    n, p = c.n_periods, c.max_assets
    innovations = _rng(c.seed, 0).normal(size=(n, 2))
    factors = np.empty((n, 2))
    # Initial draw from the stationary marginal distribution; no burn-in.
    factors[0] = innovations[0]
    innovation_sd = np.sqrt(1 - c.factor_rho**2)
    for t in range(1, n):
        factors[t] = c.factor_rho * factors[t - 1] + innovation_sd * innovations[t]

    loadings = np.empty((p, 2))
    theta = np.empty((p, 2))
    measurement_scales = np.full(p, c.measurement_noise)
    for j in range(p):
        angle = _rng(c.seed, 1, j).uniform(0, 2 * np.pi)
        loadings[j] = np.sqrt(2) * np.array([np.cos(angle), np.sin(angle)])
        donor_offset = c.donor_shift if j > 0 else 0.0
        theta[j] = [
            1.0, 0.8 + c.heterogeneity * (_rng(c.seed, 2, j).normal() + donor_offset)
        ]
        if j >= c.anchor_assets:
            if c.added_predictor_quality == "noisy":
                measurement_scales[j] *= c.noisy_multiplier
            elif c.added_predictor_quality == "correlated":
                loadings[j] = [np.sqrt(2), 0.0]
            elif c.added_predictor_quality == "irrelevant":
                loadings[j] = 0.0
    # A well-conditioned spanning pair. Independent per-asset streams keep
    # target coefficients invariant across N without centering donors on it.
    loadings[0] = [np.sqrt(2), 0.0]
    loadings[1] = [0.0, np.sqrt(2)]

    measurement_common = _rng(c.seed, 3).normal(size=n)
    outcome_common = _rng(c.seed, 4).normal(size=n)
    measurement_shocks = np.column_stack(
        [_rng(c.seed, 5, j).normal(size=n) for j in range(p)]
    )
    outcome_shocks = np.column_stack(
        [_rng(c.seed, 6, j).normal(size=n) for j in range(p)]
    )
    measurement_shocks = (
        np.sqrt(c.measurement_correlation) * measurement_common[:, None]
        + np.sqrt(1 - c.measurement_correlation) * measurement_shocks
    )
    outcome_shocks = (
        np.sqrt(c.outcome_correlation) * outcome_common[:, None]
        + np.sqrt(1 - c.outcome_correlation) * outcome_shocks
    )
    conditional_mean = factors @ theta.T
    X = factors @ loadings.T + measurement_shocks * measurement_scales
    Y = conditional_mean + c.outcome_noise * outcome_shocks
    return SyntheticPanel(X, Y, factors, conditional_mean, loadings, theta)
