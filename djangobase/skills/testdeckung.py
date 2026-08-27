# -*- coding: utf-8 -*-
u"""Testdeckung - welche Seite, welcher Endpunkt, welcher Menuepunkt hat KEINEN Test?

    Kriterium 17 (Zusatz): Testcases für alle wichtigen Funktionen und Menues.

DIE FRAGE VON DER ANDEREN SEITE
===============================
``testaufbau`` prüft, ob die vorhandenen Tests ordentlich liegen. Das sagt
nichts darueber, ob sie das Wichtige treffen. Hier wird umgekehrt gefragt: Das
Projekt sagt selbst, was wichtig ist - die URL-Tabelle und das Menue -, und für
jeden Eintrag wird nachgesehen, ob ihn irgendein Test ueberhaupt erwaehnt.

WARUM „ERWAEHNT" UND NICHT „GEPRUEFT"
=====================================
Ob ein Test etwas SINNVOLL prüft, kann ein Werkzeug nicht beurteilen. Dass eine
Seite in KEINEM Test vorkommt, ist dagegen eindeutig - und genau das ist die
teure Sorte Lücke: Ein Menuepunkt, den niemand fährt, fällt erst dem Nutzer
auf. Deshalb zählt jede Erwaehnung (URL-Name, Pfad oder Funktionsname), und der
Befund heißt „ungeprüft", nicht „falsch".

GEWICHTUNG
==========
Seiten (GET, im Menue verlinkt) wiegen schwerer als interne Endpunkte: Eine tote
Seite sieht der Nutzer sofort, eine tote API erst im Umweg. Menuepunkte ohne Test
stehen deshalb ganz oben.
"""
import re

from .werkzeug import Ergebnis
from .basis import EigenesWerkzeug

__all__ = ["Testdeckung"]


class Testdeckung(EigenesWerkzeug):
    slug = "testdeckung"
    titel = "Tests: was hat gar keinen?"
    zweck = ("Vergleicht URL-Tabelle und Menü mit dem, was die Tests erwähnen — "
             "und listet Seiten, Endpunkte und Menüpunkte ohne jeden Test.")
    befund = ("Ein Menüpunkt, den kein Test je aufruft, fällt erst dem Nutzer "
              "auf. Die Gliederung der Tests sagt darüber nichts.")
    abhilfe = ("Je ungeprüfter Seite ein UI-Test (Status 200 + eine Zusicherung "
               "auf den Inhalt), je Endpunkt ein Component-Test.")
    dauer = "3–10 s"
    kriterium = 17

    #: Django-eigene und Hilfsrouten - nicht die Verantwortung des Projekts.
    FREMD = ("admin:", "djangobase:", "account_", "socialaccount",
             "django.contrib", "allauth", "static", "media")

    #: Rahmencode. ``django.contrib`` allein reichte nicht: Djangos Admin legt
    #: fuer die alte Objekt-Adresse (``/admin/auth/group/<id>/``) eine
    #: ``RedirectView`` an, und die wohnt in ``django.views.generic.base``.
    #: Sie stand in 3DTools als ungepruefte Projektseite in der Liste — ein
    #: Fehlalarm, der eine echte Luecke verdeckt haette (17.08.2026).
    RAHMEN = ("django.", "rest_framework.", "debug_toolbar.")

    #: Kein Anlassfall - und das ist in Ordnung:
    ohne_anlassfall_weil = "misst nur (welche Bereiche Tests haben)"

    def laufen(self):
        # Die Routen kommen aus DJANGO, nicht aus den geprueften Dateien. Auf
        # einem leeren Verzeichnis meldete das Werkzeug deshalb Seiten eines
        # Projekts, das dort gar nicht liegt — ein Fehlalarm, den die
        # Gegenprobe „laeuft auf leerem Projekt ohne Befund" gefunden hat
        # (17.08.2026).
        if not self.hat_code():
            return Ergebnis(["art", "stelle", "ziel", "hinweis"], [],
                            "kein Quelltext gefunden — nichts zu prüfen",
                            "Die Routen stammen aus Django; ohne Projektcode "
                            "wäre jede Meldung eine über ein fremdes Projekt.")
        erwaehnt = self._testtexte()
        zeilen = []
        zeilen += self._menue(erwaehnt)
        zeilen += self._routen(erwaehnt)
        zeilen += self._klassen(erwaehnt)
        rang = {"Menüpunkt ungeprüft": 0, "Seite ungeprüft": 1,
                "Klasse ungeprüft": 2, "Endpunkt ungeprüft": 3}
        zeilen.sort(key=lambda z: (rang.get(z["art"], 9),
                                   -z.get("gewicht", 0), z["stelle"]))
        seiten = [z for z in zeilen if z["art"] in ("Menüpunkt ungeprüft",
                                                    "Seite ungeprüft")]
        klassen = [z for z in zeilen if z["art"] == "Klasse ungeprüft"]
        return Ergebnis(
            ["art", "stelle", "ziel", "hinweis"], zeilen,
            "%d ungeprüft — %d Seiten/Menüpunkte (die sichtbaren), "
            "%d Klassen auf einem Arbeitsweg"
            % (len(zeilen), len(seiten), len(klassen)),
            "„Ungeprüft“ heißt: kommt in keinem Test vor. Ob ein vorhandener Test "
            "sinnvoll prüft, sagt dieses Werkzeug nicht — das bleibt Handarbeit.")

    # ------------------------------------------------------------------ Quellen

    def _testtexte(self):
        """Ein Text aus allen Testdateien - einmal gelesen, dann nachgeschlagen."""
        teile = []
        for d in self.dateien():
            name = "/" + d.name
            if "/tests" in name or name.rsplit("/", 1)[-1].startswith("test_"):
                teile.append(d.text)
        return "\n".join(teile)

    def _klassen(self, erwaehnt):
        u"""Welche KLASSE des laufenden Systems erwähnt kein Test?

        DIE ANSAGE (Edgar, 27.08.2026)
        ==============================
            „bdd soll ja auch den ganzen Code absuchen, ob es testcases
             dafür gibt usw"
            „merge das mit dem was es schon gibt, keine Duplikate"

        Bis hierher fragte dieses Werkzeug nur nach Seiten, Endpunkten und
        Menüpunkten — also nach dem, was das Projekt nach AUSSEN zeigt.
        Der Code dahinter kam nicht vor.

        Ein eigenes Werkzeug dafür wäre ein Duplikat gewesen: Die Frage
        ist dieselbe („was hat gar keinen Test?"), nur die Quelle ist eine
        andere. Also steht sie hier, als dritte Spalte derselben Antwort.

        WARUM NICHT ALLE 448 IN DER LISTE STEHEN
        ========================================
        Gemessen an CamTrack am 27.08.2026: **448 von 587 Klassen** (76 %)
        erwähnt kein Test. Diese Zahl ungefiltert auszugeben wäre keine
        Arbeitsliste, sondern eine Tapete — man liest sie einmal und nie
        wieder.

        Gewichtet wird deshalb über die Workflows (``umbau/workflows.py``):
        Eine Klasse, die auf einem der ermittelten Arbeitswege liegt,
        läuft im Betrieb; eine, die auf keinem liegt, ist Randbereich.

            178 auf mindestens einem Weg   <- die Arbeitsliste
            270 auf keinem                 <- nur gezählt

        Die Zahl der Wege ist zugleich die Sortierung: ``CorruptFileCounter``
        liegt auf 23 Wegen und hat keinen Test — das ist ein anderer Befund
        als eine Hilfsklasse, die einmal vorkommt.
        """
        try:
            from ..umbau.workflows import Workflowspeicher
            from ..umbau.wegenetz import Verzeichnis
        except ImportError:                            # pragma: no cover
            return []
        wurzel = self.wurzel()
        verzeichnis = Verzeichnis(wurzel).lesen()
        gewicht = {}
        liste, _alter = Workflowspeicher.holen(wurzel)
        for weg in liste.wege:
            for name in weg.klassen:
                gewicht[name] = gewicht.get(name, 0) + 1
        aus = []
        for name, bezug in sorted(verzeichnis.klassen.items()):
            if self._kommt_vor(erwaehnt, name):
                continue
            wege = gewicht.get(name, 0)
            if not wege:
                continue          # Randbereich — gezählt, nicht gelistet
            aus.append({
                "art": "Klasse ungeprüft",
                "stelle": name,
                "ziel": "%s:%d" % (bezug.modul, bezug.zeile),
                "gewicht": wege,
                "hinweis": "liegt auf %d Arbeitsweg%s, wird aber in keinem "
                           "Test erwähnt" % (wege, "en" if wege != 1 else ""),
            })
        return aus

    def _routen(self, erwaehnt):
        """Jede Route des Projekts gegen die Testtexte halten."""
        try:
            from django.urls import get_resolver
            wurzel = get_resolver()
        except Exception:                                       # noqa: BLE001
            return []
        aus, gesehen = [], set()

        def gehen(muster, praefix=""):
            for p in muster:
                if hasattr(p, "url_patterns"):
                    try:
                        gehen(p.url_patterns, praefix + str(p.pattern))
                    except Exception:                           # noqa: BLE001
                        pass
                    continue
                pfad = praefix + str(p.pattern)
                ziel = getattr(p.callback, "__name__", "?")
                modul = self._modul(p.callback)
                name = getattr(p, "name", None) or ""
                if any(f in modul or f in (name or "") for f in self.FREMD):
                    continue
                if modul.startswith(self.RAHMEN):
                    continue
                if not modul.split(".")[0] or "djangobase" in modul:
                    continue
                # Der Schluessel braucht den PFAD. Auf den Zielnamen allein
                # gestellt verschwanden dreizehn Seiten hinter einer: Djangos
                # ``View.as_view()`` gibt eine Funktion zurueck, die immer
                # ``view`` heisst — ein Projekt, das seine Seiten als Klassen
                # baut, sah damit fast keine Luecken mehr (17.08.2026).
                if (ziel, pfad) in gesehen:
                    continue
                gesehen.add((ziel, pfad))
                if self._kommt_vor(erwaehnt, ziel, name, pfad):
                    continue
                # Der Pfad kommt OHNE fuehrenden Schraegstrich („api/audio/…"),
                # deshalb zusaetzlich auf den Anfang pruefen: die erste Fassung
                # meldete jeden API-Endpunkt als „Seite" (17.08.2026).
                voll = "/" + pfad.lstrip("^/")
                api = ("/api/" in voll or voll.startswith("/api")
                       or ziel.endswith(("_api", "_status", "_json", "_stream")))
                aus.append({
                    "art": "Endpunkt ungeprüft" if api else "Seite ungeprüft",
                    "stelle": "/" + pfad.lstrip("^/"), "ziel": ziel,
                    "hinweis": ("Component-Test: Aufruf + erwartete Antwort"
                                if api else
                                "UI-Test: Status 200 und eine Zusicherung auf den "
                                "Inhalt")})
        try:
            gehen(wurzel.url_patterns)
        except Exception:                                       # noqa: BLE001
            pass
        return aus

    @staticmethod
    def _modul(callback):
        """Woher stammt diese Ansicht — vom Projekt oder vom Rahmen?

        Bei einer klassenbasierten Ansicht ist ``callback`` die Funktion, die
        ``View.as_view()`` gebaut hat; ihr ``__module__`` ist das der KLASSE.
        Fuer Djangos eigene ``RedirectView`` ist das ``django.views.generic``,
        fuer eine Projektklasse das Projektmodul — genau die Unterscheidung, die
        hier gebraucht wird. ``view_class`` wird zuerst gefragt, weil ein
        Dekorator (``xframe_options_sameorigin``) das ``__module__`` der
        Funktion auf sein eigenes Modul setzen kann.

        Bekannte Grenze: Ein Projekt, das ``TemplateView.as_view()`` OHNE eigene
        Unterklasse direkt in ``urls.py`` eintraegt, ist von Djangos eigener
        Ansicht nicht zu unterscheiden und faellt hier heraus. Eine eigene
        Klasse zu schreiben ist ohnehin die Hausregel (eine Klasse je Datei).
        """
        klasse = getattr(callback, "view_class", None)
        if klasse is not None:
            return getattr(klasse, "__module__", "") or ""
        return getattr(callback, "__module__", "") or ""

    def _menue(self, erwaehnt):
        """Die Menuepunkte aus DJANGOBASE - das ist die Sicht des Nutzers."""
        from django.conf import settings
        cfg = (getattr(settings, "DJANGOBASE", {}) or {})
        aus = []
        for eintrag in self._menue_eintraege(cfg.get("menu") or []):
            titel, ziel = eintrag
            if not ziel:
                continue
            marke = str(ziel).strip("/").split("/")[-1] or str(ziel)
            if self._kommt_vor(erwaehnt, marke, str(ziel), ""):
                continue
            aus.append({"art": "Menüpunkt ungeprüft", "stelle": titel,
                        "ziel": str(ziel),
                        "hinweis": "sichtbarer Einstieg ohne Test — ein Ausfall "
                                   "fällt sonst erst dem Nutzer auf"})
        return aus

    @staticmethod
    def _menue_eintraege(menue):
        """(Titel, Ziel) aus der Menuestruktur - beliebig tief verschachtelt."""
        aus = []
        for e in menue or []:
            if not isinstance(e, dict):
                continue
            ziel = e.get("url") or e.get("href") or e.get("pfad") or ""
            titel = e.get("titel") or e.get("name") or e.get("label") or str(ziel)
            if ziel:
                aus.append((titel, ziel))
            for schluessel in ("kinder", "children", "unter", "items", "eintraege"):
                aus.extend(Testdeckung._menue_eintraege(e.get(schluessel) or []))
        return aus

    @staticmethod
    def _kommt_vor(text, *marken):
        """Wird die Marke irgendwo in den Testtexten erwaehnt?

        Die Wortgrenze wird nur dort gesetzt, wo sie ueberhaupt greifen kann.
        ``\\b`` hinter einem Pfad, der auf ``/`` endet, verlangt ein Wortzeichen
        DANACH — in ``self.client.get("/einstellungen/tags-und-workflows/")``
        folgt ein Anfuehrungszeichen, der Treffer fiel also immer durch. Drei
        Seiten galten deshalb als ungeprueft, obwohl ein Test sie woertlich
        aufruft (17.08.2026). Fehlalarme dieser Sorte verdecken die echten
        Luecken.

        NACHGESCHLAGEN STATT DURCHSUCHT (27.08.2026)
        ============================================
        Ein einfacher Bezeichner wird ueber eine EINMAL gebaute Wortmenge
        nachgeschlagen statt ueber einen Ausdruck ueber 1,58 Mio. Zeichen.
        Nur was keine Wortmenge treffen kann — ein Pfad mit Schraegstrich —
        geht weiter durch den regulaeren Ausdruck.

        Gemessen davor: ``_routen`` 16,9 s und ``_klassen`` 15,3 s,
        zusammen 32 s fuer ein Werkzeug, das man oft drueckt. Die Wortmenge
        kostet einmal 0,2 s und danach nichts mehr."""
        woerter = Testdeckung._woerter(text)
        for m in marken:
            m = (m or "").strip()
            if len(m) < 4:
                continue
            if m.isidentifier():
                if m in woerter:
                    return True
                continue
            vorn = r"\b" if m[:1].isalnum() or m[:1] == "_" else ""
            hinten = r"\b" if m[-1:].isalnum() or m[-1:] == "_" else ""
            if re.search(vorn + re.escape(m) + hinten, text):
                return True
        return False

    #: Die Wortmenge EINES Textes, gemerkt am Text selbst.
    _wortcache = {}

    @classmethod
    def _woerter(cls, text):
        u"""Alle Bezeichner des Textes als Menge — einmal je Text.

        Gemerkt wird an der Länge plus einem Ausschnitt statt am ganzen
        Text: Ein 1,58-MB-String als dict-Schlüssel wird bei jedem Zugriff
        neu gehasht, und genau das sollte hier ja wegfallen.
        """
        schluessel = (len(text), text[:80], text[-80:])
        menge = cls._wortcache.get(schluessel)
        if menge is None:
            menge = set(re.findall(r"[A-Za-z_][A-Za-z0-9_]*", text))
            cls._wortcache = {schluessel: menge}
        return menge
