# -*- coding: utf-8 -*-
u"""Seitenzeiten - was jede Seite kostet: Server UND Browser.

DER BEFUND (3DTools, 17.08.2026)
================================
Die Endpunkt-Messung sagte „alles unter 100 ms" — und die Szenenseite brauchte
trotzdem 2,6 Sekunden, bis sie stand: 250 Dateien, 14,8 MB. Darunter Dutzende
Kleider-Vorschaubilder, die der Browser in Sechsergruppen abarbeitet; jedes
einzelne meldet 1,4 s Dauer, weil es 1,3 s davon in der Warteschlange stand.

Eine Messung, die nur den Server fragt, sieht davon nichts. Deshalb misst
dieses Werkzeug ZWEI Dinge:

* **serverseitig** (hier, ueber den Test-Client): Wie lange braucht die Ansicht
  fuer das HTML, und wie gross ist es? Das trifft Datenbankarbeit und
  Vorlagenrendern.
* **im Browser** (Knopf „Im Browser messen" auf der Seite): Wie viele Dateien
  laedt die Seite, wie viele Bytes, wann steht das DOM, wann ist alles da? Das
  trifft alles andere — und das ist meistens mehr.

Die Browser-Messung laedt jede Seite in einem unsichtbaren `<iframe>` und liest
dort die Navigation- und Resource-Timing-Werte. Deshalb braucht sie keinen
externen Dienst und misst genau das, was der Benutzer erlebt.

WELCHE SEITEN: Alle benannten GET-Routen ohne Parameter — Django kennt sie
selbst (`urls`), es wird nichts geraten. Wer eine Seite ausnehmen will:
``DJANGOBASE["skills2_seiten_ausser"] = ["logout", "…"]``.
"""
import time

from django.conf import settings
from django.test import Client, override_settings
from django.urls import get_resolver

from .werkzeug import Ergebnis, Werkzeug2

__all__ = ["Seitenzeiten"]


class Seitenzeiten(Werkzeug2):
    slug = "seitenzeiten"
    titel = "Seiten: Serverzeit und Groesse"
    zweck = ("Ruft jede parameterlose Seite auf und misst Antwortzeit und "
             "HTML-Groesse. Der Knopf „Im Browser messen\" ergaenzt Dateizahl, "
             "Bytes und Ladezeit aus dem Browser.")
    befund = ("3DTools: Alle Endpunkte unter 100 ms — die Szenenseite brauchte "
              "trotzdem 2,6 s und lud 250 Dateien mit 14,8 MB. Serverzeit allein "
              "sagt nichts ueber das, was der Benutzer erlebt.")
    abhilfe = ("Grosse Antworten hinter einen Parameter legen (nur laden, was "
               "gebraucht wird), Vorschaubilder erst beim Aufklappen holen, "
               "Listen paginieren.")
    dauer = "5-30 s (jede Seite wird wirklich aufgerufen)"
    kriterium = 12

    #: So oft wird jede Seite aufgerufen; berichtet wird die BESTZEIT.
    #:
    #: FALLE, im Bau gemessen (17.08.2026): Der erste Aufruf fuellt Caches. Mit
    #: EINEM Lauf meldete das Werkzeug 4.103 ms fuer die Systemstatistik und
    #: 6.215 ms fuer die Versionsseite — ueber HTTP gemessen waren es 7 ms und
    #: 745 ms. Wer solche Zahlen weitergibt, jagt Gespenster.
    LAEUFE = 2
    #: Ab hier gilt eine Seite als langsam.
    GRENZE_MS = 300
    #: Ab hier ist das HTML selbst zu gross.
    GRENZE_KB = 400
    #: Routen mit diesen Namensteilen werden nicht aufgerufen — sie aendern
    #: Daten, melden ab oder gehoeren nicht zur Anwendung.
    AUSSER = ("logout", "delete", "loeschen", "abmelden", "start", "stop",
              "bulk", "reset", "admin/", "__debug__", "media/", "static/")

    def seiten(self):
        u"""Benannte GET-Routen ohne Parameter — von Django selbst erfragt."""
        eigen = (getattr(settings, "DJANGOBASE", {}) or {}).get(
            "skills2_seiten_ausser") or []
        raus = tuple(Seitenzeiten.AUSSER) + tuple(eigen)
        gefunden = []
        for muster in self._alle_muster(get_resolver()):
            weg, name = muster
            if any(teil in (name or "") or teil in weg for teil in raus):
                continue
            if "<" in weg or weg.startswith("api/"):
                continue        # Parameter noetig bzw. keine Seite
            gefunden.append("/" + weg)
        return sorted(set(gefunden))

    def _alle_muster(self, resolver, vorsilbe=""):
        """(Pfad, Name) aller Routen — rekursiv durch die include()-Baeume."""
        for eintrag in resolver.url_patterns:
            weg = vorsilbe + str(getattr(eintrag.pattern, "_route", ""))
            if hasattr(eintrag, "url_patterns"):
                yield from self._alle_muster(eintrag, weg)
            else:
                yield (weg, getattr(eintrag, "name", "") or "")

    def laufen(self):
        u"""Jede Seite einmal aufrufen und Zeit und Groesse festhalten.

        FALLE, die beim Bau zuschlug (17.08.2026): Der Test-Client schickt den
        Host `testserver`. Steht der nicht in `ALLOWED_HOSTS`, antwortet Django
        mit 400 — und die Messung zeigte fuer JEDE Seite 295 KB in 90 ms: die
        Groesse der Fehlerseite. Ein Werkzeug, das immer dieselbe Zahl liefert,
        misst nichts. Deshalb wird der Host fuer den Lauf ergaenzt, und der
        Statuscode steht in der Tabelle — 400 oder 500 faellt damit auf.
        """
        zeilen = []
        erlaubt = list(getattr(settings, 'ALLOWED_HOSTS', [])) + ['testserver']
        with override_settings(ALLOWED_HOSTS=erlaubt):
            zeilen = self._messen()
        zeilen.sort(key=lambda z: -z["ms"])
        langsam = [z for z in zeilen if z["hinweis"]]
        return Ergebnis(
            ["ms", "kb", "status", "seite", "hinweis"], zeilen,
            zusammenfassung="%d Seiten gemessen, %d ueber %d ms oder %d KB"
                            % (len(zeilen), len(langsam), Seitenzeiten.GRENZE_MS,
                               Seitenzeiten.GRENZE_KB),
            hinweis="Das ist die SERVERZEIT. Was der Benutzer erlebt, steht "
                    "erst nach dem Knopf „Im Browser messen“ daneben "
                    "— dort zaehlen Dateizahl und Bytes meist mehr.")

    def _messen(self):
        klient = Client()
        zeilen = []
        for weg in self.seiten():
            zeiten = []
            antwort = None
            try:
                for _ in range(Seitenzeiten.LAEUFE):
                    beginn = time.perf_counter()
                    antwort = klient.get(weg)
                    zeiten.append((time.perf_counter() - beginn) * 1000)
            except Exception as fehler:            # noqa: BLE001
                zeilen.append({"ms": 0, "kb": 0, "status": "Fehler",
                               "seite": weg,
                               "hinweis": type(fehler).__name__})
                continue
            dauer = int(min(zeiten))
            kb = len(antwort.content) // 1024
            hinweise = []
            if dauer >= Seitenzeiten.GRENZE_MS:
                hinweise.append("langsam")
            if kb >= Seitenzeiten.GRENZE_KB:
                hinweise.append("grosses HTML")
            zeilen.append({"ms": dauer, "kb": kb, "status": antwort.status_code,
                           "seite": weg, "hinweis": ", ".join(hinweise)})
        return zeilen
