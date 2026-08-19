"""Lehren — die Regeln, die aus einem Review-/Umbaudurchgang haengengeblieben sind.

Jede Lehre ist ankreuzbar (Vorgabe: an) und gilt dann als Regel fuer dieses
Projekt. Die Seite baut daraus einen fertigen Auftragstext, den man einem
Modell oder einem Menschen als Arbeitsgrundlage geben kann — darum geht es:
nicht bei null anfangen.

Gespeichert wird in einer eigenen JSON-Datei neben `.djangobase.json`. Bewusst
NICHT im Einstellungs-Store: Dessen Werte sind eine feste Whitelist von
Layout-Optionen; die Lehren sind Projektinhalt und sollen sich frei erweitern
lassen, ohne dass jemand die Whitelist pflegt.
"""

import json
from pathlib import Path

from django.conf import settings


class Lehre:
    """Eine Regel mit Begruendung und Beleg."""

    __slots__ = ('slug', 'titel', 'regel', 'warum', 'beleg', 'bereich')

    def __init__(self, slug, titel, regel, warum, beleg='', bereich='Allgemein'):
        self.slug = slug
        self.titel = titel
        #: Was zu tun ist — eine Zeile, im Imperativ.
        self.regel = regel
        #: Warum das so ist. Ohne Begruendung wird eine Regel beim ersten
        #: Widerstand fallengelassen.
        self.warum = warum
        #: Was es konkret gebracht hat. Zahlen ueberzeugen, Behauptungen nicht.
        self.beleg = beleg
        self.bereich = bereich


BEREICHE = ['Struktur', 'Datenmodell', 'Django', 'Performance', 'numpy',
            'Frontend', 'Vorgehen']

#: Die Lehren aus dem Durchgang, der diesen Werkzeugkasten hervorgebracht hat
#: (3DTools, August 2026). Reihenfolge: nach Bereich, innerhalb nach Nutzen.
LEHREN = [
    Lehre('klassen-statt-dicts',
          'Datensatz mit mehr als drei Feldern → eigene Klasse',
          'Verlaesst ein Dictionary mit mehr als drei festen Schluesseln seine '
          'Ursprungsfunktion und wird anderswo per ["schluessel"] gelesen, wird '
          'daraus eine Klasse.',
          'Als Dictionary faellt ein Tippfehler im Schluesselnamen erst zur '
          'Laufzeit auf, und der Uebergabe sieht niemand an, welche Felder '
          'erwartet werden. Ausnahme: Der Datensatz geht unveraendert als JSON '
          'nach draussen oder liegt so in der Datenbank — dann bleibt er ein '
          'Dictionary, sonst baut man zweimal dasselbe.',
          'Aus dieser Regel entstanden u. a. Befund, Ergebnis, Messwert und '
          'Bvhdatei — Letztere mit __slots__, weil es 7.067 davon gibt.',
          'Datenmodell'),
    Lehre('eine-klasse-eine-datei',
          'Eine Klasse je Datei, 200–300 Zeilen',
          'Waechst eine Datei ueber ~300 Zeilen, wird sie nach Aufgaben '
          'getrennt: Endpunkte, Fachlogik, Datenzugriff.',
          'Eine grosse Datei versteckt Duplikate: Dieselbe Schleife stand '
          'zweimal in derselben Datei, 80 Zeilen auseinander, und ist niemandem '
          'aufgefallen.',
          'Ausgangslage: 6.495 Zeilen mit 110 Endpunkten in einer Datei.',
          'Struktur'),
    Lehre('doppelte-logik-zusammenfuehren',
          'Gleiche Logik an mehreren Stellen zusammenfuehren',
          'Bevor eine Funktion geaendert wird: nach Kopien suchen. Gefundene '
          'Kopien zuerst zusammenfuehren, dann aendern.',
          'Kopien werden bei Aenderungen nur an einer Stelle nachgezogen. Das '
          'faellt nicht auf, weil beide Seiten fuer sich funktionieren.',
          'Die Aufklapp-Logik eines Auswahlfeldes stand Zeile fuer Zeile in '
          'vier Vorlagen, das Fuellen eines Modell-Feldes in fuenf.',
          'Struktur'),
    Lehre('kein-legacy-als-backup',
          'Keinen toten Code "zur Sicherheit" behalten',
          'Unerreichbaren Code, verwaiste Vorlagen und ungenutzte '
          'Kontextvariablen loeschen, nicht auskommentieren.',
          'Die Versionsverwaltung ist das Backup. Toter Code kostet bei jeder '
          'Suche Zeit und taeuscht Abhaengigkeiten vor, die es nicht gibt.',
          'Gefunden: zwei unerreichbare Vorlagen, ein try/except, in dem nichts '
          'werfen konnte, und ein COUNT(*) je Seitenaufruf fuer eine Zahl, die '
          'die Vorlage nie anzeigte.',
          'Struktur'),
    Lehre('gleiche-namen',
          'Ein Begriff, ein Name',
          'Dieselbe Sache heisst ueberall gleich — in Ansicht, Vorlage, '
          'JavaScript und Datenbank.',
          'Unterschiedliche Namen fuer dasselbe erzeugen stille Fehler: Die '
          'Vorlage liest einen Namen, den niemand liefert, und Django rendert '
          'dafuer kommentarlos einen Leerstring.',
          'Eine if-Bedingung zeigte vier Monate lang auf einen nie gelieferten '
          'Namen — das Datei-Feld war dadurch immer Pflicht.',
          'Django'),
    Lehre('meta-ordering-distinct',
          'Meta.ordering hebelt values_list(...).distinct() aus',
          'Vor `.values_list(...).distinct()` immer ein argumentloses '
          '`.order_by()` setzen.',
          'Hat das Modell eine Standardsortierung, haengt Django deren Felder '
          'an die Auswahl an — `distinct()` wirkt dann auf (feld, sortierfeld) '
          'statt auf das Feld allein.',
          'Ein Auswahlfeld bekam 7.110 Eintraege statt zwei: einen je Datei, '
          'alle mit demselben Wert.',
          'Django'),
    Lehre('values-list-statt-objekte',
          'values_list statt Modellobjekte, wenn nur gelesen wird',
          'Werden aus einer Abfrage nur ein paar Felder gebraucht, `values_list` '
          'nehmen — Modellobjekte nur, wo auch gespeichert wird.',
          'Jedes Modellobjekt kostet Aufbauzeit; bei tausenden Zeilen ist das '
          'der groesste Posten der Anfrage, ohne dass eine einzelne Funktion '
          'auffaellt.',
          '7.110 Objekte kosteten 105 ms, nur um drei Felder zu lesen.',
          'Django'),
    Lehre('nur-sichtbares-rendern',
          'Serverseitig nur rendern, was sichtbar ist',
          'Zugeklappte oder gefilterte Listen nicht mitliefern, sondern beim '
          'Aufklappen ueber einen eigenen Endpunkt nachladen.',
          'Was zugeklappt startet, sieht niemand — der Server baut es trotzdem, '
          'der Browser baut daraus DOM-Knoten, und beides kostet.',
          'Eine Einstellungsseite lieferte 7.067 Eintraege in 4,7 MB HTML, von '
          'denen beim Aufruf keiner sichtbar war. Danach: 28 KB, 27 statt '
          '408 ms.',
          'Frontend'),
    Lehre('seitenweise-listen',
          'Lange Listen seitenweise ausgeben',
          'Uebersichtsseiten mit Suche, Filter und Seitenaufteilung bauen, '
          'sobald die Liste mit den Daten mitwaechst.',
          'Eine Liste mit tausenden Eintraegen ist ohne Suche ohnehin nicht '
          'benutzbar — die Seitenaufteilung loest damit zwei Probleme auf '
          'einmal.',
          'Eine Bibliotheksseite rendete 7.110 Karten in 10,5 MB HTML '
          '(2.082 ms). Mit 60 je Seite: 98 KB, 21 ms.',
          'Frontend'),
    Lehre('fertige-antwort-zwischenspeichern',
          'Die fertige Antwort zwischenspeichern, nicht das Objekt',
          'Wird ein grosses Ergebnis unveraendert immer wieder ausgeliefert, '
          'die fertig kodierte Zeichenkette speichern.',
          'Sonst wird bei jeder Anfrage neu kodiert, obwohl sich nichts '
          'geaendert hat. Die Zeichenkette braucht ausserdem einen Bruchteil '
          'des Arbeitsspeichers der Objektstruktur.',
          '144 ms reines JSON-Kodieren je Anfrage — danach 2 ms.',
          'Performance'),
    Lehre('scandir-statt-stat',
          'os.scandir statt listdir + stat je Datei',
          'Verzeichnisse mit `os.scandir` lesen und `DirEntry.stat()` benutzen.',
          'Groesse und Zeitstempel liefert das Betriebssystem schon mit dem '
          'Verzeichniseintrag; ein eigener stat-Aufruf je Datei ist ein '
          'Systemaufruf fuer nichts.',
          '7.067 stat-Aufrufe mit 110 ms wurden zu 9 ms.',
          'Performance'),
    Lehre('unique-axis-vermeiden',
          'np.unique(..., axis=0) meiden — Paare als eine Ganzzahl kodieren',
          'Statt Paaren `a * n + b` als int64 bilden und darauf `np.unique` '
          'anwenden.',
          '`axis=0` sortiert zeilenweise und faellt dabei auf einen langsamen '
          'Weg zurueck. Der Ganzzahl-Schluessel ist dieselbe Rechnung, nur '
          'eindimensional.',
          'Zweimal erlebt: einmal brachte die Vektorisierung ohne diesen Kniff '
          'gar nichts (391 statt 380 ms), einmal kostete das Sortieren allein '
          '200 ms.',
          'numpy'),
    Lehre('bincount-statt-add-at',
          'np.bincount statt np.add.at',
          'Streuende Summen (Werte auf Indizes addieren) mit `np.bincount` '
          'rechnen, je Achse einmal.',
          '`np.add.at` arbeitet elementweise und ohne Puffer, damit mehrfach '
          'getroffene Ziele richtig summiert werden — das ist korrekt, aber '
          'sehr langsam. `np.bincount` leistet dasselbe in kompiliertem Code.',
          '82 ms wurden 9,6 ms, Ergebnis Bit fuer Bit gleich.',
          'numpy'),
    Lehre('kdtree-workers',
          'cKDTree.query mit workers=-1 aufrufen',
          'Bei jeder Nachbarsuche `workers=-1` setzen.',
          'Ohne das Argument sucht scipy einkernig. Die Suche ist punktweise '
          'unabhaengig, das Ergebnis daher Index fuer Index identisch.',
          '3,8-fach schneller auf zwoelf Kernen — ein Argument, kein Umbau.',
          'numpy'),
    Lehre('feld-oder-skalar',
          '& und ~ nur auf Feldern, nie auf einzelnen Wahrheitswerten',
          'Beim Vektorisieren von Bedingungen `np.logical_and` und '
          '`np.logical_not` benutzen, wenn die Funktion auch mit Einzelwerten '
          'aufgerufen werden kann.',
          '`~True` ist in Python die Zahl -2 und damit wahr. Eine so '
          'umgeschriebene Bedingung laesst dann alles durch — ohne Fehlermeldung.',
          'Beim Umbau genau so passiert; aufgefallen erst im Vergleich mit der '
          'Vorgaengerfassung (16.784 statt 16.388 ausgewaehlte Flaechen).',
          'numpy'),
    Lehre('aequivalenz-beweisen',
          'Jede Optimierung gegen die alte Fassung beweisen',
          'Die alte Fassung aufheben und beide auf echten Daten vergleichen — '
          'groesste Abweichung und Beschleunigung ausgeben, nicht nur '
          '"sieht gut aus".',
          'Eine schnellere Funktion, die etwas anderes rechnet, ist kein '
          'Fortschritt. Bei Fliesskomma ist "gleich" ausserdem eine Zahl '
          '(1e-16), keine Meinung.',
          'Der Vergleich hat zwei echte Fehler gefunden, die kein Test bemerkt '
          'haette — und einmal gezeigt, dass eine "Optimierung" gar keine war.',
          'Vorgehen'),
    Lehre('messen-nicht-raten',
          'Erst messen, dann optimieren',
          'Mit cProfile beide Sichten ansehen: tottime fuer die eigene Zeit, '
          'cumulative fuer die Aufrufer.',
          'Die teuerste Stelle liegt fast nie dort, wo man sie vermutet — und '
          'ohne Ausgangsmessung ist hinterher nicht belegbar, ob es besser '
          'wurde.',
          'Der groesste Posten einer Seite war am Ende kein Rechenschritt, '
          'sondern 71.000 Variablenaufloesungen in einer Vorlagenschleife.',
          'Vorgehen'),
    Lehre('regressionsnetz-vorher',
          'Vor dem Umbau ein Sicherheitsnetz aufnehmen',
          'Alle GET-Routen einmal abfahren und die Statuscodes als Referenz '
          'ablegen, solange die Anwendung nachweislich laeuft.',
          'Tests decken selten alle Routen ab. Wer eine grosse Datei zerlegt, '
          'merkt einen kaputten Endpunkt sonst erst, wenn jemand die Seite '
          'oeffnet.',
          'Hat den Umbau von 110 Endpunkten abgesichert.',
          'Vorgehen'),
    Lehre('keine-temp-dateien-im-system',
          'Zwischendateien ins Projekt, nicht in den System-Temp',
          'Werkzeuge und Tests schreiben in ein Projektverzeichnis.',
          'System-Temp-Verzeichnisse werden nicht aufgeraeumt und liegen oft '
          'auf der Systemplatte.',
          'Vorgeschichte: rund 100 GB Datenmuell auf C:.',
          'Vorgehen'),
    Lehre('kein-globaler-zustand',
          'Veränderlicher Zustand gehört in eine Klasse, nicht auf Modulebene',
          'Eine Modulvariable, die sich nach dem Import noch ändert '
          '(Zwischenspeicher, Zähler, Liste), wird zum Attribut der Klasse, die '
          'sie benutzt. Gibt es diese Klasse noch nicht, ist SIE der eigentliche '
          'Befund. Globale Konstanten kommen gebündelt in eine Kontext- oder '
          'Konfigurationsklasse.',
          'Modulweiter Zustand überlebt jeden Aufruf und gehört niemandem: Im '
          'Testlauf trägt die zweite Prüfung noch, was die erste hineingeschrieben '
          'hat, und im Server-Prozess teilen sich alle Anfragen denselben Wert. '
          'Als Klassenvariable statt Modulvariable ist es derselbe Fehler, nur '
          'weniger sichtbar — auch dort teilen sich alle Instanzen den Wert.',
          'Werkzeuge: „Globale Variablen und Konstanten" findet den Zustand, '
          '„Klassen-Kandidaten aus geteiltem Zustand" nennt die Klasse, die '
          'daraus wird — samt der Funktionen, die zu ihren Methoden werden.',
          'Struktur'),
    Lehre('utility-statt-leerer-klasse',
          'Ohne Zustand: Utility-Klasse mit statischen Methoden',
          'Funktionsbündel, die keinen gemeinsamen Zustand anfassen, kommen in '
          'eine Klasse mit @staticmethod — ohne __init__.',
          'Eine Klasse, die man erst instanziieren muss, um ihre Methoden zu '
          'rufen, ist eine Funktionssammlung mit Umweg. Sie sieht '
          'objektorientiert aus und ist es nicht. Der Unterschied entscheidet, '
          'welcher Umbau richtig ist: geteilter Zustand → Klasse mit Attributen, '
          'kein Zustand → Utility-Klasse.',
          'Beide Fälle meldet „Klassen-Kandidaten aus geteiltem Zustand" '
          'getrennt, weil sie zu verschiedenen Umbauten führen.',
          'Struktur'),
    Lehre('testbaum-statt-vererbung',
          'Testdaten als Beimischung, nicht als Basis-TestCase',
          'Gemeinsame Testvorbereitung in eine Mixin-Klasse OHNE TestCase '
          'legen, sonst laufen die Tests der Basis in jeder Unterklasse erneut.',
          'Aus 15 Tests werden sonst unbemerkt 44 — die Suite wird langsamer '
          'und die Zahlen im Bericht sind falsch.',
          'Genau so passiert, aufgefallen an der Testzahl.',
          'Vorgehen'),
]


class Lehrenstand:
    """Welche Lehren angekreuzt sind — mit Speicherung in einer JSON-Datei."""

    DATEI = '.djangobase-skills.json'

    @classmethod
    def _pfad(cls):
        return Path(str(settings.BASE_DIR)) / cls.DATEI

    @classmethod
    def laden(cls):
        """{slug: bool}. Unbekannte Lehren sind an — Vorgabe ist Zustimmung."""
        gespeichert = {}
        try:
            daten = json.loads(cls._pfad().read_text(encoding='utf-8'))
            if isinstance(daten, dict) and isinstance(daten.get('lehren'), dict):
                gespeichert = daten['lehren']
        except (OSError, ValueError):
            gespeichert = {}
        return {lehre.slug: bool(gespeichert.get(lehre.slug, True))
                for lehre in LEHREN}

    @classmethod
    def speichern(cls, angekreuzt):
        """`angekreuzt` ist die Menge der Slugs, die an sein sollen."""
        stand = {lehre.slug: lehre.slug in angekreuzt for lehre in LEHREN}
        cls._pfad().write_text(
            json.dumps({'lehren': stand}, indent=2, ensure_ascii=False),
            encoding='utf-8')
        return stand

    @classmethod
    def aktive(cls):
        stand = cls.laden()
        return [lehre for lehre in LEHREN if stand.get(lehre.slug)]

    @classmethod
    def auftragstext(cls):
        """Die aktiven Lehren als Arbeitsgrundlage — zum Kopieren."""
        zeilen = ['Regeln fuer diesen Umbau (aus Hilfe -> Skills):', '']
        for bereich in BEREICHE:
            teil = [lehre for lehre in cls.aktive() if lehre.bereich == bereich]
            if not teil:
                continue
            zeilen.append('## ' + bereich)
            for lehre in teil:
                zeilen.append('- %s' % lehre.regel)
                zeilen.append('  Warum: %s' % lehre.warum)
                if lehre.beleg:
                    zeilen.append('  Beleg: %s' % lehre.beleg)
            zeilen.append('')
        return '\n'.join(zeilen)
