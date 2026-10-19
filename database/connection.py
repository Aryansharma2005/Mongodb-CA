import os
import logging
from pathlib import Path
from dotenv import load_dotenv
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError

# Load environment variables
BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

logger = logging.getLogger(__name__)

MONGODB_URI = os.getenv("MONGODB_URI", "mongodb://localhost:27017/")
MONGODB_DB_NAME = os.getenv("MONGODB_DB_NAME", "expense_tracker_db")

_client = None
_db = None
_is_mock = False


def init_connection(force_mock: bool = False, timeout_ms: int = 3000):
    """
    Initializes and caches the MongoDB client and database.
    If the real MongoDB server (Atlas / local) is unreachable or force_mock is True,
    it falls back to mongomock so the application continues functioning smoothly.
    """
    global _client, _db, _is_mock

    if force_mock:
        import mongomock
        logger.info("Initializing in-memory mongomock database client.")
        _client = mongomock.MongoClient()
        _db = _client[MONGODB_DB_NAME]
        _is_mock = True
        return _db

    try:
        logger.info(f"Connecting to MongoDB at: {MONGODB_URI.split('@')[-1] if '@' in MONGODB_URI else MONGODB_URI}")
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=timeout_ms)
        # Verify server is responding
        client.admin.command("ping")
        _client = client
        _db = _client[MONGODB_DB_NAME]
        _is_mock = False
        logger.info(f"Successfully connected to MongoDB database '{MONGODB_DB_NAME}'")
        return _db
    except (ConnectionFailure, ServerSelectionTimeoutError, Exception) as exc:
        logger.warning(
            f"Could not connect to live MongoDB ({exc}). "
            f"Falling back to in-memory mongomock for offline/demo operation. "
            f"To connect to MongoDB Atlas, set MONGODB_URI in your .env file."
        )
        import mongomock
        _client = mongomock.MongoClient()
        _db = _client[MONGODB_DB_NAME]
        _is_mock = True
        return _db


def get_client():
    """Returns the MongoClient instance (creating it if necessary)."""
    global _client
    if _client is None:
        init_connection()
    return _client


def get_db():
    """Returns the Database instance (creating it if necessary)."""
    global _db
    if _db is None:
        init_connection()
    return _db


def is_mock_db() -> bool:
    """Returns True if the current connection is running on in-memory mongomock."""
    global _is_mock
    if _db is None:
        init_connection()
    return _is_mock


def check_connection() -> dict:
    """
    Returns connection health and details for UI status banner.
    """
    try:
        db = get_db()
        client = get_client()
        if _is_mock:
            return {
                "connected": True,
                "is_mock": True,
                "db_name": MONGODB_DB_NAME,
                "message": "Running on in-memory MongoMock (offline demo mode). Set MONGODB_URI in .env to connect to MongoDB Atlas."
            }
        # Run ping to test live server
        client.admin.command("ping")
        # Mask credentials in URI for display
        masked_uri = MONGODB_URI
        if "@" in masked_uri:
            prefix = masked_uri.split("@")[0].split("://")[0]
            host = masked_uri.split("@")[1]
            masked_uri = f"{prefix}://*****@{host}"
        return {
            "connected": True,
            "is_mock": False,
            "db_name": MONGODB_DB_NAME,
            "server_uri": masked_uri,
            "message": f"Connected to live MongoDB ({MONGODB_DB_NAME})"
        }
    except Exception as e:
        return {
            "connected": False,
            "is_mock": False,
            "error": str(e),
            "message": f"Failed to connect to MongoDB: {str(e)}"
        }
