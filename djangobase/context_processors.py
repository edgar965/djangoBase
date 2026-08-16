from . import jobs
from .conf import conf


def djangobase(request):
    """Stellt Branding, Farben, Menue, Version und Layout-Optionen in
    jedem Template bereit. Die Layout-Keys (extra_css, extra_js_head,
    sidebar_template, theme_modes, theme_default, toast_stack) werden
    von djangobase/_shell.html + base_app.html konsumiert."""
    c = conf()
    return {"djangobase": {
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
    }}


def _test_arten(c):
    """[{'art','kurz','anzahl'}] - die Kategorien, die es wirklich gibt."""
    from .views.tests import TestsView
    try:
        _alles, arten, _rest = TestsView._kategorien_alle(c.get("test_befehle") or [])
    except Exception:                                          # noqa: BLE001
        return []
    # Dictionary gewollt: geht unveraendert in die Vorlage.
    return [{"art": a["art"], "kurz": a["kurz"], "anzahl": len(a["befehle"])}
            for a in arten if a.get("sammel")]
