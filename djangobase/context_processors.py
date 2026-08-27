import logging

from . import jobs
from .basiswurzel import Basiswurzel
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


def _offen_setzen(eintraege, aktiv):
    u"""Ein Klappmenü, dessen Seite gerade offen ist, muss offen stehen.

    DIE FALLE, ZWEIMAL DIESELBE (24.08.2026)
    ========================================
    Das aufklappbare Untermenü hatte kein ``show`` — es blieb auf seinen
    EIGENEN Seiten zu. Wer „Technik → Kodierung" anklickte, sah danach ein
    geschlossenes „Technik" und keinen Hinweis, wo er ist.

    Genau das hat `test_genau_ein_abschnitt_ist_offen` schon einmal für die
    Hilfe-Gruppe gemeldet („/help/prozesse/: 0 offene Abschnitte"). Dort
    wurde es an Ort und Stelle geflickt; hier ist es wiedergekommen, weil
    die Regel nirgends stand. Jetzt steht sie an EINER Stelle und gilt für
    jede Schachtelungstiefe.

    Arbeitet auf Kopien: Die Liste kommt womöglich aus einer Konstanten des
    Projekts, und ein Kontextprozessor, der sie beschreibt, verändert sie
    für jeden weiteren Aufruf.
    """
    raus = []
    for eintrag in eintraege or ():
        if not isinstance(eintrag, dict):
            raus.append(eintrag)
            continue
        eintrag = dict(eintrag)
        for schluessel in ('untermenu', 'abschnitt'):
            kinder = eintrag.get(schluessel)
            if not kinder:
                continue
            kinder = _offen_setzen(kinder, aktiv)
            eintrag[schluessel] = kinder
            if any(k.get('offen') or (k.get('aktiv') and k['aktiv'] == aktiv)
                   for k in kinder if isinstance(k, dict)):
                eintrag['offen'] = True
        raus.append(eintrag)
    return raus


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
        # Praefix, unter dem `djangobase.urls` haengt. Die
        # mitgelieferten JS-Module lesen ihn aus dem Grundgeruest —
        # vorher stand `/hilfe/` in vier Dateien fest und lieferte in
        # jedem anders eingebundenen Projekt eine stille 404
        # (Befund 27.08.2026, siehe `basiswurzel.py`).
        "wurzel": Basiswurzel.weg(),
        "titel": c["titel"],
        "untertitel": c["untertitel"],
        "logo_icon": c["logo_icon"],
        "favicon": c.get("favicon", ""),
        # Mehrere Zeichen mit Cache-Kennung (26.08.2026, aus CamTrack).
        "favicons": c.get("favicons", ()),
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
        "sidebar_extra_class": c.get("sidebar_extra_class", ""),
        "einstellungen_menu": c["einstellungen_menu"],
        "hilfe_menu": c["hilfe_menu"],
        # Profil-Umschalter (Combobox + Anlegen/Loeschen) auf der
        # Einstellungsseite zeigen? Projekte mit nur EINEM Profil koennen das
        # per DJANGOBASE["profile_switcher"]=False ausblenden. Default True ->
        # bestehende Projekte unveraendert.
        "profile_switcher": c.get("profile_switcher", True),
        "einstellungen_extra": c["einstellungen_extra"],
        # Die offene Gruppe kennt nur der Kontextprozessor: Der URL-Name
        # steht am `resolver_match`, und die Eintraege tragen ihn als
        # `aktiv`. In der Vorlage waere dieselbe Frage eine Schleife ueber
        # unbekannte Tiefe — dort gibt es die nicht.
        "hilfe_extra": _offen_setzen(
            _hilfe_extra(c),
            getattr(getattr(request, 'resolver_match', None),
                    'url_name', '') or ''),
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
            "Test-Kategorien für das Menue nicht ermittelbar - der Eintrag "
            "Tests zeigt dann nur 'Alle'")
        return []
    # Dictionary gewollt: geht unveraendert in die Vorlage.
    return [{"art": a["art"], "kurz": a["kurz"], "anzahl": len(a["befehle"])}
            for a in arten if a.get("sammel")]
