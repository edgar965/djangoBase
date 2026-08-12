"""djangobase.system_stats - GPU-/CPU-Auslastung als wiederverwendbare Leiste.

WARUM: Eine Grid-Optimierung laeuft je nach Raster Minuten. Ohne Anzeige sieht man
nicht, ob die Karte wirklich rechnet oder ob der Lauf im Vorbereitungsteil (Python,
also CPU) haengt - genau die Unterscheidung, die am 27.07.2026 den Unterschied
zwischen "Batch zu klein" (GPU bei 0,6 %) und "Zeilenbau" (CPU auf einem Kern)
ausgemacht hat.

Vorbild: CamTrack (``app/views/settings_views.py: api_system_stats`` +
``_shared.py: _read_gpu_stats``) - dieselbe nvidia-smi-Abfrage, dieselbe
Pill-Leiste, hier nur auf GPU/VRAM/Temp/CPU/RAM eingedampft.

Reine stdlib + psutil (optional). Kein Django-Import - die View reicht das Dict durch.

HIERHER VERSCHOBEN AM 12.08.2026 (Ansage Edgar: „dieses GPU-Auslastungs-Modul soll
in djangoBase verschoben werden. Alle Vorkommnisse von allen Seiten dieses
Auslastungs-Moduls dann nur noch von djangoBase"). Vorher lag es in
shortlongx/dashboard - dort war es an EIN Projekt gebunden, obwohl jedes
Django-Projekt dieselbe Frage hat: rechnet die Maschine gerade, oder haengt sie?
"""
import subprocess
import time

# Am Dateikopf (09.08.2026): ``hintergrund_cache`` ist reine Standardbibliothek und
# importiert nichts aus ``dashboard`` - ein Ring ist ausgeschlossen
# (werkzeug/import_graph.py). Der Zwischenspeicher selbst wird weiterhin erst beim
# ersten Abruf ANGELEGT, damit der Serverstart keinen Thread startet.
from .hintergrund_cache import HintergrundCache

#: Traegt den VORHERIGEN Netzwerk-Zaehlerstand (``net_vor``). psutil liefert nur
#: Summen seit Systemstart - ohne den Vorgaenger stuende in der Leiste eine sinnlos
#: grosse Konstante statt der Rate. Der eigentliche Werte-Cache liegt in ``_HG``.
_CACHE = {"ts": 0.0, "daten": None}
_TTL = 1.0

#: Erneuert wird im HINTERGRUND, nicht in der Anfrage. Gemessen 28.07.2026: eine
#: Aktualisierung kostet 0,22 s (nvidia-smi + psutil.cpu_percent(interval=0.15)).
#: Die Leiste fragt waehrend einer Optimierung jede Sekunde, und der Nutzer hat
#: mehrere Tabs offen - der Entwicklungs-Server verbrachte damit rund ein Fuenftel
#: seiner einzigen Bahn mit dem ANZEIGEN der Auslastung statt mit dem Rechnen.
_HG = None


class SystemStats:
    """GPU- und CPU-Auslastung als einfaches Dict, gecacht (1 s) und GEGLAETTET."""

    #: Schwellen fuer die Farbe der Leiste (gelb / rot).
    WARN, GEFAHR = 75, 90

    #: Ueber so viele Messungen wird gemittelt. Bei ~1 s Abstand sind das ~5 s.
    #: WARUM (gemessen 28.07.2026): nvidia-smi liefert den Anteil eines sehr kurzen
    #: Momentfensters, in dem mindestens ein Kernel lief. Drei Abrufe im 3-s-Abstand
    #: ergaben 11 %, 34 %, 30 % - der Windows-Zaehler dazu 11 %, 16 %, 3 %. Ein
    #: einzelner Momentwert taugt nicht als Anzeige: er springt, und der Nutzer haelt
    #: die Leiste fuer kaputt (genau das ist passiert). Gemittelt zeigt sie das, was
    #: man meint, wenn man "die GPU ist bei 30 %" sagt.
    FENSTER = 5

    _verlauf = {}

    @classmethod
    def verlauf_leeren(cls):
        """Messverlauf verwerfen (Tests, Neustart einer Messreihe)."""
        cls._verlauf = {}

    @classmethod
    def glaetten(cls, key, wert):
        """Momentwert in den Verlauf legen und den Mittelwert des Fensters liefern.

        Einfacher gleitender Mittelwert - kein exponentielles Glaetten: ein Ausreisser
        soll die Anzeige weder sofort hochreissen noch minutenlang nachhaengen."""
        try:
            w = float(wert)
        except (TypeError, ValueError):
            return wert
        reihe = cls._verlauf.setdefault(key, [])
        reihe.append(w)
        if len(reihe) > cls.FENSTER:
            del reihe[:-cls.FENSTER]
        return round(sum(reihe) / len(reihe), 1)

    @staticmethod
    def gpu():
        """GPU-Werte via nvidia-smi - None, wenn keine NVIDIA-Karte da ist."""
        try:
            r = subprocess.run(
                ["nvidia-smi",
                 "--query-gpu=name,utilization.gpu,memory.used,memory.total,temperature.gpu",
                 "--format=csv,noheader,nounits"],
                capture_output=True, text=True, timeout=2,
            )
            if r.returncode != 0:
                return None
            teile = [t.strip() for t in (r.stdout or "").strip().splitlines()[0].split(",")]
            if len(teile) < 5:
                return None
            return {"name": teile[0], "util": int(teile[1]),
                    "mem_used": int(teile[2]), "mem_total": int(teile[3]),
                    "temp": int(teile[4])}
        except (subprocess.TimeoutExpired, OSError, ValueError, IndexError):
            return None

    @staticmethod
    def _disks():
        """Belegung der Start-/System-Platte UND der Platte, auf der die App
        laeuft (aus dem cwd abgeleitet). Bei nur einer Platte genau eine,
        sonst beide (dedupliziert). Reine stdlib (shutil.disk_usage).

        Windows: 'C:' (SystemDrive) + z.B. 'A:' (Projekt-Laufwerk).
        Unix: in aller Regel nur '/'."""
        import os
        import shutil
        kandidaten = []
        sysdrv = os.environ.get("SystemDrive")            # Windows: 'C:'
        kandidaten.append((sysdrv.rstrip("\\/") + os.sep) if sysdrv
                          else os.path.abspath(os.sep))    # Unix: '/'
        try:
            appdrv = os.path.splitdrive(os.getcwd())[0]    # Windows: 'A:'
            kandidaten.append((appdrv + os.sep) if appdrv
                              else os.path.abspath(os.sep))
        except OSError:
            pass
        gesehen, aus = [], []
        for pfad in kandidaten:
            key = pfad.rstrip("\\/").upper() or "/"
            if key in gesehen:
                continue
            gesehen.append(key)
            try:
                u = shutil.disk_usage(pfad)
            except OSError:
                continue
            aus.append({
                "name": key,
                "percent": round(100 * u.used / u.total, 1) if u.total else 0,
                "used_gb": round(u.used / 1e9, 1),
                "total_gb": round(u.total / 1e9, 1),
            })
        return aus

    @classmethod
    def lesen(cls):
        """Aktuelle Auslastung - antwortet SOFORT aus dem Zwischenspeicher.

        Ist der Wert aelter als ``_TTL``, erneuert ihn ein Hintergrund-Thread; die
        Anfrage wartet nicht darauf (siehe ``hintergrund_cache``). Nur der erste
        Abruf nach dem Serverstart rechnet hier."""
        global _HG
        if _HG is None:
            _HG = HintergrundCache("system-stats", cls._messen, _TTL)
        return _HG.holen()

    @classmethod
    def _messen(cls):
        """Eine echte Messung (kostet ~0,22 s) - laeuft im Hintergrund-Thread."""
        jetzt = time.time()
        _gpu = cls.gpu()
        if _gpu:                                   # Momentwert -> Fenster-Mittel
            _gpu["util_roh"] = _gpu["util"]
            _gpu["util"] = int(round(cls.glaetten("gpu", _gpu["util"])))
        daten = {"gpu": _gpu, "cpu_percent": None, "ram_percent": None,
                 "kerne": None, "net_recv_mbps": 0.0, "net_sent_mbps": 0.0,
                 "disks": []}
        try:
            import psutil
            # interval=0.15 statt 0.3 (CamTrack): die Leiste laeuft WAEHREND einer
            # Optimierung mit - jede Zehntelsekunde Blockade geht dort ab.
            daten["cpu_percent"] = cls.glaetten("cpu", psutil.cpu_percent(interval=0.15))
            daten["ram_percent"] = round(psutil.virtual_memory().percent, 1)
            daten["kerne"] = psutil.cpu_count(logical=True)
            # Netzwerk wie CamTrack: DIFFERENZ zum vorherigen Sample ueber alle
            # Interfaces. psutil liefert nur Zaehler seit Systemstart - ohne die
            # Differenz stuende dort eine sinnlos grosse Konstante. Beim ersten
            # Aufruf gibt es keinen Vorgaenger, also 0.
            n = psutil.net_io_counters()
            vor = _CACHE.get("net_vor")
            if vor:
                dt = jetzt - vor["ts"]
                if dt > 0:
                    daten["net_recv_mbps"] = round((n.bytes_recv - vor["recv"]) * 8 / 1e6 / dt, 1)
                    daten["net_sent_mbps"] = round((n.bytes_sent - vor["sent"]) * 8 / 1e6 / dt, 1)
            _CACHE["net_vor"] = {"ts": jetzt, "recv": n.bytes_recv, "sent": n.bytes_sent}
        except ImportError:
            pass
        # Bewusst NICHT mehr `daten` hier ablegen: den Wert haelt seit dem Umbau
        # `_HG`, dieser Eintrag wurde nie wieder gelesen. `net_vor` (oben) bleibt -
        # er traegt den vorherigen Netzwerk-Zaehlerstand fuer die Differenz.
        daten["disks"] = cls._disks()
        _CACHE["ts"] = jetzt
        return daten
