# -*- coding: utf-8 -*-
u"""AltWerkzeug - ein skills-Werkzeug in der skills2-Welt.

WARUM EIN ADAPTER STATT NEU SCHREIBEN
=====================================
Die skills-Werkzeuge liefern Befunde (``ort``, ``was``, ``warum``, ``gewicht``);
die skills2-Werkzeuge liefern eine Tabelle (Spalten + Zeilen-Dicts). Vier Felder
bilden verlustfrei auf vier Spalten ab - deshalb laesst sich JEDES skills-Werkzeug
ueber diesen Adapter in derselben Welt fahren, ohne es Zeile fuer Zeile zu
portieren. Die inhaltliche Hochhebung auf den Quelldatei-Cache der skills2-Engine
(einmal lesen/parsen statt je Werkzeug neu) bleibt ein spaeterer, werkzeugweiser
Schritt - der Adapter macht sie erst einmal alle sichtbar und lauffaehig.

Die skills-Basisklasse faengt Ausnahmen bereits in ``laufen`` ab und liefert ein
``Ergebnis`` mit ``fehler`` - das wird hier in einen Tabellen-Hinweis uebersetzt,
nicht noch einmal geworfen.
"""
from .werkzeug import Ergebnis, Werkzeug2

__all__ = ["AltWerkzeug"]


class AltWerkzeug(Werkzeug2):
    """Umschliesst ein ``skills``-Werkzeug und spricht die ``skills2``-Schnittstelle.

    Erbt von ``Werkzeug2`` fuer die Schnittstelle (``als_dict``): Ein Adapter, der
    die Werkzeug2-Rolle spielt, IST ein Werkzeug2. Die Datei-Methoden
    (``wurzel``/``dateien``) bleiben ungenutzt - ``laufen`` delegiert an das
    umschlossene Werkzeug, das seine eigene Dateisuche mitbringt."""

    #: Die vier Befund-Felder als Tabellenspalten.
    SPALTEN = ["schwere", "ort", "befund", "hinweis"]

    def __init__(self, alt, kriterium=0):
        self._alt = alt
        # Attributnamen auf die skills2-Welt vereinheitlichen, damit die View
        # alle Werkzeuge gleich behandelt.
        self.slug = alt.slug
        self.titel = alt.name
        self.zweck = alt.zweck
        self.dauer = alt.dauer
        self.befund = getattr(alt, "beleg", "")
        self.wann = getattr(alt, "wann", "")
        self.abhilfe = self.wann          # "wann einsetzen" tritt an die Stelle von abhilfe
        self.kriterium = kriterium
        self.eingabe = getattr(alt, "eingabe", None)
        self.ruft_endpunkte_auf = getattr(alt, "ruft_endpunkte_auf", False)

    def laufen(self, **argumente):
        erg = self._alt.laufen(**argumente)       # skills.Ergebnis (faengt Fehler)
        zusammenfassung = " · ".join(erg.kopf)
        if erg.fehler:
            return Ergebnis(self.SPALTEN, [], zusammenfassung, "FEHLER: %s" % erg.fehler)
        zeilen = [{"schwere": b.gewicht, "ort": str(b.ort),
                   "befund": b.was, "hinweis": b.warum} for b in erg.befunde]
        return Ergebnis(self.SPALTEN, zeilen, zusammenfassung, "")
