import logging

from . import jobs
from .conf import conf
from .statik import Statik
from .pflichtmenue import PFLICHTSEITEN

log = logging.getLogger('djangobase.nav')


def _hilfe_extra(c):
    u"""Die Hilfeseiten des Projekts — Liste ODER Funktion.

    WARUM AUCH EINE FUNKTION (24.08.2026)
    =====================================
        „camtrack soll NICHT seine eigene Hilfe Seitenleiste nutzen, sondern
         die von djangoBase nutzen!!"

    CamTrack hat 32 eigene Hilfeseiten. Eine feste Liste in `settings.py`
    kann sie nicht tragen: Die Adressen entstehen ueber `reverse()`, und
    beim Laden der Einstellungen gibt es noch keine URL-Zuordnung. Fest
    eingetragene Pfade waeren beim naechsten Umbenennen still kaputt.

    Deshalb darf `hilfe_extra` auch ein Aufruf sein — als Funktion oder als
    gepunkteter Pfad. Er laeuft beim Anzeigen, wenn `reverse()` geht.

    Faellt er hin, bleibt das Menue leer statt die Seite mitzureissen: Eine
    Navigation ist Beiwerk, kein Grund fuer eine Fehlerseite.
    """
    wert = c.get("hilfe_extra") or []
    if isinstance(wert, str):
        try:
            from django.utils.module_loading import import_string
            wert = import_string(wert)
        except Exception:
            log.exception("hilfe_extra: %r nicht ladbar", wert)
            return []
    if callable(wert):
        try:
            wert = wert()
        except Exception:
            log.exception("hilfe_extra: Aufruf fehlgeschlagen")
            return []
    return list(wert or [])


def djangobase(request):
    """Stellt Branding, Farben, Menue, Version und Layout-Optionen in
    jedem Template bereit. Die Layout-Keys (extra_css, extra_js_head,
    sidebar_template, theme_modes, theme_default, toast_stack) werden
    von djangobase/_shell.html + base_app.html konsumiert."""
    c = conf()
    return {"djangobase": {
        # Cache-Kennung der MITGELIEFERTEN JS/CSS. Vorlagen haengen sie an
        # Skript-Adressen und ES-Importe (`?v={{ djangobase.statik_v }}`) —
        # ohne sie liefert der Browser-Cache alte Module aus, und der Fix kommt
        # nie an (gemessen 17.08.2026, siehe `statik.py`).
        "statik_v": Statik.kennung(),
        "titel": c["titel"],
        "untertitel": c["untertitel"],
        "logo_icon": c["logo_icon"],
        "favicon": c.get("favicon", ""),
        "farben": c["farben"],
        "base_template": c["base_template"],
        "menu": c["menu"],
        "version": c["version"],
        "extra_css": c["extra_css"],
        "extra_js_head": c["extra_js_head"],
        "extra_body_js": c.get("extra_body_js", []),
        "sidebar_template": c["sidebar_template"] or "djangobase/_sidebar.html",
        "theme_modes": c["theme_modes"],
        "theme_default": c["theme_default"],
        "toast_stack": c["toast_stack"],
        "resizable_sidebar": c["resizable_sidebar"],
        "sidebar_default": c["sidebar_default"],
        "sidebar_min": c["sidebar_min"],
        "sidebar_max": c["sidebar_max"],
        "sidebar_storage_key": c.get("sidebar_storage_key", ""),
        "sidebar_extra_css_vars": c.get("sidebar_extra_css_vars", ""),
        "einstellungen_menu": c["einstellungen_menu"],
        "hilfe_menu": c["hilfe_menu"],
        # Profil-Umschalter (Combobox + Anlegen/Loeschen) auf der
        # Einstellungsseite zeigen? Projekte mit nur EINEM Profil koennen das
        # per DJANGOBASE["profile_switcher"]=False ausblenden. Default True ->
        # bestehende Projekte unveraendert.
        "profile_switcher": c.get("profile_switcher", True),
        "einstellungen_extra": c["einstellungen_extra"],
        "hilfe_extra": _hilfe_extra(c),
        "benutzer_verwaltung": c["benutzer_verwaltung"],
        # Nav-Eintrag „Jobs" nur zeigen, wenn ein Projekt Jobs registriert hat
        # (djangobase.jobs). Leere Registry -> kein Eintrag -> bestehende
        # Projekte unveraendert.
        "has_jobs": jobs.has_jobs(),
        # „Review" und „Aktuell" erscheinen in JEDEM Projekt (Vorgabe
        # 13.08.2026) — deshalb steht hier kein Schalter mehr. Ob ein
        # Modell-Partner konfiguriert ist, erklaert die Review-Seite selbst.
        #
        # Die Test-Kategorien fuers Menue („Alle Unit-Tests", „Alle Component
        # …"). Sie stehen im Menue an ERSTER Stelle, vor den einzelnen
        # Bereichen — das ist der haeufigere Wunsch. Abgeleitet aus
        # ``test_befehle``, also auch in Projekten mit handgepflegter Liste
        # vorhanden (Vorgabe 17.08.2026: „in allen Projekten sichtbar").
        "test_arten": _test_arten(c),
        # Die Werkzeugkasten-Seiten (Skills/Skills1/Skills2) fuer
        # ``_nav_skills.html``. Sie kamen dort frueher HANDGEPFLEGT vor - und
        # genau das ging schief: ``Skills1`` war gebaut und stand in keinem
        # Menue (17.08.2026). Jetzt liest die Vorlage dieselbe Liste, die auch
        # ``pflicht_eintraege()`` an Projekte mit eigener Sidebar gibt.
        # Die Objekte selbst, nicht ``als_dict()``: Die Vorlage braucht
        # zusaetzlich ``route`` fuer das Aktiv-Kennzeichen, und das
        # Uebergabeformat der Menue-Bauer bleibt davon unberuehrt.
        "pflichtseiten": PFLICHTSEITEN,
    }}


def _test_arten(c):
    u"""[{'art','kurz','anzahl'}] - die Kategorien, die es wirklich gibt.

    STILLER FEHLER, gefunden am 17.08.2026: Hier stand ein Aufruf von
    ``TestsView._kategorien_alle`` — eine Methode, die beim Aufteilen der View
    nach :class:`~.testkategorien.Kategorien` gewandert war. Das ``except``
    fing den ``AttributeError``, gab eine leere Liste zurueck, und im Menue
    stand seither nur noch „Alle". Kein Fehler, keine Meldung, eine halbe
    Navigation weniger.

    Jetzt: die richtige Quelle, und ein Fehlschlag geht ins Log.
    """
    from .testkategorien import Kategorien
    befehle = c.get("test_befehle") or []
    try:
        if not befehle:
            # Dieselbe Ableitung wie die Seite selbst - sonst haette ein
            # Projekt ohne gepflegte `test_befehle` eine Seite voller Tests
            # und ein leeres Menue.
            from .views.tests import TestsView
            befehle = TestsView._befehle_abgeleitet()
        arten = Kategorien(befehle).arten
    except Exception:                                          # noqa: BLE001
        import logging
        logging.getLogger("djangobase.tests").exception(
            "Test-Kategorien fuer das Menue nicht ermittelbar - der Eintrag "
            "Tests zeigt dann nur 'Alle'")
        return []
    # Dictionary gewollt: geht unveraendert in die Vorlage.
    return [{"art": a["art"], "kurz": a["kurz"], "anzahl": len(a["befehle"])}
            for a in arten if a.get("sammel")]
