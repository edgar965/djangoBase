"""SMTP-Backend, das Host/Port/Benutzer/Passwort aus den djangoBase-
Einstellungen (Einstellungen → E-Mail, JSON-Store) zur Laufzeit liest.

Ist dort kein Host gesetzt, fällt es auf die normalen Django-EMAIL_*-Settings
zurück. In settings.py:

    EMAIL_BACKEND = "djangobase.email.StoreSMTPBackend"
"""
from django.core.mail.backends.smtp import EmailBackend

from .conf import conf


class StoreSMTPBackend(EmailBackend):
    def __init__(self, *args, **kwargs):
        c = conf()
        if c.get("email_host"):
            kwargs.update(
                host=c.get("email_host"),
                port=int(c.get("email_port") or 587),
                username=c.get("email_host_user") or "",
                password=c.get("email_host_password") or "",
                use_tls=bool(c.get("email_use_tls")),
                use_ssl=bool(c.get("email_use_ssl")),
            )
        super().__init__(*args, **kwargs)
