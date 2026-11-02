"""Google als Anbieter für ``djangobase.uebersetzung`` — der kostenlose Endpunkt über
``deep_translator.GoogleTranslator`` ohne API-Key (wie auf schwanenburg.de).

Aus ``uebersetzung.py`` herausgelöst (31.10.2026), als dort Azure als zweiter Anbieter dazukam; das
Verhalten ist unverändert.
"""

import re

MAX_LAENGE = 4500  # Limit des Google-Endpoints (~5000) mit Puffer
TAG_RE = re.compile(r"(<[^>]+>)")


class GoogleUebersetzer:
    """Deutsch → Zielsprache; ein ``GoogleTranslator`` je Sprachpaar (CleanOrga-Muster)."""

    _translators = {}

    @classmethod
    def _translator(cls, quelle, ziel):
        if (quelle, ziel) not in cls._translators:
            from deep_translator import GoogleTranslator

            cls._translators[(quelle, ziel)] = GoogleTranslator(source=quelle, target=ziel)
        return cls._translators[(quelle, ziel)]

    @classmethod
    def _klartext(cls, text, quelle, ziel):
        if not text.strip():
            return text
        if len(text) <= MAX_LAENGE:
            return cls._translator(quelle, ziel).translate(text) or text
        # Lange Texte an Satz-/Absatzgrenzen stückeln
        teile, aktuell = [], ""
        for stueck in re.split(r"(?<=[.!?\n])\s+", text):
            if len(aktuell) + len(stueck) > MAX_LAENGE and aktuell:
                teile.append(aktuell)
                aktuell = stueck
            else:
                aktuell = f"{aktuell} {stueck}".strip()
        if aktuell:
            teile.append(aktuell)
        return " ".join(cls._translator(quelle, ziel).translate(t) or t for t in teile)

    @classmethod
    def uebersetze(cls, text, quelle, ziel, pause):
        """HTML wird an den Tags zerlegt und nur der Text dazwischen übersetzt (Markup bleibt unangetastet) –
        gleiche Idee wie die Shortcode-Zerlegung des Schwanenburg-Plugins. ``pause`` schont den Endpunkt
        (``uebersetzung.PAUSE``, im Test ``Pause.sofort()``)."""
        if "<" not in text:
            return cls._klartext(text, quelle, ziel)
        out = []
        for teil in TAG_RE.split(text):
            if teil.startswith("<") or not teil.strip():
                out.append(teil)
            else:
                out.append(cls._klartext(teil, quelle, ziel))
                pause.warten(0.15)  # Endpoint schonen
        return "".join(out)
