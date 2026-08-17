# -*- coding: utf-8 -*-
u"""Skills2 - Pruefwerkzeuge und Lehren aus dem shortlongx-Review (August 2026).

Vierzehn Werkzeuge, die in JEDEM djangoBase-Projekt laufen: Sie suchen unter
``settings.BASE_DIR`` und lesen den Syntaxbaum, statt Pfade zu raten. Dazu die
Lehren des Durchgangs als Arbeitsliste (``lehren.py``) - jede mit dem Fall, der
sie ausgeloest hat.

Aufruf ueber Hilfe -> Skills2 oder direkt:

    from djangobase.skills2 import werkzeug_finden
    erg = werkzeug_finden("modulzustand").laufen()
    print(erg.zusammenfassung)

Neues Werkzeug: Klasse von ``Werkzeug2`` ableiten, EINE Klasse je Datei, unten
eintragen.

Verhaeltnis zu ``djangobase.skills``: Beide sind am selben Tag in zwei
Sitzungen entstanden (dieses hier aus dem shortlongx-Durchgang, jenes aus
3DTools). Sie bleiben getrennt, bis jemand sie bewusst zusammenlegt - zwei
halbfertige Fassungen derselben Basisklasse gegeneinander zu mergen waere
teurer gewesen als zwei saubere Pakete.
"""
from .altlast import Altlast
from .anlassfall import Anlassfall
from .anlassfall_check import AnlassfallCheck
from .anzeigeformat import Anzeigeformat
from .dateigroesse import Dateigroesse
from .doppelrumpf import Doppelrumpf
from .esmodulimporte import EsModulImporte
from .fix_dictklasse import FixDictKlasse
from .fix_jserbe import FixJsErbe
from .fix_jsschnitt import FixJsSchnitt
from .fix_vermerk import FixVermerk
from .fixer import Aenderung, Fixer, Vorschau
from .getattrnamen import GetattrNamen
from .jsbefunde import JsBefunde
from .jsfaenger import JsFaenger
from .jsfunktionen import JsFunktionen
from .jsregistrierung import JsRegistrierung
from .jsstilfassungen import JsStilfassungen
from .jssyntax import JsSyntax
from .jsvererbung import JsVererbung
from .jswaisen import JsWaisen
from .jsschnitt import JsSchnitt
from .kapselung import Kapselung
from .klassenplan import Klassenplan
from .leserzahl import LeserzahlWerkzeug
from .kriterien import KRITERIEN, OHNE_WERKZEUG
from .lehren import LEHREN, gruppen
from .modulzustand import ModulZustand
from .namensvarianten import Namensvarianten
from .rueckgabedict import RueckgabeDict
from .frontendadressen import Frontendadressen
from .seitenzeiten import Seitenzeiten
from .vorlagenblock import Vorlagenblock
from .rueckgabetupel import RueckgabeTupel
from .schleifenarbeit import Schleifenarbeit
from .wachstum import Wachstum
from .werkzeug import Ergebnis, Quelldatei, Werkzeug2

#: Reihenfolge = Anzeigereihenfolge. Vorne, was am haeufigsten echte Fehler
#: findet; hinten, was eher Aufraeumarbeit anzeigt.
WERKZEUGE = [
    # Ganz vorne, weil es die teuerste Fehlerklasse trifft: Ein ``getattr`` mit
    # Vorgabe auf einen falschen Namen wird NIE rot. In shortlongx lief der
    # Live-Autotrader deshalb anders als der Backtest daneben.
    GetattrNamen,
    LeserzahlWerkzeug,
    ModulZustand,
    EsModulImporte,
    # --- Frontend-Pruefungen aus dem 3DTools-Durchgang (16.08.2026).
    # Reihenfolge nach Wirkung: erst was die Seite tot macht (Syntax, Waisen,
    # fehlende Anmeldung), dann was still ausfaellt (Faenger), dann Mengen.
    JsSyntax,
    JsWaisen,
    # Direkt hinter den Waisen: Beide melden Fehler, die beim Laden NICHT
    # auffallen. Ein Klassenname, den die Basisklasse nicht kennt, wirft erst
    # beim ersten Aufruf - und dann mitten im Betrieb.
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
    # Am 16.08.2026 dazugekommen - die vier, die im shortlongx-Durchgang die
    # meiste Arbeit gespart haben. Sie beantworten nicht „was ist falsch",
    # sondern „lohnt der Umbau ueberhaupt":
    Anzeigeformat,   # 134 von 204 Befunden waren gar keine
    Klassenplan,     # Feld oder blosses Zwischenergebnis?
    JsSchnitt,       # wo laesst sich teilen, ohne Zirkel zu erzeugen
    Wachstum,        # misst nach, statt „quadratisch" zu behaupten
    # Zuletzt, weil es ueber die anderen laeuft: Sieht jedes Werkzeug noch den
    # Fall, fuer den es gebaut wurde? Zwei waren blind, ohne dass es auffiel.
    AnlassfallCheck,
]


def werkzeuge():
    """Je eine Instanz aller Werkzeuge."""
    return [klasse() for klasse in WERKZEUGE]


def werkzeug_finden(slug):
    """Werkzeug nach Kennung, sonst None."""
    for klasse in WERKZEUGE:
        if klasse.slug == slug:
            return klasse()
    return None


__all__ = ["WERKZEUGE", "Werkzeug2", "Ergebnis", "Quelldatei", "werkzeuge",
           "werkzeug_finden", "LEHREN", "gruppen", "KRITERIEN", "OHNE_WERKZEUG"]


#: FIXER - Werkzeuge, die einen Befund BEHEBEN statt ihn nur zu melden.
#: Getrennt von WERKZEUGE, weil sie schreiben: jeder braucht Vorschau,
#: Sicherung und ein Netz (siehe fixer.py). Ein Fix-Knopf neben einem
#: Prüf-Knopf waere eine Falle - man klickt einen davon aus Versehen.
FIXER = [
    FixVermerk,
    FixJsSchnitt,
    FixJsErbe,
    FixDictKlasse,
]


def fixer():
    """Je eine Instanz aller Fixer."""
    return [klasse() for klasse in FIXER]


def fixer_finden(slug):
    """Den Fixer mit dieser Kennung - oder ``None``."""
    for f in fixer():
        if f.slug == slug:
            return f
    return None
