# -*- coding: utf-8 -*-
u"""JsBefunde - zaehlbare Auffaelligkeiten im Frontend (JavaScript und Vorlagen).

DER BEFUND (3DTools, 16.08.2026)
================================
Ein Auftrag verlangte einen tiefen Review mit einer nachpruefbaren Zahl von
Befunden. Eine Zahl aus dem Bauch ist wertlos - deshalb erhebt dieses Werkzeug
jeden Befund mit Datei, Zeile und Begruendung, gruppiert nach Art. Erste
Erhebung: 3.290 Befunde, davon nach dem Durchgang beseitigt:

    Antwort ohne .ok-Pruefung      71 -> 0   (echte Fehlerklasse)
    console.log im Betrieb        144 -> 0
    var statt let/const           157 -> 0   (alle in Django-Vorlagen)
    setInterval ohne Abbruch        4 -> 0

WOZU DAS TAUGT
==============
Die Zahl je Art ist nach jeder Aenderung neu messbar. Das unterscheidet einen
Review von einem Gefuehl: „1.082 Inline-Stile" ist eine Aufgabe, „viel zu viele
Inline-Stile" ist eine Meinung.

Die Regeln stehen in `jsregeln.py` - eine Klasse je Auffaelligkeit, jede mit dem
Fehlalarm, der beim Bau aufgefallen ist.
"""
from .jsregeln import REGELN
from .anlassfall import Anlassfall
from .werkzeug import Ergebnis, Werkzeug

__all__ = ["JsBefunde"]


class JsBefunde(Werkzeug):
    slug = "jsbefunde"
    titel = "Frontend-Befunde (JS + Vorlagen)"
    zweck = ("Zaehlt zehn objektiv pruefbare Auffaelligkeiten in .js und .html "
             "- fehlende ok-Pruefung, console.log, var, Inline-Stile, lange "
             "Zeilen, TODOs.")
    befund = ("3DTools: 3.290 Befunde erhoben. Die 71 fehlenden .ok-Pruefungen "
              "waren eine echte Fehlerklasse - bei einer 500er-Antwort las der "
              "Code die HTML-Fehlerseite als JSON und meldete "
              "\"Unexpected token '<'\".")
    abhilfe = ("Nach Wirkung abarbeiten: erst fehlende ok-Pruefungen und "
               "Dauerlaeufer, dann console.log und var, zuletzt Inline-Stile "
               "und lange Zeilen.")
    dauer = "1-3 s"
    kriterium = 13

    #: Auch Vorlagen werden geprueft - `style=""` im Markup ist derselbe Befund
    #: wie im JavaScript, und dort steht er meist in groesserer Zahl.
    ENDUNGEN = (".js", ".html")

    #: Mehrere der zehn Auffaelligkeiten auf einmal: ``var``, ``console.log``,
    #: ``fetch`` ohne ok-Pruefung und ein loser Vergleich. Die beiden
    #: Fehlalarm-Fallen stehen bewusst daneben und duerfen NICHT zaehlen:
    #: ``== null`` (die uebliche Pruefung auf null oder undefined) und ``==``
    #: in einem Django-Vorlagen-Tag, wo es die einzige richtige Form ist.
    anlassfall = Anlassfall(
        {"seite.js": '''var alt = 1;

export async function laden(url) {
  console.log('lade', url);
  const d = await fetch(url).then(r => r.json());
  if (d.wert == '3') return d;
  return alt == null ? null : d;
}
''',
         "seite.html": '''{% if job.status == 'complete' %}<b>fertig</b>{% endif %}
'''},
        erwartet_in="var",
        warum="Zehn objektiv prüfbare Auffälligkeiten — mit den zwei "
              "Fehlalarm-Fallen daneben, die vier Regeln erst brauchbar machten")

    def laufen(self):
        gruppen = {}
        dateien = 0
        for pfad in self._quellen():
            dateien += 1
            zeilen = pfad.read_text(encoding="utf-8",
                                    errors="replace").split("\n")
            kurz = pfad.relative_to(self.wurzel()).as_posix()
            ist_html = pfad.suffix == ".html"
            skript = JsBefunde.skriptzeilen(zeilen) if ist_html else set()
            for regel in REGELN:
                funde = regel.pruefen(kurz, zeilen)
                if ist_html and regel.nur_javascript:
                    funde = [f for f in funde if (f.zeile - 1) in skript]
                if funde:
                    gruppen.setdefault(regel.art, []).extend(funde)

        sortiert = sorted(gruppen.items(), key=lambda p: -len(p[1]))
        zeilen_aus = []
        for art, funde in sortiert:
            zeilen_aus.append({"art": "%s (%d)" % (art, len(funde)),
                               "ort": funde[0].datei + ":%d" % funde[0].zeile,
                               "text": funde[0].warum})
            for fund in funde[:JsBefunde.JE_ART]:
                zeilen_aus.append(fund.als_zeile())
        gesamt = sum(len(f) for f in gruppen.values())
        return Ergebnis(
            ["art", "ort", "text"], zeilen_aus,
            zusammenfassung="%d Befunde in %d Arten, %d Dateien geprueft"
                            % (gesamt, len(gruppen), dateien),
            hinweis="Je Art die ersten %d Stellen; die Zahl in Klammern ist die "
                    "vollstaendige." % JsBefunde.JE_ART)

    #: So viele Beispielstellen je Art. Alle waeren mehrere Tausend Zeilen.
    JE_ART = 12

    #: Ausschlussliste und Suche stehen seit dem 17.08.2026 in
    #: ``Frontendquellen`` — vorher hatte sie jedes JS-Werkzeug einzeln,
    #: in vier verschiedenen Fassungen.
    def _quellen(self):
        return self.frontendquellen().pfade(*JsBefunde.ENDUNGEN)

    @staticmethod
    def skriptzeilen(zeilen):
        u"""Zeilennummern (0-basiert) innerhalb von <script>-Bloecken.

        FEHLALARM, der hier behoben ist: Ein Einzeiler wie
        ``<script src="…/three.min.js"></script>`` oeffnete den Block und
        schloss ihn nie - ``<script`` wurde zuerst gefunden und die Zeile
        uebersprungen. Ab dort galt die GANZE Vorlage als JavaScript, und
        ``{% if job.status == 'pending' %}`` erschien als Befund „Vergleich mit
        ==". Deshalb entscheidet die Reihenfolge innerhalb der Zeile.
        """
        drin = set()
        offen = False
        for nummer, zeile in enumerate(zeilen):
            klein = zeile.lower()
            auf = klein.rfind("<script")
            zu = klein.rfind("</script")
            if auf >= 0 or zu >= 0:
                offen = auf > zu
                continue
            if offen:
                drin.add(nummer)
        return drin
