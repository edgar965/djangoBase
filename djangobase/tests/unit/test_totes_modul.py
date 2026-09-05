# -*- coding: utf-8 -*-
u"""`totes-modul` schlägt an — und nur da, wo wirklich nichts mehr hängt.

WARUM DIESER TEST AUSFÜHRLICHER IST ALS ANDERE
==============================================
Die Befunde dieser Prüfung sind **Löschvorschläge**. Eine frühere Fassung in
shortlongx hat damit dreimal danebengelegen, und jedes Mal wäre lebender Code
verschwunden:

* ``technik_archiv_verwaltung`` (drei URL-Ziele), ``menue_archiv`` (das
  Archiv-Untermenü) und ``storno_lage`` (eine Klasse mit dreizehn
  Verwendungen) galten als tot — bei ``from .x import *`` steht der Modulname
  genau einmal, nämlich in der Datei selbst.
* ``hilfe_netzsysteme_teil2..5`` galten als tot, obwohl Zeile 15–18 der
  Sammeldatei sie importiert.
* 122 lebende Namen auf einmal, weil „wird auswärts benutzt?" jede Klasse
  traf, die nur ihr eigenes Modul benutzt.

Dazu die Rückkopplung: Die Prüfung las den Bericht, den sie selbst schrieb.
Vier Läufe ergaben 62, 1, 60, 1 — jede Zahl sah nach einem Ergebnis aus.

Jeder dieser Fälle steht hier als eigener Test.
"""
import tempfile
from pathlib import Path

from django.test import SimpleTestCase

from djangobase.skills.totesmodul import TotesModul
from djangobase.skills.werkzeug import Quelldatei


class _TotesModul(TotesModul):
    u"""Sucht in einem Wegwerf-Verzeichnis statt im Projekt."""

    def __init__(self, ordner):
        super().__init__()
        self._ordner = Path(ordner)

    def wurzel(self):
        return self._ordner

    def pfade(self, muster="*.py", unter=None):
        return sorted(self._ordner.rglob(muster))

    def dateien(self, endung=".py"):
        return [Quelldatei(p, self._ordner)
                for p in sorted(self._ordner.rglob("*" + endung))]


def _lauf(dateien):
    with tempfile.TemporaryDirectory() as ordner:
        for name, inhalt in dateien.items():
            ziel = Path(ordner) / name
            ziel.parent.mkdir(parents=True, exist_ok=True)
            ziel.write_text(inhalt, encoding="utf-8")
        satz = _TotesModul(ordner).pruefen()
        return sorted(str(b.ort) for b in satz.befunde), " ".join(satz.kopf)


class TotesModulTest(SimpleTestCase):

    def test_ein_wirklich_totes_modul_wird_gemeldet(self):
        orte, kopf = _lauf({"tot.py": "def niemand():\n    return 1\n"})
        self.assertEqual(orte, ["tot.py"], kopf)

    def test_importiertes_modul_lebt(self):
        orte, kopf = _lauf({
            "lebt.py": "WERT = 1\n",
            "start.py": 'from lebt import WERT\n\n'
                        'if __name__ == "__main__":\n    print(WERT)\n'})
        self.assertEqual(orte, [], kopf)

    def test_paket_lebt_wenn_sein_inhalt_gebraucht_wird(self):
        u"""``from a.b.c import x`` hält auch ``a.b`` am Leben."""
        orte, kopf = _lauf({
            "paket/__init__.py": "",
            "paket/tief.py": "WERT = 1\n",
            "start.py": 'from paket.tief import WERT\n\n'
                        'if __name__ == "__main__":\n    print(WERT)\n'})
        self.assertEqual(orte, [], kopf)


class LebendeModuleTest(SimpleTestCase):
    u"""Die drei Fälle, die eine frühere Fassung löschen wollte."""

    def test_sternimport_haelt_das_modul_am_leben(self):
        u"""``from .x import *`` — der Modulname steht nur in der Datei selbst.

        Gerettet wird es über Stufe 3: Ein öffentlicher Name des Moduls wird
        anderswo benutzt."""
        orte, kopf = _lauf({
            "views/__init__.py": "from .storno_lage import *\n",
            "views/storno_lage.py": "class StornoLage:\n    def zeigen(self):\n"
                                    "        return 1\n",
            "start.py": 'from views import StornoLage\n\n'
                        'if __name__ == "__main__":\n    print(StornoLage)\n'})
        self.assertEqual(orte, [], kopf)

    def test_ein_einziger_import_von_aussen_reicht(self):
        u"""``teil2..5``: Ein Import ergibt genau EINEN Treffer im Text.

        Die frühere Fassung verlangte mehr als einen und verwarf ihn damit."""
        orte, kopf = _lauf({
            "sammel.py": 'from teil2 import ZWEI\n\n'
                         'if __name__ == "__main__":\n    print(ZWEI)\n',
            "teil2.py": "ZWEI = 2\n"})
        self.assertEqual(orte, [], kopf)

    def test_nur_im_eigenen_modul_benutzt_ist_kein_toter_code(self):
        u"""Kapselung ist kein toter Code — 122 Namen auf einmal."""
        orte, kopf = _lauf({
            "dienst.py": "class Helfer:\n    pass\n\n\n"
                         "class Dienst:\n    def bauen(self):\n"
                         "        return Helfer()\n",
            "start.py": 'from dienst import Dienst\n\n'
                        'if __name__ == "__main__":\n    print(Dienst)\n'})
        self.assertEqual(orte, [], kopf)


class KonventionTest(SimpleTestCase):
    u"""Was per Konvention gefunden wird, darf nirgends erwähnt sein."""

    def test_testmodul_ist_kein_befund(self):
        orte, kopf = _lauf({"test_etwas.py": "def test_lauf():\n    assert True\n"})
        self.assertEqual(orte, [], kopf)

    def test_skript_mit_main_ist_kein_befund(self):
        orte, kopf = _lauf({"s.py": 'def haupt():\n    return 1\n\n\n'
                                    'if __name__ == "__main__":\n    haupt()\n'})
        self.assertEqual(orte, [], kopf)

    def test_skript_OHNE_main_ist_kein_befund(self):
        u"""``depot/ohlcv_check.py``: kein ``__main__``, aber Django-Aufbau,
        ``print`` auf Modulebene und ``os._exit(0)`` am Schluss."""
        orte, kopf = _lauf({"d.py": "import django\n\ndjango.setup()\n"
                                    'print("Tabelle")\n'})
        self.assertEqual(orte, [], kopf)

    def test_schleife_auf_modulebene_ist_ein_skript(self):
        u"""``depot/vol_futures_probe.py`` hat weder ``__main__`` noch einen
        der bekannten Aufrufe — es arbeitet in einer Schleife."""
        orte, kopf = _lauf({"p.py": "TICKER = [1, 2]\n\nfor t in TICKER:\n"
                                    "    pass\n"})
        self.assertEqual(orte, [], kopf)

    def test_management_command_ist_kein_befund(self):
        orte, kopf = _lauf({"app/management/commands/tun.py":
                            "class Command:\n    def handle(self):\n        pass\n"})
        self.assertEqual(orte, [], kopf)

    def test_die_zahl_der_ausnahmen_steht_in_der_kopfzeile(self):
        u"""Eine Ausnahme, die niemand sieht, ist eine Hintertür."""
        _orte, kopf = _lauf({"test_x.py": "def test_a():\n    pass\n",
                             "tot.py": "def niemand():\n    return 1\n"})
        self.assertIn("per Konvention gefunden", kopf)


class RueckkopplungTest(SimpleTestCase):
    u"""Der Bericht, den die Prüfung selbst schreibt, macht nichts lebendig."""

    def test_ein_bericht_im_ergebnisordner_zaehlt_nicht(self):
        orte, kopf = _lauf({
            "tot.py": "def niemand():\n    return 1\n",
            # Genau so sieht der Bericht aus: Er nennt den Namen der Datei,
            # die er gerade gemeldet hat.
            "ergebnis/befunde.md": "# Befunde\n\n- tot.py: Modul wird nirgends "
                                   "erwähnt (niemand)\n"})
        self.assertEqual(orte, ["tot.py"],
                         "der eigene Bericht darf das Modul nicht am Leben "
                         "halten: " + kopf)

    def test_eine_echte_erwaehnung_in_einer_vorlage_zaehlt_sehr_wohl(self):
        u"""DIE GEGENPROBE: Nur das ERGEBNIS-Verzeichnis ist ausgenommen."""
        orte, kopf = _lauf({
            "tot.py": "def niemand():\n    return 1\n",
            "vorlage.html": "<p>siehe tot.py und niemand()</p>\n"})
        self.assertEqual(orte, [], kopf)
