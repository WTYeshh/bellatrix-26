import os
import socket

class CollectorConfig:
    TENANT_ID: str = os.getenv("AEGIS_TENANT_ID", "ORG_001")
    COLLECTOR_ID: str = os.getenv("AEGIS_COLLECTOR_ID", "COLLECTOR_001")
    # Pseudonymized source ID
    RAW_HOSTNAME: str = socket.gethostname()
    SOURCE_ID: str = os.getenv("AEGIS_SOURCE_ID", f"NODE_{abs(hash(RAW_HOSTNAME)) % 10000:04d}")
    
    SAAS_URL: str = os.getenv("AEGIS_SAAS_URL", "http://localhost:8000/api/v1")
    AUTH_TOKEN: str = os.getenv("AEGIS_AUTH_TOKEN", "aegis-collector-token-001")
    
    LOCAL_DB_PATH: str = os.getenv("AEGIS_LOCAL_DB", "collector_local.db")
    
    COLLECTION_INTERVAL_SECONDS: int = 5
    HEARTBEAT_INTERVAL_SECONDS: int = 15
    MAX_BUFFERED_RECORDS: int = 5000

collector_config = CollectorConfig()
