# -*- coding: utf-8 -*-
u"""Sind Hilfe→Versionen und der UI-Rahmen dieses Projekts djangoBase-konform?

DER AUFTRAG (Edgar, 21.08.2026)
==============================
    „3. Ist Hilfe - Versionen konform mit djangoBase Template
     4. Ist das UI tamplate (menü, verschiebbares Menubar) konform mit
        djangoBase template"

    Nachtrag: „lösche alle testcases die eine test db brauchen, überleg dir was
    anderes!"

OHNE DATENBANK
==============
Die erste Fassung meldete einen Nutzer an und rief die Seiten mit dem
Test-Client ab — dafür legt Django eine Test-Datenbank an und migriert sie.
Minuten für eine Frage, die keine Daten betrifft.

Stattdessen wird an drei Stellen geprüft, die zusammen dasselbe aussagen:

    1. **Konfiguration** — was das Projekt an djangoBase übergibt (Menü, repos,
       resizable_sidebar). Hier steckt der Großteil der Konformität.
    2. **Die eigenen Vorlagen** — erben sie den Rahmen, und überschreiben sie
       den Block, der die Seitenleiste trägt?
    3. **Die djangoBase-Vorlagen selbst** — bringen sie noch das mit, worauf
       sich Punkt 1 und 2 verlassen? Ohne diese Gegenprobe prüften die anderen
       gegen eine Annahme, die längst überholt sein kann.
"""
import re
from pathlib import Path

from django.conf import settings
from django.test import SimpleTestCase

from djangobase.tests.konform.quellen import TABU, dateien  # noqa: F401

#: Wurzel des djangoBase-Pakets.
PAKET = Path(__file__).resolve().parents[2]
VORLAGEN = PAKET / "templates" / "djangobase"

_EXTENDS = re.compile(r"{%\s*extends\s+[\"']?([^\"'%\s]+)")


def _djangobase(schluessel):
    return (getattr(settings, "DJANGOBASE", {}) or {}).get(schluessel)


def _menue_durchgehen(punkte, pfad=""):
    u"""Jeden Menüpunkt mit seinem Pfad liefern — auch dritte Ebene."""
    for p in punkte or ():
        if not isinstance(p, dict):
            continue
        name = pfad + str(p.get("label") or "(ohne Label)")
        yield name, p
        yield from _menue_durchgehen(p.get("untermenu"), name + " → ")


class VersionenKonformTest(SimpleTestCase):
    u"""Punkt 3: Hilfe → Versionen."""

    databases = []          # ausdrücklich keine: dieser Test fasst nie Daten an

    def test_repos_sind_konfiguriert(self):
        u"""Ohne ``repos`` fragt die Seite nichts ab und bleibt dauerhaft leer —
        ohne Fehlermeldung."""
        self.assertTrue(_djangobase("repos"),
                        u"DJANGOBASE['repos'] ist leer. Die Versions-Seite zieht "
                        u"ihre Historie aus GitHub; ohne Repo-Angabe zeigt sie "
                        u"still nichts an.")

    def test_repo_eintraege_haben_namen(self):
        u"""Ein Eintrag ohne Namen erscheint in der Auswahl als leere Zeile."""
        luecken = []
        for r in _djangobase("repos") or ():
            if isinstance(r, (list, tuple)):
                name = r[0] if r else None
            elif isinstance(r, dict):
                name = r.get("name")
            else:
                name = r
            if not name:
                luecken.append(repr(r)[:50])
        self.assertFalse(luecken, u"Repo-Einträge ohne Namen: %s" % luecken[:3])

    def test_version_ist_gesetzt(self):
        u"""Die Projektkonvention: Die aktuelle Version steht immer im UI."""
        self.assertTrue(_djangobase("version"),
                        u"DJANGOBASE['version'] fehlt — die Sidebar zeigt dann "
                        u"keine Versionsnummer.")

    def test_die_vorlage_bringt_ihren_teil_mit(self):
        u"""Gegenprobe an der djangoBase-Vorlage selbst: Erbt sie nicht mehr,
        wäre die Seite ohne Seitenleiste — und alle Prüfungen oben blieben
        trotzdem grün."""
        text = (VORLAGEN / "hilfe" / "versions.html").read_text(encoding="utf-8")
        self.assertTrue(_EXTENDS.search(text),
                        u"djangobase/hilfe/versions.html erbt von nichts mehr.")
        self.assertIn("vw-", text,
                      u"Die Versions-Klassen (vw-tag/vw-pill) fehlen in der "
                      u"Vorlage — dann zeigt die Seite keine Historie mehr.")


class MenueKonformTest(SimpleTestCase):
    u"""Punkt 4: Menü und Seitenleiste — aus der Konfiguration gelesen."""

    databases = []

    def test_menue_ist_gefuellt(self):
        u"""Eine leere Seitenleiste ist formal konform und praktisch nutzlos.

        ZWEI WEGE, EIN ERGEBNIS (Korrektur 21.08.2026): djangoBase baut die
        Seitenleiste entweder aus ``menu`` — oder das Projekt bringt eine
        eigene Vorlage mit (``sidebar_template``, im Rezept ausdrücklich
        vorgesehen: „Eigene Sidebar behalten"). Der assistant tut das seit
        jeher; die erste Fassung dieser Prüfung meldete ihn trotzdem als
        „Seitenleiste leer", obwohl dort LLM-Status, Mail-Konten und
        Chat-Sitzungen stehen. Ein Prüfer, der die dokumentierte Alternative
        anmeckert, wird abgeschaltet statt gelesen."""
        eigene = _djangobase("sidebar_template")
        self.assertTrue(_djangobase("menu") or eigene,
                        u"Weder DJANGOBASE['menu'] noch ['sidebar_template'] "
                        u"gesetzt — die Seitenleiste bliebe bis auf "
                        u"Hilfe/Einstellungen leer.")

    def test_eigene_seitenleiste_gibt_es_wirklich(self):
        u"""Eine Vorlage, die nicht auffindbar ist, wirft erst beim Aufruf —
        also womöglich erst beim Nutzer."""
        eigene = _djangobase("sidebar_template")
        if not eigene:
            self.skipTest("keine eigene Seitenleiste konfiguriert")
        from django.template import TemplateDoesNotExist
        from django.template.loader import get_template
        try:
            get_template(eigene)
        except TemplateDoesNotExist:
            self.fail(u"DJANGOBASE['sidebar_template'] = %r ist nicht "
                      u"auffindbar." % eigene)

    def test_untermenue_heisst_untermenu(self):
        u"""``items`` löst in Django-Vorlagen auf ``dict.items`` auf und ist
        damit IMMER wahr — jeder Punkt würde fälschlich aufklappbar.

        Der Kommentar in ``_sidebar.html`` warnt davor; hier wird es geprüft
        statt nur beschrieben."""
        falsch = [name for name, p in _menue_durchgehen(_djangobase("menu"))
                  if "items" in p]
        self.assertFalse(falsch,
                         u"Diese Menüpunkte nutzen „items“ statt „untermenu“: %s"
                         % ", ".join(falsch))

    def test_jeder_punkt_hat_ein_ziel(self):
        u"""Ein Punkt ohne URL ist ein toter Eintrag, einer ohne Label unsichtbar."""
        luecken = []
        for name, p in _menue_durchgehen(_djangobase("menu")):
            if not p.get("label"):
                luecken.append(name + ": kein label")
            elif not p.get("untermenu") and not p.get("url"):
                luecken.append(name + ": weder url noch untermenu")
        self.assertFalse(luecken, u"Unvollständige Menüpunkte: %s"
                         % "; ".join(luecken[:8]))

    def test_verschiebbare_menuleiste(self):
        u"""„verschiebbares Menubar" (Ansage): Der Ziehgriff kommt aus
        ``sidebar_resizer.js`` und wird nur geladen, wenn das Projekt
        ``resizable_sidebar`` setzt. Ohne das Flag ist die Breite fest."""
        self.assertTrue(_djangobase("resizable_sidebar"),
                        u"DJANGOBASE['resizable_sidebar'] ist nicht gesetzt — die "
                        u"Seitenleiste lässt sich nicht in der Breite ziehen. "
                        u"djangoBase liefert das fertig mit.")

    def test_der_griff_wird_bei_gesetztem_flag_geladen(self):
        u"""Gegenprobe in der Shell: Das Flag allein bewirkt nichts, wenn die
        Vorlage das Modul nicht mehr einbindet."""
        if not _djangobase("resizable_sidebar"):
            self.skipTest("Flag nicht gesetzt - siehe Test darüber")
        shell = (VORLAGEN / "_shell.html").read_text(encoding="utf-8")
        self.assertIn("sidebar_resizer.js", shell,
                      u"_shell.html lädt sidebar_resizer.js nicht mehr — der "
                      u"Griff fehlt trotz gesetztem Flag.")
        self.assertIn("resizable_sidebar", shell,
                      u"Die Bedingung um den Ziehgriff ist verschwunden.")


class EigeneVorlagenTest(SimpleTestCase):
    u"""Erben die Vorlagen des Projekts den djangoBase-Rahmen?"""

    databases = []

    def basis_vorlagen(self):
        u"""Die Projekt-Vorlagen, die ihrerseits als Basis dienen."""
        for pfad in dateien(".html"):
            if not pfad.name.startswith("base") or PAKET in pfad.parents:
                continue
            yield pfad

    def test_eine_basis_vorlage_erbt_von_djangobase(self):
        u"""Erbt die eigene Basis nicht mehr, verlieren ALLE Seiten auf einmal
        Seitenleiste, Menü und Versionsnummer.

        Erlaubt ist eine Kette über mehrere Ebenen — sie muss nur irgendwo bei
        djangoBase ankommen. Gemeldet wird deshalb erst, wenn KEINE erbt."""
        eltern = []
        for pfad in self.basis_vorlagen():
            text = pfad.read_text(encoding="utf-8", errors="replace")
            m = _EXTENDS.search(text)
            if m:
                eltern.append((pfad.name, m.group(1)))
        if not eltern:
            self.skipTest("keine erbende Basis-Vorlage gefunden")
        self.assertTrue(any(z.startswith("djangobase/") for _, z in eltern),
                        u"Keine Basis-Vorlage erbt von djangobase/: %s"
                        % "; ".join("%s → %s" % (a, b) for a, b in eltern[:5]))

    def test_sidebar_block_wird_nicht_leer_ueberschrieben(self):
        u"""Wer ``{% block sidebar %}{% endblock %}`` schreibt, hat formal
        geerbt und praktisch keine Seitenleiste."""
        leer = re.compile(r"{%\s*block\s+sidebar\s*%}\s*{%\s*endblock")
        treffer = [p.name for p in self.basis_vorlagen()
                   if leer.search(p.read_text(encoding="utf-8", errors="replace"))]
        self.assertFalse(treffer,
                         u"Diese Vorlagen überschreiben den sidebar-Block mit "
                         u"Leere: %s" % ", ".join(treffer))


class GegenprobeTest(SimpleTestCase):
    u"""Greifen die Regeln?"""

    databases = []

    def test_items_falle_wird_erkannt(self):
        probe = [{"label": "Falsch", "items": [{"label": "x", "url": "/"}]}]
        falsch = [n for n, p in _menue_durchgehen(probe) if "items" in p]
        self.assertEqual(falsch, ["Falsch"])

    def test_luecke_wird_erkannt(self):
        probe = [{"label": "Ohne Ziel"}]
        luecken = [n for n, p in _menue_durchgehen(probe)
                   if not p.get("untermenu") and not p.get("url")]
        self.assertEqual(luecken, ["Ohne Ziel"])

    def test_dritte_ebene_wird_erreicht(self):
        u"""Ein Fehler in der dritten Ebene darf nicht durchrutschen."""
        probe = [{"label": "A", "untermenu": [
            {"label": "B", "untermenu": [{"label": "C"}]}]}]
        namen = [n for n, _ in _menue_durchgehen(probe)]
        self.assertIn("A → B → C", namen)

    def test_shell_vorlage_existiert(self):
        u"""Ohne sie prüfte test_der_griff_wird_bei_gesetztem_flag_geladen
        gegen eine Datei, die es nicht gibt."""
        self.assertTrue((VORLAGEN / "_shell.html").exists())
