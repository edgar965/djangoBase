# -*- coding: utf-8 -*-
u"""FixAusnahme - verschluckte Ausnahmen protokollieren statt verschwinden lassen.

DER BEFUND (assistant, 17.08.2026)
==================================
``protokoll`` meldete 636 except-Bloecke, die eine Ausnahme fangen und nichts
damit tun: 233 verschlucken sie vollstaendig (``pass``/``continue``/blankes
``return``), 403 behandeln etwas, hinterlassen aber keine Spur. 346 davon fangen
``except Exception`` - die breiteste Form, bei der jeder Programmierfehler
mitverschwindet. Betroffen: 212 Module, 138 davon ohne jeden Logger.

Von Hand ist das nicht zu machen, und pauschal ist es gefaehrlich. Deshalb ein
Fixer mit genau zwei Eingriffen, beide aus dem Code ableitbar (Einzelheiten in
``fix_ausnahme_datei``):

    logger.exception('<Funktion>: <Typ> gefangen')   in den Block
    # stumm gewollt: <Grund>                         ueber den Block

DIE MELDUNG ENTHAELT KEINE VARIABLEN
====================================
Nur Funktionsname und gefangener Typ. Damit kann durch diesen Umbau nichts
Geheimes ins Log geraten - kein Passwort, keine Mailadresse, kein Dateiinhalt.
Den Rest (Traceback) liefert ``logger.exception`` von selbst.

WO ER NICHT HINSCHREIBT
=======================
* ``tests``-Verzeichnisse: Ein geschluckter Fehler ist dort die Sache des Tests.
* Die Protokoll-Infrastruktur selbst (``logging``, ``middleware``, ``dblog``):
  Ein Log-Aufruf im Logger kann sich rekursiv aufrufen - genau deshalb steht
  dort ``# stumm gewollt:`` von Hand.
* Alles, was ``Fixer.raus()`` ausschliesst (Fremdcode, venv, Sicherungen).

DAS NETZ
========
Je Datei: ``compile()`` muss durchlaufen, die Zahl der Zeilen darf nur wachsen,
und ``protokoll`` muss die Datei danach mit WENIGER Befunden sehen. Faellt eine
der drei Pruefungen, wird genau diese Datei zurueckgespielt.
"""
import ast

from .fix_ausnahme_datei import Ausnahmedatei
from .anlassfall import Anlassfall
from .fixer import Aenderung, Fixer, Vorschau

__all__ = ["FixAusnahme"]


class FixAusnahme(Fixer):
    slug = "fix-ausnahme"
    #: Der Befund, den dieser Fixer behebt — als Kennung des
    #: Werkzeugs, das ihn meldet. Die Oberflaeche zeigt daraus die
    #: NUMMER der Pruefung in der Tabelle statt einer
    #: Kriteriums-Nummer, die dort nirgends steht.
    behebt = 'protokoll'
    titel = "Verschluckte Ausnahmen protokollieren"
    tut = ("Setzt in jeden stummen except-Block einen `logger.exception(…)` mit "
           "Funktionsname und gefangenem Typ — und dort, wo Schweigen richtig "
           "ist (ImportError, KeyboardInterrupt), den Vermerk `# stumm "
           "gewollt: <Grund>`.")
    warum = ("`except Exception: pass` macht aus einem Absturz eine leere Seite, "
             "und die Ursache steht nirgends. Im Projekt assistant traf das 636 "
             "Stellen in 212 Modulen, 346 davon mit `except Exception`.")
    grenzen = ("Tests, die Logging-Infrastruktur selbst und Fremdcode bleiben "
               "unberührt. Ein Block mit `continue` bekommt `logger.debug` statt "
               "`exception` — sonst schreibt ein Lauf über 100.000 Zeilen "
               "100.000 Tracebacks.")
    kriterium = 16
    dauer = "5–20 s"

    anlassfall = Anlassfall(
        # NICHT `test…` oder `…middleware…` nennen: Diese Pfadteile stehen in
        # NICHT_HIER, und die Datei fiele aus dem Lauf — der Anlassfall
        # meldete dann „blind", obwohl der Fixer richtig arbeitet.
        {"holen.py": "import json\n"
                     "\n\n"
                     "def lesen(pfad):\n"
                     "    try:\n"
                     "        return json.loads(open(pfad).read())\n"
                     "    except Exception:\n"
                     "        pass\n"
                     "    return None\n"},
        mindestens=1, hoechstens=1, erwartet_in="holen.py",
        warum="Ein `except Exception: pass` macht aus einem Absturz eine leere "
              "Seite — die Ursache ist mit der Antwort weg")

    #: Pfadteile, in denen nicht instrumentiert wird (siehe Modulkopf).
    NICHT_HIER = ("tests", "test", "logging_utils.py", "middleware", "dblog.py",
                  "conftest.py")

    def __init__(self, hoechstens=0):
        #: Obergrenze fuer einen Lauf (0 = alle). Erlaubt es, in Etappen zu
        #: gehen und nach der ersten Etappe die Anwendung anzusehen.
        self.hoechstens = hoechstens
        self._protokoll = None

    def pruefer(self):
        u"""Das Pruefwerk, das die stummen Bloecke findet.

        DIESELBE WURZEL WIE DER FIXER (25.08.2026)
        ==========================================
        Hier stand nur ``Protokoll()`` — mit der EIGENEN Wurzel des
        Pruefwerks, nicht der des Fixers. ``vorschau()`` durchsuchte damit
        immer das ganze Projekt, gleichgueltig worauf der Fixer gerichtet
        war. Aufgefallen ist es, als `anlassfall-check` erstmals auch die
        Fixer pruefte::

            fix-ausnahme   im Anlassfall 32   im Leeren 32
            -> meldet im Leeren 32 — sucht nicht in der übergebenen Wurzel

        Im gewoehnlichen Lauf faellt das nicht auf, weil beide Wurzeln
        dieselbe sind. Bei einem Werkzeug, das SCHREIBT, ist „durchsucht
        mehr als ihm gesagt wurde" trotzdem der falsche Zustand.
        """
        from .protokoll import Protokoll
        if self._protokoll is None:
            self._protokoll = Protokoll()
            self._protokoll.wurzel = self.wurzel
            # `raus()` des Fixers hat dieselbe Form wie `ausgeschlossen()`
            # des Pruefwerks: eine Menge von Verzeichnisnamen.
            self._protokoll.ausgeschlossen = self.raus
            # UND den Git-Filter. Ohne ihn filtert das innere Pruefwerk
            # gegen das echte Repo — im Probelauf sind die Pruefdateien
            # dort nicht bekannt, und der Fixer sieht nichts. Drei Dinge
            # muessen uebereinstimmen, nicht zwei: Wurzel, Ausschlussliste
            # UND die Frage, was ueberhaupt zum Projekt gehoert.
            self._protokoll.gitfilter = self.gitfilter
        return self._protokoll

    # ------------------------------------------------------------- Vorschau

    def vorschau(self):
        aus = []
        gesamt = 0
        for d in self.pruefer().dateien():
            if d.baum is None or not self.erlaubt(d.pfad):
                continue
            if any(t in d.name for t in self.NICHT_HIER):
                continue
            treffer = self._stumme(d)
            if not treffer:
                continue
            aenderung = self._datei(d, treffer)
            if aenderung is None:
                continue
            aus.append(aenderung)
            gesamt += 1
            if self.hoechstens and gesamt >= self.hoechstens:
                break
        return Vorschau(aus, hinweis=(
            "Die Meldung enthält nur Funktionsname und gefangenen Typ — keine "
            "Variablen. Nach dem Schreiben prüft das Netz je Datei: compile(), "
            "Zeilenzahl gewachsen, und `protokoll` sieht weniger Befunde."))

    def _stumme(self, d):
        u"""Die Handler, die ``protokoll`` in dieser Datei meldet."""
        pruefer = self.pruefer()
        aus = []
        for k in d.knoten(ast.ExceptHandler):
            if not k.body:
                continue
            if pruefer._ausnahme(d, k):        # dieselbe Frage wie im Pruefwerk
                aus.append(k)
        return aus

    def _datei(self, d, handler):
        """Eine Änderung für EINE Datei - oder None, wenn nichts zu tun ist."""
        datei = Ausnahmedatei(d.pfad, d.text, d.baum)
        logger = datei.loggername()
        braucht_logger = False
        # Von unten nach oben, damit die Zeilennummern der noch offenen Bloecke
        # gueltig bleiben (der Text wird erst in `neuer_text` zusammengesetzt,
        # die Reihenfolge hier entscheidet nur ueber die Zaehlung).
        for k in sorted(handler, key=lambda x: x.lineno, reverse=True):
            if datei.vermerken(k):
                continue
            braucht_logger = True
        if braucht_logger and logger is None:
            logger = datei.logger_anlegen()
        for k in sorted(handler, key=lambda x: x.lineno, reverse=True):
            if Ausnahmedatei.typname(k) in Ausnahmedatei.STUMM_ERLAUBT:
                continue
            datei.protokollieren(k, logger)
        if not datei.anzahl:
            return None
        return Aenderung(d.pfad, datei.was, datei.neuer_text())

    # ----------------------------------------------------------------- Netz

    def pruefen(self, aenderung):
        fehler = []
        text = aenderung.pfad.read_text(encoding="utf-8", errors="replace")
        try:
            baum = ast.parse(text)
            compile(text, str(aenderung.pfad), "exec")
        except SyntaxError as e:
            return ["kompiliert nicht mehr: Zeile %s, %s" % (e.lineno, e.msg)]
        # NAMEN, DIE ERST ZUR LAUFZEIT FEHLEN (17.08.2026)
        # ================================================
        # ``compile()`` sieht keinen NameError. In ``mail/models.py`` stand ein
        # ``import logging as _logging`` weiter unten; der Fixer hielt das fuer
        # den Import, setzte ``logger = logging.getLogger(__name__)`` an den
        # Kopf — die Datei kompilierte, und die ganze Anwendung startete nicht
        # mehr (``NameError: name 'logging' is not defined``). Ein Netz, das
        # nur kompiliert, faengt genau diese Klasse nicht.
        if "logging.getLogger" in text:
            gebunden = any(
                isinstance(k, ast.Import)
                and any(a.name == "logging" and a.asname is None for a in k.names)
                for k in baum.body)
            if not gebunden and self._nutzt_modulweit(baum):
                fehler.append("nutzt `logging.` auf Modulebene, bindet den Namen "
                              "aber nicht — das wäre ein NameError beim Import")
        # Zweite Frage: Sieht das Pruefwerk hier jetzt weniger? Ohne diese
        # Gegenprobe koennte der Fixer Zeilen einsetzen, die gar nicht als Log
        # gelten - und alle 636 Befunde blieben stehen, waehrend der Bericht
        # „geschrieben" sagt.
        from .werkzeug import Quelldatei
        neu = Quelldatei(aenderung.pfad, self.wurzel())
        offen = self._stumme(neu)
        if offen:
            fehler.append("noch %d stumme Blöcke — der Umbau hat nicht "
                          "gegriffen" % len(offen))
        return fehler

    @staticmethod
    def _nutzt_modulweit(baum):
        u"""Steht ein ``logging.<etwas>`` AUSSERHALB jeder Funktion?

        Nur dann fliegt der fehlende Name schon beim Import. Innerhalb einer
        Funktion darf ``import logging`` lokal stehen — so machen es
        ``mail/views/ImportView.py`` und ``DavAccountsView.py``, und das ist
        in Ordnung.
        """
        innen = set()
        for k in ast.walk(baum):
            if isinstance(k, (ast.FunctionDef, ast.AsyncFunctionDef)):
                for x in ast.walk(k):
                    innen.add(id(x))
        for k in ast.walk(baum):
            if (isinstance(k, ast.Attribute) and isinstance(k.value, ast.Name)
                    and k.value.id == "logging" and id(k) not in innen):
                return True
        return False
