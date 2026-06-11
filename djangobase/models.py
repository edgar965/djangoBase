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
    # Lebenslauf-Zeitstempel (Audit, gepflegt über signals.py / Benutzer-Views)
    registriert_am = models.DateTimeField("Registriert am", null=True, blank=True)
    email_bestaetigt_am = models.DateTimeField("E-Mail bestätigt am", null=True, blank=True)
    freigegeben_am = models.DateTimeField("Freigegeben am", null=True, blank=True)

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


class Seitenaufruf(models.Model):
    """Ein erfasster Seitenaufruf für die Traffic-Statistik
    (djangobase.traffic.TrafficMiddleware, Seite: views/traffic.py).

    Datenschutz: Die IP wird NIE gespeichert — nur ein täglich wechselnder
    Besucher-Hash (IP + User-Agent + Tagessalz + SECRET_KEY). Damit lassen
    sich eindeutige Besucher pro Tag zählen, ohne dass jemand identifizierbar
    oder über Tage hinweg verfolgbar wäre."""
    TYPEN = [("html", "Seite"), ("json", "JSON/API"), ("andere", "Andere")]
    GERAETE = [("desktop", "Desktop"), ("mobile", "Mobil"), ("tablet", "Tablet")]

    zeit = models.DateTimeField("Zeit", auto_now_add=True, db_index=True)
    pfad = models.CharField("Pfad", max_length=300, db_index=True)
    typ = models.CharField("Typ", max_length=8, choices=TYPEN, default="html")
    land = models.CharField("Land (ISO)", max_length=2, blank=True)
    besucher = models.CharField("Besucher-Hash", max_length=16, db_index=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="+",
                             verbose_name="Benutzer")
    geraet = models.CharField("Gerät", max_length=8, choices=GERAETE,
                              default="desktop")
    referrer = models.CharField("Referrer-Domain", max_length=120, blank=True)
    bot = models.BooleanField("Bot", default=False)
    # Unkomprimierte Antwortgröße; /static/ & /media/ liefert nginx direkt
    # aus und tauchen hier folglich nicht auf.
    groesse = models.PositiveBigIntegerField("Antwortgröße (Bytes)", default=0)

    class Meta:
        verbose_name = "Seitenaufruf"
        verbose_name_plural = "Seitenaufrufe"

    def __str__(self):
        return f"{self.zeit:%Y-%m-%d %H:%M} {self.pfad}"


class LoginSitzung(models.Model):
    """Eine Login-Sitzung (von–bis) für den Audit-Trail. `benutzer` als
    Snapshot-Text, damit die Historie eine spätere Konto-Löschung überlebt
    (user wird dann auf NULL gesetzt, der Name bleibt)."""
    user = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                             on_delete=models.SET_NULL, related_name="login_sitzungen",
                             verbose_name="Benutzer")
    benutzer = models.CharField("Benutzer (Snapshot)", max_length=200)
    beginn = models.DateTimeField("Login", db_index=True)
    ende = models.DateTimeField("Logout", null=True, blank=True)
    ip = models.GenericIPAddressField("IP", null=True, blank=True)

    class Meta:
        verbose_name = "Login-Sitzung"
        verbose_name_plural = "Login-Sitzungen"
        ordering = ["-beginn"]

    def __str__(self):
        return f"{self.benutzer} {self.beginn:%Y-%m-%d %H:%M}"


class Verbrauch(models.Model):
    """Verbrauch externer Dienste (Traffic-Seite, Unterkategorie „Externe
    Dienste"): Kartenkacheln (vom Browser direkt von den OSM-Tile-Servern
    geladen, gemeldet per Beacon) und Navigations-/Routing-Anfragen (über den
    eigenen Valhalla-Proxy). Dient der Fair-Use-Überwachung.

    `anzahl` = Stück (Kacheln bzw. Routing-Anfragen), `bytes` = übertragene
    Datenmenge (bei Kacheln aus der Resource-Timing-API des Browsers, 0 bei
    Cache-Treffern), `detail` = Quelle/Modus (z. B. "auto"/"pedestrian")."""
    TYPEN = [("tile", "Kartenkacheln"), ("route", "Navigation/Routing")]

    zeit = models.DateTimeField("Zeit", auto_now_add=True, db_index=True)
    typ = models.CharField("Typ", max_length=8, choices=TYPEN, db_index=True)
    anzahl = models.PositiveIntegerField("Anzahl", default=1)
    bytes = models.PositiveBigIntegerField("Bytes", default=0)
    detail = models.CharField("Detail", max_length=40, blank=True)

    class Meta:
        verbose_name = "Verbrauch"
        verbose_name_plural = "Verbrauch"

    def __str__(self):
        return f"{self.zeit:%Y-%m-%d %H:%M} {self.typ} ×{self.anzahl}"


class TextQuelle(models.Model):
    """Ein deutscher Originaltext der öffentlichen User-Seite (Basis-Version).

    Wird beim ersten Rendern eines {% t %}-/{% tblock %}-Tags automatisch
    registriert (djangobase.uebersetzung). Der Schlüssel ist bei {% t %} der
    md5-Hash des Texts (Textänderung = neuer Eintrag), bei {% tblock %} ein
    fester Name (Textänderung = Übersetzung „veraltet")."""
    schluessel = models.CharField("Schlüssel", max_length=64, unique=True)
    quelle = models.TextField("Deutscher Text")
    zuletzt_gesehen = models.DateTimeField("Zuletzt gesehen", auto_now=True)

    class Meta:
        verbose_name = "Textquelle"
        verbose_name_plural = "Textquellen"

    def __str__(self):
        return self.quelle[:60]


class Uebersetzung(models.Model):
    """Maschinelle (Google-)Übersetzung einer TextQuelle in eine Zielsprache.
    quelle_hash hält fest, welcher deutsche Stand übersetzt wurde – weicht er
    vom aktuellen Quelltext ab, gilt die Übersetzung als veraltet."""
    quelle = models.ForeignKey(TextQuelle, on_delete=models.CASCADE,
                               related_name="uebersetzungen", verbose_name="Quelle")
    sprache = models.CharField("Sprache", max_length=8)
    text = models.TextField("Übersetzung")
    quelle_hash = models.CharField("Quell-Hash", max_length=32)
    uebersetzt_am = models.DateTimeField("Übersetzt am", auto_now=True)

    class Meta:
        verbose_name = "Übersetzung"
        verbose_name_plural = "Übersetzungen"
        constraints = [models.UniqueConstraint(fields=["quelle", "sprache"],
                                               name="uebersetzung_quelle_sprache")]

    def __str__(self):
        return f"{self.sprache}: {self.text[:50]}"


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
