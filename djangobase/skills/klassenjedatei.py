"""KlassenJeDatei — Dateien mit mehr als einer Klasse."""

import ast

from .werkzeug_alt import Befund, Ergebnis, Werkzeug


class KlassenJeDatei(Werkzeug):

    slug = 'klassen-je-datei'
    name = 'Klassen je Datei'
    zweck = ('Listet Dateien mit mehr als einer Klasse — mit Zeilenzahl je '
             'Klasse, damit man sieht, ob es sich um eine Sammlung oder um eine '
             'Hauptklasse mit kleinen Helfern handelt.')
    wann = ('Wenn die Regel "eine Klasse je Datei" gilt. Kleine Datentraeger '
            'direkt neben ihrer Hauptklasse sind dabei kein Verstoss, sondern '
            'meist genau richtig — deshalb zeigt das Werkzeug die Groessen '
            'mit an, statt nur zu zaehlen.')
    beleg = ('Im Ursprungsprojekt lagen 110 Endpunkte und ein Dutzend Klassen '
             'in einer Datei; nach dem Schnitt: eine Aufgabe je Modul, '
             'Datentraeger bei ihrer Klasse.')
    dauer = 'Sekunden'
    eingabe = ('ab', 'Ab wie vielen Klassen je Datei melden?', '2')

    #: Klassen unter dieser Zeilenzahl gelten als Datentraeger/Helfer.
    KLEIN = 40

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
                warum = ('nur %d davon groesser als %d Zeilen — das sind '
                         'Datentraeger bei ihrer Klasse, kein Verstoss'
                         % (len(grosse), self.KLEIN))
                gewicht = Befund.HINWEIS
            else:
                warum = ('%d eigenstaendige Klassen in einer Datei — trennen'
                         % len(grosse))
                gewicht = Befund.WARNUNG
            befunde.append(Befund(self.kurz(datei), beschreibung, warum, gewicht))

        befunde.sort(key=lambda b: (b.gewicht != Befund.WARNUNG, b.ort))
        kopf = ['%d Klassen insgesamt' % gesamt,
                '%d Dateien mit mindestens %d Klassen' % (len(befunde), grenze)]
        return Ergebnis(self.name, kopf, befunde)

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
