"""
Application-Level Validators for Personal Expense Tracker.
Enforces validation rules specified in Section 5 of the Implementation Plan.
"""
from decimal import Decimal, InvalidOperation
from datetime import datetime, date
from bson import ObjectId
from bson.errors import InvalidId
from django.core.exceptions import ValidationError


def validate_positive_amount(value):
    """
    Validates that the amount is a valid positive decimal number greater than zero.
    """
    if value is None:
        raise ValidationError("Amount is required.")

    try:
        dec_val = Decimal(str(value))
    except (InvalidOperation, TypeError, ValueError):
        raise ValidationError("Amount must be a valid number.")

    if dec_val <= Decimal("0"):
        raise ValidationError("Amount must be greater than zero.")

    if dec_val.as_tuple().exponent < -2:
        raise ValidationError("Amount cannot have more than 2 decimal places.")

    return dec_val


def validate_transaction_type(value):
    """
    Validates that type is strictly either 'income' or 'expense'.
    """
    if not value or value not in ("income", "expense"):
        raise ValidationError("Type must be either 'income' or 'expense'.")
    return value


def validate_category_kind(value):
    """
    Validates category kind: 'income', 'expense', or 'both'.
    """
    if not value or value not in ("income", "expense", "both"):
        raise ValidationError("Category kind must be 'income', 'expense', or 'both'.")
    return value


def validate_note_length(value, max_length=500):
    """
    Validates optional note text length.
    """
    if value and len(value) > max_length:
        raise ValidationError(f"Note cannot exceed {max_length} characters.")
    return value or ""


def validate_object_id(oid_string):
    """
    Validates string and converts it to a bson.ObjectId, or raises ValidationError.
    """
    if not oid_string:
        raise ValidationError("ID is required.")
    try:
        return ObjectId(str(oid_string))
    except (InvalidId, TypeError, ValueError):
        raise ValidationError("Invalid MongoDB ObjectId format.")


def parse_transaction_date(date_val):
    """
    Validates and standardizes transaction date to datetime object.
    """
    if not date_val:
        return datetime.combine(date.today(), datetime.min.time())

    if isinstance(date_val, datetime):
        return date_val
    if isinstance(date_val, date):
        return datetime.combine(date_val, datetime.min.time())

    # Try common string formats
    formats = ["%Y-%m-%d", "%Y-%m-%dT%H:%M", "%d-%m-%Y", "%m/%d/%Y"]
    for fmt in formats:
        try:
            return datetime.strptime(str(date_val), fmt)
        except ValueError:
            pass

    raise ValidationError("Invalid date format. Expected YYYY-MM-DD.")
