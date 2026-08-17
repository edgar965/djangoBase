# -*- coding: utf-8 -*-
u"""Skills - der Werkzeugkasten. EINE Seite, EIN Paket, alle Werkzeuge.

WIE ES HIERHIN KAM (17.08.2026)
===============================
Es gab drei Werkzeugkaesten nebeneinander, an verschiedenen Tagen in
verschiedenen Sitzungen entstanden:

    skills   (3DTools-Durchgang)    12 Werkzeuge, Basis ``Werkzeug``
    skills2  (shortlongx-Durchgang) 28 Werkzeuge, Basis ``Werkzeug2``
    skills1  (Zusammenfuehrung)     beides ueber einen Adapter

Drei Seiten mit ueberlappenden Werkzeugen sind kein Werkzeugkasten, sondern drei
halbe. Deshalb ist dieses Paket jetzt der Master: Alle Module aus ``skills2`` und
``skills3`` (dem frueheren ``skills``) liegen HIER. ``skills2`` und ``skills3``
sind nur noch duenne Weiterleitungen auf dieses Paket, damit vorhandene Links,
Lesezeichen und Importe weiterlaufen - sie verschwinden, sobald niemand mehr
darauf zeigt.

ZWEI BASISKLASSEN, MIT ABSICHT
==============================
* ``Werkzeug2`` (``werkzeug.py``) ist die Basis fuer alles Neue: Tabelle aus
  Spalten und Zeilen, Quelldatei-Cache mit Syntaxbaum, Suche ab der
  REPO-Wurzel statt nur ``BASE_DIR``, abgestufte Bewertung, Bezug auf ein
  Kriterium.
* ``Werkzeug`` (``werkzeug_alt.py``) ist die aeltere Basis der 3DTools-Werkzeuge
  (Befund-Objekte, Textausgabe, einstellbare Schwellen). Sie wurde NICHT
  umgeschrieben: Elf laufende, belegte Werkzeuge fuer eine einheitliche
  Oberklasse anzufassen waere teurer als der Adapter - und riskanter.
  ``AltWerkzeug`` (``adapter.py``) bildet sie verlustfrei auf eine Tabelle ab.

Aufruf ueber Hilfe -> Skills (``djangobase/views/skills.py``) oder direkt:

    from djangobase.skills import werkzeug_finden
    erg = werkzeug_finden("modulzustand").laufen()
    print(erg.zusammenfassung)

Neues Werkzeug: von ``Werkzeug2`` ableiten, EINE Klasse je Datei, unten in
``NEUE`` eintragen.
"""
# --- Basis und Infrastruktur -------------------------------------------------
from .adapter import AltWerkzeug
from .basis import EigenesWerkzeug
from .bericht import Bericht
from .fixer import Aenderung, Fixer, Vorschau
from .kriterien import KRITERIEN as _KRITERIEN_BASIS
from .kriterien import OHNE_WERKZEUG
from .lehren import BEREICHE, LEHREN, Lehre, Lehrenstand, als_zeilen, gruppen
from .netz import Abnahme, Umbaunetz
from .werkzeug import Ergebnis, Quelldatei, Werkzeug2
from .werkzeug_alt import Ausgabe, Befund
from .werkzeug_alt import Ergebnis as ErgebnisAlt
from .werkzeug_alt import Werkzeug

# --- Werkzeuge auf der neuen Basis (frueher skills2) -------------------------
from .altlast import Altlast
from .anlassfall import Anlassfall
from .anlassfall_check import AnlassfallCheck
from .anzeigeformat import Anzeigeformat
from .dateigroesse import Dateigroesse
from .doppelrumpf import Doppelrumpf
from .esmodulimporte import EsModulImporte
from .frontendadressen import Frontendadressen
from .getattrnamen import GetattrNamen
from .jsbefunde import JsBefunde
from .jsfaenger import JsFaenger
from .jsfunktionen import JsFunktionen
from .jsregistrierung import JsRegistrierung
from .jsschnitt import JsSchnitt
from .jsstilfassungen import JsStilfassungen
from .jssyntax import JsSyntax
from .jsvererbung import JsVererbung
from .jswaisen import JsWaisen
from .kapselung import Kapselung
from .klassenplan import Klassenplan
from .leserzahl import LeserzahlWerkzeug
from .modulzustand import ModulZustand
from .namensvarianten import Namensvarianten
from .rueckgabedict import RueckgabeDict
from .rueckgabetupel import RueckgabeTupel
from .schleifenarbeit import Schleifenarbeit
from .seitenzeiten import Seitenzeiten
from .vorlagenblock import Vorlagenblock
from .wachstum import Wachstum

# --- Werkzeuge auf der alten Basis (frueher skills, jetzt ueber AltWerkzeug) --
from .abhaengigkeiten import Abhaengigkeiten
from .doppelcode import Doppelcode
from .endpunktprobe import Endpunktprobe
from .endpunktprofil import Endpunktprofil
from .endpunktzeiten import Endpunktzeiten
from .freiefunktionen import FreieFunktionen
from .grossdateien import Grossdateien
from .klassenjedatei import KlassenJeDatei
from .namensdubletten import Namensdubletten
from .toteimporte import ToteImporte
from .vorlagenkontext import Vorlagenkontext
from .vorlagenvariablen import Vorlagenvariablen

# --- Werkzeuge zu den Kriterien 16 und 17 ------------------------------------
from .protokoll import Protokoll
from .testaufbau import Testaufbau
from .testdeckung import Testdeckung

# --- Fixer -------------------------------------------------------------------
from .fix_dictklasse import FixDictKlasse
from .fix_importe import ImportFixer
from .fix_jserbe import FixJsErbe
from .fix_jsschnitt import FixJsSchnitt
from .fix_vermerk import FixVermerk

#: Kriterien 16 und 17 gehen ueber die vierzehn aus dem shortlongx-Durchgang
#: hinaus. Sie stehen hier und nicht in ``kriterien.py``, weil jene Datei den
#: Stand JENES Durchgangs festhaelt - eine Quelle, ein Zeitpunkt.
KRITERIEN_ZUSATZ = {
    # 0 ist kein Auftragspunkt, sondern die ehrliche Antwort für Werkzeuge, die
    # über die anderen Werkzeuge laufen. Ohne diesen Eintrag brach die Prüfung
    # „jedes Werkzeug nennt ein bekanntes Kriterium" an ``AnlassfallCheck`` ab.
    0: "Kein Auftrags-Kriterium — Werkzeug über die Werkzeuge",
    16: "Logging sauber: kein console.log, Server-Logging über den rotierenden "
        "djangoBase-Logger, klare Ausnahmen im UI und im Exception-Log, wichtige "
        "Aktionen mit Zeitstempel",
    17: "Testcases sauber erzeugen für alle wichtigen Funktionen und Menüs, "
        "startbar unter Hilfe → Tests (djangoBase); Untermenüs für Unit, "
        "Component, UI und Longrunner — bei großen Projekten mehrere Unterseiten",
}
KRITERIEN = dict(_KRITERIEN_BASIS)
KRITERIEN.update(KRITERIEN_ZUSATZ)

#: Reihenfolge = Anzeigereihenfolge. Vorne, was die teuerste Fehlerklasse
#: trifft; hinten, was Aufraeumarbeit anzeigt.
NEUE = [
    # Ganz vorne, weil nie rot: Ein ``getattr`` mit Vorgabe auf einen falschen
    # Namen faellt nirgends auf. In shortlongx lief der Live-Autotrader deshalb
    # anders als der Backtest daneben.
    GetattrNamen,
    LeserzahlWerkzeug,
    ModulZustand,
    EsModulImporte,
    # --- Frontend: erst was die Seite tot macht, dann was still ausfaellt.
    JsSyntax,
    JsWaisen,
    JsVererbung,
    JsRegistrierung,
    JsFaenger,
    JsFunktionen,
    JsBefunde,
    JsStilfassungen,
    Frontendadressen,
    Seitenzeiten,
    Vorlagenblock,
    Doppelrumpf,
    RueckgabeDict,
    RueckgabeTupel,
    Kapselung,
    Namensvarianten,
    Schleifenarbeit,
    Dateigroesse,
    Altlast,
    # „Lohnt der Umbau ueberhaupt" statt „was ist falsch":
    Anzeigeformat,   # 134 von 204 Befunden waren gar keine
    Klassenplan,     # Feld oder blosses Zwischenergebnis?
    JsSchnitt,       # wo teilen, ohne Zirkel zu erzeugen
    Wachstum,        # misst nach, statt „quadratisch" zu behaupten
    # --- Kriterien 16/17
    Protokoll,
    Testaufbau,
    Testdeckung,
    # Zuletzt, weil es ueber die anderen laeuft: Sieht jedes Werkzeug noch den
    # Fall, fuer den es gebaut wurde? Zwei waren blind, ohne dass es auffiel.
    AnlassfallCheck,
]

#: Werkzeuge auf der alten Basis - Anzeige ueber ``AltWerkzeug``.
#: ``Grossdateien`` faellt weg: ``Dateigroesse`` deckt es reicher ab (auch
#: Klassen > 300, Funktionen > 60, JS-Module > 200). Die Datei bleibt liegen,
#: damit der Vergleich nachvollziehbar ist.
ALTE = [
    FreieFunktionen,
    KlassenJeDatei,
    Abhaengigkeiten,
    Vorlagenkontext,
    ToteImporte,
    Doppelcode,
    Namensdubletten,
    Endpunktzeiten,
    Endpunktprobe,
    Endpunktprofil,
    Vorlagenvariablen,
]

#: Alte Kennung -> Auftrags-Kriterium. 0 = keinem zugeordnet.
ALT_KRITERIUM = {
    "freie-funktionen": 1,      # Funktionen kapseln (neben Kapselung)
    "klassen-je-datei": 2,      # eine Klasse je Datei
    "abhaengigkeiten": 9,       # klare Strukturen/Abhaengigkeiten
    "doppelcode": 6,            # keine Duplikate (Textbloecke, auch HTML)
    "tote-importe": 5,          # ungenutzten Code entfernen
    "namens-dubletten": 7,      # keine abweichenden Namen
}

#: Nicht anzeigen - von einem neueren Werkzeug abgedeckt.
UEBERSPRINGEN = {"grossdateien"}

#: Die Werkzeuge zu den Kriterien 16 und 17 - die Seite bietet dafuer einen
#: eigenen Knopf an („Logging und Tests"), deshalb stehen sie zusaetzlich als
#: eigene Gruppe hier.
EIGENE = [Protokoll, Testaufbau, Testdeckung]

#: Die Klassen auf der NEUEN Basis. Bewusst NICHT ``NEUE + ALTE``: An diesem
#: Namen haengen Zusicherungen, die nur ``Werkzeug2`` erfuellt (``kriterium``,
#: Spalten/Zeilen, Anlassfall). Ein alter ``Werkzeug``-Nachfahre hier drin liess
#: prompt vier Pruefungen mit AttributeError abbrechen (17.08.2026). Die alten
#: stehen in ``ALTE`` und erscheinen ueber ``werkzeuge()`` als ``AltWerkzeug``.
WERKZEUGE = NEUE

#: Werkzeuge, die einen Befund BEHEBEN statt ihn nur zu melden. Getrennt von
#: WERKZEUGE, weil sie schreiben: jeder braucht Vorschau, Sicherung und ein Netz
#: (siehe ``fixer.py``). Ein Fix-Knopf neben einem Pruef-Knopf waere eine Falle.
FIXER = [
    FixVermerk,
    FixJsSchnitt,
    FixJsErbe,
    FixDictKlasse,
    ImportFixer,
]


def werkzeuge():
    """Je eine Instanz aller Werkzeuge - neue Basis zuerst, dann die alten."""
    aus = [klasse() for klasse in NEUE]
    for klasse in ALTE:
        if klasse.slug in UEBERSPRINGEN:
            continue
        aus.append(AltWerkzeug(klasse(), ALT_KRITERIUM.get(klasse.slug, 0)))
    return aus


def werkzeug_finden(slug):
    """Werkzeug nach Kennung, sonst None."""
    for w in werkzeuge():
        if w.slug == slug:
            return w
    return None


def fixer():
    """Je eine Instanz aller Fixer."""
    return [klasse() for klasse in FIXER]


def fixer_finden(slug):
    """Der Fixer mit dieser Kennung, sonst None."""
    for f in fixer():
        if f.slug == slug:
            return f
    return None


def hat_fixer(slug):
    """Gibt es zu diesem Werkzeug einen Fixer?"""
    return any(f.slug == slug for f in fixer())


def kriterien():
    """Alle siebzehn Kriterien."""
    return dict(KRITERIEN)


__all__ = [
    "WERKZEUGE", "NEUE", "ALTE", "FIXER", "werkzeuge", "werkzeug_finden",
    "fixer", "fixer_finden", "hat_fixer",
    "Werkzeug2", "Ergebnis", "Quelldatei", "EigenesWerkzeug",
    "Werkzeug", "ErgebnisAlt", "Befund", "Ausgabe", "AltWerkzeug",
    "Fixer", "Vorschau", "Aenderung", "ImportFixer",
    "Bericht", "Umbaunetz", "Abnahme",
    "KRITERIEN", "KRITERIEN_ZUSATZ", "OHNE_WERKZEUG", "kriterien",
    "ALT_KRITERIUM", "UEBERSPRINGEN", "EIGENE",
    "LEHREN", "BEREICHE", "gruppen", "als_zeilen", "Lehre", "Lehrenstand",
    "Anlassfall", "Protokoll", "Testaufbau", "Testdeckung",
]
