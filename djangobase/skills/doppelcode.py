"""Doppelcode — gleiche Codebloecke an mehreren Stellen."""

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
                   "        raise ValueError('zu gross')\n"
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
    zweck = ('Sucht identische Codebloecke (Vorgabe: ab 6 Zeilen) in Python-, '
             'JavaScript- und HTML-Dateien und zeigt alle Fundstellen.')
    abhilfe = ('Vor dem Zusammenfassen von Modulen. Doppelter Code faellt im '
            'Alltag nicht auf, weil die Kopien in verschiedenen Dateien liegen '
            '— und wird bei Aenderungen genau deshalb nur an einer Stelle '
            'nachgezogen.')
    befund = ('Im Ursprungsprojekt stand die Aufklapp- und Auswahllogik eines '
             'Auswahlfeldes Zeile fuer Zeile in VIER Vorlagen, das Fuellen '
             'eines Modell-Feldes in fuenf. Beides jetzt je ein ES-Modul.')
    dauer = 'Sekunden bis eine Minute'
    eingabe = ('mindestens', 'Ab wie vielen gleichen Zeilen melden?', '6')

    #: Zeilen, die als Blockanfang nichts taugen (zu haeufig, zu leer).
    UNINTERESSANT = re.compile(r'^\s*(#|//|/\*|\*|\}|\)|\]|$)')
    #: Hoechstens so viele Stellen anzeigen (die Kappung wird im Kopf genannt).
    ZEILEN = 200

    #: Derselbe Block in zwei Dateien - das ist der ganze Fall.
    _WIEDERHOLT = ("def preis_pruefen(betrag):\n"
                   "    if betrag < 0:\n"
                   "        raise ValueError('negativ')\n"
                   "    if betrag > 1000:\n"
                   "        raise ValueError('zu gross')\n"
                   "    return round(betrag, 2)\n")

    anlassfall = Anlassfall(
        {"eins.py": _WIEDERHOLT, "zwei.py": _WIEDERHOLT},
        mindestens=1, erwartet_in="eins.py",
        warum="Derselbe Block an zwei Stellen: Wer den einen fixt, vergisst "
              "den anderen — so entstehen zwei Wahrheiten")

    def pruefen(self, mindestens='6', **_argumente):
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

        befunde = []
        for fundstellen in bloecke.values():
            if len(fundstellen) < 2:
                continue
            # Ueberlappende Treffer derselben Datei nicht doppelt melden.
            orte = sorted({str(f) for f in fundstellen})
            if len(orte) < 2:
                continue
            befunde.append(Befund(
                orte[0], '%d gleiche Bloecke à %d Zeilen' % (len(orte), fenster),
                'auch: ' + ', '.join(orte[1:6]) + (' …' if len(orte) > 6 else ''),
                Befund.WARNUNG if len(orte) > 2 else Befund.HINWEIS))
        befunde.sort(key=lambda b: b.was, reverse=True)
        kopf = ['%d Dateien geprueft, Blockgroesse %d Zeilen' % (dateien, fenster),
                '%d Stellen mit mehrfach vorkommenden Bloecken' % len(befunde)]
        if len(befunde) > self.ZEILEN:
            # Kappung benennen, nicht verschweigen: Sonst liest sich die Liste
            # wie eine vollstaendige Bestandsaufnahme.
            kopf.append('angezeigt: die ersten %d — mit groesserer Blockgroesse '
                        'wird die Liste kuerzer und die Funde gewichtiger'
                        % self.ZEILEN)
        return Befundsatz(self.titel, kopf, befunde[:self.ZEILEN])

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
            text = '\n'.join(z for _n, z in fensterzeilen)
            schluessel = hashlib.blake2b(text.encode('utf-8'),
                                         digest_size=16).hexdigest()
            bloecke[schluessel].append(Fundstelle(kurz, fensterzeilen[0][0]))
