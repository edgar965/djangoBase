# -*- coding: utf-8 -*-
u"""FixDictKlasse - ein Rueckgabe-Dictionary zu einer Klasse machen.

WARUM DAS OHNE UMBAU DER AUFRUFER GEHT (16.08.2026)
===================================================
Kriterium 11 verlangt eine Klasse fuer jedes Dictionary mit mehr als drei festen
Schluesseln, das durch mehrere Funktionen geht. Der teure Teil daran ist
normalerweise nicht die Klasse - es sind die Aufrufer: jedes ``d["gesamt"]``
muesste ``d.gesamt`` werden, und jede uebersehene Stelle wirft erst zur Laufzeit.

Die MAPPING-BRUECKE loest das. Die neue Klasse beantwortet ``d["gesamt"]``,
``d.get(…)`` und ``"gesamt" in d`` genau wie vorher; neuer Code benutzt
``d.gesamt``. Kein Aufrufer muss mitwandern, und der Umbau ist rueckwaerts
vertraeglich.

WAS AUSDRUECKLICH FEHLT UND WARUM
=================================
``__bool__`` und ``__len__``. Beide entscheiden mit, was ``if ergebnis:``
bedeutet. Bei einem Dictionary heisst das „nicht leer", bei einem Ergebnis-Objekt
soll es „es liegt eines vor" heissen - und ein Objekt, das sich leer nennt,
faellt beim Aufrufer in den Fehlerzweig. Genau das drehte am 16.08.2026 zwoelf
von 35 Pfaden um, bevor es auffiel.

``__iter__`` wirft einen sprechenden ``TypeError``. ``for x in ergebnis`` ist
mehrdeutig - Schluessel? Werte? Zeilen? -, und still das Falsche zu tun ist
schlimmer als ein klarer Abbruch. ``dict(ergebnis)`` funktioniert trotzdem: dafuer
genuegen ``keys()`` und ``__getitem__``.

WANN ER NICHT ANFASST
=====================
Wenn ein Schluessel kein gueltiger Bezeichner ist, wenn das Ergebnis im selben
Modul durch ``json.dumps`` oder ``JsonResponse`` geht (dort braucht es ein
echtes Dictionary), oder wenn der Vermerk „Dictionary gewollt" schon dransteht.
"""
import ast
import keyword
import re

from .fix_vermerk import Serialisierungsweg
from .fixer import Aenderung, Fixer, Vorschau

MARKER = "Dictionary gewollt"


class Feldsatz:
    """Die festen Schluessel einer Rueckgabe - und der Name ihrer Klasse."""

    #: Funktionsnamen, die ueber den DATENTYP nichts aussagen.
    NICHTSSAGEND = {"as_dict", "to_dict", "dict", "daten", "datensatz", "leer",
                    "ergebnis", "zeile", "eintrag", "bauen", "erzeugen", "run",
                    "main", "aus", "info", "werte", "form"}
    #: Verben, die hinten wegkoennen: ``kennzahlen_bauen`` -> ``Kennzahlen``.
    VERBEN = ("_bauen", "_holen", "_rechnen", "_lesen", "_erzeugen", "_machen",
              "_liefern", "_sammeln", "_ermitteln", "_berechnen")

    def __init__(self, funktion, knoten, schluessel, modul):
        self.funktion = funktion
        self.knoten = knoten
        self.schluessel = list(schluessel)
        self.modul = modul
        #: Wird bei Namenskollision gesetzt und dem Klassennamen vorangestellt.
        self.vorsatz = ""

    @property
    def klassenname(self):
        """Ein Name, der den DATENSATZ benennt - nicht die Funktion.

        Die erste Fassung nahm stur den Funktionsnamen und schlug ``AsDict``,
        ``Leer`` und ``BloeckeUndZufall`` vor. Das sind Namen fuer Vorgaenge,
        nicht fuer Datentypen, und ein schlechter Name ueberlebt jeden Umbau.
        Deshalb: nichtssagende Funktionsnamen weichen dem MODULNAMEN, und
        angehaengte Verben fallen weg (16.08.2026).
        """
        roh = self.funktion.lstrip("_")
        for verb in self.VERBEN:
            if roh.endswith(verb):
                roh = roh[:-len(verb)]
                break
        if roh.lower() in self.NICHTSSAGEND or not roh:
            stamm = self.modul[:-3] if self.modul.endswith(".py") else self.modul
            name = self._camel(stamm)
            # ``grid_daten`` + „Daten" waere ``GridDatenDaten``.
            name = name if name.endswith(("Daten", "Satz")) else name + "Daten"
        else:
            name = self._camel(roh) or "Ergebnis"
        if self.vorsatz and not name.startswith(self.vorsatz):
            return self.vorsatz + name
        return name

    @staticmethod
    def _camel(roh):
        return "".join(t.capitalize() for t in roh.split("_") if t)

    @property
    def dateiname(self):
        teile = re.findall(r"[A-Z][a-z0-9]*", self.klassenname)
        return "_".join(t.lower() for t in teile) + ".py"

    @property
    def brauchbar(self):
        return all(s.isidentifier() and not keyword.iskeyword(s)
                   for s in self.schluessel)


class Klassentext:
    """Der Quelltext der neuen Klasse - Felder plus Mapping-Bruecke."""

    def __init__(self, satz):
        self.satz = satz

    def bauen(self):
        n = self.satz.klassenname
        f = self.satz.schluessel
        zeilen = ['# -*- coding: utf-8 -*-',
                  'u"""%s - <WOFÜR steht dieser Datensatz? Ein Satz — HANDARBEIT.>' % n,
                  '',
                  'Aus dem Rückgabe-Dictionary von ``%s`` in ``%s`` entstanden'
                  % (self.satz.funktion, self.satz.modul),
                  '(Kriterium 11: mehr als drei feste Schlüssel, mehrere Leser).',
                  '',
                  'Die Mapping-Brücke unten hält die alten Aufrufer am Leben:',
                  '``x["%s"]`` liest weiter, neuer Code schreibt ``x.%s``.' % (f[0], f[0]),
                  '"""',
                  '',
                  '',
                  'class %s:' % n,
                  '    """<Ein Satz, was dieser Datensatz bedeutet.>"""',
                  '',
                  '    #: Die Feldnamen in ihrer ursprünglichen Reihenfolge.',
                  '    FELDER = (%s)' % ", ".join('"%s"' % s for s in f) +
                  ("," if len(f) == 1 else ""),
                  '']
        zeilen += self._konstruktor(f)
        zeilen += self._bruecke(n)
        return "\n".join(zeilen)

    @staticmethod
    def _konstruktor(felder):
        kopf = "    def __init__(self, %s):" % ", ".join(felder)
        if len(kopf) > 95:
            kopf = "    def __init__(self,\n" + ",\n".join(
                " " * 17 + s for s in felder) + "):"
        return [kopf] + ["        self.%s = %s" % (s, s) for s in felder] + [""]

    @staticmethod
    def _bruecke(name):
        return [
            "    # ---- Mapping-Brücke: die alten Aufrufer bleiben unberührt ----",
            "    #",
            "    # KEIN __bool__ und KEIN __len__. Beide würden mitentscheiden, was",
            "    # ``if ergebnis:`` bedeutet — bei einem Dictionary „nicht leer\", hier",
            "    # aber „es liegt eines vor\". Ein Ergebnis, das sich leer nennt, fällt",
            "    # beim Aufrufer in den Fehlerzweig.",
            "",
            "    def __getitem__(self, name):",
            "        try:",
            "            return getattr(self, name)",
            "        except AttributeError:",
            "            raise KeyError(name) from None",
            "",
            "    def get(self, name, standard=None):",
            "        return getattr(self, name, standard)",
            "",
            "    def __contains__(self, name):",
            "        return name in self.FELDER",
            "",
            "    def keys(self):",
            "        \"\"\"Damit ``dict(x)`` weiter funktioniert — ohne __iter__.\"\"\"",
            "        return self.FELDER",
            "",
            "    def items(self):",
            "        return [(s, getattr(self, s)) for s in self.FELDER]",
            "",
            "    def __iter__(self):",
            "        raise TypeError(",
            "            \"%s lässt sich nicht durchlaufen — Schlüssel? Werte? \"" % name,
            "            \"Gemeint ist wohl .items() oder .FELDER.\")",
            "",
            "    def __repr__(self):",
            "        return \"%s(%%s)\" %% \", \".join(" % name,
            "            \"%s=%r\" % (s, getattr(self, s)) for s in self.FELDER)",
            "",
        ]


class FixDictKlasse(Fixer):
    slug = "fix-dictklasse"
    titel = "Rückgabe-Dictionary in eine Klasse überführen"
    tut = ("Legt für jedes Rückgabe-Dictionary mit >3 festen Schlüsseln eine "
           "Klasse in eigener Datei an und gibt sie statt des Dictionaries "
           "zurück — mit Mapping-Brücke, damit kein Aufrufer bricht.")
    warum = ("Gemessen an 68 Befunden: 51 davon haben zwei oder mehr Leser, das "
             "Kriterium greift also zu Recht. Der teure Teil sind sonst die "
             "Aufrufer — die Brücke macht ihn überflüssig.")
    grenzen = ("Nicht bei Schlüsseln, die keine Bezeichner sind, nicht bei "
               "JsonResponse/json.dumps im selben Modul, nicht bei bereits "
               "vermerkten Anzeigeformaten.")
    kriterium = 11
    dauer = "10–30 s"

    MIN_SCHLUESSEL = 4
    RAUS = ("__pycache__", "node_modules", "venv", "pythonVENV", ".git",
            "sicherung", "backup", "archiv", "migrations")
    #: Wo ein echtes Dictionary gebraucht wird.
    ROH_NOETIG = ("json.dumps", "JsonResponse", "**")

    #: Kriterium 11 verlangt „durch MEHRERE Funktionen".
    MIN_LESER = 2

    def __init__(self):
        self._belegte = None
        self._baeume = None
        self._importeure = None
        self._methoden = None

    @property
    def baeume(self):
        """{Pfad: Syntaxbaum} - einmal fuer das ganze Projekt."""
        if self._baeume is None:
            aus = {}
            for pfad in self._pyquellen():
                try:
                    aus[pfad] = ast.parse(pfad.read_text(encoding="utf-8"))
                except (OSError, SyntaxError, ValueError):
                    continue
            self._baeume = aus
        return self._baeume

    @property
    def importeure(self):
        """{importierter Name: {Dateien, die ihn holen}} - EINMAL aufgebaut.

        Die erste Fassung suchte die Importeure je Fundstelle neu und brauchte
        154 Sekunden fuer einen Knopfdruck: derselbe Durchlauf ueber tausend
        Syntaxbaeume, zwanzig Mal. Das ist der Befund „Arbeit in Schleifen",
        den das Nachbarwerkzeug meldet - hier im Fixer selbst.
        """
        if self._importeure is None:
            aus = {}
            for pfad, baum in self.baeume.items():
                for k in ast.walk(baum):
                    if isinstance(k, ast.ImportFrom):
                        for a in k.names:
                            aus.setdefault(a.name, set()).add(pfad)
            self._importeure = aus
        return self._importeure

    @property
    def eindeutige_methoden(self):
        """Methodennamen, die es im Projekt nur EINMAL gibt.

        Nur bei denen sagt ein ``x.name()`` eindeutig, welche gemeint ist.
        """
        if self._methoden is None:
            wo = {}
            for pfad, baum in self.baeume.items():
                for k in ast.walk(baum):
                    if not isinstance(k, ast.ClassDef):
                        continue
                    for m in k.body:
                        if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            wo.setdefault(m.name, set()).add(pfad)
            self._methoden = {n for n, w in wo.items() if len(w) == 1}
        return self._methoden

    def leser(self, pfad, funktion):
        """Wie viele Funktionen rufen ``funktion`` - und lesen damit das Dict?

        DIE ZAEHLWEISE IST ZWEIMAL DANEBENGEGANGEN, bevor sie stimmte
        (16.08.2026, an 68 Befunden gemessen):

            nur das eigene Modul       62 von 68 haetten „hoechstens einen Leser"
            reiner Namensabgleich      272 „Leser" fuer eine Funktion ``kennzahlen``
            eigenes Modul + Importeure 51 von 68 haben zwei oder mehr  ← richtig

        Die dritte Zahl hat das Kriterium bestaetigt, nicht entkraeftet - deshalb
        baut dieser Fixer die Klassen wirklich, statt die Regel aufzuweichen.
        """
        erlaubt = {pfad} | self.importeure.get(funktion, set())
        # METHODEN BRAUCHEN KEINEN IMPORT: ``obj.datensatz()`` ist ein Leser,
        # ohne dass der Name irgendwo importiert waere. Ist der Methodenname im
        # Projekt eindeutig, zaehlen deshalb alle Attributaufrufe mit - sonst
        # meldet der Fixer null Leser fuer eine Methode, die zwei hat.
        if funktion in self.eindeutige_methoden:
            erlaubt = set(self.baeume)
        gefunden = set()
        for anderer in erlaubt:
            baum = self.baeume.get(anderer)
            if baum is None:
                continue
            for f in ast.walk(baum):
                if not isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    continue
                if anderer == pfad and f.name == funktion:
                    continue
                for k in ast.walk(f):
                    if isinstance(k, ast.Call) and \
                            self._aufrufname(k.func) == funktion:
                        gefunden.add("%s:%s" % (anderer.name, f.name))
                        break
        return len(gefunden)

    @staticmethod
    def _aufrufname(knoten):
        if isinstance(knoten, ast.Name):
            return knoten.id
        if isinstance(knoten, ast.Attribute):
            return knoten.attr
        return ""

    @property
    def belegte_namen(self):
        """Alle Klassennamen im Projekt - gegen selbstgemachte Doppelnamen.

        In derselben Sitzung entstand ``BlockUrteil`` ein drittes Mal, weil beim
        Anlegen niemand nachgesehen hat. Kriterium 7 verbietet genau das.
        """
        if self._belegte is None:
            aus = set()
            for pfad in self._pyquellen():
                try:
                    text = pfad.read_text(encoding="utf-8")
                except OSError:
                    continue
                aus.update(re.findall(r"^class\s+(\w+)", text, re.M))
            self._belegte = aus
        return self._belegte

    def _pyquellen(self):
        for pfad in sorted(self.wurzel().rglob("*.py")):
            if any(t in self.RAUS for t in pfad.parts):
                continue
            yield pfad

    def _saetze(self, pfad, text, baum):
        zeilen = text.split("\n")
        for f in ast.walk(baum):
            if not isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            rueckgaben = [k for k in ast.walk(f)
                          if isinstance(k, ast.Return) and
                          isinstance(k.value, ast.Dict)]
            if len(rueckgaben) != 1:
                continue                      # mehrere Formen: Handarbeit
            k = rueckgaben[0]
            feste = [s.value for s in k.value.keys
                     if isinstance(s, ast.Constant) and isinstance(s.value, str)]
            if len(feste) != len(k.value.keys) or len(feste) < self.MIN_SCHLUESSEL:
                continue
            von = max(0, k.lineno - 7)
            if any(MARKER in z for z in zeilen[von:k.lineno]):
                continue
            if self.leser(pfad, f.name) < self.MIN_LESER:
                continue          # ein einzelner Leser ist kein Datentyp
            yield Feldsatz(f.name, k, feste, pfad.name)

    def vorschau(self):
        aenderungen = []
        for pfad in self._pyquellen():
            try:
                text = pfad.read_text(encoding="utf-8")
                baum = ast.parse(text)
            except (OSError, SyntaxError):
                continue
            saetze = list(self._saetze(pfad, text, baum))
            if not saetze:
                continue
            aenderungen += self._je_datei(pfad, text, saetze)
        return Vorschau(aenderungen,
                        "Die Klasse liegt in einer eigenen Datei (Kriterium 2). "
                        "Ihr Kopfkommentar ist ein Platzhalter — bitte füllen.")

    def _roh_noetig(self, pfad, funktion):
        """Geht DIESES Ergebnis wirklich in die Serialisierung?

        DREI FASSUNGEN, ZWEI DAVON UNBRAUCHBAR (16.08.2026):

            „json.dumps steht irgendwo im Modul"        70 von 133 blockiert
            „… oder irgendwo bei einem Leser"           17 von 20 blockiert
            „das Ergebnis fliesst nachweislich hinein"  ← gemessen, nicht geraten

        Die ersten beiden blockierten fast alles: In einer Django-Datei steht
        immer irgendwo ein ``JsonResponse``, meist fuer eine ganz andere
        Funktion. Gefragt ist der WEG dieses einen Ergebnisses, und den
        beantwortet ``Serialisierungsweg`` - dieselbe Klasse, die auch
        ``FixVermerk`` benutzt (Kriterium 6: keine zweite Fassung davon).

        Zusaetzlich bleibt eine Textprobe auf ``**``: Wird das Ergebnis
        irgendwo entpackt, traegt die Mapping-Bruecke nicht.
        """
        beleg = Serialisierungsweg(self.baeume, self.importeure).beleg(pfad,
                                                                      funktion)
        if beleg:
            return "geht über %s hinaus — dort wird ein echtes Dictionary " \
                   "gebraucht" % beleg
        if re.search(r"\*\*\s*%s\s*\(" % re.escape(funktion), self._text(pfad)):
            return "das Ergebnis wird mit ** entpackt"
        return ""

    @staticmethod
    def _text(pfad):
        try:
            return pfad.read_text(encoding="utf-8")
        except OSError:
            return ""

    def _je_datei(self, pfad, text, saetze):
        """Eine Aenderung je Datei; mehrere Saetze werden von hinten eingesetzt."""
        aus = []
        for satz in saetze:
            warnungen = []
            if not satz.brauchbar:
                warnungen.append("Schlüssel ist kein gültiger Bezeichner")
            roh = self._roh_noetig(pfad, satz.funktion)
            if roh:
                warnungen.append(roh)
            # BEI KOLLISION AUSWEICHEN, NICHT AUFGEBEN: ``Kennzahlen`` gibt es
            # dreimal im Projekt. Der Modulname davor macht den Namen eindeutig
            # UND sprechender - ``NetzGegenOrbKennzahlen`` sagt mehr als
            # ``Kennzahlen``. Erst wenn auch der belegt ist, bleibt die Stelle
            # liegen; ein drittes ``BlockUrteil`` entsteht hier nicht (Kriterium 7).
            if satz.klassenname in self.belegte_namen:
                satz.vorsatz = Feldsatz._camel(
                    satz.modul[:-3] if satz.modul.endswith(".py") else satz.modul)
                if satz.klassenname in self.belegte_namen:
                    warnungen.append("Klassenname %s ist schon vergeben"
                                     % satz.klassenname)
            # DIE NEUE DATEI DARF NIE DIE ALTE SEIN. ``grid_daten.py`` mit einer
            # Funktion ``datensatz`` ergab die Klasse ``GridDaten`` in
            # ``grid_daten.py`` - der Begleiter haette das Original ueberschrieben
            # und dabei den ganzen Modulinhalt verloren (16.08.2026, vor dem
            # ersten Schreibzugriff aufgefallen).
            if satz.dateiname == pfad.name:
                satz.vorsatz = "Satz"
            if satz.dateiname == pfad.name:
                warnungen.append("neue Datei hieße wie die alte (%s)" % pfad.name)
            was = "%s: %d Schlüssel → Klasse %s in %s" % (
                satz.funktion, len(satz.schluessel), satz.klassenname,
                satz.dateiname)
            if warnungen:
                aus.append(Aenderung(pfad, was, None, warnungen))
                continue
            aus.append(Aenderung(
                pfad, was, self._neuer_modultext(text, satz),
                begleiter=(pfad.parent / satz.dateiname,
                           Klassentext(satz).bauen())))
            aus[-1].felder = satz.schluessel
            # Nur EINE Aenderung je Datei: die zweite wuerde auf dem alten Text
            # aufsetzen und die erste ueberschreiben.
            break
        return aus

    def _neuer_modultext(self, text, satz):
        zeilen = text.split("\n")
        k = satz.knoten
        von, bis = k.lineno - 1, (k.end_lineno or k.lineno)
        einzug = " " * (len(zeilen[von]) - len(zeilen[von].lstrip()))
        werte = [self._ausdruck(text, w) for w in k.value.values]
        args = ", ".join("%s=%s" % (s, w)
                         for s, w in zip(satz.schluessel, werte))
        neu = "%sreturn %s(%s)" % (einzug, satz.klassenname, args)
        if len(neu) > 95:
            neu = ("%sreturn %s(\n" % (einzug, satz.klassenname) +
                   ",\n".join("%s    %s=%s" % (einzug, s, w)
                              for s, w in zip(satz.schluessel, werte)) + ")")
        modul = satz.dateiname[:-3]
        importzeile = "from %s%s import %s" % (self._punkt(text), modul,
                                               satz.klassenname)
        kopf = self._mit_import(zeilen[:von], importzeile)
        return "\n".join(kopf + neu.split("\n") + zeilen[bis:])

    @staticmethod
    def _punkt(text):
        """``"."`` oder ``""`` - der Import-Stil, den die Datei schon benutzt.

        SKRIPTE VERTRAGEN KEINEN RELATIVEN IMPORT (16.08.2026). Die Werkzeuge
        unter ``werkzeug/`` starten als ``python werkzeug/xyz.py``; dann liegt
        ihr eigenes Verzeichnis im Pfad und sie schreiben ``from zahl import
        Zahl``. Ein eingefuegtes ``from .xyz_daten import …`` warf dort sofort
        „attempted relative import with no known parent package" - vier Skripte
        auf einen Schlag, gefangen erst beim Startversuch.

        Deshalb wird nicht geraten, sondern abgelesen, wie die Datei es haelt.
        """
        if re.search(r"^from\s+\.\w", text, re.M):
            return "."
        if re.search(r"^if\s+__name__\s*==", text, re.M):
            return ""
        return "."

    @staticmethod
    def _ausdruck(text, knoten):
        return ast.get_source_segment(text, knoten) or "None"

    #: Import-Zeile auf Modulebene - RELATIVE eingeschlossen (``from .x import``).
    #:
    #: Hier stand ``^(import|from)\s+\w``, und der Punkt fiel durch das ``\w``.
    #: In Dateien, deren Importe ALLE relativ sind, fand die Suche deshalb
    #: keinen einzigen - und der Zweig darunter gab die Zeilen unveraendert
    #: zurueck. Ergebnis: Die Klasse wurde benutzt und nirgends importiert.
    #: Getroffen hat es 2 von 14 Umbauten (``dax_signal_tabelle.py``,
    #: ``orders_faelle.py``); gemeldet hat es das Vorwaermen des Servers mit
    #: „name 'DaxSignalTabelleDaten' is not defined", nicht der Fixer.
    IMPORTZEILE = re.compile(r"^(import|from)\s+[.\w]")

    @classmethod
    def _mit_import(cls, zeilen, importzeile):
        """Den Import hinter den letzten bestehenden setzen.

        Gibt es keinen, kommt er hinter den Modul-Docstring. STILL AUFGEBEN
        gibt es nicht: Ein Fixer, der die Verwendung schreibt und den Import
        weglaesst, erzeugt genau den Fehler, den er verhindern soll."""
        if any(importzeile in z for z in zeilen):
            return zeilen
        letzter = -1
        for i, z in enumerate(zeilen):
            if cls.IMPORTZEILE.match(z):
                letzter = i
        if letzter < 0:
            letzter = cls._nach_docstring(zeilen)
            return zeilen[:letzter] + [importzeile, ""] + zeilen[letzter:]
        return zeilen[:letzter + 1] + [importzeile] + zeilen[letzter + 1:]

    @staticmethod
    def _nach_docstring(zeilen):
        """Index der ersten Zeile hinter Kodierungszeile und Modul-Docstring."""
        i = 0
        while i < len(zeilen) and (not zeilen[i].strip()
                                   or zeilen[i].lstrip().startswith("#")):
            i += 1
        if i >= len(zeilen):
            return len(zeilen)
        auf = re.match(r"^[a-z]*(\"\"\"|''')", zeilen[i])
        if not auf:
            return i
        zeichen = auf.group(1)
        # Einzeiliger Docstring: Anfang und Ende in derselben Zeile.
        if zeilen[i].count(zeichen) >= 2:
            return i + 1
        for j in range(i + 1, len(zeilen)):
            if zeichen in zeilen[j]:
                return j + 1
        return i

    def pruefen(self, aenderung):
        """Beide Dateien müssen kompilieren, und die Felder müssen stimmen."""
        for pfad in [aenderung.pfad] + ([aenderung.begleiter[0]]
                                        if aenderung.begleiter else []):
            try:
                ast.parse(pfad.read_text(encoding="utf-8"))
            except SyntaxError as e:
                return ["%s kompiliert nicht: %s" % (pfad.name, e)]
            except OSError as e:
                return ["%s nicht lesbar: %s" % (pfad.name, e)]
        felder = getattr(aenderung, "felder", None)
        if felder and aenderung.begleiter:
            text = aenderung.begleiter[0].read_text(encoding="utf-8")
            fehlt = [f for f in felder if "self.%s = " % f not in text]
            if fehlt:
                return ["Felder fehlen in der Klasse: %s" % ", ".join(fehlt)]
        # EIN SKRIPT MIT RELATIVEM IMPORT STARTET NICHT MEHR. ``ast.parse`` sieht
        # das nicht - die Zeile ist syntaktisch tadellos und scheitert erst beim
        # Ausfuehren. Deshalb hier die Stilprobe: hat die Datei einen
        # ``__main__``-Block und sonst keinen einzigen relativen Import, war der
        # eingefuegte falsch.
        eigener = aenderung.pfad.read_text(encoding="utf-8")
        if re.search(r"^if\s+__name__\s*==", eigener, re.M):
            relative = re.findall(r"^from\s+\.(\w+)\s+import", eigener, re.M)
            if len(relative) == 1:
                return ["Skript mit __main__-Block, aber relativer Import "
                        "„from .%s" % relative[0] + "“ — das startet nicht"]
        return []
