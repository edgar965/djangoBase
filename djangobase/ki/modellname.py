# -*- coding: utf-8 -*-
u"""Was im NAMEN eines Modells steht - Parameterzahl und was daraus folgt.

Reines Lesen von Zeichenketten, kein Netz, keine Datei. Herausgeloest aus
``modelle.py`` (30.08.2026), weil dort inzwischen drei Dinge nebeneinander
standen: der Onlinekatalog, die lokale Ollama-Installation und diese
Namensdeutung. Der Katalog RUFT sie, gehoert ihr aber nicht - ``OllamaModelle``
braucht dieselben Regeln.

WIE SICHER SIND DIE ZAHLEN? Die Parameterzahl steht im Namen nur, wenn der
Hersteller die Gewichte veroeffentlicht hat. Bei geschlossenen Modellen (Gemini,
GPT, Claude, qwen-max) gibt es sie nicht - dann ``None`` und NICHT eine
Schaetzung. Ein Modell ohne Zahl im Namen gilt hier deshalb als geschlossen;
das ist eine Faustregel, keine Garantie (``llama-4-scout`` ist offen und traegt
trotzdem keine Zahl).
"""
import re

#: Plattenbedarf je Mrd. Parameter in der ueblichen 4-Bit-Quantisierung (Q4_K_M).
#: NICHT aus der Bit-Rechnung hergeleitet, sondern an drei echten Ollama-Downloads
#: kalibriert: 27B = 17 GB (0,63), 26B = 16 GB (0,62), 9B = 6,6 GB (0,73). Kleine
#: Modelle liegen darueber, weil Einbettungstabellen und Vokabular kaum mit der
#: Modellgroesse schrumpfen - die Formel unterschaetzt sie also.
GB_JE_MRD = 0.63


class Modellname:
    u"""Liest Parameterzahl, Plattenbedarf und Sortiergroesse aus einer Kennung."""

    #: ``550b-a55b`` = 550 Mrd. Parameter gesamt, davon 55 Mrd. je Token aktiv.
    #: Fuer Tempo und Speicherbedarf zaehlt die zweite Zahl, fuer die Faehigkeiten
    #: eher die erste - deshalb werden beide gelesen.
    MOE = re.compile(r"(\d+(?:\.\d+)?)b-a(\d+(?:\.\d+)?)b")
    #: ``27b`` ja, ``qwen3.8`` nein, ``b32`` nein: Die Zahl muss auf ein ``b``
    #: enden, dem kein weiteres Wortzeichen folgt.
    EINFACH = re.compile(r"(?<![\d.])(\d+(?:\.\d+)?)b(?![a-z0-9])")

    @classmethod
    def parameter(cls, kennung):
        u"""('550B', '55B') aus einem Modellnamen - oder (None, None).

        Die zweite Zahl ist nur bei MoE-Modellen gesetzt (aktive Parameter)."""
        name = (kennung or "").lower()
        moe = cls.MOE.search(name)
        if moe:
            return "%sB" % moe.group(1), "%sB" % moe.group(2)
        einfach = cls.EINFACH.findall(name)
        if einfach:
            return "%sB" % einfach[-1], None
        return None, None

    @classmethod
    def gb(cls, param):
        u"""Geschaetzter Plattenbedarf in GB aus '27B' - oder None."""
        mrd = cls.mrd(param)
        return None if mrd is None else round(mrd * GB_JE_MRD, 1)

    #: Groessensuffix -> Faktor in MILLIARDEN. Ollama liefert `parameter_size`
    #: als Text mit Einheit ("20.9B", "137M"); ohne diese Tabelle bleibt von
    #: "137M" nach `rstrip("Bb")` der Text "137M" stehen und float() wirft.
    EINHEITEN = {"t": 1000.0, "b": 1.0, "m": 0.001, "k": 0.000001}

    @staticmethod
    def mrd(param):
        u"""'550B' -> 550.0, '20.9B' -> 20.9, '137M' -> 0.137; sonst None.

        BEFUND 01.09.2026 - die Einheit fehlte, und zwar an zwei Stellen:
        Hier warf ``float("137M")`` still ein ValueError (Ergebnis None), und
        in der Vorlage stand der ROHTEXT als ``data-sort``. Die Sortierung
        las daraus die blanke Ziffer und stellte ein 137-Millionen-Modell
        zwischen zwei mit ueber hundert MILLIARDEN Parametern.

        Rueckgabe immer in Milliarden, damit ein einziger Massstab sortiert."""
        if not param:
            return None
        text = str(param).strip()
        faktor = 1.0
        if text and text[-1].lower() in Modellname.EINHEITEN:
            faktor = Modellname.EINHEITEN[text[-1].lower()]
            text = text[:-1]
        try:
            # Runden, weil 0.137 * 1.0 in Fliesskomma als 0.13700000000000001
            # herauskommen kann - das landete sonst so im data-sort-Attribut.
            return round(float(text) * faktor, 9)
        except ValueError:
            return None
