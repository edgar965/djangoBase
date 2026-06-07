"""Zentrales Logging für Projekte, die djangobase nutzen.

Verwendung in settings.py:
    import djangobase.logging as dblog
    LOGGING = dblog.config(BASE_DIR / "logs")

Schreibt rotierende Dateien (django.log, request.log) ins Log-Verzeichnis –
genau die, die die Hilfe→Logs-Seite anzeigt.
"""
import os


def config(log_dir, level="INFO"):
    log_dir = str(log_dir)
    os.makedirs(log_dir, exist_ok=True)

    def datei(name):
        return {
            "class": "logging.handlers.RotatingFileHandler",
            "filename": os.path.join(log_dir, name),
            "maxBytes": 3 * 1024 * 1024,
            "backupCount": 5,
            "encoding": "utf-8",
            "formatter": "voll",
        }

    return {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "voll": {
                "format": "{asctime} [{levelname}] {name}: {message}",
                "style": "{",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": {"class": "logging.StreamHandler", "formatter": "voll"},
            "django_file": datei("django.log"),
            "error_file": {**datei("error.log"), "level": "ERROR"},
        },
        "root": {"handlers": ["console", "django_file", "error_file"], "level": level},
        "loggers": {
            "django": {"handlers": ["console", "django_file", "error_file"],
                       "level": level, "propagate": False},
            "django.request": {"handlers": ["django_file", "error_file"],
                               "level": "WARNING", "propagate": False},
        },
    }
