# -*- coding: utf-8 -*-
u"""Laufzeiten lesbar schreiben — EINE Regel fuer die ganze Oberflaeche.

Ansage 17.08.2026: *„wenn die ausführungszeit unter 1 s ist dann schreibe immer
ms als Zeit"*. Vorher lag die Grenze bei 10 ms; alles darueber stand als
``0,42 s`` da, was sich schlechter vergleichen laesst als ``420 ms``.

Warum ein eigenes Modul: Dieselbe Zahl wird an drei Stellen angezeigt — in den
Tabellenzellen (:mod:`.testtabelle`), in der Ergebniszeile eines Laufs
(:mod:`.testlauf`) und im Browser (``tests_ui.js``). Stuende die Regel dreimal
im Code, waeren nach der naechsten Aenderung zwei Stellen gleich und eine
anders. Das JavaScript kann diese Funktion nicht aufrufen und traegt die Regel
als Kommentar mit Verweis hierher.

Sortiert wird ueberall nach dem Rohwert (``data-sort``), nie nach dem Text —
die Anzeige darf also frei die passende Einheit waehlen.
"""

GRENZE = 1.0        # darunter Millisekunden


def dauer_text(wert, stellen=2):
    u"""Sekunden als Text: unter :data:`GRENZE` in ms, sonst mit Komma.

    >>> dauer_text(0.002), dauer_text(0.42), dauer_text(3.9)
    ('2 ms', '420 ms', '3,90 s')

    ``None`` liefert einen leeren Text — wer ein Zeichen fuer „nie gelaufen"
    braucht, setzt es selbst (die Tabelle nimmt ein graues „—").
    """
    if wert is None:
        return ""
    try:
        wert = float(wert)
    except (TypeError, ValueError):
        return ""
    # Auch die Null: „0,00 s" neben „35 ms" in derselben Spalte sah aus wie
    # zwei verschiedene Einheiten fuer dieselbe Sache (im Browser gesehen,
    # 17.08.2026). Unter einer Sekunde heisst unter einer Sekunde.
    if wert < GRENZE:
        return "%d ms" % round(wert * 1000)
    return "%s s" % ("%.*f" % (stellen, wert)).replace(".", ",")
