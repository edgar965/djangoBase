# -*- coding: utf-8 -*-
u"""Funktionen, die auf Modulebene stehen MUESSEN — Djangos Vorschrift.

DER FEHLALARM (27.08.2026, 3DTools)
===================================
`freie-funktionen` meldete `ui/context_processors.py` als **Warnung**: zwei
Funktionen auf Modulebene, keine Klasse. Der Vorschlag lautete, sie in eine
Klasse `ContextProcessors` zu stecken. Wer dem folgt, macht die Seite kaputt.

Django loest solche Eintraege mit `django.utils.module_loading.import_string`
auf, und das macht **genau einen** `rsplit(".", 1)`::

    module_path, class_name = dotted_path.rsplit(".", 1)

`ui.context_processors.Vorlagenkontext.version` wuerde damit als MODUL
`ui.context_processors.Vorlagenkontext` gesucht — und scheitern. Dieselbe
Vorschrift wie bei Djangos `Command`-Klasse in einem Management-Befehl.

Geraten wird hier nichts: Gefragt werden die EINSTELLUNGEN des Projekts. Nur
was dort als gepunkteter Pfad eingetragen ist, gilt als vorgeschrieben.
"""

from django.conf import settings


class Rahmenvorschrift:
    u"""Welche Modulfunktionen Django beim Namen aus den Einstellungen holt."""

    #: Einstellungen, die gepunktete Pfade auf Funktionen/Klassen fuehren.
    #: `TEMPLATES` steht nicht dabei — die Kontextprozessoren liegen dort
    #: verschachtelt und werden eigens gelesen.
    LISTEN = ('MIDDLEWARE', 'AUTHENTICATION_BACKENDS',
              'PASSWORD_HASHERS', 'DEFAULT_EXCEPTION_REPORTER_FILTER',
              'MESSAGE_STORAGE', 'SESSION_ENGINE', 'FILE_UPLOAD_HANDLERS',
              'STATICFILES_FINDERS', 'LOGIN_URL')

    #: Dateien, deren Modulfunktion der Rahmen selbst ruft. `manage.py` ist
    #: von Django erzeugt (`main()` unter `if __name__ == "__main__"`),
    #: `wsgi.py`/`asgi.py` tragen `application`.
    DATEIEN = ('manage.py', 'wsgi.py', 'asgi.py')

    @staticmethod
    def _aus_einstellungen():
        u"""Alle gepunkteten Pfade, die in den Einstellungen stehen."""
        pfade = set()
        for name in Rahmenvorschrift.LISTEN:
            wert = getattr(settings, name, None)
            if isinstance(wert, str):
                pfade.add(wert)
            elif isinstance(wert, (list, tuple)):
                pfade.update(w for w in wert if isinstance(w, str))
        for vorlage in getattr(settings, 'TEMPLATES', None) or ():
            werte = (vorlage.get('OPTIONS') or {}).get('context_processors')
            pfade.update(w for w in (werte or ()) if isinstance(w, str))
        return pfade

    @staticmethod
    def namen():
        u"""Die letzten Namensteile: `{'version', 'active_theme', …}`.

        Nur der Name, nicht der Pfad — das Werkzeug sieht Dateipfade, nicht
        Modulpfade, und ein Abgleich ueber den Modulnamen waere in einem
        Projekt mit mehreren Anwendungen unzuverlaessig. Ein gleichnamiger
        Treffer anderswo ist der guenstigere Fehler: Er unterschlaegt einen
        Hinweis, statt zum Umbau von etwas Vorgeschriebenem aufzufordern.
        """
        namen = set()
        for pfad in Rahmenvorschrift._aus_einstellungen():
            teil = pfad.rsplit('.', 1)[-1]
            # Klassen (`SessionMiddleware`) meint diese Frage nicht — die
            # duerfen und sollen Klassen sein.
            if teil and teil[:1].islower():
                namen.add(teil)
        return namen

    @staticmethod
    def eigene_datei(pfad):
        u"""Ist die Datei selbst eine Rahmendatei (`manage.py`, `wsgi.py`)?"""
        name = str(pfad).replace('\\', '/').split('/')[-1]
        return name in Rahmenvorschrift.DATEIEN
