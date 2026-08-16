"""Skills — Analysewerkzeuge und Lehren aus Code-Reviews.

Die Werkzeuge hier sind aus einem grossen Review-/Umbaudurchgang entstanden
(3DTools, August 2026) und bewusst PROJEKTUNABHAENGIG gehalten: Sie fragen
Django nach seinen eigenen Vorlagen, Routen und Modulen, statt Pfade zu raten.
Damit laufen sie in jedem Projekt, das djangoBase einbindet.

Aufruf ueber Hilfe -> Skills (`djangobase/views/skills.py`) oder direkt:

    from djangobase.skills import werkzeug_finden
    ergebnis = werkzeug_finden('vorlagen-kontext').laufen()
    print(ergebnis.text())

Neue Werkzeuge: Klasse von `Werkzeug` ableiten, Datei hier ablegen und unten in
`WERKZEUGE` eintragen — eine Klasse je Datei.
"""

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
from .werkzeug import Ergebnis, Werkzeug

#: Reihenfolge = Anzeigereihenfolge auf der Seite, gruppiert nach Anlass:
#: erst Struktur (Objektorientierung, Schnitt), dann Reste (tot, doppelt),
#: dann Laufzeit. Innerhalb der Gruppen vorne, was am haeufigsten etwas findet.
WERKZEUGE = [
    # --- Struktur: was gehoert in Klassen, was gehoert getrennt
    Grossdateien,
    FreieFunktionen,
    KlassenJeDatei,
    Abhaengigkeiten,
    # --- Reste: tot, doppelt, uneinheitlich benannt
    Vorlagenkontext,
    ToteImporte,
    Doppelcode,
    Namensdubletten,
    # --- Laufzeit
    Endpunktzeiten,
    Endpunktprobe,
    Endpunktprofil,
    Vorlagenvariablen,
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


__all__ = ['WERKZEUGE', 'Werkzeug', 'Ergebnis', 'werkzeuge', 'werkzeug_finden']
