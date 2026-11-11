from django.apps import AppConfig


class TrackerConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'tracker'
    verbose_name = 'Expense Tracker'

    def ready(self):
        try:
            from database.mongo_auth import init_mongo_auth
            init_mongo_auth()
        except Exception:
            pass
