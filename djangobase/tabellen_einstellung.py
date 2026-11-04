"""TabellenEinstellung — was ein Benutzer an einer Tabelle eingestellt hat (04.11.2026, aus StayNestor).

Spaltenbreiten, Sortierung, ausgeblendete Spalten und Reihenfolge: ein Text (JSON) je Schlüssel, genau wie
``tabellen_speicher.js`` ihn sonst in den localStorage schreibt (``tblBreiten:…``, ``dbTabSort:…``,
``db-spalten:…``, ``tblReihe:…``). Nur mit ``DJANGOBASE["tabellen_je_benutzer"] = True``: dann setzt
``{% djb_tabellen %}`` alle Einträge des Benutzers in die Seite, und ``TabellenEinstellungSpeichern`` nimmt
Änderungen an. Ohne den Schalter fragt niemand diese Tabelle ab — ein Projekt ohne ``migrate djangobase``
läuft unverändert.

Liegt in einer eigenen Datei und wird in ``models.py`` eingebunden (eine Klasse je Datei).
"""

from django.conf import settings
from django.db import models


class TabellenEinstellung(models.Model):
    benutzer = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="djb_tabellen_einstellungen"
    )
    schluessel = models.CharField("Schlüssel", max_length=200)
    wert = models.TextField("Wert (JSON)")
    geaendert = models.DateTimeField(auto_now=True)

    class Meta:
        app_label = "djangobase"
        verbose_name = "Tabellen-Einstellung"
        verbose_name_plural = "Tabellen-Einstellungen"
        constraints = [
            models.UniqueConstraint(fields=["benutzer", "schluessel"], name="djb_tabellen_einstellung_einmal")
        ]

    def __str__(self):
        return f"{self.benutzer} · {self.schluessel}"
