# -*- coding: utf-8 -*-
u"""Stilnamen - ein Klassenname, der zweierlei bedeutet.

DER FALL, GEMESSEN (29.08.2026, 3DTools)
========================================
Ein Umsteller hat Inline-Stile in Klassen ueberfuehrt und die Klassen nach
ihrer ERSTEN Angabe benannt: ``style="margin-top: 20px; color: #4fc1ff"`` wurde
``.hb-margin-top-20px``. Zwei Elemente mit demselben ersten Wert und
verschiedenem Rest bekamen damit denselben Namen — und die Datei zwei Regeln
dazu:

    .hb-margin-top-20px { margin-top: 20px; color: #4fc1ff; }   /* 3x */
    .hb-margin-top-20px { margin-top: 20px; color: #ff9940; }   /* 2x */

Der Browser wendet BEIDE an; bei gleichem Merkmal gewinnt die spaetere, bei
verschiedenen addieren sie sich. Ergebnis: Drei Ueberschriften der Rigging-
Hilfe waren seit dem 16.08.2026 orange statt blau, vier Kaesten der
Theatre-Hilfe hatten den falschen Randstreifen, zwei Knopfleisten einen
Abstand, den nie jemand wollte.

Nichts davon wirft, nichts steht im Log, kein Test wird rot. Die Seite sieht
nicht kaputt aus — sie sieht anders aus.

ZWEI SCHWEREGRADE, und der Unterschied ist wichtig
==================================================
* **In DERSELBEN Datei** zweimal derselbe Name mit verschiedenem Rumpf: Das
  wirkt sofort, auf dieser Seite, heute. -> Fehler.
* In VERSCHIEDENEN Dateien: Solange beide in ihrem eigenen ``<style>``-Block
  stehen, tut es nicht weh. Es ist eine Falle fuer den naechsten, der einen
  dieser Bloecke in eine gemeinsame Datei zieht — dann gilt ploetzlich eine
  Fassung fuer alle. -> Hinweis.

WAS NICHT GEMELDET WIRD
=======================
Gruppen-Auswahlausdruecke (``.a, .b { … }``). Dort gibt EIN Rumpf an mehrere
Namen, und derselbe Name steht absichtlich in mehreren Gruppen; zusammen
ergeben sie den Stil. Das ist kein Streit, sondern Aufteilung — und wer es
dafuer haelt, nimmt beim Aufraeumen einem Element die Haelfte seines Stils.
Genau das ist beim ersten Anlauf dieser Pruefung passiert.
"""
import re
from collections import defaultdict

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

__all__ = ["Stilnamen"]


class Stilnamen(BefundWerkzeug):
    slug = "stilnamen"
    titel = u"Ein Klassenname, zwei Regeln"
    zweck = (u"Sucht Klassennamen, die in einer Vorlage (oder über Vorlagen "
             u"hinweg) mit VERSCHIEDENEN Regeln belegt sind.")
    befund = (u"3DTools: Ein Umsteller benannte erzeugte Klassen nach ihrer "
              u"ersten Angabe. Fünf Vorlagen trugen denselben Namen zweimal "
              u"mit verschiedenem Rumpf — drei Überschriften waren zwei Wochen "
              u"lang orange statt blau, ohne dass etwas rot wurde.")
    abhilfe = (u"Den Namen je Fassung eindeutig machen. Welche Verwendung zu "
               u"welcher Fassung gehört, steht in der Fassung VOR dem "
               u"Umstellen — dort trug jedes Element seinen Stil selbst.")
    dauer = "unter 1 s"
    kriterium = 12

    REGEL = re.compile(r"([^{}]+)\{([^{}]*)\}")
    STIL = re.compile(r"<style>(.*?)</style>", re.S)

    #: Nur erzeugte Klassen: ein einzelner Name, moeglicherweise vervielfacht
    #: (``.x.x.x`` — so erzwingt der Umsteller seine Spezifitaet).
    EINZELNAME = re.compile(r"^\.([A-Za-z][\w-]*)(?:\.\1)*$")

    anlassfall = Anlassfall(
        dateien={
            "seite.html": (
                "<style>\n"
                ".hb-margin-top-20px { margin-top: 20px; color: #4fc1ff; }\n"
                ".hb-margin-top-20px { margin-top: 20px; color: #ff9940; }\n"
                ".hb-gruppe, .hb-andere { background: #111; }\n"
                ".hb-gruppe, .hb-dritte { padding: 4px; }\n"
                "</style>\n"
                '<h3 class="hb-margin-top-20px">Eins</h3>\n'),
        },
        mindestens=1, hoechstens=1,
        erwartet_in="seite.html",
        warum=(u"Der echte Fall und die Gruppen-Schreibweise sehen gleich aus: "
               u"beide Male steht derselbe Name an zwei Regeln. Wer die Gruppe "
               u"nicht ausnimmt, meldet jede aufgeteilte Regel — und wer sie "
               u"dann 'aufräumt', nimmt dem Element die halbe Gestalt."))

    @staticmethod
    def _ist_erzeugt(name, rumpf):
        u"""Traegt der Name seine eigene erste Angabe im Namen?

        So arbeiten die Umsteller: ``margin-top: 20px`` wird
        ``…-margin-top-20px``, ``color: #4fc1ff`` wird ``…-color-4fc1ff``.
        Ein handgeschriebener Name wie ``panel-tab`` tut das nie — und genau
        der soll hier nicht gemeldet werden, denn dass eine Seitenkomponente
        auf jeder Seite anders aussieht, ist ihr Zweck.
        """
        erste = rumpf.split(";")[0]
        if ":" not in erste:
            return False
        merkmal, wert = erste.split(":", 1)
        teile = re.sub(r"[^a-z0-9]+", "-",
                       ("%s-%s" % (merkmal, wert)).lower()).strip("-")
        return bool(teile) and name.lower().endswith(teile)

    def _regeln(self, text):
        u"""[(Name, Rumpf)] — nur Einzelnamen, Gruppen bleiben draussen."""
        aus = []
        gruppennamen = set()
        for block in Stilnamen.STIL.finditer(text):
            for r in Stilnamen.REGEL.finditer(block.group(1)):
                wahl = " ".join(r.group(1).split()).split("*/")[-1].strip()
                rumpf = " ".join(r.group(2).split())
                if "," in wahl:
                    for teil in wahl.split(","):
                        treffer = Stilnamen.EINZELNAME.match(teil.strip())
                        if treffer:
                            gruppennamen.add(treffer.group(1))
                    continue
                treffer = Stilnamen.EINZELNAME.match(wahl)
                if treffer:
                    aus.append((treffer.group(1), rumpf))
        return [(n, r) for n, r in aus if n not in gruppennamen]

    def pruefen(self, **argumente):
        befunde = []
        dateien = self.pfade("*.html")
        ueber_dateien = defaultdict(lambda: defaultdict(set))
        for pfad in dateien:
            text = pfad.read_text(encoding="utf-8", errors="replace")
            in_datei = defaultdict(set)
            for name, rumpf in self._regeln(text):
                in_datei[name].add(rumpf)
                ueber_dateien[name][rumpf].add(self.kurz(pfad))
            for name, saetze in sorted(in_datei.items()):
                if len(saetze) < 2:
                    continue
                befunde.append(Befund(
                    self.kurz(pfad),
                    u"`.%s` steht %d× mit verschiedenem Inhalt"
                    % (name, len(saetze)),
                    u"Beide Regeln gelten — bei gleichem Merkmal gewinnt die "
                    u"spätere, sonst addieren sie sich",
                    Befund.FEHLER))

        for name, fassungen in sorted(ueber_dateien.items()):
            if len(fassungen) < 2:
                continue
            if not any(self._ist_erzeugt(name, r) for r in fassungen):
                continue
            orte = sorted({o for s in fassungen.values() for o in s})
            if len(orte) < 2:
                continue                       # schon oben als Fehler gemeldet
            befunde.append(Befund(
                orte[0],
                u"`.%s` bedeutet in %d Vorlagen %d Verschiedenes"
                % (name, len(orte), len(fassungen)),
                u"auch: %s — wer einen dieser Blöcke in eine gemeinsame Datei "
                u"zieht, gibt allen dieselbe Fassung" % ", ".join(orte[1:4]),
                Befund.HINWEIS))

        return Befundsatz(
            self.titel,
            kopf=["%d Vorlagen geprüft" % len(dateien)],
            befunde=befunde)
