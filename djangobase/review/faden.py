# -*- coding: utf-8 -*-
"""ReviewFaden — EIN Gespraech ueber EINEN Codebereich.

Ein Lauf mit mehreren Bereichen besteht aus mehreren Faeden, die gleichzeitig
laufen und je einen eigenen Verlauf haben. Getrennte Verlaeufe sind kein
Schoenheitsfehler-Vermeiden, sondern noetig: In einem gemeinsamen Gespraech
vermischt das Modell Befunde aus fremden Bereichen und bezieht sich in Runde 3
auf Code, um den es gerade nicht geht.

Jeder Faden schreibt seine Mitschrift fortlaufend auf die Platte. Der Lauf lebt
im Arbeitsspeicher und ist nach einem Server-Neustart weg — die Mitschrift
nicht.
"""
import logging
import threading
import time

logger = logging.getLogger(__name__)


class ReviewFaden:
    """Verlauf, Zustand und Mitschrift eines Gespraechs."""

    def __init__(self, slug, titel, partner, mitschrift=None):
        self.slug = slug
        self.titel = titel
        self.partner = partner
        self.mitschrift = mitschrift
        self.runden = []                  # [{'frage','antwort','sekunden','verbrauch'}]
        self.status = "wartet"            # wartet | laeuft | fertig | fehler
        self.fehler = ""
        self._lock = threading.Lock()

    # ------------------------------------------------------------------ fragen

    def fragen(self, text, marke=""):
        """Eine Runde stellen. Laeuft im Hintergrund-Faden des Laufs."""
        with self._lock:
            if self.status == "laeuft":
                raise RuntimeError("Dieser Faden wartet noch auf eine Antwort")
            self.status = "laeuft"
        t0 = time.time()
        try:
            antwort = self.partner.fragen(text)
        except Exception as e:                                    # noqa: BLE001
            with self._lock:
                self.status, self.fehler = "fehler", str(e)
            logger.warning("Review-Faden '%s' fehlgeschlagen: %s", self.slug, e)
            self._schreiben(marke, text, "FEHLER: %s" % e, time.time() - t0)
            return None
        dauer = time.time() - t0
        with self._lock:
            self.runden.append({
                "marke": marke or ("Runde %d" % (len(self.runden) + 1)),
                "frage": text, "antwort": antwort, "sekunden": round(dauer, 1),
                "verbrauch": self.partner.verbrauch[-1] if self.partner.verbrauch else {},
            })
            self.status = "fertig"
        self._schreiben(marke, text, antwort, dauer)
        return antwort

    # -------------------------------------------------------------- Mitschrift

    def _schreiben(self, marke, frage, antwort, dauer):
        if not self.mitschrift:
            return
        try:
            self.mitschrift.parent.mkdir(parents=True, exist_ok=True)
            with open(self.mitschrift, "a", encoding="utf-8") as f:
                f.write("\n\n## %s — %s (%s, %.0f s)\n\n### Gefragt\n\n%s\n\n"
                        "### Geantwortet\n\n%s\n"
                        % (marke or "Runde", self.titel, self.partner.modell,
                           dauer, frage.strip(), (antwort or "").strip()))
        except OSError as e:
            # Die Mitschrift ist Beiwerk — ein fehlender Ordner darf das
            # Gespraech nicht beenden.
            logger.warning("Mitschrift '%s' nicht schreibbar: %s", self.mitschrift, e)

    # ------------------------------------------------------------------ Anzeige

    def zustand(self, mit_text=True):
        with self._lock:
            d = {"slug": self.slug, "titel": self.titel, "status": self.status,
                 "fehler": self.fehler, "modell": self.partner.modell,
                 "partner": self.partner.name, "runden_anzahl": len(self.runden)}
            if mit_text:
                d["runden"] = list(self.runden)
            return d
