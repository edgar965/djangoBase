# -*- coding: utf-8 -*-
u"""Zwischendateien ohne ``dir=`` — und die Ausnahmen, die bleiben muessen.

Der ``anlassfall-check`` faehrt das Werkzeug an seinem eigenen Fall.
Hier stehen die Formen daneben, an denen ein solcher Pruefer zu viel
meldet: Fehlalarme sind teurer als fehlende Befunde, weil sie die
echten verdecken.

DIE VORGESCHICHTE
=================
Aus ``tempfile`` ohne ``dir=`` sind in einem Projekt rund 100 GB
Datenmuell auf C: entstanden. In assistant fanden sich sechs solche
Stellen — jede legt eine VOLLSTAENDIGE Kopie an (Mail-Anhang, PDF beim
Verkleinern, WAV beim Entrauschen).

BDD - GEGEBEN / DANN
====================
    EineZwischendateiOhneOrt ... wird gemeldet
    EineMitOrt               ... nicht
    EinTest                  ... nicht
    JedeAnlegerfunktion      ... wird erkannt
"""
from djangobase.skills.systemablage import Systemablage

from .test_neue_werkzeuge import WerkzeugBasis


class EineZwischendateiOhneOrt(WerkzeugBasis):
    u"""Gegeben: Der Ort bleibt offen — dann waehlt ihn das System."""

    def test_mkstemp_wird_gemeldet(self):
        projekt = self.projekt({
            'a.py': "import tempfile\n\nx = tempfile.mkstemp(suffix='.pdf')\n"})
        zeilen = projekt.fahren(Systemablage)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('a.py:3', zeilen[0]['ort'])

    def test_die_meldung_nennt_den_aufruf(self):
        projekt = self.projekt({'a.py': "import tempfile\nx = tempfile.mkstemp()\n"})
        self.assertIn('mkstemp', projekt.fahren(Systemablage)[0]['befund'])

    def test_auch_direkt_importiert(self):
        u"""``from tempfile import mkstemp`` ist derselbe Aufruf."""
        projekt = self.projekt({
            'a.py': "from tempfile import mkstemp\nx = mkstemp()\n"})
        self.assertEqual(len(projekt.fahren(Systemablage)), 1)

    def test_mehrere_in_einer_datei_zaehlen_einzeln(self):
        projekt = self.projekt({
            'a.py': ("import tempfile\n"
                     "x = tempfile.mkstemp()\n"
                     "y = tempfile.mkstemp()\n")})
        self.assertEqual(len(projekt.fahren(Systemablage)), 2)


class JedeAnlegerfunktion(WerkzeugBasis):
    u"""Gegeben: ``tempfile`` bietet mehrere Wege zum selben Ergebnis."""

    def test_alle_werden_erkannt(self):
        zeilen = ['import tempfile']
        for name in Systemablage.ANLEGER:
            zeilen.append(f'x = tempfile.{name}()')
        projekt = self.projekt({'a.py': '\n'.join(zeilen) + '\n'})
        self.assertEqual(len(projekt.fahren(Systemablage)),
                         len(Systemablage.ANLEGER))

    def test_ein_verzeichnis_zaehlt_mit(self):
        u"""``TemporaryDirectory`` ist der teuerste Fall — dort landet
        nicht eine Datei, sondern ein ganzer Ablauf."""
        projekt = self.projekt({
            'a.py': ("import tempfile\n"
                     "with tempfile.TemporaryDirectory() as d:\n"
                     "    pass\n")})
        self.assertEqual(len(projekt.fahren(Systemablage)), 1)


class EineMitOrt(WerkzeugBasis):
    u"""Gegeben: ``dir=`` ist angegeben."""

    def test_sie_wird_nicht_gemeldet(self):
        projekt = self.projekt({
            'a.py': ("import tempfile\n"
                     "x = tempfile.mkstemp(dir='/projekt/tmp')\n")})
        self.assertEqual(projekt.fahren(Systemablage), [])

    def test_egal_was_darin_steht(self):
        u"""Wohin genau, entscheidet das Projekt — nicht dieses
        Werkzeug."""
        projekt = self.projekt({
            'a.py': ("import tempfile\n"
                     "from django.conf import settings\n"
                     "x = tempfile.mkstemp(dir=settings.BASE_DIR)\n")})
        self.assertEqual(projekt.fahren(Systemablage), [])

    def test_auch_neben_anderen_angaben(self):
        projekt = self.projekt({
            'a.py': ("import tempfile\n"
                     "x = tempfile.mkstemp(suffix='.pdf', prefix='a_',\n"
                     "                     dir='/projekt/tmp')\n")})
        self.assertEqual(projekt.fahren(Systemablage), [])

    def test_aber_die_daneben_schon(self):
        u"""Die Gegenprobe: Eine richtige Stelle darf die falsche
        daneben nicht verdecken."""
        projekt = self.projekt({
            'a.py': ("import tempfile\n"
                     "gut = tempfile.mkstemp(dir='/projekt/tmp')\n"
                     "schlecht = tempfile.mkstemp()\n")})
        zeilen = projekt.fahren(Systemablage)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('a.py:3', zeilen[0]['ort'])


class EinTest(WerkzeugBasis):
    u"""Gegeben: Eine Pruefung legt eine Zwischendatei an.

    UEBERGANGEN WIRD NUR, WAS SICH SELBST RAEUMT (31.08.2026). Der Satz
    „ein Wegwerf-Verzeichnis in einer Pruefung verschwindet mit ihr"
    stimmt fuer `TemporaryDirectory` und `NamedTemporaryFile` in einem
    `with`-Block — und fuer `mkdtemp`/`mkstemp` gerade nicht: Beide geben
    einen Pfad zurueck und vergessen ihn; das Aufraeumen liegt beim
    Aufrufer (so steht es auch in der Python-Doku zu `mkstemp`).

    DER BELEG: Im Systemtemp lagen an dem Tag **1.761 Verzeichnisse** aus
    Prueflaeufen — 1.717 `kr_*` aus `test_skills_klassenreif.py` und 44
    `kk_*` aus `test_skills_klassenkandidat.py`, das aelteste fuenf Tage
    alt. Beide riefen `mkdtemp` je Prueffall und raeumten nie. Die
    Ausnahme hat damit genau den Schaden gedeckt, den dieses Werkzeug
    verhindern soll — dieselbe Klasse wie die 779 `mail_test_archive_*`
    im Projekt `assistant`.

    Abhilfe im Projekt: `djangobase/tests/wegwerfordner.py`.
    """

    def test_selbstraeumendes_in_pruefung_uebergangen(self):
        u"""`TemporaryDirectory` im `with` — der Ordner ist danach weg."""
        projekt = self.projekt({
            'app/test_x.py': "import tempfile\n"
                             "with tempfile.TemporaryDirectory() as o:\n"
                             "    pass\n"})
        self.assertEqual(projekt.fahren(Systemablage), [])

    def test_mkstemp_in_pruefung_wird_gemeldet(self):
        u"""Am Dateinamen als Pruefung erkannt — und trotzdem gemeldet."""
        projekt = self.projekt({
            'app/test_x.py': "import tempfile\nx = tempfile.mkstemp()\n"})
        zeilen = projekt.fahren(Systemablage)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('test_x.py', zeilen[0]['ort'])

    def test_mkdtemp_im_pruefordner_wird_gemeldet(self):
        u"""Am Ordner als Pruefung erkannt — und trotzdem gemeldet."""
        projekt = self.projekt({
            'app/tests/hilfe.py': "import tempfile\n"
                                  "x = tempfile.mkdtemp()\n"})
        zeilen = projekt.fahren(Systemablage)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('hilfe.py', zeilen[0]['ort'])

    def test_mit_dir_bleibt_uebergangen(self):
        u"""`dir=` ist der richtige Weg — auch in einer Pruefung."""
        projekt = self.projekt({
            'app/tests/hilfe.py': "import tempfile\n"
                                  "x = tempfile.mkdtemp(dir='irgendwo')\n"})
        self.assertEqual(projekt.fahren(Systemablage), [])

    def test_produktivcode_daneben_auch(self):
        projekt = self.projekt({
            'app/tests/hilfe.py': "import tempfile\nx = tempfile.mkstemp()\n",
            'app/dienst.py': "import tempfile\nx = tempfile.mkstemp()\n"})
        orte = [z['ort'] for z in projekt.fahren(Systemablage)]
        self.assertEqual(len(orte), 2, orte)
        self.assertTrue(any('dienst.py' in o for o in orte), orte)
        self.assertTrue(any('hilfe.py' in o for o in orte), orte)


class EineKaputteDatei(WerkzeugBasis):
    u"""Gegeben: Eine Datei, die sich nicht zerlegen laesst."""

    def test_sie_wirft_nicht(self):
        projekt = self.projekt({
            'kaputt.py': "def (:\n",
            'gut.py': "import tempfile\nx = tempfile.mkstemp()\n"})
        zeilen = projekt.fahren(Systemablage)
        self.assertEqual(len(zeilen), 1, zeilen)


class DerEigeneAnlassfall(WerkzeugBasis):
    u"""Gegeben: Der Fall, den das Werkzeug bei sich traegt."""

    def test_er_wird_gefunden(self):
        fall = Systemablage.anlassfall
        projekt = self.projekt(fall.dateien)
        zeilen = fall.dateibezogen(projekt.fahren(Systemablage))
        self.assertGreaterEqual(len(zeilen), fall.mindestens, zeilen)
        self.assertLessEqual(len(zeilen), fall.hoechstens, zeilen)
        self.assertIn(fall.erwartet_in, zeilen[0]['ort'])

    def test_und_im_leeren_findet_es_nichts(self):
        self.assertEqual(self.projekt({}).fahren(Systemablage), [])


class EineBelegteAusnahme(WerkzeugBasis):
    u"""Gegeben: Der Vermerk nimmt die Stelle von DIESER Lehre aus.

    DER FALL (31.08.2026, assistant): ``_vorlage_kopieren`` legt die
    Datei mit Absicht im System-Zwischenspeicher an — ACE-Step prueft
    den uebergebenen Pfad mit ``commonpath(...) == gettempdir()`` und
    weist jeden anderen mit einem Fehler ab. Der Vermerk stand da,
    aber dieses Werkzeug kannte gar keine Einzelfall-Ausnahme.
    """

    MIT_VERMERK = (
        "import tempfile\n\n\n"
        "def kopieren():\n"
        '    u"""Der fremde Dienst nimmt nur Pfade aus dem Temp an.\n\n'
        '    Lehre gilt hier nicht ("keine-temp-dateien-im-system"): Das\n'
        "    ist eine Aussage ueber ein FREMDES Programm.\n"
        '    """\n'
        "    return tempfile.mkstemp(prefix='ace_')\n")

    def test_die_stelle_wird_nicht_gemeldet(self):
        projekt = self.projekt({'a.py': self.MIT_VERMERK})
        self.assertEqual(projekt.fahren(Systemablage), [])

    def test_ohne_vermerk_bleibt_es_ein_befund(self):
        u"""Die Gegenprobe: Das Werkzeug ist nicht still geworden."""
        ohne = self.MIT_VERMERK.replace(
            'Lehre gilt hier nicht ("keine-temp-dateien-im-system"): Das',
            'Der Grund steht hier nicht: Das')
        zeilen = self.projekt({'a.py': ohne}).fahren(Systemablage)
        self.assertEqual(len(zeilen), 1, zeilen)

    def test_ein_vermerk_fuer_eine_ANDERE_lehre_zaehlt_nicht(self):
        u"""Der Vermerk gilt nur fuer die Lehre, die er beim Namen nennt."""
        fremd = self.MIT_VERMERK.replace('keine-temp-dateien-im-system',
                                         'irgendeine-andere-lehre')
        zeilen = self.projekt({'a.py': fremd}).fahren(Systemablage)
        self.assertEqual(len(zeilen), 1, zeilen)


class EineOrtsnennung(WerkzeugBasis):
    u"""Gegeben: `gettempdir()` — der Aufruf legt selbst nichts an.

    DER FALL (31.08.2026, HumanBody): In `collision/test_collision.py`
    standen vier `mkstemp`-Stellen und eine Zeile

        os.path.join(tempfile.gettempdir(), 'out.mp4')

    Die vier meldete das Werkzeug, die fuenfte nicht — dabei landet auch
    sie unter Windows auf C:. Ein `dir=` gibt es hier nicht; jeder Aufruf
    ist ein Befund.
    """

    def test_sie_wird_gemeldet(self):
        projekt = self.projekt({
            'a.py': ("import os\nimport tempfile\n"
                     "z = os.path.join(tempfile.gettempdir(), 'out.mp4')\n")})
        zeilen = projekt.fahren(Systemablage)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('a.py:3', zeilen[0]['ort'])

    def test_die_meldung_nennt_den_aufruf(self):
        projekt = self.projekt({
            'a.py': "from tempfile import gettempdir\nz = gettempdir()\n"})
        self.assertIn('gettempdir', projekt.fahren(Systemablage)[0]['befund'])

    def test_auch_in_einer_pruefung(self):
        u"""Kein Anleger, also greift die Test-Ausnahme hier gar nicht."""
        projekt = self.projekt({
            'app/tests/x.py': "import tempfile\nz = tempfile.gettempdir()\n"})
        self.assertEqual(len(projekt.fahren(Systemablage)), 1)

    def test_ein_vermerk_nimmt_sie_aus(self):
        u"""Der belegte Fall: `gettempdir()` in einer ZUSICHERUNG.

        `test_projekt_temp.py` prueft, dass eine Datei NICHT dort liegt —
        geschrieben wird nichts. Ohne diese Ausnahme meldete das Werkzeug
        genau die Pruefung, die seine eigene Lehre durchsetzt.
        """
        projekt = self.projekt({
            'a.py': ("import tempfile\n\n\n"
                     "def pruefen(pfad):\n"
                     '    # Steht hier in einer ZUSICHERUNG.\n'
                     '    # Lehre gilt hier nicht\n'
                     '    # ("keine-temp-dateien-im-system").\n'
                     "    return not pfad.startswith(tempfile.gettempdir())\n")})
        self.assertEqual(projekt.fahren(Systemablage), [])

    def test_ohne_vermerk_bleibt_es_ein_befund(self):
        u"""Die Gegenprobe zur Ausnahme."""
        projekt = self.projekt({
            'a.py': ("import tempfile\n\n\n"
                     "def pruefen(pfad):\n"
                     "    return not pfad.startswith(tempfile.gettempdir())\n")})
        self.assertEqual(len(projekt.fahren(Systemablage)), 1)
