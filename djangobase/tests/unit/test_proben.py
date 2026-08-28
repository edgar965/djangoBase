# -*- coding: utf-8 -*-
u"""`proben`: Findet es die Gegenproben - und merkt es, wenn eine stumm ist?

DER ANLASS (28.08.2026, 3DTools)
================================
    „kannst du diese Tools gleich speichern auf der Code Review seite fuer die
     sabotageaktionen, seitenproben usw?"

Acht Proben lagen in `Docu/umbau` - Seitenaufrufe im echten Browser,
Cache-Header, LOGGING-Gleichheit, Szenenwerte Feld fuer Feld. Auf keiner Seite
stand, dass es sie gibt. Beim ersten Lauf des neuen Werkzeugs kam sofort ein
Befund heraus, den niemand gesucht hatte: `anlass_protokoll.py` druckte sein
Urteil und endete trotzdem IMMER mit 0.

DREI DINGE WERDEN HIER FESTGENAGELT
===================================
1. Die Auswahl haengt am ENDE des Namens. Mit `*probe*` fing die erste Fassung
   `theatre_studio/probeszene.js` ein - eine Beispielszene - und uebersah
   dabei jede echte Probe.
2. „Kann sie rot werden?" muss stimmen. Eine Probe ohne Fehlschlag-Weg meldet
   ewig „alles wie erwartet" und deckt genau dadurch zu.
3. Der Aufruf kommt aus dem Kopf der Datei, wenn dort einer steht - sonst aus
   der Endung. Ein Eintrag ohne Aufrufbefehl ist eine Fussnote, kein Werkzeug.
"""
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.skills.proben import Proben


ECHTE = u'''"""Gegenprobe: kommt die geaenderte Datei beim Browser an?

Start: python cache_gegenprobe.py --laut
"""
import sys
sys.exit(1 if abweichungen else 0)
'''

STUMME = u'''// Sichtprobe der Tabellen - meldet, aber faellt nie durch.
console.log(schlecht ? "FEHL" : "ok");
process.exit(0);
'''

OHNE_AUFRUF = u'''"""Seitenprobe: laedt jede Seite und liest die Konsole mit."""
if (fehler.length) throw new Error("Konsolenfehler");
'''


class _Werkzeug(Proben):
    u"""Ein `Proben`, das in einem Wegwerf-Verzeichnis sucht."""

    def __init__(self, ordner):
        super().__init__()
        self._ordner = Path(ordner)

    def wurzel(self):
        return self._ordner

    def pfade(self, muster="*.py", unter=None):
        return sorted(p for p in self._ordner.rglob(muster) if p.is_file())


def _lauf(dateien):
    with tempfile.TemporaryDirectory(prefix="djb-proben-") as ordner:
        for name, inhalt in dateien.items():
            pfad = Path(ordner) / name
            pfad.parent.mkdir(parents=True, exist_ok=True)
            pfad.write_text(inhalt, encoding="utf-8")
        return _Werkzeug(ordner).laufen()


class AuswahlTest(SimpleTestCase):

    def test_nur_namen_die_auf_probe_enden(self):
        erg = _lauf({"cache_gegenprobe.py": ECHTE,
                     "seitenprobe.mjs": OHNE_AUFRUF,
                     "probeszene.js": STUMME,
                     "dienst.py": u"x = 1\n"})
        namen = sorted(z["probe"] for z in erg.zeilen)
        self.assertEqual(namen, ["cache_gegenprobe.py", "seitenprobe.mjs"],
                         erg.zusammenfassung)

    def test_wegwerfstuecke_bleiben_draussen(self):
        u"""Ein fuehrender Unterstrich heisst: waehrend einer Sitzung
        entstanden, nicht zum Aufheben."""
        erg = _lauf({"_globalprobe.mjs": ECHTE, "seitenprobe.mjs": ECHTE})
        self.assertEqual([z["probe"] for z in erg.zeilen], ["seitenprobe.mjs"])

    def test_ausnahme_aus_den_einstellungen_greift(self):
        with tempfile.TemporaryDirectory(prefix="djb-proben-") as ordner:
            (Path(ordner) / "fremd").mkdir()
            (Path(ordner) / "fremd" / "seitenprobe.mjs").write_text(
                ECHTE, encoding="utf-8")
            (Path(ordner) / "eigenprobe.py").write_text(ECHTE, encoding="utf-8")
            werkzeug = _Werkzeug(ordner)
            werkzeug._einstellung = lambda name: (["fremd/"] if name ==
                                                  "proben_ausser" else [])
            erg = werkzeug.laufen()
        self.assertEqual([z["probe"] for z in erg.zeilen], ["eigenprobe.py"])


class RotWerdenTest(SimpleTestCase):

    def test_probe_mit_rueckgabewert_kann_rot_werden(self):
        erg = _lauf({"cache_gegenprobe.py": ECHTE})
        self.assertEqual(erg.zeilen[0]["kann rot werden"], "ja")

    def test_probe_die_immer_null_zurueckgibt_wird_gemeldet(self):
        u"""`process.exit(0)` ist KEIN Fehlschlag-Weg — genau der Fall, den
        `anlass_protokoll.py` am 28.08.2026 hatte."""
        erg = _lauf({"tabellenprobe.mjs": STUMME})
        self.assertEqual(erg.zeilen[0]["kann rot werden"], "nein")
        self.assertIn("kann nicht rot werden", erg.zusammenfassung)

    def test_throw_zaehlt_als_fehlschlag_weg(self):
        u"""Gegenprobe zur Gegenprobe: Wer nur nach `exit` sucht, meldet die
        halbe Sammlung faelschlich als stumm."""
        erg = _lauf({"seitenprobe.mjs": OHNE_AUFRUF})
        self.assertEqual(erg.zeilen[0]["kann rot werden"], "ja")

    def test_saubere_sammlung_sagt_nichts_von_stummen(self):
        erg = _lauf({"cache_gegenprobe.py": ECHTE,
                     "seitenprobe.mjs": OHNE_AUFRUF})
        self.assertNotIn("rot werden", erg.zusammenfassung)


class AufrufTest(SimpleTestCase):

    def test_start_zeile_aus_dem_kopf(self):
        erg = _lauf({"cache_gegenprobe.py": ECHTE})
        self.assertEqual(erg.zeilen[0]["aufruf"],
                         "python cache_gegenprobe.py --laut")

    def test_ohne_start_zeile_aus_der_endung(self):
        erg = _lauf({"seitenprobe.mjs": OHNE_AUFRUF})
        self.assertEqual(erg.zeilen[0]["aufruf"], "node seitenprobe.mjs")
        self.assertEqual(erg.zeilen[0]["art"], "Browser")

    def test_zweck_kommt_aus_dem_kopf(self):
        erg = _lauf({"seitenprobe.mjs": OHNE_AUFRUF})
        self.assertIn("laedt jede Seite", erg.zeilen[0]["zweck"])
