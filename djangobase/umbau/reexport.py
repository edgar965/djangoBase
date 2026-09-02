# -*- coding: utf-8 -*-
u"""``# noqa: F401`` — die Absicht, die pyright nicht liest.

Ein Sammelmodul holt Namen herein, um sie weiterzureichen::

    from .strategien_basis import (AMPEL_CONTEXT, AMPEL_ORDER,   # noqa: F401
                                   AMPEL_SIGNS, ATR_PERIOD)

Für flake8 ist damit alles gesagt: ``F401`` ist „imported but unused", und der
Marker erklärt es zur Absicht. pyright kennt diese Sprache nicht und meldet
jeden Namen einzeln als ``reportUnusedImport``.

Gemessen an shortlongx (02.09.2026): von 165 verbliebenen ``reportUnusedImport``
standen **147 an einer so markierten Zeile** — in 39 Dateien, angeführt von
``brain/strategies.py`` (21), ``brain/news_fetcher.py`` (18) und
``brain/dax_signale.py`` (16). Die Absicht war also längst notiert; sie stand
nur in der falschen Sprache. Die übrigen 18 sind echte Aufräumkandidaten.

WARUM NICHT ``__all__`` IN DIE 39 DATEIEN SCHREIBEN
===================================================
Das wäre der andere Weg und ist nicht falsch — aber er ändert Verhalten: Ein
``__all__`` legt fest, was ``from modul import *`` liefert. Wer dabei einen
öffentlichen Namen vergisst, bricht die Aufrufer, und der Fehler zeigt sich
erst zur Laufzeit. Einen vorhandenen Marker zu lesen ändert nichts am Programm.

Django-frei.
"""
import ast
import re

__all__ = ["Reexporte"]


class Reexporte:
    u"""Findet Import-Anweisungen, die als Weitergabe markiert sind."""

    #: ``# noqa`` mit optionaler Code-Liste (``F401``, ``F401,E501``).
    MARKER = re.compile(
        r"#\s*noqa(?:\s*:\s*(?P<codes>[A-Z][A-Z0-9]*(?:\s*,\s*[A-Z][A-Z0-9]*)*))?",
        re.I)

    @classmethod
    def ist_marker(cls, zeile):
        u"""Sagt diese Zeile „unbenutzt ist Absicht"?

        ``# noqa: F401`` ja. Nacktes ``# noqa`` auch — es unterdrückt jede
        Regel, F401 eingeschlossen. ``# noqa: E501`` dagegen spricht über die
        Zeilenlänge und sagt über Importe nichts; das darf nicht zählen, sonst
        verschwindet ein echter Befund hinter einer langen Zeile."""
        treffer = cls.MARKER.search(zeile or "")
        if not treffer:
            return False
        codes = treffer.group("codes")
        return codes is None or "F401" in codes.upper().replace(" ", "")

    @classmethod
    def zeilen(cls, baum, quellzeilen):
        u"""``{Zeilennummern}`` aller so markierten Import-Anweisungen.

        Der Marker steht an EINER Zeile der Anweisung, meist der ersten; pyright
        meldet aber jeden Namen einzeln, auch in den Folgezeilen einer
        umbrochenen Klammer. Deshalb zählt der ganze Bereich::

            from .basis import (A, B,      # noqa: F401   <- Marker hier
                                C, D)      #              <- Meldung auch hier
        """
        raus = set()
        for knoten in ast.walk(baum):
            if not isinstance(knoten, (ast.Import, ast.ImportFrom)):
                continue
            anfang = knoten.lineno
            ende = getattr(knoten, "end_lineno", None) or anfang
            bereich = range(anfang, ende + 1)
            if any(cls.ist_marker(quellzeilen[n - 1])
                   for n in bereich if 0 < n <= len(quellzeilen)):
                raus.update(bereich)
        return raus
