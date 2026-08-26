# -*- coding: utf-8 -*-
u"""Kommt ein geänderter Fix beim Nutzer an — oder liefert der Browser die alte Datei?

DER AUFTRAG (Edgar, 21.08.2026): „mach alle"
============================================
Zwei der vorgeschlagenen Prüfungen, beide zur selben Fehlerklasse:

    * Cache-Busting greift (``?v=`` an eigener Statik)
    * ein Modul, EINE URL

DIE FEHLERKLASSE
================
Aus ``~/.claude/rules/frontend-cache.md``, nach Vorfällen in drei Projekten:
Der Fix steht auf Platte, kommt aber nie im Browser an. Das kostet jedes Mal
Stunden, weil man den Fehler im Code sucht statt im Cache — und weil die Seite
dabei völlig normal aussieht.

Zwei Ausprägungen:

1. **Ohne ``?v=``** liefert der Browser die gemerkte Fassung. Ein Projekt, das
   seine Statik ohne Versionskennung einbindet, hat das Problem dauerhaft.
2. **Zwei URLs für dasselbe Modul.** Wird eine Datei einmal als
   ``modul.js?v=123`` geladen und woanders als ``modul.js`` importiert, sind das
   für den Browser ZWEI Module mit getrenntem Zustand. Am 21.08.2026 hat genau
   das jeden Klick doppelt aufgezeichnet: zwei Aufzeichner mit eigenen Puffern,
   neun Schritte doppelt in der Aufnahme, identische Zeitstempel.

WAS AUSGENOMMEN IST
===================
Fremde Statik (CDN, ``https://``) braucht keine eigene Kennung. Bilder und
Schriften ebenfalls nicht — sie ändern sich nicht mit dem Code. Geprüft wird,
was Verhalten trägt: ``.js`` und ``.css`` aus dem eigenen Projekt.
"""
import re

from django.test import SimpleTestCase

from djangobase.tests.konform.quellen import TABU, dateien, text_von  # noqa: F401

#: <script src=…> / <link href=…> auf eigene Statik.
#:
#: Das Anführungszeichen wird zurückverwiesen (``(?P=q)``) statt „alles außer
#: Anführungszeichen“ zu nehmen. Grund (21.08.2026): In
#: ``src="{% static 'app/x.js' %}?v=3"`` steht ein einfaches Anführungszeichen
#: MITTEN im doppelt gequoteten Wert. Die erste Fassung brach dort ab, fand
#: „{% static “ und verwarf es als „keine .js-Datei“ — im ``assistant`` waren
#: damit sämtliche Einbindungen unsichtbar, und der Prüfer meldete brav null
#: Verstöße.
_EINBINDUNG_RE = re.compile(
    r"""<(?:script|link)\b[^>]*?(?:src|href)\s*=\s*(?P<q>["'])(?P<adr>[^\n]*?)(?P=q)""",
    re.IGNORECASE)


#: ``{% comment %}…{% endcomment %}`` und ``{# … #}``.
_KOMMENTAR_RE = re.compile(
    r"\{%\s*comment\s*%\}.*?\{%\s*endcomment\s*%\}|\{#.*?#\}",
    re.DOTALL)


def ohne_kommentare(text):
    u"""Vorlagentext ohne Django-Kommentare.

    WARUM DER PRUEFER DAS BRAUCHT (26.08.2026)
    ==========================================
    Er meldete neun Einbindungen ohne Kennung. Sechs waren echt — drei
    standen in einem ``{% comment %}``-Block, der genau diesen Fehler
    ERKLAERT::

        {% comment %}
            <link href="{% static 'app/css/theme.css' %}" rel="stylesheet">   ohne ?v=
        {% endcomment %}

    Das ist Dokumentation, kein Mangel. Ein Pruefer, der die eigene
    Erklaerung anmahnt, wird nicht ernst genommen — und dann uebersieht
    man auch die sechs echten daneben.

    Die Laenge bleibt erhalten, damit Zeilennummern stimmen: Ersetzt wird
    durch Leerzeichen und Zeilenumbrueche, nicht geloescht.
    """
    def leeren(treffer):
        return re.sub(r"[^\n]", " ", treffer.group(0))
    return _KOMMENTAR_RE.sub(leeren, text)


class _Einbindung(object):
    u"""``findall``/``search`` wie ein Muster — liefert aber nur die Adresse."""

    @staticmethod
    def findall(text):
        return [m.group("adr")
                for m in _EINBINDUNG_RE.finditer(ohne_kommentare(text))]

    @staticmethod
    def search(text):
        return _EINBINDUNG_RE.search(ohne_kommentare(text))


_EINBINDUNG = _Einbindung()

#: Importe innerhalb von JS-Modulen.
_IMPORT = re.compile(
    r"""(?:from|import)\s*\(?\s*["'](/static/[^"']+\.js[^"']*)["']""")


def _dateien(muster):
    u"""Alle Projektdateien eines Musters (``"*.html"``) — ohne Fremdordner.

    Die Auswahl trifft ``quellen.dateien``: Was dort ausgenommen ist (Umgebungen,
    Medien, ``DJANGOBASE_KONFORM_AUS``), sieht KEINE Konformitätsprüfung."""
    return dateien(muster.split(".")[-1])


#: ``{% static 'app/x.js' %}`` — in Django-Vorlagen die übliche Schreibweise.
_STATIC_TAG = re.compile(r"""{%\s*static\s+["']([^"']+)["']""")


def _datei_der_adresse(adresse):
    u"""Die Datei, auf die eine Einbindung zeigt.

    BLINDER FLECK, GESCHLOSSEN AM 21.08.2026: Die erste Fassung sah nur
    Adressen, die selbst auf ``.js``/``.css`` enden. In Django-Vorlagen steht
    dort aber fast immer ``{% static 'app/x.js' %}`` — und die endet auf ``%}``.
    Die Prüfung war für den Normalfall damit blind; grün war sie nur, weil in
    einem Datenordner altmodische Einbindungen lagen."""
    m = _STATIC_TAG.search(adresse)
    if m:
        return m.group(1)
    return adresse.split("?")[0].split("#")[0]


def _eigene_statik(adresse):
    u"""Zeigt die Adresse auf eine eigene .js/.css-Datei?"""
    if adresse.startswith(("http://", "https://", "//", "data:")):
        return False
    return _datei_der_adresse(adresse).endswith((".js", ".css"))


class CacheBustingTest(SimpleTestCase):
    u"""Jede eigene Statik trägt eine Versionskennung."""

    def sammeln(self):
        u"""[(datei, adresse)] aller Einbindungen ohne ``?v=``."""
        ohne = []
        for pfad in _dateien("*.html"):
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for adresse in _EINBINDUNG.findall(text):
                if not _eigene_statik(adresse):
                    continue
                # `{% static %}` mit angehängter Query zählt - die Kennung steht
                # dann hinter dem Tag, nicht in der Adresse.
                if "?" in adresse or "|add:" in adresse:
                    continue
                ohne.append((pfad, adresse))
        return ohne

    def test_eigene_statik_traegt_eine_kennung(self):
        ohne = self.sammeln()
        if not ohne:
            return
        beispiele = "\n".join("    %s: %s" % (p.name, a[:70]) for p, a in ohne[:10])
        self.fail(
            u"%d Einbindungen ohne ?v=-Kennung:\n%s%s\n\n"
            u"Der Browser liefert diese Dateien aus seinem Cache — ein Fix "
            u"kommt beim Nutzer erst nach hartem Neuladen an, und die Seite "
            u"sieht dabei völlig normal aus.\n"
            u"    <script src=\"{%% static 'app/x.js' %%}?v={{ djangobase.statik_v }}\">"
            % (len(ohne), beispiele, "\n    …" if len(ohne) > 10 else ""))

    def test_es_wurde_wirklich_gesucht(self):
        u"""Findet der Sucher gar keine Einbindungen, ist „0 Verstöße" wertlos."""
        gesamt = 0
        for pfad in _dateien("*.html"):
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            gesamt += sum(1 for a in _EINBINDUNG.findall(text) if _eigene_statik(a))
        self.assertTrue(gesamt,
                        u"Keine einzige eigene Statik-Einbindung gefunden — das "
                        u"Suchmuster passt nicht mehr.")


class KommentareZaehlenNichtTest(SimpleTestCase):
    u"""Was in einem Kommentar steht, ist Dokumentation, kein Mangel.

    Am 26.08.2026 meldete `CacheBustingTest` neun Einbindungen ohne
    Kennung. Drei standen in ``{% comment %}``-Bloecken, die genau diesen
    Fehler ERKLAEREN — in `login.html` sogar mit dem Vermerk „ohne ?v=".
    """

    VORLAGE = (
        "{% comment %}\n"
        "    <link href=\"{% static 'app/css/alt.css' %}\" rel=\"stylesheet\">\n"
        "{% endcomment %}\n"
        "<link href=\"{% static 'app/css/echt.css' %}\" rel=\"stylesheet\">\n")

    def test_einbindung_im_kommentar_wird_nicht_gefunden(self):
        adressen = _EINBINDUNG.findall(self.VORLAGE)
        self.assertEqual(len(adressen), 1, adressen)
        self.assertIn('echt.css', adressen[0])

    def test_einzeiliger_kommentar_zaehlt_auch_nicht(self):
        adressen = _EINBINDUNG.findall(
            "{# <link href=\"{% static 'app/css/alt.css' %}\"> #}\n")
        self.assertEqual(adressen, [])

    def test_die_zeilennummern_bleiben_stehen(self):
        u"""Geleert, nicht geloescht — sonst zeigt jede Meldung daneben."""
        raus = ohne_kommentare(self.VORLAGE)
        self.assertEqual(raus.count('\n'), self.VORLAGE.count('\n'))
        self.assertEqual(len(raus), len(self.VORLAGE))

    def test_ohne_kommentar_bleibt_alles_stehen(self):
        text = "<link href=\"{% static 'a.css' %}\">"
        self.assertEqual(ohne_kommentare(text), text)


class ModulUrlTest(SimpleTestCase):
    u"""Ein Modul, eine URL."""

    def sammeln(self):
        u"""{modulname: {adressen}} über Vorlagen UND JS-Dateien."""
        wo = {}
        for muster in ("*.html", "*.js"):
            for pfad in _dateien(muster):
                try:
                    text = pfad.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                adressen = _IMPORT.findall(text)
                if muster == "*.html":
                    adressen += [a for a in _EINBINDUNG.findall(text)
                                 if a.startswith("/static/") and ".js" in a]
                for a in adressen:
                    name = a.split("?")[0].split("/")[-1]
                    wo.setdefault(name, set()).add("?" in a)
        return wo

    def test_kein_modul_mit_und_ohne_kennung(self):
        u"""Beides gemischt = zwei Modulinstanzen mit getrenntem Zustand.

        Belegt am 21.08.2026: ``aufzeichner.js`` wurde in der Shell mit ``?v=``
        geladen und im Knopf-Modul ohne — es lief zweimal, und jeder Klick stand
        doppelt in der Aufnahme."""
        gemischt = sorted(name for name, arten in self.sammeln().items()
                          if len(arten) > 1)
        self.assertFalse(gemischt,
                         u"Diese Module werden MIT und OHNE ?v= geladen: %s\n\n"
                         u"Für den Browser sind das je zwei Module mit eigenem "
                         u"Zustand. Im Importeur die Kennung übernehmen:\n"
                         u"    await import('/static/…/x.js' + "
                         u"new URL(import.meta.url).search)"
                         % ", ".join(gemischt[:10]))


class KennungIstDynamischTest(SimpleTestCase):
    u"""Eine feste Kennung ist Cache-Busting, das nie bustet.

    GEFUNDEN BEIM ERSTEN LAUF (21.08.2026): In ShortLongX importieren mehrere
    Module ``tabellen_sortierung.js?v=2`` — die Zwei steht seit dem Tag fest, an
    dem jemand sie hingeschrieben hat. Sie sieht aus wie eine Versionskennung,
    tut aber nichts: Ändert sich die Datei, liefert der Browser weiter seine
    gemerkte Fassung, weil die URL gleich blieb.

    Das ist die tückischere Hälfte der Fehlerklasse — ohne ``?v=`` sucht man
    wenigstens noch; mit einer festen Zahl hält man das Thema für erledigt.
    """

    #: ``?v=`` gefolgt von einer reinen Zahl, ohne Vorlagen-Ausdruck dahinter.
    FEST = re.compile(r"""["'][^"']*\.js\?v=\d+(?:\.\d+)?["']""")

    def test_keine_feste_versionsnummer_in_js_importen(self):
        treffer = []
        for pfad in _dateien("*.js"):
            try:
                text = pfad.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for nr, zeile in enumerate(text.splitlines(), 1):
                if "import" not in zeile:
                    continue
                if self.FEST.search(zeile):
                    treffer.append((pfad.name, nr, zeile.strip()))
        if treffer:
            zeilen = "\n".join("    %s:%d  %s" % (d, n, z[:78])
                               for d, n, z in treffer[:10])
            self.fail(
                u"%d Import(e) mit fest verdrahteter Kennung:\n%s%s\n\n"
                u"Die Zahl ändert sich nie, also ändert sich die URL nie, also "
                u"liefert der Browser weiter seine gemerkte Fassung. Die Kennung "
                u"des eigenen Moduls übernehmen:\n"
                u"    await import('/static/…/x.js' + new URL(import.meta.url).search)"
                % (len(treffer), zeilen, "\n    …" if len(treffer) > 10 else ""))

    def test_muster_trifft_nur_feste_zahlen(self):
        u"""Gegenprobe: Ein dynamischer Anhänger darf NICHT gemeldet werden."""
        self.assertTrue(self.FEST.search("import x from '/static/a/x.js?v=2';"))
        self.assertIsNone(self.FEST.search(
            "await import('/static/a/x.js' + new URL(import.meta.url).search)"))
        self.assertIsNone(self.FEST.search("'/static/a/x.js?v=' + stand"))


class GegenprobeTest(SimpleTestCase):
    u"""Erkennen die Muster, was sie erkennen sollen?"""

    def test_einbindung_wird_gefunden(self):
        html = '<script src="{% static \'app/x.js\' %}?v=3"></script>'
        self.assertTrue(_EINBINDUNG.findall(html))

    def test_fremde_statik_ist_ausgenommen(self):
        self.assertFalse(_eigene_statik("https://cdn.example/bootstrap.min.css"))
        self.assertFalse(_eigene_statik("/static/app/logo.png"))
        self.assertTrue(_eigene_statik("/static/app/x.js"))

    def test_static_tag_wird_erkannt(self):
        u"""Der Normalfall in Django-Vorlagen. Ohne ihn prüfte die Regel nur
        die Ausnahme (siehe ``_datei_der_adresse``)."""
        self.assertTrue(_eigene_statik("{% static 'app/x.js' %}"))
        self.assertTrue(_eigene_statik("{% static \"app/x.css\" %}?v=3"))
        self.assertFalse(_eigene_statik("{% static 'app/logo.png' %}"))

    def test_import_wird_gefunden(self):
        for zeile in ("import { X } from '/static/app/x.js';",
                      "await import('/static/app/x.js' + suche)"):
            with self.subTest(zeile=zeile):
                self.assertTrue(_IMPORT.findall(zeile), zeile)

    def test_gemischte_ladeart_faellt_auf(self):
        u"""Der Kern von test_kein_modul_mit_und_ohne_kennung an einer Probe."""
        arten = {True, False}
        self.assertTrue(len(arten) > 1)
