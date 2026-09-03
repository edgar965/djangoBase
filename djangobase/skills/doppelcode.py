"""Doppelcode — gleiche Codeblöcke an mehreren Stellen."""

import ast
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
    #: NACHGETRAGEN (30.08.2026, assistant): der Modul-Logger.
    #:
    #: Vier ``basis.py`` bekamen eine Warnung fuer ihren Modulkopf — drei
    #: Zeilen Erklaerung, zwei Importe und::
    #:
    #:     logger = logging.getLogger(__name__)
    #:
    #: Die eine Zeile machte aus einem uebergangenen Fenster einen Befund.
    #: Sie laesst sich so wenig zusammenfassen wie ein Import: ``__name__``
    #: ist in jeder Datei ein anderer, und genau darum steht sie dort. Wer
    #: dem Befund folgt, nimmt den Modulen ihren eigenen Logger — und die
    #: Regel „Logger statt print, je Modul einer" faellt.
    NUR_HEREINGEHOLT = re.compile(
        r'^\s*('
        r'import\s|from\s.+\simport\s|'                 # Python und ES
        r'export\s.*\sfrom\s|'                          # ES-Weitergabe
        r'\{%\s*(load|extends)\s|'                      # Django-Vorlagen
        r'#|//|/[*]|[*]|'                                        # Kommentarzeilen
        r'\w+\s*=\s*logging\.getLogger\(__name__\)|'    # Modul-Logger
        r'"""$|\'\'\'$'                                 # Ende des Docstrings
        r')')
    #: Der Startblock eines eigenstaendigen Skripts.
    #:
    #: DER FALL (03.09.2026, shortlongx)
    #: =================================
    #: 200 Warnungen, fast alle aus ``werkzeug/`` - und fast alle derselbe
    #: Block::
    #:
    #:     WURZEL = Path(__file__).resolve().parents[1]
    #:     sys.path.insert(0, str(WURZEL))
    #:     os.environ.setdefault("DJANGO_SETTINGS_MODULE", "...settings")
    #:     import django
    #:     django.setup()
    #:
    #: Er steht in jedem Skript, das Django braucht, und er MUSS es: Wer
    #: ihn in ein gemeinsames Modul auslagert, muss dieses Modul
    #: importieren - und braucht dafuer wieder den Pfad. Dieselbe
    #: Ueberlegung wie beim Importblock: Ein Befund, der nichts zu tun
    #: gibt, verdeckt die, die etwas zu tun geben.
    #:
    #: Streng gefasst: Eine Zuweisung zaehlt nur mit ``__file__`` oder
    #: einem Laufwerkspfad rechts. ``WURZEL = berechne()`` bleibt Code.
    NUR_STARTBLOCK = re.compile(
        r'^\s*('
        r'sys\.path\.(insert|append)\(|'
        r'os\.environ(\.setdefault)?[(\[]\s*[^)]*SETTINGS_MODULE|'
        r'django\.setup\(\)|'
        r'sys\.(stdout|stderr)\.reconfigure\(|'
        r'\w+\s*=\s*[^#]*__file__|'
        r'\w+\s*=\s*r?[\x22\x27][A-Za-z]:[\\/]'
        r')')
    #: Ein Fenster, das nur noch ZUMACHT.
    #:
    #: DER FALL (31.08.2026, assistant)
    #: ================================
    #: Jede Tabelle im Projekt endet gleich::
    #:
    #:     </td>
    #:     </tr>
    #:     {% endfor %}
    #:     </tbody>
    #:     </table>
    #:     </div>
    #:
    #: Sechs Zeilen, in dieser Reihenfolge, in jeder Vorlage mit einer
    #: Tabelle — und nichts davon laesst sich zusammenfassen: So endet
    #: eine HTML-Tabelle. Solche Fenster stellten einen grossen Teil der
    #: HTML-Befunde und gaben nichts zu tun.
    #:
    #: Gezaehlt wird streng: NUR wenn JEDE Zeile des Fensters allein
    #: zumacht. Ein Fenster mit einer einzigen Inhaltszeile bleibt ein
    #: Befund — dort steht dann etwas, das man teilen koennte.
    NUR_SCHLIESSEND = re.compile(
        r'^\s*('
        r'(</[A-Za-z][\w-]*>\s*)+|'                  # </td></tr> …
        r'\{%\s*end\w+\s*%\}|'                       # {% endfor %} …
        r'\{%\s*(else|empty)\s*%\}|'                 # {% else %}
        r'-->|'                                      # Ende eines Kommentars
        r'[)}\];,]+|'                                # Klammern und Kommas
        r'\)?\);?|\}\);?'                            # }); und Verwandte
        r')\s*$')

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
        #: Wie viele Fenster ganz in einem Docstring lagen. Gehoert in die
        #: Kopfzeile: Eine Ausnahme, die schweigt, ist ein blinder Fleck.
        self.nur_doku = 0
        self.nur_start = 0
        #: Wie viele Fenster nur Markup geschlossen haben.
        self.nur_zu = 0
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
        if self.nur_doku:
            kopf.append('%d Fenster uebergangen: reiner Docstring'
                        % self.nur_doku)
        if self.nur_start:
            kopf.append('%d Fenster uebergangen: Startblock eines Skripts'
                        % self.nur_start)
        if self.nur_zu:
            kopf.append('%d Fenster uebergangen: schliessen nur Markup'
                        % self.nur_zu)
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

    @staticmethod
    def _docstringzeilen(datei, text):
        u"""Zeilennummern, die zu einem Docstring gehoeren (nur ``.py``).

        WARUM EXAKT UND NICHT PER MUSTER (29.08.2026): Ein Docstring ist
        mehrzeiliger Text, und eine zeilenweise Suche sieht darin ganz
        normale Zeilen. `ast` weiss es genau — und weiss auch, was NUR wie
        ein Docstring aussieht (eine Zeichenkette mitten im Code ist keiner).

        Bei einem Syntaxfehler wird nichts ausgenommen: Lieber ein Befund zu
        viel als eine stille Ausnahme, die halbe Dateien schluckt.
        """
        if datei.suffix != '.py':
            return frozenset()
        try:
            baum = ast.parse(text)
        except (SyntaxError, ValueError):
            return frozenset()
        zeilen = set()
        for knoten in ast.walk(baum):
            if not isinstance(knoten, (ast.Module, ast.ClassDef,
                                       ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            erster = knoten.body[0] if knoten.body else None
            if (isinstance(erster, ast.Expr)
                    and isinstance(erster.value, ast.Constant)
                    and isinstance(erster.value.value, str)):
                zeilen.update(range(erster.lineno,
                                    (erster.end_lineno or erster.lineno) + 1))
        return frozenset(zeilen)

    def _sammeln(self, datei, fenster, bloecke):
        text = datei.read_text(encoding='utf-8', errors='replace')
        roh = text.split('\n')
        #: Zeilen, die zu einem Docstring gehoeren — siehe `_docstringzeilen`.
        docstring = self._docstringzeilen(datei, text)
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
            # BEIDE AUSNAHMEN ZUSAMMEN, nicht nacheinander (29.08.2026):
            # Ein Modulkopf ist beides — vier Zeilen Erklaerung, die
            # schliessenden Anfuehrungszeichen, dann `import uuid`. Getrennt
            # gefragt ist kein Fenster darueber rein das eine oder das andere,
            # und die Stellen blieben stehen. Ein Fenster, in dem JEDE Zeile
            # entweder hereingeholt ODER Docstring ist, enthaelt keinen Code.
            #
            # Ein wiederholter Docstring ist ausserdem richtig so: Vier
            # Modellklassen in vier Dateien duerfen viermal erklaeren, woher
            # sie kommen. Ein Befund, der verlangt, Dokumentation
            # zusammenzufassen, gibt nichts zu tun.
            in_doku = [n in docstring for n, _z in fensterzeilen]
            if all(self.NUR_HEREINGEHOLT.match(z)
                   or self.NUR_STARTBLOCK.match(z) or drin
                   for (_n, z), drin in zip(fensterzeilen, in_doku)):
                if any(in_doku):
                    self.nur_doku += 1
                elif any(self.NUR_STARTBLOCK.match(z)
                         for _n, z in fensterzeilen):
                    self.nur_start += 1
                else:
                    self.nur_importe += 1
                continue
            # Ein Fenster, das nur zumacht, enthaelt nichts zum Teilen.
            if all(self.NUR_SCHLIESSEND.match(z) for _n, z in fensterzeilen):
                self.nur_zu += 1
                continue
            text = '\n'.join(z for _n, z in fensterzeilen)
            schluessel = hashlib.blake2b(text.encode('utf-8'),
                                         digest_size=16).hexdigest()
            bloecke[schluessel].append(Fundstelle(kurz, fensterzeilen[0][0]))
