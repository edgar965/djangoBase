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

DERSELBE FALL AUSSERHALB VON DJANGO (01.09.2026, 3DTools)
=========================================================
Nicht jeder Rahmen ist Django. Das Blender-Addon in `HumanBodyBlender`
wurde mit zehn Modulen gemeldet, die `register`/`unregister` auf
Modulebene tragen — Blenders Addon-Protokoll ruft genau diese beiden
Namen am Modul auf (`bpy.utils.register_class` haengt darunter). Als
Methoden einer Klasse ruft sie niemand mehr, und das Addon laedt nicht.

Django-Einstellungen koennen das nicht wissen. Deshalb darf ein Projekt
die Namen seines eigenen Rahmens nennen::

    DJANGOBASE = {"rahmenfunktionen": ["register", "unregister"]}

Das ist eine ANGABE, keine Abschaltung: Wer den Schluessel setzt,
behauptet, dass ein Rahmen diese Namen am Modul ruft — und muss es neben
dem Eintrag begruenden.
"""

import ast

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

    #: Dekoratoren, die eine Funktion beim Rahmen ANMELDEN. Wer sie in
    #: eine Klasse verschiebt, meldet nichts mehr an.
    #:
    #: DER FEHLALARM (28.08.2026, assistant)
    #: =====================================
    #: `mail/signals.py` wurde mit sechs freien Funktionen gemeldet. Alle
    #: sechs sind `@receiver`-Signalhandler: Django haelt sie ueber eine
    #: schwache Referenz auf das Funktionsobjekt, und `dispatch_uid`
    #: unterscheidet sie. Als Methoden waeren sie zwar aufrufbar, aber die
    #: Anmeldung liefe ueber ein anderes Objekt — und `post_save` fuer
    #: `Mail` feuerte ins Leere. Bei `mail/signals.py` haengt daran das
    #: automatische Einbetten, Einsortieren und Verschlagworten JEDER neu
    #: angelegten Mail.
    #:
    #: Dasselbe gilt fuer Templatetags: Django sucht sie beim Namen, den
    #: `@register.filter` eintraegt.
    #:
    #: NICHT in dieser Liste stehen `require_POST`, `csrf_exempt`,
    #: `contextmanager` und `atomic` — die wirken auch auf Methoden. Sie
    #: nehmen keine Anmeldung vor, sie umhuellen nur den Aufruf.
    ANMELDENDE_DEKORATOREN = frozenset((
        # Django-Signale
        'receiver',
        # Django-Templatetags: register.filter / .simple_tag / .tag /
        # .inclusion_tag
        'filter', 'simple_tag', 'inclusion_tag', 'tag',
        # Celery und verwandte Aufgabenplaner
        'task', 'shared_task', 'periodic_task',
        # Django-Admin-Aktionen werden ueber den Funktionsnamen gefunden
        'action', 'display',
    ))

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
        namen = set(Rahmenvorschrift._eigene_namen())
        for pfad in Rahmenvorschrift._aus_einstellungen():
            teil = pfad.rsplit('.', 1)[-1]
            # Klassen (`SessionMiddleware`) meint diese Frage nicht — die
            # duerfen und sollen Klassen sein.
            if teil and teil[:1].islower():
                namen.add(teil)
        return namen

    @staticmethod
    def _eigene_namen():
        u"""Was das Projekt als Rahmen-Namen ANGIBT.

        `DJANGOBASE["rahmenfunktionen"]` — eine Liste blanker Namen, kein
        gepunkteter Pfad: Der fremde Rahmen ruft sie am Modul, nicht ueber
        `import_string`. Fuer 3DTools sind das Blenders `register` und
        `unregister`.

        Grossgeschriebenes wird verworfen, wie oben bei den Einstellungen:
        Eine Klasse darf und soll eine Klasse sein, und ein Tippfehler
        `Register` soll keine stille Ausnahme bewirken.
        """
        cfg = getattr(settings, 'DJANGOBASE', None) or {}
        eintraege = cfg.get('rahmenfunktionen') or ()
        if isinstance(eintraege, str):
            eintraege = (eintraege,)
        return {str(e) for e in eintraege
                if str(e) and str(e)[:1].islower()}

    @staticmethod
    def selbst_gerufen(baum):
        u"""Namen, die die Datei in ihrem ``__main__``-Block selbst ruft.

        DER FEHLALARM (01.09.2026, 3DTools)
        ===================================
        `convert/dazknochennamen.py` ist ein Werkzeug fuer die
        Kommandozeile: unten steht ``if __name__ == "__main__": main()``.
        Gemeldet wurde es als „1 freie Funktion, Vorschlag Klasse
        `Dazknochennamen`" — in einer Klasse ruft der Block sie nicht
        mehr, und das Werkzeug startet nicht.

        Erkannt wird das AM CODE, nicht am Ordner: eine Ordnerliste raet
        und liegt beim naechsten Verzeichnis daneben
        (`~/.claude/rules/analysewerkzeuge.md`, Punkt 6).
        """
        namen = set()
        for knoten in baum.body:
            if not isinstance(knoten, ast.If):
                continue
            pruefung = ast.dump(knoten.test)
            if "'__name__'" not in pruefung and '"__name__"' not in pruefung:
                continue
            for teil in ast.walk(knoten):
                if isinstance(teil, ast.Call) and isinstance(teil.func,
                                                             ast.Name):
                    namen.add(teil.func.id)
        return namen

    @staticmethod
    def eigene_datei(pfad):
        u"""Ist die Datei selbst eine Rahmendatei (`manage.py`, `wsgi.py`)?"""
        name = str(pfad).replace('\\', '/').split('/')[-1]
        return name in Rahmenvorschrift.DATEIEN

    @staticmethod
    def wird_angemeldet(knoten):
        u"""Traegt die Funktion einen Dekorator, der sie ANMELDET?

        Erkannt werden alle Schreibweisen, in denen sie vorkommen::

            @receiver(post_save, sender=Mail)      Aufruf mit Argumenten
            @register.filter                       Attribut ohne Aufruf
            @register.simple_tag(takes_context=1)  beides
            @app.task                              Attribut

        Verglichen wird nur der LETZTE Namensteil: ``register`` heisst in
        jedem Projekt anders, ``filter`` nicht.
        """
        import ast

        for dekorator in getattr(knoten, 'decorator_list', ()):
            teil = dekorator
            # ``@receiver(...)`` -> der Aufruf, dann die Funktion darin
            while isinstance(teil, ast.Call):
                teil = teil.func
            name = getattr(teil, 'attr', None) or getattr(teil, 'id', None)
            if name in Rahmenvorschrift.ANMELDENDE_DEKORATOREN:
                return True
        return False
