# -*- coding: utf-8 -*-
u"""Umbau - Werkzeuge, die Quelltext AENDERN (keine Web-Knoepfe).

Warum nicht in ``skills2``: Die Werkzeuge dort messen und melden. Diese hier
schreiben Dateien. Ein Knopf auf einer Hilfe-Seite, der 30 Dateien umschreibt,
ist keine gute Idee - deshalb laufen sie ueber die Kommandozeile, mit
Probelauf als Vorgabe.

    python -m djangobase.umbau.serverabrufe <wurzel>              # Probelauf
    python -m djangobase.umbau.serverabrufe <wurzel> --schreiben
    python -m djangobase.umbau.protokoll <wurzel> --schreiben
    python -m djangobase.umbau.jsimporte Protokoll datei.js …
    python -m djangobase.umbau.stilklassen vorlage.html --schreiben

ENTSTANDEN im 3DTools-Durchgang (16.08.2026), wo sie zusammen 144 Stellen
umgestellt haben: 125 ungepruefte `fetch`-Aufrufe und 133 `console.log`.

VORAUSSETZUNG im Zielprojekt: die beiden Frontend-Klassen `Serverabruf`
(Statuspruefung, CSRF, POST-Helfer) und `Protokoll` (debug/info/warnung/fehler
mit Schalter). Die Umsteller schreiben die Importe darauf - ohne die Klassen
laufen die Seiten danach nicht. Vorlagen dafuer stehen in
``djangobase/static/djangobase/js/``.

REIHENFOLGE, die sich bewaehrt hat:
1. Probelauf, Liste der „braucht Handarbeit"-Stellen lesen.
2. Mit ``--schreiben`` laufen lassen.
3. `skills2.JsSyntax` laufen lassen (findet kaputte Importe, die `node --check`
   auf `.js` uebersieht).
   Beim Stil-Umbau stattdessen `static/djangobase/js/stilmessung.js`: VOR dem
   Lauf im Browser messen, danach vergleichen. Eine CSS-Klasse hat eine
   niedrigere Spezifitaet als ein Inline-Stil — zwei Regressionen sind auf
   genau diesem Weg aufgefallen und waeren sonst niemandem aufgefallen.
4. Testsuite und die betroffenen Seiten im Browser pruefen.
"""

from .jsimporte import Importblock
from .protokoll import ProtokollUmstellung
from .serverabrufe import ServerabrufUmstellung
from .stilklassen import Stilklassen

__all__ = ["Importblock", "ProtokollUmstellung", "ServerabrufUmstellung",
           "Stilklassen"]
