"""Doppelcode — gleiche Codeblöcke an mehreren Stellen."""

import hashlib
import re
from collections import defaultdict

from .befund import Befund, Befundsatz, BefundWerkzeug
from .anlassfall import Anlassfall


class Fundstelle:
    """Ein Vorkommen eines Blocks: Datei und Zeile."""

    __slots__ = ('datei', 'zeile')

    #: Ein Block, der zweimal dasteht - das ist der ganze Fall.
    _WIEDERHOLT = ("def preis_pruefen(betrag):\n"
                   "    if betrag < 0:\n"
                   "        raise ValueError('negativ')\n"
                   "    if betrag > 1000:\n"
                   "        raise ValueError('zu groß')\n"
                   "    return round(betrag, 2)\n")

    def __init__(self, datei, zeile):
        self.datei = datei
        self.zeile = zeile

    def __str__(self):
        return '%s:%d' % (self.datei, self.zeile)


class Doppelcode(BefundWerkzeug):

    slug = 'doppelcode'

    #: Auftrags-Kriterium (kam bis 18.08.2026 aus der

    #: Tabelle ALT_KRITERIUM neben der Registrierung).

    kriterium = 6
    titel = 'Doppelter Code'
    zweck = ('Sucht identische Codeblöcke (Vorgabe: ab 6 Zeilen) in Python-, '
             'JavaScript- und HTML-Dateien und zeigt alle Fundstellen.')
    abhilfe = ('Vor dem Zusammenfassen von Modulen. Doppelter Code fällt im '
            'Alltag nicht auf, weil die Kopien in verschiedenen Dateien liegen '
            '— und wird bei Änderungen genau deshalb nur an einer Stelle '
            'nachgezogen.')
    befund = ('Im Ursprungsprojekt stand die Aufklapp- und Auswahllogik eines '
             'Auswahlfeldes Zeile für Zeile in VIER Vorlagen, das Füllen '
             'eines Modell-Feldes in fünf. Beides jetzt je ein ES-Modul.')
    dauer = 'Sekunden bis eine Minute'
    eingabe = ('mindestens', 'Ab wie vielen gleichen Zeilen melden?', '6')

    #: Zeilen, die als Blockanfang nichts taugen (zu haeufig, zu leer).
    UNINTERESSANT = re.compile(r'^\s*(#|//|/\*|\*|\}|\)|\]|$)')

    #: Eine Zeile, die nur etwas hereinholt.
    #:
    #: WARUM SIE NICHT ZAEHLT (27.08.2026, 3DTools)
    #: ===========================================
    #: Vier Module bekamen eine Warnung fuer diesen Block::
    #:
    #:     import json
    #:     import logging
    #:     import os
    #:     import re
    #:
    #:     from django.conf import settings
    #:
    #: Der ist tatsaechlich in allen vier gleich — und muss es sein. Ein
    #: Importblock laesst sich nicht zusammenfassen: Wer `json` braucht, muss
    #: `json` importieren. Ein Befund, der nichts zu tun gibt, verdeckt die,
    #: die etwas zu tun geben.
    #:
    #: NACHGETRAGEN (28.08.2026, 3DTools): der BEGINN eines
    #: Blockkommentars. Drei Module im BVH-Studio bekamen eine Warnung
    #: fuer ihre fuenf gleichen Importzeilen PLUS der oeffnenden Zeile
    #: ihres Modulkopfs - die Ausnahme griff um genau eine Zeile nicht
    #: weit genug. Ein Fenster aus Importen und dem Anfang eines
    #: Kommentars enthaelt keinen Code, den man zusammenfassen koennte.
    #:
    #: Gezaehlt wird streng: NUR wenn JEDE Zeile des Fensters so aussieht.
    #: Ein Block, der mit Importen anfaengt und mit Code weitergeht, bleibt
    #: ein Befund.
    NUR_HEREINGEHOLT = re.compile(
        r'^\s*('
        r'import\s|from\s.+\simport\s|'                 # Python und ES
        r'export\s.*\sfrom\s|'                          # ES-Weitergabe
        r'\{%\s*(load|extends)\s|'                      # Django-Vorlagen
        r'#|//|/[*]|[*]|'                                        # Kommentarzeilen
        r'"""$|\'\'\'$'                                 # Ende des Docstrings
        r')')
    #: Hoechstens so viele Stellen anzeigen (die Kappung wird im Kopf genannt).
    ZEILEN = 200

    #: Derselbe Block in zwei Dateien - das ist der ganze Fall.
    _WIEDERHOLT = ("def preis_pruefen(betrag):\n"
                   "    if betrag < 0:\n"
                   "        raise ValueError('negativ')\n"
                   "    if betrag > 1000:\n"
                   "        raise ValueError('zu groß')\n"
                   "    return round(betrag, 2)\n")

    anlassfall = Anlassfall(
        {"eins.py": _WIEDERHOLT, "zwei.py": _WIEDERHOLT},
        mindestens=1, erwartet_in="eins.py",
        warum="Derselbe Block an zwei Stellen: Wer den einen fixt, vergisst "
              "den anderen — so entstehen zwei Wahrheiten")

    def pruefen(self, mindestens='6', **_argumente):
        #: Wie viele Fenster nur Importe waren — gehoert in die Kopfzeile,
        #: sonst verschweigt die Ausnahme, wie viel sie schluckt.
        self.nur_importe = 0
        try:
            fenster = max(3, int(str(mindestens).strip() or 6))
        except ValueError:
            fenster = 6

        bloecke = defaultdict(list)
        dateien = 0
        for endung in ('.py', '.js', '.html'):
            for datei in self.projektdateien(endung):
                if '.min.' in datei.name:
                    continue
                dateien += 1
                self._sammeln(datei, fenster, bloecke)

        roh = []
        for fundstellen in bloecke.values():
            if len(fundstellen) < 2:
                continue
            # Ueberlappende Treffer derselben Datei nicht doppelt melden.
            orte = sorted({str(f) for f in fundstellen})
            if len(orte) < 2:
                continue
            roh.append(orte)

        befunde = []
        for orte, laenge in self._zusammenfassen(roh, fenster):
            befunde.append(Befund(
                orte[0], '%d gleiche Bloecke à %d Zeilen' % (len(orte), laenge),
                'auch: ' + ', '.join(orte[1:6]) + (' …' if len(orte) > 6 else ''),
                Befund.WARNUNG if len(orte) > 2 else Befund.HINWEIS))
        befunde.sort(key=lambda b: b.was, reverse=True)
        kopf = ['%d Dateien geprüft, Blockgroesse %d Zeilen' % (dateien, fenster),
                '%d Stellen mit mehrfach vorkommenden Bloecken' % len(befunde)]
        if self.nur_importe:
            # Nie verschweigen, wie viel die Ausnahme schluckt.
            kopf.append('%d Fenster uebergangen: reine Importbloecke'
                        % self.nur_importe)
        if len(befunde) > self.ZEILEN:
            # Kappung benennen, nicht verschweigen: Sonst liest sich die Liste
            # wie eine vollstaendige Bestandsaufnahme.
            kopf.append('angezeigt: die ersten %d — mit groesserer Blockgroesse '
                        'wird die Liste kuerzer und die Funde gewichtiger'
                        % self.ZEILEN)
        return Befundsatz(self.titel, kopf, befunde[:self.ZEILEN])

    @staticmethod
    def _zusammenfassen(roh, fenster):
        """Aneinandergrenzende Fenster zu EINEM Block - mit echter Laenge.

        WARUM (25.08.2026, Projekt assistant)
        =====================================
        Gesucht wird mit einem GLEITENDEN Fenster: jede Startzeile
        bekommt ihren eigenen Hash. Ein zusammenhaengender Duplikatblock
        von zwoelf Zeilen erzeugt bei Fenstergroesse sechs also SIEBEN
        Fenster - und damit sieben Befunde fuer eine einzige Stelle.

        Gemessen in den ersten 200 angezeigten Befunden: 112 waren
        blosse Folgezeilen, echte Stellen gab es 88. In
        ``acestep_create.html`` standen zehn Befunde untereinander
        (Zeile 32 bis 41), alle fuer denselben Block.

        ZWEI FALLEN AUF DEM WEG
        =======================
        1. Die Fundstellen muessen NUMERISCH sortiert werden. Mit
           ``sorted()`` ueber die Textform steht ``x.html:1000`` vor
           ``x.html:961``, und die Nachbarschaft ist nicht mehr zu sehen.
        2. Der Sprung ist NICHT immer eins. ``_sammeln`` laesst
           Leerzeilen weg und schiebt das Fenster um einen INHALTS-Index
           weiter; steht im Block eine Leerzeile, springt die gemeldete
           Zeilennummer um zwei oder drei. Verlangt man +1, fasst man
           fast nichts zusammen (670 wurden 659 statt der halben Zahl).

        Zusammengefasst wird deshalb, was in ALLEN beteiligten Dateien um
        DENSELBEN Betrag weiterrueckt. Die gemeldete Laenge waechst je
        Fenster um eine Zeile: aus "7 Stellen a 6 Zeilen" wird "1 Stelle
        a 12 Zeilen" - und das ist die Zahl, die zaehlt.
        """
        def zerlegen(orte):
            raus = []
            for ort in orte:
                datei, _t, nummer = ort.rpartition(':')
                if not nummer.isdigit():
                    return None
                raus.append((datei, int(nummer)))
            return raus

        def sortierschluessel(orte):
            zerlegt = zerlegen(orte)
            if zerlegt is None:
                return (1, orte[0], 0)
            return (0, zerlegt[0][0], zerlegt[0][1])

        offen = []      # [[Dateien, aktuelle Zeilen, Laenge, Startorte]]
        fertig = []
        for orte in sorted(roh, key=sortierschluessel):
            zerlegt = zerlegen(orte)
            if zerlegt is None:
                fertig.append((orte, fenster))
                continue
            dateien = tuple(d for d, _n in zerlegt)
            zeilen = tuple(n for _d, n in zerlegt)

            fortsetzung = None
            for eintrag in offen:
                if eintrag[0] != dateien:
                    continue
                spruenge = {neu_ - alt_
                            for alt_, neu_ in zip(eintrag[1], zeilen)}
                if len(spruenge) == 1 and 1 <= next(iter(spruenge)) <= 4:
                    fortsetzung = eintrag
                    break

            if fortsetzung is not None:
                fortsetzung[1] = zeilen
                fortsetzung[2] += 1
            else:
                offen.append([dateien, zeilen, fenster, list(orte)])

        for _dateien, _zeilen, laenge, startorte in offen:
            fertig.append((startorte, laenge))
        return fertig

    def _sammeln(self, datei, fenster, bloecke):
        roh = datei.read_text(encoding='utf-8', errors='replace').split('\n')
        # Normalisiert wird nur die Einrueckung: Wer Leerzeichen mitvergleicht,
        # findet Kopien nicht wieder, die eine Ebene tiefer eingerueckt sind.
        zeilen = [(nummer, z.strip()) for nummer, z in enumerate(roh, 1)]
        inhalt = [(n, z) for n, z in zeilen if z]
        kurz = self.kurz(datei)
        for start in range(len(inhalt) - fenster + 1):
            fensterzeilen = inhalt[start:start + fenster]
            erste = fensterzeilen[0][1]
            if self.UNINTERESSANT.match(erste):
                continue
            if all(self.NUR_HEREINGEHOLT.match(z) for _n, z in fensterzeilen):
                self.nur_importe += 1
                continue
            text = '\n'.join(z for _n, z in fensterzeilen)
            schluessel = hashlib.blake2b(text.encode('utf-8'),
                                         digest_size=16).hexdigest()
            bloecke[schluessel].append(Fundstelle(kurz, fensterzeilen[0][0]))
