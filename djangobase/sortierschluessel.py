# -*- coding: utf-8 -*-
u"""Sortierschluessel — eine Zahl so schreiben, wie die Tabelle sie liest.

DER BEFUND (05.09.2026, Werkzeug ``sortierwerte``)
==================================================
``data-sort`` traegt den Rohwert, damit die Spalte nach der ZAHL sortiert
und nicht nach dem angezeigten Text. Nur: ``tabellen_sortierung._zahl``
liest **deutsch** — Komma trennt die Dezimalen, JEDER Punkt gilt als
Tausenderzeichen und fliegt raus.

Ein Python-Float landet aber als ``0.3`` im Attribut. Daraus wird 3.
Gemessen an zwei Stellen:

* Hilfe -> KI-Modelle, Kosten je Frage: ``0.3`` -> 3, und
  ``0.019000000000000003`` -> eine siebzehnstellige Zahl. Die teuerste
  Zeile stand unten.
* Hilfe -> Tests, Dauer: ``0.379`` -> 379. Ein Testlauf von 0,4 Sekunden
  galt als der langsamste der Seite.

WARUM EIN EIGENES MODUL
=======================
Es gibt zwei Erzeuger von ``data-sort``: die Vorlagen (ueber den Filter
``sortzahl``) und ``testtabelle._zellen_html`` in Python. Zwei Kopien
derselben Regel laufen auseinander, sobald eine angefasst wird — genau
die Fehlerklasse, gegen die dieses Modul geschrieben ist. Die Regel steht
deshalb EINMAL hier, und beide Seiten fragen sie.

UNTERSCHIED ZU ``sortwert``
===========================
``templatetags.zahlen.sortwert`` rechnet ``137M`` auf Milliarden um; er
ist fuer Parameterzahlen da. Hier kommt eine fertige Zahl an und wird nur
lesbar aufgeschrieben.
"""

__all__ = ['Sortierschluessel']


class Sortierschluessel:
    u"""Wandelt einen Wert in das Format, das die Sortierung versteht."""

    #: Mehr Nachkommastellen braucht keine Sortierung — und es schneidet
    #: zugleich das Fliesskomma-Rauschen ab: ``0.019000000000000003``
    #: wird ``0,019`` statt einer siebzehnstelligen Zahl.
    STELLEN = 9

    @staticmethod
    def aus(wert):
        u"""Der Attributwert zu ``wert``.

        * ``None`` und Leerstring bleiben leer — das heisst der Sortierung
          „kein Wert" und stellt die Zeile ans Ende. Ein Gedankenstrich
          waere Text und sortierte zwischen die Zahlen.
        * Text bleibt unveraendert: Eine Note, ein ISO-Datum oder ein
          Modellname sortieren als Zeichenkette voellig richtig.
        * Eine Ganzzahl kommt ohne Komma zurueck.
        """
        if wert is None or wert == '':
            return ''
        try:
            zahl = float(wert)
        except (TypeError, ValueError):
            return wert
        # `%f` statt `str()`: `str(1e-06)` waere `1e-06` — fuer die
        # Sortierung unlesbar, und zwar still.
        text = ('%.*f' % (Sortierschluessel.STELLEN, zahl)).rstrip('0')
        text = text.rstrip('.')
        return (text or '0').replace('.', ',')
