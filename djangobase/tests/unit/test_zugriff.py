# -*- coding: utf-8 -*-
"""Wächter für ZugriffMixin — wer die Hilfe-Seiten sehen darf.

WARUM (Review 15.08.2026)
-------------------------
`ZugriffMixin` entscheidet in SECHS Projekten, wer Hilfe → Logs, Einstellungen,
Benutzer und Review öffnen darf. Die Prüfung war:

    if z != "none":            -> Anmeldung verlangen
        if z == "staff" ...    -> Rechte verlangen

Ein Tippfehler in der Projektkonfiguration (`'stff'`, `'Staff'`, `'staff '`)
fällt durch BEIDE Abfragen: Er ist nicht `"none"`, also wird angemeldet; er ist
aber auch nicht `"staff"`, also entfällt die Rechteprüfung. Aus einem
Schreibfehler wurde still die schwächere Stufe — und zwar dauerhaft, weil nichts
darauf hinweist.

Jetzt gilt: unbekannt -> strengste Stufe, mit einer Zeile im Protokoll.
"""
from django.contrib.auth.models import AnonymousUser, User
from django.core.exceptions import PermissionDenied
from django.test import RequestFactory, TestCase, override_settings
from django.views import View

from djangobase.mixins import ZugriffMixin


class _Seite(ZugriffMixin, View):
    def get(self, request):
        from django.http import HttpResponse
        return HttpResponse('geheim')


def _anfrage(user):
    r = RequestFactory().get('/help/logs/')
    r.user = user
    return r


class ZugriffMixinTest(TestCase):

    @classmethod
    def setUpTestData(cls):
        cls.gast = AnonymousUser()
        cls.nutzer = User.objects.create_user('nutzer', password='x')
        cls.chef = User.objects.create_user('chef', password='x', is_staff=True)

    def _status(self, zugriff, user):
        with override_settings(DJANGOBASE={'zugriff': zugriff}):
            try:
                return _Seite.as_view()(_anfrage(user)).status_code
            except PermissionDenied:
                return 403

    # ----------------------------------------------------------- die drei Stufen

    def test_none_laesst_alle_durch(self):
        self.assertEqual(self._status('none', self.gast), 200)

    def test_login_verlangt_anmeldung(self):
        self.assertEqual(self._status('login', self.gast), 302)
        self.assertEqual(self._status('login', self.nutzer), 200)

    def test_staff_verlangt_rechte(self):
        self.assertEqual(self._status('staff', self.gast), 302)
        self.assertEqual(self._status('staff', self.nutzer), 403)
        self.assertEqual(self._status('staff', self.chef), 200)

    # ------------------------------------------------------------- der Tippfehler

    def test_tippfehler_faellt_auf_die_strengste_stufe_zurueck(self):
        for falsch in ('stff', 'Staff', 'staff ', 'STAFF', '', None, 'admin'):
            with self.subTest(wert=falsch):
                self.assertEqual(self._status(falsch, self.nutzer), 403,
                                 'zugriff=%r liess einen Nicht-Berechtigten durch'
                                 % falsch)
                self.assertEqual(self._status(falsch, self.chef), 200,
                                 'zugriff=%r sperrt auch Berechtigte aus' % falsch)

    def test_vorgabe_ohne_konfiguration_ist_staff(self):
        """Ohne DJANGOBASE-Eintrag gilt die Vorgabe aus conf.py."""
        with override_settings(DJANGOBASE={}):
            with self.assertRaises(PermissionDenied):
                _Seite.as_view()(_anfrage(self.nutzer))
