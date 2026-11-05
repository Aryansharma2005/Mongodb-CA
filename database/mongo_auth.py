"""
MongoDB Authentication and User Synchronization for Serverless Deployment.
Enables Django to run purely on MongoDB Atlas without requiring external SQL databases.
"""
import logging
from datetime import datetime
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth.models import User
from django.contrib.auth.hashers import check_password, make_password
from database.collections import get_users_collection

logger = logging.getLogger(__name__)


class MongoAuthBackend(BaseBackend):
    """
    Authenticates users against MongoDB Atlas 'users' collection.
    If the user exists in MongoDB, ensures a matching Django User model exists
    in the local SQLite cache for this session.
    """

    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None

        try:
            users_col = get_users_collection()
            user_doc = users_col.find_one({"username": username})
            if not user_doc:
                return None

            stored_password = user_doc.get("password", "")
            if not check_password(password, stored_password):
                return None

            # User authenticated successfully in MongoDB!
            django_id = user_doc.get("django_id")
            user = None
            if django_id:
                user = User.objects.filter(id=django_id).first()
            if not user:
                user = User.objects.filter(username=username).first()
            if not user:
                user = User.objects.create(
                    id=django_id,
                    username=user_doc["username"],
                    email=user_doc.get("email", ""),
                    password=stored_password,
                    is_active=True
                )
            else:
                if user.password != stored_password:
                    user.password = stored_password
                    user.save()

            return user
        except Exception as exc:
            logger.error(f"MongoAuthBackend authentication error: {exc}")
            return None

    def get_user(self, user_id):
        try:
            user = User.objects.filter(pk=user_id).first()
            if user:
                return user

            # On cold boot in serverless, retrieve user from MongoDB
            users_col = get_users_collection()
            user_doc = None
            try:
                user_doc = users_col.find_one({"django_id": int(user_id)})
            except (ValueError, TypeError):
                pass

            if not user_doc:
                user_doc = users_col.find_one({"username": str(user_id)})

            if user_doc:
                did = user_doc.get("django_id")
                if not did and str(user_id).isdigit():
                    did = int(user_id)
                user = User.objects.create(
                    id=did,
                    username=user_doc["username"],
                    email=user_doc.get("email", ""),
                    password=user_doc.get("password", ""),
                    is_active=True
                )
                return user

            return None
        except Exception as exc:
            logger.error(f"MongoAuthBackend get_user error: {exc}")
            return None


def sync_user_to_mongo(user):
    """
    Persists a newly registered or updated Django user into MongoDB Atlas.
    """
    try:
        users_col = get_users_collection()
        users_col.update_one(
            {"username": user.username},
            {
                "$set": {
                    "username": user.username,
                    "email": user.email,
                    "password": user.password,
                    "django_id": user.id,
                    "updated_at": datetime.utcnow()
                },
                "$setOnInsert": {
                    "created_at": datetime.utcnow()
                }
            },
            upsert=True
        )
    except Exception as exc:
        logger.error(f"Failed to sync user '{user.username}' to MongoDB: {exc}")


def init_mongo_auth():
    """
    Runs during application boot.
    1. Ensures SQLite schema migrations are applied in /tmp.
    2. Syncs existing users from MongoDB Atlas into SQLite.
    3. Ensures the default 'demo' user exists in both MongoDB and SQLite.
    """
    try:
        from django.core.management import call_command
        call_command("migrate", interactive=False, verbosity=0)
    except Exception as e:
        logger.warning(f"Auto-migrate notice: {e}")

    try:
        users_col = get_users_collection()

        # 1. Ensure demo user exists in MongoDB
        demo_doc = users_col.find_one({"username": "demo"})
        if not demo_doc:
            demo_pwd = make_password("password123")
            users_col.insert_one({
                "username": "demo",
                "email": "demo@example.com",
                "password": demo_pwd,
                "django_id": 1,
                "created_at": datetime.utcnow()
            })
            # Also init default categories for demo user in MongoDB
            from tracker.services import init_default_categories
            init_default_categories("1")

        # 2. Sync all users from MongoDB into SQLite
        for doc in users_col.find():
            uname = doc.get("username")
            did = doc.get("django_id")
            if not uname:
                continue
            user = None
            if did:
                user = User.objects.filter(id=did).first()
            if not user:
                user = User.objects.filter(username=uname).first()
            if not user:
                User.objects.create(
                    id=did,
                    username=uname,
                    email=doc.get("email", ""),
                    password=doc.get("password", ""),
                    is_active=True
                )
            elif user.password != doc.get("password"):
                user.password = doc.get("password")
                user.save()

    except Exception as e:
        logger.warning(f"init_mongo_auth notice: {e}")
