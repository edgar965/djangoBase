"""Signale rund um die Benutzer-Profile.

- Neu angelegte User bekommen automatisch ein Teilnehmer-Profil.
- Login/Logout pflegen das `eingeloggt`-Flag (last_login macht Django selbst).
"""
from django.contrib.auth import get_user_model
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Teilnehmer

User = get_user_model()


@receiver(post_save, sender=User)
def teilnehmer_anlegen(sender, instance, created, **kwargs):
    if created:
        Teilnehmer.objects.get_or_create(user=instance)


def _setze_eingeloggt(user, wert):
    if not user or not getattr(user, "is_authenticated", False):
        return
    Teilnehmer.objects.filter(user=user).update(eingeloggt=wert)


@receiver(user_logged_in)
def beim_login(sender, request, user, **kwargs):
    _setze_eingeloggt(user, True)


@receiver(user_logged_out)
def beim_logout(sender, request, user, **kwargs):
    _setze_eingeloggt(user, False)
