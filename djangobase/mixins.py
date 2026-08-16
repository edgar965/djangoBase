import logging

from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .conf import conf

logger = logging.getLogger(__name__)

#: Die drei Stufen, die es gibt. Alles andere ist ein Tippfehler.
STUFEN = ("staff", "login", "none")


class ZugriffMixin:
    """Schützt die Hilfe-Seiten gemäß settings.DJANGOBASE['zugriff']:
    'staff' (Standard), 'login' oder 'none'.

    UNBEKANNTE WERTE GELTEN ALS 'staff' (Review 15.08.2026): Vorher stand hier

        if z != "none":
            ... Anmeldung verlangen ...
            if z == "staff" and not request.user.is_staff:
                raise PermissionDenied

    Ein Tippfehler in der Konfiguration eines der sechs Projekte — `'stff'`,
    `'Staff'`, `'staff '` — fiel damit durch BEIDE Abfragen: nicht `"none"`, also
    Anmeldung verlangt, aber auch nicht `"staff"`, also keine Rechteprüfung. Aus
    einem Schreibfehler wurde still die schwächere Stufe. Jetzt gewinnt die
    strengste, und die Zeile steht im Protokoll."""

    def dispatch(self, request, *args, **kwargs):
        z = conf()["zugriff"]
        if z not in STUFEN:
            logger.warning("DJANGOBASE['zugriff'] = %r ist unbekannt — es gilt "
                           "'staff'. Erlaubt: %s", z, ", ".join(STUFEN))
            z = "staff"
        if z != "none":
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if z == "staff" and not request.user.is_staff:
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
