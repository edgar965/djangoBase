from django.apps import AppConfig


class DjangoBaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "djangobase"
    verbose_name = "Basis (Hilfe/Logs/Versionen)"
