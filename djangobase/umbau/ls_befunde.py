# -*- coding: utf-8 -*-
u"""Die Befunde eines Laufs — gewichtet, gefiltert, gezählt, als Tabellenzeilen.

Ein ``LsErgebnis`` ist die rohe Liste. Was die Seite zeigt, hängt an der
Konfiguration (Anzeigestufe, Deckel) und an der Frage, die man stellt:
je Regel, je Datei, oder alles der Reihe nach. Das steht hier, getrennt
vom Lauf und von der Ansicht.
"""
from django.utils.html import escape

__all__ = ["LsBefunde"]

#: Reihenfolge = Gewicht. Sortierwert für die Tabelle.
GEWICHT = {"error": 0, "warning": 1, "information": 2}
BESCHRIFTUNG = {"error": u"Fehler", "warning": u"Warnung", "information": u"Hinweis"}


class LsBefunde:
    u"""Sichten auf die Befunde EINES Ergebnisses."""

    def __init__(self, ergebnis, konfig):
        self.ergebnis = ergebnis
        self.konfig = konfig

    # ── Auswahl ──────────────────────────────────────────────────────────
    def gefiltert(self):
        u"""Nur bis zur Anzeigestufe, nach Gewicht, Datei, Zeile sortiert."""
        grenze = GEWICHT.get(self.konfig.stufe, 1)
        raus = [b for b in self.ergebnis.befunde
                if GEWICHT.get(b["stufe"], 2) <= grenze]
        raus.sort(key=lambda b: (GEWICHT.get(b["stufe"], 2), b["datei"], b["zeile"]))
        return raus

    def kennzahlen(self):
        alle = self.ergebnis.befunde
        zahl = {s: sum(1 for b in alle if b["stufe"] == s) for s in GEWICHT}
        gezeigt = self.gefiltert()
        return {
            "fehler": zahl["error"], "warnungen": zahl["warning"],
            "hinweise": zahl["information"], "gesamt": len(alle),
            "gezeigt": min(len(gezeigt), self.konfig.deckel),
            "gefiltert": len(gezeigt),
            "dateien": self.ergebnis.dateien,
            "dauer_s": self.ergebnis.dauer_s,
            "dateien_mit_befund": len({b["datei"] for b in alle}),
        }

    def je_regel(self):
        u"""``[(regel, anzahl, stufe)]`` — die häufigste zuerst."""
        zaehler, stufe = {}, {}
        for b in self.ergebnis.befunde:
            zaehler[b["regel"]] = zaehler.get(b["regel"], 0) + 1
            stufe.setdefault(b["regel"], b["stufe"])
        return sorted(((r, n, stufe[r]) for r, n in zaehler.items()),
                      key=lambda t: (-t[1], t[0]))

    def je_datei(self, hoechstens=25):
        zaehler = {}
        for b in self.ergebnis.befunde:
            zaehler[b["datei"]] = zaehler.get(b["datei"], 0) + 1
        return sorted(zaehler.items(), key=lambda t: (-t[1], t[0]))[:hoechstens]

    # ── Tabelle ──────────────────────────────────────────────────────────
    SPALTEN = (
        (u"Stufe", "stufe", False),
        (u"Datei", "datei", False),
        (u"Zeile", "zeile", True),
        (u"Regel", "regel", False),
        (u"Meldung", "text", False),
        (u"", "aktion", False),
    )

    def tabelle(self):
        u"""Die Struktur für ``djangobase/_tabelle.html`` — höchstens ``deckel`` Zeilen."""
        zeilen = []
        for b in self.gefiltert()[:self.konfig.deckel]:
            zeilen.append({
                "klasse": "ls-" + b["stufe"],
                # Datei, Zeile und Spalte — die Referenzen-Tafel liest sie ab.
                "id": u"%s|%d|%d" % (b["datei"], b["zeile"], b["spalte"]),
                "zellen": [
                    {"html": BESCHRIFTUNG.get(b["stufe"], b["stufe"]),
                     "klasse": "ls-stufe", "sort": GEWICHT.get(b["stufe"], 2)},
                    {"html": u'<code class="ls-datei">%s</code>' % escape(b["datei"]),
                     "klasse": "ls-datei-zelle"},
                    {"html": u"%d" % b["zeile"], "klasse": "num", "sort": b["zeile"]},
                    {"html": escape(b["regel"] or u"—"), "klasse": "ls-regel"},
                    {"html": escape(b["text"]), "klasse": "ls-text"},
                    # Referenzen und Umbenennen gibt es nur ueber die
                    # Python-Sitzung; JavaScript-Befunde (tsc) bekommen keinen Knopf.
                    {"html": ((u'<button type="button" class="ls-knopf ls-ref" '
                               u'title="Wer benutzt das? Definition? Umbenennen?">'
                               u'<i class="bi bi-diagram-2"></i></button>')
                              if b["datei"].endswith(".py") else u""),
                     "klasse": "ls-aktion"},
                ],
            })
        return {
            "key": "db-languageserver",
            "klasse": "ls-tabelle",
            "spalten": [{"label": l, "key": k, "num": n} for l, k, n in self.SPALTEN],
            "zeilen": zeilen,
            "leer": u"keine Befunde — oder noch kein Lauf",
        }
