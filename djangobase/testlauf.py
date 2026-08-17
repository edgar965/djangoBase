# -*- coding: utf-8 -*-
u"""Testlauf - ein Testkommando fahren und seine Laufzeiten festhalten.

Aus ``views/tests.py`` herausgeloest (17.08.2026): Die Ansicht war mit den
Laufzeiten auf 399 Zeilen gewachsen und trug drei Aufgaben. Hier steht nur noch
die eine: Prozess starten, Ausgabe einsammeln, Historie schreiben.

WAS DABEI ZU BEACHTEN WAR
=========================
* ``--durations 0`` kommt aus :class:`~.testdauern.Dauern` und nur, wenn der
  Interpreter DES PROJEKTS es kennt (Python 3.12+).
* Der Block „Slowest test durations" landet je nach Django/unittest auf stdout
  ODER stderr - beide werden gelesen, statt zu raten.
* Ein Fehler beim Schreiben der Historie darf den Lauf nicht kosten: Das
  Ergebnis steht schon fest, nur die Laufzeiten fehlen dann.
"""
import logging
import subprocess
import time

from django.conf import settings

from .testdauern import Dauern
from .zeitformat import dauer_text
from .testhistorie import Testhistorie

__all__ = ["Testlauf"]

log = logging.getLogger("djangobase.tests")

#: Auf Windows kein Konsolenfenster je Lauf.
_NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)


class Testlauf:
    """Ein Aufruf von ``manage.py test …`` samt Laufzeit-Erfassung."""

    #: Vorgabe-Frist eines Einzellaufs.
    FRIST = 600

    def __init__(self, historie=None):
        self.historie = historie or Testhistorie()

    def fahren(self, cmd, name, frist=None, slug=""):
        u"""Fahren und Ergebnis liefern (dieselben Schluessel wie bisher)."""
        cmd = Dauern.option_setzen(cmd)
        t0 = time.time()
        try:
            r = subprocess.run(cmd, capture_output=True, text=True,
                               timeout=int(frist or self.FRIST),
                               encoding="utf-8", errors="replace",
                               cwd=str(settings.BASE_DIR),
                               creationflags=_NO_WINDOW)
            out, err, rc = r.stdout or "", r.stderr or "", r.returncode
        except Exception as exc:  # noqa: BLE001
            out, err, rc = "", str(exc), -1
        # Drei Nachkommastellen, nicht eine: Ein Lauf unter einer Sekunde wird
        # in Millisekunden angezeigt (Ansage 17.08.2026), und aus einer auf 0,1
        # gerundeten Zahl wuerden dort Stufen von 100 ms.
        dauer = round(time.time() - t0, 3)
        dauern = Dauern.lesen(out) or Dauern.lesen(err)
        self._merken(slug, name, dauer, rc == 0, dauern)
        # Dictionary gewollt: geht unveraendert in die Vorlage.
        return {"name": name,
                "cmd": " ".join(cmd) if isinstance(cmd, (list, tuple)) else str(cmd),
                "rc": rc, "ok": rc == 0,
                "out": out[-40000:], "err": err[-40000:],
                "dauer": dauer, "dauer_text": dauer_text(dauer),
                "dauern": len(dauern)}

    def _merken(self, slug, name, dauer, ok, dauern):
        zeit = time.strftime("%d.%m.%Y %H:%M:%S")
        suite = ({"slug": slug, "name": name, "dauer": dauer, "ok": ok,
                  "tests": len(dauern)} if slug else None)
        try:
            self.historie.merken(zeit, dauern, suite)
        except Exception:  # noqa: BLE001
            log.exception("Testhistorie nicht geschrieben — der Lauf selbst ist "
                          "unberührt, nur seine Laufzeiten fehlen")
