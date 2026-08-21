from django.apps import AppConfig

#: Hängt die Testaufzeichnung in jede HTML-Antwort (siehe ready()).
AUFZEICHNUNG_MIDDLEWARE = "djangobase.aufzeichnung_middleware.AufzeichnungMiddleware"


class DjangoBaseConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "djangobase"
    verbose_name = "Basis (Hilfe/Logs/Versionen)"

    def ready(self):
        from . import signals  # noqa: F401  (Signale verbinden)
        self._aufzeichnung_einhaengen()

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
