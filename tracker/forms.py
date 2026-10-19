"""
Django Forms for Personal Expense Tracker.
Handles form presentation and validation for transactions, categories, and filters.
"""
from django import forms
from decimal import Decimal
from datetime import date
from tracker.services import get_user_categories


class TransactionForm(forms.Form):
    TYPE_CHOICES = [
        ("expense", "Expense (Money Out)"),
        ("income", "Income (Money In)"),
    ]

    PAYMENT_CHOICES = [
        ("Credit Card", "Credit Card"),
        ("Debit Card", "Debit Card"),
        ("UPI / Online", "UPI / Online Payment"),
        ("Cash", "Cash"),
        ("Bank Transfer", "Bank Transfer"),
        ("Other", "Other"),
    ]

    type = forms.ChoiceField(
        choices=TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select", "id": "id_type"}),
        label="Transaction Type"
    )

    category_id = forms.ChoiceField(
        widget=forms.Select(attrs={"class": "form-select", "id": "id_category"}),
        label="Category"
    )

    amount = forms.DecimalField(
        max_digits=12,
        decimal_places=2,
        min_value=Decimal("0.01"),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "0.00",
            "step": "0.01",
            "min": "0.01"
        }),
        label="Amount ($)"
    )

    transaction_date = forms.DateField(
        widget=forms.DateInput(attrs={
            "class": "form-control",
            "type": "date"
        }),
        initial=date.today,
        label="Transaction Date"
    )

    note = forms.CharField(
        required=False,
        max_length=500,
        widget=forms.Textarea(attrs={
            "class": "form-control",
            "rows": 3,
            "placeholder": "Add a note or description (e.g. Groceries at Walmart, Freelance project...)"
        }),
        label="Note / Description"
    )

    # Embedded document demonstration (Receipt metadata)
    merchant = forms.CharField(
        required=False,
        max_length=150,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Amazon, Shell, Whole Foods"
        }),
        label="Merchant / Payee"
    )

    receipt_no = forms.CharField(
        required=False,
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. INV-90412"
        }),
        label="Receipt / Reference Number"
    )

    payment_method = forms.ChoiceField(
        required=False,
        choices=PAYMENT_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Payment Method"
    )

    # Array demonstration (Tags)
    tags = forms.CharField(
        required=False,
        max_length=200,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. groceries, weekend, personal (comma-separated)"
        }),
        label="Tags (Comma separated)"
    )

    def __init__(self, user_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Populate categories belonging to this user
        cats = get_user_categories(user_id)
        self.fields["category_id"].choices = [(c["id"], f"{c['name']} ({c['kind'].capitalize()})") for c in cats]


class CategoryForm(forms.Form):
    KIND_CHOICES = [
        ("expense", "Expense Category"),
        ("income", "Income Category"),
        ("both", "Both (Income & Expense)"),
    ]

    name = forms.CharField(
        max_length=100,
        widget=forms.TextInput(attrs={
            "class": "form-control",
            "placeholder": "e.g. Entertainment, Health, Utilities"
        }),
        label="Category Name"
    )

    kind = forms.ChoiceField(
        choices=KIND_CHOICES,
        widget=forms.Select(attrs={"class": "form-select"}),
        label="Category Kind"
    )

    budget_monthly = forms.DecimalField(
        required=False,
        max_digits=10,
        decimal_places=2,
        min_value=Decimal("0.00"),
        widget=forms.NumberInput(attrs={
            "class": "form-control",
            "placeholder": "0.00 (Optional monthly limit)",
            "step": "0.01"
        }),
        label="Monthly Budget Target ($)"
    )


class TransactionFilterForm(forms.Form):
    SORT_CHOICES = [
        ("date_desc", "Date (Newest First)"),
        ("date_asc", "Date (Oldest First)"),
        ("amount_desc", "Amount (Highest First)"),
        ("amount_asc", "Amount (Lowest First)"),
    ]

    TYPE_CHOICES = [
        ("", "All Types"),
        ("expense", "Expenses Only"),
        ("income", "Income Only"),
    ]

    type = forms.ChoiceField(
        required=False,
        choices=TYPE_CHOICES,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"})
    )

    category_id = forms.ChoiceField(
        required=False,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"})
    )

    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "class": "form-control form-control-sm",
            "type": "date"
        })
    )

    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "class": "form-control form-control-sm",
            "type": "date"
        })
    )

    keyword = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            "class": "form-control form-control-sm",
            "placeholder": "Search notes or tags..."
        })
    )

    sort_by = forms.ChoiceField(
        required=False,
        choices=SORT_CHOICES,
        widget=forms.Select(attrs={"class": "form-select form-select-sm"})
    )

    def __init__(self, user_id, *args, **kwargs):
        super().__init__(*args, **kwargs)
        cats = get_user_categories(user_id)
        choices = [("", "All Categories")] + [(c["id"], c["name"]) for c in cats]
        self.fields["category_id"].choices = choices
