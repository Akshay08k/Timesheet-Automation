"""Application configuration settings using Pydantic Settings."""

import os
import re
import urllib.parse
from functools import lru_cache
from typing import Optional
from pydantic import Field, AliasChoices
from pydantic_settings import BaseSettings, SettingsConfigDict


def is_valid_mongo_uri(uri: str) -> bool:
    """Verifies that the URI has a valid protocol and includes a non-empty host."""
    if not uri or not isinstance(uri, str):
        return False
    uri = uri.strip()
    if not (uri.startswith("mongodb://") or uri.startswith("mongodb+srv://")):
        return False
    if uri.endswith("@"):
        return False
    try:
        after_proto = uri.split("://", 1)[1]
        if "@" in after_proto:
            host_part = after_proto.rsplit("@", 1)[1].split("/", 1)[0].split("?", 1)[0]
        else:
            host_part = after_proto.split("/", 1)[0].split("?", 1)[0]
        return bool(host_part.strip())
    except Exception:
        return False


def _read_env_file_key(key: str, env_path: str = ".env") -> Optional[str]:
    """Reads raw key value from .env file directly, avoiding naive comment truncation at '#'."""
    if not os.path.exists(env_path):
        return None
    try:
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line.startswith("#") or not line:
                    continue
                if line.startswith(f"{key}="):
                    val = line.split("=", 1)[1].strip()
                    if (val.startswith('"') and val.endswith('"')) or (val.startswith("'") and val.endswith("'")):
                        val = val[1:-1]
                    return val
    except Exception:
        pass
    return None


def normalize_mongodb_uri(uri: str) -> str:
    """Safely URL-encodes credentials in MongoDB URI if they contain special characters like '@' or '#'."""
    if not uri or not (uri.startswith("mongodb://") or uri.startswith("mongodb+srv://")):
        return uri
    match = re.match(r"^(mongodb(?:\+srv)?:\/\/)([^:]+):(.*)@([^@\/]+)(\/?.*)$", uri)
    if match:
        proto, user, pwd, host, rest = match.groups()
        # unquote first to prevent double-encoding, then quote
        user_enc = urllib.parse.quote_plus(urllib.parse.unquote_plus(user))
        pwd_enc = urllib.parse.quote_plus(urllib.parse.unquote_plus(pwd))
        return f"{proto}{user_enc}:{pwd_enc}@{host}{rest}"
    return uri


class Settings(BaseSettings):
    app_env: str = "development"
    host: str = "127.0.0.1"
    port: int = 8000
    debug: bool = True

    # Security
    secret_key: str = "dev_secret_key_change_in_production_min_32_characters_long"
    pat_encryption_key: Optional[str] = None
    access_token_expire_minutes: int = 60 * 24 * 7  # 7 days

    # MongoDB Database
    mongodb_uri: str = Field(
        default="mongodb://localhost:27017",
        validation_alias=AliasChoices("MONGODB_URI", "MONGODB_URL", "DATABASE_URL"),
    )
    mongodb_db_name: str = Field(
        default="devtimesheet",
        validation_alias=AliasChoices("MONGODB_DB_NAME", "MONGO_DB_NAME", "DB_NAME"),
    )

    # Gemini AI
    gemini_api_key: Optional[str] = None
    gemini_model: str = "gemini-3.5-flash"
    gemini_fallback_model: str = "gemini-3.8-flash"

    # Azure DevOps Defaults
    default_client_org_url: str = Field(
        default="https://dev.azure.com/ClientCompany",
        validation_alias=AliasChoices("DEFAULT_CLIENT_ORG_URL", "DEFAULT_CLIENTCOMPANY_ORG_URL"),
    )
    default_mycompany_org_url: str = Field(
        default="https://dev.azure.com/MyCompany",
        validation_alias=AliasChoices("DEFAULT_MYCOMPANY_ORG_URL", "DEFAULT_RYSUN_ORG_URL", "DEFAULT_COMPANY_ORG_URL"),
    )
    # Compatibility alias for default_rysun_org_url
    @property
    def default_rysun_org_url(self) -> str:
        return self.default_mycompany_org_url

    # Default Timesheet Project Metadata
    default_client_name: str = Field(
        default="ClientCompany",
        validation_alias=AliasChoices("DEFAULT_CLIENT_NAME"),
    )
    default_iteration: str = Field(
        default="MyCompany Project Management",
        validation_alias=AliasChoices("DEFAULT_ITERATION"),
    )
    default_project_name: str = Field(
        default="ClientCompany - Core Enhancements",
        validation_alias=AliasChoices("DEFAULT_PROJECT_NAME"),
    )
    default_area_path: str = Field(
        default=r"MyCompany Project Management\ClientCompany",
        validation_alias=AliasChoices("DEFAULT_AREA_PATH"),
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    def get_mongo_connection_uri(self) -> str:
        """Returns the normalized MongoDB connection string, prioritizing valid URIs."""
        # 1. Check direct .env parsing first (avoids shell or dotenv comment truncation)
        for var in ["MONGODB_URI", "MONGODB_URL", "DATABASE_URL"]:
            val = _read_env_file_key(var)
            if val and is_valid_mongo_uri(val):
                return normalize_mongodb_uri(val)

        # 2. Check os.environ if valid
        for var in ["MONGODB_URI", "MONGODB_URL", "DATABASE_URL"]:
            val = os.environ.get(var)
            if val and is_valid_mongo_uri(val):
                return normalize_mongodb_uri(val)

        # 3. Fallback to self.mongodb_uri if valid
        if is_valid_mongo_uri(self.mongodb_uri):
            return normalize_mongodb_uri(self.mongodb_uri)

        return self.mongodb_uri


@lru_cache()
def get_settings() -> Settings:
    return Settings()
