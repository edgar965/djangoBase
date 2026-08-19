# -*- coding: utf-8 -*-
u"""Hilfe -> KI-Modelle: welches Modell taugt als Sparringspartner?

Die Seite zeigt DREI Tabellen (Ansage Edgar, 11.08.2026):

    1. die Bestenliste - gemessen, egal ob kostenlos oder bezahlt
    2. die kostenlosen Modelle
    3. die bezahlten Modelle

Die Katalogdaten kommen live von OpenRouter und aus ``ollama list``
(``djangobase.ki.modelle``), die Bewertung aus der eigenen Messung
(``djangobase.ki.messungen``). Beides bewusst getrennt: Preise aendern sich
woechentlich, ein einmal gemessenes Urteil nicht.

AUS shortlongx HIERHER (18.08.2026, Ansage: „kannst du diese Seite nach
djangoBase verschieben?"). Projektspezifisch war daran nur zweierlei, und beides
ist jetzt konfigurierbar:

    ``ki_cache``      wohin der Katalog zwischengespeichert wird
                      (Vorgabe: ``BASE_DIR/output/KI_Modelle``)
    ``ki_anbieter``   welche Anbieter ueberhaupt angezeigt werden

OHNE FILTER waeren es ueber 400 Zeilen, die meisten davon Bildmodelle,
Rollenspiel-Ableger und Altbestand. „moonshot" kam am 11.08.2026 dazu: Kimi K3
stand in der GEMESSENEN Bestenliste, fehlte aber im Katalog darunter - dieselbe
Seite zeigte das Modell einmal mit Note und einmal gar nicht. Wer ein Modell
testet, traegt seinen Anbieter hier nach.
"""
import logging
from pathlib import Path

from django.conf import settings
from django.shortcuts import render
from django.views import View

logger = logging.getLogger(__name__)

#: Anbieter, die das Feld abdecken, das fuer diese Arbeit in Frage kommt.
ANBIETER = ("qwen", "nvidia", "gemini", "gemma", "llama", "deepseek",
            "openai", "anthropic", "mistral", "moonshot")


class KiModelleView(View):
    """Bestenliste, kostenlose und bezahlte Modelle - mit Note, Preis und GB."""

    vorlage = "djangobase/hilfe/ki_modelle.html"

    def _konf(self, name, vorgabe):
        return (getattr(settings, "DJANGOBASE", {}) or {}).get(name, vorgabe)

    def _cache_verzeichnis(self):
        u"""Wohin der Katalog zwischengespeichert wird.

        ``BASE_DIR`` statt einer festen Projektwurzel: In shortlongx stand hier
        ``PROJEKT_WURZEL / "output" / "KI_Modelle"`` - ein Pfad, den es in
        anderen Projekten nicht gibt.
        """
        eigen = self._konf("ki_cache", None)
        if eigen:
            return Path(eigen)
        return Path(str(getattr(settings, "BASE_DIR", "."))) / "output" / "KI_Modelle"

    def get(self, request):
        from ..ki import BEFUNDE, Bestenliste, GB_JE_MRD, ModellKatalog

        katalog = ModellKatalog(cache_verzeichnis=self._cache_verzeichnis())
        frei, bezahlt, lokal, beste = [], [], [], []
        try:
            frei, bezahlt = katalog.tabellen(
                anbieter=tuple(self._konf("ki_anbieter", ANBIETER)))
            # EINMAL holen und diese Liste weiterreichen: ``lokal()`` baut bei
            # jedem Aufruf eine neue Liste, ein Update auf einer Zwischenkopie
            # waere wirkungslos gewesen.
            lokal = katalog.lokal()
            beste = Bestenliste(katalog).zeilen()
            # DIE MESSWERTE IN DIE KATALOG-TABELLEN (Ansage Edgar, 11.08.2026):
            # Note, Zeit und Trefferzahl standen bisher nur in der Bestenliste.
            # Wer in der langen Preisliste steht und ob er getestet wurde, waren
            # zwei getrennte Ansichten - man musste hin und her springen.
            # Ungetestete Zeilen bleiben leer; eine Note zu erfinden waere
            # schlimmer als eine Luecke.
            gemessen = {z["kennung"]: z for z in beste}
            for zeile in frei + bezahlt + lokal:
                m = gemessen.get(zeile["kennung"])
                if m:
                    zeile.update(note=m.get("note"), note_grund=m.get("note_grund"),
                                 sek_je_frage=m.get("sek_je_frage"), kern=m.get("kern"),
                                 kern_moeglich=m.get("kern_moeglich"),
                                 ct_je_frage=m.get("ct_je_frage"))
        except Exception:                                   # noqa: BLE001
            logger.exception("Modellkatalog konnte nicht aufgebaut werden")

        return render(request, self.vorlage, {
            "beste": beste,
            "frei": frei,
            "bezahlt": bezahlt,
            "lokal": lokal,
            "befunde": BEFUNDE,
            "quelle": katalog.quelle,
            "stand": katalog.stand,
            "gb_je_mrd": GB_JE_MRD,
        })
