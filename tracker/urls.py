"""
URL routing for the tracker app.
"""
from django.urls import path
from tracker import views

urlpatterns = [
    path("", views.dashboard_view, name="dashboard"),
    path("transactions/", views.transaction_list_view, name="transactions"),
    path("transactions/new/", views.transaction_create_view, name="transaction_create"),
    path("transactions/<str:transaction_id>/edit/", views.transaction_update_view, name="transaction_update"),
    path("transactions/<str:transaction_id>/delete/", views.transaction_delete_view, name="transaction_delete"),
    path("categories/", views.category_list_view, name="categories"),
    path("categories/<str:category_id>/edit/", views.category_update_view, name="category_update"),
    path("categories/<str:category_id>/delete/", views.category_delete_view, name="category_delete"),
    path("reports/", views.reports_view, name="reports"),
    path("insights/", views.insights_view, name="insights"),
    path("explain/", views.explain_view, name="explain"),
    path("register/", views.register_view, name="register"),
]
