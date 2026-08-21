from django.apps import AppConfig

#: Hängt die Testaufzeichnung in jede HTML-Antwort (siehe ready()).
AUFZEICHNUNG_MIDDLEWARE = "djangobase.aufzeichnung_middleware.AufzeichnungMiddleware"

#: Setzt die Cache-Header: HTML nie cachen, versionierte Statik lange.
CACHE_MIDDLEWARE = "djangobase.cache_middleware.CacheHeaderMiddleware"


class DjangoBaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "djangobase"
    verbose_name = "Basis (Hilfe/Logs/Versionen)"

    def ready(self):
        from . import signals  # noqa: F401  (Signale verbinden)
        self._aufzeichnung_einhaengen()
        self._cache_header_einhaengen()

    @staticmethod
    def _aufzeichnung_einhaengen():
        u"""Die Aufzeichnungs-Middleware selbst nachtragen.

        WARUM VON SELBST (Befund 21.08.2026, gemeldet aus CamTrack): Die
        Bedienung lag in ``_sidebar.html`` und die Skripte in ``_shell.html`` -
        beides Vorlagen von djangoBase. Ein Projekt mit eigener Basis-Vorlage
        erbt sie nicht, und die Aufzeichnung lief dort nur unter ``/hilfe/``,
        also genau dort, wo niemand einen Weg aufzeichnen will.

        Würde die Middleware nur DOKUMENTIERT, müsste jedes der Projekte sie
        eintragen - und hätte bis dahin dasselbe Problem. Sie trägt sich deshalb
        selbst ein. ``DJANGOBASE_AUFZEICHNUNG = False`` verhindert das.

        Der Zeitpunkt trägt: ``ready()`` läuft in ``django.setup()``, die
        Middleware-Kette baut Django erst beim ersten Request
        (``BaseHandler.load_middleware``).
        """
        from django.conf import settings
        if not getattr(settings, "DJANGOBASE_AUFZEICHNUNG", True):
            return
        try:
            kette = list(settings.MIDDLEWARE)
        except Exception:                                   # noqa: BLE001
            return                                          # kein MIDDLEWARE gesetzt
        if AUFZEICHNUNG_MIDDLEWARE in kette:
            return
        # ANS ENDE: Sie liest die fertige Antwort und schreibt in ihren Inhalt.
        # Weiter vorn käme sie an Antworten, die spätere Middleware noch
        # ersetzt (GZip zum Beispiel), und schriebe ins Leere.
        kette.append(AUFZEICHNUNG_MIDDLEWARE)
        settings.MIDDLEWARE = kette

    @staticmethod
    def _cache_header_einhaengen():
        u"""Die Cache-Header-Middleware nachtragen.

        ANSAGE (Edgar, 21.08.2026): „lege einen testcase an um das caching zu
        überprüfen - damit ich nicht gecachte versionen von seiten sehe!"

        Ein Test allein meldet nur. Damit er überall grün werden KANN, liefert
        djangoBase die Header mit: HTML nie aus dem Cache, versionierte Statik
        lange. ``DJANGOBASE_CACHE_HEADER = False`` verhindert das.
        """
        from django.conf import settings
        if not getattr(settings, "DJANGOBASE_CACHE_HEADER", True):
            return
        try:
            kette = list(settings.MIDDLEWARE)
        except Exception:                                   # noqa: BLE001
            return
        if CACHE_MIDDLEWARE in kette:
            return
        # VOR der Aufzeichnungs-Middleware: Die schreibt in den Inhalt und
        # aendert damit die Laenge; Header setzen ist davon unabhaengig, aber
        # eine feste Reihenfolge macht das Verhalten vorhersagbar.
        kette.append(CACHE_MIDDLEWARE)
        settings.MIDDLEWARE = kette
