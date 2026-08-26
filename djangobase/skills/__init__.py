# -*- coding: utf-8 -*-
u"""Skills - der Werkzeugkasten. EINE Seite, EIN Paket, alle Werkzeuge.

WIE ES HIERHIN KAM (17.08.2026)
===============================
Es gab drei Werkzeugkaesten nebeneinander, an verschiedenen Tagen in
verschiedenen Sitzungen entstanden:

    skills   (3DTools-Durchgang)    12 Werkzeuge, Basis ``Werkzeug``
    skills2  (shortlongx-Durchgang) 28 Werkzeuge, Basis ``Werkzeug``
    skills1  (Zusammenfuehrung)     beides ueber einen Adapter

Drei Seiten mit ueberlappenden Werkzeugen sind kein Werkzeugkasten, sondern drei
halbe. Deshalb ist dieses Paket jetzt der Master: Alle Module aus ``skills2`` und
``skills3`` (dem frueheren ``skills``) liegen HIER. ``skills2`` und ``skills3``
sind nur noch duenne Weiterleitungen auf dieses Paket, damit vorhandene Links,
Lesezeichen und Importe weiterlaufen - sie verschwinden, sobald niemand mehr
darauf zeigt.

EINE BASIS, ZWEI BAUFORMEN (18.08.2026)
=======================================
``Werkzeug`` (``werkzeug.py``) ist die Basis fuer ALLE: Projektwurzel ueber das
Git-Repo statt nur ``BASE_DIR``, EINE Ausschlussliste, Quelldatei-Cache mit
Syntaxbaum, Bezug auf ein Kriterium, Anlassfall.

Darauf gibt es zwei Bauformen, je nachdem, was ein Werkzeug zu sagen hat:

* ``Werkzeug`` direkt - freie Tabelle: ``laufen()`` liefert ``Ergebnis`` mit
  eigenen Spalten und Zeilen.
* ``BefundWerkzeug`` (``befund.py``) - Befunde: ``pruefen()`` liefert einen
  ``Befundsatz`` aus ``Befund``-Objekten (Ort, Was, Warum, Gewicht), die Basis
  macht daraus dieselbe Tabelle.

Bis zum 18.08.2026 waren das ZWEI Basisklassen in zwei Welten, verbunden durch
einen Adapter (``AltWerkzeug``), mit zwei Dateisuchen und zwei
Ausschlusslisten - die prompt auseinanderliefen. Beides ist zusammengefuehrt;
``werkzeug_alt.py`` und ``adapter.py`` sind entfallen.

Aufruf ueber Hilfe -> Skills (``djangobase/views/skills.py``) oder direkt:

    from djangobase.skills import werkzeug_finden
    erg = werkzeug_finden("modulzustand").laufen()
    print(erg.zusammenfassung)

Neues Werkzeug: von ``Werkzeug`` ableiten (oder von ``BefundWerkzeug``,
wenn es Befunde meldet), EINE Klasse je Datei, unten in ``NEUE`` bzw.
``BEFUNDBASIERT`` eintragen.
"""
# --- Basis und Infrastruktur -------------------------------------------------
from .basis import EigenesWerkzeug
from .bericht import Bericht
from .fixer import Aenderung, Fixer, Vorschau
from .kriterien import KRITERIEN as _KRITERIEN_BASIS
from .kriterien import OHNE_WERKZEUG
from .lehren import BEREICHE, LEHREN, Lehre, Lehrenstand, als_zeilen, gruppen
from .netz import Abnahme, Umbaunetz
from .befund import Befund, Befundsatz, BefundWerkzeug
from .werkzeug import Ergebnis, Quelldatei, Werkzeug
from .befund import BefundWerkzeug

# --- Werkzeuge auf der neuen Basis (frueher skills2) -------------------------
from .altlast import Altlast
from .anlassfall import Anlassfall
from .anlassfall_check import AnlassfallCheck
from .anzeigeformat import Anzeigeformat
from .codequalitaet import CodeQualitaet
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
from .jsstumm import JsStumm
from .jssyntax import JsSyntax
from .jsvererbung import JsVererbung
from .jswaisen import JsWaisen
from .kapselung import Kapselung
from .klassenreif import Klassenreif
from .klassenplan import Klassenplan
from .lehrentreue import Lehrentreue
from .leserzahl import LeserzahlWerkzeug
from .modulzustand import ModulZustand
from .namensvarianten import Namensvarianten
from .rueckgabedict import RueckgabeDict
from .rueckgabetupel import RueckgabeTupel
from .schleifenarbeit import Schleifenarbeit
from .szenarien import Szenarien
from .schreibrouten import Schreibrouten
from .seitenzeiten import Seitenzeiten
from .uebersprungen import Uebersprungen
from .vorlagenblock import Vorlagenblock
from .wachstum import Wachstum

# --- Werkzeuge auf der alten Basis (frueher skills, jetzt ueber AltWerkzeug) --
from .abhaengigkeiten import Abhaengigkeiten
from .doppelcode import Doppelcode
from .endpunktprobe import Endpunktprobe
from .endpunktprofil import Endpunktprofil
from .endpunktzeiten import Endpunktzeiten
from .freiefunktionen import FreieFunktionen
from .globalerzustand import GlobalerZustand
from .objektwurzeln import Objektwurzeln
from .seitenwurzeln import Seitenwurzeln
from .sammelzustand import Sammelzustand
from .klassenkandidat import Klassenkandidat
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
from .fix_ausnahme import FixAusnahme
from .fix_dictklasse import FixDictKlasse
from .fix_fzeichenkette import FixFZeichenkette
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
    18: "Freie Funktionen und globale Variablen in Klassen unterbringen: "
        "Verhalten in Klassen bzw. Utility-Klassen mit statischen Methoden, "
        "veränderlichen Zustand als Attribut, globale Konstanten in einer "
        "Kontext-Klasse",
    # KRITERIUM 19 — BDD, aber ohne Gherkin (26.08.2026)
    # =================================================
    #     „Macht es sinn, dass ich die anwende?"
    #
    # Gemessen statt geraten: 88 % der 1538 Pruefungen tragen schon einen
    # Satz als Namen (`test_ausgeblendete_person_bleibt_ausgeblendet`), und
    # 50 von 60 Werkzeugen haben einen `Anlassfall` — woertlich
    # Given/When/Then. Was fehlte, war nicht die Schreibweise, sondern die
    # LUECKEN: 179 Seiten und Endpunkte ohne jede Abnahme, ein Werkzeug
    # ohne Beispiel.
    #
    # Deshalb ein Kriterium statt eines Rahmenwerks: Es prueft die drei
    # Zusicherungen, die BDD wirklich gibt — jede Regel hat ein Beispiel,
    # jede Seite eine Abnahme, jeder Pruefungsname sagt das Verhalten.
    19: "BDD ohne Gherkin: jede Regel hat ein Beispiel (Anlassfall), jede "
        "Seite und jeder Endpunkt eine Abnahme, jeder Pruefungsname nennt "
        "das erwartete Verhalten",
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
    # Direkt hinter JsFaenger: dieselbe Frage von der anderen Seite. Dort geht
    # eine Ausnahme ungefangen verloren, hier wird sie GEFANGEN und dann
    # weggeworfen — der Ausgang ist derselbe, nur sieht dieser sauber aus.
    JsStumm,
    JsFunktionen,
    JsBefunde,
    JsStilfassungen,
    Frontendadressen,
    # Datenverlust auf ein GET hin - vorn, weil es der teuerste Ausgang ist.
    Schreibrouten,
    # Direkt dahinter (26.08.2026): Eine Pruefung, die sich selbst
    # ueberspringt, meldet gruen. Das ist billiger zu uebersehen als
    # jeder andere Befund — es sieht ja aus wie bestanden.
    Uebersprungen,
    # Die fuenf Lehren, die sich am Quelltext ablesen lassen
    # (26.08.2026). Zehn der 22 hingen vorher an gar keiner
    # Pruefung — es sind die Fehler, die man beim zweiten Mal
    # genauso macht wie beim ersten.
    Lehrentreue,
    # Kriterium 19 (26.08.2026): BDD ohne Gherkin. Eine Pruefung
    # ohne Zusicherung meldet gruen, egal was passiert — teurer
    # als gar keine, weil sie Sicherheit vortaeuscht.
    Szenarien,
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

#: Die Werkzeuge der zweiten Bauform: Sie liefern BEFUNDE (Ort, Was, Warum,
#: Gewicht) statt einer freien Tabelle und erben ueber ``BefundWerkzeug``
#: dieselbe Basis wie alle anderen — dieselbe Projektwurzel, dieselbe
#: Ausschlussliste. Frueher war das eine eigene Welt mit eigener Basisklasse.
BEFUNDBASIERT = [
    # Direkt vor FreieFunktionen (26.08.2026): dieselbe Frage, aber
    # die richtige. `FreieFunktionen` zaehlt Funktionen; dieses hier
    # fragt nach ZUSTAND. Gemessen an CamTrack: 806 Funktionen auf
    # Modulebene, aber nur fuenf Stellen mit veraenderlichem
    # Modulzustand — und der eine echte Fehler, den ein Umbau an dem
    # Tag fand, steckte in einem geteilten Lock.
    Klassenreif,
    # Ganz vorn (24.08.2026): das EINZIGE Werkzeug hier, das nicht
    # selbst misst. Komplexitaet, Wartbarkeit, tote Namen und PEP 8
    # sind seit Jahren geloest — radon, pyflakes und pycodestyle
    # koennen das besser, als ich es nachbauen wuerde. Die anderen
    # Werkzeuge stellen Fragen, die kein Standardwerkzeug kennt;
    # dieses bringt die Antworten der Standardwerkzeuge in dieselbe
    # Form.
    CodeQualitaet,
    FreieFunktionen,
    # Direkt hinter FreieFunktionen (19.08.2026, Kriterium 18): dieselbe Frage
    # von der Zustandsseite. Freie Funktionen zeigen, wo Verhalten heimatlos
    # ist; ``GlobalerZustand`` zeigt, wo DATEN es sind - und ``Klassenkandidat``
    # verbindet beides zu einem konkreten Umbauvorschlag.
    GlobalerZustand,
    # Direkt dahinter (23.08.2026): dieselbe Frage eine Ebene weiter. Bei
    # ``GlobalerZustand`` steht der Zustand ausserhalb jeder Klasse; hier steht
    # er IN einer — nur in der falschen. Eine Wache fuer elf Kameras sieht in
    # jeder Pruefung sauber aus und laesst trotzdem vier Kameras zehn Stunden
    # blind laufen.
    Sammelzustand,
    # Und die Frage nach der FORM DES GANZEN (23.08.2026): Wie viele Klassen
    # entstehen ueberhaupt ausserhalb jeder Klasse? „Ein gutes Objektmodell
    # faengt mit einer Klasse an und verzweigt immer weiter ueber Instanzen"
    # — gemessen an CamTrack: 29 Wurzeln statt einer.
    Objektwurzeln,
    # Dieselbe Frage ans Frontend: Wie viele Objekte erzeugt eine
    # Vorlage selbst? `live_view.html` sind es neun, dazu zwei
    # `setTimeout`, mit denen die Reihenfolge geraten wird.
    Seitenwurzeln,
    Klassenkandidat,
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

#: Nicht anzeigen - von einem neueren Werkzeug abgedeckt (``dateigroesse``
#: kann alles, was ``grossdateien`` kann, und mehr). Die Datei bleibt liegen,
#: damit der Vergleich nachvollziehbar ist.
UEBERSPRINGEN = {"grossdateien"}

#: ENTFERNT am 26.08.2026 — die Liste war der Fehler.
#:
#:     „warum ist Logging & Tests auf /hilfe/skills/ noch anders, mit
#:      anderen Nummern usw?"
#:
#: Hier standen drei von Hand eingetragene Werkzeuge. Nachgemessen trugen
#: FUENF das Kriterium 16 oder 17 — `jsstumm` und `schreibrouten` liefen
#: nie mit, wenn jemand „Logging & Tests pruefen" drueckte.
#:
#: Der Block zu Kriterium 18 fragte laengst die Registrierung; sein
#: Kommentar sagte auch warum („Hier wird gefragt statt aufgezaehlt").
#:
#: Am selben Tag ging es einen Schritt weiter: Die zwei Kästen unter
#: der Tabelle sind ganz weg. Ihre Werkzeuge standen dort ein ZWEITES
#: Mal — in der Tabelle koennen sie mehr. Der Sammellauf-Knopf sitzt
#: jetzt in der Abschnitts-Zeile und gilt fuer jeden Bereich
#: (``SkillsView._gruppenkopf``).

#: ALLE Werkzeuge, EINE Liste (Ansage 18.08.2026: „ich brauche keine AlteBasis,
#: merge alles"). Bis dahin standen sie in zwei Listen mit zwei Basisklassen,
#: und ein Adapter rechnete die eine in die andere um; ihr Kriterium stand in
#: einer Tabelle NEBEN der Registrierung. Jetzt tragen alle dieselbe Basis
#: (``Werkzeug``), die befundbasierten ueber ``BefundWerkzeug`` — und jedes
#: Werkzeug traegt sein Kriterium selbst.
WERKZEUGE = NEUE + [k for k in BEFUNDBASIERT if k.slug not in UEBERSPRINGEN]

#: Werkzeuge, die einen Befund BEHEBEN statt ihn nur zu melden. Getrennt von
#: WERKZEUGE, weil sie schreiben: jeder braucht Vorschau, Sicherung und ein Netz
#: (siehe ``fixer.py``). Ein Fix-Knopf neben einem Pruef-Knopf waere eine Falle.
FIXER = [
    # Vorne: die teuerste Fehlerklasse. Eine verschluckte Ausnahme kostet
    # spaeter Stunden, weil die Ursache nirgends steht.
    FixAusnahme,
    FixVermerk,
    FixJsSchnitt,
    FixJsErbe,
    FixDictKlasse,
    ImportFixer,
    # Direkt hinter ImportFixer (25.08.2026): dieselbe Bauart, andere
    # Fehlerklasse. `ImportFixer` nimmt tote Einfuhren, dieser die
    # leeren f-Zeichenketten — beides meldet `pyflakes`, und beides
    # gehoert HIERHER und nicht in ein Skript im Wirtsprojekt.
    FixFZeichenkette,
]


def werkzeuge():
    """Je eine Instanz aller Werkzeuge - eine Liste, eine Basis."""
    return [klasse() for klasse in WERKZEUGE]


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
    "Werkzeug", "Ergebnis", "Quelldatei", "EigenesWerkzeug",
    "Werkzeug", "ErgebnisAlt", "Befund", "Ausgabe", "AltWerkzeug",
    "Fixer", "Vorschau", "Aenderung", "ImportFixer",
    "Bericht", "Umbaunetz", "Abnahme",
    "KRITERIEN", "KRITERIEN_ZUSATZ", "OHNE_WERKZEUG", "kriterien",
    "ALT_KRITERIUM", "UEBERSPRINGEN",
    "LEHREN", "BEREICHE", "gruppen", "als_zeilen", "Lehre", "Lehrenstand",
    "Anlassfall", "Protokoll", "Testaufbau", "Testdeckung",
]
