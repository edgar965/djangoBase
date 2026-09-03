"""KlassenJeDatei — Dateien mit mehr als einer Klasse."""

import ast

from .befund import Befund, Befundsatz, BefundWerkzeug
from .anlassfall import Anlassfall
from .werkzeug import Quelldatei


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

    #: Ab dieser Groesse lohnt das Aufteilen - darunter schadet es.
    #:
    #: „Eine Klasse je Datei" dient der Lesbarkeit. Acht kleine Klassen auf
    #: 150 Zeilen in acht Dateien zu verteilen macht sie schlechter, nicht
    #: besser. Gemessen an shortlongx (03.09.2026): Von 36 Warnungen fielen
    #: **31** allein hierunter.
    ZUSAMMEN_BIS = 300

    #: Dateien, in denen ein Framework oder die Aufgabe MEHRERE Klassen
    #: verlangt.
    #:
    #: Django FINDET seine Modelle in ``models.py`` - eine Datei je Modell
    #: waere gegen das Framework, nicht fuer die Uebersicht. Attrappen fuer
    #: einen Test gehoeren zusammen: gemeinsam gebaut, gemeinsam gelesen,
    #: einzeln sinnlos.
    ZUSAMMEN_MUSTER = ('/models.py', '/admin.py', '/forms.py',
                       '/serializers.py', '_attrappe.py', '_attrappen.py',
                       '/migrations/')

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
            zusammen = self._gehoeren_zusammen(datei)
            if len(grosse) <= 1:
                warum = ('nur %d davon größer als %d Zeilen — das sind '
                         'Datentraeger bei ihrer Klasse, kein Verstoß'
                         % (len(grosse), self.KLEIN))
                gewicht = Befund.HINWEIS
            elif zusammen:
                # KEIN VERSTOSS, aber auch nicht verschwiegen: Die Zeile bleibt
                # als Hinweis stehen und traegt den Grund. Wer sie stillschweigen
                # liesse, koennte spaeter nicht nachrechnen, was ausgenommen war.
                warum = zusammen
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

    def _gehoeren_zusammen(self, datei):
        u"""Warum diese Klassen in EINER Datei stehen duerfen - oder ``''``."""
        kurz = '/' + self.kurz(datei)
        for muster in self.ZUSAMMEN_MUSTER:
            if muster in kurz:
                return ('%s — hier verlangt das Framework bzw. die Aufgabe '
                        'mehrere Klassen, kein Verstoß' % muster.strip('/'))
        n = Quelldatei(datei, self.wurzel()).codezeilen
        if n <= self.ZUSAMMEN_BIS:
            return ('nur %d Code-Zeilen — unter %d ist die Übersicht ohnehin da, '
                    'Aufteilen schadet' % (n, self.ZUSAMMEN_BIS))
        return ''

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
