# -*- coding: utf-8 -*-
u"""Hilfe -> Skills: DER Werkzeugkasten.

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
from django.http import HttpResponse
from django.shortcuts import redirect, render
from django.utils.html import escape
from django.views import View

from ..mixins import ZugriffMixin
from ..skills import (Bericht, Umbaunetz, fixer, fixer_finden,
                       kriterien, werkzeuge)
from ..skills.lehren_review import BEREICHE, LEHREN, Lehrenstand
from ..skills.rangliste import rangliste
from ..skills.werkzeug import Ergebnis


class SkillsView(ZugriffMixin, View):

    def get(self, request):
        # Deep-Link `?run=<slug>` faehrt ein einzelnes Werkzeug.
        bericht = Bericht()
        gelaufen = []
        slug = request.GET.get("run", "")
        if slug:
            gelaufen = self._laufen([slug], request.GET, bericht)
        if request.GET.get("auftrag") == "1":
            # Als Textdatei: Der Auftragstext wird kopiert, nicht gelesen.
            return HttpResponse(Lehrenstand.auftragstext(),
                                content_type="text/plain; charset=utf-8")
        return self._seite(request, bericht.text(), gelaufen)

    def post(self, request):
        # Fix-Aktion ("modus:slug") laeuft getrennt vom Detektor-Stapel.
        if request.POST.get("fix"):
            return self._fix(request)
        if request.POST.get("netz"):
            return self._netz(request)
        if request.POST.get("aktion") == "rang":
            # EIN Eintrag je Absenden. Anders als bei einer Zuordnung lassen
            # sich Ränge nicht stapelweise setzen: Jede Verschiebung ändert die
            # Nummern der anderen, zwei Wünsche zugleich widersprechen sich
            # („A auf 3" und „B auf 3"). Der Knopf steht deshalb in der Zeile.
            slug = request.POST.get("rang_slug", "")
            ziel = request.POST.get("rang_ziel", "")
            ok = rangliste().verschieben(slug, ziel, list(werkzeuge()))
            return redirect("%s?verschoben=%s" % (request.path, slug if ok else ""))
        if request.POST.get("aktion") == "lehren":
            # Die Ankreuzliste der Review-Lehren (bis 18.08.2026 auf der
            # eigenen Seite „Skills3"). Sie gehoert hierher: Es ist derselbe
            # Werkzeugkasten, und drei Seiten mit ueberlappendem Inhalt sind
            # kein Werkzeugkasten, sondern drei halbe.
            Lehrenstand.speichern(set(request.POST.getlist("lehre")))
            return redirect(request.path + "#lehren")
        # Die Textbox schickt ihren bisherigen Inhalt mit und bekommt ihn
        # ergaenzt zurueck - so haengt ein zweiter Lauf an, statt zu ueberschreiben.
        bericht = Bericht(request.POST.get("ausgabe", ""))
        # „Logging + Tests pruefen": der Sammellauf ueber die Kriterien 16/17.
        # Eigener Knopf statt eines weiteren Hakens in der Tabelle - es ist die
        # Frage, die man am Ende eines Umbaus stellt, nicht zwischendurch.
        gewaehlt = (request.POST.getlist("werkzeug")
                    or (self._k1617_slugs() if request.POST.get("k1617") else [])
                    # Kriterium 18 (19.08.2026): derselbe Gedanke wie 16/17 -
                    # eine Frage, die man am Ende eines Umbaus stellt.
                    or (self._k18_slugs() if request.POST.get("k18") else []))
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
        return render(request, "djangobase/hilfe/skills.html", {
            "aktiv": "skills",
            "tabelle": self._tabelle(gelaufen),
            "ausgabe": ausgabetext,
            "anzahl_werkzeuge": len(werkzeuge()),
            # Die Fixer aus skills2 (Sicherung + Netz) plus die hiesigen.
            "fixer_da": [f.als_dict() for f in fixer()],
            "netz": {"titel": Umbaunetz.titel, "tut": Umbaunetz.tut,
                     "warum": Umbaunetz.warum, "grenzen": Umbaunetz.grenzen},
            # Kriterium 16/17 als eigener Sammellauf.
            "k1617": [{"titel": w.titel, "zweck": w.zweck,
                       "kriterium": getattr(w, "kriterium", 0)}
                      for w in self._zu_kriterien(16, 17)],
            "k1617_texte": [(nr, kriterien()[nr]) for nr in (16, 17)],
            # Kriterium 18: Klassen und Zustand - eigener Sammellauf.
            "k18": [{"titel": w.titel, "zweck": w.zweck, "slug": w.slug}
                    for w in self._k18_werkzeuge()],
            "k18_text": kriterien().get(18, ""),
            "fix": fix,      # nach einer Vorschau: {slug, bereich, n, modus} -> Anwenden-Knopf
            # Die Lehren aus den Code-Reviews - Ankreuzliste mit Auftragstext.
            "lehren_bereiche": self._lehren(),
            "anzahl_lehren": len(LEHREN),
            "anzahl_aktiv": sum(1 for an in Lehrenstand.laden().values() if an),
        })

    @staticmethod
    def _zu_kriterien(*nummern):
        u"""Die Werkzeuge zu diesen Kriterien — aus der Registrierung.

        WARUM ABGELEITET (19.08.2026): Der Block fuer 16/17 fuehrte seine
        Werkzeuge als feste Liste. Als Kriterium 18 dazukam, erschien es
        deshalb NIRGENDS auf der Seite — die Werkzeuge liefen, aber der
        Auftrag, zu dem sie gehoeren, stand nicht da.

        DERSELBE FEHLER STECKTE NOCH IM BLOCK 16/17 (26.08.2026)
        ========================================================
            „warum ist Logging & Tests auf /hilfe/skills/ noch anders, mit
             anderen Nummern usw?"

        Er lief ueber ``EIGENE`` — drei von Hand eingetragene Werkzeuge.
        Nachgemessen trugen aber FUENF das Kriterium 16 oder 17::

            Kr 16  jsstumm          Stille Rueckmeldung        FEHLTE
            Kr 16  schreibrouten    Ansicht schreibt auf GET    FEHLTE
            Kr 16  protokoll        Logging                     dabei
            Kr 17  testaufbau       Tests gegliedert            dabei
            Kr 17  testdeckung      Tests: was hat gar keinen?  dabei

        Zwei Werkzeuge liefen also nie mit, wenn jemand „Logging & Tests
        pruefen" drueckte — und niemand sah es, weil die Karte ihre eigene
        Liste zeigte statt der Registrierung.

        Jetzt fragt BEIDES dieselbe Stelle: Ein neues Werkzeug mit
        ``kriterium = 16`` steht ohne Zutun im Block und laeuft im
        Sammellauf mit.
        """
        gesucht = set(nummern)
        return [w for w in werkzeuge()
                if getattr(w, "kriterium", 0) in gesucht]

    @classmethod
    def _k18_werkzeuge(cls):
        return cls._zu_kriterien(18)

    @classmethod
    def _k18_slugs(cls):
        return [w.slug for w in cls._k18_werkzeuge()]

    @classmethod
    def _k1617_slugs(cls):
        return [w.slug for w in cls._zu_kriterien(16, 17)]

    @staticmethod
    def _lehren():
        u"""Die Lehren je Bereich, mit ihrem Ankreuzstand."""
        # `BEREICHE` sind Zeichenketten, keine Objekte - der erste Wurf las
        # `bereich.slug` und flog mit AttributeError (18.08.2026).
        stand = Lehrenstand.laden()
        aus = []
        for bereich in BEREICHE:
            eintraege = [{"lehre": l, "an": stand.get(l.slug, True)}
                         for l in LEHREN if l.bereich == bereich]
            if eintraege:
                # Dictionary gewollt: geht unveraendert in die Vorlage.
                aus.append({"name": bereich, "lehren": eintraege,
                            "anzahl": len(eintraege)})
        return aus

    def _tabelle(self, gelaufen):
        """Struktur fuer djangobase/_tabelle.html. Die Zellen enthalten die
        Formularfelder; die Tabelle steht innerhalb des Formulars."""
        zeilen = []
        rang = rangliste()
        alle = list(werkzeuge())
        # NACH BEREICHEN GEGLIEDERT (25.08.2026). Vorher eine Liste von 50
        # Eintraegen in Kriteriums-Reihenfolge - man sah nicht, was zusammen
        # gehoert. Die Abschnittszeile kann _tabelle.html von sich aus
        # (``gruppe``), es musste nichts an der Vorlage geaendert werden.
        for abschnitt in rang.abschnitte(alle):
            eintraege = abschnitt["eintraege"]
            if not eintraege:
                continue
            b = abschnitt["bereich"]
            zeilen.append({"gruppe": True, "zellen": [
                {"html": '<b>%s</b> <span class="sk1-leise">%s</span>'
                         % (escape(b["name"]), escape(b["warum"])),
                 "colspan": 6}]})
            for nr, w in eintraege:
                zeilen.append(self._zeile(w, nr, gelaufen))
        return self._rahmen(zeilen)

    def _zeile(self, w, nr, gelaufen):
        u"""Eine Werkzeug-Zeile. Herausgeloest, weil _tabelle sonst ueber
        300 Zeilen ginge und zwei Dinge zugleich taete."""
        return {
            "klasse": "db-hervor" if w.slug in gelaufen else "",
            "zellen": [
                {"html": ('<input type="checkbox" name="werkzeug" value="%s"'
                          ' class="sk1-wahl"%s>'
                          % (escape(w.slug),
                             " checked" if w.slug in gelaufen else "")),
                 "sort": 1 if w.slug in gelaufen else 0, "klasse": "sk1-mitte"},
                # DER RANG - eindeutig, und aendern verschiebt (Ansage
                # 25.08.2026). Der Knopf steht IN der Zeile, nicht oben am
                # Stapel: Jede Verschiebung aendert die Nummern der anderen,
                # zwei Wuensche zugleich widersprechen sich.
                #
                # ``formnovalidate`` am Knopf, damit die Zahlenfelder der
                # anderen Zeilen keine Pflichtpruefung ausloesen - sie gehoeren
                # zum selben Formular wie der Stapellauf.
                {"html": ('<input type="number" name="rang_ziel" value="%d"'
                          ' min="1" max="999" class="sk1-rang"'
                          ' aria-label="Rang">'
                          '<button type="submit" name="aktion" value="rang"'
                          ' class="sk1-rang-los" formnovalidate'
                          ' title="Auf diese Nummer verschieben">'
                          '<i class="bi bi-arrow-right-short"></i></button>'
                          '<input type="hidden" name="rang_slug" value="%s">'
                          % (nr, escape(w.slug))),
                 "sort": nr, "klasse": "sk1-mitte"},
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
        }

    def _rahmen(self, zeilen):
        u"""Kopf und Rumpf der Tabelle - getrennt vom Zeilenbau, damit
        keine der beiden Methoden zwei Dinge zugleich tut."""
        # Dictionary gewollt: das ist die Eingabestruktur von _tabelle.html.
        return {
            "key": "db-skills",
            "spalten": [
                {"label": ('<input type="checkbox" id="sk1-alle" '
                           'title="Alle aus- oder abwählen">'),
                 "key": "wahl", "sortAus": True},
                # RANG STATT KRITERIUMS-NUMMER (25.08.2026, Ansage Edgar:
                # „mach nur die neuen Bereiche, die alten brauche ich nicht
                # mehr"). Hier stand die Nummer des Auftrags-Kriteriums (1-18),
                # die sich mehrere Werkzeuge teilten. Jetzt eine EINDEUTIGE
                # Nummer je Eintrag: Wer sie ändert, verschiebt den Eintrag,
                # und die anderen rutschen nach.
                #
                # Das Kriterium ist damit nicht abgeschafft - es steht weiter
                # am Werkzeug und ordnet es seinem Bereich zu. Es wird nur
                # nicht mehr angezeigt und nicht mehr von Hand gepflegt.
                {"label": "Rang", "key": "rang", "sortAus": True,
                 "titel": "Eindeutige Nummer. Ändern verschiebt den Eintrag."},
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
