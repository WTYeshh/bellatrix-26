import asyncio
import json
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from backend.app.api.broadcaster import broadcaster

router = APIRouter(prefix="/events", tags=["Live Telemetry Streaming"])

@router.get("/stream")
async def event_stream():
    """
    Server-Sent Events (SSE) streaming endpoint.
    Pushes real-time telemetry, anomaly alerts and incident updates
    directly to connected dashboard instances.
    """
    async def sse_generator():
        q = broadcaster.subscribe()
        try:
            # Send initial keepalive
            yield f"data: {json.dumps({'event': 'connected', 'msg': 'AEGIS Real-time Stream Active'})}\n\n"
            while True:
                try:
                    payload = await asyncio.wait_for(q.get(), timeout=25.0)
                    yield f"data: {json.dumps(payload)}\n\n"
                except asyncio.TimeoutError:
                    # Keepalive ping
                    yield f": ping\n\n"
        finally:
            broadcaster.unsubscribe(q)

    return StreamingResponse(
        sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no"
        }
    )
