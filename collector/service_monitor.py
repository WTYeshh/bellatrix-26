import sys
import psutil
from typing import Dict, Any, List, Optional

class ServiceMonitor:
    """
    Tier 1 Windows Service Monitoring.
    Monitors state, availability, and transitions for explicitly configured services.
    Does not claim all Windows services are monitored unless configured.
    """
    DEFAULT_SERVICES = [
        "EventLog", "LanmanServer", "wuauserv", "Spooler", "Themes", "PlugPlay", "RpcSs"
    ]

    def __init__(self, services: Optional[List[str]] = None):
        self.monitored_services = services or self.DEFAULT_SERVICES
        self._last_states: Dict[str, str] = {}

    def collect(self) -> Dict[str, Any]:
        results = []
        transitions = []
        running_count = 0

        if sys.platform == "win32":
            for sname in self.monitored_services:
                try:
                    srv = psutil.win_service_get(sname)
                    info = srv.as_dict()
                    curr_status = info.get("status", "unknown")
                    if curr_status == "running":
                        running_count += 1

                    prev_status = self._last_states.get(sname)
                    if prev_status and prev_status != curr_status:
                        transitions.append({
                            "service": sname,
                            "previous": prev_status,
                            "current": curr_status
                        })
                    self._last_states[sname] = curr_status

                    results.append({
                        "name": info.get("name", sname),
                        "display_name": info.get("display_name", sname),
                        "status": curr_status,
                        "start_type": info.get("start_type", "unknown")
                    })
                except Exception:
                    results.append({
                        "name": sname,
                        "display_name": sname,
                        "status": "stopped",
                        "start_type": "manual"
                    })
        else:
            # Fallback on non-windows dev
            for sname in self.monitored_services:
                results.append({
                    "name": sname,
                    "display_name": f"{sname} (Simulated)",
                    "status": "running",
                    "start_type": "automatic"
                })
            running_count = len(self.monitored_services)

        return {
            "monitored_service_count": len(self.monitored_services),
            "running_service_count": running_count,
            "services": results,
            "state_transitions": transitions
        }
