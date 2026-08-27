"""Zentrales Logging für Projekte, die djangobase nutzen.

Verwendung in settings.py:
    import djangobase.logging as dblog
    LOGGING = dblog.config(BASE_DIR / "logs")

Schreibt rotierende Dateien (django.log, error.log) ins Log-Verzeichnis —
genau die, die die Hilfe→Logs-Seite anzeigt.

Multi-Process/Multi-Thread-Sicherheit:
    ``concurrent_log_handler`` (portalocker-basiert) statt stdlib
    ``RotatingFileHandler``. Seit dem 20.08.2026 eine feste Abhaengigkeit,
    nicht mehr optional.

    WARUM (Befund shortlongx, 20.08.2026): Nicht nur Threads teilen sich die
    Datei - SCHON ZWEI PROZESSE reichen. Laeuft ein Werkzeug neben dem Server
    (der Normalfall: Messskripte, Management-Commands, Testlaeufe), halten
    beide dieselbe rotierende Datei offen, und unter Windows kann nur einer
    umbenennen. Ein einziger Testlauf erzeugte 107 Meldungen

        PermissionError: [WinError 32] … django.log -> django.log.1

    Waehrend der Kollision gehen Logzeilen verloren, und die Ausgabe des
    Werkzeugs wird mit Tracebacks zugeschuettet. Der stdlib-Fallback bleibt
    als Notnagel stehen, falls das Paket in einer Umgebung fehlt - dann ist
    das Verhalten wie vorher.
"""
import os

try:
    import concurrent_log_handler  # noqa: F401
    _HANDLER_CLASS = "concurrent_log_handler.ConcurrentRotatingFileHandler"
except ImportError:
    _HANDLER_CLASS = "logging.handlers.RotatingFileHandler"


#: Der Name des Filters, der die Auftragskennung an jede Zeile haengt.
JOB_FILTER = "job_context"

#: Der Formatierer, den `LogFenster` lesen kann (siehe `config`).
FORMATIERER = "voll"


def handler_filters_fuer(job_context):
    """Die Filterliste eines Handlers — mit oder ohne Auftragskennung."""
    return [JOB_FILTER] if job_context else []


def datei_handler(log_dir, name, *, level=None, max_bytes=3 * 1024 * 1024,
                  backup_count=5, filters=None):
    """Ein rotierender Datei-Handler, gebaut wie djangoBases eigene.

    OEFFENTLICH SEIT DEM 28.08.2026: Projekte mit eigenen Logdateien geben sie
    ueber `extra_handlers` mit und brauchten dafuer denselben Bausatz. Wer ihn
    nachbaut, hat zwei Fassungen — und wer dann `maxBytes` aendert, aendert
    `django.log`, aber nicht die Projektdatei daneben.

        LOGGING = dblog.config(
            LOG_DIR, job_context=True,
            extra_handlers={'core_file': dblog.datei_handler(
                LOG_DIR, 'core.log', level='DEBUG',
                filters=dblog.handler_filters_fuer(True))})
    """
    handler = {
        "class": _HANDLER_CLASS,
        "filename": os.path.join(str(log_dir), name),
        "maxBytes": max_bytes,
        "backupCount": backup_count,
        "encoding": "utf-8",
        "formatter": FORMATIERER,
    }
    if level:
        handler["level"] = level
    if filters:
        handler["filters"] = list(filters)
    return handler


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
        return datei_handler(log_dir, name, level=level_override,
                             max_bytes=file_max_bytes,
                             backup_count=file_backup_count,
                             filters=handler_filters_fuer(job_context))

    # Wenn job_context aktiv: format-String enthaelt einen {job_str}-Slot,
    # der vom JobContextFilter befuellt wird. Filter wird automatisch auf
    # alle Handler gesetzt.
    fmt = ("{asctime} [{levelname}] {name}: {job_str}{message}"
           if job_context else "{asctime} [{levelname}] {name}: {message}")
    base_filters = {}
    handler_filters = handler_filters_fuer(job_context)
    if job_context:
        base_filters["job_context"] = {"()": "djangobase.jobctx.JobContextFilter"}

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
