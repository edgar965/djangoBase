"""Gemeinsame Test-Helfer für djangoBase.

Die Tests laufen im Kontext des Host-Projekts (z. B. spin1more):
    python manage.py test djangobase                # alle
    python manage.py test djangobase.tests.unit     # nur Unit-Tests
    python manage.py test djangobase.tests.component
    python manage.py test djangobase.tests.integration

Struktur (wie in den anderen Projekten):
    unit/        – reine Funktions-/Modell-Logik, keine HTTP-Schicht
    component/   – einzelne Views/Seiten rendern korrekt (Test-Client)
    integration/ – mehrere Bausteine zusammen (Login-Audit, Signup-Gating …)
"""
import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

User = get_user_model()


class BasisTest(TestCase):
    """Basisklasse mit kleinen Helfern für Nutzer/Clients."""

    def nutzer(self, username="t_nutzer", passwort="pw-test-12345", **felder):
        return User.objects.create_user(username=username, password=passwort, **felder)

    def staff(self, username="t_staff", passwort="pw-test-12345", **felder):
        felder.setdefault("is_staff", True)
        return User.objects.create_user(username=username, password=passwort, **felder)

    def staff_client(self):
        c = Client()
        c.force_login(self.staff())
        return c


class StoreIsolationMixin:
    """Lenkt die JSON-Einstellungen (store) während des Tests auf eine
    temporäre Datei – die echte .djangobase.json bleibt unangetastet."""

    def store_isolieren(self):
        from djangobase import store
        tmp = tempfile.NamedTemporaryFile(suffix=".json", delete=False)
        tmp.close()
        self._store_tmp = Path(tmp.name)
        self._store_orig = store._pfad
        store._pfad = lambda: self._store_tmp
        self.addCleanup(self._store_wiederherstellen)

    def _store_wiederherstellen(self):
        from djangobase import store
        store._pfad = self._store_orig
        try:
            self._store_tmp.unlink()
        except OSError:
            pass
