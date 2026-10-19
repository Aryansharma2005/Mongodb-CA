"""
Database package for Personal Expense Tracker.
Contains MongoDB connection, collections, indexes, JSON schemas, seed data, and query explain utilities.
"""
from .connection import get_db, get_client, check_connection

__all__ = ["get_db", "get_client", "check_connection"]
