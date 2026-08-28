# -*- coding: utf-8 -*-
u"""`review-befunde`: Was aus 1,8 MB Mitschrift herauskommt — und was nicht.

DER ANLASS (28.08.2026, 3DTools)
================================
Im Ablageordner lagen 51 Mitschriften mit 38.000 Zeilen: echte Antworten eines
starken Modells zu vierzig Codebereichen. Gelesen hatte sie niemand — zwanzig
Lehren waren von Hand uebernommen worden, der Rest lag als Fliesstext da.

DREI FRAGEN, DIE HIER FESTGENAGELT WERDEN
=========================================
1. Werden die Befunde ueberhaupt gefunden? Zwei Gliederungen kommen vor
   (``### 3. Titel`` und ``**Datei: …**``), und nur eine zu koennen hiesse,
   ein Drittel zu uebersehen.
2. Wird ERLEDIGTES als solches erkannt? Ein Review vom 12.08. nennt
   `core/character_api.py` — die Datei ist beim Umbau am 15.08. aufgegangen.
   Ohne diese Trennung besteht die Liste zur Haelfte aus Archaeologie.
3. Fallen die Attrappen raus? In 3DTools lagen 33 Mitschriften aus
   Testlaeufen im Produktivordner (114 Bytes, Antwort „ok").

Der dritte Punkt hat schon einmal zugeschlagen: Der erste Wurf mass die
DATEIlaenge (``< 400``) statt der Antwortlaenge. Die Frage enthaelt aber den
Quelltext des Bereichs und ist immer lang — der eigene Anlassfall fiel durch,
und das Werkzeug galt als blind.
"""

import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.skills.befund import Befund
from djangobase.skills.reviewbefunde import Mitschrift, Reviewbefund, ReviewBefunde


def _mitschrift(bereich, modell, antwort, sekunden=12):
    return (u"\n## Runde 1 — %s (%s, %d s)\n\n### Gefragt\n\n"
            u"# Codebereich\n\n### Geantwortet\n\n%s\n"
            % (bereich, modell, sekunden, antwort))


NUMMERIERT = _mitschrift(u"Probebereich", u"grossmodell", u"""
### 1. Ungepruefter Rueckgabewert

**Datei: `dienst.py`, Funktion `holen`**

Der Aufrufer bekommt `None` und merkt es nicht. Das faellt erst auf, wenn
die Seite leer bleibt — ohne Fehlermeldung, ohne Logeintrag.

---

### 2. Pfadpruefung per Zeichenvergleich

In `dienst.py` wird `startswith` benutzt, wo `is_relative_to` gehoert.
""")

DATEIKOEPFE = _mitschrift(u"Zweiter", u"grossmodell", u"""
**Datei: `alt_und_weg.py`, Funktion `rechnen`**

Die Schleife laeuft quadratisch ueber alle Punkte, und die Zahl der Punkte
waechst mit der Aufloesung des Netzes.

---

**Datei: `dienst.py`, Funktion `schreiben`**

Der Schreibvorgang hat kein `finally`; bricht er ab, bleibt die halbe Datei
liegen und der naechste Lauf liest sie als vollstaendig.
""")

ATTRAPPE = _mitschrift(u"Bereich A", u"attrappe", u"ok", sekunden=0)


class _Werkzeug(ReviewBefunde):
    u"""Ein `ReviewBefunde`, das in einem Wegwerf-Verzeichnis sucht."""

    def __init__(self, ordner):
        super().__init__()
        self._ordner = Path(ordner)

    def wurzel(self):
        return self._ordner

    def projektdateien(self, endung=".py", ausser=None):
        return sorted(p for p in self._ordner.rglob("*" + endung)
                      if "review" not in p.parts)

    def kurz(self, datei):
        return Path(datei).name


def _lauf(mitschriften, dateien=(), **argumente):
    with tempfile.TemporaryDirectory(prefix="djb-reviewbefunde-") as ordner:
        ablage = Path(ordner) / "logs" / "review"
        ablage.mkdir(parents=True)
        for name, inhalt in mitschriften.items():
            (ablage / name).write_text(inhalt, encoding="utf-8")
        for name in dateien:
            # MIT den Funktionen, die die Mitschriften nennen: Seit dem
            # 28.08.2026 reicht der Dateiname nicht mehr — nennt ein Befund
            # eine Funktion, muss sie in der Datei auch stehen.
            (Path(ordner) / name).write_text(
                "def holen():\n    return None\n\n\n"
                "def schreiben(wert):\n    return wert\n", encoding="utf-8")
        return _Werkzeug(ordner).pruefen(**argumente)


class BefundeFindenTest(SimpleTestCase):

    def test_nummerierte_ueberschriften(self):
        erg = _lauf({"review_a_probe.md": NUMMERIERT}, ["dienst.py"])
        self.assertEqual(len(erg.befunde), 2, " | ".join(erg.kopf))
        self.assertIn("Ungepruefter", erg.befunde[0].ort
                      + erg.befunde[1].ort)

    def test_dateikoepfe_ohne_nummern(self):
        u"""Die zweite Gliederung — nur sie zu koennen hiesse, ein Drittel
        der Befunde zu uebersehen."""
        erg = _lauf({"review_b_zweiter.md": DATEIKOEPFE}, ["dienst.py"])
        self.assertEqual(len(erg.befunde), 2, " | ".join(erg.kopf))

    def test_bereich_laesst_sich_eingrenzen(self):
        erg = _lauf({"review_a_probe.md": NUMMERIERT,
                     "review_b_zweiter.md": DATEIKOEPFE},
                    ["dienst.py"], bereich="Zweiter")
        self.assertEqual(len(erg.befunde), 2)
        self.assertTrue(all("Zweiter" in b.ort for b in erg.befunde))


class ErledigtesTest(SimpleTestCase):
    u"""Ein Befund zu einer Datei, die es nicht mehr gibt, ist ERLEDIGT."""

    def test_vorhandene_datei_wird_zur_warnung(self):
        erg = _lauf({"review_a_probe.md": NUMMERIERT}, ["dienst.py"])
        self.assertTrue(all(b.gewicht == Befund.WARNUNG for b in erg.befunde),
                        [b.warum for b in erg.befunde])

    def test_verschwundene_datei_wird_zum_hinweis(self):
        u"""DIE GEGENPROBE: Ohne die Datei darf es keine Warnung sein."""
        erg = _lauf({"review_a_probe.md": NUMMERIERT}, [])
        self.assertTrue(all(b.gewicht == Befund.HINWEIS for b in erg.befunde),
                        [b.warum for b in erg.befunde])
        self.assertIn("nicht mehr", erg.befunde[0].warum)

    def test_gleicher_dateiname_andere_datei_zaehlt_nicht(self):
        u"""DER FEHLALARM DES WERKZEUGS SELBST (28.08.2026).

        Ein Befund nannte `retarget.py` mit `retarget_bvh_to_rigify`. Im
        Projekt gibt es eine gleichnamige Datei — 217 Zeilen HTTP-Schale ohne
        eine dieser Funktionen. Der blosse Dateiname meldete drei Befunde
        faelschlich als offen.
        """
        anderswo = _mitschrift(u"Dritter", u"grossmodell", u"""
### 1. Etwas stimmt nicht

**Datei: `dienst.py`, Funktion `gibtesnichtmehr`**

Die Funktion rechnet die Summe ueber alle Punkte, ohne die Gewichte zu
beruecksichtigen. Bei gleichmaessig verteilten Werten faellt das nicht auf;
sobald ein Ausreisser dabei ist, verschiebt sich das Ergebnis sichtbar, und
niemand sieht dem Zahlenwert an, dass er falsch ist.
""")
        erg = _lauf({"review_d_dritter.md": anderswo}, ["dienst.py"])
        self.assertEqual(len(erg.befunde), 1)
        self.assertEqual(erg.befunde[0].gewicht, Befund.HINWEIS,
                         u"`dienst.py` gibt es, `gibtesnichtmehr` nicht — "
                         u"das ist Namensgleichheit, keine Fundstelle")

    def test_die_zahl_steht_in_der_kopfzeile(self):
        erg = _lauf({"review_b_zweiter.md": DATEIKOEPFE}, ["dienst.py"])
        text = " ".join(erg.kopf)
        self.assertIn("erledigt", text,
                      u"Ein Befund zu `alt_und_weg.py` muss als erledigt "
                      u"gezaehlt werden: %s" % text)


class AttrappenTest(SimpleTestCase):
    u"""Mitschriften aus Testlaeufen sind keine Befunde."""

    def test_attrappe_wird_uebergangen(self):
        erg = _lauf({"review_c_a.md": ATTRAPPE}, ["dienst.py"])
        self.assertEqual(erg.befunde, [])
        self.assertIn("Attrappen", " ".join(erg.kopf))

    def test_eine_echte_neben_einer_attrappe(self):
        erg = _lauf({"review_a_probe.md": NUMMERIERT,
                     "review_c_a.md": ATTRAPPE}, ["dienst.py"])
        self.assertEqual(len(erg.befunde), 2)
        self.assertIn("1 Attrappen", " ".join(erg.kopf))

    def test_die_LANGE_frage_macht_keine_echte_daraus(self):
        u"""DER FEHLER VOM ERSTEN WURF, festgenagelt.

        Gemessen wurde die DATEIlaenge. Die Frage enthaelt aber den Quelltext
        des Bereichs und ist deshalb immer lang — eine Attrappe mit langer
        Frage waere damit als echter Durchgang durchgegangen, und umgekehrt
        fiel der eigene Anlassfall durch.
        """
        lang = ATTRAPPE.replace(u"# Codebereich",
                                u"# Codebereich\n\n" + "x = 1\n" * 400)
        self.assertGreater(len(lang), 2000)
        erg = _lauf({"review_c_a.md": lang}, ["dienst.py"])
        self.assertEqual(erg.befunde, [], u"an der Antwort messen, nicht an "
                                          u"der Datei")

    def test_kurze_antwort_ohne_attrappen_namen(self):
        u"""Auch ein echtes Modell kann „ok" antworten — das ist kein Befund."""
        kurz = _mitschrift(u"Kurz", u"grossmodell", u"ok")
        erg = _lauf({"review_d_kurz.md": kurz}, ["dienst.py"])
        self.assertEqual(erg.befunde, [])


class KopfdatenTest(SimpleTestCase):
    u"""Bereich, Modell und Dauer stehen in der ersten Zeile."""

    def test_kopfzeile_wird_gelesen(self):
        with tempfile.TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "review_a_probe.md"
            pfad.write_text(NUMMERIERT, encoding="utf-8")
            m = Mitschrift(pfad)
        self.assertEqual(m.bereich, u"Probebereich")
        self.assertEqual(m.modell, u"grossmodell")
        self.assertEqual(m.sekunden, 12)

    def test_ohne_kopfzeile_gilt_der_dateiname(self):
        with tempfile.TemporaryDirectory() as ordner:
            pfad = Path(ordner) / "review_abc_mein_bereich.md"
            pfad.write_text(u"nur Text", encoding="utf-8")
            m = Mitschrift(pfad)
        self.assertEqual(m.bereich, u"mein_bereich")

    def test_dateinamen_werden_erkannt(self):
        befund = Reviewbefund(None, u"T", u"siehe `core/api/x.py` und `y.js`")
        self.assertEqual(befund.dateien, ["core/api/x.py", "y.js"])
