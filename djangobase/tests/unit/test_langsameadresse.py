# -*- coding: utf-8 -*-
u"""``localhost`` als Verbindungsziel — die Ausnahmen sind das Schwierige.

Der ``anlassfall-check`` faehrt das Werkzeug an seinem eigenen Fall. Hier
stehen die Formen daneben, an denen ein solches Werkzeug typischerweise
zu viel meldet — und Fehlalarme sind hier teurer als fehlende Befunde:
Wer ``localhost`` in einem Docstring gemeldet bekommt, glaubt dem
Werkzeug beim naechsten Mal nicht mehr.

DIE MESSUNG DAHINTER (28.08.2026)
=================================
Gegen Ollama, je fuenf Aufrufe im Wechsel: ueber ``localhost`` 2.923 ms,
ueber ``127.0.0.1`` 840 ms. Der Unterschied ist die Aufloesung auf
``::1``, wo niemand lauscht.

BDD - GEGEBEN / DANN
====================
    EineAdresseImCode        ... wird gemeldet
    EinBeschriebenerFall     ... Docstring und Kommentar nicht
    EineNamensliste          ... ALLOWED_HOSTS nicht
    EineJsDatei              ... auch dort, ohne Kommentare
    EineKaputteDatei         ... meldet nichts, wirft nicht
"""
from djangobase.skills.langsameadresse import LangsameAdresse

from .test_neue_werkzeuge import WerkzeugBasis


class EineAdresseImCode(WerkzeugBasis):
    u"""Gegeben: Eine Zeichenkette, die ein Verbindungsziel ist."""

    def test_sie_wird_gemeldet(self):
        projekt = self.projekt({
            'klient.py': "BASIS = 'http://localhost:11434'\n"})
        zeilen = projekt.fahren(LangsameAdresse)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('klient.py:1', zeilen[0]['ort'])

    def test_jedes_schema(self):
        u"""Die Aufloesung haengt am Namen, nicht am Schema — ein
        Datenbankzugang ueber ``localhost`` kostet dasselbe."""
        projekt = self.projekt({
            'a.py': ("A = 'ws://localhost:9000/strom'\n"
                     "B = 'postgres://nutzer@localhost:5432/db'\n"
                     "C = 'https://localhost:8443'\n")})
        self.assertEqual(len(projekt.fahren(LangsameAdresse)), 3)

    def test_127_0_0_1_nicht(self):
        projekt = self.projekt({
            'a.py': "BASIS = 'http://127.0.0.1:11434'\n"})
        self.assertEqual(projekt.fahren(LangsameAdresse), [])

    def test_und_0_0_0_0_auch_nicht(self):
        u"""Das ist die Adresse, auf der ein Server LAUSCHT."""
        projekt = self.projekt({
            'a.py': "ADRESSE = 'http://0.0.0.0:8090'\n"})
        self.assertEqual(projekt.fahren(LangsameAdresse), [])


class EinBeschriebenerFall(WerkzeugBasis):
    u"""Gegeben: Jemand schreibt AUF, dass ``localhost`` teuer ist.

    Genau diese Datei duerfte das Werkzeug nicht melden — sonst meldet
    es am Ende seine eigene Dokumentation.
    """

    def test_ein_docstring_ist_kein_verbindungsziel(self):
        projekt = self.projekt({
            'a.py': ('u"""Nicht http://localhost nehmen.\n'
                     '"""\n'
                     "BASIS = 'http://127.0.0.1:11434'\n")})
        self.assertEqual(projekt.fahren(LangsameAdresse), [])

    def test_auch_nicht_der_einer_funktion(self):
        projekt = self.projekt({
            'a.py': ("def holen():\n"
                     '    """Frueher http://localhost:11434."""\n'
                     "    return 1\n")})
        self.assertEqual(projekt.fahren(LangsameAdresse), [])

    def test_und_ein_kommentar_erst_recht_nicht(self):
        projekt = self.projekt({
            'a.py': ("# Nicht http://localhost: loest auf ::1 auf.\n"
                     "BASIS = 'http://127.0.0.1:11434'\n")})
        self.assertEqual(projekt.fahren(LangsameAdresse), [])

    def test_aber_der_code_daneben_schon(self):
        u"""Die Gegenprobe zu den dreien: In derselben Datei mit
        Docstring UND Kommentar wird die echte Zeile gefunden."""
        projekt = self.projekt({
            'a.py': ('u"""Frueher http://localhost:11434."""\n'
                     "# Siehe http://localhost:11434\n"
                     "BASIS = 'http://localhost:11434'\n")})
        zeilen = projekt.fahren(LangsameAdresse)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('a.py:3', zeilen[0]['ort'])


class EineNamensliste(WerkzeugBasis):
    u"""Gegeben: ``localhost`` steht als NAME da, nicht als Adresse."""

    def test_allowed_hosts_wird_nicht_gemeldet(self):
        u"""Das ist der Vergleich gegen den ``Host``-Kopf einer
        EINGEHENDEN Anfrage — dort loest niemand etwas auf."""
        projekt = self.projekt({
            'settings.py': "ALLOWED_HOSTS = ['localhost', '127.0.0.1']\n"})
        self.assertEqual(projekt.fahren(LangsameAdresse), [])

    def test_ein_blosser_rechnername_auch_nicht(self):
        projekt = self.projekt({'a.py': "RECHNER = 'localhost'\n"})
        self.assertEqual(projekt.fahren(LangsameAdresse), [])

    def test_csrf_trusted_origins_auch_nicht(self):
        u"""DER ERSTE FEHLALARM (28.08.2026, assistant).

        Dieselbe Sorte wie ``ALLOWED_HOSTS``, nur MIT ``//`` — eine
        Herkunft wird nun einmal so geschrieben. Aufgeloest wird auch
        hier nichts: Django vergleicht gegen den ``Origin``-Kopf einer
        EINGEHENDEN Anfrage.
        """
        projekt = self.projekt({
            'settings.py': ("CSRF_TRUSTED_ORIGINS = [\n"
                            "    'http://localhost:8001',\n"
                            "    'http://127.0.0.1:8001',\n"
                            "]\n")})
        self.assertEqual(projekt.fahren(LangsameAdresse), [])

    def test_aber_eine_echte_adresse_in_derselben_datei_schon(self):
        u"""Die Gegenprobe: Die Ausnahme gilt der Zuweisung, nicht der
        Datei. Sonst waere eine ganze ``settings.py`` blind."""
        projekt = self.projekt({
            'settings.py': ("CSRF_TRUSTED_ORIGINS = ['http://localhost:8001']\n"
                            "OLLAMA = 'http://localhost:11434'\n")})
        zeilen = projekt.fahren(LangsameAdresse)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('settings.py:2', zeilen[0]['ort'])


class EinePruefung(WerkzeugBasis):
    u"""Gegeben: Ein Test, der die Adresse ABWEIST."""

    def test_er_wird_nicht_gemeldet(self):
        u"""DER ZWEITE FEHLALARM (28.08.2026, assistant).

        ``test_meyer_features`` prueft, dass ``http://localhost/`` als
        Ziel abgelehnt wird — Schutz gegen SSRF. Ohne die Zeichenkette
        gaebe es die Pruefung nicht.
        """
        projekt = self.projekt({
            'mail/tests/unit/test_ssrf.py':
                ("def test_weist_ab(self):\n"
                 "    self.assertFalse(pruefen('http://localhost/')[0])\n")})
        self.assertEqual(projekt.fahren(LangsameAdresse), [])

    def test_auch_ohne_tests_ordner(self):
        u"""Zwei Haelften, zwei Faelle: Diese Datei liegt in KEINEM
        Testordner — sie wird nur am Namen erkannt. Ohne diesen Fall
        koennte die Namenspruefung wegfallen, ohne dass etwas rot wird
        (bemerkt bei der Gegenprobe am 28.08.2026)."""
        projekt = self.projekt({
            'app/test_ssrf.py': "ZIEL = 'http://localhost:8001'\n"})
        self.assertEqual(projekt.fahren(LangsameAdresse), [])

    def test_auch_im_tests_ordner_ohne_praefix(self):
        projekt = self.projekt({
            'app/tests/hilfe.py': "ZIEL = 'http://localhost:8001'\n"})
        self.assertEqual(projekt.fahren(LangsameAdresse), [])

    def test_aber_produktivcode_daneben_schon(self):
        projekt = self.projekt({
            'app/tests/hilfe.py': "ZIEL = 'http://localhost:8001'\n",
            'app/klient.py': "ZIEL = 'http://localhost:8001'\n"})
        zeilen = projekt.fahren(LangsameAdresse)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('klient.py', zeilen[0]['ort'])


class EineJsDatei(WerkzeugBasis):
    u"""Gegeben: Die Adresse steht im Frontend."""

    def test_sie_wird_gefunden(self):
        projekt = self.projekt({
            'static/app.js': "const B = 'http://localhost:8001/api';\n"})
        zeilen = projekt.fahren(LangsameAdresse)
        self.assertEqual(len(zeilen), 1, zeilen)

    def test_ein_zeilenkommentar_nicht(self):
        projekt = self.projekt({
            'static/app.js': ("// frueher http://localhost:8001\n"
                              " * auch http://localhost:8001\n"
                              "const B = 'http://127.0.0.1:8001/api';\n")})
        self.assertEqual(projekt.fahren(LangsameAdresse), [])


class EineKaputteDatei(WerkzeugBasis):
    u"""Gegeben: Eine Datei, die sich nicht zerlegen laesst.

    Ein Werkzeug, das daran stirbt, reisst den Sammellauf mit — und eine
    abgebrochene Liste sieht aus wie „keine Befunde"."""

    def test_sie_wirft_nicht(self):
        projekt = self.projekt({
            'kaputt.py': "def (:\n",
            'gut.py': "B = 'http://localhost:11434'\n"})
        zeilen = projekt.fahren(LangsameAdresse)
        self.assertEqual(len(zeilen), 1, zeilen)
        self.assertIn('gut.py', zeilen[0]['ort'])


class DerEigeneAnlassfall(WerkzeugBasis):
    u"""Gegeben: Der Fall, den das Werkzeug bei sich traegt."""

    def test_er_wird_gefunden(self):
        fall = LangsameAdresse.anlassfall
        projekt = self.projekt(fall.dateien)
        zeilen = fall.dateibezogen(projekt.fahren(LangsameAdresse))
        self.assertGreaterEqual(len(zeilen), fall.mindestens, zeilen)
        self.assertLessEqual(len(zeilen), fall.hoechstens, zeilen)
        self.assertIn(fall.erwartet_in, zeilen[0]['ort'])

    def test_und_im_leeren_findet_es_nichts(self):
        self.assertEqual(self.projekt({}).fahren(LangsameAdresse), [])
