# -*- coding: utf-8 -*-
u"""Umbau - Werkzeuge, die Quelltext AENDERN (keine Web-Knoepfe).

Warum nicht in ``skills2``: Die Werkzeuge dort messen und melden. Diese hier
schreiben Dateien. Ein Knopf auf einer Hilfe-Seite, der 30 Dateien umschreibt,
ist keine gute Idee - deshalb laufen sie ueber die Kommandozeile, mit
Probelauf als Vorgabe.

DIE VIER UMSTELLER (viele Dateien in einem Lauf):

    python -m djangobase.umbau.serverabrufe <wurzel>              # Probelauf
    python -m djangobase.umbau.serverabrufe <wurzel> --schreiben
    python -m djangobase.umbau.protokoll <wurzel> --schreiben
    python -m djangobase.umbau.jsimporte Protokoll datei.js …
    python -m djangobase.umbau.stilklassen vorlage.html --schreiben

DER WERKZEUGKASTEN FUER EINEN SCHNITT (eine Datei, mehrere Schritte):

    python -m djangobase.umbau.strukturbericht gross.py       # 1. was steht drin
    python -m djangobase.umbau.aufrufgraph gross.py           # 2. wer ruft wen
    python -m djangobase.umbau.modulschneider gross.py neu.py --namen=a,b
    python -m djangobase.umbau.exportlisten datei.js          # 3. danach aufraeumen
    python -m djangobase.umbau.unbekanntenamen <ordner>       # 4. Gegenprobe
    python -m djangobase.umbau.fabrikklasse fabrik.js Name    # nur Bericht

`KlassenBauer` hat bewusst KEINE Kommandozeile: Er braucht die Zuordnung
Funktionsname -> Methodenname, und die gehoert ins Aufrufskript, nicht in ein
Flag. `Fabrikumbau` berichtet nur, was eine Klasse waere — geschrieben wird von
Hand, weil eine Closure-Fabrik zu viele Sonderfaelle hat.

REIHENFOLGE, warum diese: Erst ansehen (`strukturbericht`, `aufrufgraph`), dann
schneiden (`modulschneider`/`klassenbauer` fuer Python, `fix_jsschnitt` in
``skills2`` fuer JavaScript), dann die Folgeschaeden beheben
(`exportlisten` — ein Name in der Exportliste, dessen Definition umgezogen ist,
laesst das ganze Modul mit „Export 'x' is not defined" scheitern), und zuletzt
gegenprobieren (`unbekanntenamen` findet Bezeichner, die nirgends deklariert und
nicht importiert sind — die Fehlerklasse aus
``~/.claude/rules/es-module-stumme-fehler.md``, die keine Ausnahme wirft).

`codesicht`, `strukturbericht` und `kommateilung` sind die Grundlagen, auf denen
die anderen aufsetzen: `Codesicht` blendet Kommentare und Zeichenkettenrumpf aus,
ohne mit `re.sub` an einem Apostroph in einer Vorlage zu zerbrechen.

ENTSTANDEN im 3DTools-Durchgang (16.08.2026), wo sie zusammen 144 Stellen
umgestellt haben: 125 ungepruefte `fetch`-Aufrufe und 133 `console.log`.

VORAUSSETZUNG im Zielprojekt: die beiden Frontend-Klassen `Serverabruf`
(Statuspruefung, CSRF, POST-Helfer) und `Protokoll` (debug/info/warnung/fehler
mit Schalter). Die Umsteller schreiben die Importe darauf - ohne die Klassen
laufen die Seiten danach nicht. Vorlagen dafuer stehen in
``djangobase/static/djangobase/js/``.

REIHENFOLGE, die sich bewaehrt hat:
1. Probelauf, Liste der „braucht Handarbeit"-Stellen lesen.
2. Mit ``--schreiben`` laufen lassen.
3. `skills2.JsSyntax` laufen lassen (findet kaputte Importe, die `node --check`
   auf `.js` uebersieht).
   Beim Stil-Umbau stattdessen `static/djangobase/js/stilmessung.js`: VOR dem
   Lauf im Browser messen, danach vergleichen. Eine CSS-Klasse hat eine
   niedrigere Spezifitaet als ein Inline-Stil — zwei Regressionen sind auf
   genau diesem Weg aufgefallen und waeren sonst niemandem aufgefallen.
4. Testsuite und die betroffenen Seiten im Browser pruefen.
"""

#: Klasse -> Modul. Wird BEI BEDARF geladen, siehe `__getattr__`.
KLASSEN = {
    "Aufrufgraph": "aufrufgraph",
    "Codesicht": "codesicht",
    "Exportlisten": "exportlisten",
    "Fabrikumbau": "fabrikklasse",
    "Importblock": "jsimporte",
    "KlassenBauer": "klassenbauer",
    "Kommateilung": "kommateilung",
    "ModulSchneider": "modulschneider",
    "Modulnamen": "unbekanntenamen",
    "ProtokollUmstellung": "protokoll",
    "ServerabrufUmstellung": "serverabrufe",
    "Stilklassen": "stilklassen",
    "Strukturbericht": "strukturbericht",
}

__all__ = sorted(KLASSEN)


def __getattr__(name):
    u"""Modul erst laden, wenn seine Klasse gebraucht wird (PEP 562).

    WARUM NICHT OBEN IMPORTIEREN (17.08.2026): Wer ein Modul im ``__init__``
    importiert, laesst ``python -m djangobase.umbau.<modul>`` es ZWEIMAL laden —
    einmal als Paketmitglied, einmal als ``__main__``. Python warnt davor
    (``RuntimeWarning: found in sys.modules after import of package``), und die
    Warnung stand vor der eigentlichen Ausgabe des Werkzeugs. Bei Werkzeugen,
    die Dateien schreiben, ist doppelt ausgefuehrter Modulcode kein Schoenheits-
    fehler. So bleibt ``from djangobase.umbau import Codesicht`` moeglich, ohne
    dass der Kommandozeilenaufruf darunter leidet.
    """
    modul = KLASSEN.get(name)
    if modul is None:
        raise AttributeError("djangobase.umbau hat kein %r" % name)
    from importlib import import_module
    return getattr(import_module("." + modul, __name__), name)


def __dir__():
    return sorted(KLASSEN)
