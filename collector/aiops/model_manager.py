import os
import pickle
from typing import List, Tuple, Optional
import numpy as np
from sklearn.ensemble import IsolationForest

class LocalModelManager:
    """
    Tier 1 Local ML Model Manager:
    Trains, persists and manages local Isolation Forest instances.
    Enforces minimum sample bounds before claiming training readiness.
    """
    MIN_TRAINING_SAMPLES = 15
    MODEL_FILE = "collector_local_iforest.pkl"

    def __init__(self, persistence_path: Optional[str] = None):
        self.model_path = persistence_path or self.MODEL_FILE
        self.model_version = "v1.0.0-local"
        self._samples: List[List[float]] = []
        self._model: Optional[IsolationForest] = None
        self._load_model()

    def _load_model(self):
        if os.path.exists(self.model_path):
            try:
                with open(self.model_path, "rb") as f:
                    data = pickle.load(f)
                    self._model = data.get("model")
                    self.model_version = data.get("version", "v1.0.0-local")
            except Exception:
                self._model = None

    def _save_model(self):
        try:
            with open(self.model_path, "wb") as f:
                pickle.dump({"model": self._model, "version": self.model_version}, f)
        except Exception:
            pass

    def add_sample(self, vector: List[float]):
        self._samples.append(vector)
        # Keep rolling buffer of up to 100 observations
        if len(self._samples) > 100:
            self._samples.pop(0)

        # Trigger training once threshold reached
        if len(self._samples) >= self.MIN_TRAINING_SAMPLES and self._model is None:
            self.train()

    def train(self) -> bool:
        if len(self._samples) < self.MIN_TRAINING_SAMPLES:
            return False
        X = np.array(self._samples, dtype=float)
        clf = IsolationForest(n_estimators=40, contamination=0.1, random_state=42)
        clf.fit(X)
        self._model = clf
        self._save_model()
        return True

    def predict(self, vector: List[float]) -> Tuple[bool, float, str]:
        """
        Returns (is_anomaly, anomaly_score, status_message)
        """
        if self._model is None:
            return False, 0.0, f"COLLECTING_BASELINE ({len(self._samples)}/{self.MIN_TRAINING_SAMPLES})"

        X = np.array([vector], dtype=float)
        pred = self._model.predict(X)[0]
        score = self._model.decision_function(X)[0]
        # Normalized score: lower score means more anomalous
        norm_score = round(max(0.0, min(1.0, 0.5 - (score * 2.0))), 2)
        is_anom = bool(pred == -1 and norm_score >= 0.58)
        return is_anom, norm_score, "TRAINED"
