"""Vorlagenkontext — tote Kontextvariablen, fehlende Namen, verwaiste Vorlagen."""

import ast
import re
from pathlib import Path

from django.conf import settings
from django.template.base import FilterExpression, Variable
from django.template.loader import get_template

from .befund import Befund, Befundsatz, BefundWerkzeug

#: Namen, die aus Kontextprozessoren oder der Shell kommen, nicht aus der Ansicht.
_PROZESSOR_CACHE = None

VON_AUSSEN = {
    'request', 'user', 'perms', 'messages', 'csrf_token', 'settings', 'DEBUG',
    'True', 'False', 'None', 'block', 'forloop', 'djangobase', 'aktiv',
    'LANGUAGE_CODE', 'LANGUAGE_BIDI', 'TIME_ZONE', 'aktives_theme',
    'sidebar_initial_width', 'JS_VERSION', 'DJANGOBASE',
}

def _prozessor_namen():
    """Namen, die JEDE Vorlage bekommt, weil ein Kontextprozessor sie liefert.

    Ohne diese Abfrage meldete das Werkzeug am 18.08.2026 in CamTrack 260
    „FEHLEND" — davon 255 Namen, die acht Kontextprozessoren an jede Vorlage
    liefern (``STATIC_V``, ``active_section``, ``record_service_running`` …).
    Ein Prüfer, dem man zu 98 % nicht glauben kann, wird nicht gelesen.

    Gefragt werden die Prozessoren selbst, nicht eine gepflegte Liste: Was ein
    Projekt global liefert, weiß nur seine Konfiguration. Jeder wird einzeln
    gekapselt — einer, der ohne echte Anfrage nicht kann, darf die Prüfung
    nicht mitnehmen.
    """
    global _PROZESSOR_CACHE
    if _PROZESSOR_CACHE is not None:
        return _PROZESSOR_CACHE

    from django.test import RequestFactory
    from django.utils.module_loading import import_string

    namen = set()
    anfrage = RequestFactory().get("/")
    # EIN ECHTES User-Objekt, nicht None (25.08.2026). Fast jeder
    # Prozessor beginnt mit `if request.user.is_authenticated` - bei
    # `None` wirft das einen AttributeError, den das `except` darunter
    # still schluckt. Der Prozessor liefert dann KEINE Namen, und alles,
    # was er global bereitstellt, gilt anschliessend als "von der
    # Ansicht vergessen".
    #
    # Im Projekt assistant waren das achtzig Befunde der hoechsten
    # Stufe - `bank_firmen`, `sidebar_mail_accounts`, `steuer_firmen`
    # und Geschwister, allesamt aus einem Prozessor, der nie zu Wort kam.
    from django.contrib.auth.models import AnonymousUser

    anfrage.user = AnonymousUser()
    anfrage.session = {}
    for eintrag in settings.TEMPLATES:
        for pfad in (eintrag.get("OPTIONS") or {}).get("context_processors", []):
            for wer in (anfrage, _anfrage_angemeldet()):
                try:
                    namen |= set(import_string(pfad)(wer) or {})
                except Exception:  # noqa: BLE001 - siehe Docstring
                    continue
            # AUCH WENN DER AUFRUF LEER BLEIBT. Ein Prozessor, der fuer
            # einen nicht angemeldeten Nutzer nichts liefert, tut genau
            # das Richtige - seine Namen gibt es trotzdem, sobald jemand
            # angemeldet ist. Im Projekt assistant lieferten VIER
            # Seitenleisten-Prozessoren dem anonymen Nutzer ein leeres
            # Woerterbuch; ihre Namen (`bank_firmen`,
            # `sidebar_mail_accounts`, `steuer_firmen` …) galten danach
            # als "von der Ansicht vergessen" - achtzig Befunde der
            # hoechsten Stufe fuer nichts.
            namen |= _rueckgabeschluessel(pfad)
    _PROZESSOR_CACHE = namen
    return namen


def _anfrage_angemeldet():
    """Eine Anfrage, die als angemeldet gilt - ohne Datenbank.

    WARUM (25.08.2026, Projekt assistant)
    =====================================
    Seitenleisten-Prozessoren beginnen fast immer mit::

        if not request.user.is_authenticated:
            return {}

    Fuer einen anonymen Nutzer liefern sie also NICHTS - richtig so, nur
    sieht der Pruefer ihre Namen dadurch nie. Sechzehn Befunde der
    hoechsten Stufe entstanden allein aus `sidebar_mail_accounts`, das
    ein solcher Prozessor bereitstellt.

    Der Quelltext half hier nicht weiter: Die Funktion reicht bloss an
    eine Klasse durch (`return Seitenleistenkontext(request).kontext()`),
    die Schluessel stehen eine Ebene tiefer.

    Gefragt wird deshalb ein zweites Mal, mit einem Nutzer, der sich als
    angemeldet ausgibt. Was der Prozessor dann versucht - eine Abfrage,
    ein Zugriff auf ein Profil - scheitert vielleicht; das faengt der
    Aufrufer ab. Kommt er bis zum `return`, kennen wir seine Namen.
    """
    from django.test import RequestFactory

    from django.contrib.auth import get_user_model

    # EIN ECHTES, NICHT GESPEICHERTES User-Objekt. Eine eigene Klasse
    # mit `is_authenticated = True` reicht nicht: Sobald der Prozessor
    # danach filtert (`profil__owner=request.user`), verlangt Django ein
    # Model und wirft sonst
    # `TypeError: Field 'id' expected a number`.
    #
    # Nicht gespeichert und mit `pk=0`: Die Abfragen laufen ins Leere -
    # genau richtig. Gesucht sind die NAMEN, die der Prozessor setzt,
    # nicht ihre Werte.
    nutzer = get_user_model()(pk=0, username="pruefung")

    anfrage = RequestFactory().get("/")
    anfrage.user = nutzer
    anfrage.session = {}
    return anfrage


def _rueckgabeschluessel(pfad):
    """Die Schluessel, die diese Funktion laut Quelltext zurueckgibt.

    Gelesen wird der Syntaxbaum, nicht das Ergebnis: Ein Prozessor kann
    je nach Anfrage etwas anderes liefern, aber die MOEGLICHEN Namen
    stehen im Code. Erfasst wird ``return {...}`` mit festen
    Zeichenketten als Schluessel - alles andere waere geraten.
    """
    import ast
    import inspect

    try:
        from django.utils.module_loading import import_string as _holen

        funktion = _holen(pfad)
        quelle = inspect.getsource(funktion)
    except Exception:  # noqa: BLE001
        # stumm gewollt: Ohne Quelltext bleibt es beim Aufruf-Ergebnis.
        return set()

    quelle = quelle[quelle.index("def "):] if "def " in quelle else quelle
    try:
        baum = ast.parse(quelle)
    except SyntaxError:
        try:
            import textwrap

            baum = ast.parse(textwrap.dedent(quelle))
        except SyntaxError:
            return set()

    raus = set()
    for knoten in ast.walk(baum):
        if not isinstance(knoten, ast.Return) or knoten.value is None:
            continue
        for teil in ast.walk(knoten.value):
            if not isinstance(teil, ast.Dict):
                continue
            for schluessel in teil.keys:
                if (isinstance(schluessel, ast.Constant)
                        and isinstance(schluessel.value, str)):
                    raus.add(schluessel.value)
    return raus


#: Ueber diese Attribute fuehrt der Weg aus der Vorlage heraus: jeder Knoten
#: kennt seine Herkunft, die ihren Lader, der die Engine — und deren Cache
#: enthaelt ALLE bereits geladenen Vorlagen. Ohne die Sperre sammelt die
#: Pruefung die Variablennamen des halben Projekts ein.
NICHT_ABSTEIGEN = {
    'origin', 'engine', 'loader', 'loaders', 'template', 'template_loaders',
    'libraries', 'builtins', 'get_template_cache', 'context',
}


#: Knoten, unterhalb derer ein Name wahlfrei ist. `{% if %}` deckt auch
#: `{% elif %}`/`{% else %}` ab — Django baut daraus EINEN `IfNode`.
BEDINGTE_KNOTEN = frozenset({'IfNode', 'IfChangedNode', 'IfEqualNode'})

#: Filter, die einen Ersatzwert liefern. Wer sie schreibt, hat das
#: Fehlen des Namens eingeplant.
ERSATZFILTER = frozenset({'default', 'default_if_none'})


def _ist_name(text):
    """Zahlen und Zeichenketten aussortieren: `{{ 1 }}` ist keine Variable."""
    return bool(re.match(r'^[A-Za-z_]\w*$', text or ''))


#: Einstellungsschluessel, die den Namen einer Vorlage tragen. Wird eine
#: Vorlage ueber eine VARIABLE eingebunden, steht ihr Name nicht im
#: Quelltext - er kommt aus den Einstellungen.
VORLAGE_AUS_EINSTELLUNG = ('sidebar_template', 'nav_template',
                           'shell_template', 'kopf_template')

_INCLUDE_VARIABEL = re.compile(r"{%\s*include\s+([^\"'%\s][^%]*?)%}")
_DEFAULT_WERT = re.compile(r'default:"([^"]+)"')


def _ueber_variable(quelle):
    """Vorlagen, die per ``{% include <variable> %}`` eingebunden werden.

    DER FALL (25.08.2026, Projekt assistant)
    ========================================
    ``_shell.html`` bindet die Seitenleiste so ein::

        {% include djangobase.sidebar_template|default:"djangobase/_sidebar.html" %}

    Im Quelltext steht damit KEIN Vorlagenname, den das Muster daneben
    finden könnte. Die Kette endete an dieser Stelle - und jede
    Variable, die nur in der projekteigenen Seitenleiste gelesen wird,
    galt als "wird übergeben, aber von keiner beteiligten Vorlage
    gelesen".

    Gemessen: 73 Befunde, darunter reihenweise `active_page`,
    `active_subpage` und `firmen` - obwohl `search/_sidebar.html` allein
    `active_page` ZWEIUNDVIERZIGMAL liest.

    Aufgeloest wird beides: der ``default:"…"`` aus dem Quelltext UND der
    Wert, der in ``DJANGOBASE`` wirklich eingetragen ist.
    """
    from django.conf import settings

    gefunden = set()
    cfg = getattr(settings, 'DJANGOBASE', {}) or {}
    for treffer in _INCLUDE_VARIABEL.finditer(quelle):
        stueck = treffer.group(1)
        for wert in _DEFAULT_WERT.finditer(stueck):
            gefunden.add(wert.group(1))
        for schluessel in VORLAGE_AUS_EINSTELLUNG:
            if schluessel in stueck and cfg.get(schluessel):
                gefunden.add(str(cfg[schluessel]))
    return gefunden


class Vorlagensicht:
    """Alle Variablennamen einer Vorlage samt eingebundener Bausteine."""

    def __init__(self, name):
        self.name = name
        self.gelesen = set()
        #: Was ausserhalb jedes `{% if %}` gelesen wird. Alles andere ist
        #: absichtlich wahlfrei — siehe `feste_namen`.
        self.fest = set()
        self.lokal = set()
        self.eingebunden = set()
        self._sammeln(get_template(name).template)

    def _sammeln(self, vorlage):
        quelle = vorlage.source
        for treffer in re.finditer(r'{%\s*(?:extends|include)\s+"([^"]+)"', quelle):
            self.eingebunden.add(treffer.group(1))
        for name in _ueber_variable(quelle):
            self.eingebunden.add(name)
        for muster in (r'{%\s*with\s+([^%]+)%}',
                       r'{%\s*include\s+"[^"]+"\s+with\s+([^%]+)%}'):
            for treffer in re.finditer(muster, quelle):
                for stueck in treffer.group(1).split():
                    if '=' in stueck:
                        self.lokal.add(stueck.split('=')[0].strip())
        for treffer in re.finditer(r'{%\s*for\s+([\w\s,]+?)\s+in\s', quelle):
            for teil in treffer.group(1).split(','):
                self.lokal.add(teil.strip())
        for treffer in re.finditer(r'\sas\s+(\w+)\s*%}', quelle):
            self.lokal.add(treffer.group(1))
        self._wert(vorlage.nodelist)

    def _wert(self, wert, gesehen=None, tiefe=0, bedingt=False):
        """Alles absuchen, was Variablen enthalten könnte.

        Bewusst generisch statt nach Knotentypen: Die BEDINGUNGEN von
        `{% if %}` hängen als TemplateLiteral in Operator-Objekten
        (`.first`/`.second`) und sind weder Node noch FilterExpression. Wer nur
        die bekannten Typen abklappert, meldet dort gelesene Variablen faelsch-
        licherweise als tot.
        """
        if tiefe > 40:
            return
        gesehen = gesehen if gesehen is not None else set()
        if id(wert) in gesehen:
            return
        gesehen.add(id(wert))
        # Ab hier steht alles in einem `{% if %}`: sowohl die Bedingung
        # selbst als auch der Rumpf. Beides ist ein Name, dessen Fehlen die
        # Vorlage einkalkuliert.
        bedingt = bedingt or wert.__class__.__name__ in BEDINGTE_KNOTEN
        if isinstance(wert, FilterExpression):
            # `{{ x|default:'—' }}` sagt ausdruecklich: der Name darf fehlen.
            # Das ist die Django-Art, einen Kontext-Eintrag wahlfrei zu
            # machen — ohne diese Regel meldet die Pruefung `main_probe` in
            # `cameras/form.html` als fehlend, obwohl direkt daneben steht,
            # was bei Abwesenheit erscheinen soll.
            if any(f.__name__ in ERSATZFILTER for f, _a in wert.filters):
                bedingt = True
            if isinstance(wert.var, Variable):
                self._merken(str(wert.var).split('.')[0].split('|')[0], bedingt)
            else:
                self._wert(wert.var, gesehen, tiefe + 1, bedingt)
            for _filter, argumente in wert.filters:
                for _, argument in argumente:
                    self._wert(argument, gesehen, tiefe + 1, bedingt)
        elif isinstance(wert, Variable):
            self._merken(str(wert).split('.')[0], bedingt)
        elif isinstance(wert, (str, bytes, int, float, bool, type(None))):
            return
        elif isinstance(wert, dict):
            for eintrag in wert.values():
                self._wert(eintrag, gesehen, tiefe + 1, bedingt)
        elif isinstance(wert, (list, tuple, set, frozenset)):
            for eintrag in wert:
                self._wert(eintrag, gesehen, tiefe + 1, bedingt)
        elif hasattr(wert, '__dict__'):
            for name, eintrag in vars(wert).items():
                if name not in NICHT_ABSTEIGEN:
                    self._wert(eintrag, gesehen, tiefe + 1, bedingt)

    def _merken(self, name, bedingt):
        self.gelesen.add(name)
        if not bedingt:
            self.fest.add(name)

    def feste_namen(self, tiefe=0):
        u"""Nur was außerhalb jedes `{% if %}` gelesen wird.

        DIE SIEBEN FEHLALARME (CamTrack, 23.08.2026)
        ============================================
        Nach dem Aufraeumen der toten Namen blieben sieben FEHLEND-Befunde
        stehen — und **alle sieben waren falsch**::

            {% if is_edit %}...{{ camera.name }}...{% endif %}
            {% if is_live %}<video src="{{ live_media_url }}">{% endif %}
            {% if tab.key == zb_aktiv or forloop.first and not zb_aktiv %}

        Die Vorlage rechnet in allen drei Fällen damit, dass der Name
        fehlt: `is_edit` ist auf dem Anlegen-Weg falsch, `is_live` auf dem
        Abspiel-Weg, und `zb_aktiv` wird per `not zb_aktiv` selbst
        abgefragt.

        Ein Prüfer, der zu hundert Prozent falsch meldet, wird abgestellt.
        Gemeldet wird deshalb nur noch, was die Vorlage UNBEDINGT liest.
        """
        alle = set(self.fest)
        if tiefe > 4:
            return alle
        for name in self.eingebunden:
            try:
                alle |= Vorlagensicht(name).feste_namen(tiefe + 1)
            except Exception:  # noqa: BLE001
                pass
        return alle

    def namen(self, tiefe=0):
        """Gelesene Namen inklusive der eingebundenen Vorlagen."""
        alle = set(self.gelesen)
        if tiefe > 4:
            return alle
        for name in self.eingebunden:
            try:
                alle |= Vorlagensicht(name).namen(tiefe + 1)
            except Exception:  # noqa: BLE001 — fehlende Vorlage darf nicht stoppen
                pass
        return alle

    def alle_lokal(self, tiefe=0):
        alle = set(self.lokal)
        if tiefe > 4:
            return alle
        for name in self.eingebunden:
            try:
                alle |= Vorlagensicht(name).alle_lokal(tiefe + 1)
            except Exception:  # noqa: BLE001
                pass
        return alle


class Renderstelle:
    """Ein render()-Aufruf: Vorlage, übergebene Schlüssel, Ort im Quelltext."""

    __slots__ = ('datei', 'zeile', 'vorlage', 'schluessel', 'vollstaendig')

    def __init__(self, datei, zeile, vorlage, schluessel, vollstaendig):
        self.datei = datei
        self.zeile = zeile
        self.vorlage = vorlage
        self.schluessel = schluessel
        #: False, wenn der Kontext nicht nur aus Literalen besteht (`**extra`).
        #: Dann taugt die Gegenrichtung (FEHLEND) nicht.
        self.vollstaendig = vollstaendig

    @property
    def ort(self):
        return '%s:%d' % (self.datei, self.zeile)


class Vorlagenkontext(BefundWerkzeug):

    slug = 'vorlagen-kontext'
    titel = 'Vorlagen-Kontext'
    zweck = ('Vergleicht jeden render()-Aufruf mit seiner Vorlage: übergebene, '
             'aber nie gelesene Schlüssel (TOT), gelesene, aber nie gelieferte '
             'Namen (FEHLEND) und Vorlagen, die niemand rendert (VERWAIST).')
    abhilfe = ('Nach jedem groesseren Umbau und vor einem Review — findet stille '
            'Fehler, die kein Test bemerkt, weil Django fehlende Variablen '
            'kommentarlos als Leerstring rendert.')
    befund = ('Im Ursprungsprojekt: eine if-Bedingung, die seit vier Monaten auf '
             'einen nie gelieferten Namen zeigte (das Datei-Feld war dadurch '
             'immer Pflicht), zwei tote Kontextschluessel samt einem COUNT(*) '
             'je Aufruf und zwei unerreichbare Vorlagen.')
    dauer = 'wenige Sekunden'

    #: Kein Anlassfall - und das ist in Ordnung:
    ohne_anlassfall_weil = ("braucht den Django-Template-Loader - "
                            "in einem Wegwerf-Verzeichnis gibt es keine Vorlagen")

    def pruefen(self, **_argumente):
        stellen = self._renderstellen()
        sicht, befunde = {}, []
        einbinde = self._einbindeparameter()
        for stelle in stellen:
            if stelle.vorlage not in sicht:
                try:
                    sicht[stelle.vorlage] = Vorlagensicht(stelle.vorlage)
                except Exception as fehler:  # noqa: BLE001
                    befunde.append(Befund(
                        stelle.ort, 'Vorlage %s nicht ladbar' % stelle.vorlage,
                        str(fehler), Befund.WARNUNG))
                    continue
            ansicht = sicht[stelle.vorlage]
            gelesen = ansicht.namen()
            ungenutzt = sorted(s for s in stelle.schluessel if s not in gelesen)
            for name in ungenutzt:
                befunde.append(Befund(
                    stelle.ort, 'TOT: %s (%s)' % (name, stelle.vorlage),
                    'wird übergeben, aber von keiner beteiligten Vorlage gelesen',
                    Befund.WARNUNG))
            if stelle.vollstaendig:
                fehlend = sorted(n for n in ansicht.feste_namen()
                                 - stelle.schluessel
                                 - ansicht.alle_lokal() - VON_AUSSEN - einbinde
                                 - _prozessor_namen()
                                 if _ist_name(n))
                for name in fehlend:
                    befunde.append(Befund(
                        stelle.ort, 'FEHLEND: %s (%s)' % (name, stelle.vorlage),
                        'die Vorlage liest den Namen, niemand liefert ihn — '
                        'Django rendert dafür stillschweigend nichts',
                        Befund.FEHLER))
        befunde.extend(self._verwaiste(stellen))
        kopf = ['%d render()-Stellen, %d Vorlagen geprueft'
                % (len(stellen), len(sicht))]
        return Befundsatz(self.titel, kopf, befunde)

    # ------------------------------------------------------------------ intern

    def _renderstellen(self):
        gefunden = []
        for datei in self.projektdateien('.py'):
            try:
                baum = ast.parse(datei.read_text(encoding='utf-8', errors='replace'))
            except (SyntaxError, OSError):
                continue
            for knoten in ast.walk(baum):
                stelle = self._aus_aufruf(knoten, datei)
                if stelle is not None:
                    gefunden.append(stelle)
        return gefunden

    def _aus_aufruf(self, knoten, datei):
        if not (isinstance(knoten, ast.Call) and isinstance(knoten.func, ast.Name)
                and knoten.func.id == 'render'):
            return None
        if len(knoten.args) < 2 or not isinstance(knoten.args[1], ast.Constant):
            return None
        schluessel, vollstaendig = set(), True
        wortliste = knoten.args[2] if len(knoten.args) > 2 else None
        for stichwort in knoten.keywords:
            if stichwort.arg == 'context':
                wortliste = stichwort.value
        if isinstance(wortliste, ast.Dict):
            for taste in wortliste.keys:
                if isinstance(taste, ast.Constant):
                    schluessel.add(taste.value)
                else:
                    vollstaendig = False
        elif wortliste is not None:
            vollstaendig = False
        return Renderstelle(self.kurz(datei), knoten.lineno,
                            knoten.args[1].value, schluessel, vollstaendig)

    def _einbindeparameter(self):
        """Namen, die irgendwo per `{% include … with name=… %}` gesetzt werden.

        Ein Baustein liest solche Namen, bekommt sie aber von der EINBINDENDEN
        Vorlage — aus Sicht des render()-Aufrufs saehen sie sonst wie fehlende
        Kontextvariablen aus.
        """
        namen = set()
        for ordner in self._alle_vorlagenordner():
            for datei in Path(ordner).rglob('*.html'):
                quelle = datei.read_text(encoding='utf-8', errors='replace')
                for treffer in re.finditer(r'{%\s*(?:include|with)\s[^%]*?%}', quelle):
                    for stueck in treffer.group(0).split():
                        kopf = stueck.split('=')[0].strip()
                        if '=' in stueck and _ist_name(kopf):
                            namen.add(kopf)
        return namen

    @staticmethod
    def _vorlagenordner():
        """Alle DIRS aus der Template-Konfiguration, die es wirklich gibt."""
        ordner = []
        for eintrag in getattr(settings, 'TEMPLATES', []) or []:
            for verzeichnis in eintrag.get('DIRS', []) or []:
                if Path(str(verzeichnis)).is_dir():
                    ordner.append(str(verzeichnis))
        return ordner

    def _alle_vorlagenordner(self):
        return self._vorlagenordner() + self._app_vorlagenordner()

    @staticmethod
    def _app_vorlagenordner():
        u"""Auch `<app>/templates/` — sonst sieht die Prüfung nichts.

        CamTrack trägt in `DIRS` nichts ein und legt alle 57 Vorlagen
        unter `app/templates/` ab. Alle drei Stellen, die hier nach
        Vorlagen suchen, liefen deshalb über eine leere Liste: die Suche
        nach verwaisten Vorlagen meldete nie etwas, und die Namen aus
        `{% include … with … %}` blieben unbekannt.
        """
        from django.template.utils import get_app_template_dirs
        # Ohne den Filter kommen die Vorlagen der Fremd-Pakete mit:
        # `allauth` allein steuerte 60 „verwaiste" Vorlagen bei, die
        # seine eigenen Ansichten sehr wohl rendern.
        return [str(o) for o in get_app_template_dirs('templates')
                if 'site-packages' not in str(o)]

    def _verwaiste(self, stellen):
        """Vorlagen, die niemand rendert und niemand einbindet."""
        befunde = []
        erreichbar = {s.vorlage for s in stellen}
        namen = set()
        for ordner in self._alle_vorlagenordner():
            for datei in Path(ordner).rglob('*.html'):
                quelle = datei.read_text(encoding='utf-8', errors='replace')
                for treffer in re.finditer(
                        r'{%\s*(?:extends|include)\s+"([^"]+)"', quelle):
                    erreichbar.add(treffer.group(1))
        for datei in self.projektdateien('.py'):
            quelle = datei.read_text(encoding='utf-8', errors='replace')
            for treffer in re.finditer(r'["\']([\w/_.-]+\.html)["\']', quelle):
                erreichbar.add(treffer.group(1))
            # AUCH DER BLOSSE NAME (23.08.2026): Vorlagennamen werden oft
            # zusammengesetzt. In CamTrack steht
            # `HelpPage('help_workflow', 'workflow', …)`, und die Ansicht
            # baut daraus `app/help/workflow.html` — die vollstaendige
            # Zeichenkette gibt es im Quelltext nirgends. Ohne diese Zeile
            # meldete die Pruefung sieben Seiten als verwaist, die taeglich
            # aufgerufen werden.
            for treffer in re.finditer(r"""['"](\w[\w.-]*)['"]""", quelle):
                namen.add(treffer.group(1))
        for ordner in self._alle_vorlagenordner():
            for datei in Path(ordner).rglob('*.html'):
                titel = str(datei.relative_to(ordner)).replace('\\', '/')
                if not str(datei).startswith(str(self.wurzel())):
                    continue
                if titel in erreichbar or Path(titel).stem in namen:
                    continue
                if True:
                    befunde.append(Befund(
                        self.kurz(datei), 'VERWAIST (%d Byte)' % datei.stat().st_size,
                        'kein render(), kein include, kein extends verweist darauf',
                        Befund.HINWEIS))
        return befunde
