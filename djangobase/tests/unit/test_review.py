# -*- coding: utf-8 -*-
"""Wächter für Hilfe → Review.

Geprüft wird das, was ohne Netz prüfbar ist und trotzdem schiefgehen kann:

* **Was gesendet wird.** Das Paket wird aus dem echten Quelltext gebaut. Ein
  Pfad, der aus der Wurzel herausführt, darf NICHT gelesen werden — bei einem
  Online-Partner verlässt der Inhalt sonst den Rechner. Das ist der einzige
  Punkt dieser Seite, an dem ein Fehler nach draußen wirkt.
* **Dass Kürzungen sichtbar sind.** Stillschweigend abschneiden hieße, das
  Modell über den Umfang zu täuschen — und Befunde zu bekommen, die sich auf
  Code beziehen, den es nie gesehen hat.
* **Dass ein Netzfehler den Faden nicht zerreißt**, sondern als Zustand
  „fehler" mit Text ankommt.

Die Modell-Anfrage selbst wird ersetzt (kein Netz im Test, keine Kosten).
"""
import json
import tempfile
from pathlib import Path
from unittest import mock

from django.test import override_settings
from django.urls import reverse

from djangobase.review import ReviewFehler, ReviewLauf, ReviewPartner
from djangobase.review.register import LaufRegister
from djangobase.tests.base import BasisTest

PARTNER = {"slug": "test", "name": "Testmodell", "ziel": "lokal", "modell": "attrappe"}


class ReviewPaketTest(BasisTest):
    """Was landet im Paket — und was auf keinen Fall."""

    def setUp(self):
        self.wurzel = Path(tempfile.mkdtemp(prefix="review-wurzel-"))
        self.ablage = self.wurzel / "_ablage"
        (self.wurzel / "paket").mkdir()
        (self.wurzel / "paket" / "modul.py").write_text(
            "def f():\n    return 42\n", encoding="utf-8")
        # Liegt NEBEN der Wurzel — genau der Fall, den die Prüfung fangen muss.
        self.geheim = self.wurzel.parent / ("geheim-%s.txt" % self.wurzel.name)
        self.geheim.write_text("APIKEY=nicht-nach-draussen", encoding="utf-8")
        self.addCleanup(self._aufraeumen)

    def _aufraeumen(self):
        import shutil
        shutil.rmtree(self.wurzel, ignore_errors=True)
        try:
            self.geheim.unlink()
        except OSError:
            pass

    def _lauf(self):
        return ReviewLauf("dialog", PARTNER, wurzel=self.wurzel, ablage=self.ablage)

    def test_quelltext_kommt_ins_paket(self):
        paket = self._lauf()._paket(
            {"slug": "a", "name": "Bereich A", "dateien": ["paket/modul.py"],
             "hinweis": "Ein Hinweis", "fragen": ["Warum 42?"]}, "")
        self.assertIn("return 42", paket)
        self.assertIn("Ein Hinweis", paket)
        self.assertIn("Warum 42?", paket)
        self.assertIn("```python", paket, "Sprache für den Codeblock fehlt")

    def test_ein_verzeichnis_meint_alle_quelldateien_darin(self):
        """Ein Paket als Bereichs-Eintrag (31.08.2026).

        ANLASS: Ein Bereich nannte `humanbody_core/skeleton/formats.py` —
        504 Zeilen, acht Skelett-Formate in einer Datei. Beim Aufteilen in
        ein Paket zeigte der Eintrag ins Leere. Der Bereich hätte weiter
        geladen, nur ohne Quelltext: Seite baut sich auf, Modell
        antwortet, es hatte den Code nur nicht gesehen.
        """
        (self.wurzel / "paket" / "zweit.py").write_text(
            "def zwei():\n    return 2\n", encoding="utf-8")
        (self.wurzel / "paket" / "liesmich.txt").write_text(
            "kein Quelltext", encoding="utf-8")
        paket = self._lauf()._paket(
            {"slug": "a", "name": "Bereich A", "dateien": ["paket/"]}, "")
        self.assertIn("return 42", paket, "erste Datei des Pakets fehlt")
        self.assertIn("return 2", paket, "zweite Datei des Pakets fehlt")
        self.assertNotIn("kein Quelltext", paket,
                         "eine .txt gehört nicht in den Quelltext-Anhang")

    def test_verzeichnis_auch_ohne_schraegstrich(self):
        paket = self._lauf()._paket(
            {"slug": "a", "name": "Bereich A", "dateien": ["paket"]}, "")
        self.assertIn("return 42", paket)

    def test_unterpakete_werden_nicht_mitgezogen(self):
        """Nicht rekursiv: sonst wird aus einem Tippfehler der halbe Baum."""
        (self.wurzel / "paket" / "tiefer").mkdir()
        (self.wurzel / "paket" / "tiefer" / "versteckt.py").write_text(
            "def tief():\n    return 'zu tief'\n", encoding="utf-8")
        paket = self._lauf()._paket(
            {"slug": "a", "name": "Bereich A", "dateien": ["paket/"]}, "")
        self.assertIn("return 42", paket)
        self.assertNotIn("zu tief", paket)

    def test_eine_datei_bleibt_eine_datei(self):
        """Die Gegenprobe: Das Auffalten darf den Normalfall nicht anfassen."""
        paket = self._lauf()._paket(
            {"slug": "a", "name": "Bereich A", "dateien": ["paket/modul.py"]}, "")
        self.assertIn("return 42", paket)

    def test_pfad_ausserhalb_der_wurzel_wird_nicht_gesendet(self):
        """DER EINZIGE FEHLER DIESER SEITE, DER NACH DRAUSSEN WIRKT.

        Ein `../` in der Bereichs-Konfiguration ist ein Tippfehler, kein
        Angriff — aber bei einem Online-Partner schickt er fremde Dateien an
        einen fremden Dienst. Deshalb wird gelesen erst nach der Prüfung."""
        paket = self._lauf()._paket(
            {"slug": "a", "name": "A", "dateien": ["../%s" % self.geheim.name]}, "")
        self.assertNotIn("APIKEY", paket)
        self.assertIn("außerhalb", paket.lower())

    def test_fehlende_datei_meldet_sich_statt_zu_schweigen(self):
        paket = self._lauf()._paket(
            {"slug": "a", "name": "A", "dateien": ["paket/gibtesnicht.py"]}, "")
        self.assertIn("gibtesnicht.py", paket)
        self.assertIn("lesbar", paket.lower())

    def test_kuerzung_wird_ausgewiesen(self):
        """Kürzen ist in Ordnung, stillschweigend kürzen nicht."""
        lang = self.wurzel / "paket" / "lang.py"
        lang.write_text("# %s\n" % ("x" * 200), encoding="utf-8")
        lauf = self._lauf()
        with mock.patch.object(ReviewLauf, "MAX_ZEICHEN_DATEI", 50):
            paket = lauf._paket({"slug": "a", "name": "A", "dateien": ["paket/lang.py"]}, "")
        self.assertIn("GEKUERZT", paket)

    def test_funktionsauswahl_schneidet_und_nennt_fehlende(self):
        """Ohne Funktionsauswahl ist eine 6.400-Zeilen-Datei nicht besprechbar."""
        (self.wurzel / 'paket' / 'gross.py').write_text(
            "import os\n\n\ndef eins():\n    return 1\n\n\n"
            "def zwei():\n    return 2\n\n\nclass Drei:\n    pass\n", encoding='utf-8')
        paket = self._lauf()._paket(
            {'slug': 'a', 'name': 'A',
             'dateien': [{'pfad': 'paket/gross.py',
                          'funktionen': ['zwei', 'Drei', 'gibtesnicht']}]}, '')
        self.assertIn('return 2', paket)
        self.assertIn('class Drei', paket)
        self.assertNotIn('return 1', paket, 'nicht angeforderte Funktion mitgeschickt')
        self.assertIn('NICHT gefunden: gibtesnicht', paket,
                      'ein fehlender Name muss im Paket stehen — sonst hält das '
                      'Modell den Ausschnitt für vollständig')
        self.assertIn('Zeile 8', paket, 'Zeilennummer als Anker in die ECHTE Datei fehlt')

    def test_funktionsauswahl_schneidet_vor_dem_kuerzen(self):
        """DER FEHLER DER ERSTEN FASSUNG (13.08.2026).

        Gekürzt wurde ZUERST auf MAX_ZEICHEN_DATEI, geschnitten danach — alles,
        was weiter hinten in einer großen Datei stand, war „nicht gefunden".
        Aufgefallen ist es nur, weil der Hinweis die fehlenden Namen nennt."""
        füller = "\n\n".join("def f%d():\n    return %d" % (i, i) for i in range(400))
        (self.wurzel / 'paket' / 'riesig.py').write_text(
            füller + "\n\n\ndef ganz_hinten():\n    return 'hier'\n", encoding='utf-8')
        lauf = self._lauf()
        with mock.patch.object(ReviewLauf, 'MAX_ZEICHEN_DATEI', 200):
            paket = lauf._paket(
                {'slug': 'a', 'name': 'A',
                 'dateien': [{'pfad': 'paket/riesig.py',
                              'funktionen': ['ganz_hinten']}]}, '')
        self.assertIn("return 'hier'", paket)
        self.assertNotIn('NICHT gefunden', paket)

    def test_bereich_mit_eigener_wurzel(self):
        """Geteilter Code (djangoBase selbst) liegt ausserhalb jedes Projekts.

        Ein Bereich darf deshalb eine eigene Wurzel nennen — und die Pruefung
        muss dann gegen DIESE greifen, nicht gegen die des Laufs."""
        fremd = Path(tempfile.mkdtemp(prefix="review-fremd-"))
        (fremd / "geteilt.py").write_text("WERT = 1\n", encoding="utf-8")
        self.addCleanup(lambda: __import__("shutil").rmtree(fremd, ignore_errors=True))

        paket = self._lauf()._paket(
            {"slug": "g", "name": "Geteilt", "wurzel": str(fremd),
             "dateien": ["geteilt.py"]}, "")
        self.assertIn("WERT = 1", paket)

        # Und die Grenze gilt weiter: aufwaerts aus der EIGENEN Wurzel ist nichts zu holen.
        paket = self._lauf()._paket(
            {"slug": "g", "name": "Geteilt", "wurzel": str(fremd),
             "dateien": ["../geheim.txt"]}, "")
        self.assertIn("außerhalb", paket.lower())

    def test_eigene_frage_ersetzt_die_bereichsfragen(self):
        paket = self._lauf()._paket(
            {"slug": "a", "name": "A", "dateien": [], "fragen": ["Vorgabe?"]},
            "Meine eigene Frage")
        self.assertIn("Meine eigene Frage", paket)
        self.assertNotIn("Vorgabe?", paket)


class ReviewFadenTest(BasisTest):
    """Ein Fehler im Gespräch darf den Faden nicht zerreißen."""

    def test_netzfehler_wird_zum_zustand_nicht_zur_ausnahme(self):
        lauf = ReviewLauf("frage", PARTNER,
                          wurzel=Path(tempfile.gettempdir()),
                          ablage=Path(tempfile.mkdtemp(prefix="review-ablage-")))
        lauf._faden_anlegen("f", "Faden")
        faden = lauf.faeden["f"]
        with mock.patch.object(ReviewPartner, "fragen",
                               side_effect=ReviewFehler("Dienst meldet: kein Guthaben")):
            self.assertIsNone(faden.fragen("Frage?"))
        self.assertEqual(faden.status, "fehler")
        self.assertIn("kein Guthaben", faden.fehler)

    def test_antwort_landet_im_verlauf_und_in_der_mitschrift(self):
        ablage = Path(tempfile.mkdtemp(prefix="review-ablage-"))
        lauf = ReviewLauf("frage", PARTNER, wurzel=Path(tempfile.gettempdir()), ablage=ablage)
        lauf._faden_anlegen("f", "Faden")
        faden = lauf.faeden["f"]
        with mock.patch.object(ReviewPartner, "fragen", return_value="Befund X"):
            faden.fragen("Frage?", marke="Runde 1")
        self.assertEqual(faden.status, "fertig")
        self.assertEqual(faden.runden[0]["antwort"], "Befund X")
        self.assertIn("Befund X", faden.mitschrift.read_text(encoding="utf-8"))


class NebenlaeufigkeitTest(BasisTest):
    """Fehler, die das Review DIESES Werkzeugs gefunden hat (13.08.2026)."""

    def _lauf(self):
        return ReviewLauf("dialog", PARTNER, wurzel=Path(tempfile.gettempdir()),
                          ablage=Path(tempfile.mkdtemp(prefix="review-nl-")))

    def test_nur_einer_gewinnt_den_faden(self):
        """Zwei gleichzeitige Nachfragen auf denselben Faden.

        Vorher prüften Aufrufer und Faden getrennt: Beide kamen durch, beide
        starteten einen Faden, der zweite scheiterte erst im Faden mit einer
        Ausnahme — nachdem die Antwort dem Browser schon „gestartet" gemeldet
        hatte. Die Runde war weg, der Nutzer glaubte, sie liefe."""
        lauf = self._lauf()
        lauf._faden_anlegen("f", "Faden")
        faden = lauf.faeden["f"]
        self.assertTrue(faden.beansprucht(), "der erste muss gewinnen")
        self.assertFalse(faden.beansprucht(), "der zweite darf NICHT gewinnen")

    def test_nachfassen_meldet_nur_was_wirklich_lief(self):
        lauf = self._lauf()
        lauf._faden_anlegen("f", "Faden")
        lauf.faeden["f"].beansprucht()          # Faden ist belegt
        self.assertEqual(lauf.nachfassen("noch eine Frage", slug="f"), [],
                         "ein belegter Faden darf nicht als gestartet gemeldet werden")

    def test_wurzel_gross_klein_egal_unter_windows(self):
        """Eine legitime Datei darf nicht an der Schreibweise der Wurzel scheitern."""
        import os as _os
        if _os.name != "nt":
            self.skipTest("nur unter Windows aussagekräftig")
        wurzel = Path(tempfile.mkdtemp(prefix="review-gross-"))
        (wurzel / "datei.py").write_text("X = 1\n", encoding="utf-8")
        lauf = ReviewLauf("dialog", PARTNER, wurzel=Path(str(wurzel).upper()),
                          ablage=wurzel / "_ablage")
        paket = lauf._paket({"slug": "a", "name": "A", "dateien": ["datei.py"]}, "")
        self.assertIn("X = 1", paket)


class LaufRegisterTest(BasisTest):
    def test_aelteste_laeufe_fallen_heraus(self):
        """Ein Lauf hält den kompletten Quelltext im Verlauf — ein Register,
        das nie vergisst, ist ein Speicherleck mit Extraschritten."""
        r = LaufRegister()
        laeufe = []
        for _ in range(r.MAX_LAEUFE + 3):
            l = ReviewLauf("frage", PARTNER, wurzel=Path(tempfile.gettempdir()),
                           ablage=Path(tempfile.gettempdir()))
            laeufe.append(l)
            r.hinzu(l)
        self.assertEqual(len(r.liste()), r.MAX_LAEUFE)
        self.assertIsNone(r.holen(laeufe[0].id), "ältester Lauf hängt noch fest")
        self.assertIsNotNone(r.holen(laeufe[-1].id))


#: Wohin die Mitschriften der PRUEFUNG gehen.
#:
#: WARUM DAS HIER STEHEN MUSS (Befund 28.08.2026, gemessen in 3DTools)
#: ===================================================================
#: `test_nur_konfigurierte_bereiche_zaehlen` faehrt einen ECHTEN Lauf ueber
#: `review_start` (nur die Modellanfrage ist eine Attrappe). Der Lauf schreibt
#: seine Mitschrift nach::
#:
#:     ablage = c["review_ablage"] or (c["log_verzeichnis"] / "review")
#:
#: `@override_settings(DJANGOBASE={...})` ersetzt das GANZE Woerterbuch, also
#: fehlt darin `log_verzeichnis` — und die Vorgabe dafuer ist `BASE_DIR`. Die
#: Datei landete damit als `<Projekt>/review/review_<id>_a.md`. Gemessen:
#: 32 Dateien vor dem Lauf, 33 danach, jedes Mal. In 3DTools lagen so 33
#: Attrappen a 114 Bytes, 23 davon versehentlich im Repo.
#:
#: Dasselbe wie `pruefung-ohne-spuren` in shortlongx: Eine Pruefung, die in
#: Produktivdaten schreibt, faellt niemandem auf — sie ist ja gruen.
_ABLAGE = tempfile.TemporaryDirectory(prefix="djb-review-test-")


@override_settings(DJANGOBASE={"zugriff": "staff", "review_partner": [PARTNER],
                               "review_ablage": _ABLAGE.name,
                               "review_bereiche": [
                                   {"slug": "a", "name": "Bereich A", "dateien": []}]})
class ReviewSeiteTest(BasisTest):
    """Die Seite und ihre beiden POST-Endpunkte."""

    def test_die_pruefung_schreibt_nur_in_ihre_eigene_ablage(self):
        u"""DER WAECHTER: Ohne ihn faellt der naechste Rueckfall nicht auf.

        Geprueft wird die Vereinbarung selbst — dass die Einstellung, die den
        Schreibort bestimmt, in diesem Test auf ein Wegwerf-Verzeichnis zeigt
        und NICHT auf `BASE_DIR`.
        """
        from django.conf import settings
        from djangobase.conf import conf
        ablage = Path(str(conf()["review_ablage"]))
        self.assertNotEqual(ablage.resolve(), Path(settings.BASE_DIR).resolve(),
                            u"Die Mitschriften landen im Projektstamm")
        self.assertEqual(ablage.resolve(), Path(_ABLAGE.name).resolve())

    def test_seite_zeigt_partner_und_bereiche(self):
        a = self.staff_client().get(reverse("djangobase:review"))
        self.assertEqual(a.status_code, 200)
        self.assertContains(a, "Testmodell")
        self.assertContains(a, "Bereich A")

    def test_unbekannter_partner_wird_abgelehnt(self):
        a = self.staff_client().post(
            reverse("djangobase:review_start"),
            data=json.dumps({"modus": "frage", "partner": "erfunden", "frage": "?"}),
            content_type="application/json")
        self.assertEqual(a.status_code, 400)

    def test_dialog_ohne_bereich_wird_abgelehnt(self):
        a = self.staff_client().post(
            reverse("djangobase:review_start"),
            data=json.dumps({"modus": "dialog", "partner": "test", "bereiche": []}),
            content_type="application/json")
        self.assertEqual(a.status_code, 400)

    def test_nur_konfigurierte_bereiche_zaehlen(self):
        """Die Seite nimmt KEINE Dateipfade aus dem Browser entgegen — ein
        erfundener Bereichs-Slug darf nicht zu einem Lauf führen."""
        # Die Modell-Anfrage ersetzen: Der Start legt einen Hintergrund-Faden an,
        # und der soll im Test weder ins Netz gehen noch Geld kosten.
        with mock.patch.object(ReviewPartner, "fragen", return_value="ok"):
            a = self.staff_client().post(
                reverse("djangobase:review_start"),
                data=json.dumps({"modus": "bereiche", "partner": "test",
                                 "bereiche": ["a", "../../etc"]}),
                content_type="application/json")
        self.assertEqual(a.status_code, 200)
        zustand = a.json()["zustand"]
        self.assertEqual([f["slug"] for f in zustand["faeden"]], ["a"])

    def test_status_unbekannter_lauf(self):
        a = self.staff_client().get(
            reverse("djangobase:review_status", args=["gibtesnicht"]))
        self.assertEqual(a.status_code, 404)
