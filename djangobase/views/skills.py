# -*- coding: utf-8 -*-
u"""Hilfe -> Skills: DER Werkzeugkasten.

Die Seite vereint skills2 (Engine) und skills (Import-Graph, Doppelcode über
HTML, tote Importe, Synonyme, Vorlagen-/Endpunkt-Analysen). Die skills-Werkzeuge
laufen über einen Adapter in derselben Tabellen-Welt. Ausgefuehrt wird
server-seitig als Stapel (Auswahl ankreuzen, EIN POST); jeder Lauf hängt seinen
Klartext-Bericht unten an - von dort in eine Sitzung kopierbar.

Sicherheit: Gestartet wird nur, was in der Registry steht - die Kennungen aus der
Anfrage werden dagegen geprüft, nicht ausgefuehrt.
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
                       werkzeuge)
from ..skills.lehren_review import BEREICHE, LEHREN, Lehrenstand
from ..skills.rangliste import (fixerrangliste, lehrenrangliste,
                                rangliste)
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
        if request.POST.get("aktion") == "fixrang":
            # Dieselbe Bauart wie „rang", nur die andere Liste. Getrennt,
            # weil ein Rang die POSITION in SEINER Liste ist: 52 Pruefer und
            # 7 Fixer gemeinsam zu nummerieren hiesse, dass das Verschieben
            # eines Fixers die Nummer eines Pruefers aendert.
            slug = request.POST.get("rang_slug", "")
            ziel = request.POST.get("rang_ziel", "")
            ok = fixerrangliste().verschieben(slug, ziel, list(fixer()))
            return redirect("%s?verschoben=%s#fixer" % (request.path,
                                                        slug if ok else ""))
        if request.POST.get("aktion") == "lehrenrang":
            slug = request.POST.get("rang_slug", "")
            ziel = request.POST.get("rang_ziel", "")
            ok = lehrenrangliste().verschieben(slug, ziel, list(LEHREN))
            return redirect("%s?verschoben=%s#lehren" % (request.path,
                                                         slug if ok else ""))
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
        # Entweder die angehakten Werkzeuge — oder der Knopf in einer
        # Abschnitts-Zeile, der den ganzen Bereich in einem Lauf faehrt.
        #
        # Bis zum 26.08.2026 standen hier zwei weitere Sonderwege
        # (``k1617``, ``k18``) fuer zwei Kaesten unter der Tabelle. Die
        # Kaesten sind weg, der Knopf gilt jetzt fuer JEDEN Bereich.
        gewaehlt = (request.POST.getlist("werkzeug")
                    or self._bereich_slugs(request.POST.get("bereich")))
        gelaufen = self._laufen(gewaehlt, request.POST, bericht)
        return self._seite(request, bericht.text(), gelaufen)

    # --------------------------------------------------------------- Umbau-Netz

    def _netz(self, request):
        """Abnahme vor dem Umbau, Vergleich danach - beides über die Repo-Wurzel.

        Bewusst NICHT auf den Fix-Bereich eingeschraenkt: Wandert eine Funktion
        beim Schnitt in ein Modul außerhalb des Bereichs, muesste sie als
        verschwunden gelten - und das wäre ein Fehlalarm auf genau dem Weg, den
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
            return self._seite(request, "Kein Fixer für '%s'." % escape(slug), [])

        basis = Path(str(settings.BASE_DIR))
        if bereich:
            ziel = (basis / bereich).resolve()
            if ziel != basis and basis not in ziel.parents:
                return self._seite(
                    request, "Bereich '%s' liegt außerhalb des Projekts — abgelehnt."
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
                  "%d geschrieben, %d zurueckgespielt, %d übersprungen."
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

        Der Fehlerfang gehört hierher: Die skills2-Basisklasse hat keinen
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
            "fixtabelle": self._fixtabelle(fix),
            "netz": {"titel": Umbaunetz.titel, "tut": Umbaunetz.tut,
                     "warum": Umbaunetz.warum, "grenzen": Umbaunetz.grenzen},
            "fix": fix,      # nach einer Vorschau: {slug, bereich, n, modus} -> Anwenden-Knopf
            # Die Lehren aus den Code-Reviews - Ankreuzliste mit Auftragstext.
            "lehren_bereiche": self._lehren(),
            "lehrentabelle": self._lehrentabelle(),
            "anzahl_lehren": len(LEHREN),
            "anzahl_aktiv": sum(1 for an in Lehrenstand.laden().values() if an),
        })





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

    @staticmethod
    def _gruppenkopf(nummer, bereich, anzahl):
        u"""Abschnitts-Zeile der Tabelle — mit eigenem Sammellauf-Knopf.

        JEDER ABSCHNITT, NICHT ZWEI AUSGEWAEHLTE (26.08.2026)
        =====================================================
            „ich will keine neuen Bereich ohne tabelle die mit 17 anfangen,
             gliedere diese Bereiche ein in der Art und weise der Tabellen
             wie die vorherigen Bereiche"

        Unter der Tabelle standen zwei Kästen — „Logging & Tests" und
        „Klassen & Zustand" — mit je einem Knopf, der alle Werkzeuge eines
        Kriteriums in einem Lauf fährt. Die zehn Werkzeuge darin standen
        aber laengst in der Tabelle, verteilt auf drei Abschnitte:

            Stille Fehler                    jsstumm, protokoll, schreibrouten
            Objektorientierung und Struktur  klassenreif, globaler-zustand, …
            Tests und Werkzeuge selbst       testaufbau, testdeckung, …

        Zwei Darstellungen derselben Sache also, und die zweite fing mit
        „17." und „18." an — als wären es neue Bereiche. Das waren sie nie.

        Der Knopf war das einzig Eigene daran. Er sitzt jetzt in der
        Abschnitts-Zeile und gilt für ALLE Abschnitte, nicht für zwei
        ausgewählte.
        """
        return (
            '<b>%s</b> <span class="sk1-leise">%s</span>'
            '<button type="submit" name="bereich" value="%d" formnovalidate'
            ' class="sk1-knopf" style="float:right;"'
            ' title="Alle %d Werkzeuge dieses Bereichs in einem Lauf">'
            '<i class="bi bi-play-circle"></i> Bereich prüfen</button>'
            % (escape(bereich["name"]), escape(bereich["warum"]),
               nummer, anzahl))

    @classmethod
    def _bereich_slugs(cls, nummer):
        u"""Die Werkzeuge EINES Abschnitts — für den Knopf in seiner Zeile."""
        try:
            nummer = int(nummer)
        except (TypeError, ValueError):
            return []
        abschnitte = rangliste().abschnitte(list(werkzeuge()))
        if not 0 <= nummer < len(abschnitte):
            return []
        return [w.slug for _rang, w in abschnitte[nummer]["eintraege"]]

    def _tabelle(self, gelaufen):
        """Struktur für djangobase/_tabelle.html. Die Zellen enthalten die
        Formularfelder; die Tabelle steht innerhalb des Formulars."""
        zeilen = []
        rang = rangliste()
        alle = list(werkzeuge())
        # NACH BEREICHEN GEGLIEDERT (25.08.2026). Vorher eine Liste von 50
        # Eintraegen in Kriteriums-Reihenfolge - man sah nicht, was zusammen
        # gehoert. Die Abschnittszeile kann _tabelle.html von sich aus
        # (``gruppe``), es musste nichts an der Vorlage geaendert werden.
        for nummer, abschnitt in enumerate(rang.abschnitte(alle)):
            eintraege = abschnitt["eintraege"]
            if not eintraege:
                continue
            b = abschnitt["bereich"]
            zeilen.append({"gruppe": True, "zellen": [
                {"html": self._gruppenkopf(nummer, b, len(eintraege)),
                 "colspan": 6}]})
            for nr, w in eintraege:
                zeilen.append(self._zeile(w, nr, gelaufen))
        return self._rahmen(zeilen)

    def _zeile(self, w, nr, gelaufen):
        u"""Eine Werkzeug-Zeile. Herausgeloest, weil _tabelle sonst über
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

    # ------------------------------------------------------ Fix-Werkzeuge

    def _fixtabelle(self, fix):
        u"""Die Fix-Werkzeuge in derselben Tabelle wie die Prüfer.

            „ordne den Bereich Fix-Werkzeuge · schreiben Code — Diff-Vorschau
             zuerst auch in einer tabelle, mit veraenderbaren nummern"

        Vorher war es eine Liste von ``sk1-fixzeile``-Bloecken: keine
        Nummer, keine Sortierung, keine Spalten. Dieselbe Sorte Sonderfall
        wie die zwei Kästen, die heute schon weggefallen sind — was
        nebeneinander gehört, gehört in dieselbe Tabelle.

        Der Anwenden-Knopf erscheint NUR für den Fixer, dessen Vorschau
        gerade gelaufen ist und etwas gefunden hat. Ein Knopf, der ohne
        Vorschau schreibt, wäre die Falle, gegen die es die Vorschau gibt.
        """
        rang = fixerrangliste()
        alle = list(fixer())
        folge = rang.reihenfolge(alle)
        da = {f.slug: f for f in alle}
        zeilen = []
        for nr, slug in enumerate(folge, start=1):
            f = da.get(slug)
            if f is not None:
                zeilen.append(self._fixzeile(f, nr, fix))
        return {
            "key": "db-fixer",
            "spalten": [
                {"label": "Rang", "key": "rang", "sortAus": True,
                 "titel": "Eindeutige Nummer. Aendern verschiebt den Eintrag."},
                {"label": "Fix-Werkzeug", "key": "name"},
                {"label": "Behebt", "key": "behebt",
                 "titel": "Die Prüfung, deren Befund dieser Fixer behebt"},
                {"label": "Was es tut", "key": "zweck"},
                {"label": "Grenzen", "key": "grenzen"},
                {"label": "Aktion", "key": "start", "sortAus": True},
            ],
            "zeilen": zeilen,
            "leer": "kein Fixer registriert",
        }

    def _fixzeile(self, f, nr, fix):
        d = f.als_dict()
        p = d.get("pruefung")
        behebt = ('Nr. %d<span class="sk1-dauer">%s</span>'
                  % (p["nr"], escape(p["titel"]))) if p else \
            '<span class="sk1-leise">—</span>'
        offen = (fix and fix.get("modus") == "vorschau"
                 and fix.get("slug") == f.slug and fix.get("n"))
        knoepfe = ('<button type="submit" name="fix" value="vorschau:%s"'
                   ' class="sk1-knopf" formnovalidate>'
                   '<i class="bi bi-search"></i> Vorschau</button>'
                   % escape(f.slug))
        if offen:
            knoepfe += ('<button type="submit" name="fix" value="anwenden:%s"'
                        ' class="sk1-batch" formnovalidate>'
                        '<i class="bi bi-check2-circle"></i> Anwenden (%s)'
                        '</button>' % (escape(f.slug), escape(str(fix["n"]))))
        return {
            "klasse": "db-hervor" if offen else "",
            "zellen": [
                {"html": ('<input type="number" name="rang_ziel" value="%d"'
                          ' min="1" max="999" class="sk1-rang"'
                          ' aria-label="Rang">'
                          '<button type="submit" name="aktion" value="fixrang"'
                          ' class="sk1-rang-los" formnovalidate'
                          ' title="Auf diese Nummer verschieben">'
                          '<i class="bi bi-arrow-right-short"></i></button>'
                          '<input type="hidden" name="rang_slug" value="%s">'
                          % (nr, escape(f.slug))),
                 "sort": nr, "klasse": "sk1-mitte"},
                {"html": ('<span class="sk1-name">%s</span>'
                          '<span class="sk1-dauer">%s</span>'
                          % (escape(f.titel), escape(d["dauer"]))),
                 "sort": f.titel},
                {"html": behebt, "sort": p["nr"] if p else 999},
                {"html": escape(d["tut"])},
                {"html": '<span class="sk1-leise">%s</span>'
                         % escape(d["grenzen"])},
                {"html": knoepfe, "klasse": "sk1-mitte"},
            ],
        }

    # ------------------------------------------------------------- Lehren

    def _lehrentabelle(self):
        u"""Die Lehren in derselben Tabelle wie Prüfer und Fixer.

            „mach die Lehren auch in einer veraenderbaren Tabelle mit
             veraenderbaren Nummern"

        Vorher eine Liste von ``sk-lehre``-Bloecken, nach Bereichen
        gruppiert: kein Rang, keine Sortierung, keine Spalten. Der Bereich
        geht dabei nicht verloren — er wird eine SPALTE und lässt sich
        damit sogar sortieren, was er als Zwischenueberschrift nicht
        konnte.

        Das Haekchen bleibt, was es war: „gilt für dieses Projekt".
        """
        stand = Lehrenstand.laden()
        rang = lehrenrangliste()
        alle = list(LEHREN)
        da = {l.slug: l for l in alle}
        zeilen = []
        for nr, slug in enumerate(rang.reihenfolge(alle), start=1):
            lehre = da.get(slug)
            if lehre is not None:
                zeilen.append(self._lehrezeile(lehre, nr,
                                               stand.get(slug, True)))
        return {
            "key": "db-lehren",
            "spalten": [
                {"label": ('<input type="checkbox" id="sk-lehre-alle"'
                           ' title="Alle aus- oder abwaehlen">'),
                 "key": "wahl", "sortAus": True},
                {"label": "Rang", "key": "rang", "sortAus": True,
                 "titel": "Eindeutige Nummer. Aendern verschiebt den Eintrag."},
                {"label": "Bereich", "key": "bereich"},
                {"label": "Lehre", "key": "name"},
                {"label": "Regel und Begründung", "key": "regel"},
                {"label": "Prüfung", "key": "pruefung",
                 "titel": "Welches Werkzeug hält diese Regel?"},
            ],
            "zeilen": zeilen,
            "leer": "keine Lehren hinterlegt",
        }

    @staticmethod
    def _lehrezeile(lehre, nr, an):
        nummern = lehre.nummern()
        if nummern:
            pruefung = ' · '.join('Nr. %d<span class="sk1-dauer">%s</span>'
                                  % (r, escape(titel))
                                  for r, titel in nummern)
        else:
            # KEINE PRUEFUNG IST EINE AUSSAGE, keine fehlende Angabe: Diese
            # Regel haengt allein an der Sorgfalt dessen, der schreibt.
            pruefung = ('<span class="sk1-leise">keine — diese Regel prüft '
                        'kein Werkzeug</span>')
        text = '<span class="sk1-fixtut">%s</span>' % escape(lehre.regel)
        text += ('<span class="sk1-dauer"><b>Warum:</b> %s</span>'
                 % escape(lehre.warum))
        if lehre.beleg:
            text += ('<span class="sk1-dauer"><b>Beleg:</b> %s</span>'
                     % escape(lehre.beleg))
        return {
            "klasse": "" if an else "db-aus",
            "zellen": [
                {"html": ('<input type="checkbox" name="lehre" value="%s"'
                          ' class="sk-lehre-wahl"%s>'
                          % (escape(lehre.slug), " checked" if an else "")),
                 "sort": 1 if an else 0, "klasse": "sk1-mitte"},
                {"html": ('<input type="number" name="rang_ziel" value="%d"'
                          ' min="1" max="999" class="sk1-rang"'
                          ' aria-label="Rang">'
                          '<button type="submit" name="aktion"'
                          ' value="lehrenrang" class="sk1-rang-los"'
                          ' formnovalidate title="Auf diese Nummer'
                          ' verschieben">'
                          '<i class="bi bi-arrow-right-short"></i></button>'
                          '<input type="hidden" name="rang_slug" value="%s">'
                          % (nr, escape(lehre.slug))),
                 "sort": nr, "klasse": "sk1-mitte"},
                {"html": escape(lehre.bereich), "sort": lehre.bereich},
                {"html": '<span class="sk1-name">%s</span>' % escape(lehre.titel),
                 "sort": lehre.titel},
                {"html": text},
                {"html": pruefung,
                 "sort": nummern[0][0] if nummern else 999},
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
