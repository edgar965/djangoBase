# -*- coding: utf-8 -*-
u"""Hilfe -> Skills1: beide Werkzeugkaesten unter einem Dach.

Die Seite vereint skills2 (Engine) und skills (Import-Graph, Doppelcode ueber
HTML, tote Importe, Synonyme, Vorlagen-/Endpunkt-Analysen). Die skills-Werkzeuge
laufen ueber einen Adapter in derselben Tabellen-Welt. Ausgefuehrt wird
server-seitig als Stapel (Auswahl ankreuzen, EIN POST); jeder Lauf haengt seinen
Klartext-Bericht unten an - von dort in eine Sitzung kopierbar.

Sicherheit: Gestartet wird nur, was in der Registry steht - die Kennungen aus der
Anfrage werden dagegen geprueft, nicht ausgefuehrt.
"""
import time
from datetime import datetime
from pathlib import Path

from django.conf import settings
from django.shortcuts import render
from django.utils.html import escape
from django.views import View

from ..mixins import ZugriffMixin
from ..skills1 import (EIGENE, Bericht, Umbaunetz, fixer, fixer_finden,
                       kriterien, werkzeuge)
from ..skills2.werkzeug import Ergebnis


class Skills1View(ZugriffMixin, View):

    def get(self, request):
        # Deep-Link `?run=<slug>` faehrt ein einzelnes Werkzeug.
        bericht = Bericht()
        gelaufen = []
        slug = request.GET.get("run", "")
        if slug:
            gelaufen = self._laufen([slug], request.GET, bericht)
        return self._seite(request, bericht.text(), gelaufen)

    def post(self, request):
        # Fix-Aktion ("modus:slug") laeuft getrennt vom Detektor-Stapel.
        if request.POST.get("fix"):
            return self._fix(request)
        if request.POST.get("netz"):
            return self._netz(request)
        # Die Textbox schickt ihren bisherigen Inhalt mit und bekommt ihn
        # ergaenzt zurueck - so haengt ein zweiter Lauf an, statt zu ueberschreiben.
        bericht = Bericht(request.POST.get("ausgabe", ""))
        # „Logging + Tests pruefen": der Sammellauf ueber die Kriterien 16/17.
        # Eigener Knopf statt eines weiteren Hakens in der Tabelle - es ist die
        # Frage, die man am Ende eines Umbaus stellt, nicht zwischendurch.
        gewaehlt = (request.POST.getlist("werkzeug")
                    or ([k.slug for k in EIGENE] if request.POST.get("k1617") else []))
        gelaufen = self._laufen(gewaehlt, request.POST, bericht)
        return self._seite(request, bericht.text(), gelaufen)

    # --------------------------------------------------------------- Umbau-Netz

    def _netz(self, request):
        """Abnahme vor dem Umbau, Vergleich danach - beides ueber die Repo-Wurzel.

        Bewusst NICHT auf den Fix-Bereich eingeschraenkt: Wandert eine Funktion
        beim Schnitt in ein Modul ausserhalb des Bereichs, muesste sie als
        verschwunden gelten - und das waere ein Fehlalarm auf genau dem Weg, den
        ein Umbau nimmt."""
        netz = Umbaunetz()
        wurzel = Path(str(settings.BASE_DIR))
        try:
            if request.POST.get("netz") == "abnehmen":
                text = netz.abnehmen(wurzel)
            else:
                text, _befunde = netz.vergleichen(wurzel)
        except Exception as e:                                    # noqa: BLE001
            text = "FEHLER im Umbau-Netz: %s: %s" % (type(e).__name__, e)
        return self._seite(request, text, [])

    # -------------------------------------------------------------------- Fixen

    def _fix(self, request):
        """Einen Fixer fahren. ``fix`` traegt "vorschau:slug" oder "anwenden:slug".

        Die Fixer stehen auf der skills2-Basis: ``vorschau()`` schreibt nie,
        ``anwenden()`` sichert jede Datei vorher und spielt sie zurueck, wenn das
        Netz (``pruefen``) faellt. Der Bereich schraenkt die Wurzel auf einen
        Unterordner ein und muss INNERHALB des Projekts liegen (kein ``..``)."""
        modus, _, slug = request.POST.get("fix", "").partition(":")
        bereich = (request.POST.get("fix_bereich") or "").strip().strip("/\\")
        fixer = fixer_finden(slug)
        if fixer is None:
            return self._seite(request, "Kein Fixer fuer '%s'." % escape(slug), [])

        basis = Path(str(settings.BASE_DIR))
        if bereich:
            ziel = (basis / bereich).resolve()
            if ziel != basis and basis not in ziel.parents:
                return self._seite(
                    request, "Bereich '%s' liegt ausserhalb des Projekts — abgelehnt."
                    % bereich, [], fix={"slug": slug, "bereich": bereich,
                                        "n": 0, "modus": "vorschau"})
            # Die Fixer leiten ihre Wurzel selbst ab; fuer den Bereichslauf wird
            # sie auf den Unterordner festgenagelt. Die Sicherung haengt daran -
            # sie landet damit unter <bereich>/werkzeug/sicherung/fixer.
            fixer.wurzel = lambda _ziel=ziel: _ziel

        try:
            if modus == "anwenden":
                erg = fixer.anwenden()
                n = len(erg["geschrieben"])
                text = self._fix_bericht(fixer, erg)
            else:
                modus = "vorschau"
                v = fixer.vorschau()
                n = len(v.machbar)
                text = self._fix_vorschau(fixer, v)
        except Exception as e:                                    # noqa: BLE001
            return self._seite(request, "FEHLER beim Fixen: %s: %s"
                               % (type(e).__name__, e), [])
        return self._seite(request, text, [],
                           fix={"slug": slug, "bereich": bereich, "n": n, "modus": modus})

    @staticmethod
    def _fix_vorschau(fixer, v):
        zeilen = ["VORSCHAU: %s" % fixer.titel, v.als_dict()["zusammenfassung"],
                  "Nichts geschrieben — unten 'Anwenden' druecken.", ""]
        for a in v.aenderungen:
            zeilen.append("  %-52s %s%s"
                          % (a.name, a.was,
                             "" if a.machbar else "  [BLOCKIERT: %s]"
                             % "; ".join(a.warnungen)))
        if v.hinweis:
            zeilen += ["", v.hinweis]
        return "\n".join(zeilen)

    @staticmethod
    def _fix_bericht(fixer, erg):
        zeilen = ["ANGEWENDET: %s" % fixer.titel,
                  "%d geschrieben, %d zurueckgespielt, %d uebersprungen."
                  % (len(erg["geschrieben"]), len(erg["zurueckgespielt"]),
                     len(erg["uebersprungen"])), ""]
        for e in erg["geschrieben"]:
            zeilen.append("  OK          %-46s Sicherung: %s"
                          % (e["datei"], e["sicherung"]))
        for e in erg["zurueckgespielt"]:
            # Das Netz hat gehalten: geschrieben, geprueft, verworfen.
            zeilen.append("  ZURUECK     %-46s %s" % (e["datei"], e["grund"]))
        for e in erg["uebersprungen"]:
            zeilen.append("  UEBERSPRUNG %-46s %s" % (e["datei"], e["grund"]))
        zeilen += ["", "Rueckgaengig: die Originale liegen im Sicherungsordner "
                       "(oben je Datei genannt), sonst git checkout -- <datei>."]
        return "\n".join(zeilen)

    # ------------------------------------------------------------------ intern

    def _laufen(self, slugs, daten, bericht):
        """Die gewaehlten Werkzeuge in Registry-Reihenfolge ausfuehren."""
        gewaehlt = [w for w in werkzeuge() if w.slug in set(slugs)]
        for w in gewaehlt:
            argumente = {}
            eingabe = getattr(w, "eingabe", None)
            if eingabe:
                feld = eingabe[0]
                argumente[feld] = (daten.get("arg_%s" % w.slug)
                                   or daten.get(feld) or eingabe[2])
            erg, dauer = self._ausfuehren(w, argumente)
            bericht.anhaengen(w, erg, dauer,
                              datetime.now().strftime("%d.%m.%Y %H:%M:%S"))
        return [w.slug for w in gewaehlt]

    @staticmethod
    def _ausfuehren(werkzeug, argumente):
        """Ein Werkzeug fahren, Fehler abfangen, Wall-Zeit messen.

        Der Fehlerfang gehoert hierher: Die skills2-Basisklasse hat keinen
        Wrapper (dort faengt die Einzel-View ab), und ein Stapel darf nicht an
        EINEM kaputten Werkzeug abbrechen. Werkzeuge ohne Eingabefeld werden
        ohne Argumente gerufen - die skills2-Werkzeuge nehmen keine."""
        t0 = time.perf_counter()
        try:
            erg = werkzeug.laufen(**argumente) if argumente else werkzeug.laufen()
        except Exception as e:                                    # noqa: BLE001
            erg = Ergebnis([], [], "", "FEHLER: %s: %s" % (type(e).__name__, e))
        return erg, round(time.perf_counter() - t0, 2)

    def _seite(self, request, ausgabetext, gelaufen, fix=None):
        return render(request, "djangobase/hilfe/skills1.html", {
            "aktiv": "skills1",
            "tabelle": self._tabelle(gelaufen),
            "ausgabe": ausgabetext,
            "anzahl_werkzeuge": len(werkzeuge()),
            # Die Fixer aus skills2 (Sicherung + Netz) plus die hiesigen.
            "fixer_da": [f.als_dict() for f in fixer()],
            "netz": {"titel": Umbaunetz.titel, "tut": Umbaunetz.tut,
                     "warum": Umbaunetz.warum, "grenzen": Umbaunetz.grenzen},
            # Kriterium 16/17 als eigener Sammellauf.
            "k1617": [{"titel": k.titel, "zweck": k.zweck, "kriterium": k.kriterium}
                      for k in EIGENE],
            "k1617_texte": [(nr, kriterien()[nr]) for nr in (16, 17)],
            "fix": fix,      # nach einer Vorschau: {slug, bereich, n, modus} -> Anwenden-Knopf
        })

    def _tabelle(self, gelaufen):
        """Struktur fuer djangobase/_tabelle.html. Die Zellen enthalten die
        Formularfelder; die Tabelle steht innerhalb des Formulars."""
        zeilen = []
        for w in werkzeuge():
            krit = getattr(w, "kriterium", 0)
            zeilen.append({
                "klasse": "db-hervor" if w.slug in gelaufen else "",
                "zellen": [
                    {"html": ('<input type="checkbox" name="werkzeug" value="%s"'
                              ' class="sk1-wahl"%s>'
                              % (escape(w.slug),
                                 " checked" if w.slug in gelaufen else "")),
                     "sort": 1 if w.slug in gelaufen else 0, "klasse": "sk1-mitte"},
                    {"html": (str(krit) if krit else "—"), "sort": krit,
                     "klasse": "sk1-mitte", "titel": kriterien().get(krit, "")},
                    {"html": ('<span class="sk1-name">%s</span>'
                              '<span class="sk1-dauer">%s</span>%s'
                              % (escape(w.titel), escape(w.dauer),
                                 ('<span class="sk1-ruft">ruft Endpunkte auf</span>'
                                  if getattr(w, "ruft_endpunkte_auf", False) else ""))),
                     "sort": w.titel},
                    {"html": escape(w.zweck)},
                    {"html": self._eingabefeld(w), "klasse": "sk1-mitte"},
                    {"html": ('<button type="submit" name="werkzeug" value="%s"'
                              ' class="sk1-run"><i class="bi bi-play-fill"></i>'
                              ' Start</button>' % escape(w.slug)),
                     "klasse": "sk1-mitte"},
                ],
            })
        # Dictionary gewollt: das ist die Eingabestruktur von _tabelle.html.
        return {
            "key": "db-skills1",
            "spalten": [
                {"label": ('<input type="checkbox" id="sk1-alle" '
                           'title="Alle aus- oder abwählen">'),
                 "key": "wahl", "sortAus": True},
                {"label": "Nr.", "key": "nr", "titel": "Nummer des Auftrags-Kriteriums"},
                {"label": "Werkzeug", "key": "name"},
                {"label": "Was es tut", "key": "zweck"},
                {"label": "Vorgabe", "key": "eingabe", "sortAus": True,
                 "titel": "Zusatzangabe für dieses Werkzeug"},
                {"label": "Start", "key": "start", "sortAus": True},
            ],
            "zeilen": zeilen,
            "leer": "keine Werkzeuge registriert",
        }

    @staticmethod
    def _eingabefeld(w):
        eingabe = getattr(w, "eingabe", None)
        if not eingabe:
            return '<span class="sk1-leise">—</span>'
        _feld, beschriftung, vorgabe = eingabe
        return ('<input type="text" name="arg_%s" value="%s" size="8" '
                'title="%s" class="sk1-arg">'
                % (escape(w.slug), escape(vorgabe), escape(beschriftung)))
