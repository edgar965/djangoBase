# -*- coding: utf-8 -*-
u"""Die Reihenfolge der Werkzeuge - eine eindeutige Nummer je Eintrag.

DER AUFTRAG (25.08.2026, Edgar)
===============================
    „mach Nummern für jeden Testcase, nicht mehr als eine Nummer pro testcase.
     wenn die Nummer eines Testcases verändert wird, dann rutscht er in den
     neuen Bereich, die anderen Nummern ändern sich"
    „Die Nummern nach wichtigkeit, vielleicht können wir die Tabelle in
     Bereiche aufteilen … Trotzdem eine eindeutige Nummer pro Testcase"

RANG UND KRITERIUM SIND ZWEI VERSCHIEDENE DINGE
===============================================
Die naheliegende Lösung wäre gewesen, die vorhandene Kriteriums-Nummer zur
Rangfolge zu machen. Das hätte etwas zerstört, das gerade erst gebaut wurde:
Die Kriteriums-Nummer ist die VERBINDUNG zwischen einer Prüfung und den
Werkzeugen, die ihren Befund beheben - Ebene 2 in ``werkzeugwahl.py``. Wird
sie zur Rangfolge, ist diese Verbindung weg.

    kriterium   WOFÜR das Werkzeug zuständig ist   (1-18, mehrere teilen sie)
    rang        WO es in der Liste steht           (1..N, eindeutig)

WIE DER BEREICH ENTSTEHT
========================
Nicht als eigenes Feld. Der Bereich ergibt sich aus dem RANG: Die Liste ist in
Abschnitte geteilt, und wer eine Nummer ändert, wandert in den Abschnitt, zu
dem sie gehört. Genau das war die Ansage - die Nummer bestimmt den Bereich,
nicht umgekehrt.

Die GRUNDORDNUNG (bevor jemand etwas verschiebt) kommt aus dem Kriterium:
Jedes Kriterium gehört zu einem Bereich, und innerhalb des Bereichs entscheiden
Kriterium und Name. Damit steht die Liste vom ersten Tag an sinnvoll da, ohne
dass jemand fünfzig Nummern vergeben muss.

WARUM DIE ABLAGE EINE LISTE IST UND KEINE ZUORDNUNG
===================================================
``{slug: rang}`` wäre der erste Gedanke und wäre falsch: Beim Verschieben eines
Eintrags ändern sich alle Nummern dazwischen. Eine Zuordnung müsste dafür jedes
Mal neu durchnummeriert und vollständig geschrieben werden - und beim kleinsten
Fehler stünden zwei Werkzeuge auf derselben Nummer.

Gespeichert wird deshalb die REIHENFOLGE selbst (eine Liste von Kennungen). Der
Rang ist dann die Position darin, und er ist zwangsläufig eindeutig. Werkzeuge,
die nicht in der Liste stehen - neu hinzugekommene -, hängen sich an ihrer
Stelle in der Grundordnung ein.
"""
import json
import logging
import os
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

__all__ = ["BEREICHE", "Rangliste", "rangliste"]

#: Die Abschnitte der Liste, in der Reihenfolge ihrer Wichtigkeit.
#:
#: ``kriterien`` sagt, welche Auftrags-Kriterien in diesen Bereich gehören -
#: daraus entsteht die Grundordnung. ``warum`` steht als Erklärung über dem
#: Abschnitt; ohne sie wäre die Reihenfolge eine Behauptung.
BEREICHE = (
    {"name": "Stille Fehler", "kriterien": (13, 16),
     "warum": "Fehler, die niemand sieht: kein Absturz, keine Meldung, nur ein "
              "falsches Ergebnis. Die teuerste Klasse, weil sie erst auffällt, "
              "wenn jemand ihr Ergebnis glaubt."},
    {"name": "Toter und doppelter Code", "kriterien": (5, 6, 7),
     "warum": "Verdeckt die echten Befunde. Zwei Fassungen derselben Sache "
              "laufen auseinander, und nichts meldet es."},
    {"name": "Objektorientierung und Struktur", "kriterien": (1, 2, 4, 9, 10, 11, 18),
     "warum": "Kriterium 1 und 2 des Auftrags: Funktionen in Klassen, eine "
              "Klasse je Datei, 200-300 Zeilen."},
    {"name": "Frontend und ES-Module", "kriterien": (3, 15),
     "warum": "Fehler im Browser bleiben still - die Seite lädt mit 200, die "
              "Konsole schweigt, die Funktion tut nichts."},
    {"name": "Geschwindigkeit", "kriterien": (12,),
     "warum": "Wichtig, aber nachrangig: Ein langsames Programm liefert "
              "richtige Ergebnisse, ein falsches nicht."},
    {"name": "Tests und Werkzeuge selbst", "kriterien": (17,),
     "warum": "Was die Prüfer prüft. Nie dringend und deshalb der Bereich, der "
              "als erster liegen bleibt."},
    # BDD OHNE GHERKIN — EIN EIGENER BEREICH (26.08.2026)
    # ==================================================
    #     „Mach auch einen neuen Abschnitt (meinetwegen BDD) der genau das
    #      überprüft"
    #
    # Er steht ABSICHTLICH ganz hinten und damit als letzter Bereich auch
    # dort, wo `bereich_von()` alles Unbekannte hinsortiert. Das passt: Ein
    # Werkzeug ohne Kriterium ist selbst ein Fall für diesen Bereich — es
    # sagt nicht, wozu es da ist.
    {"name": "Abnahme und Beispiele (BDD)", "kriterien": (19,),
     "warum": "Nicht Gherkin, sondern die drei Zusicherungen dahinter: jede "
              "Regel hat ein Beispiel, jede Seite eine Abnahme, jeder "
              "Prüfungsname nennt das erwartete Verhalten. Gemessen waren "
              "88 % der Prüfungen schon so benannt — was fehlte, waren die "
              "Lücken."},
)


class Rangliste:
    u"""Die Reihenfolge der Werkzeuge - lesen, verschieben, in Bereiche teilen."""

    def __init__(self, pfad):
        self.pfad = Path(pfad)
        self._zwischen = None

    # ------------------------------------------------------- Grundordnung
    @staticmethod
    def bereich_von(kriterium):
        u"""Index des Bereichs, in den dieses Kriterium gehört.

        Unbekannte und fehlende Kriterien landen im LETZTEN Bereich, nicht im
        ersten: Ein Werkzeug ohne Zuordnung soll nicht ungefragt ganz oben
        stehen - „unbekannt" ist kein Grund für Vorrang.
        """
        for n, b in enumerate(BEREICHE):
            if kriterium in b["kriterien"]:
                return n
        return len(BEREICHE) - 1

    @classmethod
    def grundordnung(cls, werkzeuge):
        u"""Die Reihenfolge, bevor jemand etwas verschiebt.

        Bereich, dann Kriterium, dann Name - der Name zuletzt, damit zwei Läufe
        dieselbe Liste ergeben. Ohne ihn stünde die Tabelle bei jedem Neustart
        anders da, und niemand könnte sagen, ob sich etwas geändert hat.
        """
        return [w.slug for w in sorted(
            werkzeuge,
            key=lambda w: (cls.bereich_von(getattr(w, "kriterium", 0) or 0),
                           getattr(w, "kriterium", 0) or 99,
                           getattr(w, "slug", "")))]

    # ---------------------------------------------------------------- lesen
    def gespeichert(self):
        u"""Die abgelegte Reihenfolge als Liste von Kennungen - oder leer."""
        if self._zwischen is not None:
            return self._zwischen
        self._zwischen = []
        if self.pfad.exists():
            try:
                roh = json.loads(self.pfad.read_text(encoding="utf-8") or "[]")
                self._zwischen = [str(x) for x in roh] if isinstance(roh, list) else []
            except (ValueError, TypeError, OSError) as e:
                logger.warning("Rangliste %s nicht lesbar: %s", self.pfad, e)
        return self._zwischen

    def reihenfolge(self, werkzeuge):
        u"""Die gültige Reihenfolge: Ablage, ergänzt um alles Neue.

        Drei Fälle, und alle drei kommen vor:

          * In der Ablage UND vorhanden  -> dort, wo die Ablage es hinstellt.
          * Vorhanden, aber nicht in der Ablage (neues Werkzeug) -> an seiner
            Stelle in der Grundordnung, nicht hinten angehängt. Sonst sammeln
            sich neue Werkzeuge am Listenende, wo sie niemand sucht.
          * In der Ablage, aber nicht mehr vorhanden -> fällt weg. Ein
            umbenanntes Werkzeug soll die Liste nicht mit Leichen füllen.
        """
        da = {w.slug: w for w in werkzeuge}
        grund = self.grundordnung(werkzeuge)
        aus = [s for s in self.gespeichert() if s in da]
        fehlend = [s for s in grund if s not in aus]
        for s in fehlend:
            # An die Stelle setzen, die es in der Grundordnung hat: hinter dem
            # letzten Nachbarn, der schon in der Liste steht.
            vorher = [x for x in grund[:grund.index(s)] if x in aus]
            pos = aus.index(vorher[-1]) + 1 if vorher else 0
            aus.insert(pos, s)
        return aus

    def rang_von(self, slug, werkzeuge):
        u"""Die angezeigte Nummer (ab 1) - oder 0, wenn unbekannt."""
        folge = self.reihenfolge(werkzeuge)
        return folge.index(slug) + 1 if slug in folge else 0

    def grenzen(self, werkzeuge):
        u"""Wie viele Ränge jeder Bereich umfasst - aus der GRUNDORDNUNG.

        Die Größe eines Bereichs steht fest: So viele Werkzeuge ordnet ihm die
        Kriterien-Zuordnung im Code zu. Verschieben ändert daran NICHTS - es
        ändert nur, WER in welchem Abschnitt steht.

        Das ist der Kern der Ansage vom 25.08.2026: „wenn die Nummer eines
        Testcases verändert wird, dann rutscht er in den neuen Bereich". Wer
        ein Werkzeug auf Rang 1 setzt, will es unter „Stille Fehler" sehen -
        nicht auf Rang 1 innerhalb seines alten Abschnitts.

        Der Preis ist der ehrliche Teil davon: Der Bereich hat danach einen
        Eintrag mehr, ein anderer einen weniger. Das LETZTE Werkzeug des
        Bereichs rutscht hinaus. Ein Bereich, der beliebig wachsen kann, wäre
        keine Rangfolge mehr, sondern wieder eine Kategorie.
        """
        grund = self.grundordnung(werkzeuge)
        krit = {w.slug: (getattr(w, "kriterium", 0) or 0) for w in werkzeuge}
        groessen = [0] * len(BEREICHE)
        for slug in grund:
            groessen[self.bereich_von(krit.get(slug, 0))] += 1
        aus, start = [], 1
        for n, g in enumerate(groessen):
            aus.append((n, start, start + g - 1))
            start += g
        return aus

    def abschnitte(self, werkzeuge):
        u"""Die Liste in Bereiche geteilt, wie sie angezeigt wird.

        Der Bereich kommt aus der POSITION, nicht aus dem Kriterium: Rang 1 bis
        5 ist „Stille Fehler", egal welches Werkzeug dort steht. Erst dadurch
        verschiebt eine geänderte Nummer den Eintrag wirklich in einen anderen
        Abschnitt.

        Liste von ``{"bereich": {...}, "eintraege": [(rang, werkzeug), ...]}``.
        """
        da = {w.slug: w for w in werkzeuge}
        folge = self.reihenfolge(werkzeuge)
        aus = [{"bereich": b, "eintraege": []} for b in BEREICHE]
        for n, (idx, von, bis) in enumerate(self.grenzen(werkzeuge)):
            for rang in range(von, bis + 1):
                if rang <= len(folge):
                    w = da.get(folge[rang - 1])
                    if w is not None:
                        aus[idx]["eintraege"].append((rang, w))
        return aus


    # -------------------------------------------------------------- ändern
    def verschieben(self, slug, ziel, werkzeuge):
        u"""Einen Eintrag auf Rang ``ziel`` setzen - die anderen rutschen.

        Genau das war die Ansage: „die anderen Nummern ändern sich". Entfernen
        und an der Zielstelle wieder einsetzen; alles dazwischen verschiebt sich
        um eins. Es gibt danach keine doppelte und keine übersprungene Nummer,
        weil der Rang die POSITION ist und nicht ein gespeicherter Wert.
        """
        folge = self.reihenfolge(werkzeuge)
        if slug not in folge:
            return False
        try:
            ziel = int(ziel)
        except (TypeError, ValueError):
            return False
        # Auf die Liste begrenzen: Ein Ziel von 0 oder 999 ist ein Vertipper,
        # kein Wunsch nach einer Lücke.
        ziel = max(1, min(ziel, len(folge)))
        if folge.index(slug) + 1 == ziel:
            return False
        folge.remove(slug)
        folge.insert(ziel - 1, slug)
        return self._schreiben(folge, werkzeuge)

    def _schreiben(self, folge, werkzeuge):
        u"""Erst in eine Nebendatei, dann umbenennen.

        Entspricht die Reihenfolge wieder der Grundordnung, wird die Datei
        GELÖSCHT statt geschrieben: Eine Ablage, die nur wiederholt, was der
        Code ohnehin sagt, würde spätere Änderungen an der Grundordnung
        stilllegen, ohne dass jemand den Zusammenhang sieht.
        """
        try:
            if folge == self.grundordnung(werkzeuge):
                if self.pfad.exists():
                    self.pfad.unlink()
                self._zwischen = []
                return True
            self.pfad.parent.mkdir(parents=True, exist_ok=True)
            fd, tmp = tempfile.mkstemp(dir=str(self.pfad.parent),
                                       prefix="." + self.pfad.name + ".",
                                       suffix=".tmp")
            with os.fdopen(fd, "w", encoding="utf-8") as f:
                json.dump(folge, f, ensure_ascii=False, indent=2)
            os.replace(tmp, str(self.pfad))
            self._zwischen = folge
            return True
        except OSError as e:
            logger.warning("Rangliste %s nicht schreibbar: %s", self.pfad, e)
            return False


def rangliste():
    u"""Die Rangliste dieses Projekts (Pfad aus der Konfiguration)."""
    from ..conf import conf
    c = conf()
    return Rangliste(c.get("skills_rang_datei")
                     or (c["log_verzeichnis"] / "skills_rang.json"))


class Lehrenrangliste(Rangliste):
    u"""Rangliste für die Lehren — mit der ERKLAERTEN Reihenfolge als Grund.

    `Rangliste.grundordnung` sortiert nach Bereich, Kriterium und Kennung.
    Für Werkzeuge stimmt das; für die Lehren nicht: Sie haben kein
    Kriterium, und nach Kennung sortiert stünde `aequivalenz-beweisen`
    vor `bincount-statt-add-at` — eine Reihenfolge nach Alphabet, die
    niemand so gemeint hat.

    Die Grundordnung ist deshalb die Reihenfolge, in der sie in
    ``lehren_review.py`` stehen: nach Bereichen gruppiert und innerhalb
    davon so, wie sie beim Review entstanden sind. Wer verschiebt,
    überschreibt das — aber der Ausgangspunkt ist nicht das Alphabet.
    """

    @classmethod
    def grundordnung(cls, werkzeuge):
        return [getattr(w, "slug", "") for w in werkzeuge]


def lehrenrangliste():
    u"""Die Rangliste der Lehren — dritte Ablage neben Pruefern und Fixern.

        „mach die Lehren auch in einer veraenderbaren Tabelle mit
         veraenderbaren Nummern" (26.08.2026)

    Eigene Datei aus demselben Grund wie bei den Fixern: Ein Rang ist die
    Position in SEINER Liste. Drei Listen, drei Ablagen, eine Klasse.
    """
    from ..conf import conf
    c = conf()
    return Lehrenrangliste(c.get("lehren_rang_datei")
                           or (c["log_verzeichnis"] / "lehren_rang.json"))


def fixerrangliste():
    u"""Die Rangliste der FIX-Werkzeuge — eigene Ablage, gleiche Klasse.

        „ordne den Bereich Fix-Werkzeuge auch in einer tabelle, mit
         veraenderbaren nummern" (26.08.2026)

    Getrennt von den Pruef-Werkzeugen, weil es zwei Listen sind: Ein Rang
    ist die POSITION in seiner Liste, und 52 Prüfer und 7 Fixer in einer
    Nummerierung zu führen hiesse, dass das Verschieben eines Fixers die
    Nummer eines Pruefers ändert.

    Dieselbe Klasse, nur ein anderer Pfad — der ganze Umgang mit
    Reihenfolge, Verschieben und neuen Einträgen steht damit an EINER
    Stelle.
    """
    from ..conf import conf
    c = conf()
    return Rangliste(c.get("fixer_rang_datei")
                     or (c["log_verzeichnis"] / "fixer_rang.json"))
