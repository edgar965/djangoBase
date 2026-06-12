"""Aktivitäts-/Online-Status eingeloggter Nutzer.

Problem: „Eingeloggt bleiben" (remember me) erzeugt wochenlang gültige Sessions.
Wer die Benutzerliste über *aktive Sessions* als „online" markiert, zeigt daher
auch längst weggeklickte Nutzer als eingeloggt an.

Lösung: bei jeder Anfrage eines eingeloggten Nutzers einen kurzlebigen Cache-
Eintrag setzen. „Online" = in den letzten Minuten tatsächlich aktiv. Selbst-
korrigierend (Cache-TTL läuft ab) und ohne DB-Migration.

Opt-in: nur aktiv, wenn ``OnlineMiddleware`` in MIDDLEWARE steht UND
``DJANGOBASE_ONLINE_TRACKING = True`` gesetzt ist. Sonst bleibt das bisherige
Verhalten (aktive Session) erhalten – andere Projekte werden nicht verändert.
"""
from django.conf import settings
from django.core.cache import cache


def online_fenster():
    """Sekunden, die ein Nutzer nach seiner letzten Anfrage als online gilt."""
    return int(getattr(settings, "DJANGOBASE_ONLINE_FENSTER", 300))


def _schluessel(user_id):
    return "djb:online:%d" % int(user_id)


def markiere_online(user_id):
    """Aktivität festhalten (gedrosselt: höchstens ~1× pro Minute schreiben).
    Gibt True zurück, wenn jetzt tatsächlich geschrieben wurde (= nicht gedrosselt)."""
    s = _schluessel(user_id)
    if cache.get(s + ":frisch"):
        return False
    cache.set(s, True, online_fenster())
    cache.set(s + ":frisch", 1, 60)
    return True


def schreibe_zuletzt_aktiv(user):
    """Persistenten „zuletzt aktiv"-Zeitstempel im Profil aktualisieren (für die
    Spalte „Zuletzt" – im Gegensatz zu last_login = letzte Anmeldung)."""
    from django.utils import timezone
    from .models import Teilnehmer
    Teilnehmer.objects.update_or_create(
        user=user, defaults={"zuletzt_aktiv": timezone.now()})


def online_ids(user_ids):
    """Teilmenge der user_ids, die laut Cache aktuell online sind."""
    treffer = set()
    for uid in user_ids:
        if cache.get(_schluessel(uid)):
            treffer.add(int(uid))
    return treffer


def tracking_aktiv():
    return bool(getattr(settings, "DJANGOBASE_ONLINE_TRACKING", False))


class OnlineMiddleware:
    """Markiert eingeloggte Nutzer bei jeder Anfrage als aktiv (Cache)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        u = getattr(request, "user", None)
        if u is not None and getattr(u, "is_authenticated", False):
            try:
                if markiere_online(u.id):           # nur wenn nicht gedrosselt
                    schreibe_zuletzt_aktiv(u)        # persistenter Zeitstempel
            except Exception:  # noqa: BLE001 – Online-Status darf nie die Anfrage stören
                pass
        return self.get_response(request)
