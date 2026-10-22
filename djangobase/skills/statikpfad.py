# -*- coding: utf-8 -*-
"""Ein relativer ES-Modul-Import, aufgelöst wie im Browser: im URL-Raum, nicht auf der Platte.

FEHLALARM (assistant, 22.10.2026): ``search/static/search/js/sys_stats_widget.js``
importiert ``../../djangobase/js/system_stats.js``. Auf der Platte zeigt das auf
``search/static/djangobase/js/`` — gibt es nicht. Der Browser rechnet aber von der
Adresse ``/static/search/js/sys_stats_widget.js`` aus und landet bei
``/static/djangobase/js/system_stats.js``; das liefert die App ``djangobase`` aus
ihrem eigenen Static-Ordner. ``esmodulimporte`` und ``jswaisen`` meldeten deshalb
zwei gültige Importe als „Datei fehlt" bzw. „Import ins Leere".

Gilt genauso für ``{% fassungspfad %}`` (``/statik/v-<fassung>/…``): relative
Importe bleiben unter derselben Wurzel. Ein Import, der über die Static-Wurzel
hinaus nach oben zeigt, findet nichts — wie im Browser.
"""

from __future__ import annotations

import posixpath
from pathlib import Path


class Statikpfad:
    WURZEL = "/static/"

    @classmethod
    def adresse(cls, quelldatei: Path, angabe: str) -> str | None:
        """Der Pfad unter ``/static/``, den der Browser aus ``angabe`` macht — oder
        None, wenn die Quelldatei in keinem ``static``-Ordner liegt oder der Import
        über die Wurzel hinausgeht."""
        teile = Path(quelldatei).parts
        if "static" not in teile:
            return None
        i = len(teile) - 1 - teile[::-1].index("static")
        basis = cls.WURZEL + "/".join(teile[i + 1 : -1])
        ziel = posixpath.normpath(posixpath.join(basis, angabe.split("?")[0]))
        if not ziel.startswith(cls.WURZEL):
            return None
        return ziel[len(cls.WURZEL) :]

    @classmethod
    def finden(cls, quelldatei: Path, angabe: str) -> Path | None:
        """Die Datei, die Djangos Static-Finder für diese Adresse ausliefert, sonst None."""
        adresse = cls.adresse(quelldatei, angabe)
        if not adresse:
            return None
        from django.contrib.staticfiles import finders

        treffer = finders.find(adresse)
        if isinstance(treffer, (list, tuple)):
            treffer = treffer[0] if treffer else None
        return Path(treffer).resolve() if treffer else None
