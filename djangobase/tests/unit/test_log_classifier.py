"""Unit-Tests fuer djangobase.log_classifier.LogClassifier.

Decken die Faelle ab, die die alten Substring-Checks NICHT erkannt haben:
benannte/Custom-Exceptions ohne [ERROR]-Prefix, Traceback-Frames ohne
Header im Fenster, und die kontextsensitive Continuation-Erkennung.
"""
from django.test import SimpleTestCase

from djangobase.log_classifier import LogClassifier as LC


class SeverityTests(SimpleTestCase):
    def test_critical(self):
        self.assertEqual(LC.severity("2026-06-15 [CRITICAL] core: boom"), "critical")

    def test_error_prefix(self):
        self.assertEqual(LC.severity("2026-06-15 [ERROR] core: kaputt"), "err")

    def test_named_exception_without_prefix(self):
        # Alte Logik (Substring [ERROR]) haette das verpasst -> 'info'/uncolored.
        self.assertEqual(LC.severity("ValueError: expected 3 got 5"), "err")

    def test_custom_exception_suffix(self):
        self.assertEqual(LC.severity("RetargetingError: bone missing"), "err")
        self.assertEqual(LC.severity("GarmentFitException: no fit"), "err")

    def test_traceback_header(self):
        self.assertEqual(LC.severity("Traceback (most recent call last):"), "trace")

    def test_traceback_frame_without_header(self):
        self.assertEqual(LC.severity('  File "x.py", line 42, in foo'), "trace")

    def test_warning(self):
        self.assertEqual(LC.severity("2026-06-15 [WARNING] core: hmm"), "warn")

    def test_plain_info(self):
        self.assertEqual(LC.severity("2026-06-15 [INFO] core: gestartet"), "info")

    def test_json_indent_is_not_trace(self):
        # JSON-Indent hat NICHT das File-line-in-Pattern -> kein trace/err.
        self.assertEqual(LC.severity('    "key": "value",'), "info")

    def test_ausdrueckliche_stufe_gewinnt_gegen_den_namen(self):
        """Ein abgefangener Fehler ist kein Fehler (Befund 13.08.2026).

        Vorher stand die Exception-Namensheuristik VOR dem Stufenmarker; diese
        echten Zeilen wurden dadurch rot und landeten im Ausnahmen-Reiter,
        obwohl der Fall behandelt wurde:

            [WARNING] core: Caught ValueError: invalid input, retrying
            [INFO]    core: Handling KeyError: missing_key gracefully

        Wer eine Stufe ausdrücklich hinschreibt, meint sie. Ein wirklich
        protokollierter Fehler kommt über logger.exception/error und trägt
        [ERROR] — das wird davor abgefangen."""
        self.assertEqual(
            LC.severity("2026-08-15 [WARNING] core: Caught ValueError: invalid input"),
            "warn")
        self.assertEqual(
            LC.severity("2026-08-15 [INFO] core: Handling KeyError: missing gracefully"),
            "info")
        # Und die Gegenprobe: OHNE Stufenmarker bleibt der Name ausschlaggebend.
        self.assertEqual(LC.severity("ValueError: invalid input"), "err")
        self.assertEqual(LC.severity("2026-08-15 [ERROR] core: ValueError: x"), "err")

    def test_abgefangener_fehler_nicht_im_ausnahmen_reiter(self):
        """Dieselbe Regel in `is_exception_line` — sonst färbt die Zeile richtig
        und erscheint trotzdem in der Ausnahmen-Ansicht."""
        self.assertFalse(LC.is_exception_line(
            "2026-08-15 [WARNING] core: Caught ValueError: invalid input"))
        self.assertTrue(LC.is_exception_line("2026-08-15 [ERROR] core: kaputt"))
        self.assertTrue(LC.is_exception_line("ValueError: invalid input"))


class IterExceptionsTests(SimpleTestCase):
    def test_groups_traceback_block(self):
        lines = [
            "[INFO] starte job",
            "Traceback (most recent call last):",
            '  File "a.py", line 10, in run',
            "    do_it()",
            "ValueError: nope",
            "[INFO] nächster job",
        ]
        got = list(LC.iter_exceptions(lines))
        self.assertEqual(got, [
            "Traceback (most recent call last):",
            '  File "a.py", line 10, in run',
            "    do_it()",
            "ValueError: nope",
        ])

    def test_json_block_not_swallowed_as_trace(self):
        # Ein indentierter JSON-Block nach einer Info-Zeile darf NICHT als
        # Traceback-Continuation gelten.
        lines = [
            "[INFO] payload:",
            '    {"a": 1,',
            '     "b": 2}',
        ]
        self.assertEqual(list(LC.iter_exceptions(lines)), [])

    def test_orphan_frame_opens_trace(self):
        # Header ausserhalb des Fensters: ein einzelner File-Frame reicht.
        lines = ['  File "a.py", line 5, in foo', "    boom()", "KeyError: 'x'"]
        self.assertEqual(list(LC.iter_exceptions(lines)), lines)
