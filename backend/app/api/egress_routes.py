import json
import hashlib
from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import desc

from backend.app.database import get_db
from backend.app.models import EgressProof, User
from backend.app.schemas import EgressProofOut
from backend.app.auth.security import get_current_user

router = APIRouter(prefix="/egress-proof", tags=["Egress Proof"])

@router.get("", response_model=List[EgressProofOut])
@router.get("/", response_model=List[EgressProofOut])
@router.get("/proofs", response_model=List[EgressProofOut])
async def list_egress_proofs(
    current_user: User = Depends(get_current_user),
    limit: int = 50,
    db: AsyncSession = Depends(get_db)
):
    """
    DIFFERENTIATOR 2: REAL EGRESS PROOF
    Returns the verifiable log of every transmitted payload:
    - Payload ID
    - Approved field names
    - Redacted / dropped fields
    - Applied policy
    - Exact transmitted JSON
    - SHA-256 hash
    - Verification match
    """
    stmt = (
        select(EgressProof)
        .where(EgressProof.tenant_id == current_user.tenant_id)
        .order_by(desc(EgressProof.timestamp_utc))
        .limit(limit)
    )
    records = (await db.execute(stmt)).scalars().all()
    out = []

    for r in records:
        try:
            app_fields = json.loads(r.approved_fields) if isinstance(r.approved_fields, str) else r.approved_fields
        except:
            app_fields = []
        try:
            red_fields = json.loads(r.redacted_fields) if isinstance(r.redacted_fields, str) else r.redacted_fields
        except:
            red_fields = []

        # Independently verify SHA-256 hash match on the fly
        calculated_hash = hashlib.sha256(r.exact_transmitted_json.encode("utf-8")).hexdigest()
        is_verified = (calculated_hash == r.payload_hash)

        out.append(EgressProofOut(
            payload_id=r.payload_id,
            tenant_id=r.tenant_id,
            source_id=r.source_id,
            timestamp_utc=r.timestamp_utc.isoformat() if r.timestamp_utc else "",
            raw_local_log_blocked=r.raw_local_log_blocked,
            sanitized_saas_payload=r.exact_transmitted_json,
            approved_fields=app_fields,
            redacted_fields=red_fields,
            applied_policy=r.applied_policy,
            exact_transmitted_json=r.exact_transmitted_json,
            payload_hash=r.payload_hash,
            transmission_status=r.transmission_status,
            server_ack_utc=r.server_ack_utc.isoformat() if r.server_ack_utc else "",
            hash_verified=is_verified
        ))
    return out
