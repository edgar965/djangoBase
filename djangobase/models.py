"""Benutzer-Profile als Klassen-Hierarchie (Variante 2, Multi-Table-Inheritance).

    auth.User  (Identität; is_staff = „Django-Nutzer")
       │ 1:1
       ▼
    BasisProfil   (abstrakt — gemeinsame Felder, KEINE Tabelle)
       ▲ erbt
    Teilnehmer(BasisProfil)        (konkret — Basisnutzer)
       ▲ erbt (MTI)
    Provider(Teilnehmer)           (+ Anbieter-Felder; „Provider ist ein Teilnehmer")

Die Rolle ergibt sich aus der KLASSE: existiert ein Provider-Datensatz zum
Nutzer, ist er Provider, sonst Teilnehmer. Diese Modelle gehören djangoBase und
stehen daher in jedem Projekt zur Verfügung (einmalig `migrate djangobase`).
"""
import re

from django.conf import settings
from django.db import models


class BasisProfil(models.Model):
    """Abstrakte Basis: gemeinsame Stammdaten jedes Nutzers."""
    SPRACHEN = [
        ("de", "Deutsch"), ("en", "English"), ("fr", "Français"),
        ("es", "Español"), ("it", "Italiano"),
    ]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name="profil", verbose_name="Benutzer")
    avatar = models.ImageField("Avatar-Bild", upload_to="avatare/", blank=True)
    avatar_emoji = models.CharField("Avatar (Emoji)", max_length=8, blank=True)
    sprache = models.CharField("Sprache", max_length=5, choices=SPRACHEN, default="de")
    telefon = models.CharField("Telefon", max_length=60, blank=True)
    strasse = models.CharField("Straße", max_length=200, blank=True)
    plz = models.CharField("PLZ", max_length=20, blank=True)
    stadt = models.CharField("Stadt", max_length=120, blank=True)
    land = models.CharField("Land", max_length=120, blank=True)
    # eingeloggtZuletzt = user.last_login (von Django gepflegt)
    eingeloggt = models.BooleanField("Eingeloggt", default=False)
    anwesend = models.BooleanField("Anwesend", default=False)
    ui = models.PositiveIntegerField("UI", default=1)

    class Meta:
        abstract = True

    def __str__(self):
        return self.user.get_full_name() or self.user.get_username()

    @property
    def adresse_kurz(self):
        ort = " ".join(t for t in [self.plz, self.stadt] if t)
        return ", ".join(t for t in [self.strasse, ort, self.land] if t)

    @property
    def initialen(self):
        v = (self.user.first_name or "").strip()
        n = (self.user.last_name or "").strip()
        if v or n:
            roh = (v[:1] + n[:1]) or v[:2] or n[:2]
        else:
            roh = re.sub(r"\s+", "", self.user.get_username())[:2]
        return (roh or "?").upper()


class Teilnehmer(BasisProfil):
    """Konkreter Basisnutzer (normaler Teilnehmer)."""

    class Meta:
        verbose_name = "Teilnehmer"
        verbose_name_plural = "Teilnehmer"

    @property
    def ist_provider(self):
        # Reverse-MTI-Accessor: Provider, falls vorhanden.
        return Provider.objects.filter(pk=self.pk).exists()


class Provider(Teilnehmer):
    """Anbieter von Events/Touren. Erbt per MTI von Teilnehmer
    („Provider ist ein Teilnehmer")."""
    anbietername = models.CharField("Anbieter-Name", max_length=200, blank=True)
    logo = models.ImageField("Logo", upload_to="anbieter/", blank=True)
    beschreibung = models.TextField("Beschreibung", blank=True)
    website = models.URLField("Website", blank=True)
    verifiziert = models.BooleanField("Verifiziert", default=False)

    class Meta:
        verbose_name = "Provider"
        verbose_name_plural = "Provider"


# --------------------------------------------------------------------- Helfer
def als_provider(user, **felder):
    """Stellt sicher, dass `user` ein Provider ist. Promotet ein vorhandenes
    Teilnehmer-Profil per MTI zum Provider (ohne die Parent-Felder zu verlieren)
    und setzt die übergebenen Provider-Felder."""
    teilnehmer, _ = Teilnehmer.objects.get_or_create(user=user)
    try:
        prov = Provider.objects.get(pk=teilnehmer.pk)
    except Provider.DoesNotExist:
        prov = Provider(teilnehmer_ptr_id=teilnehmer.pk)
        # Parent-Felder übernehmen, damit save() sie nicht auf Defaults setzt.
        prov.__dict__.update(teilnehmer.__dict__)
    for key, wert in felder.items():
        setattr(prov, key, wert)
    prov.save()
    return prov


def als_teilnehmer(user):
    """Degradiert einen Provider zurück auf reinen Teilnehmer: löscht nur die
    Provider-Child-Zeile, das Teilnehmer-Profil bleibt erhalten."""
    teilnehmer, _ = Teilnehmer.objects.get_or_create(user=user)
    try:
        Provider.objects.get(pk=teilnehmer.pk).delete(keep_parents=True)
    except Provider.DoesNotExist:
        pass
    return teilnehmer
