"""Grossdateien — Dateien ueber der vereinbarten Zeilengrenze."""

import ast
import re

from .werkzeug_alt import Befund, Ergebnis, Werkzeug


class Dateimass:
    """Mass einer Quelldatei: Zeilen, Klassen, Funktionen, laengste Funktion."""

    __slots__ = ('pfad', 'zeilen', 'klassen', 'funktionen', 'laengste',
                 'laengste_name')

    def __init__(self, pfad, zeilen, klassen=0, funktionen=0,
                 laengste=0, laengste_name=''):
        self.pfad = pfad
        self.zeilen = zeilen
        self.klassen = klassen
        self.funktionen = funktionen
        self.laengste = laengste
        self.laengste_name = laengste_name

    def beschreibung(self):
        teile = ['%d Zeilen' % self.zeilen]
        if self.klassen or self.funktionen:
            teile.append('%d Klassen, %d Funktionen' % (self.klassen, self.funktionen))
        if self.laengste:
            teile.append('laengste: %s (%d Zeilen)' % (self.laengste_name, self.laengste))
        return ', '.join(teile)


class Grossdateien(Werkzeug):

    slug = 'grossdateien'
    name = 'Grosse Dateien'
    zweck = ('Listet Python- und JavaScript-Dateien ueber der Zeilengrenze, mit '
             'Anzahl Klassen und Funktionen und der laengsten Funktion je Datei.')
    wann = ('Zu Beginn eines Umbaus, um die Schnittkandidaten zu finden — und '
            'danach als Nachweis, dass keine neue Monsterdatei entstanden ist.')
    beleg = ('Ausgangslage im Ursprungsprojekt: eine Datei mit 6.495 Zeilen und '
             '110 Endpunkten, eine zweite mit 3.496 Zeilen — beide zerlegt.')
    dauer = 'Sekunden'
    eingabe = ('grenze', 'Ab wie vielen Zeilen melden?', '300')

    def pruefen(self, grenze='300', **_argumente):
        try:
            schwelle = max(1, int(str(grenze).strip() or 300))
        except ValueError:
            schwelle = 300
        masse = []
        for datei in self.projektdateien('.py'):
            masse.append(self._python(datei))
        for datei in self.projektdateien('.js'):
            if '.min.' in datei.name:
                continue
            masse.append(self._javascript(datei))

        ueber = sorted((m for m in masse if m.zeilen > schwelle),
                       key=lambda m: -m.zeilen)
        befunde = []
        for mass in ueber:
            gewicht = (Befund.FEHLER if mass.zeilen > schwelle * 3
                       else Befund.WARNUNG if mass.zeilen > schwelle * 1.5
                       else Befund.HINWEIS)
            befunde.append(Befund(mass.pfad, mass.beschreibung(),
                                  gewicht=gewicht))
        gesamt = sum(m.zeilen for m in masse)
        kopf = [
            '%d Quelldateien, %d Zeilen insgesamt' % (len(masse), gesamt),
            '%d ueber %d Zeilen' % (len(ueber), schwelle),
        ]
        if ueber:
            kopf.append('groesste: %s mit %d Zeilen' % (ueber[0].pfad, ueber[0].zeilen))
        return Ergebnis(self.name, kopf, befunde)

    def _python(self, datei):
        quelle = datei.read_text(encoding='utf-8', errors='replace')
        zeilen = quelle.count('\n') + 1
        try:
            baum = ast.parse(quelle)
        except SyntaxError:
            return Dateimass(self.kurz(datei), zeilen)
        klassen = funktionen = 0
        laengste, laengste_name = 0, ''
        for knoten in ast.walk(baum):
            if isinstance(knoten, ast.ClassDef):
                klassen += 1
            elif isinstance(knoten, (ast.FunctionDef, ast.AsyncFunctionDef)):
                funktionen += 1
                ende = getattr(knoten, 'end_lineno', knoten.lineno) or knoten.lineno
                laenge = ende - knoten.lineno + 1
                if laenge > laengste:
                    laengste, laengste_name = laenge, knoten.name
        return Dateimass(self.kurz(datei), zeilen, klassen, funktionen,
                         laengste, laengste_name)

    def _javascript(self, datei):
        """Grobzaehlung ohne Parser — fuer eine Groessenordnung genuegt das.

        Bewusst keine JS-Syntaxanalyse: Die haette Abhaengigkeiten gebraucht,
        und fuer die Frage "welche Datei ist zu gross" reicht das Zaehlen von
        `class`- und Funktionsschluesselwoertern.
        """
        quelle = datei.read_text(encoding='utf-8', errors='replace')
        zeilen = quelle.count('\n') + 1
        klassen = len(re.findall(r'^\s*(?:export\s+)?class\s+\w+', quelle, re.M))
        funktionen = len(re.findall(
            r'^\s*(?:export\s+)?(?:async\s+)?function\s+\w+|^\s*\w+\s*\([^)]*\)\s*\{',
            quelle, re.M))
        return Dateimass(self.kurz(datei), zeilen, klassen, funktionen)
