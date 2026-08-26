# -*- coding: utf-8 -*-
u"""Toeter - einen Testlauf samt seiner Kinder beenden.

``prozess.kill()`` beendet GENAU den einen Prozess. Ein Testlauf startet aber
selbst welche: ``ProcessPoolExecutor``-Arbeiter, Hilfsprogramme, ein zweiter
Interpreter. Die bleiben stehen — und auf Windows sterben Pool-Arbeiter NICHT
mit ihrem Elternprozess, wenn der hart beendet wird. In einem anderen Projekt
sind so 90 verwaiste Prozesse und rund 10 GB Arbeitsspeicher zusammengekommen.

Deshalb wird der BAUM beendet:

* Windows: ``taskkill /F /T /PID`` — ``/T`` nimmt die Kinder mit.
* POSIX: ``os.killpg`` auf die Prozessgruppe. Dafuer startet
  :class:`~.teststrom.Teststrom` den Lauf mit ``start_new_session=True``; ohne
  eigene Gruppe traefe ein Gruppen-Signal den Server selbst.

Kein ``psutil``: djangoBase soll ohne zusaetzliche Abhaengigkeit laufen.
"""
import logging
import os
import signal
import subprocess
import sys

__all__ = ["Toeter"]

log = logging.getLogger("djangobase.tests")


class Toeter:
    """Beendet einen Prozess mit allem, was er gestartet hat."""

    #: So lange wird auf das Ende gewartet, bevor es beim Melden bleibt.
    GEDULD = 10

    @classmethod
    def prozess(cls, prozess):
        u"""Einen ``Popen`` beenden - Baum zuerst, dann der Prozess selbst."""
        if prozess is None or prozess.poll() is not None:
            return False
        cls.baum(prozess.pid)
        try:
            prozess.kill()
        except OSError:
            pass
        try:
            prozess.wait(timeout=cls.GEDULD)
        except Exception:  # noqa: BLE001
            log.warning("Testlauf-Prozess %s ist nach %d s noch da",
                        prozess.pid, cls.GEDULD)
            return False
        return True

    @classmethod
    def baum(cls, pid):
        u"""Prozess ``pid`` und seine Kinder beenden. ``True``, wenn versucht."""
        if not pid:
            return False
        if sys.platform.startswith("win"):
            return cls._windows(pid)
        return cls._posix(pid)

    @staticmethod
    def _windows(pid):
        try:
            ergebnis = subprocess.run(
                ["taskkill", "/F", "/T", "/PID", str(int(pid))],
                capture_output=True, text=True, timeout=Toeter.GEDULD,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        except Exception:  # noqa: BLE001
            log.exception("taskkill für PID %s nicht ausfuehrbar", pid)
            return False
        if ergebnis.returncode not in (0, 128):
            # 128 = „Prozess nicht gefunden" — der Normalfall, wenn er schon weg
            # ist. Alles andere gehoert ins Log, sonst raetselt man spaeter,
            # warum ein Prozess ueberlebt hat.
            log.warning("taskkill /T PID %s: rc=%s %s", pid,
                        ergebnis.returncode,
                        (ergebnis.stderr or ergebnis.stdout or "").strip()[:200])
        return True

    @staticmethod
    def _posix(pid):
        try:
            os.killpg(os.getpgid(int(pid)), signal.SIGKILL)
            return True
        except ProcessLookupError:
            return True                      # schon weg
        except OSError:
            # Keine eigene Gruppe (oder keine Rechte): dann nur dieser Prozess.
            try:
                os.kill(int(pid), signal.SIGKILL)
                return True
            except OSError:
                log.exception("Prozess %s nicht beendbar", pid)
                return False
