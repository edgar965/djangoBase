"""LogClassifier - Single source of truth fuers Klassifizieren von Log-Zeilen.

Severity + Exception-Erkennung + kontextsensitive Traceback-Continuation.
Wird von views/logs.py genutzt, um Log-Zeilen einzufaerben (CSS-Klasse
``lg-{severity}``) und die Exceptions-Sicht zu fuellen.

Gegenueber naiven Substring-Checks (``"[ERROR]" in line``):
  - erkennt benannte Python-Exceptions auch OHNE ``[ERROR]``-Prefix
    (``ValueError: ...``, ``KeyError: ...``),
  - erkennt Custom-Exceptions per Suffix-Regex (``GarmentFitError:``,
    ``RetargetingException:``) ohne sie hardcoden zu muessen,
  - erkennt Traceback-Frames (``  File "...", line 42, in foo``) selbst
    wenn der Traceback-Header ausserhalb des Tail-Fensters liegt,
  - haelt in ``iter_exceptions`` State, damit JSON-Indents oder Tabellen-
    Output NICHT faelschlich als Traceback-Continuation gelten.

Severity-Level (CSS-Klasse: lg-{severity}):
  - critical : [CRITICAL] level
  - err      : [ERROR] level, named/custom Exception class with colon
  - trace    : Traceback header + continuation frames (kontextsensitiv!)
  - warn     : [WARNING] level
  - info     : default
"""
from __future__ import annotations

import re
from typing import Iterable, Iterator, Literal


Severity = Literal['critical', 'err', 'trace', 'warn', 'info']


_TS_PREFIX = re.compile(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\s')


class LogClassifier:
    """Stateless einzelne-Zeile-Klassifizierung + stateful Traceback-Tracker."""

    @staticmethod
    def _content_after_ts(line: str) -> str:
        """Liefert die Zeile ohne den (optionalen) Timestamp-Praefix, den ein
        Stitch-Schritt davorklebt. Damit kann die Continuation-Erkennung in
        iter_exceptions auch gestitchte Lines korrekt als indented erkennen."""
        m = _TS_PREFIX.match(line)
        return line[m.end():] if m else line

    # Eingebaute Python-Exception-Klassen mit Colon. Erweitert um Custom-
    # Exception-Suffix-Regex weiter unten, damit `RetargetingError:` etc.
    # auch matchen.
    _EXC_CLASS_RE = re.compile(
        r'\b('
        r'AssertionError|AttributeError|TypeError|ValueError|KeyError|'
        r'RuntimeError|ConnectionError|ImportError|ModuleNotFoundError|'
        r'OSError|IOError|FileNotFoundError|PermissionError|'
        r'NotImplementedError|IndexError|StopIteration|ZeroDivisionError|'
        r'UnicodeDecodeError|UnicodeEncodeError|TimeoutError|MemoryError|'
        r'RecursionError|CancelledError|SystemExit|KeyboardInterrupt|'
        r'BaseException|Exception'
        r')(:|\b\s+in\s+|\Z)'
    )

    # Jede Klasse die auf "Error" oder "Exception" endet, gefolgt von ":"
    # (echter Exception-Render). Faengt Custom-Exceptions wie
    # `GarmentFitError:`, `RetargetingException:` ohne sie hardcoden zu muessen.
    _CUSTOM_EXC_RE = re.compile(r'\b[A-Z][A-Za-z0-9_]*(?:Error|Exception):')

    # Inhaltliche Fehler-Signale die auch bei WARNING-Level als Exception
    # gelten (z.B. "extraction failed: No module named 'cv2'" wurde als
    # .warning gelogt, ist aber inhaltlich ein Fehler).
    _ERROR_SIGNALS = (
        "No module named ",
        " failed:", " failed.", "Failed:",
        "raise ",
    )

    _TRACEBACK_HEADER = 'Traceback (most recent call last):'
    _TRACEBACK_AUX = ('During handling', 'The above exception')

    # Sehr spezifisches Python-Traceback-Frame-Pattern:
    #   `  File "path", line 42, in funcname`
    # Matcht auch wenn ein Stitch-Schritt einen Timestamp prefixt hat:
    #   `2026-05-30 13:38:07   File "path", line 42, in funcname`
    # JSON-Indents oder Table-Output haben diese exakte Struktur nicht.
    # Eine einzelne solche Zeile reicht aus um sie als Exception zu erkennen
    # auch wenn der Traceback-Header ausserhalb des Tail-Fensters liegt.
    _TRACEBACK_FRAME_RE = re.compile(r'\bFile "[^"]+", line \d+, in ')

    @classmethod
    def severity(cls, line: str) -> Severity:
        """Klassifiziert eine einzelne Zeile für die Faerbung in der UI."""
        if '[CRITICAL]' in line or ' CRITICAL ' in line:
            return 'critical'
        if '[ERROR]' in line or ' ERROR ' in line:
            return 'err'
        if cls._TRACEBACK_HEADER in line:
            return 'trace'
        if cls._TRACEBACK_FRAME_RE.search(line):
            return 'trace'
        # DER AUSDRUECKLICHE STUFENMARKER GEWINNT gegen die Namensheuristik
        # (Befund 13.08.2026, nachgemessen). Vorher stand die Exception-Erkennung
        # davor, und diese echten Zeilen wurden rot als Fehler eingeordnet:
        #   [WARNING] core: Caught ValueError: invalid input, retrying   -> err
        #   [INFO]    core: Handling KeyError: missing_key gracefully    -> err
        # Sie landeten damit auch im Ausnahmen-Reiter. Wer eine Stufe
        # ausdruecklich hinschreibt, meint sie: Eine WARNUNG, die den Namen einer
        # Ausnahme ERWAEHNT, ist keine Ausnahme. Ein wirklich protokollierter
        # Fehler kommt ueber logger.exception/error und traegt [ERROR] — das ist
        # oben schon abgefangen.
        if '[WARNING]' in line or ' WARNING ' in line:
            return 'warn'
        if '[INFO]' in line or '[DEBUG]' in line:
            return 'info'
        if cls._EXC_CLASS_RE.search(line) or cls._CUSTOM_EXC_RE.search(line):
            return 'err'
        return 'info'

    @classmethod
    def is_exception_line(cls, line: str) -> bool:
        """Stateless Exception-Heuristik fuer Einzelzeilen (z.B. fuer Counter).

        Fuer korrekte Traceback-Continuation-Erkennung benutze
        `iter_exceptions()` welches State haelt.
        """
        s = line.lstrip()
        if not s:
            return False
        if '[ERROR]' in line or '[CRITICAL]' in line:
            return True
        if cls._TRACEBACK_HEADER in line:
            return True
        if cls._TRACEBACK_FRAME_RE.search(line):
            return True
        # Wie in `severity`: Ein ausdruecklicher Stufenmarker gewinnt gegen die
        # Namensheuristik. Ohne das landete
        #   [WARNING] core: Caught ValueError: invalid input, retrying
        # im Ausnahmen-Reiter, obwohl der Fall abgefangen und behandelt wurde —
        # und der Reiter soll zeigen, was WIRKLICH schiefging (13.08.2026).
        if '[WARNING]' in line or '[INFO]' in line or '[DEBUG]' in line:
            return False
        if cls._EXC_CLASS_RE.search(line) or cls._CUSTOM_EXC_RE.search(line):
            return True
        if any(sig in line for sig in cls._ERROR_SIGNALS):
            return True
        return False

    @classmethod
    def iter_exceptions(cls, lines: Iterable[str]) -> Iterator[str]:
        """Yieldet nur Exception-Zeilen + ihre zugehoerigen Traceback-Frames.

        Stateful: nach einem Traceback-Header gelten indented Folgezeilen
        ('  File "...', '    code', '      ^^^') als Continuation und werden
        ebenfalls yielded — bis eine Exception-Klasse mit Colon den Traceback
        schliesst oder eine Nicht-indented Zeile kommt.

        Vorteil ggue. der naiven `startswith('    ')`-Regel: JSON-Indents oder
        Table-Outputs werden NICHT mehr als Traceback fehlinterpretiert.
        """
        in_trace = False
        for ln in lines:
            if not ln.strip():
                in_trace = False
                continue

            if cls._TRACEBACK_HEADER in ln:
                in_trace = True
                yield ln
                continue

            # Orphan Traceback-Frame (Header ausserhalb Tail-Window):
            # eindeutiges Python-Frame-Pattern -> Trace-Context oeffnen
            # auch ohne Header.
            if cls._TRACEBACK_FRAME_RE.search(ln):
                in_trace = True
                yield ln
                continue

            if in_trace:
                content = cls._content_after_ts(ln)
                # Indented = Traceback-Frame (File-Line, Source-Code-Echo,
                # Caret-Underlines, Variable-Renders der neuen Tracebacks).
                if content.startswith((' ', '\t')):
                    yield ln
                    continue
                # Auxiliary-Header "During handling..." haelt Trace offen
                if any(content.lstrip().startswith(aux) for aux in cls._TRACEBACK_AUX):
                    yield ln
                    continue
                # Sonst: Exception-Klasse mit Colon schliesst den Trace.
                if cls._EXC_CLASS_RE.search(ln) or cls._CUSTOM_EXC_RE.search(ln):
                    in_trace = False
                    yield ln
                    continue
                # Was anderes -> Trace zu Ende, Zeile evtl. trotzdem Exception.
                in_trace = False
                if cls.is_exception_line(ln):
                    yield ln
                continue

            # Nicht in Traceback: stateless Check.
            if cls.is_exception_line(ln):
                yield ln
