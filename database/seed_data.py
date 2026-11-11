import sys
import os

# Ensure project root is first on sys.path and remove 'database/' directory
# so Python's standard library 'collections' is never shadowed.
_script_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(_script_dir)
if sys.path and sys.path[0] == _script_dir:
    sys.path.pop(0)
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

from pathlib import Path
from datetime import datetime, timedelta
from decimal import Decimal
from bson.decimal128 import Decimal128
from bson import ObjectId

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")
import django
django.setup()

from django.contrib.auth.models import User
from database.connection import get_db
from database.collections import get_categories_collection, get_transactions_collection
from database.indexes import setup_indexes


def seed_database(username="demo", password="password123"):
    print("=" * 60)
    print(f"Seeding Database for user: '{username}'")
    print("=" * 60)

    # 1. Ensure Django user exists
    user, created = User.objects.get_or_create(username=username, defaults={"email": f"{username}@example.com"})
    if created:
        user.set_password(password)
        user.save()
        print(f" [+] Created Django auth user: '{username}' (password: '{password}')")
    else:
        print(f" [i] Found existing Django auth user: '{username}'")

    db = get_db()
    users_col = db["users"]
    users_col.update_one(
        {"username": username},
        {"$set": {
            "username": username,
            "email": f"{username}@example.com",
            "password": user.password,
            "django_id": int(user.id),
            "updated_at": datetime.utcnow()
        },
        "$setOnInsert": {
            "created_at": datetime.utcnow()
        }},
        upsert=True
    )
    print(f" [+] Ensured MongoDB 'users' document for '{username}'")

    user_id = str(user.id)
    db = get_db()
    categories_col = get_categories_collection(db)
    transactions_col = get_transactions_collection(db)

    # Setup indexes
    setup_indexes()

    # 2. Seed Default Categories
    category_templates = [
        {"name": "Food & Dining", "kind": "expense", "budget": "500.00"},
        {"name": "Travel & Commute", "kind": "expense", "budget": "200.00"},
        {"name": "Education & Fees", "kind": "expense", "budget": "1500.00"},
        {"name": "Bills & Utilities", "kind": "expense", "budget": "250.00"},
        {"name": "Shopping", "kind": "expense", "budget": "300.00"},
        {"name": "Healthcare", "kind": "expense", "budget": "150.00"},
        {"name": "Entertainment", "kind": "expense", "budget": "100.00"},
        {"name": "Salary", "kind": "income", "budget": "0.00"},
        {"name": "Freelance", "kind": "income", "budget": "0.00"},
        {"name": "Investment Return", "kind": "income", "budget": "0.00"},
    ]

    cat_map = {}
    now = datetime.now()

    for item in category_templates:
        existing = categories_col.find_one({"user_id": user_id, "name": item["name"]})
        if not existing:
            doc = {
                "user_id": user_id,
                "name": item["name"],
                "kind": item["kind"],
                "budget_monthly": Decimal128(Decimal(item["budget"])),
                "created_at": now
            }
            res = categories_col.insert_one(doc)
            cat_map[item["name"]] = res.inserted_id
            print(f" [+] Inserted Category: {item['name']} ({item['kind']})")
        else:
            cat_map[item["name"]] = existing["_id"]
            print(f" [i] Existing Category: {item['name']}")

    # 3. Seed Realistic Transactions across current and past months
    today = now.date()
    # List of realistic transactions: (days_ago, cat_name, type, amount, note, tags, receipt)
    tx_samples = [
        # Incomes
        (1, "Salary", "income", "4500.00", "Monthly Company Salary - Direct Deposit", ["payroll", "primary"], {"merchant": "TechCorp Inc", "payment_method": "Direct Deposit"}),
        (8, "Freelance", "income", "750.00", "Web Design Consultation Project", ["freelance", "client"], {"merchant": "DesignLab", "payment_method": "Wire Transfer"}),
        (20, "Investment Return", "income", "125.50", "Quarterly Mutual Fund Dividend", ["investment"], {"merchant": "Vanguard", "payment_method": "ACH"}),
        (32, "Salary", "income", "4500.00", "Previous Month Company Salary", ["payroll", "primary"], {"merchant": "TechCorp Inc", "payment_method": "Direct Deposit"}),
        (35, "Freelance", "income", "400.00", "Mobile UI Fixes", ["freelance"], {"merchant": "StartUp LLC", "payment_method": "PayPal"}),
        
        # Expenses - Current Month
        (0, "Food & Dining", "expense", "24.50", "Lunch at Healthy Cafe", ["lunch", "food"], {"merchant": "Green Bowl", "payment_method": "Credit Card"}),
        (2, "Shopping", "expense", "89.99", "Noise-cancelling bluetooth headphones", ["electronics"], {"merchant": "Amazon", "receipt_no": "REC-98213", "payment_method": "Credit Card"}),
        (3, "Travel & Commute", "expense", "45.00", "Monthly Subway Metro Pass recharge", ["transit"], {"merchant": "Metro Transit", "payment_method": "Debit Card"}),
        (4, "Food & Dining", "expense", "112.30", "Weekly Grocery supplies", ["groceries"], {"merchant": "SuperMart", "payment_method": "Apple Pay"}),
        (6, "Bills & Utilities", "expense", "85.00", "High-speed Fiber Internet bill", ["utilities", "home"], {"merchant": "FiberNet ISP", "receipt_no": "BILL-4412", "payment_method": "Autopay"}),
        (7, "Healthcare", "expense", "35.00", "Pharmacy vitamins and prescriptions", ["health"], {"merchant": "CVS Pharmacy", "payment_method": "Debit Card"}),
        (9, "Entertainment", "expense", "18.99", "Movie tickets and popcorn", ["cinema"], {"merchant": "AMC Theatres", "payment_method": "Credit Card"}),
        (11, "Food & Dining", "expense", "54.20", "Dinner with team colleagues", ["dining"], {"merchant": "Bistro Central", "payment_method": "Credit Card"}),
        (14, "Bills & Utilities", "expense", "120.40", "Monthly Electricity Bill", ["utilities", "home"], {"merchant": "City Power Co.", "payment_method": "Online Banking"}),
        (16, "Travel & Commute", "expense", "22.50", "Uber ride to railway station", ["rideshare"], {"merchant": "Uber", "payment_method": "Credit Card"}),
        (18, "Shopping", "expense", "64.00", "Warm casual winter sweater", ["clothing"], {"merchant": "H&M Store", "payment_method": "Debit Card"}),
        (21, "Food & Dining", "expense", "95.60", "Weekend groceries & fresh fruits", ["groceries"], {"merchant": "Organic WholeFoods", "payment_method": "Apple Pay"}),
        (25, "Education & Fees", "expense", "450.00", "DBMS Certification Exam Fee", ["education", "exam"], {"merchant": "NoSQL Academy", "receipt_no": "CERT-2026", "payment_method": "Credit Card"}),
        
        # Expenses - Previous Month (for trend and monthly comparisons)
        (33, "Food & Dining", "expense", "340.00", "Prior month groceries & food total", ["groceries"], {"merchant": "SuperMart", "payment_method": "Card"}),
        (36, "Bills & Utilities", "expense", "195.00", "Water, Gas & Electric bills", ["utilities"], {"merchant": "Public Utilities", "payment_method": "Online"}),
        (40, "Travel & Commute", "expense", "75.00", "Fuel refill at Shell station", ["fuel"], {"merchant": "Shell Oil", "payment_method": "Credit Card"}),
        (45, "Shopping", "expense", "150.00", "Office chair ergonomic cushion", ["home_office"], {"merchant": "IKEA", "payment_method": "Credit Card"}),
        (50, "Education & Fees", "expense", "800.00", "College Semester Tuition installment", ["college", "fees"], {"merchant": "University Treasury", "receipt_no": "FEE-77291", "payment_method": "Bank Transfer"}),
    ]

    inserted_count = 0
    for days_ago, cat_name, tx_type, amt_str, note, tags, receipt in tx_samples:
        t_date = datetime.combine(today - timedelta(days=days_ago), datetime.min.time())
        cat_id = cat_map.get(cat_name)
        if not cat_id:
            continue

        # Check if identical transaction already exists to keep seeding idempotent
        existing_tx = transactions_col.find_one({
            "user_id": user_id,
            "note": note,
            "type": tx_type
        })
        if not existing_tx:
            doc = {
                "user_id": user_id,
                "category_id": cat_id,
                "type": tx_type,
                "amount": Decimal128(Decimal(amt_str)),
                "note": note,
                "tags": tags,
                "receipt": receipt,
                "transaction_date": t_date,
                "created_at": now - timedelta(days=days_ago),
                "updated_at": now - timedelta(days=days_ago)
            }
            transactions_col.insert_one(doc)
            inserted_count += 1

    print(f" [+] Inserted {inserted_count} new transactions for user '{username}'.")
    print("=" * 60)
    print("Seeding finished successfully!")
    print(f"Login credentials: Username='{username}', Password='{password}'")
    print("=" * 60)


if __name__ == "__main__":
    u = sys.argv[1] if len(sys.argv) > 1 else "demo"
    p = sys.argv[2] if len(sys.argv) > 2 else "password123"
    seed_database(u, p)
