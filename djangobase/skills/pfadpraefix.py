# -*- coding: utf-8 -*-
u"""Pfadpraefix — eine Pfadpruefung, die auf Zeichen statt auf Ordner schaut.

DER FEHLER
==========
::

    if str(ziel).startswith(str(wurzel)):
        ...  # gilt als „liegt unter der Wurzel"

Das ist ein ZEICHENKETTEN-Vergleich. ``…/media_evil/x.bvh`` beginnt mit
``…/media``, also besteht es die Pruefung — und der Endpunkt schreibt in einen
Ordner, den er nie anfassen sollte. Richtig ist ``Path.is_relative_to``, das
Pfad-TEILE vergleicht (und unter Windows zusaetzlich aufloest, weil ``A:\\Media``
und ``a:\\media`` dasselbe Verzeichnis sind).

WARUM ALS WERKZEUG
==================
Dieselbe Schreibweise ist in 3DTools VIERMAL aufgetaucht und viermal einzeln
gefunden worden:

    12.08.2026  drei Endpunkte nahmen jeden Pfad an; der vierte prueft mit
                ``startswith`` — daraus entstand ``core/safe_paths.SafePath``.
    13.08.2026  ``smooth_bvh`` und ``save_bvh_effects`` (die Datei wird am Ende
                UEBERSCHRIEBEN).
    16.08.2026  ``retarget`` — beim Umbau am 12.08. uebersehen.
    27.08.2026  ``api/posen.py`` — ``poseData`` gegen ``poseData_evil``; die
                Ansicht loescht und benennt um. Im selben Durchgang fanden sich
                sechs weitere Stellen.

Ein Fund, der sich viermal wiederholt, gehoert in den Werkzeugkasten und nicht
in die Erinnerung.

WAS GEMELDET WIRD
=================
``x.startswith(y)``, wenn BEIDE Seiten nach Pfad aussehen: ``str(...)``,
``os.path.normpath(...)``, ``Path(...)``, ``os.path.join(...)`` — oder ein Name,
der auf ``pfad``, ``path``, ``dir``, ``wurzel``, ``root``, ``ordner``, ``ziel``
oder ``datei`` endet.

WAS NICHT GEMELDET WIRD
=======================
* ``startswith`` auf offensichtlichen Nicht-Pfaden: ``'morph_'``, ``'#'``,
  ``'http'``.
* ADRESSEN statt Pfade (29.08.2026): ``pfad.startswith(str(settings.MEDIA_URL))``
  vergleicht URL-Praefixe. ``Path.is_relative_to`` gibt es dafuer nicht, und
  die Luecke, um die es hier geht, ist zu: Djangos Systempruefung ``urls.E006``
  erzwingt den Schraegstrich am Ende von ``MEDIA_URL``/``STATIC_URL``, also
  besteht ``/mediathek/x`` den Vergleich mit ``/media/`` NICHT. Erkannt an
  einem Namen, der auf ``url`` endet, oder an einer Zeichenkette, die auf
  ``/`` endet.
* Die eigene Datei und ``safe_paths.py`` — dort steht der Vergleich als
  Gegenbeispiel im Docstring.
"""
import ast
import re

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

__all__ = ["Pfadpraefix"]


class Pfadpraefix(BefundWerkzeug):
    """Pfadpruefungen per ``startswith`` statt ``is_relative_to``."""

    slug = "pfadpraefix"
    titel = "Pfadpruefung per Zeichenvergleich"
    zweck = ("Findet `str(ziel).startswith(str(wurzel))` — ein Nachbarordner "
             "mit gleichem Namensanfang besteht diese Pruefung.")
    befund = ("Viermal in 3DTools gefunden und viermal einzeln repariert: "
              "`media_evil` beginnt mit `media`, `poseData_evil` mit "
              "`poseData`. Dahinter liegen Endpunkte, die schreiben, "
              "ueberschreiben und loeschen.")
    abhilfe = ("`Path(ziel).resolve().is_relative_to(Path(wurzel).resolve())` "
               "— oder eine eigene Wurzelpruefung, die zusaetzlich "
               "Geraetenamen, UNC-Pfade und NTFS-Datenstroeme abweist.")
    dauer = "unter 1 s"
    kriterium = 0

    anlassfall = Anlassfall(
        {"wache.py": (
            "import os\n"
            "\n"
            "\n"
            "def erlaubt(ziel, wurzel):\n"
            "    return str(ziel).startswith(os.path.normpath(wurzel))\n"),
         "adresse.py": (
            "from django.conf import settings\n"
            "\n"
            "\n"
            "def ist_medium(pfad):\n"
            "    return pfad.startswith(str(settings.MEDIA_URL))\n"),
         "sauber.py": (
            "from pathlib import Path\n"
            "\n"
            "\n"
            "def erlaubt(ziel, wurzel):\n"
            "    return Path(ziel).resolve().is_relative_to(Path(wurzel))\n")},
        mindestens=1, hoechstens=1, erwartet_in="wache.py",
        warum="In 3DTools viermal einzeln gefunden: `media_evil` beginnt mit "
              "`media`, `poseData_evil` mit `poseData`. Dahinter lagen "
              "Endpunkte, die schreiben, ueberschreiben und loeschen. "
              "`sauber.py` und `adresse.py` stehen daneben: die richtige "
              "Schreibweise und ein URL-Vergleich, der wie einer "
              "aussieht und keiner ist.")

    #: Namensenden, die auf einen Pfad deuten.
    PFADNAMEN = re.compile(r"(pfad|path|dir|wurzel|root|ordner|ziel|datei)$",
                           re.I)
    #: Aufrufe, deren Ergebnis ein Pfad ist.
    PFADRUFE = ("str", "normpath", "abspath", "realpath", "Path", "resolve",
                "join")
    #: Diese Dateien beschreiben den Fehler, statt ihn zu machen.
    AUSNAHMEN = ("safe_paths.py", "pfadpraefix.py")

    def pruefen(self, **_argumente):
        befunde = []
        dateien = 0
        for pfad in self.projektdateien(".py"):
            if pfad.name in self.AUSNAHMEN:
                continue
            baum = self._baum(pfad)
            if baum is None:
                continue
            dateien += 1
            befunde += self._aus_baum(baum, self.kurz(pfad))
        kopf = ["%d Python-Dateien gelesen" % dateien,
                "%d Pfadpruefungen per Zeichenvergleich" % len(befunde)]
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
            if not isinstance(knoten, ast.Call):
                continue
            if not isinstance(knoten.func, ast.Attribute):
                continue
            if knoten.func.attr != "startswith" or len(knoten.args) != 1:
                continue
            if not (self._nach_pfad(knoten.func.value)
                    and self._nach_pfad(knoten.args[0])):
                continue
            if self._ist_adresse(knoten.args[0]):
                continue
            raus.append(Befund(
                "%s:%d" % (name, knoten.lineno),
                "startswith(…) als Pfadpruefung",
                "Ein Nachbarordner mit gleichem Namensanfang besteht sie. "
                "`Path.is_relative_to` vergleicht Pfadteile statt Zeichen.",
                Befund.FEHLER))
        return raus

    def _ist_adresse(self, knoten):
        """Wird hier ein URL-Praefix verglichen statt ein Pfad?

        Zwei Formen zaehlen: ein Name, der auf ``url`` endet (Djangos
        ``MEDIA_URL``/``STATIC_URL`` muessen laut ``urls.E006`` auf ``/``
        enden — damit ist die Luecke zu), und eine Zeichenkette, die selbst
        auf ``/`` endet. Alles andere bleibt ein Befund.
        """
        if isinstance(knoten, ast.Call):
            return any(self._ist_adresse(a) for a in knoten.args)
        if isinstance(knoten, ast.Name):
            return knoten.id.lower().endswith("url")
        if isinstance(knoten, ast.Attribute):
            return knoten.attr.lower().endswith("url")
        if isinstance(knoten, ast.Constant) and isinstance(knoten.value, str):
            return knoten.value.endswith("/")
        return False

    def _nach_pfad(self, knoten):
        """Sieht dieser Ausdruck nach einem Pfad aus?"""
        if isinstance(knoten, ast.Call):
            gerufen = knoten.func
            name = (gerufen.attr if isinstance(gerufen, ast.Attribute)
                    else getattr(gerufen, "id", ""))
            if name in self.PFADRUFE:
                return True
            return any(self._nach_pfad(a) for a in knoten.args)
        if isinstance(knoten, ast.Name):
            return bool(self.PFADNAMEN.search(knoten.id))
        if isinstance(knoten, ast.Attribute):
            return bool(self.PFADNAMEN.search(knoten.attr))
        return False
