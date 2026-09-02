# -*- coding: utf-8 -*-
u"""djangoBase prüft seine EIGENEN Tabellen mit den Regeln, die es aufstellt.

DIE LÜCKE (Edgar, 01.09.2026)
=============================
    „warum hat der Code Review nicht zugeschlagen? Es gibt einen für doppelten
     Code und einen ob die djangoBase tabellentemplates überall genutzt werden?"

Weil beide Werkzeuge die Datei gar nicht sehen. Gemessen an jenem Tag:

    HTML-Dateien im Prüfbereich von shortlongx:  112
    davon aus djangoBase:                          0

``skills.werkzeug.wurzel()`` ist das Projekt-Repo; djangoBase liegt als
editable Install daneben. Und ``konform/quellen.py`` nimmt das Paket sogar
ausdrücklich heraus - mit gutem Grund: Sonst meldeten alle sechs Konsumenten
dieselben Befunde, sechsmal.

Die Folge war trotzdem, dass **der Code mit der größten Reichweite die
geringste Deckung hatte**. Auf ``/hilfe/ki-modelle/`` - einer djangoBase-Seite -
sortierte die Parameter-Spalte sichtbar falsch, und drei Prüfwerkzeuge sahen
sie nie an.

WAS DIESER TEST TUT
===================
Er wendet dieselben zwei Regeln (``class="sortable"``, ``data-sort-key``) auf
die Vorlagen des PAKETS an - und läuft damit genau einmal, im Konsumenten, der
gerade testet. Das ist die richtige Stelle: djangoBase hat kein eigenes
``manage.py``.

WARUM NICHT DIE KONSUMENTEN-AUSNAHME AUFHEBEN
=============================================
Weil sie richtig ist. Ein Projekt soll für den Fremdcode in seinem
``site-packages`` nicht verantwortlich sein. Was fehlte, war nicht die
Aufhebung der Ausnahme, sondern ihr Gegenstück.
"""
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.tests.konform.quellen import TABU
from djangobase.tests.konform.test_tabellen import (_KLASSEN, datentabellen)

#: Wurzel des Pakets - dieselbe Rechnung wie ``quellen.PAKET``.
PAKET = Path(__file__).resolve().parents[2]

#: Wie in ``test_tabellen``: Tabellen, deren ZEILENFOLGE die Aussage ist.
ORDNUNG_ZAEHLT = "data-sort-aus"


def _eigene_vorlagen():
    u"""Alle HTML-Vorlagen des djangoBase-Pakets."""
    aus = []
    for pfad in PAKET.rglob("*.html"):
        if any(teil in TABU for teil in pfad.parts):
            continue
        aus.append(pfad)
    return aus


class EigeneTabellenTest(SimpleTestCase):
    u"""Was djangoBase von seinen Konsumenten verlangt, gilt für es selbst."""

    databases = []

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.vorlagen = _eigene_vorlagen()
        cls.tabellen = datentabellen(cls.vorlagen)

    def test_es_gibt_eigene_vorlagen(self):
        u"""GEGENPROBE ZUERST. Findet der Sammler nichts, prüfen die Regeln
        unten nichts - und ein grüner Haken hieße nur, dass niemand hinsieht.

        Genau diese Sorte stiller Blindheit ist der Anlass dieses Tests."""
        self.assertGreater(len(self.vorlagen), 10,
                           u"keine Paket-Vorlagen gefunden - stimmt PAKET noch?")

    def test_eigene_datentabellen_sind_sortierbar(self):
        u"""Jede Datentabelle des Pakets trägt ``class="sortable"``."""
        ohne = [(p, a) for p, a in self.tabellen
                if "sortable" not in " ".join(_KLASSEN.findall(a)).lower().split()
                and ORDNUNG_ZAEHLT not in a.lower()]
        self.assertEqual(
            ohne, [], u"%d Tabellen in djangoBase ohne class=\"sortable\":\n  %s"
            % (len(ohne), "\n  ".join("%s: <table %s>" % (Path(p).name, a[:60].strip())
                                      for p, a in ohne[:8])))

    def test_eigene_datentabellen_merken_die_breiten(self):
        u"""Jede Datentabelle des Pakets trägt ``data-sort-key``.

        Ohne ihn sortiert die Tabelle zwar, aber die Spaltenbreiten werden
        nicht gemerkt - die stille Sorte Abweichung, bei der nichts kaputt
        aussieht und die halbe Bedienung fehlt."""
        ohne = [(p, a) for p, a in self.tabellen if "data-sort-key" not in a.lower()]
        self.assertEqual(
            ohne, [], u"%d Tabellen in djangoBase ohne data-sort-key:\n  %s"
            % (len(ohne), "\n  ".join("%s: <table %s>" % (Path(p).name, a[:60].strip())
                                      for p, a in ohne[:8])))
