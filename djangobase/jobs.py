"""Optionale Registry fuer Hintergrund-Jobs (Daemon-Threads o. ae.).

Projekte registrieren ihre laufenden Jobs einmalig — typischerweise in
``AppConfig.ready()`` — und liefern dazu eine ``state``-Callable, die den
aktuellen Zustand als dict zurueckgibt. Die Hilfe -> Jobs-Seite
(``views/jobs.py``) listet alle registrierten Jobs und zeigt deren Zustand
live; optionale Callables ``trigger`` und ``set_enabled`` schalten Buttons
fuer „Jetzt ausfuehren" bzw. Aktivieren/Deaktivieren frei.

Alles in-memory, keine DB / keine Migration. Registriert ein Projekt nichts,
ist die Registry leer: der Nav-Eintrag „Jobs" wird ausgeblendet und die Seite
(nur per Direkt-URL erreichbar) zeigt einen Hinweis. Bestehende Projekte sind
damit voellig unberuehrt.

Beispiel (im Projekt, AppConfig.ready)::

    from djangobase import jobs
    from . import cron_runner
    jobs.register(
        "intraday", "Intraday-Abruf",
        state=cron_runner.get_state,
        beschreibung="Holt 1-Minuten-Bars im konfigurierten Intervall.",
        trigger=cron_runner.trigger_now,
    )
"""
import threading

_lock = threading.Lock()
_jobs: dict = {}   # slug -> dict(slug, name, beschreibung, state, trigger, set_enabled)


def register(slug, name, state, *, beschreibung="", trigger=None, set_enabled=None):
    """Registriert (oder ersetzt) einen Job.

    slug         eindeutiger Schluessel (str)
    name         Anzeigename (str)
    state        Callable -> dict; beliebige Key/Value-Paare (siehe Template).
                 Darf Exceptions werfen — snapshot() faengt sie ab.
    beschreibung optionaler Hilfetext (str)
    trigger      optional Callable() -> loest einen sofortigen Lauf aus
    set_enabled  optional Callable(bool) -> aktiviert/deaktiviert den Job
    """
    if not callable(state):
        raise TypeError("jobs.register: 'state' muss callable sein")
    with _lock:
        _jobs[slug] = {
            "slug": slug, "name": name, "beschreibung": beschreibung,
            "state": state, "trigger": trigger, "set_enabled": set_enabled,
        }


def unregister(slug):
    with _lock:
        _jobs.pop(slug, None)


def get(slug):
    with _lock:
        return _jobs.get(slug)


def has_jobs():
    with _lock:
        return bool(_jobs)


def snapshot():
    """Liste aller Jobs mit aufgeloestem Zustand — fuer View + JSON-Endpoint.

    Der State jedes Jobs wird einzeln in try/except aufgeloest, damit ein
    fehlerhafter Job die Seite nie crasht; sein Fehler erscheint dann als
    Feld ``fehler`` in seinem State-dict."""
    with _lock:
        jobs = list(_jobs.values())
    out = []
    for job in jobs:
        try:
            st = dict(job["state"]() or {})
        except Exception as e:   # noqa: BLE001 — Job-State darf die Seite nie crashen
            st = {"fehler": f"{type(e).__name__}: {e}"}
        out.append({
            "slug": job["slug"],
            "name": job["name"],
            "beschreibung": job["beschreibung"],
            "state": st,
            "kann_triggern": job["trigger"] is not None,
            "kann_schalten": job["set_enabled"] is not None,
        })
    return out
