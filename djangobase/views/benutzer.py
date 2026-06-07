"""Hilfe -> Einstellungen -> Benutzer: generische Benutzer-Verwaltung.

Arbeitet auf auth.User + den djangoBase-Profilen (Teilnehmer/Provider, MTI).
Drei Tabs nach Klassen-Zugehörigkeit:
  * Provider     – es existiert ein Provider-Datensatz (und nicht Staff)
  * Teilnehmer   – nur Teilnehmer (und nicht Staff)
  * Django-Nutzer – is_staff / is_superuser

Da die Modelle djangoBase gehören, steht die Seite in jedem Projekt bereit,
das `migrate djangobase` ausgeführt hat.
"""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views import View

from ..forms import BenutzerForm
from ..mixins import ZugriffMixin
from ..models import Provider, Teilnehmer

User = get_user_model()

# Auswählbare Avatar-Emojis (wie bei Cleanorga – einfach anklicken).
AVATAR_EMOJIS = ["🧑", "👩", "👨", "🧑‍💼", "👩‍💼", "👨‍💼", "🧑‍🔧", "👷",
                 "🧑‍🍳", "🧑‍🏫", "🧑‍💻", "🦸", "🧑‍🎨", "🏠", "🌟", "🚲"]


def _zeile(user, profil, ist_provider):
    return {
        "user": user,
        "profil": profil,
        "ist_provider": ist_provider,
        "avatar_url": profil.avatar.url if (profil and profil.avatar) else "",
        "avatar_emoji": profil.avatar_emoji if profil else "",
        "initialen": profil.initialen if profil else (user.get_username()[:2] or "?").upper(),
        "sprache_code": profil.sprache if profil else "de",
        "sprache": profil.get_sprache_display() if profil else "",
        "adresse": profil.adresse_kurz if profil else "",
        "online": bool(profil and profil.eingeloggt),
        "anwesend": bool(profil and profil.anwesend),
        "ui": profil.ui if profil else 1,
    }


def _listen():
    """(provider, teilnehmer, django_nutzer) – je Liste von Zeilen-Dicts."""
    teilnehmer_map = {t.user_id: t for t in Teilnehmer.objects.select_related("user")}
    provider_pks = set(Provider.objects.values_list("pk", flat=True))
    provider, teilnehmer, django_nutzer = [], [], []
    for user in User.objects.order_by("-is_active", "last_name", "first_name", "username"):
        t = teilnehmer_map.get(user.id)
        ist_provider = bool(t and t.pk in provider_pks)
        zeile = _zeile(user, t, ist_provider)
        if user.is_staff or user.is_superuser:
            django_nutzer.append(zeile)
        elif ist_provider:
            provider.append(zeile)
        else:
            teilnehmer.append(zeile)
    return provider, teilnehmer, django_nutzer


def _context(form=None, modal_offen=False):
    provider, teilnehmer, django_nutzer = _listen()
    return {
        "aktiv": "einstellungen_benutzer",
        "provider": provider,
        "teilnehmer": teilnehmer,
        "django_nutzer": django_nutzer,
        "form": form or BenutzerForm(),
        "modal_offen": modal_offen,
        "sprachen": Teilnehmer.SPRACHEN,
        "avatar_emojis": AVATAR_EMOJIS,
    }


class BenutzerListeView(ZugriffMixin, View):
    def get(self, request):
        return render(request, "djangobase/hilfe/benutzer.html", _context())


class BenutzerErstellenView(ZugriffMixin, View):
    def post(self, request):
        form = BenutzerForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.speichern()
            messages.success(request, f"Benutzer {user.get_full_name() or user.username} angelegt.")
            return redirect(reverse("djangobase:benutzer"))
        return render(request, "djangobase/hilfe/benutzer.html",
                      _context(form=form, modal_offen=True))


class BenutzerBearbeitenView(ZugriffMixin, View):
    template_name = "djangobase/hilfe/benutzer_form.html"

    def _initial(self, user):
        t = Teilnehmer.objects.filter(user=user).first()
        prov = Provider.objects.filter(pk=t.pk).first() if t else None
        return {
            "vorname": user.first_name, "name": user.last_name, "email": user.email,
            "aktiv": user.is_active,
            "rolle": "anbieter" if prov else "teilnehmer",
            "sprache": getattr(t, "sprache", "de"),
            "telefon": getattr(t, "telefon", ""),
            "strasse": getattr(t, "strasse", ""),
            "plz": getattr(t, "plz", ""),
            "stadt": getattr(t, "stadt", ""),
            "land": getattr(t, "land", ""),
            "anbietername": getattr(prov, "anbietername", ""),
            "website": getattr(prov, "website", ""),
            "verifiziert": getattr(prov, "verifiziert", False),
        }

    def _avatar_ctx(self, user):
        t = Teilnehmer.objects.filter(user=user).first()
        return {
            "aktueller_avatar": t.avatar.url if (t and t.avatar) else "",
            "aktuelle_initialen": t.initialen if t else (user.get_username()[:2] or "?").upper(),
        }

    def get(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = BenutzerForm(instance=user, initial=self._initial(user))
        return render(request, self.template_name,
                      {"form": form, "ziel": user, **self._avatar_ctx(user)})

    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        form = BenutzerForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            form.speichern()
            messages.success(request, "Benutzer aktualisiert.")
            return redirect(reverse("djangobase:benutzer"))
        return render(request, self.template_name,
                      {"form": form, "ziel": user, **self._avatar_ctx(user)})


class BenutzerStatusView(ZugriffMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, "Du kannst dein eigenes Konto nicht deaktivieren.")
            return redirect(reverse("djangobase:benutzer"))
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        zustand = "aktiv" if user.is_active else "inaktiv"
        messages.success(request, f"{user.get_full_name() or user.username} ist jetzt {zustand}.")
        return redirect(reverse("djangobase:benutzer"))


class BenutzerInlineView(ZugriffMixin, View):
    """Inline-Schnellbearbeitung aus der Tabelle: Passwort/Sprache/UI/Anwesend."""
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        feld = request.POST.get("feld")
        wert = (request.POST.get("wert") or "").strip()
        t, _ = Teilnehmer.objects.get_or_create(user=user)

        if feld == "passwort":
            if wert:
                user.set_password(wert)
                user.save(update_fields=["password"])
                messages.success(request, f"Passwort von {user.get_username()} geändert.")
            else:
                messages.error(request, "Kein neues Passwort angegeben.")
        elif feld == "sprache":
            gueltig = dict(Teilnehmer.SPRACHEN)
            if wert in gueltig:
                t.sprache = wert
                t.save(update_fields=["sprache"])
                messages.success(request, f"Sprache: {gueltig[wert]}.")
        elif feld == "ui":
            try:
                t.ui = max(0, int(wert))
                t.save(update_fields=["ui"])
                messages.success(request, "UI gespeichert.")
            except ValueError:
                messages.error(request, "UI muss eine Zahl sein.")
        elif feld == "anwesend":
            t.anwesend = not t.anwesend
            t.save(update_fields=["anwesend"])
        elif feld == "avatar_emoji":
            t.avatar_emoji = wert[:8]
            t.save(update_fields=["avatar_emoji"])
        return redirect(reverse("djangobase:benutzer"))


class BenutzerLoeschenView(ZugriffMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, "Du kannst dein eigenes Konto nicht löschen.")
            return redirect(reverse("djangobase:benutzer"))
        name = user.get_full_name() or user.get_username()
        user.delete()
        messages.success(request, f"Benutzer {name} gelöscht.")
        return redirect(reverse("djangobase:benutzer"))
