"""Zentrales Logging für Projekte, die djangobase nutzen.

Verwendung in settings.py:
    import djangobase.logging as dblog
    LOGGING = dblog.config(BASE_DIR / "logs")

Schreibt rotierende Dateien (django.log, error.log) ins Log-Verzeichnis —
genau die, die die Hilfe→Logs-Seite anzeigt.

Multi-Process/Multi-Thread-Sicherheit:
    Wenn das optionale Paket ``concurrent_log_handler`` installiert ist
    (``pip install concurrent-log-handler``), wird
    ``ConcurrentRotatingFileHandler`` (portalocker-basiert) statt stdlib
    ``RotatingFileHandler`` genutzt. Damit sind Projekte mit >10 Threads,
    die parallel ins Log schreiben, sicher vor dem Windows-Rotate-
    Cycle-Deadlock (Symptom: ~30-60 s Stalls beim Rotate). Single-Thread-
    Projekte brauchen das Paket nicht; der stdlib-Fallback reicht.
"""
import os

try:
    import concurrent_log_handler  # noqa: F401
    _HANDLER_CLASS = "concurrent_log_handler.ConcurrentRotatingFileHandler"
except ImportError:
    _HANDLER_CLASS = "logging.handlers.RotatingFileHandler"


def config(log_dir, level="INFO"):
    log_dir = str(log_dir)
    os.makedirs(log_dir, exist_ok=True)

    def datei(name):
        return {
            "class": _HANDLER_CLASS,
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


def handler_class():
    """Exportiert den effektiv genutzten Handler-Klassen-Pfad. Projekte
    mit eigenen LOGGING-Dicts (z.B. CamTrack mit Per-Camera-Loggern) können
    denselben Handler ziehen wie djangoBase — ohne den Try/Except-Tanz
    selbst zu wiederholen."""
    return _HANDLER_CLASS
