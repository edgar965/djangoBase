# -*- coding: utf-8 -*-
"""Cachekonzept — prueft ein Projekt gegen die Cache-Regeln von djangoBase.

EINE QUELLE, DREI VERBRAUCHER (06.09.2026, Edgar: „dokumentiere das Caching-
Konzept (auch fuer ES-Module usw.) in djangoBase Hilfe - Cache … und schreibe
Testcases unter CodeReview und ganz normale djangoBase-Testcases, die jede
Seite ueberpruefen, ob das richtig drin ist, inkl. ES-Module")
================================================================================
    * Hilfe -> Cache              erklaert die Regeln und zeigt die Befunde
    * Hilfe -> Skills / Review    `skills.cachekonzept.Cachekonzept` (Befund-Werkzeug)
    * Konformitaetspruefung       `tests/konform/test_cachekonzept.py` (rot, wenn
                                  eine Vorlage oder Einstellung dagegen verstoesst)

Alle drei rufen DIESES Modul. Eine Regel, die nur an einer der drei Stellen
stuende, waere nach der zweiten Woche keine mehr.

DIE REGELN — und der Vorfall, aus dem jede stammt
=================================================
1. HTML nie aus dem Zwischenspeicher (``CacheHeaderMiddleware``, traegt sich
   selbst ein). Wer nach einem Deploy die Seite von gestern sieht, sucht den
   Fehler im Code.
2. Keine pauschale ``NoCache``-Middleware: Sie macht die zweite Haelfte kaputt,
   jede Seite laedt dann saemtliche Module neu, und jede ``?v=``-Kennung ist
   wirkungslos (ShortLongX, 3DTools bis 28.08.2026).
3. Eigene Statik traegt eine Fassung — aber KEINEN Zeitstempel ``?t={% now %}``
   an Skript- und Stildateien: Der aendert sich jede Sekunde, die Datei liegt
   nie im Zwischenspeicher, und jede Seite laedt alles neu. Fuer Adressen von
   Daten (``bvhUrl``) ist ``?t=`` richtig, fuer Statik nicht.
4. ES-Module ueber ``{% fassungspfad %}`` (``/statik/v-<fassung>/…``), nicht
   ueber ``{% static %}?t=`` oder ``?v=``: Eine Abfrage vererbt sich NICHT auf
   relative Importe. Die Einstiegsdatei kam frisch, ``./skinning.js`` aus dem
   Zwischenspeicher — ``SyntaxError: does not provide an export named …``,
   leere Seite bei HTTP 200 (3DTools, 05.09.2026, zweimal an einem Tag).
5. Keine Kennung in Import-Adressen (``from './x.js?v=3'``): dieselbe Datei
   unter zwei Adressen laedt der Browser zweimal, mit getrennten Zustaenden —
   jeder Klick wurde doppelt aufgezeichnet (21.08.2026).
6. Der Fassungspfad ist eingehaengt (``include('djangobase.fassungsstatik')``),
   sonst antwortet ``/statik/v-…/`` mit 404 und jede Modulseite ist leer.
7. ``StatikKopfzeilen`` liegt um die ASGI-Anwendung: Der Entwicklungsserver
   beantwortet Statik VOR der Middleware; ohne diese Huelle bleibt Statik ohne
   ``Cache-Control``, und der Browser schaetzt die Frische selbst — 10 % des
   Dateialters, bei drei Wochen zwei Tage ohne Rueckfrage.

Regeln 1, 2, 5 prueft djangoBase seit dem 21.08.2026 an anderer Stelle
(``test_cache.py``, ``test_statik.py``, Werkzeug ``esmodulimporte``); sie stehen
hier der Vollstaendigkeit halber und werden mitgeprueft, damit die Seite
Hilfe -> Cache EIN Bild zeigt.
"""

import os
import re

from django.conf import settings

__all__ = ["Cachekonzept", "Regel"]


class Regel:
    """Eine Regel des Konzepts — Kennung, Titel, Warum, und was zu tun ist."""

    __slots__ = ("kennung", "titel", "warum", "wie")

    def __init__(self, kennung, titel, warum, wie):
        self.kennung = kennung
        self.titel = titel
        self.warum = warum
        self.wie = wie


class Cachekonzept:
    """Findet Verstoesse in Vorlagen, JavaScript und Einstellungen."""

    REGELN = (
        Regel(
            "html-no-store",
            "HTML nie aus dem Zwischenspeicher",
            "Nach einem Deploy sieht der Nutzer sonst die Seite von gestern und sucht den Fehler im Code.",
            "`CacheHeaderMiddleware` traegt sich selbst ein (`djangobase.apps`). Nichts zu tun — "
            "nur nicht entfernen.",
        ),
        Regel(
            "keine-nocache-middleware",
            "Keine pauschale NoCache-Middleware",
            "`no-store` auf ALLES laesst jede Seite saemtliche Module neu laden; jede `?v=`-Kennung "
            "ist dann wirkungslos.",
            "Eigene `NoCacheMiddleware` aus `MIDDLEWARE` streichen; die djangoBase-Middleware "
            "unterscheidet HTML und Statik.",
        ),
        Regel(
            "kein-zeitstempel-an-statik",
            "Kein `?t={% now %}` an Skript- und Stildateien",
            "Der Zeitstempel aendert sich jede Sekunde: die Datei liegt nie im Zwischenspeicher, "
            "jede Seite laedt alles neu.",
            "`{% fassungspfad 'css/seite.css' %}` — die Fassung aendert sich genau dann, wenn sich "
            "eine Datei aendert.",
        ),
        Regel(
            "modul-ueber-fassungspfad",
            "ES-Module ueber `{% fassungspfad %}`, nicht ueber `{% static %}?t=`",
            "Eine Abfrage vererbt sich nicht auf relative Importe: Einstieg frisch, Geschwistermodul "
            "alt — `SyntaxError: does not provide an export named …`, leere Seite bei HTTP 200 "
            "(3DTools, 05.09.2026).",
            '`<script type="module" src="{% fassungspfad \'viewer/index.js\' %}">` und '
            "`import('{% fassungspfad \"js/x.js\" %}')`; `{% load fassung %}` oben in der Vorlage.",
        ),
        Regel(
            "keine-kennung-in-importen",
            "Keine Kennung in Import-Adressen",
            "`from './x.js?v=3'` laedt dieselbe Datei ein zweites Mal, mit eigenem Zustand — jeder "
            "Klick doppelt (21.08.2026).",
            "Importe ohne Abfrage lassen; die Fassung kommt aus dem Pfad des Einstiegs.",
        ),
        Regel(
            "fassungspfad-eingehaengt",
            "Der Fassungspfad ist eingehaengt",
            "Ohne `include('djangobase.fassungsstatik')` antwortet `/statik/v-…/` mit 404, und jede "
            "Modulseite ist leer.",
            "In `urls.py`: `path('', include('djangobase.fassungsstatik'))`.",
        ),
        Regel(
            "statik-kopfzeilen-im-asgi",
            "`StatikKopfzeilen` um die ASGI-Anwendung",
            "Der Entwicklungsserver beantwortet Statik vor der Middleware; ohne die Huelle schaetzt "
            "der Browser die Frische selbst — 10 % des Dateialters, bei drei Wochen zwei Tage ohne "
            "Rueckfrage.",
            "In `asgi.py`: `application = StatikKopfzeilen(ASGIStaticFilesHandler(get_asgi_application()))`.",
        ),
    )

    #: <script type="module" src="{% static 'x.js' %}?t=…"> (Attributreihenfolge beliebig)
    MODUL_EINSTIEG = re.compile(
        r'<script\b(?=[^>]*\btype\s*=\s*["\']module["\'])[^>]*\bsrc\s*=\s*["\']\{%\s*static\s+[^%]*%\}\?[tv]=',
        re.I | re.S,
    )
    #: import('{% static "x.js" %}?t=…')
    IMPORT_MIT_ABFRAGE = re.compile(r'\bimport\(\s*["\']\{%\s*static\s+[^%]*%\}\?[tv]=', re.I)
    #: {% static 'x.js' %}?t={% now … %} — an Skript oder Stil
    ZEITSTEMPEL = re.compile(r'\{%\s*static\s+["\'][^"\']+\.(?:js|css)["\']\s*%\}\?t=\{%\s*now\b', re.I)
    #: from './x.js?v=3' / import('./x.js?t=…') in JavaScript
    IMPORT_KENNUNG = re.compile(r"""(?:\bfrom\s*|\bimport\s*\(\s*)["'][^"']*\.m?js\?[tv]=[^"']*["']""")
    #: Vorlagenkommentare zaehlen nicht
    KOMMENTAR = re.compile(r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}|\{#.*?#\}|<!--.*?-->", re.S)
    NOCACHE = re.compile(r"nocache", re.I)

    # --------------------------------------------------------------- Vorlagen

    @classmethod
    def vorlage(cls, name, text):
        """Befunde einer Vorlage: Liste von `{regel, ort, was}`."""
        text = cls.KOMMENTAR.sub(lambda m: "\n" * m.group(0).count("\n"), text)
        raus = []
        for regel, muster in (
            ("modul-ueber-fassungspfad", cls.MODUL_EINSTIEG),
            ("modul-ueber-fassungspfad", cls.IMPORT_MIT_ABFRAGE),
            ("kein-zeitstempel-an-statik", cls.ZEITSTEMPEL),
        ):
            for treffer in muster.finditer(text):
                zeile = text.count("\n", 0, treffer.start()) + 1
                raus.append(
                    {"regel": regel, "ort": "%s:%d" % (name, zeile), "was": treffer.group(0).strip()[:120]}
                )
        return cls._einmal(raus)

    @classmethod
    def skript(cls, name, text):
        """Befunde einer JavaScript-Datei."""
        raus = []
        for treffer in cls.IMPORT_KENNUNG.finditer(text):
            zeile = text.count("\n", 0, treffer.start()) + 1
            raus.append(
                {
                    "regel": "keine-kennung-in-importen",
                    "ort": "%s:%d" % (name, zeile),
                    "was": treffer.group(0).strip()[:120],
                }
            )
        return raus

    @staticmethod
    def _einmal(befunde):
        """Ein Treffer je Ort — der Modul-Einstieg mit `?t=` faellt sonst zweimal auf."""
        gesehen, raus = set(), []
        for b in befunde:
            if b["ort"] in gesehen:
                continue
            gesehen.add(b["ort"])
            raus.append(b)
        return raus

    # ---------------------------------------------------------- Einstellungen

    @classmethod
    def einstellungen(cls):
        """Befunde an `MIDDLEWARE`, `urls.py` und `asgi.py` des laufenden Projekts."""
        raus = []
        kette = list(getattr(settings, "MIDDLEWARE", []) or [])
        if "djangobase.cache_middleware.CacheHeaderMiddleware" not in kette:
            raus.append(
                {
                    "regel": "html-no-store",
                    "ort": "settings.MIDDLEWARE",
                    "was": "CacheHeaderMiddleware fehlt in der Kette",
                }
            )
        for eintrag in kette:
            if cls.NOCACHE.search(eintrag) and not eintrag.startswith("djangobase."):
                raus.append(
                    {"regel": "keine-nocache-middleware", "ort": "settings.MIDDLEWARE", "was": eintrag}
                )
        if not cls.fassungspfad_eingehaengt():
            raus.append(
                {
                    "regel": "fassungspfad-eingehaengt",
                    "ort": "urls.py",
                    "was": "/statik/v-1/x.js loest nicht auf",
                }
            )
        asgi = cls.asgi_quelle()
        if asgi is not None and "StatikKopfzeilen" not in asgi:
            raus.append(
                {
                    "regel": "statik-kopfzeilen-im-asgi",
                    "ort": cls.asgi_pfad() or "asgi.py",
                    "was": "StatikKopfzeilen kommt in der ASGI-Anwendung nicht vor",
                }
            )
        return raus

    @staticmethod
    def fassungspfad_eingehaengt():
        from django.urls import Resolver404, resolve

        try:
            treffer = resolve("/statik/v-1/x.js")
        except Resolver404:
            return False
        return "fassungsstatik" in (getattr(treffer.func, "__module__", "") or "")

    @staticmethod
    def asgi_pfad():
        """Die Datei hinter `ASGI_APPLICATION` — `None`, wenn es keine gibt."""
        modul = getattr(settings, "ASGI_APPLICATION", "") or ""
        if not modul:
            return None
        teile = modul.split(".")[:-1]
        pfad = os.path.join(str(settings.BASE_DIR), *teile) + ".py"
        return pfad if os.path.isfile(pfad) else None

    @classmethod
    def asgi_quelle(cls):
        pfad = cls.asgi_pfad()
        if not pfad:
            return None
        with open(pfad, encoding="utf-8", errors="replace") as datei:
            return datei.read()

    # ------------------------------------------------------------------ Alles

    @classmethod
    def alles(cls, vorlagen, skripte):
        """`vorlagen`/`skripte`: Folgen von `(name, text)`. Liefert alle Befunde."""
        raus = []
        for name, text in vorlagen:
            raus.extend(cls.vorlage(name, text))
        for name, text in skripte:
            raus.extend(cls.skript(name, text))
        raus.extend(cls.einstellungen())
        return raus

    @classmethod
    def regel(cls, kennung):
        for r in cls.REGELN:
            if r.kennung == kennung:
                return r
        return None
