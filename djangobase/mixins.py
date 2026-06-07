from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied

from .conf import conf


class ZugriffMixin:
    """Schützt die Hilfe-Seiten gemäß settings.DJANGOBASE['zugriff']:
    'staff' (Standard), 'login' oder 'none'."""

    def dispatch(self, request, *args, **kwargs):
        z = conf()["zugriff"]
        if z != "none":
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            if z == "staff" and not request.user.is_staff:
                raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)
