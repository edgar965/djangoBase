# -*- coding: utf-8 -*-
"""`strukturtests` — die Strukturregeln als roter Test, mit Ratsche.

DER ANLASS (gunSlinger, 18.09.2026)
===================================
Dort ist die Regel „eine Klasse je Datei, 300 Zeilen, Test je Klasse" ein
Test (`tests/test_bdp_rules.py`), hier war sie Text. Die Bausteine dazu
(`Dateigroesse`, `KlassenJeDatei`) gab es schon als Werkzeuge; diese Datei
prüft, dass ihre Befunde jetzt ROT werden — und dass die Ratsche in BEIDE
Richtungen greift.

WAS HIER GEPRÜFT WIRD
=====================
Je Regel: ein Verstoß macht rot (mit Pfad in der Meldung), ein sauberes
Projekt bleibt grün, ein Eintrag im Bestand deckt den Verstoß, und ein
Bestandseintrag ohne Verstoß macht rot („veraltet"). Die Prüffälle laufen
auf Wegwerfordnern (`Wegwerfordner.ansetzen`), nie auf dem Host-Projekt —
deshalb werden die Klassen NUR über das Modul angesprochen: Stünden sie im
Namensraum dieser Datei, führe der Testläufer sie gegen den Host aus.
"""

from django.test import SimpleTestCase

from djangobase import strukturtests as st

from ..wegwerfordner import Wegwerfordner

GROSS = "class Riese:\n" + "".join("    def m%d(self):\n        return %d\n" % (i, i) for i in range(160))
KLEIN = "class Zwerg:\n    def a(self):\n        return 1\n"
#: Zwei eigenständige Klassen UND über 300 Code-Zeilen — erst dann ist es nach
#: der Eichung von `KlassenJeDatei` ein Verstoß (darunter: „Aufteilen schadet").
ZWEI_GROSSE = (
    "class Erste:\n"
    + "".join("    def m%d(self):\n        return %d\n" % (i, i) for i in range(80))
    + "\n\nclass Zweite:\n"
    + "".join("    def n%d(self):\n        return %d\n" % (i, i) for i in range(80))
)


def _regeln_auf(ordner, **cfg):
    """Strukturregeln, deren Werkzeuge `ordner` als Projektwurzel sehen."""

    class _Regeln(st.Strukturregeln):
        def werkzeug(self, klasse):
            return Wegwerfordner.ansetzen(klasse(), ordner)

    return _Regeln(cfg)


def _fall(basis, ordner, **cfg):
    """Eine Unterklasse des Strukturtests, die auf `ordner` mit `cfg` läuft."""
    regeln = _regeln_auf(ordner, **cfg)
    return type("Fall", (basis,), {"regeln": classmethod(lambda cls: regeln)})


def _laeuft(basis, ordner, methode, **cfg):
    """``(ok, meldung)`` eines einzelnen Testlaufs — ohne den Läufer zu bemühen."""
    fall = _fall(basis, ordner, **cfg)(methode)
    try:
        getattr(fall, methode)()
        return True, ""
    except AssertionError as e:
        return False, str(e)
    except Exception as e:  # skipTest
        return None, str(e)


def _projekt(dateien):
    ordner = Wegwerfordner.neu("struktur_")
    for name, inhalt in dateien.items():
        ziel = ordner / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8")
    return ordner


class DieGroessenregel(SimpleTestCase):
    METHODE = "test_nichts_ueber_der_groessengrenze"

    def test_eine_zu_grosse_klasse_macht_rot_mit_pfad(self):
        ordner = _projekt({"app/riese.py": GROSS})
        ok, meldung = _laeuft(st.StrukturtestDateigroesse, ordner, self.METHODE)
        self.assertFalse(ok)
        self.assertIn("app/riese.py::Riese", meldung)
        self.assertIn("app/riese.py (Datei", meldung)
        self.assertIn("NEU", meldung)

    def test_ein_sauberes_projekt_bleibt_gruen(self):
        ordner = _projekt({"app/zwerg.py": KLEIN})
        self.assertEqual(_laeuft(st.StrukturtestDateigroesse, ordner, self.METHODE), (True, ""))

    def test_die_grenze_kommt_aus_der_einstellung(self):
        ordner = _projekt({"app/zwerg.py": KLEIN})
        ok, meldung = _laeuft(st.StrukturtestDateigroesse, ordner, self.METHODE, datei=2, klasse=2)
        self.assertFalse(ok)
        self.assertIn("app/zwerg.py::Zwerg", meldung)

    def test_funktionen_werden_nur_auf_wunsch_geprueft(self):
        lang = "def lang():\n" + "".join("    x%d = %d\n" % (i, i) for i in range(70)) + "    return x1\n"
        ordner = _projekt({"app/f.py": lang})
        self.assertTrue(_laeuft(st.StrukturtestDateigroesse, ordner, self.METHODE)[0])
        ok, meldung = _laeuft(st.StrukturtestDateigroesse, ordner, self.METHODE, funktion=60)
        self.assertFalse(ok)
        self.assertIn("app/f.py::lang", meldung)


class DieRatsche(SimpleTestCase):
    METHODE = "test_nichts_ueber_der_groessengrenze"

    def test_ein_bestandseintrag_deckt_den_verstoss(self):
        ordner = _projekt({"app/riese.py": GROSS})
        bestand = {"groesse": ["app/riese.py", "app/riese.py::Riese"]}
        self.assertEqual(
            _laeuft(st.StrukturtestDateigroesse, ordner, self.METHODE, bestand=bestand), (True, "")
        )

    def test_ein_veralteter_eintrag_macht_rot(self):
        """Die Liste darf nur schrumpfen: Wer aufräumt, streicht den Eintrag."""
        ordner = _projekt({"app/zwerg.py": KLEIN})
        ok, meldung = _laeuft(
            st.StrukturtestDateigroesse, ordner, self.METHODE, bestand={"groesse": ["app/alt.py"]}
        )
        self.assertFalse(ok)
        self.assertIn("VERALTET", meldung)
        self.assertIn("app/alt.py", meldung)

    def test_bestand_gilt_je_regel(self):
        """Ein Datei-Eintrag der Größenregel ist für die Klassenregel kein Eintrag."""
        regeln = st.Strukturregeln({"bestand": {"groesse": ["a.py"]}})
        self.assertEqual(regeln.bestand("groesse"), {"a.py"})
        self.assertEqual(regeln.bestand("klassen"), set())
        self.assertEqual(regeln.ratsche("klassen", ["a.py"]), (["a.py"], []))

    def test_meldung_nennt_die_einstellung(self):
        text = st.Strukturregeln.meldung("groesse", "Kopf", ["neu.py"], ["alt.py"])
        self.assertIn("['bestand']['groesse']", text)
        self.assertLess(text.index("neu.py"), text.index("alt.py"))


class DieKlassenregel(SimpleTestCase):
    METHODE = "test_eine_eigenstaendige_klasse_je_datei"

    def test_zwei_eigenstaendige_klassen_machen_rot(self):
        ordner = _projekt({"app/sammlung.py": ZWEI_GROSSE})
        ok, meldung = _laeuft(st.StrukturtestKlassenJeDatei, ordner, self.METHODE)
        self.assertFalse(ok)
        self.assertIn("app/sammlung.py", meldung)

    def test_kleine_datentraeger_neben_der_hauptklasse_bleiben_gruen(self):
        """Die Eichung des Werkzeugs gilt: kein Nachbau einer strengeren Regel."""
        ordner = _projekt({"app/dienst.py": GROSS.replace("range(160)", "range(20)") + "\n\n" + KLEIN})
        self.assertEqual(_laeuft(st.StrukturtestKlassenJeDatei, ordner, self.METHODE), (True, ""))

    def test_laesst_sich_abschalten(self):
        ordner = _projekt({"app/sammlung.py": ZWEI_GROSSE})
        ok, _ = _laeuft(st.StrukturtestKlassenJeDatei, ordner, self.METHODE, klassen_je_datei=False)
        self.assertIsNone(ok, "abgeschaltet = übersprungen, nicht grün")


class DieTestJeKlasseRegel(SimpleTestCase):
    METHODE = "test_jede_klasse_hat_ein_testmodul"

    def test_ist_vorgabe_aus(self):
        ordner = _projekt({"app/dienst.py": KLEIN})
        self.assertIsNone(_laeuft(st.StrukturtestTestJeKlasse, ordner, self.METHODE)[0])

    def test_klasse_ohne_testmodul_macht_rot_mit_testmodul_gruen(self):
        ordner = _projekt({"app/dienst.py": KLEIN, "app/apps.py": "class AppConfig:\n    pass\n"})
        ok, meldung = _laeuft(st.StrukturtestTestJeKlasse, ordner, self.METHODE, test_je_klasse=True)
        self.assertFalse(ok)
        self.assertIn("app/dienst.py", meldung)
        self.assertNotIn("apps.py", meldung, "Django-Pflichtdateien verlangen kein Testmodul")
        (ordner / "app" / "tests" / "unit").mkdir(parents=True)
        (ordner / "app" / "tests" / "unit" / "test_dienst.py").write_text("", encoding="utf-8")
        self.assertEqual(
            _laeuft(st.StrukturtestTestJeKlasse, ordner, self.METHODE, test_je_klasse=True), (True, "")
        )
