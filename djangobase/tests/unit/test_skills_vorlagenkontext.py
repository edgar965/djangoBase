# -*- coding: utf-8 -*-
u"""Vorlagen-Kontext — was die Ansicht liefert und was die Vorlage liest.

WARUM DIESE DATEI AM 23.08.2026 ENTSTAND
========================================
Das Werkzeug meldete an CamTrack **29 Befunde**. Nachgeprueft, einzeln:

    21 x TOT       alle echt — darunter eine Kamera-Abfrage je Seiten-
                   aufruf fuer sechs Namen, die `help/recordings.html`
                   nicht liest
     2 x FEHLEND   echt: zwei Seiten ohne `title`, der Reiter blieb leer
     7 x FEHLEND   **alle falsch**

Die sieben sahen so aus::

    {% if is_edit %}...{{ camera.name }}...{% endif %}
    {% if is_live %}<video src="{{ live_media_url }}">{% endif %}
    {% if tab.key == zb_aktiv or forloop.first and not zb_aktiv %}
    Haupt: {{ main_probe.width|default:'?' }}

Die Vorlage rechnet jedes Mal damit, dass der Name fehlt — im `{% if %}`
oder mit `|default:`. Ein Pruefer, der zu hundert Prozent falsch meldet,
wird abgestellt; danach faengt er auch die echten zwei nicht mehr.

DIE GEGENPROBE IST DER WICHTIGSTE TEST HIER
===========================================
`vorlagen-kontext` ist das einzige Werkzeug OHNE Anlassfall — es braucht
den Django-Lader, und in einem Wegwerf-Verzeichnis gibt es keine Vorlagen.
Der `anlassfall-check` kann also nicht sagen, ob es blind geworden ist.
Genau deshalb steht `test_ein_wirklich_fehlender_name_wird_gemeldet` hier
an erster Stelle: Beide Ausnahmen duerfen den einfachen Fall nicht
verschlucken.
"""
import tempfile
from pathlib import Path

from django.template import engines
from django.test import override_settings

from djangobase.skills.vorlagenkontext import Vorlagensicht

from ..base import BasisTest


class Vorlagenprobe(Vorlagensicht):
    u"""`Vorlagensicht` fuer eine Vorlage aus dem Speicher.

    Der Lader braucht eine Datei auf der Platte; hier geht es nur um das
    Ablaufen des Knotenbaums, und den liefert `from_string` genauso.
    """

    def __init__(self, quelle):
        self.name = '<probe>'
        self.gelesen = set()
        self.fest = set()
        self.lokal = set()
        self.eingebunden = set()
        self._sammeln(engines['django'].from_string(quelle).template)


class WasDieVorlageUnbedingtLiest(BasisTest):

    # ------------------------------------------------- die Gegenprobe zuerst
    def test_ein_wirklich_fehlender_name_wird_gemeldet(self):
        u"""OHNE DIESEN TEST IST ALLES ANDERE WERTLOS.

        Beide Ausnahmen unten machen das Werkzeug leiser. Wenn sie es zu
        leise machen, faellt es hier auf.
        """
        probe = Vorlagenprobe('<h1>{{ titel }}</h1>')
        self.assertIn('titel', probe.fest)

    def test_auch_neben_einer_bedingung_bleibt_der_feste_name_fest(self):
        probe = Vorlagenprobe('{% if a %}x{% endif %}{{ titel }}')
        self.assertIn('titel', probe.fest)
        self.assertNotIn('a', probe.fest)

    def test_derselbe_name_fest_und_bedingt_gilt_als_fest(self):
        u"""Wer ihn einmal ohne Netz liest, braucht ihn."""
        probe = Vorlagenprobe('{{ x }}{% if x %}y{% endif %}')
        self.assertIn('x', probe.fest)

    # ------------------------------------------------------ `{% if %}`-Fall
    def test_im_rumpf_einer_bedingung_ist_der_name_wahlfrei(self):
        u"""`{% if is_edit %}...{{ camera.name }}...{% endif %}` — auf dem
        Anlegen-Weg gibt es keine Kamera, und die Vorlage weiss das."""
        probe = Vorlagenprobe('{% if is_edit %}{{ camera.name }}{% endif %}')
        self.assertIn('camera', probe.gelesen)
        self.assertNotIn('camera', probe.fest)

    def test_die_bedingung_selbst_macht_den_namen_wahlfrei(self):
        u"""`{% if tab.key == zb_aktiv or forloop.first and not zb_aktiv %}`
        — der Name wird auf Abwesenheit GEPRUEFT."""
        probe = Vorlagenprobe('{% if zb_aktiv %}x{% endif %}')
        self.assertNotIn('zb_aktiv', probe.fest)

    def test_auch_der_else_zweig_zaehlt_als_bedingt(self):
        u"""Django baut aus `{% if %}`/`{% elif %}`/`{% else %}` EINEN
        Knoten."""
        probe = Vorlagenprobe(
            '{% if d.ok %}x{% elif d %}{{ d.error }}{% else %}{{ leer }}'
            '{% endif %}')
        self.assertNotIn('d', probe.fest)
        self.assertNotIn('leer', probe.fest)

    def test_verschachtelt_bleibt_es_bedingt(self):
        probe = Vorlagenprobe(
            '{% if a %}{% for z in liste %}{{ tief }}{% endfor %}{% endif %}')
        self.assertNotIn('tief', probe.fest)

    # -------------------------------------------------------- `|default:`
    def test_ein_ersatzwert_macht_den_namen_wahlfrei(self):
        u"""`{{ main_probe.width|default:'?' }}` sagt daneben, was bei
        Abwesenheit erscheinen soll."""
        probe = Vorlagenprobe("{{ main_probe.width|default:'?' }}")
        self.assertIn('main_probe', probe.gelesen)
        self.assertNotIn('main_probe', probe.fest)

    def test_default_if_none_zaehlt_genauso(self):
        probe = Vorlagenprobe("{{ x|default_if_none:'-' }}")
        self.assertNotIn('x', probe.fest)

    def test_ein_anderer_filter_macht_ihn_nicht_wahlfrei(self):
        u"""`|upper` liefert keinen Ersatz — fehlt der Name, steht dort
        nichts."""
        probe = Vorlagenprobe('{{ x|upper }}')
        self.assertIn('x', probe.fest)

    def test_der_ersatzwert_gilt_nur_fuer_den_eigenen_ausdruck(self):
        probe = Vorlagenprobe("{{ a|default:'?' }}{{ b }}")
        self.assertNotIn('a', probe.fest)
        self.assertIn('b', probe.fest)


class DasWerkzeugAmEchtenProjekt(BasisTest):
    u"""Der ganze Weg: `render()`-Aufruf im Quelltext gegen echte Vorlage."""

    def _lauf(self, ansicht_py, vorlagen):
        from django.conf import settings
        from django.template import engines as motoren

        from djangobase.skills import werkzeug_finden

        ordner = Path(tempfile.mkdtemp(prefix='vk_'))
        (ordner / 'views.py').write_text(ansicht_py, encoding='utf-8')
        vorlagenordner = ordner / 'templates'
        vorlagenordner.mkdir()
        for name, inhalt in vorlagen.items():
            (vorlagenordner / name).write_text(inhalt, encoding='utf-8')

        werkzeug = werkzeug_finden('vorlagen-kontext')
        werkzeug.wurzel = lambda: ordner
        einstellung = [dict(settings.TEMPLATES[0])]
        einstellung[0]['DIRS'] = [str(vorlagenordner)]
        with override_settings(TEMPLATES=einstellung):
            # Die Motoren haengen an den Einstellungen und werden einmal
            # gebaut — ohne das Leeren sieht der Lader den Wegwerf-Ordner
            # nicht.
            motoren._engines = {}
            try:
                return werkzeug.pruefen()
            finally:
                motoren._engines = {}

    def test_ein_uebergebener_name_den_niemand_liest_ist_TOT(self):
        satz = self._lauf(
            "def x(request):\n"
            "    return render(request, 'a.html', {'ungenutzt': 1})\n",
            {'a.html': '<p>nichts</p>'})
        self.assertTrue(any('TOT: ungenutzt' in b.was for b in satz.befunde),
                        [b.was for b in satz.befunde])

    def test_ein_gelesener_name_den_niemand_liefert_ist_FEHLEND(self):
        u"""Der Name muss einer sein, den KEIN Kontextprozessor liefert.

        Hier stand ``titel``. In CamTrack liefert ein Kontextprozessor
        genau diesen Namen an jede Vorlage — das Werkzeug zog ihn also zu
        Recht ab, und die Pruefung fiel durch, obwohl das Werkzeug richtig
        lag. Sie haette in jedem Projekt mit einem ``titel``-Prozessor
        rot gemeldet.

        Eine Pruefung, die vom Wirtsprojekt abhaengt, prueft nicht das
        Werkzeug. Der Name traegt deshalb jetzt ein Praefix, das in
        keinem Projekt vorkommt.
        """
        satz = self._lauf(
            "def x(request):\n"
            "    return render(request, 'a.html', {})\n",
            {'a.html': '<h1>{{ pruefname_ohne_lieferant }}</h1>'})
        self.assertTrue(
            any('FEHLEND: pruefname_ohne_lieferant' in b.was
                for b in satz.befunde),
            [b.was for b in satz.befunde])

    def test_ein_name_hinter_einer_bedingung_ist_kein_befund(self):
        u"""Der Fall, der am 23.08.2026 siebenmal falsch gemeldet wurde."""
        satz = self._lauf(
            "def x(request):\n"
            "    return render(request, 'a.html', {'is_edit': False})\n",
            {'a.html': '{% if is_edit %}{{ camera.name }}{% endif %}'})
        self.assertFalse([b for b in satz.befunde if 'camera' in b.was],
                         [b.was for b in satz.befunde])
