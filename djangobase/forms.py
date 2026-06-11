"""Formular für die Benutzer-Verwaltung (User + Teilnehmer/Provider).

Rolle = Klasse: 'teilnehmer' -> Teilnehmer, 'anbieter' -> Provider (MTI).
Beim Bearbeiten ist das Passwort optional (leer = unverändert).
"""
from django import forms
from django.contrib.auth import get_user_model

from .models import Provider, Teilnehmer, als_provider, als_teilnehmer

User = get_user_model()

ROLLEN = [("teilnehmer", "Teilnehmer"), ("anbieter", "Provider")]


class BenutzerForm(forms.Form):
    vorname = forms.CharField(label="Vorname", max_length=150, required=False)
    name = forms.CharField(label="Name", max_length=150, required=False)
    email = forms.EmailField(label="E-Mail")
    passwort = forms.CharField(label="Passwort", required=False, widget=forms.PasswordInput,
                               help_text="Beim Bearbeiten leer lassen = unverändert.")
    rolle = forms.ChoiceField(label="Rolle", choices=ROLLEN, initial="teilnehmer")
    sprache = forms.ChoiceField(label="Sprache", choices=Teilnehmer.SPRACHEN, initial="de")
    telefon = forms.CharField(label="Telefon", max_length=60, required=False)
    avatar = forms.ImageField(label="Avatar", required=False)
    strasse = forms.CharField(label="Straße", max_length=200, required=False)
    plz = forms.CharField(label="PLZ", max_length=20, required=False)
    stadt = forms.CharField(label="Stadt", max_length=120, required=False)
    land = forms.CharField(label="Land", max_length=120, required=False)
    # Nur relevant für Provider:
    anbietername = forms.CharField(label="Anbieter-Name", max_length=200, required=False)
    website = forms.URLField(label="Website", required=False)
    verifiziert = forms.BooleanField(label="Verifiziert", required=False)
    aktiv = forms.BooleanField(label="Aktiv", required=False, initial=True)

    def __init__(self, *args, instance=None, **kwargs):
        self.instance = instance
        super().__init__(*args, **kwargs)
        if instance is None:
            self.fields["passwort"].required = True

    def clean_email(self):
        email = (self.cleaned_data["email"] or "").strip()
        kollision = User.objects.filter(email__iexact=email)
        if self.instance:
            kollision = kollision.exclude(pk=self.instance.pk)
        if kollision.exists():
            raise forms.ValidationError("Diese E-Mail wird bereits verwendet.")
        if self.instance is None and User.objects.filter(username=email).exists():
            raise forms.ValidationError("Dieser Benutzer existiert bereits.")
        return email

    def speichern(self):
        d = self.cleaned_data
        user = self.instance or User()
        if self.instance is None:
            user.username = d["email"]
        user.first_name = d.get("vorname", "")
        user.last_name = d.get("name", "")
        user.email = d["email"]
        user.is_active = bool(d.get("aktiv"))
        if d.get("passwort"):
            user.set_password(d["passwort"])
        user.save()

        # Rolle = Klasse: Provider (MTI) oder reiner Teilnehmer.
        if d["rolle"] == "anbieter":
            profil = als_provider(
                user,
                anbietername=d.get("anbietername", ""),
                website=d.get("website", ""),
                verifiziert=bool(d.get("verifiziert")),
            )
        else:
            profil = als_teilnehmer(user)

        # Gemeinsame Stammdaten (auf Teilnehmer/Provider gleichermaßen).
        profil.sprache = d["sprache"]
        profil.telefon = d.get("telefon", "")
        profil.strasse = d.get("strasse", "")
        profil.plz = d.get("plz", "")
        profil.stadt = d.get("stadt", "")
        profil.land = d.get("land", "")
        if d.get("avatar"):
            profil.avatar = d["avatar"]
        profil.save()
        return user


class RollenSignupForm(forms.Form):
    """Zusatzfelder für die django-allauth-Registrierung: Vor-/Nachname + Rolle.

    Einbindung im Projekt:
        ACCOUNT_SIGNUP_FORM_CLASS = "djangobase.forms.RollenSignupForm"

    allauth mischt die Felder ins Signup-Formular und ruft nach dem Anlegen des
    Users `signup(request, user)` auf. Nutzer -> Teilnehmer (vom Signal),
    Provider -> Beförderung zu Provider via als_provider().
    """
    SIGNUP_ROLLEN = [
        ("nutzer", "Nutzer – Konto für Besucher"),
        ("anbieter", "Provider – eigene Einträge/Angebote anbieten"),
    ]

    vorname = forms.CharField(label="Vorname", max_length=150, required=False)
    name = forms.CharField(label="Name", max_length=150, required=False)
    rolle = forms.ChoiceField(
        label="Ich registriere mich als …", choices=SIGNUP_ROLLEN,
        initial="nutzer", widget=forms.RadioSelect,
    )
    anbietername = forms.CharField(
        label="Anbieter-Name (nur als Provider)", max_length=200, required=False,
    )

    def signup(self, request, user):
        from .conf import conf
        user.first_name = self.cleaned_data.get("vorname", "")
        user.last_name = self.cleaned_data.get("name", "")
        # Konten-Freigabe (Gating): muss dieses Konto erst freigegeben werden,
        # bleibt es bis zur Admin-Freigabe inaktiv (kann sich nicht anmelden).
        c = conf()
        rolle = self.cleaned_data.get("rolle")
        if ((rolle == "anbieter" and c.get("freigabe_provider_noetig"))
                or (rolle != "anbieter" and c.get("freigabe_nutzer_noetig"))):
            user.is_active = False
        user.save()
        # Das djangoBase-Signal hat bereits ein Teilnehmer-Profil angelegt.
        if rolle == "anbieter":
            als_provider(user, anbietername=self.cleaned_data.get("anbietername", ""))
        return user
