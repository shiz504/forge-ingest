from functools import lru_cache
import os

from pydantic import BaseModel


class Settings(BaseModel):
    ingest_token: str
    max_bytes: int = 5 * 1024 * 1024
    timeout_seconds: int = 60
    forge_host: str = "forge"
    forge_port: int = 2222
    deploy_key_path: str = "/run/secrets/forge_deploy_key"
    known_hosts_path: str = "/run/secrets/forge_known_hosts"
    repomix_version: str = "1.14.0"


@lru_cache
def get_settings() -> Settings:
    return Settings(
        ingest_token=os.environ.get("INGEST_TOKEN", ""),
        max_bytes=int(os.environ.get("INGEST_MAX_BYTES", 5 * 1024 * 1024)),
        timeout_seconds=int(os.environ.get("INGEST_TIMEOUT_SECONDS", 60)),
        forge_host=os.environ.get("INGEST_FORGE_HOST", "forge"),
        forge_port=int(os.environ.get("INGEST_FORGE_PORT", 2222)),
        deploy_key_path=os.environ.get("INGEST_DEPLOY_KEY_PATH", "/run/secrets/forge_deploy_key"),
        known_hosts_path=os.environ.get("INGEST_KNOWN_HOSTS_PATH", "/run/secrets/forge_known_hosts"),
        repomix_version=os.environ.get("REPOMIX_VERSION", "1.14.0"),
    )
