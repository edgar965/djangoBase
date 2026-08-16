# -*- coding: utf-8 -*-
u"""Lehren - was der Review-Durchgang gekostet hat, in Saetzen.

Jede Lehre steht hier mit dem FALL, aus dem sie stammt. Ohne den Fall ist eine
Regel eine Meinung; mit ihm kann man entscheiden, ob sie im eigenen Projekt
gilt. Die Haken auf der Seite sind eine Arbeitsliste - ab damit durchs naechste
Projekt.

Reihenfolge: erst die, die Fehler VERHINDERN, dann die, die beim Aufraeumen
helfen, dann die ueber Werkzeuge und Messungen.
"""

__all__ = ["LEHREN", "gruppen"]

#: (slug, gruppe, titel, was zu tun ist, der Fall dahinter)
LEHREN = [
    ("modulzustand", "Fehler verhindern",
     "Kein veränderlicher Zustand auf Modulebene",
     "Listen, Dicts und Sets auf Modulebene gelten für ALLE Anfragen "
     "gleichzeitig — der Entwicklungsserver ist multithreaded. Was eine Anfrage "
     "lang gelten soll, gehört in ein Objekt oder in threading.local.",
     "Eine Liste wurde in einer Datei gefüllt, in zwei anderen geleert und in "
     "einer vierten gelesen. Der mechanische Rechenweg leerte sie nie — er "
     "meldete Warnungen eines fremden, längst beendeten Laufs. Neun Zeilen "
     "darüber stand im Code, der Server sei multithreaded; direkt darunter, er "
     "bearbeite eine Anfrage nach der anderen."),

    ("dict-klasse", "Fehler verhindern",
     "Dictionary nur dort, wo es hinausgeht",
     "Mehr als drei feste Schlüssel und der Datensatz wandert durch mehrere "
     "Funktionen? Dann eine Klasse mit benannten Feldern. Geht er direkt als "
     "JSON hinaus oder liegt so in der Datenbank, bleibt es ein Dictionary — "
     "dann aber mit Vermerk, wohin.",
     "Ein Tippfehler in d[\"schlüssel\"] ist kein Fehler, den jemand sieht: Er "
     "legt still einen neuen Eintrag an, den nie jemand liest."),

    ("umleitung", "Fehler verhindern",
     "Umleitungen über vars(Klasse), nie über getattr",
     "Ein Klassenattribut zum Testen ersetzen und danach zurückschreiben: Der "
     "Originalwert muss aus vars(Klasse)[name] kommen. getattr packt "
     "staticmethod/classmethod aus — die Rückgabe macht daraus eine normale "
     "Methode.",
     "Ein Test stellte @staticmethod so „zurück“, dass ab da self mitgebunden "
     "wurde. Sichtbar wurde es zwei Tests später und NUR im vollen Suitenlauf: "
     "„nimmt 6 Argumente, bekam 7“. Vierter Fall derselben Klasse im Projekt."),

    ("test-messen", "Fehler verhindern",
     "Ein Testfeld ist nur grün, wenn gemessen wurde",
     "Findet ein Test seine Voraussetzung nicht vor (Börse zu, Gerät fehlt), ist "
     "er weder bestanden noch fehlgeschlagen. Dafür braucht die Suite einen "
     "dritten Zustand „nicht messbar“ — grün stellen ist eine Lüge, rot lassen "
     "eine falsche Anschuldigung.",
     "Ein Round-Trip-Test gegen die Börse war am Wochenende rot, weil kein "
     "Geld/Brief anlag. Der erste Reparaturversuch meldete ihn als bestanden — "
     "ein grünes Feld ohne jede Messung dahinter."),

    ("gegenprobe", "Fehler verhindern",
     "Zu jedem neuen Test eine Gegenprobe",
     "Nach dem Schreiben den geprüften Code absichtlich beschädigen und "
     "nachsehen, ob der Test rot wird. Erst dann weiß man, dass er etwas prüft.",
     "Eine Prüfung blieb grün, obwohl eine Methode gelöscht war: Sie rief nur 5 "
     "von 17 Aliasen auf, und der Betroffene war nicht dabei. Aufgefallen ist "
     "das nur durch die Gegenprobe."),

    ("dict-zu-klasse-bool", "Fehler verhindern",
     "Beim Ersetzen eines Dictionary durch eine Klasse: kein __bool__",
     "Ein Dictionary mit Inhalt ist immer wahr. Gibt die neue Klasse ein "
     "__bool__ mit „wahr, wenn erfolgreich“, kehren sich alle Prüfungen der Form "
     "``if fehler:`` still um. Wer wissen will, ob es geklappt hat, fragt ein "
     "Feld — nicht das Objekt.",
     "Genau das ist beim Umbau eines Live-Orderpfads passiert: Das "
     "Fehler-Ergebnis war „falsch“, der Fehlerzweig wurde übersprungen, und der "
     "Code setzte eine Stop-Klammer auf eine Position, die es nicht gab. Zwölf "
     "von 35 Prüfpunkten eines Attrappen-Werkzeugs wurden rot — ohne das "
     "Werkzeug hätte es niemand vor dem nächsten echten Trade gemerkt."),

    ("import-am-kopf", "Fehler verhindern",
     "Code außerhalb des Django-Projekts nur SPÄT importieren",
     "Liegt ein Paket neben dem Django-Projekt (und nicht darin), steht es beim "
     "Laden der Apps noch nicht im Pfad. Ein Import am Dateikopf eines Moduls, "
     "das AppConfig.ready() lädt, killt den ganzen Server. Import in die "
     "Funktion ziehen — die Nachbarmodule machen es meist schon so.",
     "Genau so ist der Entwicklungsserver für zehn Minuten ausgefallen: ein "
     "sauberer Import am Dateikopf, „No module named depot“, und die "
     "Erreichbarkeitsprüfung davor war wertlos, weil sie den Pfad selbst gesetzt "
     "hatte. Was zählt, ist ``manage.py check`` ohne eigene sys.path-Tricks."),

    ("aufteilen", "Aufräumen",
     "Aufteilen mit Netz: Methodenliste vorher/nachher",
     "Beim Zerlegen einer großen Datei vor und nach dem Schnitt die Liste der "
     "Methoden/Funktionen vergleichen. Was verschwunden ist, muss bewusst "
     "verschoben worden sein.",
     "Beim Aufteilen eines 427-Zeilen-Moduls wurde eine Methode mitgelöscht, "
     "weil sie zwischen zwei ausgeschnittenen Blöcken lag. Kein bestehender "
     "Test sah es; der Fehler wäre erst beim Klick des Nutzers gekommen."),

    ("marker", "Aufräumen",
     "Begründung in den Code, nicht in die Ausnahmeliste",
     "Wenn ein Prüfwerkzeug eine absichtliche Stelle meldet, gehört die "
     "Begründung als Vermerk NEBEN die Stelle („geteilt gewollt: …“). Eine "
     "Ausnahmeliste im Werkzeug rät, was der Autor gemeint hat.",
     "Ein Prüfwerkzeug mit eigener Ausnahmeliste erklärte einmal 122 lebende "
     "Namen für tot und wollte 404 Dateien löschen, aus denen 53 Werkzeuge "
     "lesen."),

    ("duplikate", "Aufräumen",
     "Duplikate zusammenlegen — aber Signaturen prüfen",
     "Zeichengleiche Rümpfe sind ein Fund, keine Anweisung. Zwei Kopien können "
     "verschiedene Signaturen und Aufrufer haben; beim Zusammenlegen jeden "
     "Aufrufer einmal fahren.",
     "Vier Werkzeuge trugen denselben Ablauf. Als der geprüfte Code umgebaut "
     "wurde, lief einer davon ins Leere — drei Tage lang eine Sicherung, die "
     "keine mehr war."),

    ("generiert", "Aufräumen",
     "Generierte Ordner nie bearbeiten",
     "Ordner, die ein Werkzeug bei jedem Lauf neu schreibt, sehen aus wie "
     "Quellcode und tauchen in jeder Suche auf. Sie brauchen eine LIESMICH mit "
     "Verweis auf die echte Quelle.",
     "Eine Änderung landete im gespiegelten Arbeitsordner der Node-Tests. Der "
     "nächste Testlauf hätte sie kommentarlos gelöscht."),

    ("werkzeug-index", "Werkzeuge",
     "Prüfwerkzeuge: ein Durchlauf, dann nachschlagen",
     "Ein Werkzeug, das je Fundstelle alle Dateien erneut durchsucht, ist "
     "quadratisch und läuft in Zeitüberschreitungen. Erst alles einmal lesen und "
     "indizieren, dann nachschlagen.",
     "Die erste Fassung der Modulzustand-Prüfung brauchte über 120 Sekunden und "
     "brach ab — sie machte genau den Fehler, den sie anderswo meldet."),

    ("dateiuebergreifend", "Werkzeuge",
     "Prüfungen dateiübergreifend anlegen",
     "Wer nur innerhalb einer Datei sucht, findet die interessanten Fälle nicht: "
     "Der Zustand wird in Datei A angelegt, in B verändert und in C gelesen.",
     "Die erste Fassung suchte Mutationen nur in derselben Datei und ließ genau "
     "den Fall durch, für den sie gebaut worden war."),

    ("laufzeit-test", "Werkzeuge",
     "Ein Ladetest gegen eine DOM-Attrappe",
     "Quelltext-Prüfungen sehen nicht, ob ein Browser-Modul überhaupt "
     "durchläuft. Eine kleine DOM-Attrappe in Node (getElementById, fetch, "
     "localStorage) reicht, um „Seite tot“ von „Seite da“ zu unterscheiden.",
     "Genau dieser Test fand die beim Aufteilen mitgelöschte Methode — "
     "zwanzig Minuten, nachdem sie verschwunden war."),

    ("zahlen-quelle", "Messen",
     "Keine Zahl ohne Messung dahinter",
     "Jede angezeigte Kennzahl braucht eine nachvollziehbare Quelle. Zahlen aus "
     "einer Erinnerung oder aus einem Text abgeschrieben sind der häufigste "
     "Grund für falsche Entscheidungen.",
     "Vier angezeigte Kennzahlen hatten keine Messung dahinter — eine "
     "beschrieb einen einzigen Tag, eine andere war aus bitgleichen Zeilen "
     "gerechnet."),

    ("keine-phantasie", "Messen",
     "Begründungen messen, nicht erfinden",
     "Wer eine Entscheidung mit einer Verhaltensbehauptung begründet („das "
     "gewöhnt an …“), muss sie belegen können. Sonst ist es eine Rationalisierung "
     "für das, was man ohnehin tun wollte.",
     "Ein rot bleibender Test wurde mit einer erfundenen Begründung grün "
     "gestellt. Der Satz klang plausibel und hatte nichts hinter sich."),
]


def gruppen():
    """[(Gruppenname, [Lehre, …])] in der Reihenfolge von LEHREN."""
    aus, index = [], {}
    for slug, gruppe, titel, tun, fall in LEHREN:
        if gruppe not in index:
            index[gruppe] = []
            aus.append((gruppe, index[gruppe]))
        index[gruppe].append({"slug": slug, "titel": titel, "tun": tun, "fall": fall})
    return aus
