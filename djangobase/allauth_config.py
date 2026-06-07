"""Wiederverwendbare django-allauth-Konfiguration für djangoBase-Projekte.

So bleibt die Registrierung/Anmeldung (E-Mail-Login + Pflicht-Bestätigung,
Rollenwahl Nutzer/Provider, deutsche Mails, gestyltes Layout) in EINEM Ort.

Dieses Modul importiert KEIN allauth und ist damit auch in Projekten ohne
allauth gefahrlos importierbar (z. B. via `from djangobase.allauth_config import *`).

Einbindung in settings.py eines Projekts:

    from djangobase.allauth_config import allauth_einrichten
    allauth_einrichten(globals(), subject_prefix="[meinprojekt] ", dev_http=DEBUG)

…oder die Konstanten/Helfer einzeln verwenden. `allauth_einrichten` ergänzt
INSTALLED_APPS/MIDDLEWARE/AUTHENTICATION_BACKENDS und setzt die ACCOUNT_*-
Defaults (ohne bereits gesetzte Werte zu überschreiben). Es achtet darauf,
dass das djangobase-App VOR allauth steht, damit die djangoBase-Templates
(account/, allauth/) die allauth-Defaults überschreiben.

Voraussetzung: `pip install django-allauth`, `path("accounts/",
include("allauth.account.urls"))` in den Projekt-URLs sowie SITE-Eintrag.
"""

# Apps, die allauth benötigt (Reihenfolge: NACH djangobase, s. allauth_einrichten)
ALLAUTH_APPS = ["django.contrib.sites", "allauth", "allauth.account"]
ALLAUTH_MIDDLEWARE = "allauth.account.middleware.AccountMiddleware"
ALLAUTH_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",            # Admin/Username-Login
    "allauth.account.auth_backends.AuthenticationBackend",  # allauth (E-Mail-Login)
]

# ACCOUNT_*-Defaults: E-Mail-Login, Pflicht-Bestätigung, Rollen-Signup-Formular.
ACCOUNT_DEFAULTS = {
    "ACCOUNT_LOGIN_METHODS": {"email"},
    "ACCOUNT_SIGNUP_FIELDS": ["email*", "password1*", "password2*"],
    "ACCOUNT_EMAIL_VERIFICATION": "mandatory",
    "ACCOUNT_UNIQUE_EMAIL": True,
    "ACCOUNT_LOGOUT_ON_GET": True,
    "ACCOUNT_RATE_LIMITS": {"login_failed": "5/5m"},
    "ACCOUNT_SIGNUP_FORM_CLASS": "djangobase.forms.RollenSignupForm",
    "LOGIN_URL": "/accounts/login/",
    "ACCOUNT_LOGOUT_REDIRECT_URL": "/",
}


def allauth_einrichten(g, *, subject_prefix="[djangoBase] ", dev_http=True, site_id=1):
    """Ergänzt das settings-`globals()`-Dict um die allauth-Konfiguration.

    g          – das globals()-Dict der settings.py
    subject_prefix – Präfix der Betreffzeilen (Bestätigungs-Mails)
    dev_http   – True: Bestätigungs-Links als http:// (Dev-Server ohne TLS)
    site_id    – SITE_ID (Default 1)
    """
    apps = list(g.get("INSTALLED_APPS", []))
    # allauth NACH djangobase einsortieren, damit djangoBase-Templates gewinnen.
    for a in ALLAUTH_APPS:
        if a not in apps:
            apps.append(a)
    g["INSTALLED_APPS"] = apps

    mw = list(g.get("MIDDLEWARE", []))
    if ALLAUTH_MIDDLEWARE not in mw:
        mw.append(ALLAUTH_MIDDLEWARE)
    g["MIDDLEWARE"] = mw

    g.setdefault("AUTHENTICATION_BACKENDS", ALLAUTH_BACKENDS)
    g.setdefault("SITE_ID", site_id)
    for key, wert in ACCOUNT_DEFAULTS.items():
        g.setdefault(key, wert)
    g.setdefault("ACCOUNT_EMAIL_SUBJECT_PREFIX", subject_prefix)
    if dev_http:
        g.setdefault("ACCOUNT_DEFAULT_HTTP_PROTOCOL", "http")
