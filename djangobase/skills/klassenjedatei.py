"""KlassenJeDatei — Dateien mit mehr als einer Klasse."""

import ast

from .befund import Befund, Befundsatz, BefundWerkzeug
from .anlassfall import Anlassfall


class KlassenJeDatei(BefundWerkzeug):

    slug = 'klassen-je-datei'

    #: Auftrags-Kriterium (kam bis 18.08.2026 aus der

    #: Tabelle ALT_KRITERIUM neben der Registrierung).

    kriterium = 2
    titel = 'Klassen je Datei'
    zweck = ('Listet Dateien mit mehr als einer Klasse — mit Zeilenzahl je '
             'Klasse, damit man sieht, ob es sich um eine Sammlung oder um eine '
             'Hauptklasse mit kleinen Helfern handelt.')
    abhilfe = ('Wenn die Regel "eine Klasse je Datei" gilt. Kleine Datentraeger '
            'direkt neben ihrer Hauptklasse sind dabei kein Verstoß, sondern '
            'meist genau richtig — deshalb zeigt das Werkzeug die Größen '
            'mit an, statt nur zu zählen.')
    befund = ('Im Ursprungsprojekt lagen 110 Endpunkte und ein Dutzend Klassen '
             'in einer Datei; nach dem Schnitt: eine Aufgabe je Modul, '
             'Datentraeger bei ihrer Klasse.')
    dauer = 'Sekunden'
    eingabe = ('ab', 'Ab wie vielen Klassen je Datei melden?', '2')

    #: Klassen unter dieser Zeilenzahl gelten als Datentraeger/Helfer.
    KLEIN = 40

    anlassfall = Anlassfall(
        {"sammlung.py": "class Erste:\n" + "    def a(self):\n        return 1\n" * 1
                        + "\n\nclass Zweite:\n    def b(self):\n        return 2\n"},
        mindestens=1, hoechstens=1, erwartet_in="sammlung.py",
        warum="Zwei Klassen in einer Datei — die Hausordnung sagt: eine je Datei")

    def pruefen(self, ab='2', **_argumente):
        try:
            grenze = max(2, int(str(ab).strip() or 2))
        except ValueError:
            grenze = 2

        befunde, gesamt = [], 0
        for datei in self.projektdateien('.py'):
            klassen = self._klassen(datei)
            gesamt += len(klassen)
            if len(klassen) < grenze:
                continue
            grosse = [k for k in klassen if k[1] >= self.KLEIN]
            beschreibung = '%d Klassen: %s' % (
                len(klassen),
                ', '.join('%s (%d)' % (name, laenge) for name, laenge in klassen[:8]))
            if len(grosse) <= 1:
                warum = ('nur %d davon größer als %d Zeilen — das sind '
                         'Datentraeger bei ihrer Klasse, kein Verstoß'
                         % (len(grosse), self.KLEIN))
                gewicht = Befund.HINWEIS
            else:
                warum = ('%d eigenstaendige Klassen in einer Datei — trennen'
                         % len(grosse))
                gewicht = Befund.WARNUNG
            befunde.append(Befund(self.kurz(datei), beschreibung, warum, gewicht))

        befunde.sort(key=lambda b: (b.gewicht != Befund.WARNUNG, b.ort))
        # Die Trennung gehoert in die KOPFZEILE, nicht nur in die Spalte
        # „warum": In 3DTools waren alle 20 Zeilen ausdrueckliche Nicht-Verstoesse
        # (Fehlerklasse neben ihrem Dienst, Attrappe neben ihrem Test) — die Zahl
        # „20" liest sich aber wie 20 Mängel, und danach liest man 20 Zeilen
        # (17.08.2026).
        verstoesse = sum(1 for b in befunde if b.gewicht == Befund.WARNUNG)
        kopf = ['%d Klassen insgesamt' % gesamt,
                '%d Dateien mit mindestens %d Klassen — davon %d mit mehr als '
                'EINER eigenstaendigen Klasse (die Verstöße)'
                % (len(befunde), grenze, verstoesse)]
        return Befundsatz(self.titel, kopf, befunde)

    @staticmethod
    def _klassen(datei):
        try:
            baum = ast.parse(datei.read_text(encoding='utf-8', errors='replace'))
        except (SyntaxError, OSError):
            return []
        gefunden = []
        for knoten in baum.body:          # nur Modulebene: verschachtelte
            if isinstance(knoten, ast.ClassDef):   # Klassen sind Absicht
                ende = getattr(knoten, 'end_lineno', knoten.lineno) or knoten.lineno
                gefunden.append((knoten.name, ende - knoten.lineno + 1))
        return gefunden
