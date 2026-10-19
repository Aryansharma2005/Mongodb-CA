"""
Service Layer for Personal Expense Tracker.
Contains all business logic, database CRUD operations, and MongoDB Aggregation Pipelines.
Follows the architecture prescribed in Section 5 & 7 of the Implementation Plan.
"""
import csv
import io
from datetime import datetime, date, timedelta
from decimal import Decimal
from bson import ObjectId
from bson.decimal128 import Decimal128
from django.core.exceptions import ValidationError

from database.connection import is_mock_db
from database.collections import get_categories_collection, get_transactions_collection
from tracker.validators import (
    validate_positive_amount,
    validate_transaction_type,
    validate_category_kind,
    validate_note_length,
    validate_object_id,
    parse_transaction_date,
)


def _to_decimal(val) -> Decimal:
    """Helper to safely convert BSON Decimal128 or other types to Python Decimal."""
    if val is None:
        return Decimal("0.00")
    if isinstance(val, Decimal128):
        return val.to_decimal()
    try:
        return Decimal(str(val))
    except Exception:
        return Decimal("0.00")


# ============================================================================
# CATEGORY SERVICES
# ============================================================================

def get_user_categories(user_id: str, kind: str = None) -> list:
    """
    Retrieves all categories for the specified user, optionally filtered by kind.
    """
    col = get_categories_collection()
    query = {"user_id": str(user_id)}
    if kind and kind != "all":
        query["kind"] = {"$in": [kind, "both"]}

    cursor = col.find(query).sort("name", 1)
    categories = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc["budget_monthly_decimal"] = _to_decimal(doc.get("budget_monthly", 0))
        categories.append(doc)
    return categories


def get_category_by_id(user_id: str, category_id) -> dict:
    """
    Fetches a single category ensuring it belongs to the logged-in user.
    """
    col = get_categories_collection()
    cat_oid = validate_object_id(category_id)
    doc = col.find_one({"_id": cat_oid, "user_id": str(user_id)})
    if not doc:
        raise ValidationError("Category not found or access denied.")
    doc["id"] = str(doc["_id"])
    doc["budget_monthly_decimal"] = _to_decimal(doc.get("budget_monthly", 0))
    return doc


def create_category(user_id: str, name: str, kind: str, budget_monthly=None) -> str:
    """
    Creates a new category for the user, checking for duplicate names.
    """
    col = get_categories_collection()
    name_clean = name.strip()
    kind_clean = validate_category_kind(kind)

    # Check for duplicate category name for this user
    existing = col.find_one({"user_id": str(user_id), "name": {"$regex": f"^{name_clean}$", "$options": "i"}})
    if existing:
        raise ValidationError(f"A category named '{name_clean}' already exists.")

    budget_dec = Decimal("0.00")
    if budget_monthly:
        try:
            budget_dec = Decimal(str(budget_monthly))
        except Exception:
            budget_dec = Decimal("0.00")

    doc = {
        "user_id": str(user_id),
        "name": name_clean,
        "kind": kind_clean,
        "budget_monthly": Decimal128(budget_dec),
        "created_at": datetime.now()
    }
    res = col.insert_one(doc)
    return str(res.inserted_id)


def update_category(user_id: str, category_id, name: str, kind: str, budget_monthly=None):
    """
    Updates an existing category belonging to the user.
    """
    col = get_categories_collection()
    cat_oid = validate_object_id(category_id)
    name_clean = name.strip()
    kind_clean = validate_category_kind(kind)

    # Check name duplicate against OTHER categories of this user
    dup = col.find_one({
        "user_id": str(user_id),
        "_id": {"$ne": cat_oid},
        "name": {"$regex": f"^{name_clean}$", "$options": "i"}
    })
    if dup:
        raise ValidationError(f"Another category named '{name_clean}' already exists.")

    update_fields = {
        "name": name_clean,
        "kind": kind_clean,
        "updated_at": datetime.now()
    }
    if budget_monthly is not None:
        try:
            update_fields["budget_monthly"] = Decimal128(Decimal(str(budget_monthly)))
        except Exception:
            pass

    res = col.update_one({"_id": cat_oid, "user_id": str(user_id)}, {"$set": update_fields})
    if res.matched_count == 0:
        raise ValidationError("Category not found or access denied.")


def delete_category(user_id: str, category_id) -> bool:
    """
    Deletes a category after verifying it is not referenced by any existing transactions.
    """
    cat_oid = validate_object_id(category_id)
    tx_col = get_transactions_collection()
    
    # Check category usage before deletion
    usage_count = tx_col.count_documents({"user_id": str(user_id), "category_id": cat_oid})
    if usage_count > 0:
        raise ValidationError(
            f"Cannot delete category: it is used by {usage_count} transaction(s). "
            f"Please reassign or delete those transactions first."
        )

    col = get_categories_collection()
    res = col.delete_one({"_id": cat_oid, "user_id": str(user_id)})
    if res.deleted_count == 0:
        raise ValidationError("Category not found or access denied.")
    return True


def init_default_categories(user_id: str):
    """
    Initializes default categories for a new user if none exist.
    """
    col = get_categories_collection()
    count = col.count_documents({"user_id": str(user_id)})
    if count > 0:
        return

    defaults = [
        ("Food & Dining", "expense", "500.00"),
        ("Travel & Commute", "expense", "200.00"),
        ("Fees & Education", "expense", "1000.00"),
        ("Salary", "income", "0.00"),
        ("Shopping", "expense", "300.00"),
        ("Bills & Utilities", "expense", "250.00"),
        ("Healthcare", "expense", "150.00"),
        ("Freelance", "income", "0.00"),
    ]
    now = datetime.now()
    docs = [
        {
            "user_id": str(user_id),
            "name": name,
            "kind": kind,
            "budget_monthly": Decimal128(Decimal(budget)),
            "created_at": now
        }
        for name, kind, budget in defaults
    ]
    col.insert_many(docs)


# ============================================================================
# TRANSACTION SERVICES
# ============================================================================

def get_user_transactions(user_id: str, filters: dict = None, page: int = 1, page_size: int = 10) -> dict:
    """
    Retrieves paginated transactions for the user with filters and category metadata.
    """
    col = get_transactions_collection()
    query = {"user_id": str(user_id)}
    filters = filters or {}

    # Filter: Type (income/expense)
    tx_type = filters.get("type")
    if tx_type and tx_type in ("income", "expense"):
        query["type"] = tx_type

    # Filter: Category
    cat_id_raw = filters.get("category_id")
    if cat_id_raw:
        try:
            query["category_id"] = validate_object_id(cat_id_raw)
        except ValidationError:
            pass

    # Filter: Date range
    start_date = filters.get("start_date")
    end_date = filters.get("end_date")
    date_query = {}
    if start_date:
        s_dt = parse_transaction_date(start_date)
        date_query["$gte"] = s_dt
    if end_date:
        e_dt = parse_transaction_date(end_date)
        # End of day
        date_query["$lte"] = datetime.combine(e_dt.date(), datetime.max.time())
    if date_query:
        query["transaction_date"] = date_query

    # Filter: Keyword search in note or tags
    keyword = filters.get("keyword")
    if keyword and keyword.strip():
        kw_clean = keyword.strip()
        query["$or"] = [
            {"note": {"$regex": kw_clean, "$options": "i"}},
            {"tags": {"$in": [kw_clean.lower()]}}
        ]

    total_count = col.count_documents(query)
    total_pages = max(1, (total_count + page_size - 1) // page_size)
    page = max(1, min(page, total_pages))
    skip = (page - 1) * page_size

    # Sort options
    sort_by = filters.get("sort_by", "date_desc")
    sort_spec = [("transaction_date", -1)]
    if sort_by == "date_asc":
        sort_spec = [("transaction_date", 1)]
    elif sort_by == "amount_desc":
        sort_spec = [("amount", -1)]
    elif sort_by == "amount_asc":
        sort_spec = [("amount", 1)]

    cursor = col.find(query).sort(sort_spec).skip(skip).limit(page_size)

    # Pre-fetch user's categories for quick in-memory mapping
    categories_dict = {str(c["_id"]): c["name"] for c in get_user_categories(user_id)}

    transactions = []
    for doc in cursor:
        doc["id"] = str(doc["_id"])
        doc["amount_decimal"] = _to_decimal(doc.get("amount", 0))
        cat_id_str = str(doc.get("category_id"))
        doc["category_name"] = categories_dict.get(cat_id_str, "Uncategorized")
        doc["receipt_data"] = doc.get("receipt", {})
        doc["tags_list"] = doc.get("tags", [])
        transactions.append(doc)

    return {
        "transactions": transactions,
        "total_count": total_count,
        "page": page,
        "page_size": page_size,
        "total_pages": total_pages,
        "has_prev": page > 1,
        "has_next": page < total_pages,
        "prev_page": page - 1,
        "next_page": page + 1,
    }


def get_transaction_by_id(user_id: str, transaction_id) -> dict:
    """
    Fetches a single transaction document scoped to the user.
    """
    col = get_transactions_collection()
    tx_oid = validate_object_id(transaction_id)
    doc = col.find_one({"_id": tx_oid, "user_id": str(user_id)})
    if not doc:
        raise ValidationError("Transaction not found or access denied.")
    doc["id"] = str(doc["_id"])
    doc["amount_decimal"] = _to_decimal(doc.get("amount", 0))
    doc["category_id_str"] = str(doc.get("category_id"))
    doc["receipt_data"] = doc.get("receipt", {})
    doc["tags_list"] = doc.get("tags", [])
    return doc


def create_transaction(user_id: str, data: dict) -> str:
    """
    Creates an income or expense transaction with validation and BSON types.
    """
    amount_dec = validate_positive_amount(data.get("amount"))
    tx_type = validate_transaction_type(data.get("type"))
    note_clean = validate_note_length(data.get("note", ""))
    tx_date = parse_transaction_date(data.get("transaction_date"))

    # Validate that category exists and belongs to this user
    cat_oid = validate_object_id(data.get("category_id"))
    cat_col = get_categories_collection()
    category = cat_col.find_one({"_id": cat_oid, "user_id": str(user_id)})
    if not category:
        raise ValidationError("Selected category does not exist or does not belong to you.")

    # Optional embedded receipt and tags
    receipt = {}
    if data.get("merchant") or data.get("receipt_no") or data.get("payment_method"):
        receipt = {
            "merchant": str(data.get("merchant", "")).strip(),
            "receipt_no": str(data.get("receipt_no", "")).strip(),
            "payment_method": str(data.get("payment_method", "Other")).strip()
        }

    tags = []
    if data.get("tags"):
        raw_tags = data.get("tags")
        if isinstance(raw_tags, str):
            tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
        elif isinstance(raw_tags, list):
            tags = [str(t).strip().lower() for t in raw_tags if str(t).strip()]

    now = datetime.now()
    doc = {
        "user_id": str(user_id),
        "category_id": cat_oid,
        "type": tx_type,
        "amount": Decimal128(amount_dec),
        "note": note_clean,
        "transaction_date": tx_date,
        "receipt": receipt,
        "tags": tags,
        "created_at": now,
        "updated_at": now
    }

    col = get_transactions_collection()
    res = col.insert_one(doc)
    return str(res.inserted_id)


def update_transaction(user_id: str, transaction_id, data: dict):
    """
    Updates an existing transaction scoped to the user.
    """
    tx_oid = validate_object_id(transaction_id)
    amount_dec = validate_positive_amount(data.get("amount"))
    tx_type = validate_transaction_type(data.get("type"))
    note_clean = validate_note_length(data.get("note", ""))
    tx_date = parse_transaction_date(data.get("transaction_date"))

    cat_oid = validate_object_id(data.get("category_id"))
    cat_col = get_categories_collection()
    category = cat_col.find_one({"_id": cat_oid, "user_id": str(user_id)})
    if not category:
        raise ValidationError("Selected category does not exist or does not belong to you.")

    receipt = {}
    if data.get("merchant") or data.get("receipt_no") or data.get("payment_method"):
        receipt = {
            "merchant": str(data.get("merchant", "")).strip(),
            "receipt_no": str(data.get("receipt_no", "")).strip(),
            "payment_method": str(data.get("payment_method", "Other")).strip()
        }

    tags = []
    if data.get("tags"):
        raw_tags = data.get("tags")
        if isinstance(raw_tags, str):
            tags = [t.strip().lower() for t in raw_tags.split(",") if t.strip()]
        elif isinstance(raw_tags, list):
            tags = [str(t).strip().lower() for t in raw_tags if str(t).strip()]

    update_fields = {
        "category_id": cat_oid,
        "type": tx_type,
        "amount": Decimal128(amount_dec),
        "note": note_clean,
        "transaction_date": tx_date,
        "receipt": receipt,
        "tags": tags,
        "updated_at": datetime.now()
    }

    col = get_transactions_collection()
    res = col.update_one({"_id": tx_oid, "user_id": str(user_id)}, {"$set": update_fields})
    if res.matched_count == 0:
        raise ValidationError("Transaction not found or access denied.")


def delete_transaction(user_id: str, transaction_id):
    """
    Deletes a transaction after verifying user ownership.
    """
    col = get_transactions_collection()
    tx_oid = validate_object_id(transaction_id)
    res = col.delete_one({"_id": tx_oid, "user_id": str(user_id)})
    if res.deleted_count == 0:
        raise ValidationError("Transaction not found or access denied.")
    return True


# ============================================================================
# AGGREGATION PIPELINE SERVICES (Section 5 of Implementation Plan)
# ============================================================================

def get_monthly_totals(user_id: str, year: int = None, month: int = None) -> dict:
    """
    MongoDB Aggregation Pipeline 1:
    Aggregates income vs. expense totals and transaction counts for a given month.
    """
    col = get_transactions_collection()
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    # Calculate month boundary
    start_dt = datetime(year, month, 1, 0, 0, 0)
    if month == 12:
        end_dt = datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        end_dt = datetime(year, month + 1, 1, 0, 0, 0)

    # Match stage
    match_stage = {
        "$match": {
            "user_id": str(user_id),
            "transaction_date": {
                "$gte": start_dt,
                "$lt": end_dt
            }
        }
    }

    # Group stage
    group_stage = {
        "$group": {
            "_id": "$type",
            "totalAmount": {"$sum": "$amount"},
            "transactionCount": {"$sum": 1}
        }
    }

    pipeline = [match_stage, group_stage]
    if not is_mock_db():
        pipeline.append({"$sort": {"totalAmount": -1}})
    results = list(col.aggregate(pipeline))
    results.sort(key=lambda item: _to_decimal(item.get("totalAmount")), reverse=True)

    income_total = Decimal("0.00")
    expense_total = Decimal("0.00")
    income_count = 0
    expense_count = 0

    for item in results:
        t_type = item.get("_id")
        t_amount = _to_decimal(item.get("totalAmount"))
        t_count = item.get("transactionCount", 0)

        if t_type == "income":
            income_total = t_amount
            income_count = t_count
        elif t_type == "expense":
            expense_total = t_amount
            expense_count = t_count

    balance = income_total - expense_total
    savings_rate = Decimal("0.0")
    if income_total > 0:
        savings_rate = round((balance / income_total) * Decimal("100.0"), 1)

    return {
        "year": year,
        "month": month,
        "month_name": start_dt.strftime("%B %Y"),
        "income_total": income_total,
        "expense_total": expense_total,
        "income_count": income_count,
        "expense_count": expense_count,
        "total_count": income_count + expense_count,
        "balance": balance,
        "savings_rate": savings_rate,
        "is_positive": balance >= 0
    }


def get_category_expense_breakdown(user_id: str, year: int = None, month: int = None) -> list:
    """
    MongoDB Aggregation Pipeline 2:
    Groups expenses by category using $match, $group, $lookup, and $sort.
    """
    col = get_transactions_collection()
    now = datetime.now()
    year = year or now.year
    month = month or now.month

    start_dt = datetime(year, month, 1, 0, 0, 0)
    if month == 12:
        end_dt = datetime(year + 1, 1, 1, 0, 0, 0)
    else:
        end_dt = datetime(year, month + 1, 1, 0, 0, 0)

    # 1. $match stage
    match_stage = {
        "$match": {
            "user_id": str(user_id),
            "type": "expense",
            "transaction_date": {
                "$gte": start_dt,
                "$lt": end_dt
            }
        }
    }

    # 2. $group stage
    group_stage = {
        "$group": {
            "_id": "$category_id",
            "totalSpent": {"$sum": "$amount"},
            "count": {"$sum": 1}
        }
    }

    # 3. $lookup stage with categories collection
    lookup_stage = {
        "$lookup": {
            "from": "categories",
            "localField": "_id",
            "foreignField": "_id",
            "as": "category_info"
        }
    }

    pipeline = [match_stage, group_stage, lookup_stage]
    if not is_mock_db():
        pipeline.append({"$sort": {"totalSpent": -1}})
    results = list(col.aggregate(pipeline))
    results.sort(key=lambda r: _to_decimal(r.get("totalSpent")), reverse=True)

    # Calculate overall total for percentage
    total_spent = sum([_to_decimal(r.get("totalSpent")) for r in results], Decimal("0.00"))

    breakdown = []
    palette = [
        "#4f46e5", "#06b6d4", "#10b981", "#f59e0b",
        "#ef4444", "#8b5cf6", "#ec4899", "#14b8a6", "#64748b"
    ]

    for idx, item in enumerate(results):
        spent = _to_decimal(item.get("totalSpent"))
        pct = round((spent / total_spent * Decimal("100.0")), 1) if total_spent > 0 else Decimal("0.0")

        cat_docs = item.get("category_info", [])
        cat_name = cat_docs[0].get("name", "Unknown Category") if cat_docs else "Unknown Category"
        budget_dec = _to_decimal(cat_docs[0].get("budget_monthly", 0)) if cat_docs else Decimal("0.00")

        breakdown.append({
            "category_id": str(item.get("_id")),
            "category_name": cat_name,
            "total_spent": spent,
            "count": item.get("count", 0),
            "percentage": float(pct),
            "budget": budget_dec,
            "is_over_budget": (budget_dec > 0 and spent > budget_dec),
            "color": palette[idx % len(palette)]
        })

    return breakdown


def get_monthly_trend(user_id: str, num_months: int = 6) -> dict:
    """
    MongoDB Aggregation Pipeline 3:
    Builds month-by-month income vs. expense trend for Chart.js visualization.
    """
    col = get_transactions_collection()
    now = datetime.now()
    labels = []
    income_data = []
    expense_data = []

    # Iterate over the past num_months in chronological order
    for offset in range(num_months - 1, -1, -1):
        target_dt = now - timedelta(days=offset * 30)
        y = target_dt.year
        m = target_dt.month
        month_label = datetime(y, m, 1).strftime("%b %Y")
        labels.append(month_label)

        totals = get_monthly_totals(user_id, y, m)
        income_data.append(float(totals["income_total"]))
        expense_data.append(float(totals["expense_total"]))

    return {
        "labels": labels,
        "income": income_data,
        "expense": expense_data
    }


def get_spending_insights(user_id: str) -> dict:
    """
    Smart Spending Pattern Insights & Analytics (Unit V AI/Analytics enhancement).
    Identifies top spending categories, budget overruns, month-over-month variances,
    and actionable recommendations.
    """
    now = datetime.now()
    curr_totals = get_monthly_totals(user_id, now.year, now.month)

    # Previous month totals
    prev_month_date = datetime(now.year, now.month, 1) - timedelta(days=1)
    prev_totals = get_monthly_totals(user_id, prev_month_date.year, prev_month_date.month)

    breakdown = get_category_expense_breakdown(user_id, now.year, now.month)

    insights = []
    alerts = []

    # 1. Budget overrun alerts
    for cat in breakdown:
        if cat["is_over_budget"]:
            diff = cat["total_spent"] - cat["budget"]
            alerts.append({
                "type": "danger",
                "title": f"Budget Exceeded in {cat['category_name']}",
                "message": f"Spent ${cat['total_spent']:.2f} against a budget of ${cat['budget']:.2f} (Over by ${diff:.2f})."
            })

    # 2. Top Expense Driver
    if breakdown:
        top_cat = breakdown[0]
        insights.append({
            "title": f"Top Expense Driver: {top_cat['category_name']}",
            "text": f"Accounts for {top_cat['percentage']:.1f}% of your monthly expenses (${top_cat['total_spent']:.2f})."
        })

    # 3. Month-over-Month Comparison
    if prev_totals["expense_total"] > 0:
        pct_change = ((curr_totals["expense_total"] - prev_totals["expense_total"]) / prev_totals["expense_total"]) * Decimal("100.0")
        if pct_change > 15:
            alerts.append({
                "type": "warning",
                "title": "Expense Spike Alert",
                "message": f"Your spending is up {abs(pct_change):.1f}% compared to last month (${curr_totals['expense_total']:.2f} vs ${prev_totals['expense_total']:.2f})."
            })
        elif pct_change < -10:
            insights.append({
                "title": "Spending Under Control",
                "text": f"Great job! You have spent {abs(pct_change):.1f}% less than last month."
            })

    # 4. Savings Health
    if curr_totals["savings_rate"] >= 20:
        insights.append({
            "title": "Healthy Savings Rate",
            "text": f"You are saving {curr_totals['savings_rate']:.1f}% of your income this month, exceeding the 20% rule of thumb."
        })
    elif curr_totals["savings_rate"] < 0:
        alerts.append({
            "type": "danger",
            "title": "Deficit Spending Warning",
            "message": "Expenses currently exceed income for this month. Consider reviewing non-essential categories."
        })

    return {
        "current_totals": curr_totals,
        "previous_totals": prev_totals,
        "breakdown": breakdown,
        "insights": insights,
        "alerts": alerts
    }


def export_transactions_csv(user_id: str, filters: dict = None) -> str:
    """
    Exports filtered transactions to CSV format string.
    """
    # Fetch all matching transactions (up to 5,000)
    data = get_user_transactions(user_id, filters=filters, page=1, page_size=5000)
    tx_list = data["transactions"]

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow([
        "Transaction ID",
        "Date",
        "Type",
        "Category",
        "Amount",
        "Note",
        "Merchant",
        "Receipt No",
        "Payment Method",
        "Tags"
    ])

    for tx in tx_list:
        receipt = tx.get("receipt_data", {})
        writer.writerow([
            tx["id"],
            tx.get("transaction_date").strftime("%Y-%m-%d") if isinstance(tx.get("transaction_date"), (datetime, date)) else str(tx.get("transaction_date")),
            tx.get("type", "").capitalize(),
            tx.get("category_name", ""),
            f"{tx.get('amount_decimal', 0):.2f}",
            tx.get("note", ""),
            receipt.get("merchant", ""),
            receipt.get("receipt_no", ""),
            receipt.get("payment_method", ""),
            ", ".join(tx.get("tags_list", []))
        ])

    return output.getvalue()
