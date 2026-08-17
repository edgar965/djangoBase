# -*- coding: utf-8 -*-
u"""JsStumm - Rueckmeldungen, die im Browser lautlos verschwinden.

    Kriterium 16: Logging sauber - klare Ausnahmen im UI, kein Ereignis, das
    ohne Spur verschwindet.

DER ANLASS (17.08.2026, assistant)
==================================
Gemeldet: „auf /mail/inbox/2/1066/ kriege ich kein Feedback wenn ich auf Synch
klicke". Der Endpunkt lief einwandfrei - 31,5 s, 272 geholte Mails. Verschluckt
hat es eine einzige Zeile am Anfang der Anzeige-Methode::

    _set(kind, inner, autoClearMs) {
        const el = this._el();
        if (!el) return;            // <- die Meldung ist ab hier weg
        …
    }

Kein Fehler, kein Log, keine Ausnahme: Fehlt das Element, passiert lautlos gar
nichts. Genau diese Bauart sucht dieses Werkzeug - im Browser, wo ``protokoll``
nur ``console.*`` zaehlt und die Python-Seite (``except: pass``) abdeckt.

VIER BAUARTEN, ALLE AM CODE ABLESBAR
====================================
1. ``Meldung hängt am Element`` - eine Funktion bekommt einen Text uebergeben und
   kehrt wortlos zurueck, weil ihr Anzeige-Element fehlt. Der Fall oben.
2. ``catch ohne Meldung`` - ein ``catch``-Block, in dem NICHTS geschieht. Das
   Browser-Gegenstueck zu ``except Exception: pass``.
3. ``.catch verschluckt`` - dasselbe als Kettenglied: ``.catch(() => {})``.
4. ``Antwortfehler verschluckt`` - ``if (!antwort.ok) return;``. Der Server hat
   den Grund mitgeschickt, und er wird weggeworfen. (Die FEHLENDE ``.ok``-Pruefung
   findet ``jsbefunde``; hier geht es um die vorhandene, die nichts sagt.)

WAS BEWUSST KEIN BEFUND IST
===========================
* ``catch (e) { return null; }`` - ein Rueckfallwert ist etwas anderes als
  Schweigen; der Aufrufer muss ihn pruefen (siehe ``jsrumpf``).
* ``if (!btn) return;`` am Anfang eines Klick-Handlers - dort ist „nicht mein
  Knopf" die richtige Antwort, und es gibt keine Meldung, die verloren geht.
  Deshalb zaehlt Bauart 1 nur, wenn die Funktion einen Text ENTGEGENNIMMT und
  das geprueffte Element darunter wirklich beschriftet wird.
* Alles mit ``stumm gewollt: <Grund>`` im Block oder im Kommentar darueber. Der
  Grund ist Pflicht - ohne ihn waere der Vermerk ein Schalter, mit dem sich jeder
  Befund abstellen laesst (dieselbe Regel wie in ``protokoll``).
"""
import re

from .anlassfall import Anlassfall
from .jsklammern import Klammerzaehler
from .jsrumpf import Rumpf
from .jsstelle import SCHLUESSELWORTE
from .werkzeug import Ergebnis, Werkzeug2

__all__ = ["JsStumm"]


class JsStumm(Werkzeug2):
    slug = "jsstumm"
    titel = "Stille Rückmeldung: Meldungen, die im Nichts landen"
    zweck = ("Findet im JavaScript, was ein Ereignis lautlos verschwinden lässt: "
             "eine Meldung, die an einem fehlenden Element hängt, ein `catch` "
             "ohne Inhalt, `.catch(() => {})` und `if (!antwort.ok) return;`.")
    befund = ("Der Sync-Knopf der Mail-App gab 31 Sekunden lang keine "
              "Rückmeldung. Ursache war `if (!el) return;` in der Anzeige-"
              "Methode — fehlte das Element, passierte lautlos gar nichts.")
    abhilfe = ("Die Aussage braucht einen zweiten Weg (Toast, Konsole, Server) "
               "statt an einem Element zu hängen. Ein `catch`, der schweigen "
               "MUSS, bekommt `// stumm gewollt: <Grund>` — damit steht die "
               "Begründung am Code und ist nachprüfbar.")
    dauer = "1–5 s"
    kriterium = 16

    # ---------------------------------------------------------------- Muster

    #: Vermerk am Code. Die Begruendung ist Pflicht.
    MARKER = re.compile(r"stumm gewollt:\s*\S+")
    #: Ein Weg, auf dem die Aussage doch ankommt - beim Nutzer oder im Log.
    #: ``throw``/``reject`` zaehlen mit: Die Ausnahme geht weiter nach oben und
    #: ist nicht verschwunden (dieselbe Ausnahme wie in ``protokoll``).
    #: ``error`` steht hier auf Englisch UND auf Deutsch. Ohne die englische
    #: Fassung galten zwei Zeilen in ``bank/AbrufController.js`` als stumm, die
    #: mit ``this._error(d.error)`` genau das Gegenteil tun (17.08.2026) — der
    #: erste Fehlalarm dieses Werkzeugs, gefunden beim Nachsehen an der Stelle.
    #: ``Protokoll.\w+`` steht mit drin, weil das die Protokollklasse DIESES
    #: Hauses ist (``static/djangobase/js/protokoll.js``). Ohne sie galt
    #: ``Protokoll.debug(…)`` als Schweigen — ``Protokoll.warnung`` dagegen kam
    #: durch, weil ``\bwarn\w*`` zufaellig passt. Aufgefallen beim Abarbeiten
    #: der 47 Stellen in 3DTools: eine blieb stehen, und zwar die reparierte
    #: (17.08.2026).
    MELDEWEG = re.compile(
        r"toast|alert\s*\(|confirm\s*\(|console\.\w+|Protokoll\.\w+|logger|notify|"
        r"\bmeld\w*|\bmeldung\w*|fehler|error|\bwarn\w*|\bhinweis\w*|"
        r"setStatus|textContent|innerHTML|innerText|"
        r"\bthrow\b|reject\s*\(", re.I)
    #: ``catch (e) {`` und ``catch {`` (Bindung ist seit ES2019 wahlfrei).
    CATCH = re.compile(r"\bcatch\s*(?:\(\s*[^)]*\))?\s*\{")
    #: ``.catch(() => {`` / ``.catch(e => {`` / ``.catch(function (e) {``
    PROMISE_CATCH = re.compile(
        r"\.catch\(\s*(?:function\s*)?(?:\(\s*[\w$,\s]*\s*\)|[\w$]+)\s*"
        r"(?:=>\s*)?\{")
    #: ``if (!antwort.ok)`` bzw. ``if (antwort.ok === false)``
    ANTWORT = re.compile(r"if\s*\(\s*!\s*[\w.$\[\]]+\.ok\b"
                         r"|if\s*\(\s*[\w.$\[\]]+\.ok\s*===?\s*false\s*\)")
    #: Ein Abgang OHNE Wert. ``return null`` ist ein Rueckfall — der Aufrufer
    #: bekommt etwas in die Hand und muss es pruefen (dieselbe Unterscheidung
    #: wie bei ``catch``, siehe Kopf). Vorher stand hier ``\b(return|break|
    #: continue)\b``, was ``if (!antwort.ok) return null;`` mitzaehlte.
    NUR_RAUS = re.compile(r"\breturn\s*;|\b(?:break|continue)\s*;")
    #: ``if (!name) return;`` — ein Waechter, der NICHTS sagt und keinen Wert
    #: liefert. ``return null`` ist ein Rueckfall und faellt nicht darunter.
    WAECHTER = re.compile(r"^if\s*\(\s*!\s*([\w.$]+)\s*\)\s*"
                          r"(?:return\s*;|\{\s*return\s*;\s*\})\s*$")
    #: Eine Funktions- oder Methodendefinition MIT Parameterliste.
    DEFINITION = re.compile(
        r"^\s*(?:export\s+)?(?:default\s+)?(?:static\s+)?(?:async\s+)?"
        r"(?:function\s*\*?\s*)?([A-Za-z_$][\w$]*)\s*\(([^)]*)\)\s*\{\s*$")
    #: Ein Parametername, der einen Text traegt.
    MELDEPARAM = re.compile(r"^(text|txt|msg|nachricht|meldung|html|inner\w*|"
                            r"titel|title|label|inhalt|content|body|wert|"
                            r"fehler|hinweis|message)$", re.I)
    #: So wird ein Element BESCHRIFTET. Steht das unter dem Waechter, war das
    #: geprueffte Ding die Anzeige - und die Meldung ist mit ihm verschwunden.
    BESCHRIFTET = ("textContent", "innerHTML", "innerText", "className",
                   "classList", "hidden", "value", "setAttribute", "title")
    #: So weit wird nach oben nach der umgebenden Funktion gesucht.
    FUNKTIONSSUCHE = 150

    anlassfall = Anlassfall(
        {"anzeige.js": '''export function anzeigen(text) {
  const feld = document.getElementById('status');
  if (!feld) return;
  feld.textContent = text;
}

export function anzeigenMitRueckfall(text) {
  const feld = document.getElementById('status');
  if (!feld) { alert(text); return; }
  feld.textContent = text;
}

export function lesen(rohtext) {
  try { return JSON.parse(rohtext); } catch (e) { }
}

export function lesenBegruendet(rohtext) {
  // stumm gewollt: der Aufrufer prüft auf undefined und meldet dort
  try { return JSON.parse(rohtext); } catch (e) { }
}

export function lesenMitRueckfall(rohtext) {
  try { return JSON.parse(rohtext); } catch (e) { return null; }
}

export function schicken(url) {
  fetch(url).catch(() => {});
  fetch(url).catch((e) => { alert(e.message); });
}

export async function laden(url) {
  const antwort = await fetch(url);
  if (!antwort.ok) return;
  return antwort.json();
}

export async function ladenMitWurf(url) {
  const antwort = await fetch(url);
  if (!antwort.ok) throw new Error('HTTP ' + antwort.status);
  return antwort.json();
}

export async function ladenMitWurfUndVorlage(url) {
  const antwort = await fetch(url);
  if (!antwort.ok) throw new Error(`Szenenliste: ${antwort.status}`);
  return antwort.json();
}

export async function ladenMitRueckfall(url) {
  const antwort = await fetch(url);
  if (!antwort.ok) return null;
  return antwort.json();
}
'''},
        mindestens=4, hoechstens=4,
        erwartet_in="anzeige.js:3",
        warum="Alle vier Bauarten je einmal — und daneben je die Fassung, die "
              "KEINE sein darf: Rückfall auf `alert`, Vermerk „stumm gewollt\", "
              "Rückfallwert `null`, weitergeworfene Ausnahme — auch die mit "
              "`${…}` im Text, deren `{` als Blockanfang galt (23 Fehlalarme "
              "in 3DTools).")

    # ----------------------------------------------------------------- Ablauf

    def laufen(self):
        zeilen = []
        for kurz, quelle in self.frontendquellen().texte(".js"):
            zeilen += self._meldung(kurz, quelle)
            zeilen += self._catch(kurz, quelle)
            zeilen += self._promise(kurz, quelle)
            zeilen += self._antwort(kurz, quelle)
        rang = {"Meldung hängt am Element": 0, "Antwortfehler verschluckt": 1,
                "catch ohne Meldung": 2, ".catch verschluckt": 3}
        zeilen.sort(key=lambda z: (rang.get(z["art"], 9), z["ort"]))
        nach_art = {}
        for z in zeilen:
            nach_art[z["art"]] = nach_art.get(z["art"], 0) + 1
        return Ergebnis(
            ["art", "ort", "text", "warum"], zeilen,
            "%d Stellen: %s" % (len(zeilen), ", ".join(
                "%d× %s" % (n, a) for a, n in sorted(nach_art.items()))
                or "keine"),
            "Ein Rückfallwert (`return null`) ist KEIN Befund — der Aufrufer "
            "bekommt etwas in die Hand. Gezählt wird nur, wo gar nichts "
            "geschieht. Was schweigen muss, bekommt `// stumm gewollt: <Grund>`.")

    # ------------------------------------------------- 1. Meldung am Element

    def _meldung(self, kurz, zeilen):
        u"""Eine Funktion bekommt Text und wirft ihn weg, weil ein Element fehlt."""
        aus = []
        for nummer, zeile in enumerate(zeilen):
            treffer = self.WAECHTER.match(zeile.strip())
            if not treffer or self.MELDEWEG.search(zeile):
                continue
            if self._begruendet(zeilen, nummer, zeile):
                continue
            funktion = self._funktion(zeilen, nummer)
            if funktion is None:
                continue
            name, parameter, ende = funktion
            if not any(self.MELDEPARAM.match(p.strip().lstrip("."))
                       for p in parameter.split(",") if p.strip()):
                continue
            geprueft = treffer.group(1)
            if not self._wird_beschriftet(zeilen, nummer + 1, ende, geprueft):
                continue
            aus.append(self._als_zeile(
                "Meldung hängt am Element", kurz, nummer, zeile,
                "`%s` bekommt einen Text, gibt ihn aber nur weiter, wenn `%s` "
                "da ist — sonst passiert lautlos nichts"
                % (name, geprueft)))
        return aus

    def _funktion(self, zeilen, nummer):
        u"""(Name, Parameterliste, Endzeile) der Funktion um ``nummer`` - oder None."""
        von = max(-1, nummer - self.FUNKTIONSSUCHE)
        for i in range(nummer - 1, von, -1):
            treffer = self.DEFINITION.match(zeilen[i])
            if not treffer or treffer.group(1) in SCHLUESSELWORTE:
                continue
            ende = self._blockende(zeilen, i)
            if ende is None or ende < nummer:
                return None                   # Waechter steht ausserhalb
            return treffer.group(1), treffer.group(2), ende
        return None

    @classmethod
    def _blockende(cls, zeilen, anfang):
        """Zeile, in der der in ``zeilen[anfang]`` geoeffnete Block zugeht."""
        zaehler = Klammerzaehler()
        zaehler.zeile(zeilen[anfang])
        bis = min(len(zeilen), anfang + 1 + Rumpf.GRENZE)
        for i in range(anfang + 1, bis):
            zaehler.zeile(zeilen[i])
            if zaehler.tiefstand <= 0:
                return i
        return None

    @classmethod
    def _wird_beschriftet(cls, zeilen, von, bis, name):
        """Wird ``name`` unter dem Waechter als Anzeige benutzt?"""
        text = "\n".join(zeilen[von:bis + 1])
        return any("%s.%s" % (name, eigenschaft) in text
                   for eigenschaft in cls.BESCHRIFTET)

    # ------------------------------------------------------------- 2. catch

    def _catch(self, kurz, zeilen):
        return self._bloecke(kurz, zeilen, self.CATCH, "catch ohne Meldung",
                             "der Fehler ist hier zu Ende — nichts geschieht, "
                             "der Ablauf läuft weiter als wäre nichts gewesen")

    # ------------------------------------------------------ 3. .catch(() => {})

    def _promise(self, kurz, zeilen):
        return self._bloecke(kurz, zeilen, self.PROMISE_CATCH,
                             ".catch verschluckt",
                             "das Kettenglied fängt und sagt nichts — die "
                             "abgebrochene Aktion sieht erfolgreich aus")

    def _bloecke(self, kurz, zeilen, muster, art, warum):
        """Gemeinsamer Teil von 2 und 3: Block finden, Rumpf pruefen."""
        aus = []
        for nummer, zeile in enumerate(zeilen):
            if zeile.lstrip().startswith(("*", "//")):
                continue
            treffer = muster.search(zeile)
            if not treffer:
                continue
            rumpf = Rumpf.ab(zeilen, nummer, treffer.end())
            if not rumpf or not rumpf.nichts_passiert():
                continue
            if self._begruendet(zeilen, nummer, zeile + rumpf.kommentare()):
                continue
            aus.append(self._als_zeile(art, kurz, nummer, zeile, warum))
        return aus

    # -------------------------------------------------- 4. Antwort ohne Grund

    def _antwort(self, kurz, zeilen):
        u"""``if (!antwort.ok) return;`` - der Server hat den Grund mitgeschickt."""
        aus = []
        for nummer, zeile in enumerate(zeilen):
            if zeile.lstrip().startswith(("*", "//")):
                continue
            treffer = self.ANTWORT.search(zeile)
            if not treffer:
                continue
            rest = zeile[treffer.end():]
            klammer = self._blockklammer(zeile, treffer.start())
            if klammer is not None:
                rumpf = Rumpf.ab(zeilen, nummer, klammer + 1)
                if not rumpf:
                    continue
                schweigt = not rumpf.enthaelt(self.MELDEWEG)
                vermerk = zeile + rumpf.kommentare()
            else:
                if not self.NUR_RAUS.search(rest):
                    continue
                schweigt = not self.MELDEWEG.search(rest)
                vermerk = zeile
            if not schweigt or self._begruendet(zeilen, nummer, vermerk):
                continue
            aus.append(self._als_zeile(
                "Antwortfehler verschluckt", kurz, nummer, zeile,
                "der Status ist geprüft, aber die Meldung des Servers wird "
                "verworfen — der Nutzer sieht einen Abbruch ohne Grund"))
        return aus

    @staticmethod
    def _blockklammer(zeile, ab):
        u"""Position der ``{``, die den if-Block oeffnet — oder None.

        NICHT ``"{" in rest`` (23 Fehlalarme in 3DTools, 17.08.2026): In

            if (!resp.ok) throw new Error(`Scene list error: ${resp.status}`);

        steht ein ``{`` — es gehoert zur Vorlagenzeichenkette ``${…}``. Das galt
        als Blockanfang; gelesen wurde dann der „Rumpf" ``resp.status}…``, darin
        kein Meldeweg, also ein Befund. Gemeldet waren damit ausgerechnet die
        Zeilen, die es RICHTIG machen: Sie werfen die Ausnahme mit Statuscode
        weiter, und ``throw`` steht in ``MELDEWEG``.

        Gesucht wird deshalb die Klammer, die auf das schliessende ``)`` der
        Bedingung folgt — und nur die.
        """
        tiefe = 0
        i = ab
        while i < len(zeile):
            if zeile[i] == "(":
                tiefe += 1
            elif zeile[i] == ")":
                tiefe -= 1
                if tiefe == 0:
                    break
            i += 1
        else:
            return None
        rest = zeile[i + 1:]
        if not rest.lstrip().startswith("{"):
            return None
        return i + 1 + (len(rest) - len(rest.lstrip()))

    # ------------------------------------------------------------- Gemeinsam

    def _begruendet(self, zeilen, nummer, text):
        """Steht ein ``stumm gewollt: <Grund>`` an der Stelle oder darueber?"""
        if self.MARKER.search(text):
            return True
        return bool(self.MARKER.search(Rumpf.kommentarblock_ueber(zeilen, nummer)))

    @staticmethod
    def _als_zeile(art, kurz, nummer, zeile, warum):
        # Dictionary gewollt: geht unveraendert als JSON an die Seite.
        return {"art": art, "ort": "%s:%d" % (kurz, nummer + 1),
                "text": zeile.strip()[:110], "warum": warum}
