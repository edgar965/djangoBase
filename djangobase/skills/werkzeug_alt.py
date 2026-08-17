"""Basis fuer die Analysewerkzeuge der Skills-Seite."""

import time


class Befund:
    """Ein einzelner Fund eines Werkzeugs.

    Eigene Klasse statt Dictionary — genau die Regel, die dieser Durchgang
    hervorgebracht hat: Ein Datensatz mit mehr als drei Feldern, der seine
    Ursprungsfunktion verlaesst und anderswo per ["schluessel"] gelesen wird,
    gehoert in eine Klasse. Als Dictionary faellt ein Tippfehler im
    Schluesselnamen erst zur Laufzeit auf, und niemand sieht der Uebergabe an,
    welche Felder erwartet werden.
    """

    __slots__ = ('ort', 'was', 'warum', 'gewicht')

    #: Gewichte, aufsteigend nach Dringlichkeit.
    HINWEIS = 'hinweis'
    WARNUNG = 'warnung'
    FEHLER = 'fehler'

    def __init__(self, ort, was, warum='', gewicht=HINWEIS):
        self.ort = ort
        self.was = was
        self.warum = warum
        self.gewicht = gewicht

    def zeile(self):
        teil = '%-9s %-55s %s' % (self.gewicht.upper(), self.ort, self.was)
        return teil + ('  — ' + self.warum if self.warum else '')


class Ergebnis:
    """Was ein Werkzeug zurueckgibt: Kopfzeilen, Befunde, Laufzeit."""

    __slots__ = ('titel', 'kopf', 'befunde', 'dauer_s', 'fehler')

    def __init__(self, titel, kopf=None, befunde=None, dauer_s=0.0, fehler=''):
        self.titel = titel
        #: Freie Zeilen ueber der Liste — Zusammenfassung, Zahlen, Messwerte.
        self.kopf = list(kopf or [])
        self.befunde = list(befunde or [])
        self.dauer_s = dauer_s
        self.fehler = fehler

    @property
    def anzahl(self):
        return len(self.befunde)

    @property
    def sauber(self):
        return not self.befunde and not self.fehler

    def text(self):
        """Alles als Klartext — fuer die Zwischenablage und fuers Log."""
        zeilen = list(self.kopf)
        if self.fehler:
            zeilen.append('FEHLER: ' + self.fehler)
        if self.befunde:
            zeilen.append('')
            zeilen.extend(b.zeile() for b in self.befunde)
            zeilen.append('')
            zeilen.append('%d Befunde in %.1f s' % (self.anzahl, self.dauer_s))
        elif not self.fehler:
            zeilen.append('')
            zeilen.append('Nichts gefunden (%.1f s).' % self.dauer_s)
        return '\n'.join(zeilen)


class Ausgabe:
    """Sammelt die Klartext-Ergebnisse mehrerer Werkzeuge in einem Feld.

    Die Skills-Seite schreibt alles in eine Textbox, damit man den Inhalt einer
    Claude-Sitzung als Arbeitsgrundlage geben kann. Deshalb steht vor jedem
    Abschnitt eine deutliche Trennlinie mit Werkzeugname, Kennung, Laufzeit und
    Trefferzahl: Wer mehrere Werkzeuge hintereinander laufen laesst, muss im
    Text sofort erkennen, wo das eine endet und das naechste beginnt.
    """

    LINIE = '=' * 78

    def __init__(self, bisher=''):
        self.teile = [bisher.rstrip()] if bisher and bisher.strip() else []

    def anhaengen(self, werkzeug, ergebnis, zeitstempel=''):
        kopf = '%s  [%s]%s' % (werkzeug.name, werkzeug.slug,
                               '  ' + zeitstempel if zeitstempel else '')
        stand = ('%d Befunde' % ergebnis.anzahl if ergebnis.befunde
                 else 'FEHLER' if ergebnis.fehler else 'nichts gefunden')
        self.teile.append('\n'.join([
            self.LINIE,
            '# %s' % kopf,
            '# %s · %.1f s' % (stand, ergebnis.dauer_s),
            self.LINIE,
            ergebnis.text(),
        ]))
        return self

    def text(self):
        return '\n\n'.join(self.teile).strip()


class Werkzeug:
    """Ein Analysewerkzeug. Unterklassen ueberschreiben `pruefen`."""

    #: Kennung in der URL — kleingeschrieben, mit Bindestrichen.
    slug = ''
    name = ''
    #: Was das Werkzeug tut (eine Zeile).
    zweck = ''
    #: Wann man es einsetzt.
    wann = ''
    #: Was es im Ursprungsprojekt tatsaechlich gefunden hat — ohne so einen
    #: Beleg glaubt man einem Werkzeug nicht, dass es sich lohnt.
    beleg = ''
    #: Grobe Laufzeit, damit niemand versehentlich eine Minute wartet.
    dauer = 'Sekunden'
    #: Optionales Textfeld auf der Seite: (name, beschriftung, vorgabe)
    eingabe = None
    #: True, wenn das Werkzeug Endpunkte des laufenden Servers aufruft.
    ruft_endpunkte_auf = False

    def laufen(self, **argumente):
        """Werkzeug ausfuehren; faengt Fehler ab, damit die Seite stehen bleibt."""
        start = time.perf_counter()
        try:
            ergebnis = self.pruefen(**argumente)
        except Exception as fehler:  # noqa: BLE001 — die Seite darf nicht sterben
            ergebnis = Ergebnis(self.name, fehler='%s: %s'
                                % (type(fehler).__name__, fehler))
        ergebnis.dauer_s = time.perf_counter() - start
        return ergebnis

    def pruefen(self, **argumente):
        raise NotImplementedError

    # ------------------------------------------------------------- Hilfsmittel

    #: Immer uebersprungen — nichts davon ist eigener Quelltext.
    AUSSER = ('__pycache__', 'migrations', 'node_modules', '.git', 'venv',
              'site-packages', 'staticfiles', 'dist', 'build', '.venv')

    @classmethod
    def ausnahmen(cls):
        """Uebersprungene Ordnernamen — Standard plus Projektangabe.

        Fremder Referenzcode im Projektbaum (mitgelieferte Fremdbibliotheken,
        alte Staende, Vergleichsimplementierungen) erzeugt sonst so viele
        Befunde, dass die eigenen darin untergehen. Ergaenzen ueber

            DJANGOBASE = {..., "skills_ausser": ["TestCharakter", "alt"]}
        """
        try:
            from ..conf import conf
            zusatz = tuple(str(x) for x in (conf().get('skills_ausser') or []))
        except Exception:  # noqa: BLE001 — ohne Konfiguration eben nur Standard
            zusatz = ()
        return cls.AUSSER + zusatz

    @classmethod
    def projektdateien(cls, endung='.py', ausser=None):
        """Alle Projektdateien mit dieser Endung, unterhalb von BASE_DIR.

        BASE_DIR statt eines konfigurierten Pfades: Es ist die einzige Angabe,
        die jedes Django-Projekt hat.
        """
        from pathlib import Path

        from django.conf import settings
        uebergehen = tuple(ausser) if ausser is not None else cls.ausnahmen()
        wurzel = Path(str(settings.BASE_DIR))
        for pfad in sorted(wurzel.rglob('*' + endung)):
            if any(teil in uebergehen for teil in pfad.parts):
                continue
            yield pfad

    @staticmethod
    def kurz(pfad):
        """Pfad relativ zu BASE_DIR — absolute Pfade sind in Listen unlesbar."""
        from pathlib import Path

        from django.conf import settings
        try:
            return str(Path(pfad).relative_to(str(settings.BASE_DIR)))
        except (ValueError, TypeError):
            return str(pfad)
