# -*- coding: utf-8 -*-
u"""KI-Modelle: Katalog und Messungen - fuer jedes djangoBase-Projekt.

WOHER DAS KOMMT (Ansage Edgar, 18.08.2026)
==========================================
    „kannst du diese Seite nach djangoBase verschieben?"

Die Seite Hilfe → KI-Modelle stand bis dahin in shortlongx
(``brain/ki_modelle.py``, ``brain/ki_messungen.py``, ein eigener View). Nichts
daran ist an dieses Projekt gebunden: Der Katalog kommt live von OpenRouter und
aus ``ollama list``, die Bewertung aus Messungen an den Modellen selbst. Die
Frage „welches Modell taugt als Sparringspartner, was kostet es, passt es auf
diese Karte" stellt sich in jedem Projekt gleich.

VIER DATEIEN, ZWEI HALTBARKEITEN
================================
    ``modelle.py``    Onlinekatalog - Preis und Kontext von OpenRouter.
    ``ollama.py``     die Modelle auf DIESEM Rechner.
    ``modellname.py`` was im Namen steht: Parameterzahl, Plattenbedarf.
                      Diese drei aendern sich woechentlich, kommen deshalb live.
    ``messungen.py``  Das eigene Urteil - Note, Zeit je Frage, Treffer.
                      Einmal gemessen, bleibt gueltig.

Beide brauchen NICHTS ausser der Standardbibliothek (geprueft beim Umzug): kein
Django, kein numpy, keine Projektpfade. Der einzige veraenderliche Teil ist das
Cache-Verzeichnis, das der Aufrufer uebergibt.
"""
from .messungen import BEFUNDE, Bestenliste
from .modelle import ModellKatalog
from .modellname import GB_JE_MRD, Modellname
from .ollama import OllamaModelle

__all__ = ["ModellKatalog", "OllamaModelle", "Modellname", "GB_JE_MRD",
           "Bestenliste", "BEFUNDE"]
