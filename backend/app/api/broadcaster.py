import asyncio
import json
from typing import List, Dict, Any

class EventBroadcaster:
    """
    Manages live event subscribers for real-time SSE streaming.
    Whenever new telemetry, anomalies, or correlated incidents occur,
    broadcasts event to connected dashboard tabs instantly.
    """
    def __init__(self):
        self._subscribers: List[asyncio.Queue] = []

    def subscribe(self) -> asyncio.Queue:
        q = asyncio.Queue()
        self._subscribers.append(q)
        return q

    def unsubscribe(self, q: asyncio.Queue):
        if q in self._subscribers:
            self._subscribers.remove(q)

    async def broadcast(self, event_type: str, data: Dict[str, Any]):
        dead = []
        payload = {"event": event_type, "data": data}
        for q in self._subscribers:
            try:
                q.put_nowait(payload)
            except Exception:
                dead.append(q)
        for d in dead:
            self.unsubscribe(d)

broadcaster = EventBroadcaster()
