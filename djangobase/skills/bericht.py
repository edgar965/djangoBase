# -*- coding: utf-8 -*-
u"""Bericht - der Klartext-Stapelbericht der Skills1-Seite.

Das ist das skills-Element, das die reine skills2-Welt nicht hat: Mehrere
Werkzeuge laufen server-seitig als Stapel, und JEDER haengt seinen Bericht als
Klartext unten an - je Werkzeug mit Trennlinie und Ueberschrift. Von dort laesst
sich alles in eine Sitzung kopieren und Datei-fuer-Zeile abarbeiten.

Die skills2-Werkzeuge liefern eine Tabelle (Spalten + Zeilen-Dicts); dieselbe
Struktur bekommen die skills-Werkzeuge ueber den Adapter. Der Bericht richtet die
Spalten zu festen Breiten aus, damit die Textbox lesbar bleibt.
"""

__all__ = ["Bericht"]


class Bericht:
    """Sammelt die Ergebnisse mehrerer Werkzeuge als ausgerichteten Klartext."""

    LINIE = "=" * 78
    #: Hoechstens so viele Zeilen je Werkzeug in den Text - die Kappung wird
    #: ausgewiesen, das ganze Ergebnis steht in der Tabelle des Werkzeugs.
    MAX_ZEILEN = 300
    #: Sehr breite Zellen kuerzen, sonst sprengt eine Pfadspalte die Box.
    MAX_SPALTE = 60

    def __init__(self, bisher=""):
        self.teile = [bisher.rstrip()] if bisher and bisher.strip() else []

    def anhaengen(self, werkzeug, ergebnis, dauer_s=0.0, zeitstempel=""):
        titel = getattr(werkzeug, "titel", "") or getattr(werkzeug, "slug", "?")
        fehler = (ergebnis.hinweis or "").startswith("FEHLER")
        stand = ("FEHLER" if fehler
                 else "%d Treffer" % len(ergebnis.zeilen) if ergebnis.zeilen
                 else "nichts gefunden")
        kopf = [
            self.LINIE,
            "# %s [%s]%s" % (titel, werkzeug.slug,
                             "  " + zeitstempel if zeitstempel else ""),
            "# %s · %.1f s" % (stand, dauer_s),
            self.LINIE,
        ]
        if ergebnis.zusammenfassung:
            kopf.append(ergebnis.zusammenfassung)
        self.teile.append("\n".join(kopf) + "\n" + self._tabelle(ergebnis))
        return self

    def text(self):
        return "\n\n".join(self.teile).strip()

    # ------------------------------------------------------------------ intern

    def _tabelle(self, ergebnis):
        if (ergebnis.hinweis or "").startswith("FEHLER"):
            return ergebnis.hinweis
        if not ergebnis.zeilen:
            leer = "Nichts gefunden."
            return leer + ("\n" + ergebnis.hinweis if ergebnis.hinweis else "")
        spalten = ergebnis.spalten or list(ergebnis.zeilen[0].keys())
        zeilen = ergebnis.zeilen[:self.MAX_ZEILEN]
        breite = {
            s: min(self.MAX_SPALTE,
                   max(len(str(s)),
                       max((len(self._zelle(z.get(s, ""))) for z in zeilen), default=0)))
            for s in spalten
        }

        def zeile(werte):
            return "  ".join(self._zelle(werte.get(s, "")).ljust(breite[s])
                             for s in spalten)

        aus = [zeile({s: s for s in spalten}),
               "  ".join("-" * breite[s] for s in spalten)]
        aus.extend(zeile(z) for z in zeilen)
        if len(ergebnis.zeilen) > self.MAX_ZEILEN:
            aus.append("… %d weitere — im Werkzeug ansehen"
                       % (len(ergebnis.zeilen) - self.MAX_ZEILEN))
        if ergebnis.hinweis:
            aus.extend(["", ergebnis.hinweis])
        return "\n".join(aus)

    def _zelle(self, wert):
        return str(wert).replace("\n", " ")[:self.MAX_SPALTE]
