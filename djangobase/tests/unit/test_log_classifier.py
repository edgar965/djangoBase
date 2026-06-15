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


class IterExceptionsTests(SimpleTestCase):
    def test_groups_traceback_block(self):
        lines = [
            "[INFO] starte job",
            "Traceback (most recent call last):",
            '  File "a.py", line 10, in run',
            "    do_it()",
            "ValueError: nope",
            "[INFO] naechster job",
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
