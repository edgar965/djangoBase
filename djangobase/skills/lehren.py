# -*- coding: utf-8 -*-
u"""Lehren - alle Erkenntnisse der drei Werkzeugkaesten unter einem Dach.

DREI DURCHGAENGE, ZWEI DATENFORMEN
==================================
Die Lehren stammen aus zwei getrennt entstandenen Sammlungen:

* ``lehren_review``    - 20 Lehren aus dem 3DTools-Durchgang (August 2026),
                         als ``Lehre``-Objekte mit ``regel``/``warum``/``beleg``
                         und einem ``bereich`` (Struktur, Django, Performance …).
* ``lehren_kriterien`` - 43 Lehren aus dem shortlongx-Durchgang, als Tupel
                         ``(slug, gruppe, titel, tun, fall)``.

Beide sagen dasselbe in anderer Form: eine Regel, ihre Begruendung und der Fall,
der sie ausgeloest hat. Hier werden sie auf EINE Form gebracht - sonst muesste
jede Seite und jeder Test beide Formen kennen, und beim naechsten Zusammenlegen
waere es die dritte.

Die Quelldateien bleiben getrennt bestehen: Sie sind gewachsene Texte mit
Belegen, und sie zusammenzukopieren wuerde die Herkunft loeschen - gerade die
macht eine Lehre ueberpruefbar.
"""
from .lehren_kriterien import LEHREN as _LEHREN_KRITERIEN
from .lehren_review import BEREICHE as _BEREICHE_REVIEW
from .lehren_review import LEHREN as _LEHREN_REVIEW
from .lehren_review import Lehre, Lehrenstand

__all__ = ["Lehre", "Lehrenstand", "LEHREN", "BEREICHE", "gruppen",
           "HERKUNFT", "als_zeilen"]

#: Woher eine Lehre kommt - steht an jeder Zeile, damit man den Durchgang
#: nachschlagen kann, der sie hervorgebracht hat.
HERKUNFT = {"review": "3DTools-Durchgang", "kriterien": "shortlongx-Durchgang"}


def _aus_review():
    for l in _LEHREN_REVIEW:
        # Dictionary gewollt: geht unveraendert in die Vorlage (Skills-Seite).
        yield {"slug": l.slug, "gruppe": l.bereich, "titel": l.titel,
               "tun": l.regel, "warum": l.warum, "fall": l.beleg,
               "herkunft": "review"}


def _aus_kriterien():
    for slug, gruppe, titel, tun, fall in _LEHREN_KRITERIEN:
        # Die Tupel-Form kennt kein eigenes ``warum`` - dort steht die
        # Begruendung im Regeltext selbst. Nicht kuenstlich aufteilen.
        yield {"slug": slug, "gruppe": gruppe, "titel": titel, "tun": tun,
               "warum": "", "fall": fall, "herkunft": "kriterien"}


#: Alle Lehren in einer Form. Die Kriterien-Lehren zuerst: Sie haengen an den
#: siebzehn Auftrags-Kriterien und sind damit die Arbeitsliste; die
#: Review-Lehren sind das breitere Hintergrundwissen.
LEHREN = list(_aus_kriterien()) + list(_aus_review())

#: Alle vorkommenden Gruppen, Kriterien-Gruppen zuerst.
BEREICHE = ([g for g in dict.fromkeys(l["gruppe"] for l in LEHREN)
             if g not in _BEREICHE_REVIEW] + list(_BEREICHE_REVIEW))


def gruppen():
    """[(Gruppenname, [Lehre-Dict, …])] in der Reihenfolge von LEHREN.

    Gleiche Signatur wie die Fassung aus ``lehren_kriterien`` - die Seite und
    die Tests rufen sie unveraendert weiter auf."""
    aus, index = [], {}
    for l in LEHREN:
        if l["gruppe"] not in index:
            index[l["gruppe"]] = []
            aus.append((l["gruppe"], index[l["gruppe"]]))
        index[l["gruppe"]].append(l)
    return aus


def als_zeilen():
    """Alle Lehren als Tabelle - fuer den Bericht und die Ausgabe im Klartext."""
    return [{"gruppe": l["gruppe"], "titel": l["titel"], "tun": l["tun"],
             "fall": (l["fall"] or l["warum"])[:400],
             "herkunft": HERKUNFT.get(l["herkunft"], l["herkunft"])}
            for l in LEHREN]
