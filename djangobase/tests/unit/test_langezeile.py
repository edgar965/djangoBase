# -*- coding: utf-8 -*-
u"""`LangeZeile`: was sich umbrechen laesst — und was nicht.

WARUM DIESE AUSNAHME (31.08.2026, 3DTools)
==========================================
Von zwoelf gemeldeten langen Vorlagenzeilen liessen sich sieben brechen.
Die uebrigen fuenf hingen an EINEM `{% … %}`: ein `{% include … with … %}`
mit vier Parametern, ein `{% regler %}` mit sieben. Djangos Lexer kennt
kein DOTALL — ein Tag ueber zwei Zeilen wird STUMM zu Text: Die Seite
antwortet weiter mit 200, das Element fehlt, im Log steht nichts.

Ein Befund, den man nur durch einen Fehler beheben koennte, ist keiner.
Er bleibt aber sichtbar: Die Zusammenfassung nennt die uebergangene Zahl
(„nie verschweigen, wie viel die Ausnahme schluckt").

ABGEZOGEN WIRD NUR DER LAENGSTE EINZELNE TAG. Wer fuenf kurze Tags in
einer Zeile hat, hat sehr wohl mehrere Anweisungen hintereinander — und
die trennt man.

BDD - GEGEBEN / DANN
====================
    EineLangeZeileOhneTag        ... wird gemeldet
    EineZeileAnEinemTag          ... nicht, und wird gezaehlt
    EineZeileMitMehrerenTags     ... wird gemeldet
    EineZeileImErklaertext       ... nicht
"""
import unittest

from djangobase.skills.jsregeln import LangeZeile


class LangezeilenBasis(unittest.TestCase):
    u"""Prueft die Regel unmittelbar — ohne Dateien, ohne Ablage."""

    databases = []

    def setUp(self):
        self.regel = LangeZeile()
        self.regel.unteilbar = 0

    def funde(self, *zeilen):
        return self.regel.pruefen("probe.html", list(zeilen))


class EineLangeZeileOhneTag(LangezeilenBasis):
    u"""Gegeben: 130 Zeichen gewoehnliches Markup."""

    def test_sie_wird_gemeldet(self):
        funde = self.funde("<div>" + "x" * 130 + "</div>")
        self.assertEqual(len(funde), 1, funde)
        self.assertEqual(funde[0].zeile, 1)

    def test_und_nichts_gilt_als_unteilbar(self):
        self.funde("<div>" + "x" * 130 + "</div>")
        self.assertEqual(self.regel.unteilbar, 0)

    def test_eine_kurze_zeile_bleibt_still(self):
        self.assertEqual(self.funde("<div>kurz</div>"), [])


class EineZeileAnEinemTag(LangezeilenBasis):
    u"""Gegeben: Die Ueberlaenge steckt in EINEM `{% … %}`."""

    #: Wie sie wirklich dasteht (`_einstellungen_speichern.html`).
    ECHT = ('    {% include "_einstellungen_speichern.html" '
            'with weiter_route="theatre" weiter_text="Zur Theatre-Seite" '
            'weiter_icon="fa-film" %}')

    def test_der_echte_fall_wird_uebergangen(self):
        self.assertGreater(len(self.ECHT), 120, 'Der Fall muss lang sein')
        self.assertEqual(self.funde(self.ECHT), [])

    def test_und_die_ausnahme_zaehlt_mit(self):
        u"""Eine Ausnahme, die schweigt, ist ein blinder Fleck."""
        self.funde(self.ECHT)
        self.assertEqual(self.regel.unteilbar, 1)

    def test_auch_mit_etwas_markup_davor(self):
        u"""Der zweite echte Fall (`upload_v4.html`, 132 Zeichen): Der
        `{% if %}` allein misst 70, das `<div>` drumherum ist kurz."""
        zeile = ('                <div class="pipeline-card '
                 '{% if not status_3d.hybrid_gvhmr '
                 'and not status_3d.hybrid_prompthmr %}disabled{% endif %}"')
        self.assertGreater(len(zeile), 120)
        self.assertEqual(self.funde(zeile), [])


class EineZeileMitMehrerenTags(LangezeilenBasis):
    u"""Gegeben: Mehrere Tags — jeder fuer sich kurz."""

    def test_sie_wird_gemeldet(self):
        u"""Die Gegenprobe: Ohne sie deckte die Ausnahme jede Zeile, in
        der irgendwo ein Tag steht."""
        zeile = ("<td>{{ a }}</td>" * 3
                 + "{% if x %}A{% endif %}" * 4
                 + "<td>Ende</td>")
        self.assertGreater(len(zeile), 120)
        funde = self.funde(zeile)
        self.assertEqual(len(funde), 1, funde)
        self.assertEqual(self.regel.unteilbar, 0)

    def test_ein_kurzer_tag_rettet_eine_lange_zeile_nicht(self):
        zeile = "<div>" + "x" * 130 + "{% if a %}b{% endif %}</div>"
        self.assertEqual(len(self.funde(zeile)), 1)


class EineZeileImErklaertext(LangezeilenBasis):
    u"""Gegeben: Der Beispielaufruf steht in einem `{% comment %}`."""

    def test_sie_wird_uebergangen(self):
        u"""Wer diesem Befund folgt, kuerzt die BEGRUENDUNG."""
        funde = self.funde(
            "{% comment %}",
            "    So fordert man den zweiten Knopf an:",
            "        " + "y" * 130,
            "{% endcomment %}")
        self.assertEqual(funde, [])

    def test_aber_dieselbe_zeile_ausserhalb_schon(self):
        u"""Die Gegenprobe zum Kommentar-Ausschluss."""
        funde = self.funde("        " + "y" * 130)
        self.assertEqual(len(funde), 1, funde)


class DieRegelBleibtEinEinzelstueck(LangezeilenBasis):
    u"""Gegeben: `REGELN` haelt EINE Instanz je Regel, ueber Laeufe hinweg.

    Deshalb setzt `jsbefunde.laufen` die Zaehler vor jedem Lauf zurueck.
    Faellt das weg, waechst `unteilbar` von Lauf zu Lauf — eine Zahl, die
    niemand nachrechnet und die trotzdem in der Kopfzeile steht.
    """

    def test_der_zaehler_ist_am_objekt(self):
        self.funde(EineZeileAnEinemTag.ECHT)
        self.funde(EineZeileAnEinemTag.ECHT)
        self.assertEqual(self.regel.unteilbar, 2)

    def test_und_jsbefunde_setzt_ihn_zurueck(self):
        from djangobase.skills.jsbefunde import JsBefunde
        from djangobase.skills.jsregeln import REGELN

        for regel in REGELN:
            if isinstance(regel, LangeZeile):
                regel.unteilbar = 99
        quelle = JsBefunde.laufen.__doc__ or ''
        del quelle          # nur zur Klarheit: geprueft wird der Lauf
        JsBefunde().laufen()
        offen = [r.unteilbar for r in REGELN if isinstance(r, LangeZeile)]
        # KLEINER ALS DER STARTWERT, NICHT „ungleich 99" (Befund CodeRabbit,
        # 31.08.2026): Bliebe der Ruecksetzer weg, stuende hinterher 99 + n da,
        # wobei n die im Projekt gefundenen unteilbaren Zeilen sind. Fuer jedes
        # n > 0 war ``assertNotIn(99, …)`` trotzdem gruen — der Test verlor
        # seinen Wert in dem Moment, in dem irgendeine Vorlage eine lange
        # ``{% … %}``-Zeile bekam, und sagte das niemandem.
        self.assertTrue(
            offen and all(w < 99 for w in offen),
            'Der Zaehler wurde nicht zurueckgesetzt (Werte: %s)' % offen)
