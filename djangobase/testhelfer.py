# -*- coding: utf-8 -*-
u"""Webmodul - ein ES-Modul der Seite in Node laden, ohne Browser.

WOZU (16.08.2026)
=================
JavaScript-Logik, die ohne DOM prueffaehig ist (Parser, Umrechnungen,
Tabellen), gehoert in die Testsuite des Projekts - ``manage.py test`` soll sie
mitlaufen lassen. Node kann ein ES-Modul direkt laden, aber zwei Dinge stehen
im Weg:

1. **Absolute Pfade.** Ein Modul, das eine gemeinsame Klasse aus djangoBase
   holt, schreibt ``from '/static/djangobase/js/serverabruf.js'``. Im Browser
   loest das der Server auf; Node sucht im Dateisystem nach ``A:\\static\\…``
   und wirft ERR_MODULE_NOT_FOUND. Genau daran ist am 16.08.2026 ein gruener
   Test rot geworden, nachdem eine Klasse nach djangoBase gezogen war.
2. **Versionsanhaenge.** ``from './x.js?v=3'`` ist im Browser dieselbe Datei,
   fuer Node ein Pfad mit Fragezeichen.

`Webmodul` spiegelt deshalb das Einstiegsmodul und alles, was es transitiv
importiert, in einen Wegwerf-Ordner und biegt beim Kopieren die Importe um. Die
Dateien selbst bleiben unberuehrt.

    from djangobase.testhelfer import Webmodul

    modul = Webmodul(pfad, wurzeln={'/static/': projekt_static,
                                    '/static/djangobase/': db_static})
    ergebnis = modul.laufen("const { Bvhtext } = await import(MODUL); …")

ES WIRD NICHTS GEHEILT, WAS KAPUTT IST: Zeigt ein Import ins Leere, wirft
`Webmodul` mit dem Pfad in der Meldung. Ein Testlaeufer, der fehlende Importe
stillschweigend ueberspringt, meldet gruen und prueft nichts.
"""
import json
import os
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

__all__ = ["Webmodul", "WebmodulFehler"]

#: `from '…'` und `import('…')` - beides mit optionalem ?v=
IMPORTE = re.compile(r"""(from\s+|import\s*\(\s*)(['"])([^'"]+\.js)(\?[^'"]*)?\2""")


class WebmodulFehler(RuntimeError):
    """Ein Import zeigt ins Leere oder Node hat den Lauf abgebrochen."""


class Webmodul:
    """Ein ES-Modul samt Importen, gespiegelt und in Node ausfuehrbar."""

    #: So lange darf ein Lauf dauern.
    ZEITGRENZE_S = 60

    def __init__(self, pfad, wurzeln=None):
        self.pfad = Path(pfad).resolve()
        #: {'/static/': <Ordner>} - laengste Vorsilbe gewinnt beim Aufloesen.
        self.wurzeln = {k: Path(v).resolve()
                        for k, v in (wurzeln or {}).items()}
        self.ordner = None
        self.spiegel = {}          # echter Pfad -> Pfad im Wegwerf-Ordner

    # ------------------------------------------------------------- Spiegeln

    def aufbauen(self):
        """Alles Erreichbare kopieren; liefert den Pfad des Einstiegsmoduls."""
        self.ordner = Path(tempfile.mkdtemp(prefix="webmodul_"))
        offen = [self.pfad]
        while offen:
            quelle = offen.pop()
            if quelle in self.spiegel:
                continue
            text = quelle.read_text(encoding="utf-8", errors="replace")
            ziel = self._zielpfad(quelle)
            self.spiegel[quelle] = ziel
            for weiter in self._importziele(quelle, text):
                offen.append(weiter)
        # Erst nach dem Sammeln schreiben: Die Pfade der Nachbarn muessen
        # bekannt sein, um die Importe umzubiegen.
        for quelle, ziel in self.spiegel.items():
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(self._umgebogen(quelle), encoding="utf-8")
        return self.spiegel[self.pfad]

    def wegwerfen(self):
        if self.ordner:
            shutil.rmtree(self.ordner, ignore_errors=True)
            self.ordner = None

    def _zielpfad(self, quelle):
        """Ort im Wegwerf-Ordner - flach je Quellwurzel, Struktur erhalten."""
        for name, wurzel in sorted(self.wurzeln.items(), key=lambda p: -len(p[0])):
            try:
                rest = quelle.relative_to(wurzel)
            except ValueError:
                continue
            marke = name.strip("/").replace("/", "_") or "static"
            return self.ordner / marke / rest
        return self.ordner / "eigen" / quelle.name

    def _importziele(self, quelle, text):
        """Die Dateien, die `quelle` importiert - aufgeloest."""
        ziele = []
        for _, _, angabe, _ in IMPORTE.findall(text):
            ziel = self._aufloesen(quelle, angabe)
            if ziel is None:
                # Fremdbibliotheken ueber Importkarten ('three') haben keine
                # Endung .js und tauchen hier nicht auf; alles andere ist ein
                # echter Fehler.
                raise WebmodulFehler(
                    "%s importiert '%s' - dort liegt keine Datei"
                    % (quelle.name, angabe))
            ziele.append(ziel)
        return ziele

    def _aufloesen(self, quelle, angabe):
        if angabe.startswith("."):
            ziel = (quelle.parent / angabe).resolve()
            return ziel if ziel.is_file() else None
        for name, wurzel in sorted(self.wurzeln.items(), key=lambda p: -len(p[0])):
            if angabe.startswith(name):
                ziel = (wurzel / angabe[len(name):]).resolve()
                if ziel.is_file():
                    return ziel
        return None

    def _umgebogen(self, quelle):
        """Text der Datei mit Importen, die im Wegwerf-Ordner stimmen."""
        eigenes_ziel = self.spiegel[quelle]

        def ersetzen(treffer):
            kopf, anfuehrung, angabe, _anhang = treffer.groups()
            ziel = self._aufloesen(quelle, angabe)
            if ziel is None or ziel not in self.spiegel:
                return treffer.group(0)
            rel = os.path.relpath(self.spiegel[ziel], eigenes_ziel.parent)
            rel = rel.replace("\\", "/")
            if not rel.startswith("."):
                rel = "./" + rel
            return "%s%s%s%s" % (kopf, anfuehrung, rel, anfuehrung)

        return IMPORTE.sub(ersetzen,
                           quelle.read_text(encoding="utf-8", errors="replace"))

    # -------------------------------------------------------------- Ausfuehren

    def laufen(self, skript):
        u"""Skript in Node ausfuehren. `MODUL` darin ist der Pfad des Moduls.

        Erwartet, dass das Skript EINE JSON-Zeile ausgibt; die wird geparst
        zurueckgegeben.
        """
        if not shutil.which("node"):
            raise WebmodulFehler("node ist nicht im PATH")
        einstieg = self.aufbauen()
        try:
            vollstaendig = ("const MODUL = %s;\n%s"
                            % (json.dumps(einstieg.as_uri()), skript))
            lauf = subprocess.run(
                ["node", "--input-type=module", "-e", vollstaendig],
                capture_output=True, text=True, encoding="utf-8",
                timeout=Webmodul.ZEITGRENZE_S)
            if lauf.returncode != 0:
                raise WebmodulFehler("node-Lauf gescheitert: %s" % lauf.stderr)
            letzte = (lauf.stdout or "").strip().splitlines()
            if not letzte:
                raise WebmodulFehler("node hat nichts ausgegeben")
            return json.loads(letzte[-1])
        finally:
            self.wegwerfen()
