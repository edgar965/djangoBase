# -*- coding: utf-8 -*-
u"""Skills2 - WEITERLEITUNG auf ``djangobase.skills``. Wird abgeschafft.

Die Werkzeuge dieses Pakets liegen seit 17.08.2026 in ``djangobase.skills``;
dort ist der Werkzeugkasten zusammengefuehrt. Hier steht nur noch die
Weiterleitung, damit vorhandene Importe, Links und Lesezeichen weiterlaufen -
und damit man sieht, wo nachzuziehen ist.

WARUM NICHT SOFORT LOESCHEN
===========================
Ein Paket zu entfernen, auf das noch etwas zeigt, erzeugt einen ImportError an
einer Stelle, die mit dem Umbau nichts zu tun hat. Die Weiterleitung kostet
nichts und macht den Uebergang nachpruefbar: Solange hier etwas ankommt, ist
noch nicht alles umgestellt.

WAS SICH AENDERT
================
``werkzeuge()`` liefert jetzt ALLE Werkzeuge des Masters, nicht mehr nur die
achtundzwanzig von hier. Das ist die Absicht: Der Master ist der Werkzeugkasten,
diese Seite nur noch eine zweite Tuer dorthin.

Auch die Submodul-Importe laufen weiter (``from djangobase.skills2.jsklammern
import Klammerzaehler``) - siehe die Modul-Zuordnung unten.
"""
import sys as _sys

from .. import skills as _master
from ..skills import *                                    # noqa: F401,F403
from ..skills import __all__ as _MASTER_ALL

__all__ = list(_MASTER_ALL)

#: Die Module liegen jetzt unter ``djangobase.skills``. Damit ein alter Import
#: wie ``from djangobase.skills2.jsklammern import Klammerzaehler`` weiterhin
#: greift, wird jedes geladene Master-Modul zusaetzlich unter dem alten Pfad
#: eingetragen. Ohne das haette der Umbau in ``djangobase/umbau/`` und in
#: fremden Projekten ImportError geworfen - an Stellen, die niemand angefasst hat.
def _module_umhaengen():
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
            # stumm gewollt: Ein Modul, das sich nicht laden laesst, meldet sich
            # beim echten Import mit seinem eigenen Fehler. Hier waere die
            # Meldung nur Rauschen beim Hochfahren - die Weiterleitung ist
            # Bequemlichkeit, keine Zusicherung.
            continue


_module_umhaengen()
