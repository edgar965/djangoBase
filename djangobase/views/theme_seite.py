"""Einstellungen -> Theme (01.11.2026, aus StayNestor): Theme umschalten, Farben und Schriftrollen je Theme.

Die Definition steht in ``theme_stil.py``, die Prüfung in ``theme_bereinigung.py``. Die Seite rendert alle
Felder, ``theme_seite.js`` füllt sie mit den Werten des aktiven Themes, zeigt jede Änderung sofort an der
ganzen Seite (Seitenleiste und Kopfleiste sind die echten) und schickt beim Speichern die Arbeitskopie
ALLER Themes. Gespeichert wird im Store (Gruppe ``theme``, keine Datenbank).

Die Vorschau rechts ist eine Vorlage des Projekts (``DJANGOBASE["theme_vorschau"]``) mit dessen echten
Klassen und ``data-rolle="<rolle>"`` je Beispiel; ohne Angabe die allgemeine aus djangoBase.
"""

import json

from django.contrib import messages
from django.shortcuts import redirect, render
from django.views import View

from .. import store
from ..conf import conf
from ..mixins import ZugriffMixin
from ..theme_bereinigung import ThemeBereinigung
from ..theme_stil import ThemeStil

VORSCHAU = "djangobase/hilfe/_theme_vorschau.html"


class ThemeSeite(ZugriffMixin, View):
    def get(self, request):
        c = conf()
        pruefung = ThemeBereinigung(self._themes(c))
        return render(
            request,
            "djangobase/hilfe/theme.html",
            {
                "aktiv": "einstellungen_theme",
                "theme_modes": c["theme_modes"],
                "definition": ThemeStil.definition(),
                "anpassung": pruefung.bereinigen(c.get("theme_anpassung")),
                "vorgaben": pruefung.bereinigen(c.get("theme_vorgaben")),
                "vorschau": c.get("theme_vorschau") or VORSCHAU,
            },
        )

    def post(self, request):
        c = conf()
        try:
            daten = json.loads(request.POST.get("daten") or "{}")
        except ValueError:
            messages.error(request, "Nicht gespeichert: Die Seite hat keine lesbaren Werte geschickt.")
            return redirect(request.path)
        anpassung = ThemeBereinigung(self._themes(c)).bereinigen(daten)
        store.speichern_gruppe("theme", {"theme_anpassung": anpassung})
        messages.success(request, "Theme gespeichert.")
        return redirect(request.path)

    @staticmethod
    def _themes(c):
        return [m[0] if isinstance(m, (list, tuple)) else str(m) for m in c.get("theme_modes") or []]
