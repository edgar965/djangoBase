# -*- coding: utf-8 -*-
u"""Seitenwurzeln — wie viele Objekte erzeugt eine Vorlage selbst?

DERSELBE MASSSTAB WIE IM BACKEND, ANDERE HAELFTE
================================================
    „ein gutes Objektmodell fängt mit einer Klasse an, und verzweigt immer
     weiter über Instanzen" (Edgar, 23.08.2026)

``objektwurzeln`` misst das fuer Python. Dieses Werkzeug stellt dieselbe
Frage ans Frontend: Wie viele Objekte erzeugt eine HTML-Vorlage in ihrem
Inline-Skript, statt EINE Seiten-Klasse zu bauen, die den Rest haelt?

NACHGEMESSEN AN CAMTRACK (23.08.2026)
=====================================
    JS-Klassen im Projekt              175
      aus VORLAGEN erzeugt              16   <- die Wurzeln der Seite
      nur aus Modulen erzeugt          157   <- haengen an einem Ast

    form.html          18 Aufrufe
    base.html          10
    live_view.html      9
    live_calendar.html  4

Die 157 sind in Ordnung. Das Problem sind die Vorlagen: ``live_view.html``
erzeugt neun Objekte nebeneinander — ``GridDragReorder``,
``FocusWidthSlider``, ``setupTrefferBar``, ``setupGlobalTimeline``,
``setupZeitbereiche``, ``setupStromWache``, ``PersonsStrip``,
``ReclusterControls``. Jedes ist eine eigene Wurzel.

WORAN MAN DIE FOLGEN SIEHT
==========================
Die Abhaengigkeiten zwischen diesen neun stehen nirgends — sie werden mit
Wartezeiten geraten::

    setupZeitbereiche({...});                   // „ERST er, DANN die Leiste"
    setTimeout(() => setupStromWache(...), 2000);
    setTimeout(() => { setupGlobalTimeline({...}); }, 100);

Und die Fehler dazu sind belegt: Am 21.08.2026 liefen Zeitleiste und
Kachel-Leisten mit ZWEI Abrufen auseinander („unten ganz viele Treffer, bei
den Kacheln ganz wenige"), am 23.08.2026 fiel der Sprung zwischen Treffern
an den Anfang zurueck, weil der Zustand am DOM hing statt an einem Objekt.

WIE ES AUSSAEHE
===============
Eine Seiten-Klasse haelt die Teile, und die Reihenfolge steht im
Konstruktor statt in einem ``setTimeout``::

    export class LiveAnsichtSeite {
        constructor(wurzel) {
            this.zeitbereich = new Zeitbereich(wurzel);          // erst er
            this.zeitleiste  = new Zeitleiste(this.zeitbereich); // dann sie
            this.leisten     = new TrefferLeisten(this.zeitbereich);
        }
    }

Die Vorlage enthaelt dann eine Zeile.
"""

import re

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug


class Seite:
    u"""Eine Vorlage und das, was sie selbst erzeugt."""

    __slots__ = ('pfad', 'wurzeln', 'wartezeiten')

    def __init__(self, pfad, wurzeln, wartezeiten):
        self.pfad = pfad
        #: ``[(name, zeile)]`` — was das Inline-Skript erzeugt.
        self.wurzeln = wurzeln
        #: Zahl der ``setTimeout``, mit denen eine Reihenfolge geraten wird.
        self.wartezeiten = wartezeiten

    @property
    def gewicht(self):
        # Wartezeiten sind der Beweis, dass die Reihenfolge nirgends steht.
        if self.wartezeiten:
            return Befund.WARNUNG
        return Befund.HINWEIS


class Seitenwurzeln(BefundWerkzeug):

    slug = 'seitenwurzeln'
    kriterium = 4
    titel = 'Wurzeln je Seite (Frontend)'
    zweck = ('Zählt, wie viele Objekte eine HTML-Vorlage selbst erzeugt. '
             'Idealwert: EINE Seiten-Klasse, die den Rest hält.')
    abhilfe = ('Eine Klasse je Seite anlegen, die die Teile im Konstruktor '
               'hält — dann steht die Reihenfolge dort statt in einem '
               '`setTimeout`. Die Vorlage enthält danach eine Zeile.')
    befund = ('CamTrack: `live_view.html` erzeugt neun Objekte nebeneinander '
              'und raet ihre Reihenfolge mit zwei `setTimeout`. Am '
              '21.08.2026 liefen dadurch Zeitleiste und Kachel-Leisten mit '
              'zwei Abrufen auseinander.')
    dauer = 'Sekunden'
    eingabe = ('ab', 'Ab wie vielen Wurzeln je Seite melden?', '1')

    #: ``new Klasse(`` — der offensichtliche Fall.
    NEU = re.compile(r'new\s+([A-Z]\w+)\s*\(')

    #: ``setupX(`` / ``startX(`` am Zeilenanfang — die Fabrik-Schreibweise,
    #: die in diesem Projekt ueblich ist. Ohne sie zaehlt das Werkzeug
    #: ``live_view.html`` mit zwei statt neun Wurzeln.
    FABRIK = re.compile(r'^\s*(setup[A-Z]\w+|start[A-Z]\w+)\s*\(', re.M)

    #: Bausteine des Browsers — keine eigenen Klassen. Ohne diese Liste
    #: meldet das Werkzeug `new Date()` als Wurzel des Objektmodells.
    FREMD = frozenset({
        'Date', 'URL', 'URLSearchParams', 'CustomEvent', 'Event', 'Map',
        'Set', 'WeakMap', 'WeakSet', 'Promise', 'Image', 'Audio', 'Blob',
        'FormData', 'Headers', 'Request', 'Response', 'AbortController',
        'IntersectionObserver', 'ResizeObserver', 'MutationObserver',
        'Intl', 'RegExp', 'Error', 'TextDecoder', 'TextEncoder',
        'MediaSource', 'RTCPeerConnection', 'WebSocket', 'Worker',
    })

    #: Eine geratene Reihenfolge.
    WARTEN = re.compile(r'setTimeout\s*\(')

    #: Vorlagen, die keine Seiten sind: Bausteine ohne eigenes Skript-Ende.
    TEILE_AUS = ('_teil_', '_list_content', '_person_card', '_sidebar',
                 '_live_calendar_pane')

    anlassfall = Anlassfall(
        {"seite.html": (
            "{% block content %}\n"
            "<script type=\"module\">\n"
            "  const a = new Gitter(document);\n"
            "  const b = new Leiste(document);\n"
            "  setupZeitbereich({});\n"
            "  setTimeout(() => setupLeiste({}), 100);\n"
            "</script>\n"
            "{% endblock %}\n")},
        mindestens=1, erwartet_in="seite.html",
        warum="`live_view.html` in CamTrack erzeugt neun Objekte "
              "nebeneinander und raet ihre Reihenfolge mit zwei `setTimeout` "
              "— am 21.08.2026 liefen Zeitleiste und Kachel-Leisten deshalb "
              "mit zwei getrennten Abrufen auseinander")

    # ---------------------------------------------------------------- Ablauf
    def pruefen(self, ab='1', **_argumente):
        try:
            grenze = max(0, int(str(ab).strip() or 1))
        except ValueError:
            grenze = 1

        seiten, vorlagen = [], 0
        for pfad in self.projektdateien('.html'):
            if any(teil in pfad.name for teil in self.TEILE_AUS):
                continue
            try:
                text = pfad.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            vorlagen += 1
            wurzeln = self._wurzeln(text)
            if not wurzeln:
                continue
            seiten.append(Seite(self.kurz(pfad), wurzeln,
                                len(self.WARTEN.findall(text))))

        seiten.sort(key=lambda s: (s.gewicht != Befund.WARNUNG,
                                   -len(s.wurzeln), s.pfad))
        gesamt = sum(len(s.wurzeln) for s in seiten)
        kopf = [
            '%d Vorlagen geprüft, %d erzeugen selbst Objekte' % (vorlagen,
                                                                  len(seiten)),
            '%d Wurzeln insgesamt, %d Wartezeiten zum Raten der Reihenfolge'
            % (gesamt, sum(s.wartezeiten for s in seiten)),
            'Idealwert: EINE Seiten-Klasse je Vorlage',
        ]
        befunde = [self._befund(s) for s in seiten
                   if len(s.wurzeln) > grenze]
        return Befundsatz(self.titel, kopf, befunde)

    def _wurzeln(self, text: str) -> list:
        u"""``[(name, zeile)]`` — was diese Vorlage selbst erzeugt."""
        raus = []
        for treffer in self.NEU.finditer(text):
            if treffer.group(1) in self.FREMD:
                continue
            raus.append((treffer.group(1),
                         text.count('\n', 0, treffer.start()) + 1))
        for treffer in self.FABRIK.finditer(text):
            raus.append((treffer.group(1),
                         text.count('\n', 0, treffer.start()) + 1))
        return raus

    @staticmethod
    def _befund(seite: Seite) -> Befund:
        namen = ', '.join(n for n, _z in seite.wurzeln[:4])
        was = ('%s erzeugt %d Objekte selbst (%s%s)'
               % (seite.pfad, len(seite.wurzeln), namen,
                  ', …' if len(seite.wurzeln) > 4 else ''))
        if seite.wartezeiten:
            warum = ('Dazu %d mal `setTimeout` — die Reihenfolge zwischen '
                     'ihnen steht nirgends und wird mit Wartezeiten geraten. '
                     'Eine Seiten-Klasse hält sie im Konstruktor.'
                     % seite.wartezeiten)
        else:
            warum = ('Jedes davon ist eine eigene Wurzel. Eine Seiten-Klasse '
                     'hält sie, und die Vorlage enthält eine Zeile.')
        return Befund(seite.pfad, was, warum, seite.gewicht)


__all__ = ['Seitenwurzeln', 'Seite']
