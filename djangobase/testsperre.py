# -*- coding: utf-8 -*-
u"""Laufsperre - EIN Testlauf zur Zeit, prozessuebergreifend.

Zwei Testlaeufe gleichzeitig bauen dieselbe Testdatenbank zweimal auf. Der
zweite scheitert beim Anlegen („database … is being accessed by other users")
oder, schlimmer, beide raeumen sich gegenseitig die Datenbank ab.

WARUM NICHT IM BROWSER
======================
Die erste Fassung sperrte die Knoepfe in ``tests_strom.js``. Das hilft genau
einem Tab: Ein zweiter Tab, ein zweiter Browser oder ein zweiter Nutzer weiss
davon nichts. Die Sperre gehoert dorthin, wo der Prozess gestartet wird.

WARUM EINE DATEI UND KEIN CACHE
===============================
Djangos Vorgabe-Cache (``LocMemCache``) lebt im PROZESS. Unter einem Server mit
mehreren Arbeitern (gunicorn, Waitress-Threads sind egal, Prozesse nicht) haette
jeder seinen eigenen „einen Lauf". Eine Datei sehen alle.

STEHENGEBLIEBENE SPERREN
========================
Wird der Server hart beendet, bleibt die Datei liegen. Deshalb steht die PID des
SERVERS darin: Lebt der Prozess nicht mehr, ist die Sperre wertlos und wird
uebernommen. Zusaetzlich gilt sie hoechstens ``FRIST`` Sekunden — ein Lauf, der
laenger braucht, ist ohnehin abgebrochen.
"""
import json
import logging
import os
import sys
import time
from pathlib import Path

from django.conf import settings

__all__ = ["Laufsperre"]

log = logging.getLogger("djangobase.tests")


class Laufsperre:
    """Dateibasierte Sperre um einen Testlauf."""

    DATEINAME = "teststrom.lock"
    #: Laenger gilt keine Sperre - danach gilt sie als vergessen.
    FRIST = 3600

    def __init__(self, pfad=None):
        self.pfad = Path(pfad) if pfad else self._vorgabe()
        self.gehalten = False

    @staticmethod
    def _vorgabe():
        basis = Path(getattr(settings, "BASE_DIR", "."))
        ordner = basis / "logs"
        return (ordner if ordner.is_dir() else basis) / Laufsperre.DATEINAME

    # ------------------------------------------------------------------ Lesen

    def zustand(self):
        u"""Der Eintrag der laufenden Sperre - oder ``None``."""
        try:
            daten = json.loads(self.pfad.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            # stumm gewollt: Keine Datei heisst „frei" - der Normalfall.
            return None
        if not isinstance(daten, dict):
            return None
        if time.time() - float(daten.get("seit") or 0) > self.FRIST:
            return None
        pid = daten.get("server_pid")
        if pid and not self.lebt(int(pid)):
            # Der Server, der die Sperre gesetzt hat, laeuft nicht mehr.
            return None
        return daten

    @staticmethod
    def lebt(pid):
        u"""Laeuft dieser Prozess noch?

        Windows kennt ``os.kill(pid, 0)`` nicht in dieser Bedeutung, deshalb
        ueber ``OpenProcess``. Kein ``psutil``: djangoBase soll ohne zusaetzliche
        Abhaengigkeit laufen.
        """
        if not pid:
            return False
        if sys.platform.startswith("win"):
            import ctypes
            # NICHT nur OpenProcess: Das gelingt auch fuer einen BEENDETEN
            # Prozess, solange irgendwo noch ein Handle darauf offen ist (bei
            # einem `Popen` haelt Python es). Gemessen 18.08.2026: Nach
            # `taskkill /T /F` und `kill()` galt der Prozess weiter als lebend,
            # und eine vergessene Sperre haette bis zur Frist gehalten.
            # Maßgeblich ist der Exitcode: 259 (STILL_ACTIVE) heisst „laeuft".
            STILL_ACTIVE = 259
            RECHTE = 0x0400 | 0x00100000        # QUERY_INFORMATION | SYNCHRONIZE
            kernel = ctypes.windll.kernel32
            handle = kernel.OpenProcess(RECHTE, False, int(pid))
            if not handle:
                return False
            try:
                code = ctypes.c_ulong()
                if not kernel.GetExitCodeProcess(handle, ctypes.byref(code)):
                    return True             # nicht abfragbar -> lieber „lebt"
                return code.value == STILL_ACTIVE
            finally:
                kernel.CloseHandle(handle)
        try:
            os.kill(int(pid), 0)
        except (OSError, ValueError):
            return False
        return True

    # -------------------------------------------------------------- Schreiben

    def belegen(self, name="", pid=None):
        u"""``(True, "")`` bei Erfolg, sonst ``(False, Grund)``.

        Angelegt wird mit ``O_EXCL``: Zwei Anfragen im selben Augenblick koennen
        nicht beide gewinnen. Existiert die Datei, entscheidet :meth:`zustand`,
        ob sie noch gilt.
        """
        alt = self.zustand()
        if alt:
            return False, self._grund(alt)
        # Eine vergessene Datei aus dem Weg raeumen (zustand() hat sie geprueft).
        try:
            self.pfad.unlink()
        except OSError:
            pass
        eintrag = {"name": name, "seit": time.time(), "lauf_pid": pid,
                   "server_pid": os.getpid()}
        try:
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            kennung = os.open(str(self.pfad),
                              os.O_CREAT | os.O_EXCL | os.O_WRONLY)
            with os.fdopen(kennung, "w", encoding="utf-8") as datei:
                json.dump(eintrag, datei, ensure_ascii=False)
        except FileExistsError:
            return False, self._grund(self.zustand() or {})
        except OSError as fehler:
            # Keine Sperre schreibbar: Dann NICHT starten. Ein Lauf ohne Sperre
            # ist genau die Lage, die diese Klasse verhindern soll.
            log.exception("Laufsperre %s nicht schreibbar", self.pfad)
            return False, "Sperre nicht schreibbar: %s" % fehler
        self.gehalten = True
        return True, ""

    def pid_merken(self, pid):
        u"""Die PID des Testprozesses nachtragen (fuer den Abbruch von aussen)."""
        if not self.gehalten:
            return
        try:
            daten = json.loads(self.pfad.read_text(encoding="utf-8"))
            daten["lauf_pid"] = pid
            self.pfad.write_text(json.dumps(daten, ensure_ascii=False),
                                 encoding="utf-8")
        except (OSError, ValueError):
            log.warning("Laufsperre %s: PID %s nicht nachgetragen", self.pfad, pid)

    def freigeben(self):
        if not self.gehalten:
            return
        self.gehalten = False
        try:
            self.pfad.unlink()
        except OSError:
            # stumm gewollt: Schon weg ist der gewuenschte Zustand.
            pass

    @staticmethod
    def _grund(eintrag):
        seit = eintrag.get("seit")
        wie_lange = ""
        if seit:
            wie_lange = " (seit %d s)" % int(time.time() - float(seit))
        return ("Es läuft schon ein Testlauf%s: %s. Zwei Läufe bauen dieselbe "
                "Testdatenbank zweimal auf." % (wie_lange,
                                                eintrag.get("name") or "unbenannt"))

    # ---------------------------------------------------------------- Abbruch

    def abbrechen(self):
        u"""Den laufenden Test beenden und die Sperre loesen.

        Fuer den Knopf „Abbrechen": Ohne ihn haelt ein haengender Lauf die Sperre
        bis zur Frist, und niemand kann etwas tun.
        """
        eintrag = self.zustand()
        if not eintrag:
            return False, "Es läuft kein Testlauf."
        pid = eintrag.get("lauf_pid")
        from .testtoeter import Toeter
        if pid:
            Toeter.baum(int(pid))
        try:
            self.pfad.unlink()
        except OSError:
            pass
        self.gehalten = False
        log.warning("Testlauf %s auf Wunsch abgebrochen (PID %s)",
                    eintrag.get("name") or "?", pid)
        return True, "Testlauf abgebrochen."
