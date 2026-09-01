# -*- coding: utf-8 -*-
u"""Laeuft dieser Prozess noch? — die Frage vor jedem rekursiven Loeschen.

WARUM ES DIESE KLASSE GIBT (31.08.2026)
=======================================
``Ablageumleitung`` legt je Prozess einen Wegwerfordner an, dessen Name
die Prozessnummer traegt (``p60596``). Beim regulaeren Ende raeumt
``atexit`` ihn weg — bei einem HARTEN Abbruch nicht, und genau der
Abbruch ist der Fall, der etwas stehenlaesst. Als Auffangnetz galt bis
hierher eine Frist: Was seit 24 Stunden niemand angefasst hat, darf weg.

Das ist zu langsam. Am 31.08.2026 lagen zwoelf solcher Ordner im Projekt
— Reste dreier abgebrochener Testlaeufe desselben Tages. Einer davon
enthielt eine JS-Attrappe, die absichtlich auf ein fehlendes Modul zeigt,
und ``GrundtestEsModule`` las sie als echten Projektcode: vier
JS-Importe ins Leere, jeder Gesamtlauf rot.

Der Ordnername sagt die ganze Zeit, wessen Rest er ist. Man muss nur
fragen.

WARUM NICHT ``os.kill(pid, 0)``
===============================
Auf POSIX ist das die uebliche Antwort — Signal 0 wird nicht zugestellt,
nur geprueft. **Unter Windows ruft ``os.kill`` ``TerminateProcess`` auf
und BEENDET den Prozess**, auch mit Signal 0. Aus der Frage „laeufst du
noch?" wuerde ein Todesurteil, und zwar fuer einen fremden Prozess.
Deshalb hier ``OpenProcess`` + ``GetExitCodeProcess`` ueber ctypes.

Im Zweifel lautet die Antwort JA. Ein Ordner, der einmal zu lange liegt,
kostet nichts; ein geloeschter Ordner eines laufenden Prozesses kostet
dessen Lauf (siehe ``~/.claude/rules/rekursiv-loeschen.md``: 972 von 997
Dateien geloescht, waehrend das Programm daraus lief).
"""
import os
import sys

__all__ = ['Prozessfrage']

#: Windows: Rechte, die zum Fragen genuegen.
_PROCESS_QUERY_LIMITED_INFORMATION = 0x1000

#: Windows: Rueckgabe von ``GetExitCodeProcess``, solange der Prozess laeuft.
_STILL_ACTIVE = 259


class Prozessfrage:
    u"""Auskunft ueber fremde Prozesse — ohne sie anzufassen."""

    @staticmethod
    def lebt(pid):
        u"""Laeuft der Prozess mit dieser Nummer noch?

        Gibt im Zweifel ``True`` zurueck: Wer nicht sicher weiss, dass
        ein Prozess tot ist, raeumt seine Dateien nicht weg.
        """
        try:
            pid = int(pid)
        except (TypeError, ValueError):
            return True
        if pid <= 0:
            return True
        if sys.platform == 'win32':
            return Prozessfrage._lebt_windows(pid)
        return Prozessfrage._lebt_posix(pid)

    @staticmethod
    def _lebt_posix(pid):
        try:
            os.kill(pid, 0)
        except ProcessLookupError:
            return False
        except PermissionError:
            # Es gibt ihn, er gehoert nur jemand anderem.
            return True
        except OSError:
            return True
        return True

    @staticmethod
    def _lebt_windows(pid):
        u"""``OpenProcess`` + ``GetExitCodeProcess`` — nie ``os.kill``.

        EIN HANDLE ALLEIN REICHT NICHT als Beweis: Solange irgendwer ein
        Handle auf einen beendeten Prozess haelt, gelingt ``OpenProcess``
        weiter (der Eintrag lebt, der Prozess nicht). Erst der Exit-Code
        unterscheidet beides — ``STILL_ACTIVE`` heisst „laeuft".
        """
        import ctypes

        try:
            kernel32 = ctypes.WinDLL('kernel32', use_last_error=True)
        except (OSError, AttributeError):
            return True
        griff = kernel32.OpenProcess(
            _PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
        if not griff:
            # Kein Zugriff kann auch „Rechte fehlen" heissen. Der
            # Unterschied: ERROR_INVALID_PARAMETER (87) sagt „diese
            # Nummer gibt es nicht".
            return ctypes.get_last_error() != 87
        try:
            code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(griff, ctypes.byref(code)):
                return True
            return code.value == _STILL_ACTIVE
        finally:
            kernel32.CloseHandle(griff)

    @staticmethod
    def nummer_aus(name, praefix='p'):
        u"""Die Prozessnummer aus einem Ordnernamen wie ``p60596``.

        ``None``, wenn der Name keine traegt — dann weiss man nichts
        ueber ihn, und der Aufrufer laesst ihn in Ruhe.
        """
        if not name.startswith(praefix):
            return None
        rest = name[len(praefix):]
        return int(rest) if rest.isdigit() else None
