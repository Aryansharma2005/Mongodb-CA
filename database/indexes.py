"""
Index Creation and Database Initialization Script.
Creates required compound, single-field, and text indexes for optimal query performance.
Implements the requirements from Section 4 of the Implementation Plan.
"""
import sys
import os

_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
if sys.path and sys.path[0] == _script_dir:
    sys.path.pop(0)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from pathlib import Path

from database.connection import get_db, is_mock_db
from database.collections import (
    COLLECTION_CATEGORIES,
    COLLECTION_TRANSACTIONS,
    get_categories_collection,
    get_transactions_collection
)


def setup_indexes():
    """
    Creates compound and single-field indexes on transactions and categories.
    """
    db = get_db()
    transactions = get_transactions_collection(db)
    categories = get_categories_collection(db)

    print(f"Creating indexes on database: {db.name}...")

    # 1. Categories Index: Unique compound index on (user_id, name)
    try:
        idx_cat = categories.create_index(
            [("user_id", 1), ("name", 1)],
            unique=True,
            name="idx_user_category_name_unique"
        )
        print(f" [+] Categories index created: {idx_cat}")
    except Exception as e:
        print(f" [!] Categories index notice: {e}")

    # 2. Transactions Index 1: User dashboard - transactions sorted by date
    try:
        idx_t1 = transactions.create_index(
            [("user_id", 1), ("transaction_date", -1)],
            name="idx_user_transaction_date"
        )
        print(f" [+] Transactions index 1 created: {idx_t1}")
    except Exception as e:
        print(f" [!] Transactions index 1 notice: {e}")

    # 3. Transactions Index 2: Compound index for filtering by user, type, and date
    try:
        idx_t2 = transactions.create_index(
            [("user_id", 1), ("type", 1), ("transaction_date", -1)],
            name="idx_user_type_date"
        )
        print(f" [+] Transactions index 2 created: {idx_t2}")
    except Exception as e:
        print(f" [!] Transactions index 2 notice: {e}")

    # 4. Transactions Index 3: Category lookup per user
    try:
        idx_t3 = transactions.create_index(
            [("user_id", 1), ("category_id", 1)],
            name="idx_user_category_id"
        )
        print(f" [+] Transactions index 3 created: {idx_t3}")
    except Exception as e:
        print(f" [!] Transactions index 3 notice: {e}")

    # 5. Transactions Index 4: Text search index for note and tags
    if not is_mock_db():
        try:
            idx_t4 = transactions.create_index(
                [("note", "text"), ("tags", "text")],
                name="idx_transactions_text_search"
            )
            print(f" [+] Transactions text search index created: {idx_t4}")
        except Exception as e:
            print(f" [!] Text index notice: {e}")

    print("Index setup complete.")


def apply_schema_validators():
    """
    Applies MongoDB JSON Schema validation via collMod command (live MongoDB only).
    """
    if is_mock_db():
        print("Skipping JSON Schema collMod (in-memory mock mode).")
        return

    db = get_db()
    existing_collections = db.list_collection_names()

    # Schema for transactions
    tx_schema = {
        "$jsonSchema": {
            "bsonType": "object",
            "required": ["user_id", "category_id", "type", "amount", "transaction_date", "created_at"],
            "properties": {
                "user_id": {"bsonType": "string"},
                "category_id": {"bsonType": "objectId"},
                "type": {"enum": ["income", "expense"]},
                "amount": {"bsonType": ["decimal", "double", "int", "long"]},
                "note": {"bsonType": "string", "maxLength": 500},
                "transaction_date": {"bsonType": "date"},
                "receipt": {"bsonType": "object"},
                "tags": {"bsonType": "array"},
                "created_at": {"bsonType": "date"},
                "updated_at": {"bsonType": "date"}
            }
        }
    }

    try:
        if COLLECTION_TRANSACTIONS not in existing_collections:
            db.create_collection(COLLECTION_TRANSACTIONS, validator=tx_schema)
            print(f" [+] Collection '{COLLECTION_TRANSACTIONS}' created with JSON Schema validation.")
        else:
            db.command({
                "collMod": COLLECTION_TRANSACTIONS,
                "validator": tx_schema,
                "validationLevel": "moderate"
            })
            print(f" [+] Collection '{COLLECTION_TRANSACTIONS}' updated with JSON Schema validation.")
    except Exception as e:
        print(f" [!] Schema validator for transactions notice: {e}")


def main():
    print("=== Initializing MongoDB Indexes & Schema Validation ===")
    setup_indexes()
    apply_schema_validators()
    print("=== Database Ready ===")


if __name__ == "__main__":
    main()
