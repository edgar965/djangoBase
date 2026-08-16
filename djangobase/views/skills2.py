# -*- coding: utf-8 -*-
u"""Hilfe -> Skills2: Pruefwerkzeuge und Lehren aus dem shortlongx-Review.

Die Seite hat drei Teile:

* WERKZEUGE - die Standard-Tabelle von djangoBase (sortierbar, Spaltenbreiten
  ziehbar) mit einer Auswahlspalte. Einzeln oder als Stapel ausfuehrbar.
* AUSGABE - ein Textfeld, in das jeder Lauf seinen Bericht schreibt, je Werkzeug
  mit Ueberschrift. Gedacht zum Kopieren in eine Claude-Sitzung: Der Bericht
  nennt Datei und Zeile jeder Fundstelle, damit direkt daran gearbeitet werden
  kann.
* LEHREN - eine Arbeitsliste zum Abhaken, jede mit dem Fall dahinter. Die Haken
  liegen im Browser (localStorage), nicht auf dem Server: Sie sind eine
  persoenliche Merkliste, kein Projektzustand.

Der Lauf laeuft synchron - die Werkzeuge brauchen Sekunden, nicht Minuten. Fuer
laengeres waere die Jobs-Seite der richtige Ort.
"""
import time

from django.http import JsonResponse
from django.shortcuts import render
from django.views import View

from ..mixins import ZugriffMixin
from ..skills2 import (KRITERIEN, OHNE_WERKZEUG, gruppen, werkzeug_finden,
                       werkzeuge)


class Skills2View(ZugriffMixin, View):
    """Uebersicht; ``?werkzeug=<slug>`` faehrt eines und liefert JSON."""

    def get(self, request):
        slug = (request.GET.get("werkzeug") or "").strip()
        if slug:
            return self._laufen(slug)
        liste = []
        for w in werkzeuge():
            eintrag = w.als_dict()
            eintrag["kriterium_text"] = KRITERIEN.get(eintrag["kriterium"], "")
            liste.append(eintrag)
        return render(request, "djangobase/hilfe/skills2.html", {
            "aktiv": "skills2",
            "werkzeuge": liste,
            "tabelle": self._tabelle(liste),
            "gruppen": gruppen(),
            "ohne_werkzeug": [
                {"nr": nr, "titel": titel, "text": text}
                for nr, titel, text in OHNE_WERKZEUG],
        })

    # ------------------------------------------------------------- Darstellung
    @staticmethod
    def _tabelle(liste):
        """Die Werkzeuge in der Struktur von ``djangobase/_tabelle.html``.

        Die Auswahlspalte sortiert NICHT (``sortAus``): Eine Tabelle, die nach
        Häkchen umspringt, verliert genau die Zeile, die man gerade anklicken
        wollte."""
        spalten = [
            {"label": '<input type="checkbox" id="sk2-alle" title="alle auswählen">',
             "key": "_wahl", "sortAus": True},
            {"label": "Nr.", "key": "nr", "num": True,
             "titel": "Nummer des Auftrags-Kriteriums"},
            {"label": "Werkzeug", "key": "titel"},
            {"label": "Wonach es sucht — und der Fall dahinter", "key": "zweck"},
            {"label": "Laufzeit", "key": "dauer"},
            {"label": "", "key": "_aktion", "sortAus": True},
        ]
        zeilen = []
        for w in liste:
            wahl = ('<input type="checkbox" class="sk2-wahl" value="%s">' % w["slug"])
            beschreibung = (
                '%s<div class="sk2-fall"><b>Fall:</b> %s</div>'
                '<div class="sk2-fall"><b>Abhilfe:</b> %s</div>'
                % (w["zweck"], w["befund"], w["abhilfe"]))
            knopf = ('<button type="button" class="sk2-btn" data-werkzeug="%s">'
                     'Prüfen</button>' % w["slug"])
            zeilen.append({"zellen": [
                {"html": wahl, "klasse": "sk2-zelle-wahl"},
                {"html": str(w["kriterium"]), "sort": w["kriterium"], "klasse": "num",
                 "titel": w["kriterium_text"]},
                {"html": '<span class="sk2-name">%s</span>'
                         '<div class="sk2-krit">%s</div>'
                         % (w["titel"], w["kriterium_text"]),
                 "sort": w["titel"]},
                {"html": beschreibung},
                {"html": w["dauer"], "klasse": "sk2-dauer"},
                {"html": knopf},
            ]})
        # Dictionary gewollt: das ist die Eingabestruktur von _tabelle.html.
        return {"key": "skills2", "spalten": spalten, "zeilen": zeilen,
                "leer": "keine Werkzeuge registriert", "klasse": "sk2-tabelle"}

    # -------------------------------------------------------------------- Lauf
    @staticmethod
    def _laufen(slug):
        werkzeug = werkzeug_finden(slug)
        if werkzeug is None:
            return JsonResponse({"ok": False, "fehler": "Unbekanntes Werkzeug: %s" % slug},
                                status=404)
        t0 = time.time()
        try:
            ergebnis = werkzeug.laufen()
        except Exception as e:                                  # noqa: BLE001
            # Ein Werkzeug, das an einer kaputten Datei scheitert, darf nicht die
            # Seite mitnehmen - der Grund gehoert sichtbar in die Antwort.
            return JsonResponse({"ok": False, "slug": slug, "titel": werkzeug.titel,
                                 "fehler": "%s: %s" % (type(e).__name__, e)},
                                status=500)
        antwort = {"ok": True, "slug": slug, "titel": werkzeug.titel,
                   "kriterium": werkzeug.kriterium,
                   "abhilfe": werkzeug.abhilfe,
                   "dauer": round(time.time() - t0, 2)}
        antwort.update(ergebnis.als_dict())
        # Dictionary gewollt: geht unveraendert als JSON an die Seite.
        return JsonResponse(antwort)
