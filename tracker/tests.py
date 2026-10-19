"""
Unit and Integration Test Suite for Personal Expense Tracker.
Tests core validation rules, MongoDB CRUD operations, user isolation, and aggregations.
Directly satisfies Section 10 Checklist requirements.
"""
from datetime import datetime, date
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

from database.connection import init_connection
from tracker.services import (
    create_category,
    get_user_categories,
    delete_category,
    create_transaction,
    get_user_transactions,
    get_transaction_by_id,
    update_transaction,
    delete_transaction,
    get_monthly_totals,
)
from tracker.validators import (
    validate_positive_amount,
    validate_transaction_type,
    validate_object_id,
)


class ExpenseTrackerTestCase(TestCase):
    def setUp(self):
        # Force in-memory mongomock database during test execution
        init_connection(force_mock=True)

        # Create two distinct users for isolation testing
        self.user_a = User.objects.create_user(username="alice", password="password123")
        self.user_b = User.objects.create_user(username="bob", password="password123")

        self.uid_a = str(self.user_a.id)
        self.uid_b = str(self.user_b.id)

        # Create categories for User A
        self.cat_a_id = create_category(self.uid_a, "Groceries", "expense", budget_monthly="400.00")
        self.cat_salary_id = create_category(self.uid_a, "Salary", "income", budget_monthly="0.00")

    def test_amount_validation(self):
        """Test that non-positive, zero, and malformed amounts are rejected."""
        # Valid amount
        amt = validate_positive_amount("150.50")
        self.assertEqual(amt, Decimal("150.50"))

        # Zero amount rejected
        with self.assertRaises(ValidationError):
            validate_positive_amount("0")

        # Negative amount rejected
        with self.assertRaises(ValidationError):
            validate_positive_amount("-45.00")

        # Non-numeric rejected
        with self.assertRaises(ValidationError):
            validate_positive_amount("not-a-number")

    def test_type_validation(self):
        """Test transaction type validation."""
        self.assertEqual(validate_transaction_type("income"), "income")
        self.assertEqual(validate_transaction_type("expense"), "expense")

        with self.assertRaises(ValidationError):
            validate_transaction_type("transfer")

        with self.assertRaises(ValidationError):
            validate_transaction_type("")

    def test_invalid_object_id(self):
        """Test that invalid MongoDB ObjectIds raise ValidationError."""
        with self.assertRaises(ValidationError):
            validate_object_id("invalid-id-12345")

    def test_user_data_isolation(self):
        """Test that User B cannot view, edit, or delete User A's transactions."""
        # User A creates a transaction
        tx_id = create_transaction(self.uid_a, {
            "type": "expense",
            "category_id": self.cat_a_id,
            "amount": "45.00",
            "note": "Secret Expense",
            "transaction_date": date.today()
        })

        # User B cannot view User A's transaction
        with self.assertRaises(ValidationError):
            get_transaction_by_id(self.uid_b, tx_id)

        # User B's transaction list does not contain User A's transaction
        b_txs = get_user_transactions(self.uid_b)["transactions"]
        self.assertEqual(len(b_txs), 0)

        # User B cannot update User A's transaction
        with self.assertRaises(ValidationError):
            update_transaction(self.uid_b, tx_id, {
                "type": "expense",
                "category_id": self.cat_a_id,
                "amount": "99.00",
                "transaction_date": date.today()
            })

        # User B cannot delete User A's transaction
        with self.assertRaises(ValidationError):
            delete_transaction(self.uid_b, tx_id)

    def test_category_referential_integrity(self):
        """Test that a category cannot be deleted while referenced by active transactions."""
        # Create transaction referencing category
        create_transaction(self.uid_a, {
            "type": "expense",
            "category_id": self.cat_a_id,
            "amount": "75.00",
            "note": "Supermarket",
            "transaction_date": date.today()
        })

        # Attempting to delete category should fail
        with self.assertRaises(ValidationError):
            delete_category(self.uid_a, self.cat_a_id)

    def test_aggregation_pipeline_totals(self):
        """Test monthly totals aggregation pipeline calculation."""
        today = date.today()
        # Add income
        create_transaction(self.uid_a, {
            "type": "income",
            "category_id": self.cat_salary_id,
            "amount": "2000.00",
            "note": "Salary",
            "transaction_date": today
        })
        # Add expense
        create_transaction(self.uid_a, {
            "type": "expense",
            "category_id": self.cat_a_id,
            "amount": "500.00",
            "note": "Food",
            "transaction_date": today
        })

        totals = get_monthly_totals(self.uid_a, today.year, today.month)
        self.assertEqual(totals["income_total"], Decimal("2000.00"))
        self.assertEqual(totals["expense_total"], Decimal("500.00"))
        self.assertEqual(totals["balance"], Decimal("1500.00"))
        self.assertEqual(totals["savings_rate"], Decimal("75.0"))
