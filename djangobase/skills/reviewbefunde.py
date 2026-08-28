# -*- coding: utf-8 -*-
u"""ReviewBefunde — die Mitschriften der Review-Seite lesbar machen.

DER ANLASS (28.08.2026, 3DTools)
================================
Im Ablageordner lagen **51 Mitschriften mit 1,8 MB und 38.000 Zeilen** — echte
Antworten eines starken Modells zu vierzig Codebereichen, jede mit Datei- und
Funktionsangabe. Gelesen hatte sie niemand. Zwanzig Lehren waren daraus von
Hand nach `lehren_review` uebernommen worden; der Rest lag als Fliesstext da
und war praktisch unauffindbar.

Eine Mitschrift ist kein Bericht: Sie ist ein Gespraech, und die Befunde
stehen darin verstreut zwischen Rueckfragen und Wiederholungen. Dieses
Werkzeug zieht sie heraus und stellt sie in dieselbe Form wie jeden anderen
Befund — mit Ort, Aussage und Gewicht.

DER FILTER, DER DEN UNTERSCHIED MACHT
=====================================
Reviews altern. Ein Durchgang vom 12.08. nennt `core/character_api.py`, und
diese Datei ist beim Umbau am 15.08. in `core/api/` aufgegangen. Ein solcher
Befund ist nicht falsch — er ist ERLEDIGT, und wer ihn abarbeiten will, sucht
eine Datei, die es nicht mehr gibt.

Deshalb prueft das Werkzeug jede genannte Datei gegen den heutigen Bestand:

    Datei existiert    -> Warnung  (koennte noch gelten)
    Datei ist weg      -> Hinweis  (der Umbau ist darueber hinweggegangen)
    keine Datei genannt-> Hinweis  (allgemeine Anmerkung, nicht nachpruefbar)

Ohne diese Trennung waere die Liste zu einem guten Teil Archaeologie — und
eine Liste, die zur Haelfte aus Erledigtem besteht, arbeitet niemand durch.
"""

import json
import logging
import re
from pathlib import Path

from .anlassfall import Anlassfall
from .befund import Befund, Befundsatz, BefundWerkzeug

logger = logging.getLogger("djangobase")


class Mitschrift:
    u"""Eine Datei aus dem Ablageordner — ein Bereich, ein Modell, N Befunde."""

    #: ``## Runde 1 — Bereich (modell, 12 s)``
    KOPF = re.compile(r"^##\s+Runde\s+(\d+)\s+[—-]\s+(.+?)\s*\((.+?),\s*(\d+)\s*s\)",
                      re.M)

    #: Was das Modell geantwortet hat — davor steht nur die Frage.
    ANTWORT = "### Geantwortet"

    def __init__(self, pfad):
        self.pfad = Path(pfad)
        self.text = self._lesen()
        self.bereich, self.modell, self.sekunden = self._kopfdaten()

    def _lesen(self):
        try:
            return self.pfad.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""

    def _kopfdaten(self):
        treffer = self.KOPF.search(self.text)
        if not treffer:
            # Ohne Kopfzeile bleibt der Dateiname — `review_<id>_<bereich>.md`.
            teile = self.pfad.stem.split("_", 2)
            return (teile[2] if len(teile) > 2 else self.pfad.stem), "", 0
        return treffer.group(2), treffer.group(3), int(treffer.group(4))

    @property
    def attrappe(self):
        u"""Eine Mitschrift aus einem TESTLAUF, kein echter Durchgang.

        In 3DTools lagen 33 davon: Partner ``attrappe``, Antwort ``ok``,
        114 Bytes. Sie entstanden, weil eine Pruefung in den Produktivordner
        schrieb (behoben am 28.08.2026) — melden wuerde man sie nie wollen.

        Gemessen wird die ANTWORT, nicht die Datei: Die Frage enthaelt den
        Quelltext des Bereichs und ist deshalb immer lang. Der erste Wurf
        prueft ``len(self.text) < 400`` — damit fiel der eigene Anlassfall
        durch, und das Werkzeug galt als blind.
        """
        if self.modell == "attrappe":
            return True
        return len("".join(self.antworten()).strip()) < self.MINDESTANTWORT

    #: Kuerzer als das ist keine Antwort, sondern eine Quittung.
    MINDESTANTWORT = 200

    def antworten(self):
        u"""Nur die Antwortteile — die Frage enthaelt den Quelltext selbst."""
        stuecke = self.text.split(self.ANTWORT)[1:]
        return [s.split("\n## ")[0] for s in stuecke]


class Reviewbefund:
    u"""Ein einzelner Befund aus einer Mitschrift."""

    #: ``### 3. Titel`` — die uebliche Gliederung der Antworten.
    NUMMER = re.compile(r"^###\s+(\d+)[.)]\s+(.+?)\s*$", re.M)

    #: ``**Datei: `x.py`, Funktion `y`...**`` — der zweite gebraeuchliche Kopf.
    DATEIKOPF = re.compile(r"^\*\*Datei:\s*(.+?)\*\*\s*$", re.M)

    #: Ein Dateiname in Rueckstrichen: `core/api/kleidung.py`, `retarget.py`
    DATEINAME = re.compile(r"`([\w./\\-]+\.(?:py|js|html|css|json|mjs))`")

    #: ``FUNKTION: `x` `` oder ``Funktion `x` `` — der zweite Anker.
    #:
    #: WARUM ER NOETIG IST (Fehlalarm des eigenen Werkzeugs, 28.08.2026)
    #: ================================================================
    #: Ein Befund nannte `retarget.py` mit `retarget_bvh_to_rigify`. Im
    #: Projekt gibt es `core/api/retarget.py` — 217 Zeilen HTTP-Schale, in der
    #: keine dieser Funktionen steht; die gemeinte Datei liegt in einem
    #: anderen Paket. Der blosse Dateiname hat damit drei Befunde
    #: faelschlich als „betrifft eine Datei, die es noch gibt" gemeldet.
    #:
    #: Nennt ein Befund eine Funktion, muss sie in der gefundenen Datei auch
    #: stehen — sonst ist es Namensgleichheit, keine Fundstelle.
    FUNKTIONSNAME = re.compile(
        r"(?:FUNKTION|Funktion|function|Methode)\s*:?\s*`([\w.]+)`")

    def __init__(self, mitschrift, titel, text):
        self.mitschrift = mitschrift
        self.titel = titel.strip()
        self.text = text
        self.dateien = self._dateien()
        self.funktionen = self._funktionen()

    def _funktionen(self):
        namen = []
        for treffer in self.FUNKTIONSNAME.finditer(self.text[:800]):
            name = treffer.group(1).split(".")[-1]
            if name and name not in namen:
                namen.append(name)
        return namen

    def _dateien(self):
        namen = []
        for treffer in self.DATEINAME.finditer(self.text[:600]):
            name = treffer.group(1).replace("\\", "/")
            if name not in namen:
                namen.append(name)
        return namen

    @staticmethod
    def aus(mitschrift):
        u"""Alle Befunde einer Mitschrift.

        Zwei Gliederungen kommen vor: nummerierte Ueberschriften und
        ``**Datei: …**``-Bloecke. Gesucht wird erst nach der ersten; findet
        sie nichts, gilt die zweite.
        """
        aus = []
        for antwort in mitschrift.antworten():
            stellen = list(Reviewbefund.NUMMER.finditer(antwort))
            if not stellen:
                stellen = list(Reviewbefund.DATEIKOPF.finditer(antwort))
            for nr, stelle in enumerate(stellen):
                ende = (stellen[nr + 1].start() if nr + 1 < len(stellen)
                        else len(antwort))
                titel = stelle.group(stelle.re.groups)
                aus.append(Reviewbefund(mitschrift, titel,
                                        antwort[stelle.start():ende]))
        return aus

    #: Ein Titel, der einen ZURUECKGENOMMENEN Befund ankuendigt.
    #:
    #: Ein gutes Modell widerspricht sich selbst, wenn es in der zweiten Runde
    #: mehr Code sieht. Das ist die wertvollste Zeile der ganzen Mitschrift —
    #: und als Befund gezaehlt waere sie ein Fehlalarm.
    ZURUECKGEZOGEN = re.compile(r"zur[uü]ckgezogen", re.I)

    #: Keine Aussage, sondern eine BITTE um Code. Das Modell sagt es
    #: ausdruecklich („Code fehlt“, „brauche exakt“) — wer daraus einen Befund
    #: macht, stellt eine Frage in die Liste der Antworten.
    RUECKFRAGE = re.compile(r"code fehlt|brauche (exakt|die|den)|"
                            r"nicht (einsehbar|vorhanden|mitgeliefert)", re.I)

    @property
    def taugt(self):
        u"""Ist das ueberhaupt ein Befund?"""
        if self.ZURUECKGEZOGEN.search(self.titel):
            return False
        return not self.RUECKFRAGE.search(self.titel + self.text[:400])

    def gewicht(self, vorhanden):
        u"""Warnung nur, wenn eine genannte Datei es heute noch gibt."""
        if not self.dateien:
            return Befund.HINWEIS
        return Befund.WARNUNG if vorhanden else Befund.HINWEIS

    def hinweis(self, vorhanden):
        wo = ", ".join(self.dateien[:3]) if self.dateien else "keine Datei genannt"
        if not self.dateien:
            return u"Allgemeine Anmerkung — %s" % wo
        if vorhanden:
            return u"Betrifft: %s" % wo
        return (u"%s — die Datei(en) gibt es nicht mehr; der Umbau ist "
                u"darueber hinweggegangen" % wo)


class ReviewBefunde(BefundWerkzeug):

    slug = "review-befunde"
    kriterium = 0
    titel = u"Review-Mitschriften"
    zweck = (u"Zieht die Befunde aus den Mitschriften der Review-Seite heraus "
             u"und prueft, ob die genannten Dateien es heute noch gibt.")
    abhilfe = (u"Nach jedem Review-Durchgang. Eine Mitschrift ist ein "
               u"Gespraech — die Befunde stehen darin verstreut, und nach der "
               u"dritten liest sie niemand mehr durch.")
    befund = (u"Im Ursprungsprojekt lagen 51 Mitschriften mit 1,8 MB und "
              u"38.000 Zeilen im Ablageordner. Zwanzig Lehren waren von Hand "
              u"daraus uebernommen worden, der Rest war unauffindbar.")
    dauer = u"Sekunden"
    eingabe = ("bereich", u"Nur EIN Bereich (leer = alle)", "")

    #: Wo die Mitschriften liegen koennen, relativ zur Projektwurzel.
    ORTE = ("logs/review", "review")

    #: Endungen, die eine Mitschrift nennen kann.
    ENDUNGEN = (".py", ".js", ".html", ".css", ".mjs")

    anlassfall = Anlassfall(
        {"logs/review/review_aaaa_probe.md":
            u"\n## Runde 1 — Probebereich (grossmodell, 12 s)\n\n"
            u"### Gefragt\n\n# Codebereich\n\n### Geantwortet\n\n"
            u"### 1. Ungepruefter Rueckgabewert\n\n"
            u"**Datei: `dienst.py`, Funktion `holen`**\n\n"
            u"Der Aufrufer bekommt `None` und merkt es nicht.\n\n---\n\n"
            u"### 2. Pfadpruefung per Zeichenvergleich\n\n"
            u"In `dienst.py` wird `startswith` benutzt.\n",
         "dienst.py": "def holen():\n    return None\n"},
        mindestens=2, erwartet_in="review_aaaa_probe.md",
        warum=u"Zwei Befunde in einer Mitschrift, beide mit Dateiangabe — "
              u"genau das, was im Fliesstext untergeht")

    def pruefen(self, bereich="", **_argumente):
        gesucht = str(bereich or "").strip().lower()
        vorhandene = self._projektdateien()
        mitschriften = [Mitschrift(p) for p in self._mitschriften()]
        attrappen = [m for m in mitschriften if m.attrappe]
        echte = [m for m in mitschriften if not m.attrappe]

        befunde, erledigt, keine_aussage, geprueft = [], 0, 0, 0
        for m in sorted(echte, key=lambda m: m.pfad.name):
            if gesucht and gesucht not in m.bereich.lower():
                continue
            for treffer in Reviewbefund.aus(m):
                if not treffer.taugt:
                    keine_aussage += 1
                    continue
                ort = "%s | %s" % (m.bereich, treffer.titel[:70])
                urteil = self._pruefbuch().get(treffer.titel[:60])
                if urteil:
                    geprueft += 1
                    befunde.append(Befund(
                        ort, u"%s — nachgeprüft %s"
                        % (m.pfad.name, urteil.get("am", "")),
                        urteil.get("urteil", ""), Befund.HINWEIS))
                    continue
                da = self._gibt_es_noch(treffer, vorhandene)
                if treffer.dateien and not da:
                    erledigt += 1
                befunde.append(Befund(
                    ort, u"%s (%s)" % (m.pfad.name, m.modell or u"unbekannt"),
                    treffer.hinweis(da), treffer.gewicht(da)))

        rang = {Befund.WARNUNG: 0, Befund.HINWEIS: 1}
        befunde.sort(key=lambda b: (rang.get(b.gewicht, 2), b.ort))
        return Befundsatz(self.titel,
                          self._kopf(echte, attrappen, befunde, erledigt,
                                     keine_aussage, geprueft), befunde)

    # ------------------------------------------------------------- Bausteine

    def _kopf(self, echte, attrappen, befunde, erledigt,
              keine_aussage=0, geprueft=0):
        offen = sum(1 for b in befunde if b.gewicht == Befund.WARNUNG)
        kopf = [u"%d Mitschriften, %d Befunde" % (len(echte), len(befunde)),
                u"%d betreffen Dateien, die es noch gibt" % offen]
        if erledigt:
            kopf.append(u"%d nennen Dateien, die der Umbau entfernt hat — "
                        u"erledigt, nicht falsch" % erledigt)
        if geprueft:
            kopf.append(u"%d im Pruefbuch abgehakt (%s)"
                        % (geprueft, self.PRUEFBUCH))
        if keine_aussage:
            kopf.append(u"%d Rueckfragen und zurueckgezogene Punkte — keine "
                        u"Befunde" % keine_aussage)
        if attrappen:
            # Nie verschweigen, was uebergangen wurde.
            kopf.append(u"%d Attrappen aus Testlaeufen uebergangen"
                        % len(attrappen))
        if not echte:
            kopf.append(u"Keine Mitschriften gefunden — gesucht in: %s"
                        % ", ".join(self.ORTE))
        return kopf

    #: Neben den Mitschriften: Welcher Befund schon nachgeprueft wurde.
    #:
    #: WARUM ES DAS BRAUCHT (28.08.2026)
    #: =================================
    #: Von 19 offenen Befunden hielten 17 der Nachpruefung nicht stand — sie
    #: waren laengst behoben oder trafen die heutige Fassung nicht. Diese
    #: Arbeit steckt im Kopf dessen, der sie gemacht hat; beim naechsten Lauf
    #: stuenden dieselben 19 wieder da, und jemand faengt von vorn an.
    #:
    #: Das Pruefbuch haelt das Urteil fest — mit Datum und Begruendung, nicht
    #: als blosses Hakenzeichen. Ein Eintrag OHNE Begruendung ist wertlos:
    #: Man kann ihn nicht nachvollziehen und traut ihm deshalb nicht.
    #:
    #: Form (`geprueft.json` im Ablageordner)::
    #:
    #:     {"Titel des Befunds (erste 60 Zeichen)": {
    #:         "am": "2026-08-28",
    #:         "urteil": "Warum er nicht (mehr) gilt — mit Beleg"}}
    PRUEFBUCH = "geprueft.json"

    _buch = None

    def _pruefbuch(self):
        u"""Das Pruefbuch — einmal je Lauf gelesen."""
        if self._buch is not None:
            return self._buch
        self._buch = {}
        for ort in self.ORTE:
            pfad = Path(self.wurzel()) / ort / self.PRUEFBUCH
            if not pfad.is_file():
                continue
            try:
                self._buch.update(
                    json.loads(pfad.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                # Ein kaputtes Pruefbuch darf den Lauf nicht kosten — dann
                # gilt eben nichts als geprueft, und das faellt sofort auf.
                logger.warning("Pruefbuch %s nicht lesbar", pfad,
                               exc_info=True)
        return self._buch

    def _mitschriften(self):
        u"""Alle ``.md`` in den bekannten Ablageorten."""
        wurzel = Path(self.wurzel())
        aus = []
        for ort in self.ORTE:
            ordner = wurzel / ort
            if ordner.is_dir():
                aus.extend(sorted(ordner.glob("*.md")))
        return aus

    def _projektdateien(self):
        u"""Endstueck -> Pfade. Eine Mitschrift schreibt mal `retarget.py`,
        mal `core/api/retarget.py` — beides muss treffen."""
        namen = {}
        # `projektdateien` nimmt EINE Endung — die Mitschriften nennen aber
        # Python, JavaScript und Vorlagen durcheinander.
        for endung in self.ENDUNGEN:
            for pfad in self.projektdateien(endung):
                teile = Path(str(pfad)).as_posix().split("/")
                for tiefe in range(1, min(4, len(teile)) + 1):
                    namen.setdefault("/".join(teile[-tiefe:]), []).append(pfad)
        return namen

    def _gibt_es_noch(self, befund, vorhandene):
        u"""Gibt es die genannte Stelle heute noch — Datei UND Funktion?

        Der Dateiname allein reicht nicht: `retarget.py` gibt es in fast
        jedem Projekt zweimal. Nennt der Befund eine Funktion, muss sie in
        einer der gefundenen Dateien stehen (siehe `FUNKTIONSNAME`).
        """
        treffer = []
        for name in befund.dateien:
            treffer.extend(vorhandene.get(name)
                           or vorhandene.get(name.split("/")[-1]) or [])
        if not treffer:
            return False
        if not befund.funktionen:
            return True
        return any(self._enthaelt(pfad, befund.funktionen) for pfad in treffer)

    @staticmethod
    def _enthaelt(pfad, namen):
        u"""Steht einer der Namen als Definition in dieser Datei?"""
        try:
            text = Path(str(pfad)).read_text(encoding="utf-8", errors="replace")
        except OSError:
            # Unlesbar heisst „keine Aussage" — dann lieber melden als
            # stillschweigend abtun.
            return True
        return any(re.search(r"\b(?:def|function|class)\s+%s\b" % re.escape(n),
                             text) or ("%s(" % n) in text for n in namen)
