# -*- coding: utf-8 -*-
u"""Eine Sperrklinke für Befunde — damit „grün" auch das Projekt meint.

DIE FRAGE (Edgar, 26.08.2026)
============================
    „wie kann es sein, dass die Code-Review-Tests alles grün melden, und du
     noch hunderte freier Funktionen hast usw??"

Nachgemessen, und die Antwort war unbequem: **Die Prüfungen prüfen die
Werkzeuge, nicht das Projekt.** Von dreizehn Skills-Prüfmodulen fahren elf
gegen gestellte Fälle in einem Wegwerf-Ordner. Die zwei, die
``settings.BASE_DIR`` anfassen, biegen es per ``override_settings`` auf ein
leeres ``MiniProjekt()`` um und prüfen dort::

    „Ein Projekt ohne Code darf kein Werkzeug zum Absturz bringen"
    „Jede Ergebniszeile hat alle Spalten"

Und keiner der zwölf Grundtests fährt überhaupt ein Prüfwerkzeug.

„Grün" hiess damit: *die Werkzeuge funktionieren und sehen ihre eigenen
Testfälle*. Es hiess nie: *das Projekt ist sauber*. Gemessen an CamTrack am
26.08.2026 standen dahinter über fünfhundert gemeldete Befunde.

`anlassfall-check` beantwortet die Frage „**sieht** das Werkzeug noch
etwas?". Diese Datei beantwortet die andere: „**ist** noch etwas da?"

WARUM EINE SPERRKLINKE UND KEINE NULL
=====================================
Null wäre bei 830 Funktionen auf Modulebene weder heute noch nächste Woche
erreichbar, und eine Prüfung, die dauerhaft rot ist, wird ignoriert — dann
wäre nichts gewonnen. Die Klinke schreibt den heutigen Stand fest und wird
rot, sobald eine Zahl **steigt**. Jede Verbesserung zieht die Grenze nach.

Der Preis: Wer eine neue Datei anlegt, bringt deren Befunde mit und muss
die Grenze bewusst hochsetzen. Das ist gewollt — genau dieser Moment ist
die Gelegenheit, es stattdessen richtig zu machen.

EINRICHTUNG (im Wirtsprojekt)
=============================
    DJANGOBASE = {
        "befundgrenzen": {
            "altlast": 0,
            "freie-funktionen": 285,
            "code-qualitaet": {"fehler": 5, "warnung": 13},
        },
    }

Der Wert ist entweder eine Zahl (Obergrenze für ALLE Befunde) oder ein
Wörterbuch je Gewicht. Ohne Eintrag prüft diese Datei nichts und sagt es —
gelb, nicht grün.
"""
from django.test import SimpleTestCase

from .conf import conf


def _zahl(werkzeug):
    u"""Wie viele Befunde meldet dieses Werkzeug — und welchen Gewichts?

    Beide Bauarten: ``BefundWerkzeug`` liefert einen ``Befundsatz`` über
    ``pruefen()``, die älteren ein ``Ergebnis`` über ``laufen()``. Dieselbe
    Verwechslung hat schon den Läufer im Wirtsprojekt abstürzen lassen und
    den Anlassfall-Sammellauf an den Fixern vorbeigehen lassen.
    """
    if hasattr(werkzeug, 'pruefen'):
        satz = werkzeug.pruefen()
        je_gewicht = {}
        for befund in satz.befunde:
            je_gewicht[befund.gewicht] = je_gewicht.get(befund.gewicht, 0) + 1
        return len(satz.befunde), je_gewicht
    ergebnis = werkzeug.laufen()
    return len(ergebnis.zeilen), {}


class GrundtestBefundgrenzen(SimpleTestCase):
    u"""Kein Werkzeug darf mehr melden als beim letzten Festschreiben."""

    def test_kein_werkzeug_ueberschreitet_seine_grenze(self):
        from .skills import werkzeug_finden

        grenzen = conf().get('befundgrenzen') or {}
        if not grenzen:
            self.skipTest(
                'Keine Befundgrenzen gesetzt. Ohne DJANGOBASE'
                '["befundgrenzen"] sagt ein gruener Lauf nur, dass die '
                'Werkzeuge laufen — nicht, dass das Projekt sauber ist.')

        ueber, gelaufen = [], []
        for slug, grenze in sorted(grenzen.items()):
            werkzeug = werkzeug_finden(slug)
            if werkzeug is None:
                ueber.append('%s: gibt es nicht (mehr)' % slug)
                continue
            gesamt, je_gewicht = _zahl(werkzeug)
            gelaufen.append('%-22s %4d' % (slug, gesamt))
            if isinstance(grenze, dict):
                for gewicht, hoechstens in sorted(grenze.items()):
                    ist = je_gewicht.get(gewicht, 0)
                    if ist > hoechstens:
                        ueber.append('%s: %d %s, erlaubt %d'
                                     % (slug, ist, gewicht, hoechstens))
            elif gesamt > int(grenze):
                ueber.append('%s: %d Befunde, erlaubt %d'
                             % (slug, gesamt, int(grenze)))

        # Immer drucken, auch wenn alles passt: Eine Zahl, die nur im
        # Fehlerfall sichtbar wird, kann man nicht kleiner werden sehen.
        print('\nBefundgrenzen:\n  ' + '\n  '.join(gelaufen))

        if ueber:
            self.fail(
                '%d Werkzeug(e) melden mehr als festgeschrieben:\n  %s\n\n'
                'Entweder beheben — oder die Grenze in DJANGOBASE'
                '["befundgrenzen"] bewusst hochsetzen. Stillschweigend '
                'wachsen soll sie nicht.'
                % (len(ueber), '\n  '.join(ueber)))


__all__ = ['GrundtestBefundgrenzen']
