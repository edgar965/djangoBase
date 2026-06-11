"""Signale rund um die Benutzer-Profile + Audit-Trail.

- Neu angelegte User bekommen automatisch ein Teilnehmer-Profil.
- Login/Logout pflegen das `eingeloggt`-Flag und schreiben Login-Sitzungen
  (von–bis) in den Audit-Trail (LoginSitzung).
- Registrierung, E-Mail-Bestätigung und Admin-Freigabe werden mit Zeitstempel
  am Profil festgehalten (registriert_am / email_bestaetigt_am / freigegeben_am).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone

from .models import LoginSitzung, Teilnehmer

User = get_user_model()


def _client_ip(request):
    if request is None:
        return None
    ip = (request.META.get("HTTP_X_REAL_IP")
          or request.META.get("HTTP_X_FORWARDED_FOR", "").split(",")[0]
          or request.META.get("REMOTE_ADDR", "")).strip()
    return ip or None


@receiver(post_save, sender=User)
def teilnehmer_anlegen(sender, instance, created, **kwargs):
    if created:
        Teilnehmer.objects.get_or_create(
            user=instance, defaults={"registriert_am": instance.date_joined or timezone.now()})


def _setze_eingeloggt(user, wert):
    if not user or not getattr(user, "is_authenticated", False):
        return
    Teilnehmer.objects.filter(user=user).update(eingeloggt=wert)


@receiver(user_logged_in)
def beim_login(sender, request, user, **kwargs):
    _setze_eingeloggt(user, True)
    # Offene Sitzungen (z. B. nach Absturz ohne Logout) abschließen, dann neue
    LoginSitzung.objects.filter(user=user, ende__isnull=True).update(ende=timezone.now())
    LoginSitzung.objects.create(
        user=user, benutzer=user.get_username(),
        beginn=timezone.now(), ip=_client_ip(request))


@receiver(user_logged_out)
def beim_logout(sender, request, user, **kwargs):
    _setze_eingeloggt(user, False)
    if user:
        offen = (LoginSitzung.objects.filter(user=user, ende__isnull=True)
                 .order_by("-beginn").first())
        if offen:
            offen.ende = timezone.now()
            offen.save(update_fields=["ende"])


# --- allauth: E-Mail-Bestätigung (optional, nur wenn allauth installiert) ---
try:
    from allauth.account.signals import email_confirmed, user_signed_up

    @receiver(user_signed_up)
    def beim_signup(sender, request, user, **kwargs):
        Teilnehmer.objects.filter(user=user).update(registriert_am=timezone.now())

    @receiver(email_confirmed)
    def beim_email_bestaetigt(sender, request, email_address, **kwargs):
        Teilnehmer.objects.filter(user_id=email_address.user_id,
                                  email_bestaetigt_am__isnull=True).update(
            email_bestaetigt_am=timezone.now())
except Exception:  # noqa: BLE001 – ohne allauth einfach ohne diese Signale
    pass
