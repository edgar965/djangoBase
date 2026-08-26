# -*- coding: utf-8 -*-
u"""Die Kriterien des Review-Auftrags - und welches Werkzeug sie bedient.

Der Auftrag, aus dem Skills2 entstanden ist, nannte 14 Punkte. Zehn davon lassen
sich mechanisch prüfen; die übrigen vier NICHT - und das ist keine Lücke im
Werkzeugkasten, sondern eine Eigenschaft der Punkte selbst. Sie stehen hier
trotzdem, mit dem Weg, der bei ihnen funktioniert hat.

Wer die Liste in ein neues Projekt mitnimmt, hat damit beides: was ein Knopf
beantwortet und was Handarbeit bleibt.
"""

__all__ = ["KRITERIEN", "OHNE_WERKZEUG"]

#: KRITERIUM 13 STEHT NICHT MEHR HIER (16.08.2026): Es hat inzwischen eigene
#: Werkzeuge (``jsbefunde``, ``jsfaenger``). Ein Kriterium in BEIDEN Listen ist
#: ein Widerspruch - die Seite zeigte es dann als „ohne Werkzeug" an, während
#: darüber zwei standen. Abgesichert durch den Test
#: ``test_kriterien_ohne_werkzeug_sind_begruendet``.
#:
#: Nummer -> Wortlaut. Die Nummern stehen an den Werkzeugen (``kriterium``).
KRITERIEN = {
    1: "Möglichst alle Funktionen in Klassen kapseln",
    2: "Eine Klasse je Datei, höchstens 200–300 Zeilen",
    3: "JavaScript in ES-Module von höchstens ~200 Zeilen",
    4: "Objektorientierung – keine großen Dateien",
    5: "Ungenutzten und alten Code entfernen (keine Sicherungskopien)",
    6: "Keine Duplikate von Funktionen oder Klassen",
    7: "Keine abweichenden Namen für dieselbe Sache",
    8: "Keine Duplikate der ES-Module",
    9: "Klare Strukturen und Abhängigkeiten",
    10: "Datensatz mit mehr als drei Feldern, der seine Funktion verlässt → Klasse",
    11: "Dictionary mit mehr als drei festen Schlüsseln, das durch mehrere "
        "Funktionen gereicht wird → Klasse",
    12: "Performance prüfen und optimieren",
    13: "Tiefer Review – mindestens 1.000 Befunde",
    14: "Zweites Modell als Sparringspartner",
    15: "Alle Befunde beheben, nicht nur auflisten",
}

#: Kriterien ohne Knopf - mit dem Weg, der stattdessen getragen hat.
OHNE_WERKZEUG = [
    (8, "Keine doppelten ES-Module",
     "Zwei Module mit gleichem Zweck erkennt kein Fingerabdruck — sie sind "
     "selten zeichengleich. Praktikabel: Die Import-Prüfung (Kriterium 3) "
     "zeigt, welche Module überhaupt noch jemand lädt; was niemand importiert, "
     "ist der erste Verdacht."),
    (14, "Zweites Modell als Sparringspartner",
     "Nützlich, aber nicht als Autorität: Von acht Aussagen eines zweiten "
     "Modells war eine falsch — ausgerechnet zu der Stelle, an der wirklich ein "
     "Fehler saß. Hätte man sie übernommen, wäre eine Nicht-Regression "
     "„behoben“ worden. Der Wert lag im Zwang, jede Behauptung am Code "
     "nachzurechnen."),
]
