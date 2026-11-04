"""Das Element ``#djb-tabellen`` für ``tabellen_speicher.js`` (04.11.2026, aus StayNestor).

Trägt die Schalter aus Einstellungen -> Tabellen (``data-verschieben``, ``data-anpassen``) und mit
``DJANGOBASE["tabellen_je_benutzer"]`` die Einstellungen des angemeldeten Benutzers samt Adresse zum
Speichern. ``_shell.html`` gibt es als ``{{ djangobase.tabellen_element }}`` aus (Kontextprozessor, erst beim
Anzeigen gerechnet) — NICHT über eine eigene Tag-Bibliothek: Django kennt Tag-Bibliotheken nur aus dem Start
des Prozesses, und ``{% load djangobase_tabellen %}`` in der gemeinsamen Hülle legte am 04.11.2026 jede Seite
der Projekte lahm, deren Server vor dem Anlegen der Datei lief (shortlongx ``/depot/ib/``: TemplateSyntaxError
„not a registered tag library“). Ein fehlender Kontextwert ergibt dagegen nur nichts.

Gilt alles wie vorgegeben (verschieben aus, anpassen an, nicht je Benutzer), kommt NICHTS heraus — die
Seiten der übrigen Projekte bleiben Zeichen für Zeichen gleich.
"""

import json

from django.middleware.csrf import get_token
from django.urls import NoReverseMatch, reverse
from django.utils.html import escape
from django.utils.safestring import mark_safe

from .conf import conf

# Wie django.utils.html.json_script: <, > und & im JSON maskieren, damit kein Wert das <script> beendet.
_MASKE = {ord(">"): "\\u003E", ord("<"): "\\u003C", ord("&"): "\\u0026"}


class TabellenElement:
    @staticmethod
    def html(request):
        c = conf()
        verschieben = bool(c.get("tabellen_spalten_verschieben"))
        anpassen = bool(c.get("tabellen_spalten_anpassen", True))
        benutzer = getattr(request, "user", None)
        je_benutzer = bool(c.get("tabellen_je_benutzer")) and benutzer is not None and benutzer.is_authenticated
        if not verschieben and anpassen and not je_benutzer:
            return ""
        attribute = 'data-verschieben="%d" data-anpassen="%d"' % (verschieben, anpassen)
        daten = {}
        if je_benutzer:
            from .tabellen_einstellung import TabellenEinstellung

            try:
                url = reverse("djangobase:tabellen_einstellung")
            except NoReverseMatch:
                url = ""
            if url:
                daten = dict(
                    TabellenEinstellung.objects.filter(benutzer=benutzer).values_list("schluessel", "wert")
                )
                attribute += ' data-url="%s" data-csrf="%s"' % (escape(url), escape(get_token(request)))
        return mark_safe(
            '<script type="application/json" id="djb-tabellen" %s>%s</script>'
            % (attribute, json.dumps(daten, ensure_ascii=False).translate(_MASKE))
        )
