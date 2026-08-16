# -*- coding: utf-8 -*-
u"""Tests fuer die Pflicht-Menuepunkte (Hilfe -> Skills / Skills1 / Skills2).

WARUM ES DIESE TESTS GIBT (17.08.2026)
======================================
``Skills1`` - die Zusammenfuehrung beider Werkzeugkaesten - war fertig gebaut,
lieferte HTTP 200 und stand in KEINEM Menue. Weder in ``PFLICHTSEITEN`` (der
Weg fuer Projekte mit eigener Sidebar) noch in der damals handgepflegten Liste
in ``_nav_skills.html``. Gefunden hat es der Nutzer mit der Frage „Die Skills
seite upgedatet??", nicht ein Test.

Das ist derselbe Fehler wie am 16.08.2026, nur mit einer Seite mehr: Eine Route
existiert, die Seite rendert, und niemand findet sie. Diese Tests halten fest,
was daraus folgt:

    Eine Werkzeugkasten-Route OHNE Menueeintrag ist ein Fehler, kein Detail.

Der erste Test faellt automatisch, sobald jemand eine vierte ``skills``-Seite
in die URLconf haengt und den Menueeintrag vergisst - ohne dass jemand diese
Datei anfassen muss.
"""
from django.urls import NoReverseMatch, reverse

from djangobase.pflichtmenue import PFLICHTSEITEN, pflicht_eintraege

from ..base import BasisTest


class PflichtseitenTest(BasisTest):

    #: Praefix der Werkzeugkasten-Routen. Absichtlich per Praefix und nicht als
    #: Aufzaehlung: Eine Aufzaehlung haette ``skills1`` genauso verpasst wie das
    #: Menue, das sie verpasst hat.
    PRAEFIX = "skills"

    def _routen_der_urlconf(self):
        """Alle ``djangobase:skills*``-Routennamen aus der echten URLconf."""
        from djangobase import urls
        aus = set()
        for muster in urls.urlpatterns:
            name = getattr(muster, "name", "") or ""
            if name.startswith(self.PRAEFIX):
                aus.add(name)
        return aus

    def test_jede_werkzeugkasten_route_hat_einen_menueeintrag(self):
        eingetragen = {e.route for e in PFLICHTSEITEN}
        fehlend = self._routen_der_urlconf() - eingetragen
        self.assertFalse(
            fehlend,
            "Diese Seiten gibt es, aber sie stehen in keinem Menue: %s. "
            "Eintragen in djangobase/pflichtmenue.py -> PFLICHTSEITEN; "
            "_nav_skills.html liest dieselbe Liste."
            % ", ".join(sorted(fehlend)))

    def test_jeder_eintrag_zeigt_auf_eine_aufloesbare_route(self):
        for eintrag in PFLICHTSEITEN:
            with self.subTest(seite=eintrag.label):
                try:
                    ziel = reverse("djangobase:%s" % eintrag.route)
                except NoReverseMatch:                      # pragma: no cover
                    self.fail("Route djangobase:%s gibt es nicht"
                              % eintrag.route)
                self.assertTrue(ziel.startswith("/"))

    def test_label_und_route_sind_eindeutig(self):
        labels = [e.label for e in PFLICHTSEITEN]
        routen = [e.route for e in PFLICHTSEITEN]
        self.assertEqual(len(labels), len(set(labels)), "doppeltes Label")
        self.assertEqual(len(routen), len(set(routen)), "doppelte Route")

    def test_jeder_eintrag_hat_icon_und_zweck(self):
        for eintrag in PFLICHTSEITEN:
            with self.subTest(seite=eintrag.label):
                self.assertTrue(eintrag.icon.startswith("bi-"),
                                "Sidebar-Icons sind Bootstrap-Icons (bi-*)")
                self.assertTrue(eintrag.zweck, "Zweck fehlt (Tooltip und Doku)")

    def test_uebergabeformat_bleibt_das_der_menue_bauer(self):
        """``als_dict()`` liefert genau die Schluessel, die Projekte erwarten.

        shortlongx reicht diese Woerterbuecher unveraendert in seine eigene
        Sidebar (``menue.py``). Ein zusaetzlicher Schluessel waere dort ein
        stiller Fremdkoerper - deshalb bekommt die Vorlage die Objekte selbst
        und nicht diese Dictionaries.
        """
        for eintrag in pflicht_eintraege():
            with self.subTest(seite=eintrag.get("label")):
                self.assertEqual(set(eintrag) - {"title"},
                                 {"label", "icon", "url"})


class NavVorlageTest(BasisTest):
    """Die Vorlage darf die Liste nicht ein zweites Mal fuehren."""

    VORLAGE = "djangobase/_nav_skills.html"

    def _quelltext(self):
        from django.template.loader import get_template
        return get_template(self.VORLAGE).template.source

    def test_vorlage_rendert_aus_pflichtseiten(self):
        self.assertIn("djangobase.pflichtseiten", self._quelltext())

    def test_keine_handgepflegten_url_tags(self):
        """Kein ``{% url 'djangobase:skills…' %}`` mehr - eine Quelle."""
        quelle = self._quelltext()
        for eintrag in PFLICHTSEITEN:
            with self.subTest(seite=eintrag.label):
                self.assertNotIn("djangobase:%s'" % eintrag.route, quelle)
