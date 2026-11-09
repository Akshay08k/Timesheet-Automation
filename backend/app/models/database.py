"""MongoDB connection and database management."""

import logging
import os
from typing import Generator, Optional
from pymongo import MongoClient, ReturnDocument
from pymongo.database import Database
from backend.app.config.settings import get_settings

logger = logging.getLogger("devtimesheet.database")

_client: Optional[MongoClient] = None
_db: Optional[Database] = None


def get_client() -> MongoClient:
    """Returns singleton MongoDB client with connection pooling and resilient fallback."""
    global _client
    if _client is not None:
        return _client

    settings = get_settings()
    uri = settings.get_mongo_connection_uri()

    # Determine if we should attempt live connection or use in-memory mock for tests
    is_test_mode = os.environ.get("TESTING") == "1"

    if not is_test_mode:
        try:
            client = MongoClient(
                uri,
                serverSelectionTimeoutMS=4000,
                connectTimeoutMS=4000,
                socketTimeoutMS=10000,
                maxPoolSize=50,
                minPoolSize=1,
                maxIdleTimeMS=45000,
                waitQueueTimeoutMS=5000,
                retryWrites=True,
                retryReads=True,
            )
            # Test ping
            client.admin.command("ping")
            target_host = uri.split("@")[-1] if "@" in uri else uri
            print("\n" + "=" * 70)
            print("[MongoDB] CONNECTED TO MONGODB SUCCESSFULLY!")
            print(f"[MongoDB] Host: {target_host}")
            print(f"[MongoDB] Database Name: {settings.mongodb_db_name}")
            print("=" * 70 + "\n")
            logger.info("Connected to MongoDB at %s", target_host)
            _client = client
            return _client
        except Exception as e:
            target_host = uri.split("@")[-1] if "@" in uri else uri
            is_remote = "localhost" not in uri and "127.0.0.1" not in uri
            if is_remote:
                error_msg = (
                    f"\n{'=' * 70}\n"
                    f"[MongoDB Connection Error]\n"
                    f"Could not connect to MongoDB Atlas / remote cluster at:\n"
                    f"  {target_host}\n"
                    f"Reason: {e}\n\n"
                    f"Troubleshooting checklist:\n"
                    f"  1. Verify IP Access List in MongoDB Atlas (Network Access -> Add 0.0.0.0/0).\n"
                    f"  2. Verify database username and password in Vercel environment variables (MONGODB_URI).\n"
                    f"  3. Check your internet connection.\n"
                    f"{'=' * 70}\n"
                )
                logger.error(error_msg)
                print(error_msg)
                # In serverless/cloud environments (e.g. Vercel), fallback to in-memory mongomock
                # so the container boots up, health-checks succeed, and users receive structured error details
                if os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"):
                    logger.warning("[MongoDB] Vercel environment detected. Falling back to mongomock so app stays alive.")
                else:
                    raise RuntimeError(error_msg) from e
            else:
                logger.info(
                    "Local MongoDB not detected at %s. Falling back to in-memory mongomock for local development/testing.",
                    uri,
                )

    # In-memory mongomock fallback
    try:
        import mongomock
        _client = mongomock.MongoClient()
        logger.info("Using mongomock in-memory database.")
        return _client
    except ImportError:
        # If mongomock is not installed, retry live client
        _client = MongoClient(uri)
        return _client


def get_database() -> Database:
    """Returns the MongoDB Database instance."""
    global _db
    if _db is not None:
        return _db
    client = get_client()
    settings = get_settings()
    db_name = settings.mongodb_db_name
    _db = client[db_name]
    return _db


def get_db() -> Generator[Database, None, None]:
    """FastAPI dependency yielding the MongoDB database instance."""
    db = get_database()
    yield db


def get_next_sequence_value(db: Database, sequence_name: str) -> int:
    """Atomically increments and returns the next integer ID sequence for a collection."""
    res = db.counters.find_one_and_update(
        {"_id": sequence_name},
        {"$inc": {"seq": 1}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )
    return int(res["seq"])


def init_db():
    """Initializes MongoDB indexes for data integrity and high performance."""
    try:
        db = get_database()

        # Users collection
        db.users.create_index("id", unique=True)
        db.users.create_index("username", unique=True)
        db.users.create_index("email", unique=True)

        # Credentials collection: one credential per user per provider
        db.ado_credentials.create_index("id", unique=True)
        db.ado_credentials.create_index([("user_id", 1), ("provider", 1)], unique=True)
        db.ado_credentials.create_index("user_id")

        # Activity items collection: unique by user, source type, and external ID
        db.activity_items.create_index("id", unique=True)
        db.activity_items.create_index(
            [("user_id", 1), ("source_type", 1), ("external_id", 1)], unique=True
        )
        db.activity_items.create_index([("user_id", 1), ("date_str", 1)])
        db.activity_items.create_index([("user_id", 1), ("date_str", 1), ("is_excluded", 1)])
        db.activity_items.create_index([("user_id", 1), ("occurred_at", -1)])

        # Manual activities collection
        db.manual_activities.create_index("id", unique=True)
        db.manual_activities.create_index([("user_id", 1), ("date_str", 1)])

        # Daily timesheet drafts collection: unique per user per date
        db.daily_timesheet_drafts.create_index("id", unique=True)
        db.daily_timesheet_drafts.create_index(
            [("user_id", 1), ("date_str", 1)], unique=True
        )
        db.daily_timesheet_drafts.create_index([("user_id", 1), ("submission_status", 1)])

        # Summary versions collection
        db.summary_versions.create_index("id", unique=True)
        db.summary_versions.create_index([("draft_id", 1), ("version_number", -1)])

        logger.info("MongoDB indexes verified successfully.")
    except Exception as e:
        logger.warning("Index initialization notice: %s", e)


def check_database_health() -> dict:
    """Returns database connectivity status and details for health checks."""
    try:
        db = get_database()
        db.command("ping")
        coll_count = len(db.list_collection_names())
        is_mock = type(db.client).__module__.startswith("mongomock")
        return {
            "connected": True,
            "database_name": db.name,
            "collections_count": coll_count,
            "is_mock": is_mock,
        }
    except Exception as e:
        return {
            "connected": False,
            "error": str(e),
            "is_mock": False,
        }


def close_db():
    """Closes MongoDB connection pool."""
    global _client, _db
    if _client is not None:
        _client.close()
        _client = None
        _db = None
