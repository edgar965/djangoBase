# -*- coding: utf-8 -*-
u"""Skills3 - WEITERLEITUNG auf ``djangobase.skills``. Wird abgeschafft.

Dieses Paket hiess bis zum 17.08.2026 ``skills`` und war der erste
Werkzeugkasten (3DTools-Durchgang, August 2026). Seine zwoelf Werkzeuge liegen
jetzt in ``djangobase.skills`` - dort laufen sie ueber ``AltWerkzeug`` neben den
neueren, ohne dass eine der elf gewachsenen Pruefungen umgeschrieben werden
musste.

Hier steht nur noch die Weiterleitung, aus demselben Grund wie bei ``skills2``:
Solange noch etwas hier ankommt, ist der Umbau nicht fertig. Sobald nichts mehr
darauf zeigt, koennen beide Pakete weg.

Die alte Basisklasse heisst im Master ``werkzeug_alt.Werkzeug`` - der Name
``Werkzeug`` bleibt hier unveraendert erreichbar.
"""
import sys as _sys

from .. import skills as _master
from ..skills import ALTE, ALT_KRITERIUM                  # noqa: F401
from ..skills import Ausgabe, Befund, Werkzeug            # noqa: F401
from ..skills import ErgebnisAlt as Ergebnis             # noqa: F401
from ..skills import Grossdateien                         # noqa: F401

#: Die Klassen des urspruenglichen Kastens - unveraendert erreichbar.
#: ``Grossdateien`` gehoerte dazu und wird im Master nicht mehr angezeigt
#: (``Dateigroesse`` deckt es reicher ab) - hier bleibt es, damit diese Seite
#: zeigt, was sie immer gezeigt hat.
WERKZEUGE = [Grossdateien] + list(ALTE)


def werkzeuge():
    """Je eine Instanz - NUR die Werkzeuge dieses Kastens.

    Nicht an den Master weiterreichen: Der liefert auch die Werkzeuge auf der
    neuen Basis, und diese Seite arbeitet mit ``Befund``-Objekten und
    Textausgabe. Der erste Wurf hat einfach durchgereicht - die Seite bekam 42
    statt 12 Werkzeuge und brach beim ersten Aufruf ab (17.08.2026)."""
    return [klasse() for klasse in WERKZEUGE]


def werkzeug_finden(slug):
    """Werkzeug dieses Kastens nach Kennung, sonst None."""
    for klasse in WERKZEUGE:
        if klasse.slug == slug:
            return klasse()
    return None

__all__ = ["WERKZEUGE", "werkzeuge", "werkzeug_finden", "Werkzeug", "Ergebnis",
           "Befund", "Ausgabe", "ALT_KRITERIUM"]


def _module_umhaengen():
    """Alte Modulpfade auf die Module des Masters zeigen lassen.

    ``from djangobase.skills3.toteimporte import ToteImporte`` laeuft damit
    weiter, obwohl die Datei woanders liegt."""
    import importlib
    import pkgutil
    for info in pkgutil.iter_modules(_master.__path__):
        alt = "%s.%s" % (__name__, info.name)
        if alt in _sys.modules:
            continue
        try:
            _sys.modules[alt] = importlib.import_module(
                "%s.%s" % (_master.__name__, info.name))
        except Exception:
            # stumm gewollt: siehe skills2 - die Weiterleitung ist Bequemlichkeit,
            # keine Zusicherung. Der echte Import meldet seinen Fehler selbst.
            continue


_module_umhaengen()
