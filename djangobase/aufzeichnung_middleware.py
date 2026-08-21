# -*- coding: utf-8 -*-
u"""Die Aufzeichnung in JEDE Seite einhängen — auch ohne djangoBase-Vorlagen.

DER BEFUND (21.08.2026, gemeldet aus CamTrack)
=============================================
    „Die Übernahme kam nicht an. djangoBase legt die Bedienung in seine eigene
     Seitenleiste und lädt die Module in seiner eigenen Hülle — beides benutzt
     CamTrack nicht. Ergebnis: Auf /kameras/, /live/kalender/ und jeder anderen
     Seite gab es weder den Bereich noch die Module. Der Aufzeichner lief
     ausschließlich unter /hilfe/ — also genau dort, wo niemand etwas
     aufzeichnen will."

Das war mein Fehler: Ich hatte das Markup in ``_sidebar.html`` und die Skripte
in ``_shell.html`` gelegt. Beide Vorlagen gehören djangoBase; ein Projekt mit
eigener Basis-Vorlage erbt sie nicht. Damit lief die Aufzeichnung genau dort,
wo sie nutzlos ist — und der Grund steht im Modulkopf von ``aufzeichner.js``
seit dem ersten Tag:

    „Wer erst dorthin navigieren muss, um zu starten, kann den Weg, der ihn
     interessiert, nie aufzeichnen."

DIE LÖSUNG: EINE MIDDLEWARE, KEINE VORLAGE
==========================================
Eine Vorlage erreicht nur, wer sie einbindet. Eine Middleware sieht jede
Antwort. Sie hängt ``<link>`` und ``<script>`` unmittelbar vor ``</body>`` ein —
mehr nicht; der Bereich selbst entsteht im Browser (``aufzeichner_leiste.js``
legt ihn an, wenn die Sidebar keinen mitbringt).

WAS SIE NICHT ANFASST
=====================
Nur ``text/html``-Antworten mit Statuscode 200 und einem ``</body>``. Also keine
JSON-Antworten, keine Downloads, keine Weiterleitungen, keine Fehlerseiten. Und
nichts, was als Fragment nachgeladen wird — ein HTMX-Schnipsel hat kein
``</body>``.

AUSNAHMEN
=========
``DJANGOBASE_AUFZEICHNUNG = False`` schaltet sie ganz ab.
``DJANGOBASE_AUFZEICHNUNG_AUS`` nimmt Pfad-Präfixe aus (z. B. ``["/admin/"]``).
Das Admin ist standardmäßig NICHT ausgenommen: Wer dort einen Weg aufzeichnen
will, soll es können.
"""
import re

from django.conf import settings
from django.templatetags.static import static

#: Vor diesem Tag wird eingehängt (das LETZTE Vorkommen, case-insensitive).
_BODY_ENDE = re.compile(rb"</body\s*>", re.IGNORECASE)


class AufzeichnungMiddleware:
    u"""Hängt CSS und Module der Testaufzeichnung in jede HTML-Antwort."""

    def __init__(self, get_response):
        self.get_response = get_response
        self._schnipsel = None

    def __call__(self, request):
        antwort = self.get_response(request)
        try:
            if self._passt(request, antwort):
                self._einhaengen(antwort)
        except Exception:                                   # noqa: BLE001
            # Eine kaputte Einbettung darf NIE eine Seite kaputt machen. Die
            # Aufzeichnung ist ein Werkzeug, kein Bestandteil der Anwendung.
            pass
        return antwort

    # ------------------------------------------------------------- Prüfungen
    def _passt(self, request, antwort):
        if not getattr(settings, "DJANGOBASE_AUFZEICHNUNG", True):
            return False
        if getattr(antwort, "streaming", False):
            return False
        if antwort.status_code != 200:
            return False
        if "text/html" not in (antwort.get("Content-Type") or ""):
            return False
        pfad = request.path or ""
        for aus in getattr(settings, "DJANGOBASE_AUFZEICHNUNG_AUS", ()) or ():
            if pfad.startswith(aus):
                return False
        # Der eigene Steuer-Endpunkt und statische Dateien nie.
        if pfad.startswith("/hilfe/tests/aufzeichnung"):
            return False
        return True

    # ------------------------------------------------------------- Einhängen
    def schnipsel(self):
        u"""Das einzuhängende HTML — einmal gebaut, dann gemerkt.

        Die Versionskennung hängt an ``Statik.kennung()``; im Entwicklungsbetrieb
        rechnet die sich bei jedem Aufruf neu (damit geänderte Module ankommen),
        deshalb wird hier NICHT dauerhaft gemerkt, sondern nur, wenn DEBUG aus
        ist."""
        from .statik import Statik
        v = Statik.kennung()
        teile = [
            '<link rel="stylesheet" href="%s?v=%s">'
            % (static("djangobase/css/aufzeichner.css"), v),
        ]
        for modul in ("aufzeichner.js", "aufzeichner_leiste.js",
                      "aufzeichner_abspieler.js"):
            teile.append('<script type="module" src="%s?v=%s"></script>'
                         % (static("djangobase/js/%s" % modul), v))
        return ("\n" + "\n".join(teile) + "\n").encode("utf-8")

    def _einhaengen(self, antwort):
        inhalt = antwort.content
        treffer = list(_BODY_ENDE.finditer(inhalt))
        if not treffer:
            return                        # Fragment ohne </body> - nichts tun
        if b"aufzeichner_leiste.js" in inhalt:
            return                        # eine Vorlage bringt es schon mit
        stelle = treffer[-1].start()
        antwort.content = inhalt[:stelle] + self.schnipsel() + inhalt[stelle:]
        if antwort.has_header("Content-Length"):
            antwort["Content-Length"] = str(len(antwort.content))
