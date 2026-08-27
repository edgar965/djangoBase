# -*- coding: utf-8 -*-
u"""NurLesen — schreibt jemand in ein Verzeichnis, das nur gelesen werden darf?

DER FALL
========
Fast jedes gewachsene Projekt hat Verzeichnisse, die MITGELIEFERT und nicht
erzeugt werden: Modellgewichte, Netzdaten, eingekaufte Bestaende, Referenzen.
Ein Schreibzugriff dorthin faellt nicht auf — es gibt keine Fehlermeldung, das
Ergebnis sieht nur irgendwann falsch aus.

Belegt in 3DTools: Die maennlichen Morphdaten (``.npy``) schrumpften von 437 KB
auf 218 KB. Die Vertexzahl war halbiert, der maennliche Charakter zerstoert.
Aufgefallen ist es erst am Netz im Browser; im Log stand nichts.

EINRICHTEN
==========
Das Werkzeug weiss nicht von selbst, welche Verzeichnisse gemeint sind — es
fragt die Einstellung::

    DJANGOBASE["daten_nur_lesen"] = {
        "wurzeln": ["HumanBody/data", "HumanBodyBlender/data"],
        "ausser": ["models", "animations", "studio_projects"],
        "einstellungen": ["HUMANBODY_DATA_DIR", "HUMANBODY_BVH_DIR"],
    }

* ``wurzeln`` — Pfadstuecke, die im Quelltext auf ein solches Verzeichnis
  deuten. Vergleich auf der mit ``/`` vereinheitlichten Schreibweise.
* ``ausser`` — Unterordner darunter, die SEHR WOHL beschrieben werden duerfen
  (was der Benutzer ueber die Oberflaeche anlegt).
* ``einstellungen`` — Namen aus ``settings``, die auf eine solche Wurzel
  zeigen. Ein ``settings.HUMANBODY_DATA_DIR / 'x.npy'`` traegt den Pfad ja
  nicht als Text.

Ohne Einstellung meldet das Werkzeug nichts und sagt das in der Kopfzeile —
statt zu raten.

WAS GESUCHT WIRD
================
Aufrufe, die SCHREIBEN (``open(..., 'w')``, ``np.save``, ``shutil.copy``,
``Path.write_text``, ``rmtree``, ``unlink``, ``makedirs``) und deren Zielpfad
erkennbar unter einer der Wurzeln liegt. Lesen wird nie gemeldet.
"""
import ast
import re

from django.conf import settings

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

__all__ = ["NurLesen"]


class NurLesen(BefundWerkzeug):
    """Schreibzugriffe auf mitgelieferte, unersetzliche Daten."""

    slug = "nur-lesen"
    titel = "Nur-Lesen-Verzeichnisse: schreibende Zugriffe"
    zweck = ("Findet Stellen, die in ein als read-only erklaertes Verzeichnis "
             "schreiben. Konfiguriert ueber "
             "`DJANGOBASE[\"daten_nur_lesen\"]`.")
    befund = ("3DTools: Die maennlichen Morphdaten schrumpften von 437 KB auf "
              "218 KB — halbe Vertexzahl, Charakter zerstoert. Ohne "
              "Fehlermeldung; nur das Netz im Browser sah falsch aus.")
    abhilfe = ("In ein Wegwerfverzeichnis schreiben. Wenn es wirklich die "
               "Produktivdaten sein muessen: ausdruecklich beauftragen lassen "
               "und vorher sichern.")
    dauer = "unter 1 s"
    kriterium = 0

    anlassfall = Anlassfall(
        {"schreiber.py": (
            "import numpy as np\n"
            "\n"
            "\n"
            "def sichern(werte):\n"
            "    np.save('daten/nurlesen/morphs.npy', werte)\n"),
         "leser.py": (
            "import numpy as np\n"
            "\n"
            "\n"
            "def holen():\n"
            "    return np.load('daten/nurlesen/morphs.npy')\n")},
        mindestens=1, hoechstens=1, erwartet_in="schreiber.py",
        warum="`np.save` in ein Nur-Lesen-Verzeichnis. `leser.py` steht "
              "daneben, damit das Werkzeug nicht jeden Zugriff meldet — "
              "Lesen ist genau der erlaubte Fall.",
        )

    #: Aufrufe, die Dateien anlegen, ueberschreiben oder entfernen.
    SCHREIBER = frozenset({"save", "savez", "savez_compressed", "write_text",
                           "write_bytes", "copy", "copy2", "copyfile", "move",
                           "rmtree", "unlink", "remove", "mkdir", "makedirs"})
    #: ``open(..., 'w'|'a'|'x'|'wb'|…)`` — der Modus steht als zweites
    #: Argument oder als ``mode=``.
    SCHREIBMODUS = re.compile(r"^[wax]")

    #: Die Wurzel des eigenen Anlassfalls. Sie gilt IMMER — auch wenn das
    #: Projekt eigene Wurzeln einstellt. Im ersten Wurf galt sie nur als
    #: Rueckfall, und damit war das Werkzeug in jedem eingerichteten Projekt
    #: „blind": `anlassfall-check` legt seine Dateien unter `daten/nurlesen`
    #: ab, und danach suchte niemand mehr. Der Name ist absichtlich so
    #: gewaehlt, dass er in echtem Quelltext nicht vorkommt.
    PROBEWURZEL = "daten/nurlesen"

    # ------------------------------------------------------------ Einstellung

    def einstellung(self):
        cfg = getattr(settings, "DJANGOBASE", {}) or {}
        return cfg.get("daten_nur_lesen") or {}

    def wurzeln(self):
        eigene = [str(w).replace("\\", "/")
                  for w in (self.einstellung().get("wurzeln") or [])]
        return eigene + [self.PROBEWURZEL]

    def ausser(self):
        return tuple(str(a) for a in (self.einstellung().get("ausser") or ()))

    def namen(self):
        return tuple(str(n) for n in
                     (self.einstellung().get("einstellungen") or ()))

    # ----------------------------------------------------------------- Ablauf

    def pruefen(self, **_argumente):
        eingerichtet = bool(self.einstellung().get("wurzeln"))
        befunde = []
        dateien = 0
        for pfad in self.projektdateien(".py"):
            baum = self._baum(pfad)
            if baum is None:
                continue
            dateien += 1
            befunde += self._aus_baum(baum, self.kurz(pfad))
        kopf = ["%d Python-Dateien gelesen" % dateien,
                "%d schreibende Zugriffe" % len(befunde)]
        if eingerichtet:
            kopf.append("Wurzeln: %s"
                        % ", ".join(self.einstellung().get("wurzeln") or ()))
        else:
            kopf.append('nicht eingerichtet — `DJANGOBASE'
                        '["daten_nur_lesen"]["wurzeln"]` setzen')
        return Befundsatz(self.titel, kopf, befunde)

    @staticmethod
    def _baum(pfad):
        try:
            return ast.parse(pfad.read_text(encoding="utf-8", errors="replace"))
        except (OSError, SyntaxError):
            return None

    def _aus_baum(self, baum, name):
        raus = []
        for knoten in ast.walk(baum):
            if not isinstance(knoten, ast.Call) or not self._schreibt(knoten):
                continue
            ziel = self._zielhinweis(knoten)
            if not ziel:
                continue
            raus.append(Befund(
                "%s:%d" % (name, knoten.lineno),
                "%s(…) auf %s" % (self._rufname(knoten), ziel),
                "Zielpfad liegt unter einem Verzeichnis, das als nur lesbar "
                "erklaert ist.",
                Befund.FEHLER))
        return raus

    @staticmethod
    def _rufname(knoten):
        ziel = knoten.func
        if isinstance(ziel, ast.Attribute):
            return ziel.attr
        return getattr(ziel, "id", "?")

    def _schreibt(self, knoten):
        name = self._rufname(knoten)
        if name in self.SCHREIBER:
            return True
        return name == "open" and self._oeffnet_schreibend(knoten)

    def _oeffnet_schreibend(self, knoten):
        modus = None
        if len(knoten.args) > 1 and isinstance(knoten.args[1], ast.Constant):
            modus = knoten.args[1].value
        for wort in knoten.keywords:
            if wort.arg == "mode" and isinstance(wort.value, ast.Constant):
                modus = wort.value.value
        return bool(modus) and bool(self.SCHREIBMODUS.match(str(modus)))

    # -------------------------------------------------------------- Zielpfade

    def _zielhinweis(self, knoten):
        """Der erkennbare Zielpfad — leer, wenn er nicht geschuetzt ist."""
        teile = list(knoten.args) + [w.value for w in knoten.keywords]
        for teil in teile:
            text = self._pfadtext(teil)
            if text and self._geschuetzt(text):
                return text[:60]
        return ""

    @staticmethod
    def _pfadtext(knoten):
        """Zeichenketten und Namen aus einem Pfadausdruck, zusammengesetzt."""
        stuecke = []
        for innen in ast.walk(knoten):
            if isinstance(innen, ast.Constant) and isinstance(innen.value, str):
                stuecke.append(innen.value)
            elif isinstance(innen, ast.Attribute):
                stuecke.append(innen.attr)
            elif isinstance(innen, ast.Name):
                stuecke.append(innen.id)
        return "/".join(stuecke)

    def _geschuetzt(self, text):
        flach = text.replace("\\", "/")
        if any(erlaubt in flach for erlaubt in self.ausser()):
            return False
        if any(name in text for name in self.namen()):
            return True
        return any(wurzel in flach for wurzel in self.wurzeln())
