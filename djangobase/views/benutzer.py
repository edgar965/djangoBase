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
from ..models import LoginSitzung, Provider, Teilnehmer

User = get_user_model()

# Auswählbare Avatar-Emojis (wie bei Cleanorga – einfach anklicken).
AVATAR_EMOJIS = ["🧑", "👩", "👨", "🧑‍💼", "👩‍💼", "👨‍💼", "🧑‍🔧", "👷",
                 "🧑‍🍳", "🧑‍🏫", "🧑‍💻", "🦸", "🧑‍🎨", "🏠", "🌟", "🚲"]


def _email_adressen():
    """user_id → E-Mail-bestätigt? (django-allauth). None, wenn das Projekt
    allauth nicht nutzt – die Spalte wird dann ausgeblendet (opt-in)."""
    try:
        from allauth.account.models import EmailAddress
    except Exception:  # noqa: BLE001 – allauth ist optional
        return None
    bestaetigt = {}
    for user_id, verified in EmailAddress.objects.values_list("user_id", "verified"):
        bestaetigt[user_id] = bestaetigt.get(user_id, False) or verified
    return bestaetigt


def _eingeloggte_user_ids():
    """User-IDs mit aktiver (nicht abgelaufener) Session – die verlässliche
    „aktuell eingeloggt"-Quelle (selbstkorrigierend, anders als das gespeicherte
    eingeloggt-Flag, das beim Browser-Schließen veralten würde). Nur für den
    DB-Session-Backend; bei anderen Backends einfach leer."""
    try:
        from django.contrib.sessions.models import Session
        from django.utils import timezone
        ids = set()
        for s in Session.objects.filter(expire_date__gte=timezone.now()):
            uid = s.get_decoded().get("_auth_user_id")
            if uid:
                ids.add(int(uid))
        return ids
    except Exception:  # noqa: BLE001 – ohne DB-Sessions kein Online-Status
        return set()


def _online_ids(user_ids):
    """User-IDs, die AKTUELL online sind. Mit aktiviertem Online-Tracking
    (DJANGOBASE_ONLINE_TRACKING + OnlineMiddleware) = letzte Aktivität im
    Zeitfenster; sonst Fallback auf aktive (nicht abgelaufene) Sessions –
    Letzteres zählt aber auch „Eingeloggt bleiben"-Sessions mit."""
    try:
        from ..online import online_ids as _aktiv, tracking_aktiv
        if tracking_aktiv():
            return _aktiv(user_ids)
    except Exception:  # noqa: BLE001
        pass
    return _eingeloggte_user_ids()


def _details_map(user_ids):
    """Zusatz-Details fürs Verlauf-Popup vom optionalen Projekt-Provider
    (DJANGOBASE['benutzer_details_provider']). Gebündelt für alle Nutzer.
    {user_id: [{"titel","zeilen":[(label,wert)]}]}. Fail-silent."""
    from django.utils.module_loading import import_string
    from ..conf import conf
    pfad = conf().get("benutzer_details_provider")
    if not pfad:
        return {}
    try:
        fn = import_string(pfad) if isinstance(pfad, str) else pfad
        return fn(list(user_ids)) or {}
    except Exception:  # noqa: BLE001 – Details dürfen die Benutzerliste nie brechen
        return {}


def _sitzungen_map(grenze=40):
    """user_id → Liste der letzten Login-Sitzungen (neueste zuerst) für das
    Logs-Popup."""
    sm = {}
    for s in LoginSitzung.objects.filter(user__isnull=False).order_by("-beginn"):
        liste = sm.setdefault(s.user_id, [])
        if len(liste) < grenze:
            liste.append(s)
    return sm


# Konto-Status (kombiniert is_active + E-Mail-Bestätigung) als sprechendes Badge.
# Reihenfolge der Prüfung ist bewusst: Admin > kein-E-Mail (anonym/technisch) >
# gesperrt (is_active=False) > bestätigt > angefragt (E-Mail offen).
_STATUS_KLASSE = {
    "admin": "bg-primary", "anonym": "bg-secondary", "gesperrt": "bg-danger",
    "bestaetigt": "bg-success", "angefragt": "bg-warning text-dark",
}
_STATUS_LABEL = {
    "admin": "Admin", "anonym": "Anonym", "gesperrt": "Gesperrt",
    "bestaetigt": "Bestätigt", "angefragt": "Angefragt",
}


def _status_kennung(user, email_ok):
    if user.is_staff or user.is_superuser:
        slug = "admin"
    elif not user.email:
        slug = "anonym"
    elif not user.is_active:
        slug = "gesperrt"
    elif email_ok:
        slug = "bestaetigt"
    else:
        slug = "angefragt"
    return {"slug": slug, "label": _STATUS_LABEL[slug], "klasse": _STATUS_KLASSE[slug]}


def _zeile(user, profil, ist_provider, email_map=None, online_ids=None, sitzung_map=None,
           details_map=None):
    return {
        "user": user,
        "profil": profil,
        "ist_provider": ist_provider,
        "status": _status_kennung(user, bool(email_map and email_map.get(user.id))),
        "details": (details_map or {}).get(user.id, []),
        "avatar_url": profil.avatar.url if (profil and profil.avatar) else "",
        "avatar_emoji": profil.avatar_emoji if profil else "",
        "initialen": profil.initialen if profil else (user.get_username()[:2] or "?").upper(),
        "sprache_code": profil.sprache if profil else "de",
        "sprache": profil.get_sprache_display() if profil else "",
        "adresse": profil.adresse_kurz if profil else "",
        # „Eingeloggt" = aktive Session (nicht das veraltbare Profil-Flag)
        "online": user.id in online_ids if online_ids is not None
                  else bool(profil and profil.eingeloggt),
        "anwesend": bool(profil and profil.anwesend),
        "ui": profil.ui if profil else 1,
        "email_bestaetigt": bool(email_map and email_map.get(user.id)),
        # Audit-Zeitstempel (registriert_am Fallback: User.date_joined)
        "registriert_am": (profil.registriert_am if profil and profil.registriert_am
                           else user.date_joined),
        # „Zuletzt aktiv" (letzte Anfrage) – Fallback auf last_login (Anmeldung)
        "zuletzt_aktiv": (profil.zuletzt_aktiv if profil and profil.zuletzt_aktiv
                          else user.last_login),
        "email_bestaetigt_am": profil.email_bestaetigt_am if profil else None,
        "freigegeben_am": profil.freigegeben_am if profil else None,
        "sitzungen": (sitzung_map or {}).get(user.id, []),
    }


def _listen():
    """(provider, teilnehmer, django_nutzer, email_spalte) – Zeilen-Dicts."""
    teilnehmer_map = {t.user_id: t for t in Teilnehmer.objects.select_related("user")}
    provider_pks = set(Provider.objects.values_list("pk", flat=True))
    email_map = _email_adressen()
    sitzung_map = _sitzungen_map()
    nutzer = list(User.objects.order_by("-is_active", "last_name", "first_name", "username"))
    online_ids = _online_ids([u.id for u in nutzer])
    details_map = _details_map([u.id for u in nutzer])
    provider, teilnehmer, django_nutzer = [], [], []
    for user in nutzer:
        t = teilnehmer_map.get(user.id)
        ist_provider = bool(t and t.pk in provider_pks)
        zeile = _zeile(user, t, ist_provider, email_map, online_ids, sitzung_map, details_map)
        if user.is_staff or user.is_superuser:
            django_nutzer.append(zeile)
        elif ist_provider:
            provider.append(zeile)
        else:
            teilnehmer.append(zeile)
    return provider, teilnehmer, django_nutzer, email_map is not None


def _context(form=None, modal_offen=False):
    provider, teilnehmer, django_nutzer, email_spalte = _listen()
    return {
        "aktiv": "einstellungen_benutzer",
        "provider": provider,
        "teilnehmer": teilnehmer,
        "django_nutzer": django_nutzer,
        "email_spalte": email_spalte,
        "form": form or BenutzerForm(),
        "modal_offen": modal_offen,
        "sprachen": Teilnehmer.SPRACHEN,
        "avatar_emojis": AVATAR_EMOJIS,
    }


def _zurueck(request):
    """Ziel nach einer Aktion: die aufrufende Seite (Hidden-Feld „zurück“),
    sonst die Standard-Benutzerseite. Nur same-host-Pfade (Open-Redirect-
    Schutz via Djangos url_has_allowed_host_and_scheme)."""
    from django.utils.http import url_has_allowed_host_and_scheme
    ziel = (request.POST.get("zurueck") or "").strip()
    if ziel and url_has_allowed_host_and_scheme(
            ziel, allowed_hosts={request.get_host()}, require_https=request.is_secure()):
        return redirect(ziel)
    return redirect(reverse("djangobase:benutzer"))


class BenutzerListeView(ZugriffMixin, View):
    def get(self, request):
        return render(request, "djangobase/hilfe/benutzer.html", _context())


class BenutzerErstellenView(ZugriffMixin, View):
    def post(self, request):
        form = BenutzerForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.speichern()
            messages.success(request, f"Benutzer {user.get_full_name() or user.username} angelegt.")
            return _zurueck(request)
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
            return _zurueck(request)
        user.is_active = not user.is_active
        user.save(update_fields=["is_active"])
        if user.is_active:   # erste Freigabe mit Zeitstempel festhalten (Audit)
            from django.utils import timezone
            Teilnehmer.objects.filter(user=user, freigegeben_am__isnull=True).update(
                freigegeben_am=timezone.now())
        zustand = "freigeschaltet" if user.is_active else "gesperrt"
        messages.success(request, f"{user.get_full_name() or user.username} ist jetzt {zustand}.")
        return _zurueck(request)


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
        elif feld == "email_bestaetigt":
            # Admin-Override: E-Mail-Adresse manuell bestätigen (oder zurücksetzen)
            # – erlaubt den Login auch ohne Klick auf den Bestätigungslink.
            try:
                from allauth.account.models import EmailAddress
            except Exception:  # noqa: BLE001
                messages.error(request, "django-allauth ist in diesem Projekt nicht aktiv.")
                return _zurueck(request)
            if not user.email:
                messages.error(request, f"{user.get_username()} hat keine E-Mail-Adresse.")
                return _zurueck(request)
            ea = (EmailAddress.objects.filter(user=user, email__iexact=user.email).first()
                  or EmailAddress.objects.create(user=user, email=user.email, primary=True))
            ea.verified = not ea.verified
            ea.primary = True
            ea.save()
            from django.utils import timezone
            t.email_bestaetigt_am = timezone.now() if ea.verified else None
            t.save(update_fields=["email_bestaetigt_am"])
            zustand = "bestätigt" if ea.verified else "unbestätigt"
            messages.success(request, f"E-Mail von {user.get_username()} ist jetzt {zustand}.")
        return _zurueck(request)


class BenutzerLoeschenView(ZugriffMixin, View):
    def post(self, request, pk):
        user = get_object_or_404(User, pk=pk)
        if user == request.user:
            messages.error(request, "Du kannst dein eigenes Konto nicht löschen.")
            return _zurueck(request)
        name = user.get_full_name() or user.get_username()
        user.delete()
        messages.success(request, f"Benutzer {name} gelöscht.")
        return _zurueck(request)
