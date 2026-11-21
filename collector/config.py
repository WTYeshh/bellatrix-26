import os

class CollectorConfig:
    TENANT_ID: str = "default"
    NODE_ID: str = "server-01"
    SOURCE_ID: str = "server-01"
    COLLECTOR_ID: str = "COLLECTOR_SERVER_01"
    AUTH_TOKEN: str = "aegis-collector-token-server01"
    SALT: str = "aegis-privacy-salt-2026"
    
    SAAS_URL: str = os.getenv("AEGIS_SAAS_URL", "http://127.0.0.1:8000/api/v1")
    LOCAL_DB_PATH: str = os.getenv("AEGIS_LOCAL_DB", "collector_local.db")
    
    COLLECTION_INTERVAL_SECONDS: int = 3
    HEARTBEAT_INTERVAL_SECONDS: int = 15
    MAX_BUFFERED_RECORDS: int = 5000

collector_config = CollectorConfig()
