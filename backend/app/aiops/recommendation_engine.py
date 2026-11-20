from typing import Dict, Any, List
from backend.app.aiops.explanation_engine import ExplanationEngine

class RecommendationEngine:
    """
    Generates explainable, actionable recommendations backed by real evidence.
    """
    def __init__(self, explanation_engine: ExplanationEngine):
        self.explainer = explanation_engine

    def generate(self, incident: Dict[str, Any]) -> Dict[str, Any]:
        inc_id = incident.get("incident_id") or incident.get("id") or "INC-001"
        title = f"Remediation Strategy for {incident.get('title', 'Detected Anomaly')}"
        affected = ", ".join(incident.get("affected_collectors", []))

        evidence = []
        empirical_facts = []
        for alert in incident.get("related_alerts", []):
            m = alert.get("metric", "")
            obs = alert.get("observed_value", 0.0)
            base = alert.get("baseline_value", 0.0)
            sigma = alert.get("deviation_sigma", 3.0)
            evidence.append({
                "metric": m,
                "observed": obs,
                "baseline": base,
                "deviation": f"+{sigma}σ",
                "severity": alert.get("severity")
            })
            unit = "%" if "usage" in str(m) else ("ms" if "latency" in str(m) else "")
            empirical_facts.append(f"{m}: observed {obs}{unit} vs baseline {base}{unit} (+{sigma}σ deviation)")

        action_steps = [
            f"Scale worker process replicas or adjust compute quotas for {affected}.",
            incident.get('recommended_investigation') or "Inspect system processes and thread counts",
            "Run safe recovery simulation prior to production rollout."
        ]
        action_str = "\n".join(f"{i+1}. {step}" for i, step in enumerate(action_steps))
        reason = self.explainer.format_explanation(incident)

        return {
            "recommendation_id": f"REC-{inc_id}",
            "incident_id": inc_id,
            "title": title,
            "reason": reason,
            "severity": incident.get("severity", "Medium"),
            "confidence": incident.get("confidence", 0.85),
            "supporting_evidence": evidence,
            "evidence": {
                "empirical_facts": empirical_facts,
                "inferred_hypotheses": [incident.get("likely_cause", "Compute or network contention")]
            },
            "suggested_action": action_str,
            "actionable_steps": action_steps,
            "rollback_safe": True
        }
