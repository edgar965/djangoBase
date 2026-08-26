"""Endpunktzeiten — Laufzeit und Antwortgröße jeder GET-Route."""

from statistics import median

from .routen import alle_routen, klient
from .befund import Befund, Befundsatz, BefundWerkzeug


class Messwert:
    """Messung einer Route: Bestzeit, Median, Größe, Statuscode."""

    __slots__ = ('weg', 'best_ms', 'median_ms', 'bytes', 'status')

    def __init__(self, weg, best_ms, median_ms, groesse, status):
        self.weg = weg
        self.best_ms = best_ms
        self.median_ms = median_ms
        self.bytes = groesse
        self.status = status

    def beschreibung(self):
        return ('%7.1f ms (Median %7.1f)  %9d Byte  Status %s'
                % (self.best_ms, self.median_ms, self.bytes, self.status))


class Endpunktzeiten(BefundWerkzeug):

    slug = 'endpunkt-zeiten'
    titel = 'Endpunkt-Zeiten'
    zweck = ('Ruft jede GET-Route mehrfach auf und listet Bestzeit, Median und '
             'Antwortgröße — die langsamsten zuerst.')
    abhilfe = ('Als erster Schritt jedes Performance-Durchgangs. Erst messen, dann '
            'optimieren: Die teuerste Stelle liegt fast nie dort, wo man sie '
            'vermutet.')
    befund = ('Im Ursprungsprojekt standen so acht Endpunkte über 200 ms auf der '
             'Liste — der langsamste mit 5.880 ms. Nach dem Durchgang war keiner '
             'mehr über 250 ms; die Antwort einer Einstellungsseite schrumpfte '
             'von 4,7 MB auf 28 KB.')
    dauer = ('mehrere Minuten — gemessen: 172 s für 188 Routen bei EINEM '
             'Aufruf je Route')
    eingabe = ('laeufe', 'Aufrufe je Route', '3')
    ruft_endpunkte_auf = True

    #: Ab hier gilt eine Route als auffaellig.
    GRENZE_MS = 200
    #: So viele Zeilen werden angezeigt — der Rest steht in der Zusammenfassung.
    ZEILEN = 40

    #: Kein Anlassfall - und das ist in Ordnung:
    ohne_anlassfall_weil = ("fragt den LAUFENDEN Server - "
                            "der Fall ist eine Antwortzeit, keine Datei")

    def pruefen(self, laeufe='3', **_argumente):
        try:
            anzahl = max(1, min(10, int(str(laeufe).strip() or 3)))
        except ValueError:
            anzahl = 3

        import time
        besucher = klient()
        messwerte = []
        for route in alle_routen():
            zeiten, antwort = [], None
            for _ in range(anzahl):
                start = time.perf_counter()
                try:
                    antwort = besucher.get(route.weg)
                except Exception:  # noqa: BLE001 — eine kaputte Route stoppt nicht alles
                    antwort = None
                    break
                zeiten.append((time.perf_counter() - start) * 1000)
            if not zeiten:
                continue
            messwerte.append(Messwert(
                route.weg, min(zeiten), median(zeiten),
                len(getattr(antwort, 'content', b'')),
                getattr(antwort, 'status_code', '—')))

        messwerte.sort(key=lambda m: -m.best_ms)
        auffaellig = [m for m in messwerte if m.best_ms > self.GRENZE_MS]
        befunde = [Befund(m.weg, m.beschreibung(),
                          gewicht=(Befund.FEHLER if m.best_ms > self.GRENZE_MS * 5
                                   else Befund.WARNUNG if m.best_ms > self.GRENZE_MS
                                   else Befund.HINWEIS))
                   for m in messwerte[:self.ZEILEN]]
        kopf = [
            '%d Routen gemessen, %d Aufrufe je Route' % (len(messwerte), anzahl),
            '%d über %d ms' % (len(auffaellig), self.GRENZE_MS),
            'gemessen wird die Serverzeit im selben Prozess — ohne Netz und ohne '
            'Browser; die Antwortgröße zeigt, was zusätzlich uebertragen wird',
        ]
        # Kappung benennen: Eine stillschweigend gekuerzte Liste liest sich wie
        # "mehr gibt es nicht" — und genau so entstehen uebersehene Ausreisser.
        if len(messwerte) > self.ZEILEN:
            kopf.append('angezeigt: die %d langsamsten von %d Routen'
                        % (self.ZEILEN, len(messwerte)))
        return Befundsatz(self.titel, kopf, befunde)
