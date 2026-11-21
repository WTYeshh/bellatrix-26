import os
import pickle
from typing import Dict, List, Tuple, Optional
import numpy as np
from sklearn.ensemble import IsolationForest

class CentralModelManager:
    """
    Tier 2 Central ML Model Manager:
    Trains, manages and persists tenant-partitioned Isolation Forest models.
    """
    MIN_SAMPLES = 10

    def __init__(self, storage_dir: str = ".models"):
        self.storage_dir = storage_dir
        self.model_version = "v1.0.0-central"
        self._training_buffers: Dict[str, List[List[float]]] = {}
        self._models: Dict[str, IsolationForest] = {}
        if not os.path.exists(self.storage_dir):
            try:
                os.makedirs(self.storage_dir, exist_ok=True)
            except Exception:
                pass

    def add_training_vector(self, tenant_id: str, vector: List[float]):
        if tenant_id not in self._training_buffers:
            self._training_buffers[tenant_id] = []
        buf = self._training_buffers[tenant_id]
        buf.append(vector)
        if len(buf) > 150:
            buf.pop(0)

        # Trigger model training once sample threshold reached
        if len(buf) >= self.MIN_SAMPLES and tenant_id not in self._models:
            self.train_model(tenant_id)

    def train_model(self, tenant_id: str) -> bool:
        buf = self._training_buffers.get(tenant_id, [])
        if len(buf) < self.MIN_SAMPLES:
            return False
        X = np.array(buf, dtype=float)
        clf = IsolationForest(n_estimators=50, contamination=0.1, random_state=42)
        clf.fit(X)
        self._models[tenant_id] = clf
        return True

    def score(self, tenant_id: str, vector: List[float]) -> Tuple[bool, float, str]:
        """
        Runs Isolation Forest anomaly scoring.
        Returns: (is_anomaly, anomaly_score, status_message)
        """
        model = self._models.get(tenant_id)
        if not model:
            sample_count = len(self._training_buffers.get(tenant_id, []))
            return False, 0.20, f"COLLECTING_SAMPLES ({sample_count}/{self.MIN_SAMPLES})"

        X = np.array([vector], dtype=float)
        pred = model.predict(X)[0]
        decision = model.decision_function(X)[0]
        # Normalized score: 0.0 (normal) to 1.0 (anomalous)
        score = round(max(0.0, min(1.0, 0.5 - (decision * 2.0))), 2)
        is_anom = bool(pred == -1)
        return is_anom, score, "TRAINED"
