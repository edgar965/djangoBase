# -*- coding: utf-8 -*-
u"""Ausnahmedatei - eine Python-Datei mit ihren stummen except-Bloecken umschreiben.

Hilfsklasse zu ``fix_ausnahme.FixAusnahme``; hier steht die ganze Textarbeit, dort
Vorschau, Sicherung und Netz.

WAS EINGESETZT WIRD - UND WARUM NICHTS ANDERES
==============================================
Nur ZWEI Eingriffe, beide aus dem Code ableitbar:

1. ``logger.exception(...)`` als erste Anweisung des Blocks. Die Meldung nennt
   die umgebende Funktion und den gefangenen Typ - keine Variablen, keine
   Vermutungen. Damit kann nichts Geheimes ins Log geraten, und die Zeile sagt
   trotzdem, WO es passiert ist.
2. ``# stumm gewollt: <Grund>`` für die Fälle, in denen Schweigen richtig IST
   und der Grund am gefangenen Typ ablesbar ist:

       except ImportError        -> optionale Abhaengigkeit
       except ModuleNotFoundError-> dito
       except KeyboardInterrupt  -> Abbruch durch den Nutzer ist kein Fehler

WAS ABSICHTLICH NICHT PASSIERT
==============================
* Die ``except``-Zeile wird nicht um ``as e`` erweitert. ``logger.exception``
  braucht keinen Namen (es liest die laufende Ausnahme) - und ein neuer Name
  könnte einen vorhandenen ueberdecken.
* In einer Schleife, die den Eintrag überspringt (``continue``), wird
  ``logger.debug`` statt ``logger.exception`` gesetzt. Sonst schreibt ein Lauf
  über 100.000 Zeilen 100.000 Traceback-Bloecke - aus einem stummen Fehler
  wuerde ein unlesbares Log.
* Dateien unter ``tests`` bleiben unberuehrt: Dort ist ein geschluckter Fehler
  die Sache des Tests, nicht der Anwendung.
"""
import ast
import re

__all__ = ["Ausnahmedatei"]


class Ausnahmedatei:
    """Eine Datei, ihre stummen Bloecke und der daraus entstehende neue Text."""

    #: Typen, bei denen Schweigen richtig ist - mit dem Grund, der gesetzt wird.
    STUMM_ERLAUBT = {
        "ImportError": "optionale Abhängigkeit — ohne sie läuft der Rest weiter",
        "ModuleNotFoundError": "optionale Abhängigkeit — ohne sie läuft der "
                               "Rest weiter",
        "KeyboardInterrupt": "Abbruch durch den Nutzer ist kein Fehler",
    }
    #: Modulweiter Logger: ``name = logging.getLogger(...)``
    LOGGERZEILE = re.compile(r"^\s*([A-Za-z_]\w*)\s*=\s*logging\.getLogger\(")

    def __init__(self, pfad, text, baum):
        self.pfad = pfad
        self.zeilen = text.split("\n")
        self.baum = baum
        #: (Zeilennummer 1-basiert, Textzeilen) - von unten nach oben angewandt.
        self._einschuebe = []
        self._ersetzungen = {}
        self.gesetzt = {"log": 0, "vermerk": 0}

    # ------------------------------------------------------------------ Logger

    def loggername(self):
        u"""Name des vorhandenen Modul-Loggers - oder ``None``.

        Es wird der VORHANDENE Name benutzt (``log``, ``logger``, ``LOG`` …),
        nie ein neuer daneben gelegt: zwei Logger im selben Modul sind eine
        zweite Quelle, und die läuft auseinander.
        """
        for zeile in self.zeilen:
            treffer = self.LOGGERZEILE.match(zeile)
            if treffer:
                return treffer.group(1)
        return None

    def bindet_logging(self):
        u"""Ist der NAME ``logging`` auf Modulebene verfuegbar?

        NICHT per Textsuche: ``^\\s*import logging`` traf am 17.08.2026zweimal
        daneben und hat ``mail/models.py`` zerlegt.

        * ``import logging`` INNERHALB einer Funktion (Zeile 58 in
          ``ImportView.py``) — modulweit gilt der Name damit nicht.
        * ``import logging as _logging`` (Zeile 1215 in ``mail/models.py``) —
          gebunden wird ``_logging``, nicht ``logging``.

        Im zweiten Fall setzte der Fixer ``logger = logging.getLogger(__name__)``
        ohne Import: Die Datei kompilierte (``compile()`` sieht keinen
        NameError), und die ganze Anwendung startete nicht mehr. Deshalb
        entscheidet der Syntaxbaum, und nur die Modulebene zaehlt.
        """
        return any(isinstance(k, ast.Import)
                   and any(a.name == "logging" and a.asname is None
                           for a in k.names)
                   for k in self.baum.body)

    def logger_anlegen(self):
        u"""``logger = logging.getLogger(__name__)`` nach den Importen einsetzen.

        ``__name__`` und nicht ein fester Name: Die Projekte konfigurieren einen
        Logger je App (``mail``, ``search``); ``mail.services.X`` erbt davon
        ueber die Logger-Hierarchie und landet in derselben Datei. Ein fester
        Name muesste hier geraten werden.

        ZWEI Einschuebe, nicht einer: ``import logging`` gehoert an den ANFANG
        des Importblocks (Standardbibliothek zuerst), die Zuweisung dahinter.
        Der erste Wurf haengte beides hinten an - dann stand ein
        Standardimport unter den projekteigenen.
        """
        erster_import = letzter_import = 0
        for k in self.baum.body:
            if isinstance(k, (ast.Import, ast.ImportFrom)):
                # `from __future__ import …` MUSS die erste Anweisung der Datei
                # bleiben. Der erste Wurf setzte `import logging` davor — das
                # ist ein SyntaxError, den nur das Netz noch abgefangen hat.
                if not (isinstance(k, ast.ImportFrom) and k.module == "__future__"):
                    erster_import = erster_import or k.lineno
                letzter_import = max(letzter_import,
                                     getattr(k, "end_lineno", k.lineno))
            elif letzter_import:
                break
        hat_import = self.bindet_logging()
        zuweisung = ["", "logger = logging.getLogger(__name__)"]
        if hat_import:
            self._einschuebe.append((letzter_import + 1, zuweisung))
        elif erster_import:
            self._einschuebe.append((erster_import, ["import logging"]))
            self._einschuebe.append((letzter_import + 1, zuweisung))
        else:
            # Gibt es AUSSER `__future__` keinen Import, muessen beide Zeilen
            # DAHINTER — und in EINEM Einschub, sonst landet die Zuweisung ueber
            # ihrem eigenen Import (zwei Einschuebe auf derselben Zeilennummer
            # schieben sich gegenseitig nach unten). Zwei Dateien bestehen genau
            # daraus (`bank/context_processors.py`, `firma/…`) und wurden vom
            # Netz zurueckgespielt.
            self._einschuebe.append((letzter_import + 1,
                                     ["import logging"] + zuweisung))
        return "logger"

    # ---------------------------------------------------------------- Bloecke

    @staticmethod
    def typen(knoten):
        """ALLE gefangenen Typen als Liste - ``except (A, B)`` faengt beide."""
        t = knoten.type
        if t is None:
            return []
        if isinstance(t, ast.Tuple):
            return [getattr(e, "id", None) or getattr(e, "attr", "") or "?"
                    for e in t.elts]
        return [getattr(t, "id", None) or getattr(t, "attr", "") or "?"]

    @classmethod
    def typname(cls, knoten):
        """Erster gefangener Typ - für die Entscheidung „darf stumm bleiben"."""
        alle = cls.typen(knoten)
        return alle[0] if alle else ""

    def funktionsname(self, zeile):
        """Name der Funktion, in der ``zeile`` steht - für die Meldung."""
        name = ""
        for k in ast.walk(self.baum):
            if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if k.lineno <= zeile <= getattr(k, "end_lineno", k.lineno):
                    # Die INNERSTE passende Funktion gewinnt.
                    name = k.name
        return name or "Modulebene"

    def vermerken(self, handler):
        """``# stumm gewollt: <Grund>`` über den except-Block setzen."""
        typ = self.typname(handler)
        grund = self.STUMM_ERLAUBT.get(typ)
        if not grund:
            return False
        einzug = " " * handler.col_offset
        self._einschuebe.append((handler.lineno,
                                 ["%s# stumm gewollt: %s" % (einzug, grund)]))
        self.gesetzt["vermerk"] += 1
        return True

    #: Typen, deren Auftreten ERWARTET ist: eine Umwandlung schlaegt fehl, ein
    #: Schluessel fehlt, ein Datensatz ist nicht da. Ein Traceback je Vorkommen
    #: waere unbrauchbar (``_to_float`` laeuft ueber jede Zelle einer Tabelle),
    #: deshalb Meldung ohne Traceback.
    ERWARTET = {"ValueError", "TypeError", "KeyError", "IndexError",
                "AttributeError", "JSONDecodeError", "DoesNotExist",
                "UnicodeDecodeError", "StopIteration", "ZeroDivisionError",
                "ObjectDoesNotExist", "MultipleObjectsReturned"}

    @classmethod
    def stufe(cls, handler, typen):
        u"""Welche Log-Stufe passt - aus dem Code abgeleitet, nicht geraten.

        * ``continue`` im Rumpf: Der Block sitzt in einer Schleife und
          überspringt einen Eintrag. ``debug`` — bei 100.000 Zeilen wäre alles
          andere unlesbar.
        * erwarteter Typ (siehe ``ERWARTET``): ``warning`` — die Meldung steht
          im Log, ohne Traceback.
        * sonst (``Exception``, ``OSError``, blankes ``except``): ``exception``
          mit vollem Traceback. Hier ist die Ursache unbekannt, und genau die
          fehlte bisher.
        """
        if any(isinstance(x, ast.Continue) for x in handler.body):
            return "debug"
        if typen and all(t in cls.ERWARTET for t in typen):
            return "warning"
        return "exception"

    def protokollieren(self, handler, logger):
        u"""Log-Aufruf als erste Anweisung des Blocks einsetzen.

        Drei Fälle, alle am Rumpf ablesbar:

        * Der Block steht in EINER Zeile (``except X: pass``) - er wird auf zwei
          Zeilen gebracht, sonst liegt der Log-Aufruf hinter dem Doppelpunkt und
          der Rumpf verschwindet.
        * Der Rumpf ist genau ``pass`` - die Zeile wird ersetzt, ein ``pass``
          neben einem Log-Aufruf wäre Zierrat.
        * Sonst wird VOR die erste Anweisung eingesetzt.
        """
        typen = self.typen(handler) or ["Ausnahme"]
        funktion = self.funktionsname(handler.lineno)
        stufe = self.stufe(handler, typen)
        text = "%s: %s gefangen" % (funktion, "/".join(typen))
        erste = handler.body[0]
        einzug = " " * erste.col_offset
        aufruf = "%s%s.%s('%s')" % (einzug, logger, stufe, text)

        if erste.lineno == handler.lineno:
            # Einzeiler aufteilen: alles bis zum Doppelpunkt bleibt, der Rumpf
            # wandert eine Zeile tiefer.
            kopf = self.zeilen[handler.lineno - 1]
            schnitt = self._doppelpunkt(kopf)
            rumpf = kopf[schnitt + 1:].strip()
            tiefer = " " * (handler.col_offset + 4)
            neu = [kopf[:schnitt + 1], "%s%s.%s('%s')" % (tiefer, logger, stufe, text)]
            if rumpf and rumpf != "pass":
                neu.append(tiefer + rumpf)
            self._ersetzungen[handler.lineno] = neu
        elif isinstance(erste, ast.Pass):
            self._ersetzungen[erste.lineno] = [aufruf]
        else:
            self._einschuebe.append((erste.lineno, [aufruf]))
        self.gesetzt["log"] += 1
        return True

    @staticmethod
    def _doppelpunkt(zeile):
        u"""Position des Doppelpunkts, der den Block öffnet.

        ``except (A, B):`` und ``except X as e:`` haben nur einen; ein
        Doppelpunkt in einer Zeichenkette dahinter darf nicht gewinnen, deshalb
        wird von links bis zur ersten Klammertiefe 0 gesucht.
        """
        tiefe = 0
        for i, z in enumerate(zeile):
            if z in "([{":
                tiefe += 1
            elif z in ")]}":
                tiefe -= 1
            elif z == ":" and tiefe == 0:
                return i
        return len(zeile) - 1

    # ------------------------------------------------------------- Ergebnis

    def neuer_text(self):
        u"""Der geaenderte Dateiinhalt.

        ALLE Eingriffe in EINER Liste, streng von unten nach oben. Der erste
        Wurf lief zweimal durch (erst Ersetzungen, dann Einschuebe) - und weil
        eine Ersetzung die Zeilenzahl ändert (aus ``pass`` werden zwei Zeilen),
        zeigten die danach angewandten Zeilennummern ins Verrutschte. Von unten
        nach oben kann keine Änderung die Nummern der noch offenen treffen.
        """
        eingriffe = ([(n, "ersetzen", z) for n, z in self._ersetzungen.items()]
                     + [(n, "einschub", z) for n, z in self._einschuebe])
        # Gleiche Zeile: erst ersetzen, dann davor einschieben - so landet ein
        # Vermerk ueber dem neuen Text und nicht mitten darin.
        for nummer, art, neu in sorted(
                eingriffe, key=lambda x: (-x[0], 0 if x[1] == "ersetzen" else 1)):
            if art == "ersetzen":
                zeilen_bereich = slice(nummer - 1, nummer)
            else:
                zeilen_bereich = slice(nummer - 1, nummer - 1)
            self.zeilen[zeilen_bereich] = neu
        return "\n".join(self.zeilen)

    @property
    def anzahl(self):
        return self.gesetzt["log"] + self.gesetzt["vermerk"]

    @property
    def was(self):
        return ("%d Log-Aufruf(e), %d Vermerk(e)"
                % (self.gesetzt["log"], self.gesetzt["vermerk"]))
