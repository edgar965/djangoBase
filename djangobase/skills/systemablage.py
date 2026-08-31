# -*- coding: utf-8 -*-
u"""Systemablage — Zwischendateien, die auf der Systemplatte landen.

DIE VORGESCHICHTE
=================
``tempfile.mkstemp()``, ``NamedTemporaryFile()`` und
``TemporaryDirectory()`` schreiben OHNE ``dir=`` in den
System-Zwischenspeicher — unter Windows nach
``C:\\Users\\…\\AppData\\Local\\Temp``. Aus dieser Gewohnheit sind in
einem Projekt rund **100 GB Datenmuell auf C:** entstanden.

Seither lautet die Hausregel: Zwischendateien liegen im
Projektverzeichnis, auf derselben Platte wie die Daten, die sie
begleiten.

WARUM DAS AUFRAEUMEN NICHT REICHT
=================================
Fast jede solche Stelle raeumt im ``finally`` auf — solange der Prozess
lebt. Ein abgebrochener Lauf, ein harter Neustart, ein Absturz: dann
bleibt die Kopie liegen. Und es sind selten kleine Dateien; gefunden
wurden (assistant, 29.08.2026):

    jeder Mail-Anhang, einmal vollstaendig
    zwei Kopien je PDF-Variante beim Verkleinern
    jedes Mitglied eines Archiv-Anhangs
    ein WAV je Aufnahme beim Entrauschen und Diarisieren

WAS GEMELDET WIRD
=================
Ein Aufruf von ``mkstemp``, ``mkdtemp``, ``NamedTemporaryFile``,
``TemporaryFile``, ``SpooledTemporaryFile`` oder ``TemporaryDirectory``
OHNE ``dir=``-Angabe.

Dazu ``gettempdir()`` (31.08.2026): Es legt nichts an, sondern NENNT den
Ort — und ``os.path.join(gettempdir(), "out.mp4")`` landet genauso auf C:.
Vier ``mkstemp``-Stellen einer Datei wurden gemeldet, die fuenfte Zeile
mit derselben Wirkung nicht.

WAS NICHT GEMELDET WIRD
=======================
* **Tests.** Ein Wegwerf-Verzeichnis in einer Pruefung verschwindet mit
  ihr, und es geht um Beispieldaten, nicht um Nutzdaten.
* ``dir=`` vorhanden — egal, was drinsteht. Wohin genau, entscheidet
  das Projekt.
* Kommentare und Docstrings (der Syntaxbaum kennt sie nicht als Aufruf).
* Eine Stelle mit dem Vermerk ``Lehre gilt hier nicht
  ("keine-temp-dateien-im-system")`` — siehe ``vermerk.py``.

  NACHGETRAGEN (31.08.2026): Dieses Werkzeug kannte gar keine
  Einzelfall-Ausnahme, nur eine Liste von Dateinamen. Im Projekt
  ``assistant`` steht eine Stelle, die den Vermerk ordnungsgemaess
  traegt und deren Grund nachlesbar stimmt: ACE-Step prueft den
  uebergebenen Pfad mit ``commonpath(...) == gettempdir()`` und weist
  jeden anderen mit einem Fehler ab. Eine belegte Ausnahme, die
  trotzdem jedes Mal gemeldet wird, macht die Liste unbrauchbar.
"""
import ast

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug
from .pruefdatei import Pruefdatei
from .vermerk import Vermerk

__all__ = ["Systemablage"]


class Systemablage(BefundWerkzeug):
    u"""Zwischendateien ohne ``dir=`` — sie landen auf der Systemplatte."""

    slug = "systemablage"
    titel = "Zwischendateien im System-Zwischenspeicher"
    zweck = ("Findet `tempfile.mkstemp()` und Verwandte ohne `dir=`. Sie "
             "schreiben unter Windows nach C:, nicht neben die Daten.")
    befund = ("Aus dieser Gewohnheit sind in einem Projekt rund 100 GB "
              "Datenmuell auf C: entstanden. Aufgeraeumt wird meist im "
              "`finally` — das hilft nur, solange der Prozess lebt.")
    abhilfe = ("`dir=` auf einen Ordner im Projekt setzen (etwa "
               "`BASE_DIR/tmp`, in `.gitignore`).")
    dauer = "unter 1 s"
    kriterium = 0

    anlassfall = Anlassfall(
        {"kopierer.py": (
            "import tempfile\n"
            "\n"
            "\n"
            "def kopieren(daten):\n"
            "    griff, pfad = tempfile.mkstemp(suffix='.pdf')\n"
            "    return pfad\n"),
         "sauber.py": (
            "import tempfile\n"
            "from django.conf import settings\n"
            "\n"
            "\n"
            "def kopieren(daten):\n"
            "    griff, pfad = tempfile.mkstemp(suffix='.pdf',\n"
            "                                   dir=settings.BASE_DIR)\n"
            "    return pfad\n")},
        mindestens=1, hoechstens=1, erwartet_in="kopierer.py",
        warum="Ohne `dir=` liegt die Kopie auf C:. `sauber.py` steht "
              "daneben, damit die Ausnahme (dir= vorhanden) nicht "
              "unbemerkt wegfaellt — sonst meldete das Werkzeug jede "
              "Zwischendatei, auch die richtig abgelegten.")

    #: Die Aufrufe, die einen Ort waehlen.
    ANLEGER = ("mkstemp", "mkdtemp", "NamedTemporaryFile", "TemporaryFile",
               "SpooledTemporaryFile", "TemporaryDirectory")

    #: `gettempdir()` legt selbst nichts an — es NENNT den Ort, und was
    #: danach kommt (`os.path.join(gettempdir(), "out.mp4")`), landet
    #: genauso auf C:. Gefunden am 31.08.2026 in
    #: `HumanBody/collision/test_collision.py`, direkt neben vier
    #: `mkstemp`-Stellen: Die vier meldete das Werkzeug, die fuenfte nicht.
    #: Ein `dir=` gibt es hier nicht — jeder Aufruf ist ein Befund.
    ORTSNENNER = ("gettempdir", "gettempdirb")

    #: Diese Datei beschreibt den Fehler, statt ihn zu machen.
    AUSNAHMEN = ("systemablage.py",)

    #: Anleger, die ihren Ordner NIE von selbst raeumen — bei ihnen gilt die
    #: Ausnahme fuer Pruefungen nicht.
    #:
    #: DER BELEG (31.08.2026, Projekt 3DTools): Im Systemtemp lagen **1.761
    #: Verzeichnisse** aus Pruefungen — 1.717 `kr_*` aus
    #: `test_skills_klassenreif.py`, 44 `kk_*` aus
    #: `test_skills_klassenkandidat.py`, das aelteste fuenf Tage alt. Beide
    #: riefen `tempfile.mkdtemp(prefix=…)` je Prueffall und raeumten nie.
    #:
    #: Die Ausnahme `_ist_test` hat das gedeckt, mit der Begruendung „ein
    #: Wegwerf-Verzeichnis in einer Pruefung verschwindet mit ihr". Das
    #: stimmt fuer `TemporaryDirectory` in einem `with` — und fuer
    #: `mkdtemp` gerade nicht: Es gibt einen Pfad zurueck und vergisst ihn.
    #: Die Ausnahme deckte damit genau den Schaden, den das Werkzeug
    #: verhindern soll. Es ist dieselbe Klasse wie die 779
    #: `mail_test_archive_*` im Projekt `assistant`.
    #:
    #: Abhilfe im Projekt: `djangobase/tests/wegwerfordner.py`.
    OHNE_SELBSTAUFRAEUMEN = ("mkdtemp", "mkstemp")

    #: Der Name, unter dem diese Lehre in einem Vermerk steht.
    LEHRE = "keine-temp-dateien-im-system"

    def pruefen(self, **_argumente):
        befunde = []
        dateien = 0
        #: Wie viele Stellen ein Vermerk ausgenommen hat. Gehoert in die
        #: Kopfzeile: Eine Ausnahme, die schweigt, ist ein blinder Fleck.
        self.ausgenommen = 0
        for pfad in self.projektdateien(".py"):
            if pfad.name in self.AUSNAHMEN:
                continue
            quelle = self._quelle(pfad)
            if quelle is None:
                continue
            try:
                baum = ast.parse(quelle)
            except (SyntaxError, ValueError):
                continue
            dateien += 1
            gefunden = self._aus_baum(baum, self.kurz(pfad),
                                      Vermerk(quelle))
            if self._ist_test(pfad):
                # In Pruefungen bleibt, was nie selbst aufraeumt — und die
                # Ortsnennung, die ueberhaupt nichts anlegt und deshalb
                # auch nichts aufraeumen KANN.
                bleibt = self.OHNE_SELBSTAUFRAEUMEN + self.ORTSNENNER
                gefunden = [b for b in gefunden
                            if any(a in b.was for a in bleibt)]
            befunde += gefunden
        kopf = ["%d Python-Dateien gelesen" % dateien,
                "%d Zwischendateien ohne `dir=`" % len(befunde)]
        if self.ausgenommen:
            kopf.append("%d Stelle(n) durch Vermerk ausgenommen"
                        % self.ausgenommen)
        return Befundsatz(self.titel, kopf, befunde)

    def _ist_test(self, pfad):
        u"""Liegt die Datei in einer Pruefung?

        Fuer `TemporaryDirectory`/`NamedTemporaryFile` heisst das:
        uebergehen — sie raeumen am Ende des `with`-Blocks. Fuer `mkdtemp`
        und `mkstemp` heisst es NICHTS; siehe `OHNE_SELBSTAUFRAEUMEN`.

        Die Frage selbst steht in `pruefdatei.py` — sie wird von mehr als
        einem Werkzeug gestellt.

        MIT DER WURZEL (Befund CodeRabbit, 31.08.2026): Ohne sie zaehlte der
        ABSOLUTE Pfad. Ein Projekt unter einem Ordner namens ``tests`` haette
        damit ausschliesslich Pruefungen enthalten — und dieses Werkzeug
        haette fast alle Befunde unterdrueckt, ohne dass etwas auffaellt.
        """
        return Pruefdatei.ist_es(pfad, self.wurzel())

    @staticmethod
    def _quelle(pfad):
        try:
            return pfad.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return None

    def _aus_baum(self, baum, name, vermerk):
        raus = []
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.Call):
                continue
            gerufen = self._name(knoten.func)
            if gerufen in self.ORTSNENNER:
                if vermerk.gilt_nicht(knoten.lineno, self.LEHRE):
                    self.ausgenommen += 1
                    continue
                raus.append(Befund(
                    "%s:%d" % (name, knoten.lineno),
                    "`%s()` nennt den System-Zwischenspeicher" % gerufen,
                    "Was von hier aus zusammengesetzt wird, landet unter "
                    "Windows auf C: — genauso wie ein `mkstemp()` ohne "
                    "`dir=`.",
                    Befund.WARNUNG))
                continue
            if gerufen not in self.ANLEGER:
                continue
            if any(k.arg == "dir" for k in knoten.keywords):
                continue
            if vermerk.gilt_nicht(knoten.lineno, self.LEHRE):
                self.ausgenommen += 1
                continue
            raus.append(Befund(
                "%s:%d" % (name, knoten.lineno),
                "`%s(...)` ohne `dir=`" % gerufen,
                "Die Datei landet im System-Zwischenspeicher, unter "
                "Windows auf C:. Aufgeraeumt wird meist im `finally` — "
                "das hilft nur, solange der Prozess lebt.",
                Befund.WARNUNG))
        return raus

    @staticmethod
    def _name(knoten):
        u"""Der gerufene Name — ``mkstemp`` wie ``tempfile.mkstemp``."""
        if isinstance(knoten, ast.Attribute):
            return knoten.attr
        if isinstance(knoten, ast.Name):
            return knoten.id
        return ""
