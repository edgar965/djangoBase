# -*- coding: utf-8 -*-
u"""Verschieber - einen Testfall in eine andere Kategorie umhaengen.

    „mach in jeder tabelle eine neue Spalte, Überschrift „Verschieben". eine
    Combo Box, wo ich die aktuelle Kategorie sehe und durch auswahl in eine
    andere Kategorie verschieben kann." (Edgar, 17.08.2026)

WAS „KATEGORIE" HIER IST
========================
Der ORDNER. Die Hausordnung legt ``<app>/tests/<art>/`` fest, und genau daraus
liest die Seite die Art (``mail.tests.unit.test_x`` -> „unit"). „Verschieben"
heisst deshalb: Die Testdatei wandert in den Ordner der Zielkategorie. Nur so
faehrt der Fall danach wirklich mit „Alle Longrunner" und nicht mehr mit „Alle
Unit" — eine blosse Anzeige-Umbuchung waere eine Luege, weil die Sammellaeufe
weiter ueber die Ordner gehen.

EINE DATEI, MEHRERE FAELLE
==========================
Verschoben wird die ganze Datei. Steht in ``test_x.py`` mehr als ein Fall, gehen
alle mit — die Oberflaeche sagt das im Tooltip, statt es zu verschweigen. Eine
einzelne Methode aus ihrer Datei zu loesen waere Code-Chirurgie und gehoert nicht
in einen Klick.

WAS NICHT GEHT
==============
* Suiten (ganze Ordner) - dort steht die Kategorie im Ziel des Kommandos.
* Faelle aus einer ``testcases.js`` oder hinter einem Projekt-Endpunkt: Die
  kennt nur das Projekt, nicht djangoBase.
In beiden Faellen zeigt die Spalte die Kategorie an und laesst sich nicht
aendern.

DIE SICHERUNGEN
===============
Geschrieben wird nur, wenn ALLES stimmt: Ziel ist eine bekannte Art, die Quelle
liegt unter der Projektwurzel in einem ``tests``-Baum, heisst ``test_*.py``, und
am Ziel liegt noch keine Datei dieses Namens. Sonst passiert nichts und die
Antwort nennt den Grund.
"""
import logging
import shutil
from pathlib import Path

from django.conf import settings

from .testbefehle import Testbefehle
from .testhistorie import Testhistorie

__all__ = ["Verschieber"]

log = logging.getLogger("djangobase.tests")


class Verschieber:
    """Findet die Datei eines Testfalls und hängt sie in eine andere Art um."""

    ARTEN = Testbefehle.ARTEN
    #: Anzeigenamen der Kategorien - dieselbe Quelle wie die Reiter.
    NAMEN = Testbefehle.KURZ

    def __init__(self, wurzel=None, bereiche=None):
        self.wurzel = Path(wurzel or getattr(settings, "BASE_DIR", "."))
        #: Die zweite Einteilung (Chat, Mail, Musik, …). Sie kommt aus den
        #: Einstellungen des Projekts - siehe :mod:`.testbereiche`.
        if bereiche is None:
            from .testbereiche import Bereiche
            bereiche = Bereiche.aus_einstellungen()
        self.bereiche = bereiche
        #: {Modulpfad: Datei|None} - siehe :meth:`modul`.
        self._module = {}

    # --------------------------------------------------------------- Lesen

    #: Anzeigename der Faelle, die djangoBase selbst mitbringt.
    EIGENE_KATEGORIE = "DjangoBase"

    @staticmethod
    def aus_djangobase(test_id):
        u"""Stammt der Fall aus djangoBase selbst (statt aus dem Projekt)?

        Am Modulpfad erkannt, nicht am Ordner: djangoBase laeuft als editable
        Install, seine Testmodule heissen immer ``djangobase.…`` — egal, wo das
        Paket auf der Platte liegt. Diese Faelle sind nicht verschiebbar (sie
        gehoeren der Bibliothek) und stehen in der Liste des Projekts nur im
        Weg; sichtbar sind sie ueber die Einstellung
        ``DJANGOBASE["tests_djangobase_sichtbar"]``.
        """
        return str(test_id or "").startswith("djangobase.")

    @classmethod
    def art_von(cls, test_id):
        u"""Die Kategorie einer Test-ID - oder ``""``.

        ``mail.tests.unit.test_x.Klasse.test_fall`` -> ``unit``
        """
        for teil in str(test_id or "").split("."):
            if teil in cls.ARTEN:
                return teil
        return ""

    def modul(self, test_id):
        u"""Die Datei hinter einer Test-ID - oder ``None``.

        Die ID endet auf ``Klasse.test_fall``; davor steht der Modulpfad. Weil
        die Zahl der Endstuecke schwanken kann (Unterklassen, ``subTest``), wird
        von hinten gekuerzt, bis eine Datei existiert.

        GEMERKT je Modulpfad (18.08.2026, „der aufbau der testseiten ist
        langsam"): Die Datei haengt am MODUL, nicht am einzelnen Fall — 335
        Component-Faelle teilen sich rund 40 Dateien. Ohne das kostete jede
        Tabellenzeile ihre eigene Suche auf der Platte: gemessen 5.224
        ``is_file``-Aufrufe je Seitenaufbau.
        """
        teile = str(test_id or "").split(".")
        if len(teile) < 2:
            return None
        # Klasse und Methode weg - der Rest ist der Modulpfad.
        schluessel = ".".join(teile[:-2]) or ".".join(teile)
        if schluessel in self._module:
            return self._module[schluessel]
        gefunden = None
        for schnitt in range(len(teile) - 1, 0, -1):
            pfad = self.wurzel.joinpath(*teile[:schnitt]).with_suffix(".py")
            if pfad.is_file():
                gefunden = pfad
                break
        self._module[schluessel] = gefunden
        return gefunden

    def moeglich(self, test_id):
        u"""``(art, datei)`` wenn verschiebbar, sonst ``(art, None)``."""
        art = self.art_von(test_id)
        datei = self.modul(test_id) if art else None
        if datei is None:
            return art, None
        if not datei.name.startswith("test_"):
            return art, None
        if art not in [t for t in datei.parts]:      # Ordner muss die Art tragen
            return art, None
        return art, datei

    # -------------------------------------------------------------- Schreiben

    def verschieben(self, test_id, ziel_art):
        u"""Datei in den Ordner der Zielkategorie legen.

        Zurueck kommt ``(erfolg, meldung, neue_id)``. Es wird NICHTS angefasst,
        solange nicht alle Bedingungen erfuellt sind.
        """
        if ziel_art not in self.ARTEN:
            return False, "Unbekannte Kategorie: %s" % ziel_art, ""
        art, datei = self.moeglich(test_id)
        if datei is None:
            return False, ("Dieser Fall lässt sich nicht verschieben — die Datei "
                           "liegt nicht in einem `tests/<art>/`-Ordner."), ""
        if art == ziel_art:
            return False, "Liegt schon in dieser Kategorie.", test_id
        ziel_ordner = self._ziel_ordner(datei, art, ziel_art)
        if ziel_ordner is None:
            return False, ("Zielordner nicht ermittelbar — erwartet wird "
                           "`…/tests/%s/`." % art), ""
        ziel = ziel_ordner / datei.name
        if ziel.exists():
            return False, ("Am Ziel liegt schon eine Datei %s — bitte dort "
                           "zuerst aufräumen." % datei.name), ""
        try:
            ziel_ordner.mkdir(parents=True, exist_ok=True)
            self._paket_marke(ziel_ordner)
            shutil.move(str(datei), str(ziel))
        except OSError as fehler:
            log.exception("Test %s konnte nicht nach %s verschoben werden",
                          test_id, ziel_art)
            return False, "Verschieben fehlgeschlagen: %s" % fehler, ""
        neue_id = str(test_id).replace(".%s." % art, ".%s." % ziel_art, 1)
        self._historie_umhaengen(datei, art, ziel_art)
        praefix = self._modulpraefix(datei)
        if praefix:
            self._reihenfolge_umziehen(
                praefix, praefix.replace(".%s." % art, ".%s." % ziel_art, 1))
        log.info("Test verschoben: %s -> %s (%s)", datei.name, ziel_art, ziel)
        return True, ("%s liegt jetzt in „%s“."
                      % (datei.name, self.NAMEN.get(ziel_art, ziel_art))), neue_id

    # ------------------------------------------------------- Bereich wechseln

    def bereich_moeglich(self, test_id):
        u"""``(slug, datei)`` wenn der Bereich wechselbar ist, sonst ``(slug, None)``.

        Dieselben Bedingungen wie beim Kategoriewechsel — plus: Es muss ein
        Zielbereich mit Modulpraefix konfiguriert sein. Ein Bereich, der nur
        umbenennt, hat keinen Ordner und kann kein Ziel sein.
        """
        slug = self.bereiche.slug_von(test_id)
        _art, datei = self.moeglich(test_id)
        if datei is None or not self.bereiche.mit_ordner():
            return slug, None
        return slug, datei

    def bereich_verschieben(self, test_id, ziel_slug):
        u"""Die Testdatei in den Ordner eines ANDEREN Bereichs legen.

            „der Bereich und die Kategorie können bei jedem test in der Tabelle
            per Combo Box geändert werden" (Edgar, 17.08.2026)

        Gleiche Bauart wie :meth:`verschieben`, nur wandert die Datei quer statt
        laengs: Die Kategorie (der ``<art>``-Ordner) bleibt, der Weg davor
        wechselt auf das Praefix des Zielbereichs::

            search/tests/musik/unit/test_midi.py
            -> search/tests/chat/unit/test_midi.py

        Das ueberschreitet auch App-Grenzen (``mail.tests`` -> ``search.tests.
        musik``) — genau das war die Ansage, und es ist derselbe Vorgang: Der
        Bereich IST der Ordner, sonst wuerde ein Sammellauf ueber den Bereich
        den Fall nicht mitfahren.
        """
        # NUR erlaubte Ziele: Ein Bereich, der ueber anderen liegt
        # (`search.tests` ueber `search.tests.chat`), wuerde die Datei aus der
        # Bereichsgliederung herausheben — siehe `Bereiche.ziele`.
        ziel = self.bereiche.ziele().get(str(ziel_slug or ""), "")
        if not ziel:
            return False, ("Kein gültiges Ziel: %s (unbekannt oder Elternordner "
                           "anderer Bereiche)" % ziel_slug), ""
        art, datei = self.moeglich(test_id)
        if datei is None:
            return False, ("Dieser Fall lässt sich nicht verschieben — die Datei "
                           "liegt nicht in einem `tests/<art>/`-Ordner."), ""
        if self.bereiche.slug_von(test_id) == ziel_slug:
            return False, "Liegt schon in diesem Bereich.", test_id
        ziel_ordner = self.wurzel.joinpath(*ziel.split(".")) / art
        neu_praefix = "%s.%s.%s" % (ziel, art, datei.stem)
        ziel_datei = ziel_ordner / datei.name
        if ziel_datei.exists():
            return False, ("Am Ziel liegt schon eine Datei %s — bitte dort "
                           "zuerst aufräumen." % datei.name), ""
        alt_praefix = self._modulpraefix(datei)
        try:
            ziel_ordner.mkdir(parents=True, exist_ok=True)
            self._paket_marke(ziel_ordner)
            # Auch die Zwischenebene braucht die Marke: `search/tests/chat/`
            # ohne __init__.py findet Djangos Discovery nicht.
            self._paket_marke(ziel_ordner.parent)
            shutil.move(str(datei), str(ziel_datei))
        except OSError as fehler:
            log.exception("Test %s konnte nicht in den Bereich %s verschoben "
                          "werden", test_id, ziel_slug)
            return False, "Verschieben fehlgeschlagen: %s" % fehler, ""
        neue_id = neu_praefix + str(test_id)[len(alt_praefix):] \
            if alt_praefix and str(test_id).startswith(alt_praefix) else ""
        self._historie_umziehen(alt_praefix, neu_praefix)
        self._reihenfolge_umziehen(alt_praefix, neu_praefix)
        log.info("Test-Bereich gewechselt: %s -> %s (%s)",
                 datei.name, ziel_slug, ziel_datei)
        return True, ("%s liegt jetzt im Bereich „%s“."
                      % (datei.name, self.bereiche.name_von(ziel_slug))), neue_id

    def _ziel_ordner(self, datei, art, ziel_art):
        u"""Der Schwesterordner der Zielkategorie - ``…/tests/<ziel_art>/``.

        Gesucht wird der Ordner, der die ALTE Art traegt; sein Nachbar mit dem
        neuen Namen ist das Ziel. Damit landet die Datei im selben ``tests``-Baum
        und nicht irgendwo unter der Projektwurzel.
        """
        for eltern in datei.parents:
            if eltern.name == art:
                return eltern.parent / ziel_art
        return None

    @staticmethod
    def _paket_marke(ordner):
        u"""``__init__.py`` anlegen, falls der Zielordner neu ist.

        Ohne sie findet Djangos Discovery den Ordner nicht — der Fall waere nach
        dem Verschieben aus jeder Liste verschwunden."""
        marke = ordner / "__init__.py"
        if not marke.exists():
            marke.write_text("", encoding="utf-8")

    def _historie_umhaengen(self, datei, art, ziel_art):
        u"""Laufzeiten der VERSCHOBENEN DATEI mitnehmen.

        Sonst stuende der Fall danach auf „noch nie gelaufen": Die Test-ID
        enthaelt die Art, nach dem Umzug heisst derselbe Fall anders.

        NUR DIESE DATEI (Fehler vom 17.08.2026, beim Probelauf gefunden): Die
        erste Fassung nahm jede ID, in der ``.unit.`` vorkam — also auch
        ``mail.tests.unit.…`` und ``search.tests.unit.…``. Der Umzug EINER Datei
        haette damit die Laufzeiten aller Unit-Tests des Projekts auf die neue
        Kategorie umgeschrieben, lautlos. Gemessen wird jetzt am Modulpraefix.
        """
        alt_praefix = self._modulpraefix(datei)
        if not alt_praefix:
            return
        self._historie_umziehen(
            alt_praefix, alt_praefix.replace(".%s." % art, ".%s." % ziel_art, 1))

    @staticmethod
    def _reihenfolge_umziehen(alt_praefix, neu_praefix):
        u"""Auch den Platz („Nr.") mitnehmen - gleiche Ueberlegung wie oben."""
        from .testreihenfolge import Reihenfolge
        Reihenfolge().umhaengen(alt_praefix, neu_praefix)

    @staticmethod
    def _historie_umziehen(alt_praefix, neu_praefix):
        u"""Laufzeiten von einem Modulpraefix auf ein anderes schreiben.

        Der gemeinsame Kern von Kategorie- und BEREICHS-Wechsel. Er fehlte beim
        Bereichswechsel schlicht (``AttributeError`` im Betrieb, 17.08.2026) —
        die Datei war da schon verschoben, die Antwort kam als Fehlerseite.

        NUR DIESES PRAEFIX: Die erste Fassung des Kategoriewechsels nahm jede
        ID, in der ``.unit.`` vorkam, und haette die Laufzeiten aller
        Unit-Tests des Projekts umgeschrieben. Verglichen wird deshalb der
        Modulpfad der EINEN Datei.
        """
        if not alt_praefix or not neu_praefix or alt_praefix == neu_praefix:
            return
        historie = Testhistorie()
        umzug = {k: v for k, v in historie.daten["tests"].items()
                 if k.startswith(alt_praefix + ".")}
        if not umzug:
            return
        for alt, reihe in umzug.items():
            historie.daten["tests"].pop(alt, None)
            historie.daten["tests"][neu_praefix + alt[len(alt_praefix):]] = reihe
        historie.schreiben()

    def _modulpraefix(self, datei):
        u"""``…/firma/tests/unit/test_parser.py`` -> ``firma.tests.unit.test_parser``."""
        try:
            teile = datei.relative_to(self.wurzel).with_suffix("").parts
        except ValueError:
            return ""
        return ".".join(teile)

    # ------------------------------------------------------------- Anzeige

    @classmethod
    def auswahl(cls, art, moeglich):
        u"""Die Einträge der Combo-Box - ``[(wert, name, ausgewaehlt)]``.

        Alle sechs Arten stehen drin, auch die, die im Projekt noch keinen Ordner
        hat: Der Ordner wird beim Verschieben angelegt. Ist der Fall nicht
        verschiebbar, kommt nur die aktuelle Kategorie zurueck.
        """
        # Reihenfolge und Namen wie in den Reitern - beides ist einstellbar
        # (siehe `testarten.Arten`), und zwei verschiedene Reihenfolgen fuer
        # dieselbe Sache waeren genau der Unterschied, der niemandem auffaellt.
        from .testarten import Arten
        einteilung = Arten.aus_einstellungen()
        if not moeglich:
            return [(art, einteilung.name_von(art) if art else "—", True)]
        return [(a, einteilung.name_von(a), a == art)
                for a in einteilung.liste()]
