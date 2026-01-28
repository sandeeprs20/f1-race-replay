"""
Tyre degradation prediction model.

Uses machine learning to predict lap time degradation based on
tyre age, compound, and track conditions.
"""

import numpy as np
import pandas as pd
from typing import Dict, Optional, Tuple
from sklearn.ensemble import GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler, LabelEncoder
from sklearn.model_selection import train_test_split


# Compound ordering for encoding
COMPOUND_ORDER = ["SOFT", "MEDIUM", "HARD", "INTERMEDIATE", "WET", "UNKNOWN"]


class TyreDegradationModel:
    """
    Machine learning model for predicting tyre degradation.

    Predicts lap time delta (degradation) based on:
    - Tyre age (laps on current compound)
    - Compound type (SOFT/MEDIUM/HARD)
    - Track temperature
    - Air temperature
    - Fuel load estimate
    """

    def __init__(self):
        self.model = None
        self.scaler = StandardScaler()
        self.compound_encoder = LabelEncoder()
        self.is_trained = False
        self.feature_cols = [
            "tyre_age",
            "compound_encoded",
            "track_temp",
            "air_temp",
            "fuel_load_estimate",
        ]
        self.training_stats = {}

    def _prepare_features(self, df: pd.DataFrame) -> np.ndarray:
        """Prepare feature matrix from DataFrame."""
        # Encode compound
        df = df.copy()
        df["compound_encoded"] = self.compound_encoder.transform(df["compound"])

        # Fill missing values with defaults
        df["track_temp"] = df["track_temp"].fillna(30.0)
        df["air_temp"] = df["air_temp"].fillna(25.0)
        df["fuel_load_estimate"] = df["fuel_load_estimate"].fillna(0.5)

        X = df[self.feature_cols].values
        return X

    def train(self, features_df: pd.DataFrame) -> Dict:
        """
        Train the model on session lap data.

        Args:
            features_df: DataFrame from extract_tyre_features()

        Returns:
            Dict with training statistics
        """
        # Filter to valid laps only
        df = features_df[features_df["is_valid"]].copy()

        if len(df) < 10:
            print("Warning: Not enough valid laps for training")
            return {"error": "Not enough data"}

        # Fit compound encoder on all compounds
        self.compound_encoder.fit(COMPOUND_ORDER)

        # Remove outliers (laps > 10s off pace are likely errors)
        df = df[df["lap_time_delta"] < 10.0]
        df = df[df["lap_time_delta"] >= 0.0]

        if len(df) < 10:
            print("Warning: Not enough valid laps after filtering")
            return {"error": "Not enough data after filtering"}

        # Prepare features
        X = self._prepare_features(df)
        y = df["lap_time_delta"].values

        # Scale features
        X_scaled = self.scaler.fit_transform(X)

        # Split for validation
        X_train, X_val, y_train, y_val = train_test_split(
            X_scaled, y, test_size=0.2, random_state=42
        )

        # Train Gradient Boosting model
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=4,
            learning_rate=0.1,
            min_samples_leaf=5,
            random_state=42,
        )
        self.model.fit(X_train, y_train)

        # Calculate training stats
        train_score = self.model.score(X_train, y_train)
        val_score = self.model.score(X_val, y_val)
        train_rmse = np.sqrt(np.mean((self.model.predict(X_train) - y_train) ** 2))
        val_rmse = np.sqrt(np.mean((self.model.predict(X_val) - y_val) ** 2))

        self.is_trained = True

        self.training_stats = {
            "n_samples": len(df),
            "n_train": len(X_train),
            "n_val": len(X_val),
            "train_r2": train_score,
            "val_r2": val_score,
            "train_rmse": train_rmse,
            "val_rmse": val_rmse,
            "compounds": df["compound"].unique().tolist(),
            "feature_importance": dict(zip(
                self.feature_cols,
                self.model.feature_importances_.tolist()
            )),
        }

        return self.training_stats

    def predict_degradation(
        self,
        tyre_age: int,
        compound: str,
        track_temp: float = 30.0,
        air_temp: float = 25.0,
        fuel_load: float = 0.5,
    ) -> float:
        """
        Predict lap time delta for given conditions.

        Args:
            tyre_age: Number of laps on current tyres
            compound: Tyre compound (SOFT, MEDIUM, HARD, etc.)
            track_temp: Track temperature in Celsius
            air_temp: Air temperature in Celsius
            fuel_load: Estimated fuel load (0.0 to 1.0)

        Returns:
            Predicted lap time delta in seconds
        """
        if not self.is_trained:
            return 0.0

        # Create single-row DataFrame
        df = pd.DataFrame([{
            "tyre_age": tyre_age,
            "compound": compound.upper(),
            "track_temp": track_temp,
            "air_temp": air_temp,
            "fuel_load_estimate": fuel_load,
        }])

        X = self._prepare_features(df)
        X_scaled = self.scaler.transform(X)

        return float(self.model.predict(X_scaled)[0])

    def predict_stint_curve(
        self,
        compound: str,
        conditions: Dict,
        max_laps: int = 40,
    ) -> np.ndarray:
        """
        Predict full degradation curve for a stint.

        Args:
            compound: Tyre compound
            conditions: Dict with track_temp, air_temp keys
            max_laps: Maximum laps to predict

        Returns:
            Array of predicted lap time deltas for each lap
        """
        if not self.is_trained:
            return np.zeros(max_laps)

        track_temp = conditions.get("track_temp", 30.0)
        air_temp = conditions.get("air_temp", 25.0)

        predictions = []
        for lap in range(1, max_laps + 1):
            # Approximate fuel load decrease
            fuel_load = max(0.0, 1.0 - (lap / max_laps))

            delta = self.predict_degradation(
                tyre_age=lap,
                compound=compound,
                track_temp=track_temp,
                air_temp=air_temp,
                fuel_load=fuel_load,
            )
            predictions.append(delta)

        return np.array(predictions)

    def get_cliff_point(
        self,
        compound: str,
        conditions: Dict,
        threshold: float = 1.0,
        max_laps: int = 50,
    ) -> int:
        """
        Estimate when tyres fall off the cliff.

        Args:
            compound: Tyre compound
            conditions: Dict with track_temp, air_temp keys
            threshold: Lap time delta threshold for cliff (seconds)
            max_laps: Maximum laps to check

        Returns:
            Lap number when degradation exceeds threshold,
            or max_laps if cliff not reached
        """
        if not self.is_trained:
            return max_laps

        curve = self.predict_stint_curve(compound, conditions, max_laps)

        for i, delta in enumerate(curve):
            if delta > threshold:
                return i + 1

        return max_laps

    def get_optimal_stint_length(
        self,
        compound: str,
        conditions: Dict,
        target_delta: float = 0.5,
        max_laps: int = 50,
    ) -> int:
        """
        Estimate optimal stint length before significant degradation.

        Args:
            compound: Tyre compound
            conditions: Dict with track_temp, air_temp keys
            target_delta: Maximum acceptable lap time delta
            max_laps: Maximum laps to check

        Returns:
            Recommended stint length in laps
        """
        if not self.is_trained:
            return 20  # Default fallback

        curve = self.predict_stint_curve(compound, conditions, max_laps)

        for i, delta in enumerate(curve):
            if delta > target_delta:
                return max(1, i)

        return max_laps

    def compare_compounds(
        self,
        conditions: Dict,
        compounds: Optional[list] = None,
        max_laps: int = 40,
    ) -> Dict[str, np.ndarray]:
        """
        Compare degradation curves for multiple compounds.

        Args:
            conditions: Dict with track_temp, air_temp keys
            compounds: List of compounds to compare (default: SOFT, MEDIUM, HARD)
            max_laps: Maximum laps to predict

        Returns:
            Dict mapping compound to predicted degradation curve
        """
        if compounds is None:
            compounds = ["SOFT", "MEDIUM", "HARD"]

        results = {}
        for compound in compounds:
            results[compound] = self.predict_stint_curve(compound, conditions, max_laps)

        return results

    def get_degradation_rate(
        self,
        compound: str,
        conditions: Dict,
        start_lap: int = 5,
        end_lap: int = 20,
    ) -> float:
        """
        Calculate average degradation rate (seconds per lap).

        Args:
            compound: Tyre compound
            conditions: Dict with track_temp, air_temp keys
            start_lap: Start of measurement window
            end_lap: End of measurement window

        Returns:
            Average degradation rate in seconds per lap
        """
        if not self.is_trained:
            return 0.05  # Default estimate

        curve = self.predict_stint_curve(compound, conditions, end_lap)

        if len(curve) < end_lap:
            return 0.05

        # Calculate slope between start and end
        delta_time = curve[end_lap - 1] - curve[start_lap - 1]
        delta_laps = end_lap - start_lap

        return delta_time / delta_laps if delta_laps > 0 else 0.0
