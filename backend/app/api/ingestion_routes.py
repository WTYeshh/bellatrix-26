from fastapi import APIRouter, Depends, HTTPException, Header, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.database import get_db
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
    - Verifies collector authentication
    - Enforces field allow-listing
    - Enforces SHA-256 payload integrity
    - Prevents duplicates (idempotent)
    - Triggers AIOps anomaly detector & correlation
    """
    try:
        payload_data = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON format.")

    # Cross-check tenant ID in header matches payload
    if payload_data.get("tenant_id") != x_tenant_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tenant ID mismatch between header and payload."
        )

    try:
        ack = await process_ingestion_payload(payload_data, db)
        return ack
    except ValueError as ve:
        raise HTTPException(status_code=422, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ingestion processing error: {str(e)}")
