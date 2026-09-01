# -*- coding: utf-8 -*-
u"""Grundtests - die Mindestabsicherung, die in JEDES Projekt gehoert.

    Test-Art „automated": sichert die Grundfunktion, laeuft in Sekunden, braucht
    kein Netz, keine GPU, kein IMAP. Alles, was laenger dauert, ist ein
    Longrunner.

WAS HIER DRINSTEHT UND WARUM
============================
Jede Klasse faengt eine Fehlerklasse ab, die in echten Sitzungen Zeit gekostet
hat - und zwar die gemeinste Sorte: Der Server startet, die Seite liefert 200,
und trotzdem ist etwas kaputt.

    Werkzeugkatalog   ein vorhandenes Pruefwerkzeug wird nachgebaut
    Seiten            kaputter Import, Vorlagenfehler, fehlende Kontextvariable
    Urls              eine Funktion ist umgezogen und die Route zeigt ins Leere
    Module            Syntaxfehler in einer Datei, die niemand importiert hat
    Migrationen       Modell geaendert, `makemigrations` vergessen
    Vorlagen          TemplateSyntaxError faellt sonst erst beim Aufruf auf
    Systemcheck       Konfigurationsfehler
    Logging           Fehler landen nirgends (Kriterium 16)
    Menue             Eintrag zeigt auf eine Route, die es nicht mehr gibt
    EsModule          „Seite laedt, Konsole schweigt, Knopf tot"

BENUTZUNG IM PROJEKT
====================
Eine Datei ``<app>/tests/automated/test_grund.py`` mit:

    from djangobase.grundtests import *      # noqa: F401,F403

Der Testlaeufer entdeckt die Klassen darin und faehrt sie. Einschraenken laesst
sich alles ueber ``DJANGOBASE["grundtests"]``:

    "grundtests": {
        "seiten_aus": ["/admin/", "/api/langsam/"],   # nicht anfahren
        "module_apps": ["search", "mail"],            # sonst alle eigenen Apps
        "modelle": ["search.Document"],               # Anlegen/Lesen/Loeschen
    }

WARUM „KEIN 5xx" UND NICHT „STATUS 200"
=======================================
Geschuetzte Seiten antworten mit 302 auf die Anmeldung, manche mit 403 - das ist
richtig so. Ein 500er dagegen ist immer ein Fehler. Die Zusicherung lautet
deshalb „kein Serverfehler", nicht „200": Sonst wird der Test bei der ersten
Anmeldepflicht abgeschaltet, und dann prueft er gar nichts mehr.
"""
import importlib
import pkgutil
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase, TestCase

# ERSTER FALL DER LISTE (Ansage 25.08.2026). Er prueft nichts am
# Programm - er DRUCKT den Werkzeugkasten und meldet Nachbauten. Genau
# deshalb steht er vorn: Wer den Bericht von oben liest, sieht zuerst,
# was es an Pruefwerkzeugen schon gibt, und baut es nicht ein zweites
# Mal. Anlass war ein Nachbau von `fix_importe`, den niemand gebraucht
# haette - der vorhandene Fixer war sogar gruendlicher.
from .werkzeugkatalog import GrundtestWerkzeugkatalog  # noqa: F401


#: Verzeichnisnamen, die nie Projektcode sind. NUR die Notbremse — die
#: eigentliche Antwort gibt :func:`_projektdateien` über git.
FREMDE_ORDNER = ("node_modules", "venv", "pythonVENV", ".venv", "site-packages")


def _projektdateien(muster):
    u"""Dateien unter ``BASE_DIR``, die zum Projekt gehören.

    WARUM NICHT NUR DIE NAMENSLISTE (31.08.2026)
    ============================================
    Hier stand zweimal dieselbe feste Liste (`node_modules`, `venv`, …).
    Sie kennt nur, was jemand aufgeschrieben hat — und übersah damit
    ``_wegwerf/``, den Ordner, in den ``Ablageumleitung`` die
    Zwischendateien der Testläufe umlenkt, damit sie nicht auf C: landen.

    Darin liegen Attrappen: winzige ``static/app/js/start.js``, die
    absichtlich auf ein fehlendes Nachbarmodul zeigen, weil ein Test
    genau diesen Fall prüft. ``GrundtestEsModule`` las sie als echten
    Projektcode und meldete vier JS-Importe ins Leere — ein Fehlalarm,
    der jeden Gesamtlauf rot machte. Ein Test, der aus eigenen Resten
    rot wird, wird nach der zweiten Woche ignoriert.

    ``.gitignore`` wusste es die ganze Zeit: ``_wegwerf/`` steht dort in
    Zeile 67. Also wird git gefragt statt einer zweiten Liste. Antwortet
    git nicht (kein Repo, kein git im Pfad), filtert ``GitFilter``
    nichts — dann greift die Namensliste als Notbremse, wie bisher.
    """
    from .skills.gitfilter import GitFilter

    basis = Path(str(settings.BASE_DIR))
    filter_ = GitFilter(basis)
    for pfad in sorted(basis.rglob(muster)):
        if any(t in pfad.parts for t in FREMDE_ORDNER):
            continue
        if not filter_.erlaubt(pfad):
            continue
        yield pfad

__all__ = ["GrundtestWerkzeugkatalog",
           "GrundtestSeiten", "GrundtestUrls", "GrundtestModule",
           "GrundtestMigrationen", "GrundtestVorlagen", "GrundtestSystemcheck",
           "GrundtestLogging", "GrundtestMenue", "GrundtestEsModule",
           "einstellung"]


def einstellung(name, vorgabe=None):
    """Ein Wert aus ``DJANGOBASE["grundtests"]``."""
    cfg = (getattr(settings, "DJANGOBASE", {}) or {}).get("grundtests") or {}
    return cfg.get(name, vorgabe)


def _routen():
    """[(Muster, Callable, Name)] aller Routen des Projekts."""
    from django.urls import get_resolver
    aus = []

    def gehen(muster, praefix=""):
        for p in muster:
            if hasattr(p, "url_patterns"):
                gehen(p.url_patterns, praefix + str(p.pattern))
            else:
                aus.append((praefix + str(p.pattern), p.callback,
                            getattr(p, "name", "") or ""))
    gehen(get_resolver().url_patterns)
    return aus


def _eigene_apps():
    """Apps des Projekts (ohne Django und Fremdpakete)."""
    fest = einstellung("module_apps")
    if fest:
        return list(fest)
    basis = Path(str(settings.BASE_DIR))
    return [a for a in settings.INSTALLED_APPS
            if not a.startswith("django.") and (basis / a.split(".")[0]).is_dir()]


class GrundtestUrls(SimpleTestCase):
    """Jede Route zeigt auf etwas, das es gibt."""

    def test_jede_route_hat_einen_aufrufbaren_ziel(self):
        tot = [m for m, cb, _ in _routen() if not callable(cb)]
        self.assertEqual(tot, [], "Routen ohne aufrufbares Ziel: %s" % tot)

    def test_keine_route_zeigt_auf_ein_fehlendes_modul(self):
        fehlt = []
        for muster, cb, _ in _routen():
            modul = getattr(cb, "__module__", "")
            if modul and importlib.util.find_spec(modul) is None:
                fehlt.append("%s -> %s" % (muster, modul))
        self.assertEqual(fehlt, [], "Route zeigt auf fehlendes Modul: %s" % fehlt)


class GrundtestSeiten(TestCase):
    """Keine Seite antwortet mit einem Serverfehler."""

    #: Routen mit Parametern werden uebersprungen - ohne gueltige Werte waere
    #: ein 404 zu erwarten und die Aussage waere keine.
    def test_keine_seite_wirft_5xx(self):
        aus = set(einstellung("seiten_aus") or [])
        kaputt = []
        for muster, _cb, _name in _routen():
            pfad = "/" + muster.lstrip("^/")
            if "<" in pfad or "(" in pfad or pfad in aus:
                continue
            if any(pfad.startswith(a) for a in aus):
                continue
            try:
                antwort = self.client.get(pfad)
            except Exception as e:                            # noqa: BLE001
                kaputt.append("%s -> %s: %s" % (pfad, type(e).__name__, e))
                continue
            if antwort.status_code >= 500:
                kaputt.append("%s -> %d" % (pfad, antwort.status_code))
        self.assertEqual(kaputt, [], "Seiten mit Serverfehler: %s" % kaputt)


class GrundtestModule(SimpleTestCase):
    """Jedes Modul der eigenen Apps lässt sich importieren."""

    def test_alle_module_importierbar(self):
        fehler = []
        for app in _eigene_apps():
            try:
                paket = importlib.import_module(app)
            except Exception as e:                            # noqa: BLE001
                fehler.append("%s: %s" % (app, e))
                continue
            for _f, name, _p in pkgutil.walk_packages(
                    getattr(paket, "__path__", []), app + "."):
                if ".migrations" in name or ".tests" in name:
                    continue
                try:
                    importlib.import_module(name)
                except Exception as e:                        # noqa: BLE001
                    fehler.append("%s: %s: %s" % (name, type(e).__name__, e))
        self.assertEqual(fehler, [], "Nicht importierbar: %s" % fehler)


class GrundtestMigrationen(TestCase):
    """Kein Modell wurde geaendert, ohne eine Migration zu schreiben.

    ``TestCase`` statt ``SimpleTestCase``: ``makemigrations --check`` fragt die
    Datenbank, und ``SimpleTestCase`` verbietet das (DatabaseOperationForbidden
    beim ersten Lauf, 17.08.2026)."""

    def test_keine_ausstehenden_migrationen(self):
        from io import StringIO

        from django.core.management import call_command
        puffer = StringIO()
        try:
            call_command("makemigrations", "--check", "--dry-run",
                         stdout=puffer, stderr=puffer, verbosity=1)
        except SystemExit as e:
            self.fail("Ausstehende Migrationen (%s): %s" % (e, puffer.getvalue()))


class GrundtestVorlagen(SimpleTestCase):
    """Jede Vorlage lässt sich uebersetzen (kein TemplateSyntaxError)."""

    def test_alle_vorlagen_kompilieren(self):
        from django.template import TemplateSyntaxError
        from django.template.loader import get_template
        fehler = []
        for pfad in _projektdateien("templates/**/*.html"):
            teile = pfad.parts
            name = "/".join(teile[teile.index("templates") + 1:])
            try:
                get_template(name)
            except TemplateSyntaxError as e:
                fehler.append("%s: %s" % (name, e))
            except Exception:                                 # noqa: BLE001
                pass          # nicht auffindbar/doppelt: kein Syntaxproblem
        self.assertEqual(fehler, [], "Vorlagen mit Syntaxfehler: %s" % fehler)


class GrundtestSystemcheck(SimpleTestCase):
    """``manage.py check`` meldet nichts."""

    def test_systemcheck_ohne_fehler(self):
        from django.core.checks import Error, run_checks
        schwer = [str(m) for m in run_checks() if isinstance(m, Error)]
        self.assertEqual(schwer, [], "Systemcheck: %s" % schwer)


class GrundtestLogging(SimpleTestCase):
    """Kriterium 16: Fehler landen in einer Datei, die rotiert."""

    def test_logging_ist_konfiguriert(self):
        cfg = getattr(settings, "LOGGING", None)
        self.assertTrue(cfg, "Kein LOGGING konfiguriert — dblog.config nutzen")
        handler = list((cfg.get("handlers") or {}).values())
        self.assertTrue(
            any("Rotating" in str(h.get("class", "")) for h in handler),
            "Kein rotierender Handler — die Logdatei wächst unbegrenzt")

    def test_zeitstempel_im_format(self):
        cfg = getattr(settings, "LOGGING", None) or {}
        formate = " ".join(str(f.get("format", ""))
                           for f in (cfg.get("formatters") or {}).values())
        if formate:
            self.assertIn("asctime", formate,
                          "Ohne {asctime} ist keine Aktion zeitlich einzuordnen")

    def test_logverzeichnis_beschreibbar(self):
        cfg = getattr(settings, "LOGGING", None) or {}
        for h in (cfg.get("handlers") or {}).values():
            datei = h.get("filename")
            if not datei:
                continue
            ordner = Path(str(datei)).parent
            self.assertTrue(ordner.is_dir(),
                            "Logverzeichnis fehlt: %s" % ordner)


class GrundtestMenue(SimpleTestCase):
    """Kein Menuepunkt zeigt auf eine Route, die es nicht gibt."""

    def test_menue_zeigt_nicht_ins_leere(self):
        from django.urls import resolve
        cfg = (getattr(settings, "DJANGOBASE", {}) or {})
        ziele = []

        def sammeln(eintraege):
            for e in eintraege or []:
                if not isinstance(e, dict):
                    continue
                ziel = e.get("url") or e.get("href") or ""
                if ziel and str(ziel).startswith("/"):
                    ziele.append(str(ziel))
                for s in ("kinder", "children", "unter", "items", "eintraege"):
                    sammeln(e.get(s))
        sammeln(cfg.get("menu"))
        tot = []
        for ziel in ziele:
            try:
                resolve(ziel.split("?")[0].split("#")[0])
            except Exception:                                 # noqa: BLE001
                tot.append(ziel)
        self.assertEqual(tot, [], "Menuepunkte ohne Route: %s" % tot)


class GrundtestEsModule(SimpleTestCase):
    """Kein relativer JS-Import zeigt auf eine fehlende Datei.

    Die Fehlerklasse aus der Praxis: Der Browser laedt das Einstiegsmodul nicht,
    es gibt KEINEN Teilausfall - nur eine tote Seite und eine Meldung in einer
    Konsole, die niemand offen hat."""

    def test_relative_importe_zeigen_auf_dateien(self):
        import re
        muster = re.compile(r"""import\s+[^;'"]*?from\s*['"](\.[^'"]+)['"]""")
        fehlt = []
        for pfad in _projektdateien("static/**/*.js"):
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for treffer in muster.findall(text):
                ziel = (pfad.parent / treffer.split("?")[0]).resolve()
                if not ziel.exists():
                    fehlt.append("%s -> %s" % (pfad.name, treffer))
        self.assertEqual(fehlt, [], "JS-Importe ins Leere: %s" % fehlt)
