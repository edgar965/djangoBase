# -*- coding: utf-8 -*-
"""Wie groß ist dieses Projekt — Dateien, Zeilen, Klassen nach Art.

DIE ANSAGE (Edgar, 24.08.2026)
==============================
    „ein Button der eine Statistik macht: Anzahl Dateien, Anzahl py
     Code-Dateien, Anzahl html, js, sonstige (mach Vorschlag). Anzahl
     Code-Zeilen gesamt, py, js, htm usw. Anzahl Klassen (py, js)"

WAS DER ERSTE LAUF ZEIGTE
=========================
    Übrige   47 Dateien   4.858.015 Zeilen

Mehr als das ganze übrige Projekt zusammen. Es waren die
`.pkl`-Zwischenspeicher des Kalenders, byteweise als Text gelesen, dazu
`media/` mit 2673 Bildern und Videos — darunter eines mit 1,7 GB. Eine
Statistik über QUELLTEXT darf Laufzeitdaten nicht mitzählen, und sie muss
sagen, was sie ausgelassen hat: Sonst liest sich „1119 Dateien" wie das
ganze Verzeichnis.
"""

import tempfile
from pathlib import Path

from django.test import override_settings

from djangobase.umbau.codezahlen import Codezahlen

from ..base import BasisTest


def _zaehlen(dateien):
    ordner = Path(tempfile.mkdtemp(prefix="cz_"))
    for name, inhalt in dateien.items():
        ziel = ordner / name
        ziel.parent.mkdir(parents=True, exist_ok=True)
        ziel.write_text(inhalt, encoding="utf-8")
    return Codezahlen(ordner).lesen()


class DieArtStehtAmSuffix(BasisTest):
    def test_die_sieben_arten(self):
        for name, erwartet in (
            ("a.py", "Python"),
            ("a.html", "HTML-Vorlagen"),
            ("a.js", "JavaScript"),
            ("a.css", "Stilblätter"),
            ("a.json", "Einstellungen"),
            ("a.md", "Dokumentation"),
            ("a.png", "Bilder & Binäres"),
        ):
            self.assertEqual(Codezahlen.art(name), erwartet, name)

    def test_was_nirgends_passt_faellt_nicht_weg(self):
        """Sonst stimmt die Summe nicht — und man sieht es nicht."""
        self.assertEqual(Codezahlen.art("a.seltsam"), "Übrige")

    def test_ohne_endung_ist_es_uebrig(self):
        self.assertEqual(Codezahlen.art("Makefile"), "Übrige")

    def test_die_grossschreibung_zaehlt_nicht(self):
        self.assertEqual(Codezahlen.art("BILD.PNG"), "Bilder & Binäres")


class DreiZeilenartenStattEiner(BasisTest):
    """„Anzahl Code-Zeilen" ist mehrdeutig — hier getrennt gezählt."""

    QUELLE = (
        "# ein Kommentar\n"
        "import os\n"
        "\n"
        "\n"
        "class Ding:\n"
        '    """Ein Docstring."""\n'
        "\n"
        "    def machen(self):\n"
        '        return "# kein Kommentar"\n'
    )

    def _py(self):
        return _zaehlen({"a.py": self.QUELLE}).arten["Python"]

    def test_die_drei_arten_ergeben_die_zeilenzahl(self):
        py = self._py()
        self.assertEqual(py.anweisungen + py.kommentar + py.leer, py.zeilen)

    def test_ein_gitter_in_einer_zeichenkette_ist_kein_kommentar(self):
        """Wer das mit `startswith('#')` zählt, liegt daneben — aber hier
        steht das Gitter nicht am Zeilenanfang, also greift schon die
        einfache Regel. Der AST entscheidet über Klassen und Funktionen."""
        self.assertEqual(self._py().kommentar, 1)

    def test_klassen_und_funktionen_kommen_aus_dem_ast(self):
        """Eine Klasse — und KEINE Funktion, denn `machen` ist eine Methode.

        Die Spalte zaehlt seit dem 02.09.2026 nur noch, was an keiner
        Klasse haengt (auf Ansage: „Spalte Funktionen — wenn die
        innerhalb von Klassen sind dann lass die weg"). Vorher zaehlte
        hier jedes `def`; die Zahl sagte damit ungefaehr „wie viel Code"
        statt „wie viel haengt an keiner Klasse".
        """
        py = self._py()
        self.assertEqual((py.klassen, py.funktionen), (1, 0))

    def test_eine_freie_funktion_wird_sehr_wohl_gezaehlt(self):
        """Die Gegenprobe. Ohne sie belegte der Fall oben nur, dass die
        Spalte 0 zeigt — auch eine kaputte Zaehlung taete das."""
        quelle = "".join(
            (
                "def frei():\n",
                "    return 1\n",
                "\n",
                "\n",
                "class Ding:\n",
                "    def methode(self):\n",
                "        return 2\n",
            )
        )
        py = _zaehlen({"b.py": quelle}).arten["Python"]
        self.assertEqual((py.klassen, py.funktionen), (1, 1))

    def test_eine_verschachtelte_funktion_haengt_an_keiner_klasse(self):
        """Ein `def` im `def` haengt an keiner Klasse — beide zaehlen.

        Der Fall steht hier, damit die Regel benannt ist: Gezaehlt wird
        „ausserhalb einer KLASSE", nicht „auf Modulebene"."""
        quelle = "".join(
            ("def aussen():\n", "    def innen():\n", "        return 1\n", "    return innen\n")
        )
        py = _zaehlen({"c.py": quelle}).arten["Python"]
        self.assertEqual(py.funktionen, 2)

    def test_eine_kaputte_datei_kostet_nur_ihre_klassen(self):
        """Die Zeilen zählen weiter — ein Syntaxfehler ist kein Grund,
        die Datei aus der Statistik zu werfen."""
        z = _zaehlen({"kaputt.py": "def (:\n"})
        self.assertEqual(z.arten["Python"].dateien, 1)
        self.assertEqual(z.arten["Python"].klassen, 0)


class JavaScriptWirdMitgezaehlt(BasisTest):
    def test_klassen_und_funktionen(self):
        js = _zaehlen(
            {
                "a.js": (
                    "export class Kachel {\n"
                    "    zeichnen() { return 1; }\n"
                    "}\n"
                    "function los() { return 2; }\n"
                    "const auch = (x) => x;\n"
                )
            }
        ).arten["JavaScript"]
        self.assertEqual(js.klassen, 1)
        self.assertEqual(js.funktionen, 2)

    def test_zwei_schraegstriche_sind_kommentar(self):
        js = _zaehlen({"a.js": "// hier\nlet x = 1;\n"}).arten["JavaScript"]
        self.assertEqual((js.kommentar, js.anweisungen), (1, 1))


class LaufzeitdatenZaehlenNicht(BasisTest):
    """DER BEFUND (24.08.2026): 47 Dateien mit 4,8 Millionen Zeilen."""

    DATEIEN = {
        "echt.py": "class Echt:\n    pass\n",
        "media/.cache/kalender.pkl": "x" * 200,
        "media/bilder/a.png": "x",
        "logs/out.log": "zeile\n" * 500,
        "tmp/wegwerf.py": "class Weg:\n    pass\n",
    }

    def test_nur_der_quelltext_zaehlt(self):
        z = _zaehlen(self.DATEIEN)
        self.assertEqual(z.gesamt()["dateien"], 1)
        self.assertEqual(z.gesamt()["klassen"], 1)

    def test_das_ausgelassene_wird_genannt(self):
        """Ohne diese Zahl liest sich „1119 Dateien" wie alles."""
        z = _zaehlen(self.DATEIEN)
        self.assertEqual(z.ausgelassen, 4)
        self.assertEqual(sorted(z.ausgelassen_wo), ["logs", "media", "tmp"])

    def test_zu_grosse_dateien_sind_kein_quelltext(self):
        """Ein Modell mit 174 MB heißt `.pt`, ein Video `.mp4` — aber
        auch eine `.py` mit 3 MB ist nichts, was jemand geschrieben hat."""
        ordner = Path(tempfile.mkdtemp(prefix="cz_"))
        (ordner / "riesig.py").write_text("# x\n" * 700000, encoding="utf-8")
        (ordner / "klein.py").write_text("class K:\n    pass\n", encoding="utf-8")
        z = Codezahlen(ordner).lesen()
        self.assertEqual(z.gesamt()["dateien"], 1)
        self.assertEqual(z.ausgelassen_wo.get("zu groß"), 1)


class DieSummeStimmt(BasisTest):
    DATEIEN = {
        "a.py": "class A:\n    pass\n",
        "b.html": "<div>\n</div>\n",
        "c.js": "class C {}\n",
        "d.seltsam": "was auch immer\n",
    }

    def test_die_liste_summiert_sich_zum_gesamt(self):
        """Ohne diese Eigenschaft ist eine Statistik wertlos: Man sieht
        ihr nicht an, ob etwas fehlt."""
        z = _zaehlen(self.DATEIEN)
        gesamt = z.gesamt()
        for feld in ("dateien", "zeilen", "anweisungen", "kommentar", "leer", "klassen", "funktionen"):
            self.assertEqual(sum(a[feld] for a in z.liste()), gesamt[feld], feld)

    def test_auch_leere_arten_stehen_in_der_liste(self):
        """Dass ein Projekt KEIN CSS hat, ist eine Auskunft. Eine
        fehlende Zeile liest sich als Versehen."""
        namen = [a["name"] for a in _zaehlen({"a.py": "x = 1\n"}).liste()]
        self.assertIn("Stilblätter", namen)
        self.assertEqual(len(namen), 8)

    def test_die_kennzahlen_trennen_py_und_js(self):
        k = _zaehlen(self.DATEIEN).kennzahlen()
        self.assertEqual((k["py_klassen"], k["js_klassen"]), (1, 1))
        self.assertEqual(k["klassen"], 2)

    def test_ein_leeres_verzeichnis_wirft_nicht(self):
        z = _zaehlen({})
        self.assertEqual(z.gesamt()["dateien"], 0)
        self.assertEqual(z.kennzahlen()["kommentar_anteil"], 0.0)


class GlobalerCodeWirdGetrenntGezaehlt(BasisTest):
    """Wie viel Code hängt an KEINER Klasse? (27.08.2026, auf Ansage)

    Die Spalte „Klassen" sagt, wie viele es gibt — nicht, wie viel Code
    auf Modulebene liegt. Genau das ist der Maßstab aus Kriterium 1
    und 18: Vorgaben gehören dorthin, Zustand nicht.
    """

    #: Von Hand ausgezählt — zehn Anweisungszeilen, fünf davon in der Klasse
    #: (Dekorator, ``class``, ``x``, ``def zeig``, ``return``).
    QUELLE = (
        "import os\n"
        "MAX = 5\n"
        "\n"
        "@dataclass\n"
        "class Punkt:\n"
        "    x = 1\n"
        "\n"
        "    def zeig(self):\n"
        "        return self.x\n"
        "\n"
        "def frei():\n"
        "    return 2\n"
        "\n"
        "_cache = {}\n"
    )

    def _python(self, quelle=None):
        z = _zaehlen({"a.py": quelle if quelle is not None else self.QUELLE})
        return [a for a in z.liste() if a["name"] == "Python"][0]

    def test_nur_was_ausserhalb_steht_wird_gezaehlt(self):
        """Fünf der zehn Anweisungen stehen nicht in der Klasse."""
        self.assertEqual(self._python()["ausserhalb"], 5)

    def test_der_dekorator_gehoert_zur_klasse(self):
        """``@dataclass`` steht VOR ``lineno`` und zählt trotzdem innen."""
        ohne = self.QUELLE.replace("@dataclass\n", "")
        # Eine Anweisung weniger, und sie lag innen: aussen bleibt es bei 5.
        self.assertEqual(self._python(ohne)["ausserhalb"], 5)

    def test_eine_datei_ganz_ohne_klasse_ist_ganz_aussen(self):
        eins = self._python("import os\nMAX = 5\n")
        self.assertEqual(eins["ausserhalb"], eins["anweisungen"])

    def test_eine_datei_nur_aus_klasse_hat_nichts_aussen(self):
        self.assertEqual(self._python("class A:\n    x = 1\n")["ausserhalb"], 0)

    def test_verschachtelte_klassen_zaehlen_nicht_doppelt(self):
        """Die innere Spanne liegt in der äußeren — kein Abzug zweimal."""
        quelle = "class A:\n    class B:\n        x = 1\nY = 2\n"
        self.assertEqual(self._python(quelle)["ausserhalb"], 1)

    def test_eine_kaputte_datei_zaehlt_nicht_als_globaler_code(self):
        """Ohne Syntaxbaum ist die Klassenspanne unbekannt — lieber nichts."""
        z = _zaehlen({"kaputt.py": "class ohne Doppelpunkt\n"})
        py = [a for a in z.liste() if a["name"] == "Python"][0]
        self.assertIsNone(py["ausserhalb"])

    def test_html_traegt_keine_zahl_sondern_nichts(self):
        """Eine 0 sähe aus wie ein Messergebnis. HTML hat keine Klassen."""
        z = _zaehlen({"a.html": "<p>x</p>\n"})
        html = [a for a in z.liste() if a["name"] == "HTML-Vorlagen"][0]
        self.assertIsNone(html["ausserhalb"])

    def test_die_summe_uebergeht_die_nicht_messbaren(self):
        """None darf nicht als 0 mitsummieren — und nicht alles kippen."""
        z = _zaehlen({"a.py": self.QUELLE, "b.html": "<p>x</p>\n"})
        self.assertEqual(z.gesamt()["ausserhalb"], 5)


class WasInUebrigeSteckt(BasisTest):
    """02.09.2026 — Edgar: „bei Statistik habe ich über 3 Millionen leere
    Zeilen bei Übrige? was ist das, spezifiziere und fixe."

    Es waren 72.459 Dateien unter `Mail-Archive/`, überwiegend `.eml`,
    jede byteweise als Text gelesen. Zwei Regeln sind daraus geworden, und
    beide werden hier geprüft.
    """

    #: Eine „E-Mail": Kopf, Leerzeile, Rumpf. Die Leerzeile ist die
    #: Trennung zwischen beiden — keine Quelltextzeile.
    MAIL = "From: a@b\nSubject: x\n\nText\n\n\n"

    def test_uebrige_wird_gezaehlt_aber_nicht_gelesen(self):
        z = _zaehlen({"post.eml": self.MAIL})
        u = [a for a in z.liste() if a["name"] == "Übrige"][0]
        self.assertEqual(u["dateien"], 1)
        self.assertEqual(u["zeilen"], 0)
        self.assertEqual(u["leer"], 0)
        self.assertFalse(u["gelesen"])

    def test_gegenprobe_bekannte_arten_werden_weiter_gelesen(self):
        """Sabotage-Gegenprobe: Wäre die Regel zu grob, bliebe auch
        Python bei null. Ohne diesen Fall prüft der Test oben nur, dass
        gar nichts mehr gezählt wird."""
        z = _zaehlen({"post.eml": self.MAIL, "a.py": "x = 1\n\ny = 2\n"})
        py = [a for a in z.liste() if a["name"] == "Python"][0]
        self.assertEqual(py["zeilen"], 3)
        self.assertEqual(py["leer"], 1)
        self.assertTrue(py["gelesen"])

    def test_die_aufschluesselung_nennt_endung_und_anzahl(self):
        """Die Zeile „758" allein ist keine Auskunft — genau das war die
        Frage. Nach Endung, grösste zuerst."""
        z = _zaehlen({"a.eml": self.MAIL, "b.eml": self.MAIL, "c.dump": "x\n"})
        auf = z.uebrige_arten()
        self.assertEqual([e["endung"] for e in auf], [".eml", ".dump"])
        self.assertEqual(auf[0]["dateien"], 2)

    def test_als_beispiel_steht_die_groesste_datei(self):
        """Bei 385 Dateien ohne Endung ist die erste zufällig."""
        z = _zaehlen({"klein.eml": "x\n", "gross.eml": "y" * 5000})
        self.assertEqual(z.uebrige_arten()[0]["beispiel"], "gross.eml")

    def test_ohne_endung_bekommt_einen_eigenen_eintrag(self):
        """`Makefile` und `.gitignore` fallen sonst unter den Tisch."""
        z = _zaehlen({"Makefile": "all:\n"})
        self.assertEqual(z.uebrige_arten()[0]["endung"], "(ohne Endung)")


class AblagenMeldetDasProjektSelbstAn(BasisTest):
    """Nicht wieder eine Namensliste: `Mail-Archive` stand nicht in
    ``DATEN``, und 72.459 Dateien zählten als Quelltext des Projekts.
    Django benennt Ablagen konventionell mit ``…_ROOT``.
    """

    def _wurzel(self):
        ordner = Path(tempfile.mkdtemp(prefix="cz_ablage_"))
        (ordner / "archiv").mkdir()
        (ordner / "archiv" / "post.eml").write_text("x\n", encoding="utf-8")
        (ordner / "a.py").write_text("x = 1\n", encoding="utf-8")
        return ordner

    def test_ein_root_setting_wird_ausgelassen_und_genannt(self):
        ordner = self._wurzel()
        with override_settings(MAIL_ARCHIVE_ROOT=str(ordner / "archiv")):
            z = Codezahlen(ordner).lesen()
        self.assertEqual(z.gesamt()["dateien"], 1)  # nur a.py
        self.assertEqual(z.ausgelassen, 1)
        self.assertIn("archiv", z.ausgelassen_wo)  # GENANNT

    def test_gegenprobe_ohne_das_setting_zaehlt_es_mit(self):
        """Sabotage: Fehlt die Anmeldung, ist die Datei wieder drin.
        Ohne diesen Fall belegt der Test oben nur, dass irgendetwas
        fehlt — nicht, dass es AN DIESEM Setting hängt."""
        ordner = self._wurzel()
        z = Codezahlen(ordner).lesen()
        self.assertEqual(z.gesamt()["dateien"], 2)

    def test_der_plural_dirs_wird_nicht_angefasst(self):
        """``STATICFILES_DIRS`` zeigt in `assistant` auf `templates/css`
        — ausdrücklich auf Quelltext. Nur der Singular ``…_ROOT`` meint
        eine Ablage."""
        ordner = self._wurzel()
        with override_settings(STATICFILES_DIRS=[str(ordner / "archiv")]):
            z = Codezahlen(ordner).lesen()
        self.assertEqual(z.gesamt()["dateien"], 2)

    def test_ein_root_ausserhalb_des_projekts_stoert_nicht(self):
        ordner = self._wurzel()
        with override_settings(MEDIA_ROOT=str(Path(tempfile.gettempdir()) / "ganz_woanders")):
            z = Codezahlen(ordner).lesen()
        self.assertEqual(z.gesamt()["dateien"], 2)
