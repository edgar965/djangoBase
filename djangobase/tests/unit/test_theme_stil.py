"""Einstellungen -> Theme (01.11.2026): Stilblock aus Vorgaben und Anpassung (``ThemeStil``) und die Prüfung
davor (``ThemeBereinigung``). Ohne Datenbank und ohne Store — nur die Rechnung."""

from django.test import SimpleTestCase

from djangobase.theme_bereinigung import ThemeBereinigung
from djangobase.theme_stil import ThemeStil


class EinStilblockAusVorgabeUndAnpassung(SimpleTestCase):
    databases = []

    def test_anpassung_geht_vor_vorgabe_je_attribut(self):
        werte = ThemeStil.wirksam(
            {"schriften": {"h1": {"groesse": 30}}},
            {"schriften": {"h1": {"groesse": 20, "gewicht": "fett"}}},
        )
        self.assertEqual(werte["schriften"]["h1"], {"groesse": 30, "gewicht": "fett"})

    def test_farbe_setzt_alle_ihre_variablen_auch_rgb(self):
        teile = ThemeStil.deklarationen({"farben": {"leiste_text": "#102030"}})
        self.assertEqual(teile, ["--dbt-leiste-text: #102030", "--dbt-leiste-rgb: 16, 32, 48"])

    def test_grundschrift_faerbt_auch_die_grundfarben(self):
        teile = ThemeStil.deklarationen({"schriften": {"alle": {"farbe": "#000000", "art": "arial"}}})
        self.assertIn("--text-primary: #000000", teile)
        self.assertIn("--dbt-schrift: Arial, Helvetica, sans-serif", teile)

    def test_nur_themes_mit_angaben_bekommen_einen_block(self):
        css = ThemeStil.css({"weiss": {"schriften": {"text": {"kursiv": True}}}}, {}, ["weiss", "dark"])
        self.assertEqual(css, 'body[data-theme="weiss"] { --dbt-s-text-stil: italic; }')

    def test_ohne_alles_kein_block(self):
        self.assertEqual(ThemeStil.css({}, {}, ["weiss", "dark"]), "")

    def test_nummern_zaehlen_ueber_alle_bereiche(self):
        nummern = [r["nr"] for b in ThemeStil.definition()["bereiche"] for r in b["rollen"]]
        self.assertEqual(nummern, list(range(1, len(ThemeStil.ROLLEN) + 1)))


class DiePruefungLaesstNurSicheresDurch(SimpleTestCase):
    databases = []

    def setUp(self):
        self.pruefung = ThemeBereinigung(["weiss"])

    def test_keine_css_einschleusung_ueber_eine_farbe(self):
        sauber = self.pruefung.bereinigen({"weiss": {"farben": {"rand": "red; } body { display:none"}}})
        self.assertEqual(sauber, {})

    def test_unbekanntes_theme_und_unbekannte_rolle_fallen_weg(self):
        sauber = self.pruefung.bereinigen(
            {"dunkel": {"farben": {"akzent": "#000000"}}, "weiss": {"schriften": {"fremd": {"groesse": 12}}}}
        )
        self.assertEqual(sauber, {})

    def test_groesse_als_text_und_ausserhalb_der_grenzen(self):
        sauber = self.pruefung.bereinigen(
            {"weiss": {"schriften": {"h1": {"groesse": "24,5"}, "h2": {"groesse": 99}}}}
        )
        self.assertEqual(sauber, {})
        sauber = self.pruefung.bereinigen({"weiss": {"schriften": {"h1": {"groesse": "24.5"}}}})
        self.assertEqual(sauber["weiss"]["schriften"]["h1"], {"groesse": 24.5})

    def test_knopf_hat_keine_farbe(self):
        sauber = self.pruefung.bereinigen(
            {"weiss": {"schriften": {"knopf": {"farbe": "#ff0000", "gewicht": "fett"}}}}
        )
        self.assertEqual(sauber["weiss"]["schriften"]["knopf"], {"gewicht": "fett"})

    def test_farben_klein_geschrieben(self):
        sauber = self.pruefung.bereinigen({"weiss": {"farben": {"akzent": "#ABCDEF"}}})
        self.assertEqual(sauber, {"weiss": {"farben": {"akzent": "#abcdef"}}})
