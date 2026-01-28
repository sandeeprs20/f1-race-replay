"""
Machine Learning modules for F1 race analysis.

- feature_engineering: Extract ML features from session data
- tyre_degradation: Tyre degradation prediction model
"""

from .feature_engineering import extract_tyre_features
from .tyre_degradation import TyreDegradationModel

__all__ = ["extract_tyre_features", "TyreDegradationModel"]
