import pickle
from pathlib import Path
from typing import Dict, Any, List
import pandas as pd

try:
    from .data_preprocessor import ALL_FEATURES
except ImportError:
    from data_preprocessor import ALL_FEATURES

DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "no_show_pipeline.joblib"

class NoShowPredictor:
    """
    Production Inference Engine for predicting OPD patient no-show probability
    and assessing smart overbooking eligibility.
    """

    def __init__(self, model_path: str = str(DEFAULT_MODEL_PATH)):
        self.model_path = Path(model_path)
        if not self.model_path.exists():
            raise FileNotFoundError(
                f"Model file not found at {self.model_path}. Train the model first using model_trainer.py"
            )
        with open(self.model_path, "rb") as f:
            self.pipeline = pickle.load(f)

    def predict_probability(self, features: Dict[str, Any]) -> float:
        """
        Accepts patient and booking attributes dictionary and returns
        calibrated no-show probability P(no-show) between 0.0 and 1.0.
        """
        # Ensure all required features are present with appropriate data types
        defaults = {
            "gender": "Female",
            "day_of_week": 0,
            "age": 35,
            "lead_days": 1,
            "appointment_hour": 10,
            "past_visits": 1,
            "past_no_shows": 0,
            "past_no_show_ratio": 0.0,
            "sms_received": 1,
            "hypertension": 0,
            "diabetes": 0
        }
        input_data = {}
        for feat in ALL_FEATURES:
            val = features.get(feat)
            if val is None or (feat == "gender" and not isinstance(val, str)):
                val = defaults.get(feat, 0)
            input_data[feat] = [val]

        df_input = pd.DataFrame(input_data)
        prob = self.pipeline.predict_proba(df_input)[0, 1]
        return float(round(prob, 3))

    def assess_smart_overbooking(
        self,
        features: Dict[str, Any],
        overbook_threshold: float = 0.50
    ) -> Dict[str, Any]:
        """
        Evaluates whether an appointment slot is safe to overbook
        based on the patient's predicted no-show risk and clinical indicators.
        """
        prob = self.predict_probability(features)

        # Risk categorization
        if prob >= 0.55:
            risk_level = "HIGH RISK"
            eligible_for_overbook = True
            action_recommendation = "SAFE TO OVERBOOK: High likelihood of patient absence. Secondary booking authorized."
        elif prob >= 0.30:
            risk_level = "MEDIUM RISK"
            eligible_for_overbook = False
            action_recommendation = "STANDARD SLOT: Monitor arrival. Send automated SMS reminder."
        else:
            risk_level = "LOW RISK"
            eligible_for_overbook = False
            action_recommendation = "CONFIRMED SLOT: High attendance expectation. Do not overbook."

        # Explain key drivers
        drivers: List[str] = []
        if features.get("lead_days", 0) >= 7:
            drivers.append(f"Long booking lead time ({features.get('lead_days')} days)")
        if features.get("past_no_show_ratio", 0.0) >= 0.30:
            drivers.append(f"High past no-show ratio ({features.get('past_no_show_ratio'):.0%})")
        if features.get("sms_received", 1) == 0:
            drivers.append("No SMS alert confirmed")
        if features.get("lead_days", 0) == 0:
            drivers.append("Same-day walk-in appointment (near 100% attendance)")

        return {
            "predicted_no_show_prob": prob,
            "attendance_probability": round(1.0 - prob, 3),
            "risk_level": risk_level,
            "eligible_for_overbook": eligible_for_overbook,
            "action_recommendation": action_recommendation,
            "key_drivers": drivers
        }
