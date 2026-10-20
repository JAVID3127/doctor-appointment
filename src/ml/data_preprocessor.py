from typing import Tuple, List
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.preprocessing import StandardScaler, OneHotEncoder

NUMERIC_FEATURES: List[str] = [
    "age", "lead_days", "appointment_hour",
    "past_visits", "past_no_shows", "past_no_show_ratio"
]

CATEGORICAL_FEATURES: List[str] = [
    "gender", "day_of_week"
]

BINARY_FEATURES: List[str] = [
    "sms_received", "hypertension", "diabetes"
]

ALL_FEATURES: List[str] = NUMERIC_FEATURES + CATEGORICAL_FEATURES + BINARY_FEATURES
TARGET_COLUMN: str = "no_show"

def build_preprocessor() -> ColumnTransformer:
    """Builds a scikit-learn ColumnTransformer for OPD features."""
    preprocessor = ColumnTransformer(
        transformers=[
            ("num", StandardScaler(), NUMERIC_FEATURES),
            ("cat", OneHotEncoder(handle_unknown="ignore", drop="first"), CATEGORICAL_FEATURES),
            ("bin", "passthrough", BINARY_FEATURES),
        ]
    )
    return preprocessor

def load_and_split_data(csv_path: str, test_size: float = 0.2, random_state: int = 42) -> Tuple[pd.DataFrame, pd.DataFrame, pd.Series, pd.Series]:
    """Loads CSV dataset and splits into stratified train and test partitions."""
    df = pd.read_csv(csv_path)
    X = df[ALL_FEATURES]
    y = df[TARGET_COLUMN]

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=random_state, stratify=y
    )
    return X_train, X_test, y_train, y_test
