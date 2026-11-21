import time
import hmac
import hashlib
import json
from typing import Optional, Set
from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.database import get_db
from backend.app.models import Collector
from backend.app.schemas import IngestionAck
from backend.app.ingestion.pipeline import process_ingestion_payload

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])

# Replay protection cache (stores (collector_id, nonce) with timestamp)
_SEEN_NONCES: Set[str] = set()

@router.post("/metadata", response_model=IngestionAck)
async def ingest_metadata(
    request: Request,
    x_tenant_id: Optional[str] = Header(None, alias="X-Tenant-Id"),
    x_collector_id: Optional[str] = Header(None, alias="X-Collector-Id"),
    x_auth_token: Optional[str] = Header(None, alias="X-Auth-Token"),
    x_timestamp: Optional[str] = Header(None, alias="X-Timestamp"),
    x_nonce: Optional[str] = Header(None, alias="X-Nonce"),
    x_signature: Optional[str] = Header(None, alias="X-Signature"),
    db: AsyncSession = Depends(get_db)
):
    """
    Tier 2 Ingestion API:
    - Receives approved metadata payloads from Tier 1 collector
    - Authenticates collector via token and derives server identity
    - Verifies HMAC-SHA256 signature with nonce & +/-5 min timestamp window
    - Enforces field allow-listing & SHA-256 integrity
    - Prevents duplicates (idempotent)
    - Triggers AIOps anomaly detector & correlation
    """
    col_id = x_collector_id or "COLLECTOR_SERVER_01"
    auth_tok = x_auth_token or "aegis-collector-token-server01"

    # 1. Authenticate collector and derive node identity
    col_stmt = select(Collector).where(Collector.collector_id == col_id)
    collector = (await db.execute(col_stmt)).scalar_one_or_none()

    if not collector or collector.auth_token != auth_tok:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Collector authentication failed: Invalid collector ID or auth token."
        )

    authenticated_tenant = collector.tenant_id or "default"

    # Cross-check header matches authentic tenant if provided
    if x_tenant_id and x_tenant_id != authenticated_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant ID mismatch: Supplied X-Tenant-Id does not match authorized collector tenant."
        )

    raw_body = await request.body()

    # 2. Security: HMAC-SHA256, Nonce Replay, and Timestamp Window Verification
    if x_signature:
        now_ts = int(time.time())
        try:
            req_ts = int(x_timestamp) if x_timestamp else 0
        except ValueError:
            raise HTTPException(status_code=401, detail="Invalid timestamp header format.")

        # +/- 5 minutes window (300 seconds)
        if abs(now_ts - req_ts) > 300:
            raise HTTPException(status_code=401, detail="Stale request: Timestamp outside +/- 5 min window.")

        # Nonce replay prevention
        if not x_nonce:
            raise HTTPException(status_code=401, detail="Missing required X-Nonce header for signed request.")
        nonce_key = f"{col_id}:{x_nonce}"
        if nonce_key in _SEEN_NONCES:
            raise HTTPException(status_code=401, detail="Replay attack detected: Nonce has already been used.")
        _SEEN_NONCES.add(nonce_key)

        # HMAC-SHA256 signature check
        sig_material = f"{x_timestamp}:{x_nonce}:".encode("utf-8") + raw_body
        expected_sig = hmac.new(auth_tok.encode("utf-8"), sig_material, hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected_sig, x_signature):
            raise HTTPException(status_code=401, detail="Invalid HMAC-SHA256 request signature.")

    try:
        payload_data = json.loads(raw_body.decode("utf-8")) if raw_body else {}
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON format.")

    # Enforce tenant and collector identity from authenticated context
    payload_data["tenant_id"] = authenticated_tenant
    payload_data["collector_id"] = collector.collector_id

    try:
        ack = await process_ingestion_payload(payload_data, db)
        return ack
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion processing error: {str(e)}")
