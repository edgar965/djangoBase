# -*- coding: utf-8 -*-
u"""Skills2 - Pruefwerkzeuge und Lehren aus dem shortlongx-Review (August 2026).

Fuenf Werkzeuge, die in JEDEM djangoBase-Projekt laufen: Sie suchen unter
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
from .dateigroesse import Dateigroesse
from .doppelrumpf import Doppelrumpf
from .esmodulimporte import EsModulImporte
from .kapselung import Kapselung
from .kriterien import KRITERIEN, OHNE_WERKZEUG
from .lehren import LEHREN, gruppen
from .modulzustand import ModulZustand
from .namensvarianten import Namensvarianten
from .rueckgabedict import RueckgabeDict
from .rueckgabetupel import RueckgabeTupel
from .schleifenarbeit import Schleifenarbeit
from .werkzeug import Ergebnis, Quelldatei, Werkzeug2

#: Reihenfolge = Anzeigereihenfolge. Vorne, was am haeufigsten echte Fehler
#: findet; hinten, was eher Aufraeumarbeit anzeigt.
WERKZEUGE = [
    ModulZustand,
    EsModulImporte,
    Doppelrumpf,
    RueckgabeDict,
    RueckgabeTupel,
    Kapselung,
    Namensvarianten,
    Schleifenarbeit,
    Dateigroesse,
    Altlast,
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
