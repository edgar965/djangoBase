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


def config(log_dir, level="INFO", *,
           job_context=False,
           extra_filters=None,
           extra_formatters=None,
           extra_handlers=None,
           extra_loggers=None,
           file_max_bytes=3 * 1024 * 1024,
           file_backup_count=5):
    """Liefert ein Django-LOGGING-Dict mit rotierenden Datei-Handlern.

    Projekte koennen mit den extra_*-Parametern eigene Filter, Formatter,
    Handler oder Logger hinzufuegen, ohne das ganze Dict selbst neu zu
    bauen. Beispiel CamTrack:

        LOGGING = dblog.config(
            BASE_DIR / "logs",
            extra_filters={"job_context": {"()": "app.logging_utils.JobContextFilter"}},
            extra_formatters={"verbose": {"format": "...", "datefmt": "..."}},
            extra_handlers={
                "file_info": {
                    "class": dblog.handler_class(),
                    "filename": str(LOG_DIR / "camtrack.log"),
                    "maxBytes": 10 * 1024 * 1024,
                    "backupCount": 5,
                    "formatter": "verbose",
                    "filters": ["job_context"],
                    "level": "INFO",
                    "encoding": "utf-8",
                },
                # ... weitere
            },
            extra_loggers={
                "camtrack": {"handlers": ["console", "file_info", "file_error"],
                             "level": "INFO", "propagate": False},
                # ...
            },
            file_max_bytes=10 * 1024 * 1024,
        )
    """
    log_dir = str(log_dir)
    os.makedirs(log_dir, exist_ok=True)

    def datei(name, level_override=None):
        h = {
            "class": _HANDLER_CLASS,
            "filename": os.path.join(log_dir, name),
            "maxBytes": file_max_bytes,
            "backupCount": file_backup_count,
            "encoding": "utf-8",
            "formatter": "voll",
        }
        if level_override:
            h["level"] = level_override
        return h

    # Wenn job_context aktiv: format-String enthaelt einen {job_str}-Slot,
    # der vom JobContextFilter befuellt wird. Filter wird automatisch auf
    # alle Handler gesetzt.
    fmt = ("{asctime} [{levelname}] {name}: {job_str}{message}"
           if job_context else "{asctime} [{levelname}] {name}: {message}")
    base_filters = {}
    handler_filters = []
    if job_context:
        base_filters["job_context"] = {"()": "djangobase.jobctx.JobContextFilter"}
        handler_filters = ["job_context"]

    def _h(extra):
        return {**extra, **({"filters": handler_filters} if handler_filters else {})}

    cfg = {
        "version": 1,
        "disable_existing_loggers": False,
        "filters": base_filters,
        "formatters": {
            "voll": {
                "format": fmt,
                "style": "{",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
        },
        "handlers": {
            "console": _h({"class": "logging.StreamHandler", "formatter": "voll"}),
            "django_file": _h(datei("django.log")),
            "error_file": _h(datei("error.log", level_override="ERROR")),
        },
        "root": {"handlers": ["console", "django_file", "error_file"], "level": level},
        "loggers": {
            "django": {"handlers": ["console", "django_file", "error_file"],
                       "level": level, "propagate": False},
            "django.request": {"handlers": ["django_file", "error_file"],
                               "level": "WARNING", "propagate": False},
        },
    }
    if extra_filters:
        cfg["filters"].update(extra_filters)
    if extra_formatters:
        cfg["formatters"].update(extra_formatters)
    if extra_handlers:
        cfg["handlers"].update(extra_handlers)
    if extra_loggers:
        cfg["loggers"].update(extra_loggers)
    return cfg


def handler_class():
    """Exportiert den effektiv genutzten Handler-Klassen-Pfad. Projekte
    mit eigenen LOGGING-Dicts (z.B. CamTrack mit Per-Camera-Loggern) können
    denselben Handler ziehen wie djangoBase — ohne den Try/Except-Tanz
    selbst zu wiederholen."""
    return _HANDLER_CLASS
