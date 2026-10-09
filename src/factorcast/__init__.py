"""Forecasting experiments on predictor breadth and outcome information sharing."""

from .models import (
    DirectForecaster,
    FactorForecaster,
    OracleForecaster,
    PanelForecaster,
    PCARepresentation,
    PLSForecaster,
)
from .simulation import SimulationConfig, SyntheticPanel, generate_panel

__all__ = [
    "DirectForecaster", "FactorForecaster", "OracleForecaster", "PanelForecaster",
    "PCARepresentation", "PLSForecaster", "SimulationConfig", "SyntheticPanel",
    "generate_panel",
]
