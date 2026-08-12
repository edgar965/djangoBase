"""djangobase.hintergrund_cache - Zwischenspeicher, der NIE in der Anfrage rechnet.

WARUM (gemessen 28.07.2026): Der Entwicklungs-Server arbeitet Anfragen NACHEINANDER
ab. Alles, was eine Anfrage an Rechenzeit verbraucht, warten alle anderen Anfragen
mit - auch die Batches einer laufenden Optimierung.

Gemessen wurde genau das an der Auslastungs-Leiste:

    /api/system-stats/   0,22 s  je Aktualisierung (nvidia-smi ~0,07 s
                                 + psutil.cpu_percent(interval=0.15))
    /api/marktuebersicht/ 0,25 s je Aktualisierung (16 Assets x DB-Abfragen)

Die Leiste fragt WAEHREND einer Optimierung jede Sekunde (``takt(1000)``), und der
Nutzer hat regelmaessig drei bis vier Tabs offen. Bei 1 s Haltbarkeit heisst das:
rund jede Sekunde zahlt EIN Tab die 0,22 s - der Server verbringt damit dauerhaft
etwa ein Fuenftel seiner einzigen Bahn mit dem ANZEIGEN der Auslastung statt mit
dem Rechnen, das die Anzeige zeigen soll.

Dieser Zwischenspeicher dreht das um ("stale while revalidate"):

  * Die Anfrage bekommt SOFORT den zuletzt bekannten Wert (Mikrosekunden).
  * Ist er zu alt, startet ein Hintergrund-Thread die Neuberechnung. Der naechste
    Abruf findet den frischen Wert vor.
  * Nur der allererste Abruf rechnet in der Anfrage - vorher gibt es nichts zu zeigen.

Der Preis ist eine Anzeige, die um bis zu eine Haltbarkeitsdauer hinterherlaeuft.
Fuer eine Auslastungs-Leiste und eine Kurs-Uebersicht ist das genau richtig; fuer
Zahlen, die auf die Sekunde stimmen muessen, waere es das nicht.
"""
from __future__ import annotations

import logging
import threading
import time

logger = logging.getLogger(__name__)


class HintergrundCache:
    """Ein Wert, der im Hintergrund erneuert wird statt in der Anfrage.

    ``bauen``    Funktion ohne Argumente, die den Wert (neu) berechnet.
    ``ttl_s``    Ab diesem Alter (Sekunden) wird im Hintergrund erneuert.
    ``django_db``True, wenn ``bauen`` die Datenbank benutzt - dann gibt der Thread
                 seine eigene DB-Verbindung am Ende wieder zurueck (sonst haelt
                 jeder Thread eine SQLite-Verbindung offen).
    """

    #: Ab diesem Vielfachen der Haltbarkeit gilt ein Wert als so alt, dass er nicht
    #: mehr ausgeliefert, sondern SOFORT neu gerechnet wird.
    STALE_FAKTOR = 20

    def __init__(self, name: str, bauen, ttl_s: float, django_db: bool = False):
        self.name = name
        self._bauen = bauen
        self.ttl_s = float(ttl_s)
        self.django_db = bool(django_db)
        self._wert = None
        self._ts = 0.0
        self._laeuft = False
        self._lock = threading.Lock()
        self._fehler = None
        self._n_bau = 0

    # ------------------------------------------------------------------ lesen
    def holen(self, max_alter: float | None = None):
        """Zuletzt bekannter Wert - ohne zu warten.

        ``max_alter=0`` erzwingt eine SYNCHRONE Neuberechnung (Knopf „Aktualisieren")."""
        if max_alter == 0:
            return self.frisch()
        alter_ttl = self.ttl_s if max_alter is None else float(max_alter)
        with self._lock:
            # Nach langer Ruhe (Tab im Hintergrund, Nacht) waere der gespeicherte
            # Wert Stunden alt. So weit hinterherzulaufen sagt der Modul-Text NICHT
            # zu - ab STALE_FAKTOR x Haltbarkeit wird deshalb synchron gemessen.
            _zu_alt = (self._wert is not None
                       and (time.time() - self._ts) >= alter_ttl * self.STALE_FAKTOR)
        if _zu_alt:
            return self._bauen_jetzt()
        with self._lock:
            wert, ts, laeuft = self._wert, self._ts, self._laeuft
            if wert is not None and (time.time() - ts) >= alter_ttl and not laeuft:
                self._laeuft = True
                threading.Thread(target=self._bauen_thread,
                                 name=f"cache-{self.name}", daemon=True).start()
        # Allererster Abruf: es gibt nichts anzuzeigen, also HIER rechnen. Zwei
        # gleichzeitige erste Abrufe rechnen doppelt - das ist einmal je Serverstart
        # und deutlich harmloser als eine Seite, die beim ersten Aufruf leer bleibt.
        if wert is None:
            return self._bauen_jetzt()
        return wert

    def frisch(self):
        """Synchron neu berechnen (bewusst blockierend)."""
        return self._bauen_jetzt()

    def zustand(self) -> dict:
        """Fuer Diagnose/Tests: Alter, Zahl der Neuberechnungen, letzter Fehler."""
        with self._lock:
            return {"name": self.name, "hat_wert": self._wert is not None,
                    "alter_s": round(time.time() - self._ts, 2) if self._ts else None,
                    "laeuft": self._laeuft, "n_bau": self._n_bau, "fehler": self._fehler}

    # ----------------------------------------------------------------- bauen
    def _bauen_jetzt(self, im_thread: bool = False):
        """``im_thread=False`` = synchroner Pfad (erster Abruf oder ``frisch()``).

        Der synchrone Pfad darf ``_laeuft`` NICHT zuruecksetzen: sonst meldet er
        "kein Bau laeuft", waehrend der Hintergrund-Thread noch rechnet - dessen
        spaeteres, aelteres Ergebnis ueberschriebe danach den frisch geholten Wert
        (Befund Code-Review 29.07.2026). Und ein Ergebnis wird nur uebernommen,
        wenn es JUENGER ist als das gespeicherte."""
        t0 = time.time()
        try:
            wert = self._bauen()
        except Exception as e:                                    # noqa: BLE001
            with self._lock:
                if im_thread:
                    self._laeuft = False
                self._fehler = str(e)
            raise
        with self._lock:
            if im_thread:
                self._laeuft = False
            if t0 >= self._ts:            # nur uebernehmen, wenn nicht ueberholt
                self._wert, self._ts = wert, time.time()
                self._fehler = None
            self._n_bau += 1
        return wert

    def _bauen_thread(self) -> None:
        try:
            self._bauen_jetzt(im_thread=True)
        except Exception as e:                                    # noqa: BLE001
            # Nicht laut werden: der alte Wert bleibt stehen und wird weiter
            # ausgeliefert - genau dafuer gibt es diesen Zwischenspeicher.
            logger.warning("Hintergrund-Aktualisierung '%s' fehlgeschlagen: %s", self.name, e)
        finally:
            if self.django_db:
                try:
                    from django.db import connection
                    connection.close()
                except Exception:                                 # noqa: BLE001
                    pass
