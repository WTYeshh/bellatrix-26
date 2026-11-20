from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.app.database import get_db
from backend.app.models import Collector
from backend.app.schemas import IngestionAck
from backend.app.ingestion.pipeline import process_ingestion_payload

router = APIRouter(prefix="/ingestion", tags=["Ingestion"])

@router.post("/metadata", response_model=IngestionAck)
async def ingest_metadata(
    request: Request,
    x_tenant_id: str = Header(..., alias="X-Tenant-Id"),
    x_collector_id: str = Header(..., alias="X-Collector-Id"),
    x_auth_token: str = Header(..., alias="X-Auth-Token"),
    db: AsyncSession = Depends(get_db)
):
    """
    Tier 2 Ingestion API:
    - Receives approved metadata payloads from Tier 1 collector
    - Authenticates collector via token and derives tenant identity from database
    - Never trusts X-Tenant-Id alone
    - Enforces field allow-listing & SHA-256 integrity
    - Prevents duplicates (idempotent)
    - Triggers AIOps anomaly detector & correlation
    """
    # 1. Authenticate collector and derive tenant identity
    col_stmt = select(Collector).where(Collector.collector_id == x_collector_id)
    collector = (await db.execute(col_stmt)).scalar_one_or_none()

    if not collector or collector.auth_token != x_auth_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Collector authentication failed: Invalid collector ID or auth token."
        )

    # Derived authentic tenant from collector registration record
    authenticated_tenant = collector.tenant_id

    # Cross-check header matches authentic tenant
    if x_tenant_id != authenticated_tenant:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant ID mismatch: Supplied X-Tenant-Id does not match authorized collector tenant."
        )

    try:
        payload_data = await request.json()
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
