"""
WSGI config for Personal Expense Tracker project.
"""
import os
import logging
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

application = get_wsgi_application()

# Required entrypoint alias for Vercel
app = application

# Auto-initialize MongoDB authentication and schema on cold boot
try:
    from database.mongo_auth import init_mongo_auth
    init_mongo_auth()
except Exception as exc:
    logging.getLogger(__name__).warning(f"Mongo auth cold-boot notice: {exc}")
