"""
Django Views for Personal Expense Tracker.
Connects UI templates to the PyMongo service layer.
Enforces Django login authentication and strict user data isolation.
"""
import json
from datetime import datetime
from decimal import Decimal
from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.core.exceptions import ValidationError

from database.connection import check_connection, is_mock_db
from tracker.forms import (
    TransactionForm,
    CategoryForm,
    TransactionFilterForm
)
from tracker.services import (
    get_user_categories,
    get_category_by_id,
    create_category,
    update_category,
    delete_category,
    init_default_categories,
    get_user_transactions,
    get_transaction_by_id,
    create_transaction,
    update_transaction,
    delete_transaction,
    get_monthly_totals,
    get_category_expense_breakdown,
    get_monthly_trend,
    get_spending_insights,
    export_transactions_csv,
)


def register_view(request):
    """
    Handles user registration.
    Automatically initializes default categories for new users.
    """
    if request.user.is_authenticated:
        return redirect("dashboard")

    if request.method == "POST":
        form = UserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            # Persist user credentials in MongoDB Atlas
            try:
                from database.mongo_auth import sync_user_to_mongo
                sync_user_to_mongo(user)
            except Exception:
                pass
            # Initialize default categories for the new user in MongoDB
            init_default_categories(str(user.id))
            login(request, user)
            messages.success(request, f"Welcome to Expense Tracker, {user.username}! Your account is ready.")
            return redirect("dashboard")
    else:
        form = UserCreationForm()

    return render(request, "registration/register.html", {"form": form})


@login_required
def dashboard_view(request):
    """
    Main user dashboard showing current-month summary cards,
    recent transactions, and monthly income/expense chart.
    """
    user_id = str(request.user.id)
    # Ensure default categories exist
    init_default_categories(user_id)

    now = datetime.now()
    totals = get_monthly_totals(user_id, now.year, now.month)
    breakdown = get_category_expense_breakdown(user_id, now.year, now.month)
    trend_data = get_monthly_trend(user_id, num_months=6)

    # Fetch 5 most recent transactions
    recent_tx_data = get_user_transactions(user_id, page=1, page_size=5)
    connection_status = check_connection()

    context = {
        "totals": totals,
        "breakdown": breakdown,
        "recent_transactions": recent_tx_data["transactions"],
        "chart_labels_json": json.dumps(trend_data["labels"]),
        "chart_income_json": json.dumps(trend_data["income"]),
        "chart_expense_json": json.dumps(trend_data["expense"]),
        "connection_status": connection_status,
        "current_month_name": totals["month_name"],
    }
    return render(request, "dashboard.html", context)


@login_required
def transaction_list_view(request):
    """
    Transaction list page with filtering, sorting, pagination, and CSV export.
    """
    user_id = str(request.user.id)
    filter_form = TransactionFilterForm(user_id, request.GET)

    filters = {}
    if filter_form.is_valid():
        for k, v in filter_form.cleaned_data.items():
            if v:
                filters[k] = v

    # CSV Export support
    if request.GET.get("export") == "csv":
        csv_data = export_transactions_csv(user_id, filters=filters)
        response = HttpResponse(csv_data, content_type="text/csv")
        filename = f"transactions_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response

    page = int(request.GET.get("page", 1))
    data = get_user_transactions(user_id, filters=filters, page=page, page_size=10)

    context = {
        "filter_form": filter_form,
        "transactions": data["transactions"],
        "total_count": data["total_count"],
        "page": data["page"],
        "total_pages": data["total_pages"],
        "has_prev": data["has_prev"],
        "has_next": data["has_next"],
        "prev_page": data["prev_page"],
        "next_page": data["next_page"],
        "query_params": request.GET.urlencode(),
    }
    return render(request, "transactions.html", context)


@login_required
def transaction_create_view(request):
    """
    Creates a new income or expense transaction.
    """
    user_id = str(request.user.id)
    if request.method == "POST":
        form = TransactionForm(user_id, request.POST)
        if form.is_valid():
            try:
                tx_id = create_transaction(user_id, form.cleaned_data)
                messages.success(request, "Transaction recorded successfully in MongoDB!")
                return redirect("transactions")
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))
            except Exception as e:
                messages.error(request, f"Error creating transaction: {str(e)}")
    else:
        form = TransactionForm(user_id)

    return render(request, "transaction_form.html", {
        "form": form,
        "title": "Add New Transaction",
        "action": "Create"
    })


@login_required
def transaction_update_view(request, transaction_id):
    """
    Updates an existing transaction document.
    """
    user_id = str(request.user.id)
    try:
        tx = get_transaction_by_id(user_id, transaction_id)
    except ValidationError:
        messages.error(request, "Transaction not found or access denied.")
        return redirect("transactions")

    if request.method == "POST":
        form = TransactionForm(user_id, request.POST)
        if form.is_valid():
            try:
                update_transaction(user_id, transaction_id, form.cleaned_data)
                messages.success(request, "Transaction updated successfully.")
                return redirect("transactions")
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))
            except Exception as e:
                messages.error(request, f"Error updating transaction: {str(e)}")
    else:
        receipt = tx.get("receipt_data", {})
        initial_data = {
            "type": tx.get("type"),
            "category_id": tx.get("category_id_str"),
            "amount": tx.get("amount_decimal"),
            "transaction_date": tx.get("transaction_date").strftime("%Y-%m-%d") if tx.get("transaction_date") else "",
            "note": tx.get("note", ""),
            "merchant": receipt.get("merchant", ""),
            "receipt_no": receipt.get("receipt_no", ""),
            "payment_method": receipt.get("payment_method", "Other"),
            "tags": ", ".join(tx.get("tags_list", [])),
        }
        form = TransactionForm(user_id, initial=initial_data)

    return render(request, "transaction_form.html", {
        "form": form,
        "title": "Edit Transaction",
        "action": "Update",
        "transaction_id": transaction_id
    })


@login_required
def transaction_delete_view(request, transaction_id):
    """
    Deletes a transaction after confirming user ownership.
    """
    user_id = str(request.user.id)
    if request.method == "POST":
        try:
            delete_transaction(user_id, transaction_id)
            messages.success(request, "Transaction deleted successfully from MongoDB.")
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))
        except Exception as e:
            messages.error(request, f"Error deleting transaction: {str(e)}")

    return redirect("transactions")


@login_required
def category_list_view(request):
    """
    Lists categories with transaction usage checks and provides an inline creation form.
    """
    user_id = str(request.user.id)
    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            try:
                create_category(
                    user_id,
                    form.cleaned_data["name"],
                    form.cleaned_data["kind"],
                    form.cleaned_data.get("budget_monthly")
                )
                messages.success(request, f"Category '{form.cleaned_data['name']}' added.")
                return redirect("categories")
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))
    else:
        form = CategoryForm()

    categories = get_user_categories(user_id)
    return render(request, "categories.html", {
        "categories": categories,
        "form": form
    })


@login_required
def category_update_view(request, category_id):
    """
    Updates category name, kind, and monthly budget.
    """
    user_id = str(request.user.id)
    try:
        cat = get_category_by_id(user_id, category_id)
    except ValidationError:
        messages.error(request, "Category not found or access denied.")
        return redirect("categories")

    if request.method == "POST":
        form = CategoryForm(request.POST)
        if form.is_valid():
            try:
                update_category(
                    user_id,
                    category_id,
                    form.cleaned_data["name"],
                    form.cleaned_data["kind"],
                    form.cleaned_data.get("budget_monthly")
                )
                messages.success(request, f"Category '{form.cleaned_data['name']}' updated.")
                return redirect("categories")
            except ValidationError as e:
                messages.error(request, str(e.message if hasattr(e, 'message') else e))
    else:
        form = CategoryForm(initial={
            "name": cat["name"],
            "kind": cat["kind"],
            "budget_monthly": cat["budget_monthly_decimal"]
        })

    return render(request, "category_form.html", {
        "form": form,
        "category": cat
    })


@login_required
def category_delete_view(request, category_id):
    """
    Deletes a category if not in use.
    """
    user_id = str(request.user.id)
    if request.method == "POST":
        try:
            delete_category(user_id, category_id)
            messages.success(request, "Category deleted successfully.")
        except ValidationError as e:
            messages.error(request, str(e.message if hasattr(e, 'message') else e))
        except Exception as e:
            messages.error(request, f"Error deleting category: {str(e)}")

    return redirect("categories")


@login_required
def reports_view(request):
    """
    Monthly totals and category-wise aggregation report using MongoDB aggregation pipelines.
    """
    user_id = str(request.user.id)
    now = datetime.now()

    year = int(request.GET.get("year", now.year))
    month = int(request.GET.get("month", now.month))

    totals = get_monthly_totals(user_id, year, month)
    breakdown = get_category_expense_breakdown(user_id, year, month)

    # Prepare chart data for category breakdown
    cat_labels = [item["category_name"] for item in breakdown]
    cat_amounts = [float(item["total_spent"]) for item in breakdown]
    cat_colors = [item["color"] for item in breakdown]

    # Year choices (current - 2 to current + 1)
    years = list(range(now.year - 2, now.year + 2))
    months = [
        (1, "January"), (2, "February"), (3, "March"), (4, "April"),
        (5, "May"), (6, "June"), (7, "July"), (8, "August"),
        (9, "September"), (10, "October"), (11, "November"), (12, "December")
    ]

    context = {
        "totals": totals,
        "breakdown": breakdown,
        "selected_year": year,
        "selected_month": month,
        "years": years,
        "months": months,
        "cat_labels_json": json.dumps(cat_labels),
        "cat_amounts_json": json.dumps(cat_amounts),
        "cat_colors_json": json.dumps(cat_colors),
    }
    return render(request, "reports.html", context)


@login_required
def insights_view(request):
    """
    Spending pattern insights & budget warning analytics.
    """
    user_id = str(request.user.id)
    data = get_spending_insights(user_id)
    return render(request, "insights.html", data)


@login_required
def explain_view(request):
    """
    Interactive MongoDB Query Optimization & Indexing Evidence page.
    Demonstrates executionStats (COLLSCAN vs IXSCAN) for the CSE494 viva/evaluation.
    """
    is_mock = is_mock_db()
    return render(request, "explain.html", {
        "is_mock": is_mock,
        "db_info": check_connection()
    })
