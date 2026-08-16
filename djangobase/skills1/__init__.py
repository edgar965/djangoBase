# -*- coding: utf-8 -*-
u"""Skills1 - beide Werkzeugkaesten unter einem Dach.

Fasst ``skills`` und ``skills2`` zu EINER Werkzeugliste zusammen, ohne die beiden
bestehenden Seiten anzutasten (die wandern gerade an einen neuen Menuepunkt):

* Fundament ist die skills2-Welt (Tabelle je Werkzeug: Spalten + Zeilen-Dicts).
  Grund: Sie traegt die reifere Engine (Quelldatei-Cache, Repo-Wurzel statt nur
  ``BASE_DIR``, abgestufte Bewertung, Kriteriums-Bezug) und die skills-Befunde
  bilden verlustfrei auf eine Tabelle ab - umgekehrt gingen die Bewertungsstufen
  verloren.
* Die skills-Werkzeuge kommen ueber ``AltWerkzeug`` (Adapter) dazu - so sind
  Import-Graph, Doppelcode ueber HTML, tote Importe, Synonyme sowie die Vorlagen-
  und Endpunkt-Analysen sofort mit dabei.
* Vom skills-Bedienmodell uebernommen: server-seitiger Stapellauf mit
  Klartext-Bericht (``Bericht``) und einstellbare Schwellen (``eingabe``).

``Grossdateien`` faellt weg - ``Dateigroesse`` (skills2) deckt es reicher ab
(auch Klassen > 300, Funktionen > 60, JS-Module > 200).

Aufruf ueber Hilfe -> Skills1 (``djangobase/views/skills1.py``) oder direkt:

    from djangobase.skills1 import werkzeug_finden
    erg = werkzeug_finden("abhaengigkeiten").laufen()
"""
from ..skills import werkzeuge as _alt_werkzeuge
from ..skills2 import werkzeuge as _neu_werkzeuge
from .adapter import AltWerkzeug
from .bericht import Bericht
from ..skills2 import fixer as _skills2_fixer
from .fixer import ImportFixer
from .netz import Abnahme, Umbaunetz
from .protokoll import Protokoll
from .testaufbau import Testaufbau
from .testdeckung import Testdeckung

#: Kriterien, die ueber die vierzehn aus skills2 hinausgehen. Sie stehen HIER
#: und nicht in skills2/kriterien.py, weil dieses Paket die Zusammenfuehrung ist
#: - skills2 waechst parallel weiter.
KRITERIEN_ZUSATZ = {
    16: "Logging sauber: kein console.log, Server-Logging über den rotierenden "
        "djangoBase-Logger, klare Ausnahmen im UI und im Exception-Log, wichtige "
        "Aktionen mit Zeitstempel",
    17: "Testcases sauber erzeugen für alle wichtigen Funktionen und Menüs, "
        "startbar unter Hilfe → Tests (djangoBase); Untermenüs für Unit, "
        "Component, UI und Longrunner — bei großen Projekten mehrere Unterseiten",
}

#: Werkzeuge, die es nur hier gibt (zu den Kriterien oben).
EIGENE = [Protokoll, Testaufbau, Testdeckung]

#: Fixer = die aus skills2 (FixVermerk, FixJsSchnitt) PLUS der hiesige
#: ImportFixer. Alle stehen auf derselben Basis (``skills2.fixer.Fixer``) und
#: bringen damit Sicherung und Netz mit - anders ist Schreiben nicht zu
#: verantworten. Dynamisch geholt, weil skills2 weiter waechst.


def fixer():
    """Je eine Instanz aller Fixer - skills2 zuerst, dann die Ergaenzungen."""
    aus = list(_skills2_fixer())
    vorhanden = {f.slug for f in aus}
    for klasse in (ImportFixer,):
        if klasse.slug not in vorhanden:
            aus.append(klasse())
    return aus


def fixer_finden(slug):
    """Der Fixer mit dieser Kennung, sonst None."""
    for f in fixer():
        if f.slug == slug:
            return f
    return None


def hat_fixer(slug):
    return any(f.slug == slug for f in fixer())

#: skills-Werkzeug -> Auftrags-Kriterium (kriterien.py). 0 = keinem zugeordnet.
ALT_KRITERIUM = {
    "freie-funktionen": 1,      # Funktionen kapseln (neben Kapselung)
    "klassen-je-datei": 2,      # eine Klasse je Datei
    "abhaengigkeiten": 9,       # klare Strukturen/Abhaengigkeiten
    "doppelcode": 6,            # keine Duplikate (Textbloecke, auch HTML)
    "tote-importe": 5,          # ungenutzten Code entfernen
    "namens-dubletten": 7,      # keine abweichenden Namen
}

#: Von skills2 abgedeckt - nicht doppelt anzeigen.
#: NUR das eindeutige Duplikat: Dateigroesse (skills2) deckt Grossdateien reicher
#: ab. Weitere Kandidaten NICHT hier eintragen, solange skills2 waechst - die
#: Parallel-Sitzung hat es am 16.08.2026 von 10 auf 20 Werkzeuge ausgebaut und
#: bildet dabei skills-Werkzeuge nach. Bekannte Ueberschneidungen, die sich
#: ausblenden lassen, SOBALD skills2 steht:
#:   freie-funktionen  -> klassenplan + kapselung (Kr. 1)
#:   doppelcode (JS)   -> jssyntax/jswaisen/jsregistrierung/jsfaenger/jsschnitt
#:   klassen-je-datei  -> teilweise dateigroesse (aber "mehr als 1 Klasse je
#:                        Datei" mit Datentraeger-Filter bleibt eigenstaendig)
UEBERSPRINGEN = {"grossdateien"}


def werkzeuge():
    """skills2 (reifere Engine), dann die skills-Ergaenzungen, dann die eigenen."""
    aus = list(_neu_werkzeuge())
    for w in _alt_werkzeuge():
        if w.slug in UEBERSPRINGEN:
            continue
        aus.append(AltWerkzeug(w, ALT_KRITERIUM.get(w.slug, 0)))
    aus += [k() for k in EIGENE]
    return aus


def werkzeug_finden(slug):
    """Werkzeug nach Kennung, sonst None."""
    for w in werkzeuge():
        if w.slug == slug:
            return w
    return None


def kriterien():
    """Alle Kriterien: die vierzehn aus skills2 plus die hiesigen."""
    from ..skills2 import KRITERIEN
    aus = dict(KRITERIEN)
    aus.update(KRITERIEN_ZUSATZ)
    return aus


__all__ = ["werkzeuge", "werkzeug_finden", "Bericht", "AltWerkzeug",
           "ALT_KRITERIUM", "UEBERSPRINGEN", "ImportFixer", "fixer",
           "fixer_finden", "hat_fixer", "Umbaunetz", "Abnahme",
           "EIGENE", "KRITERIEN_ZUSATZ", "kriterien",
           "Protokoll", "Testaufbau", "Testdeckung"]
