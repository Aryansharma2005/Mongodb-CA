"""
MongoDB Collection Accessors and Schema Constants for Personal Expense Tracker.
"""
from database.connection import get_db

COLLECTION_CATEGORIES = "categories"
COLLECTION_TRANSACTIONS = "transactions"
COLLECTION_USERS = "users"


def get_categories_collection(db=None):
    """Returns the categories MongoDB collection."""
    if db is None:
        db = get_db()
    return db[COLLECTION_CATEGORIES]


def get_transactions_collection(db=None):
    """Returns the transactions MongoDB collection."""
    if db is None:
        db = get_db()
    return db[COLLECTION_TRANSACTIONS]


def get_users_collection(db=None):
    """Returns the users MongoDB collection."""
    if db is None:
        db = get_db()
    return db[COLLECTION_USERS]
