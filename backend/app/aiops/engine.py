from typing import List, Dict, Any, Optional, Tuple
from backend.app.aiops.baseline_engine import FleetBaselineEngine
from backend.app.aiops.model_manager import CentralModelManager
from backend.app.aiops.anomaly_engine import CentralAnomalyEngine
from backend.app.aiops.correlation_engine import IncidentCorrelationEngine
from backend.app.aiops.incident_engine import IncidentLifecycleEngine
from backend.app.aiops.explanation_engine import ExplanationEngine
from backend.app.aiops.recommendation_engine import RecommendationEngine

class UnifiedAIOpsEngine:
    """
    Tier 2 Central AIOps Master Orchestrator:
    Combines baseline calculation, anomaly detection, Incident DNA correlation,
    and explainable recommendations into a cohesive multi-tenant pipeline.
    """
    def __init__(self):
        self.baseline_engine = FleetBaselineEngine(window_size=40)
        self.model_manager = CentralModelManager()
        self.anomaly_engine = CentralAnomalyEngine(self.baseline_engine, self.model_manager)
        self.correlation_engine = IncidentCorrelationEngine()
        self.incident_lifecycle = IncidentLifecycleEngine()
        self.explanation_engine = ExplanationEngine()
        self.recommendation_engine = RecommendationEngine(self.explanation_engine)

    def record_observation(self, tenant_id: str, source_id: str, metric: str, value: float):
        self.baseline_engine.record(tenant_id, source_id, metric, value)

    def calculate_statistical_baseline(self, tenant_id: str, source_id: str, metric: str) -> Dict[str, float]:
        return self.baseline_engine.get_baseline(tenant_id, source_id, metric)

    def detect_statistical_anomaly(
        self,
        tenant_id: str,
        source_id: str,
        metric: str,
        current_value: float
    ) -> Optional[Dict[str, Any]]:
        # Single metric statistical check
        anomalies = self.anomaly_engine.analyze(tenant_id, {"source_id": source_id, metric: current_value})
        for a in anomalies:
            if a.get("metric") == metric:
                return a
        return None

    def train_isolation_forest(self, tenant_id: str, feature_matrix: List[List[float]]):
        for vec in feature_matrix:
            self.model_manager.add_training_vector(tenant_id, vec)
        self.model_manager.train_model(tenant_id)

    def score_multivariate_ml(self, tenant_id: str, features: List[float]) -> Tuple[bool, float]:
        is_anom, score, _ = self.model_manager.score(tenant_id, features)
        return is_anom, score

    def correlate_incident_dna(
        self,
        tenant_id: str,
        anomalies: List[Dict[str, Any]],
        existing_active_incidents: List[Any]
    ) -> Optional[Dict[str, Any]]:
        return self.correlation_engine.correlate(tenant_id, anomalies, existing_active_incidents)

    def generate_explainable_recommendation(
        self,
        incident: Dict[str, Any]
    ) -> Dict[str, Any]:
        return self.recommendation_engine.generate(incident)

# Global singleton and aliases
aiops_engine = UnifiedAIOpsEngine()
AIOpsEngine = UnifiedAIOpsEngine
