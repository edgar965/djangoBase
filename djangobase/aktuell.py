# -*- coding: utf-8 -*-
"""AktuellFeed — rollierendes Fenster fuer Ergebnisse der Claude-CLI.

WOZU (13.08.2026)
-----------------
Was die CLI in einer Sitzung herausfindet, steht danach im Terminal und ist
weg: welcher Befund bestaetigt wurde, welche Messung ihn getragen hat, was
noch offen ist. Diese Seite ist der Ort, an dem das stehen bleibt — je Projekt,
sichtbar unter Hilfe -> Aktuell.

ROLLIERENDES FENSTER, nicht Archiv: Die neuesten ``MAX_EINTRAEGE`` bleiben, der
Rest fliegt heraus. Das ist Absicht. Ein Feed, der alles behaelt, wird zur
Halde, die niemand liest, und waechst unbegrenzt in ein Verzeichnis, das
niemand beobachtet. Wer etwas dauerhaft braucht, schreibt es in die Doku oder
in einen Commit.

KEINE DATENBANK: Der Feed soll auch dann schreibbar sein, wenn kein Server
laeuft und keine Migration angewandt ist — eine Zeile JSON je Eintrag in einer
Datei. Das macht ihn ausserdem von Hand lesbar (``type aktuell.jsonl``).

GESCHRIEBEN WIRD ueber ``manage.py aktuell`` (siehe management/commands) —
bewusst als Verwaltungsbefehl und nicht ueber HTTP: kein Token, keine
Anmeldung, kein offener Schreib-Endpunkt, und es funktioniert auch bei
gestopptem Server.

    manage.py aktuell --titel "SafePath: ADS-Loch geschlossen" --art fix
    ... | manage.py aktuell --titel "Testlauf" --art messung   (Text von stdin)
"""
import json
import logging
import os
import tempfile
import time
from pathlib import Path

logger = logging.getLogger(__name__)

#: Bekannte Arten. Die Oberflaeche faerbt danach; unbekannte Werte werden
#: angezeigt, aber nicht gefaerbt.
ARTEN = ("notiz", "befund", "fix", "messung", "offen", "frage")


class AktuellFeed:
    """Ein rollierendes Fenster aus JSON-Zeilen."""

    #: So viele Eintraege bleiben. Aeltere fallen heraus.
    MAX_EINTRAEGE = 200
    #: Obergrenze je Eintragstext. Ein Testprotokoll mit 4.000 Zeilen gehoert
    #: nicht in eine Uebersichtsseite; der Anfang sagt schon, was los ist.
    MAX_ZEICHEN = 20_000

    def __init__(self, pfad):
        self.pfad = Path(pfad)

    # ------------------------------------------------------------------ lesen

    def lesen(self, limit=None, art=None):
        """Neueste zuerst. Kaputte Zeilen werden uebersprungen, nicht geworfen —
        eine halb geschriebene letzte Zeile darf die Seite nicht leer machen."""
        if not self.pfad.exists():
            return []
        eintraege = []
        try:
            with open(self.pfad, "r", encoding="utf-8", errors="replace") as f:
                for zeile in f:
                    zeile = zeile.strip()
                    if not zeile:
                        continue
                    try:
                        eintraege.append(json.loads(zeile))
                    except (json.JSONDecodeError, ValueError):
                        continue
        except OSError as e:
            logger.warning("Aktuell: %s nicht lesbar: %s", self.pfad, e)
            return []
        eintraege.reverse()
        if art:
            eintraege = [e for e in eintraege if e.get("art") == art]
        return eintraege[:limit] if limit else eintraege

    def arten_zaehlen(self):
        z = {}
        for e in self.lesen():
            z[e.get("art") or "notiz"] = z.get(e.get("art") or "notiz", 0) + 1
        return z

    # ---------------------------------------------------------------- schreiben

    def anhaengen(self, titel, text="", art="notiz", quelle="", zeitpunkt=None):
        """Einen Eintrag anhaengen und das Fenster nachziehen."""
        eintrag = {
            "zeit": zeitpunkt or time.strftime("%Y-%m-%d %H:%M:%S"),
            "titel": (titel or "").strip()[:300],
            "art": (art or "notiz").strip().lower()[:20],
            "quelle": (quelle or "").strip()[:120],
            "text": self._kuerzen(text or ""),
        }
        self.pfad.parent.mkdir(parents=True, exist_ok=True)
        with open(self.pfad, "a", encoding="utf-8") as f:
            f.write(json.dumps(eintrag, ensure_ascii=False) + "\n")
        self._fenster_nachziehen()
        return eintrag

    def _kuerzen(self, text):
        if len(text) <= self.MAX_ZEICHEN:
            return text
        # Sichtbar kuerzen: Ein stillschweigend abgeschnittener Text laesst den
        # Leser glauben, mehr sei nicht da gewesen.
        return (text[:self.MAX_ZEICHEN]
                + "\n\n[... gekuerzt: %d von %d Zeichen ...]"
                % (self.MAX_ZEICHEN, len(text)))

    def _fenster_nachziehen(self):
        """Auf MAX_EINTRAEGE zurueckschneiden — ganz oder gar nicht.

        Neu geschrieben wird in eine Nebendatei im SELBEN Verzeichnis und dann
        per ``os.replace`` an ihren Platz gerueckt: Ein Absturz mitten im
        Kuerzen darf keinen halben Feed hinterlassen."""
        try:
            with open(self.pfad, "r", encoding="utf-8", errors="replace") as f:
                zeilen = f.readlines()
        except OSError:
            return
        if len(zeilen) <= self.MAX_EINTRAEGE:
            return
        behalten = zeilen[-self.MAX_EINTRAEGE:]
        tmp = None
        try:
            with tempfile.NamedTemporaryFile(
                    mode="w", encoding="utf-8", dir=str(self.pfad.parent),
                    prefix="." + self.pfad.name + ".", suffix=".tmp",
                    delete=False) as f:
                tmp = f.name
                f.writelines(behalten)
                f.flush()
                os.fsync(f.fileno())
            os.replace(tmp, str(self.pfad))
            tmp = None
        except OSError as e:
            logger.warning("Aktuell: Fenster nicht nachgezogen: %s", e)
        finally:
            if tmp and os.path.exists(tmp):
                try:
                    os.unlink(tmp)
                except OSError:
                    pass

    def leeren(self):
        try:
            self.pfad.unlink()
        except FileNotFoundError:
            pass
        except OSError as e:
            logger.warning("Aktuell: %s nicht loeschbar: %s", self.pfad, e)


def feed():
    """Der Feed dieses Projekts (Pfad aus der Konfiguration)."""
    from .conf import conf
    c = conf()
    return AktuellFeed(c.get("aktuell_datei") or (c["log_verzeichnis"] / "aktuell.jsonl"))
