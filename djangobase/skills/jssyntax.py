# -*- coding: utf-8 -*-
u"""JsSyntax - jede .js-Datei als ES-Modul pruefen.

DER BEFUND (3DTools, 16.08.2026)
================================
Ein Werkzeug fuegte Import-Zeilen automatisch ein und traf dabei drei Dateien
MITTEN in einem mehrzeiligen Import::

    import { a, b,
    import { Serverabruf } from './serverabruf.js';     <-- hier eingefuegt
             c } from './x.js';

Die Dateien waren damit unlesbar - jede Seite, die sie laedt, blieb weiss.
``node --check datei.js`` fand es NICHT: Node prueft ``.js`` als CommonJS und
toleriert die kaputte Stelle. Erst dieselbe Datei als ``.mjs`` kopiert und
geprueft war rot.

DESHALB kopiert dieses Werkzeug jede Datei in eine Wegwerf-``.mjs`` und laesst
``node --check`` darauf laufen. Das ist die einzige Pruefung, die den Fehler
sieht, ohne einen Browser zu starten.

VORAUSSETZUNG: ``node`` im PATH. Fehlt es, meldet das Werkzeug das - und
behauptet nicht, alles sei in Ordnung.
"""
import shutil
import subprocess
import tempfile
from pathlib import Path

from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug

__all__ = ["JsSyntax"]


class JsSyntax(Werkzeug):
    slug = "jssyntax"
    titel = "ES-Module: Syntax prüfen"
    zweck = ("Kopiert jede .js-Datei als .mjs und lässt `node --check` darauf "
             "laufen - findet kaputte Importe, die als CommonJS durchgehen.")
    befund = ("3DTools: drei Dateien hatten eine Import-Zeile mitten in einem "
              "mehrzeiligen Import. `node --check` auf der .js-Datei war grün, "
              "als .mjs rot. Die Seiten blieben weiß.")
    abhilfe = ("Die gemeldete Zeile ansehen. Meist steht dort eine Zeile in "
               "einer Anweisung, die sich über mehrere Zeilen zieht.")
    dauer = "2-10 s (je Datei ein node-Aufruf)"
    kriterium = 3


    #: Eine fehlende schliessende Klammer - genau der Schaden, den ein
    #: Datei-Schnitt anrichtet, wenn der Fuss der Klasse nicht mitwandert.
    #: Daneben eine heile Datei, damit auffiele, wenn das Werkzeug pauschal
    #: alles meldet.
    anlassfall = Anlassfall(
        {"kaputt.js": '''export class Halb {
  eins() { return 1; }
''',
         "heil.js": '''export class Ganz {
  eins() { return 1; }
}
'''},
        mindestens=1, hoechstens=1,
        erwartet_in="kaputt.js",
        warum="Beim Teilen ging die schließende Klammer verloren; das Symptom "
              "war ein rätselhaftes „Unexpected token '.'“ weiter unten")

    def laufen(self):
        node = shutil.which("node")
        if not node:
            return Ergebnis(["ort", "meldung"], [],
                            zusammenfassung="node nicht gefunden",
                            hinweis="Ohne Node ist diese Prüfung nicht "
                                    "möglich. Sie gilt NICHT als grün.")
        dateien = list(self._quellen())
        kaputt = []
        with tempfile.TemporaryDirectory(prefix="jssyntax_") as ordner:
            ziel = Path(ordner) / "pruefung.mjs"
            for pfad in dateien:
                meldung = self._pruefen(node, pfad, ziel)
                if meldung:
                    kaputt.append({
                        "ort": pfad.relative_to(self.wurzel()).as_posix(),
                        "meldung": meldung})
        return Ergebnis(
            ["ort", "meldung"], kaputt,
            zusammenfassung="%d Dateien als ES-Modul geprüft, %d mit Fehler"
                            % (len(dateien), len(kaputt)))

    def _pruefen(self, node, pfad, ziel):
        """Erste Fehlerzeile von `node --check`, sonst ''."""
        try:
            ziel.write_bytes(pfad.read_bytes())
            fertig = subprocess.run([node, "--check", str(ziel)],
                                    capture_output=True, text=True, timeout=30)
        except (OSError, subprocess.SubprocessError) as fehler:
            return "%s: %s" % (type(fehler).__name__, fehler)
        if fertig.returncode == 0:
            return ""
        for zeile in (fertig.stderr or "").split("\n"):
            if "Error" in zeile or "error" in zeile:
                return zeile.strip()[:200]
        return (fertig.stderr or "unbekannter Fehler").strip()[:200]

    #: Ausschlussliste und Suche stehen seit dem 17.08.2026 in
    #: ``Frontendquellen`` — vorher hatte sie jedes JS-Werkzeug einzeln,
    #: in vier verschiedenen Fassungen.
    def _quellen(self):
        return self.frontendquellen().pfade(".js")
