# -*- coding: utf-8 -*-
u"""`BefundLager`: welcher Lauf der CodeRabbit-CLI gehoert zu welchem Repo?

WARUM DIESE PRUEFUNG (31.08.2026)
=================================
Die Befund-Tafel auf Hilfe → Review liest die Ablage eines FREMDEN Werkzeugs.
Das Format ist nicht dokumentiert, und genau daran kann der Leser still
scheitern — er zeigt dann eine leere Liste, und die sieht aus wie ein sauberer
Lauf. Deshalb wird hier an einer NACHGEBAUTEN Ablage geprueft, nicht an der
echten: Ein Test, der die Ablage des Rechners liest, ist gruen, solange dort
zufaellig etwas liegt, und sagt nichts ueber den Leser.

DIE VIER FAELLE, DIE WIRKLICH SCHIEFGEHEN
=========================================
1. **Beidateien als Befund gezaehlt.** Im Lauf-Ordner liegen neben den
   Befunden ``git.json``, ``internalState.json`` und der Diff des ganzen Laufs
   (eine LISTE, kein Objekt). Gemessen am 31.08.2026: 17 Dateien, 14 Befunde.
   Wer alles zaehlt, meldet drei Befunde zu viel.
2. **Aeltere Laeufe verschwinden.** Nur der juengste Lauf traegt eine
   ``git.json``; die CLI raeumt sie in aelteren offenbar weg. Ein Leser, der
   jeden Lauf einzeln beglaubigen will, sieht genau einen — die Historie waere
   still weg.
3. **Fremde Repos werden mitgezaehlt.** Die Ablage haelt alle Projekte
   nebeneinander. Zeigt die Zuordnung daneben, stehen auf der Seite von
   shortlongx die Befunde von djangoBase.
4. **Abgebrochene Laeufe als „nichts gefunden"**. Ein leerer Ordner ist keine
   Entwarnung.

BDD - GEGEBEN / DANN
====================
    EinLaufMitGitDatei            ... wird gefunden, Beidateien zaehlen nicht
    EinAelteterLaufOhneGitDatei   ... kommt trotzdem mit
    EinFremdesRepoDaneben         ... bleibt draussen
    EinLeererLaufOrdner           ... faellt heraus
    EinBefundOhneDatei            ... ist kein Befund
"""
import json
import unittest

from djangobase.review.befund import Befund
from djangobase.review.befund_lager import BefundLager
from djangobase.tests.wegwerfordner import Wegwerfordner


class BefundlagerBasis(unittest.TestCase):
    u"""Baut eine Ablage nach — ohne Datenbank, ohne die echte CLI."""

    databases = []

    def setUp(self):
        self.wegwerf = Wegwerfordner.neu(praefix="befundlager_")
        #: Das „Repository", um das es geht. Es muss nicht existieren — der
        #: Leser vergleicht Pfade, er liest dort nichts.
        self.repo = self.wegwerf / "meinprojekt"
        self.repo.mkdir(parents=True, exist_ok=True)
        self.ablage = self.wegwerf / "reviews"

    # ------------------------------------------------------------- Attrappen

    def lauf_anlegen(self, oben, ms, befunde, mit_git=True, verzeichnis=None):
        u"""Einen Lauf-Ordner bauen, wie die CLI ihn hinterlaesst.

        @param oben        Name des Repo-Ordners (bei der CLI eine MD5)
        @param ms          Millisekunden seit 1970 = Ordnername des Laufs
        @param befunde     Liste von (datei, grad) — je einer wird eine Datei
        @param mit_git     ``git.json`` dazu? Aeltere Laeufe haben keine.
        @param verzeichnis Was in ``workingDirectory`` steht (Vorgabe: self.repo)
        """
        ordner = self.ablage / oben / "zweighash" / "reviews" / str(ms)
        ordner.mkdir(parents=True, exist_ok=True)
        for i, (datei, grad) in enumerate(befunde):
            (ordner / ("%08d-uuid.json" % i)).write_text(json.dumps({
                "fileName": datei, "startLine": 10 + i, "endLine": 10 + i,
                "title": u"Befund %d" % i, "comment": u"**Befund %d**\n\nText." % i,
                "severity": grad, "commentCategory": "FUNCTIONAL_CORRECTNESS",
                "type": "actionable", "fingerprint": "f%d" % i,
            }), encoding="utf-8")
        if mit_git:
            (ordner / "git.json").write_text(json.dumps({
                "head": "abc123def456", "baseBranch": "main",
                "workingDirectory": str(verzeichnis or self.repo),
                "timestamp": ms // 1000,
            }), encoding="utf-8")
        # Die beiden Beidateien, die NICHT als Befund zaehlen duerfen.
        (ordner / "internalState.json").write_text('{"prObjectives": ""}', encoding="utf-8")
        (ordner / "incrementalDiff.json").write_text(
            '[{"filename": "a.py", "diff": "@@"}]', encoding="utf-8")
        return ordner

    def lager(self):
        return BefundLager(self.repo, ablage=self.ablage)

    # ---------------------------------------------------------------- Faelle

    def test_ein_lauf_mit_gitdatei_wird_gefunden(self):
        u"""GEGEBEN ein Lauf mit git.json — DANN zaehlen nur die Befunde."""
        self.lauf_anlegen("repohash", 1788000000000,
                          [("a.py", "major"), ("b.py", "minor")])
        laeufe = self.lager().laeufe()
        self.assertEqual(len(laeufe), 1)
        self.assertEqual(laeufe[0]["anzahl"], 2, u"Beidateien mitgezaehlt")
        self.assertEqual(laeufe[0]["uebersprungen"], 0,
                         u"Beidateien als unlesbaren Befund gewertet")
        self.assertEqual(laeufe[0]["commit"], "abc123de")
        self.assertTrue(laeufe[0]["belegt"])

    def test_aelterer_lauf_ohne_gitdatei_kommt_mit(self):
        u"""GEGEBEN ein aelterer Lauf ohne git.json im selben Ordner —
        DANN steht er trotzdem in der Liste (der gemessene Normalfall)."""
        self.lauf_anlegen("repohash", 1788000000000, [("a.py", "major")])
        self.lauf_anlegen("repohash", 1787000000000,
                          [("alt.py", "minor")], mit_git=False)
        laeufe = self.lager().laeufe()
        self.assertEqual(len(laeufe), 2, u"aeltere Laeufe fallen heraus")
        # Neuester zuerst.
        self.assertEqual(laeufe[0]["id"], "1788000000000")
        self.assertFalse(laeufe[1]["belegt"],
                         u"ein Lauf ohne git.json darf nicht als belegt gelten")

    def test_fremdes_repo_bleibt_draussen(self):
        u"""GEGEBEN ein zweites Projekt in derselben Ablage —
        DANN taucht keiner seiner Befunde hier auf."""
        self.lauf_anlegen("repohash", 1788000000000, [("a.py", "major")])
        self.lauf_anlegen("fremdhash", 1788000000001,
                          [("fremd1.py", "major"), ("fremd2.py", "major")],
                          verzeichnis=self.wegwerf / "fremdprojekt")
        laeufe = self.lager().laeufe()
        dateien = [b["datei"] for l in laeufe for b in l["befunde"]]
        self.assertEqual(dateien, ["a.py"], u"fremde Befunde eingemischt")

    def test_leerer_laufordner_faellt_heraus(self):
        u"""GEGEBEN ein abgebrochener Lauf ohne jede Datei —
        DANN wird er nicht als „0 Befunde" gezeigt."""
        self.lauf_anlegen("repohash", 1788000000000, [("a.py", "major")])
        leer = self.ablage / "repohash" / "zweighash" / "reviews" / "1787000000000"
        leer.mkdir(parents=True, exist_ok=True)
        self.assertEqual(len(self.lager().laeufe()), 1)

    def test_ohne_ablage_keine_laeufe(self):
        u"""GEGEBEN gar keine Ablage — DANN eine leere Liste, kein Absturz."""
        lager = BefundLager(self.repo, ablage=self.wegwerf / "gibtsnicht")
        self.assertFalse(lager.vorhanden())
        self.assertEqual(lager.laeufe(), [])

    def test_sortierung_schwer_zuerst(self):
        u"""GEGEBEN gemischte Schweregrade — DANN steht der schwerste oben."""
        self.lauf_anlegen("repohash", 1788000000000,
                          [("a.py", "minor"), ("b.py", "critical"), ("c.py", "major")])
        grade = [b["grad"] for b in self.lager().letzter()["befunde"]]
        self.assertEqual(grade, ["critical", "major", "minor"])


class BefundBasis(unittest.TestCase):
    u"""Der einzelne Befund — was ihn gueltig macht."""

    databases = []

    def test_ohne_datei_kein_befund(self):
        u"""GEGEBEN ein Eintrag ohne fileName — DANN ist er ungueltig.

        Das ist die Schranke, an der die Beidateien der CLI haengenbleiben."""
        self.assertFalse(Befund({"title": "x"}).gueltig())
        self.assertFalse(Befund({"fileName": "a.py"}).gueltig(),
                         u"weder Titel noch Text — trotzdem gueltig")
        self.assertTrue(Befund({"fileName": "a.py", "title": "x"}).gueltig())

    def test_liste_ist_kein_befund(self):
        u"""GEGEBEN die Diff-Datei (eine Liste) — DANN kein Absturz."""
        self.assertFalse(Befund([{"filename": "a.py"}]).gueltig())

    def test_nichttextliches_feld_ist_kein_befund(self):
        u"""GEGEBEN ein ``title``, der keine Zeichenkette ist — DANN ungueltig.

        BEFUND CODERABBIT (31.08.2026): Vorher kam so ein Eintrag durch
        ``gueltig()`` und stuerzte erst beim Anzeigen ab — ``["x"].strip()``
        wirft AttributeError, also HTTP 500 auf genau der Seite, die einen
        Formatwechsel ueberstehen soll. Der Fall ist nicht ausgedacht: Das
        Format ist undokumentiert, und ein Feld, das heute Text ist, kann
        morgen eine Liste sein."""
        for wert in (["x"], {"a": 1}, 42):
            roh = {"fileName": "a.py", "title": wert}
            self.assertFalse(Befund(roh).gueltig(),
                             u"nichttextlicher title (%r) durchgelassen" % (wert,))
        # GEGENPROBE: Der Wächter darf den Normalfall nicht mitnehmen.
        self.assertTrue(Befund({"fileName": "a.py", "title": "x"}).gueltig())
        # Und ein FEHLENDES Feld ist etwas anderes als ein falsches.
        self.assertTrue(Befund({"fileName": "a.py", "comment": "x",
                                "title": None}).gueltig())

    def test_alle_stripfelder_stehen_im_waechter(self):
        u"""GEGEBEN irgendein Textfeld als Liste — DANN nie ein AttributeError.

        ZWEITER BEFUND CODERABBIT DERSELBEN RUNDE (31.08.2026): Die erste
        Fassung des Waechters listete nur ``fileName``, ``title`` und
        ``comment``. ``severity``, ``commentCategory`` und ``diff`` gehen aber
        genauso durch ein ``.strip()`` — dieselbe Luecke, eine Zeile weiter
        unten. Statt die Liste noch einmal von Hand nachzuziehen, prueft
        dieser Test das VERHALTEN: Kein einzelnes kaputtes Feld darf die
        Anzeige zum Absturz bringen.

        Er faellt damit auch bei einem Feld auf, das erst morgen dazukommt."""
        gesund = {"fileName": "a.py", "title": "T", "comment": "C",
                  "severity": "major", "commentCategory": "SECURITY",
                  "diff": "@@", "fingerprint": "f1", "id": "i1",
                  "startLine": 1, "endLine": 2, "timestamp": 1788000000000}
        for feld in gesund:
            roh = dict(gesund, **{feld: ["kaputt"]})
            befund = Befund(roh)
            if not befund.gueltig():
                continue                     # abgewiesen — der saubere Ausgang
            try:
                befund.als_dict()
            except Exception as e:           # noqa: BLE001 - genau das ist der Fall
                self.fail(u"Feld %r als Liste laesst als_dict() platzen: %s"
                          % (feld, e))

    def test_stelle_nennt_die_zeilenspanne(self):
        u"""GEGEBEN Start- und Endzeile — DANN ``datei:12-18``."""
        self.assertEqual(Befund({"fileName": "a.py", "title": "x",
                                 "startLine": 12, "endLine": 18}).stelle, "a.py:12-18")
        self.assertEqual(Befund({"fileName": "a.py", "title": "x",
                                 "startLine": 12, "endLine": 12}).stelle, "a.py:12")
        self.assertEqual(Befund({"fileName": "a.py", "title": "x"}).stelle, "a.py")

    def test_kaputte_zeilennummer_stuerzt_nicht(self):
        u"""GEGEBEN ein Feld, das keine Zahl ist — DANN 0 statt Ausnahme.

        Fremde Felder ohne Netz durch ``int()`` zu schicken, ist ein
        Serverfehler, der erst auffaellt, wenn die CLI das Format aendert."""
        self.assertEqual(Befund({"fileName": "a.py", "title": "x",
                                 "startLine": "spaeter"}).zeile_von, 0)
