# -*- coding: utf-8 -*-
u"""ImportFixer - tote Importe entfernen, auf der skills2-Fixer-Basis.

WARUM AUF ``skills2.fixer.Fixer``
================================
Diese Basis bringt mit, was aggressives Fixen erst verantwortbar macht: eine
SICHERUNG (das Original wandert mit Zeitstempel nach ``werkzeug/sicherung/fixer``)
und ein NETZ (nach dem Schreiben ``pruefen``; faellt es, wird die Datei
zurueckgespielt statt kaputt liegengelassen). skills2 hat keinen Import-Fixer -
dieser ergaenzt die dortigen Fixer (``fix-vermerk``, ``fix-jsschnitt``) um
Kriterium 5, ohne die Basis zu duplizieren.

VIER SICHERUNGEN, DAMIT NUR EINDEUTIG TOTES FAELLT
==================================================
* Seiteneffekt-Module (``signals`` & Co.) bleiben - ihr Import registriert
  Handler, ohne einen Namen zu benutzen.
* ``__init__.py`` bleibt aussen vor (Re-Exporte ohne ``__all__``).
* Nur EINZEILIGE Anweisungen, deren Name(n) ALLE unbenutzt sind - ein
  Teil-Entfernen aus ``import os, sys`` ist zu fehleranfaellig.
* ``__all__``-Eintraege und ``"app.Modell"``-Strings zaehlen als Verwendung.
"""
import ast
import re

from .anlassfall import Anlassfall
from .fixer import Aenderung, Fixer, Vorschau

__all__ = ["ImportFixer"]

#: Verzeichnisse, die nie eigener Projektcode sind (auch Fremd-/Datenordner).
RAUS = ("__pycache__", "migrations", "node_modules", "venv", "pythonVENV",
        ".venv", "site-packages", "staticfiles", ".git", "sicherung", "backup",
        "archiv", "dist", "build", "vendor", "models", "unsloth_compiled_cache")


class ImportFixer(Fixer):
    #: HIESS BIS ZUM 25.08.2026 `tote-importe` — wie das PRUEFWERKZEUG
    #: (``toteimporte.ToteImporte``). Zwei Eintraege unter einer Kennung:
    #:
    #:   * `werkzeug_finden("tote-importe")` war mehrdeutig,
    #:   * der neue Werkzeugkatalog druckte zwei Zeilen mit demselben Namen,
    #:   * und `anlassfall-check` legt sein Pruefverzeichnis nach dem Slug an
    #:     — beide haetten in denselben Ordner geschrieben.
    #:
    #: `fix-importe` heisst jetzt wie die Datei und passt zu den uebrigen
    #: Fixern (`fix-vermerk`, `fix-jsschnitt`, `fix-fzeichenkette`).
    slug = "fix-importe"
    #: Der Befund, den dieser Fixer behebt — als Kennung des
    #: Werkzeugs, das ihn meldet. Die Oberflaeche zeigt daraus die
    #: NUMMER der Pruefung in der Tabelle statt einer
    #: Kriteriums-Nummer, die dort nirgends steht.
    behebt = 'tote-importe'
    titel = "Tote Importe entfernen"
    tut = "Entfernt importierte Namen, die in der Datei nirgends vorkommen."

    #: Markierung fuer "aus dieser Datei holt jemand per import *".
    #: Ein Name, den es als Python-Bezeichner nicht geben kann - so kann er
    #: nie mit einem echten Import kollidieren.
    STERN = "*stern*"
    warum = ("Tote Importe kosten Ladezeit, halten Abhängigkeiten kuenstlich am "
             "Leben und verwischen, welches Modul wirklich wovon abhaengt.")
    grenzen = ("Seiteneffekt-Importe (signals, admin) und __init__.py bleiben. "
               "Mehrfach-Importe (import os, sys) bleiben, wenn nur einer tot ist.")
    kriterium = 5
    dauer = "3-8 s"

    anlassfall = Anlassfall(
        {"laden.py": "import json\n"
                     "import os\n"
                     "import sys  # noqa: F401\n"
                     "\n\n"
                     "def lesen(pfad):\n"
                     "    return json.loads(open(pfad).read())\n"},
        mindestens=1, hoechstens=1, erwartet_in="laden.py",
        warum="`os` ist tot und fällt; `json` wird gebraucht und `sys` trägt "
              "ein noqa — beide müssen stehenbleiben")

    #: Modul-Endungen, deren blosser Import etwas bewirkt - nie entfernen.
    SEITENEFFEKT = {"signals", "admin", "receivers", "tasks", "checks", "apps"}
    ERLAUBT = {"annotations"}

    def vorschau(self):
        aenderungen = []
        for pfad in self._pyquellen():
            try:
                quelle = pfad.read_text(encoding="utf-8")
                baum = ast.parse(quelle)
            except (OSError, SyntaxError, ValueError):
                continue
            weg = self._tote_zeilen(baum, self._benutzt(baum))
            zeilen = quelle.splitlines(keepends=True)
            # `# noqa` ist die ausdrueckliche Ansage des Autors: unbenutzt,
            # aber gewollt (Weiterleitung, Seiteneffekt, Abwaertskompatibilitaet).
            # Wer sie uebergeht, entfernt Zeilen, die jemand bewusst
            # stehengelassen hat - am 22.08.2026 im assistant passiert
            # (`from .dav_schalter import suppress_dav_push  # noqa: F401`).
            weg = {n for n in weg
                   if 'noqa' not in zeilen[n - 1].lower()}
            # FUENFTE SICHERUNG (25.08.2026): Holt jemand den Namen AUS
            # DIESER Datei? Siehe `_wird_weitergereicht`.
            weg = {n for n in weg
                   if not self._wird_weitergereicht(pfad, baum, n)}
            if not weg:
                continue
            neu = "".join(z for i, z in enumerate(zeilen, 1) if i not in weg)
            aenderungen.append(Aenderung(
                pfad, "%d tote Importe entfernen" % len(weg), neu))
        return Vorschau(aenderungen,
                        "Nur einzeilige Importe mit durchweg unbenutztem Namen; "
                        "Seiteneffekt-Module und __init__.py bleiben aussen vor.")

    def pruefen(self, aenderung):
        """Netz: kompiliert die Datei nach dem Schnitt noch?

        DAS REICHT NICHT ALLEIN, und das ist wichtig zu wissen: Ein
        gebrochener Re-Export kompiliert tadellos. Er fällt erst auf,
        wenn ein ANDERES Modul den Namen holen will - im Zweifel erst
        beim Start der Anwendung. Deshalb liegt die eigentliche
        Sicherung in `_wird_weitergereicht`, VOR dem Schnitt.
        """
        try:
            ast.parse(aenderung.pfad.read_text(encoding="utf-8"))
        except SyntaxError as e:
            return ["kompiliert nicht mehr: %s" % e]
        except OSError as e:
            return ["nicht lesbar: %s" % e]
        return []

    def _wird_weitergereicht(self, pfad, baum, zeile):
        """Holt ein anderes Modul einen dieser Namen AUS DIESER Datei?

        DER VORFALL (25.08.2026, Projekt assistant)
        ===========================================
        In `mail/sync/MailboxSyncer/kern.py` stand::

            from .basis import SyncFolderResult

        - im Modul selbst nirgends benutzt, also nach allen bisherigen
        Regeln tot. Daneben lag::

            # mail/sync/MailboxSyncer/__init__.py
            # SyncFolderResult stand als zweite Klasse in derselben Datei
            # und wird von aussen gebraucht - beim ersten Schnitt fiel
            # sie durch (23.08.2026).
            from .kern import MailboxSyncer, SyncFolderResult  # noqa: F401

        Nach dem Schnitt war die Anwendung nicht mehr startbar:
        `ImportError: cannot import name 'SyncFolderResult' from
        'mail.sync.MailboxSyncer.kern'`.

        Die vorhandenen Sicherungen greifen hier alle NICHT: `__init__.py`
        ist geschuetzt, aber die Datei, aus der es holt, war es nicht.
        Das `# noqa` steht in der anderen Datei. Und das Netz
        (`pruefen`) sieht nichts, weil die geschnittene Datei weiter
        sauber kompiliert.

        Ein Modul kann also ein Durchgangstor sein, ohne `__init__.py` zu
        heissen. Deshalb wird jetzt gefragt, ob irgendwo im Projekt
        `from <dieses Modul> import <Name>` steht.
        """
        geholt = self._geholte_namen().get(pfad.stem, set())
        # Holt IRGENDWER per ``import *`` aus dieser Datei, ist jeder Import
        # darin potentiell der, den ein anderes Modul braucht - siehe
        # :meth:`_geholte_namen`. Dann bleibt die ganze Datei unangetastet.
        if self.STERN in geholt:
            return True
        namen = set()
        for k in ast.walk(baum):
            if isinstance(k, (ast.Import, ast.ImportFrom)) and k.lineno == zeile:
                namen |= {(a.asname or a.name).split(".")[0] for a in k.names}
        if not namen:
            return False
        return bool(namen & geholt)

    def _geholte_namen(self):
        """``{Modulname: {Namen, die andere daraus holen}}`` - einmal gebaut.

        Bewusst nur ueber den Modul-KURZNAMEN (`kern`, nicht
        `mail.sync.MailboxSyncer.kern`): Der relative Import
        `from .kern import X` nennt den vollen Pfad gar nicht. Zwei
        gleichnamige Module in verschiedenen Paketen schuetzen sich damit
        gegenseitig - das ist die harmlose Richtung, denn zu viel
        stehenlassen kostet eine Zeile, zu viel schneiden eine
        startunfaehige Anwendung.
        """
        if getattr(self, "_geholt", None) is not None:
            return self._geholt
        raus = {}
        # AUCH MEHRZEILIGE IMPORTE (26.08.2026 - der Vorfall in shortlongx)
        # ==================================================================
        # Hier stand ``import\s+(.+)$``: Das liest nur bis zum Zeilenende.
        # Bei der ueblichen Klammerform
        #
        #     from .basis import (
        #         logger, render, JsonResponse, csrf_exempt, require_POST,
        #     )
        #
        # steht auf der ERSTEN Zeile nur ``(`` - alle Namen dahinter waren
        # unsichtbar. ``views/basis.py`` in shortlongx reicht so rund fuenfzig
        # Namen an zehn Module weiter; der Fixer hielt sie fuer tot und
        # entfernte sie. Danach war keine einzige Seite mehr aufrufbar
        # (``NameError: name 'require_POST' is not defined``).
        #
        # Die Sicherung hat den Schaden reparabel gemacht - aber genau davor
        # sollte diese Methode schuetzen, und sie sah die Haelfte nicht.
        #
        # ``[^)]*`` laeuft ueber Zeilengrenzen (eine Zeichenklasse schliesst
        # ``\n`` ein), deshalb braucht es kein DOTALL - und weil die Klammer
        # zuerst versucht wird, gewinnt sie gegen die einzeilige Form.
        muster = re.compile(r"^[ \t]*from\s+([\w.]+)\s+import\s+(\([^)]*\)|[^\n]+)",
                            re.MULTILINE)
        for pfad in self.pfade("*.py"):
            if any(t in RAUS for t in pfad.parts):
                continue
            try:
                text = pfad.read_text(encoding="utf-8")
            except OSError:
                # stumm gewollt: Was sich nicht lesen laesst, holt auch
                # keinen Namen - genau die Frage hier.
                continue
            for woher, was in muster.findall(text):
                modul = woher.rsplit(".", 1)[-1]
                if not modul:
                    continue
                # STERN-IMPORT MACHT DAS MODUL UNANTASTBAR (26.08.2026)
                # ======================================================
                # ``from .basis_datensatz import *`` nennt KEINEN Namen. Ein
                # Werkzeug kann darum nicht wissen, welche gebraucht werden -
                # es sind moeglicherweise alle.
                #
                # DER VORFALL: shortlongx baut seine Views auf einer Kette von
                # Stern-Importen auf (``basis`` -> ``basis_segmente`` ->
                # ``basis_datensatz`` -> rund zehn View-Module). In ``basis.py``
                # selbst wird kaum einer der rund fuenfzig Importe benutzt; sie
                # sind ausschliesslich zum Weiterreichen da. Der Fixer hielt
                # alle fuer tot und entfernte sie - danach war keine Seite mehr
                # aufrufbar (``NameError: name 'require_POST' is not defined``).
                #
                # ``STERN`` als Markierung statt der Namensmenge: Der Eintrag
                # muss LEER bleiben duerfen und trotzdem schuetzen. Eine leere
                # Menge waere von „niemand holt hier etwas" nicht zu
                # unterscheiden - und genau das ist der gefaehrliche Fall.
                inhalt = was.split("#")[0].strip()
                if inhalt.strip("() \t\n") == "*":
                    raus.setdefault(modul, set()).add(self.STERN)
                    continue
                namen = {n.strip().split(" as ")[0].strip(" ()")
                         for n in inhalt.split(",")}
                raus.setdefault(modul, set()).update(n for n in namen if n)
        self._geholt = raus
        return raus

    # ------------------------------------------------------------------ intern

    def _pyquellen(self):
        for pfad in self.pfade("*.py"):
            if pfad.name == "__init__.py":
                continue
            if any(t in RAUS for t in pfad.parts):
                continue
            yield pfad

    def _tote_zeilen(self, baum, benutzt):
        weg = set()
        for k in ast.walk(baum):
            if not isinstance(k, (ast.Import, ast.ImportFrom)):
                continue
            if isinstance(k, ast.ImportFrom):
                if k.module == "__future__":
                    continue
                if (k.module or "").rsplit(".", 1)[-1] in self.SEITENEFFEKT:
                    continue
                if k.level and not k.module:        # from . import x -> Verdacht
                    continue
            if k.lineno != getattr(k, "end_lineno", k.lineno):
                continue                            # mehrzeilig: nicht anfassen
            namen = [n for n in k.names if n.name != "*"]
            if not namen or any(n.name in self.SEITENEFFEKT for n in namen):
                continue
            if all(self._kurz(n) not in benutzt and self._kurz(n) not in self.ERLAUBT
                   for n in namen):
                weg.add(k.lineno)
        return weg

    @staticmethod
    def _kurz(name):
        return (name.asname or name.name).split(".")[0]

    @staticmethod
    def _benutzt(baum):
        benutzt = set()
        for k in ast.walk(baum):
            if isinstance(k, ast.Name):
                benutzt.add(k.id)
            elif isinstance(k, ast.Attribute):
                w = k
                while isinstance(w, ast.Attribute):
                    w = w.value
                if isinstance(w, ast.Name):
                    benutzt.add(w.id)
            elif isinstance(k, ast.Constant) and isinstance(k.value, str):
                benutzt.update(k.value.replace(".", " ").replace("[", " ")
                               .replace("]", " ").split())
            elif isinstance(k, ast.Assign):
                for z in k.targets:
                    if isinstance(z, ast.Name) and z.id == "__all__":
                        for e in getattr(k.value, "elts", []):
                            if isinstance(e, ast.Constant):
                                benutzt.add(str(e.value))
        return benutzt
