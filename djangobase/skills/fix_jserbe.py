# -*- coding: utf-8 -*-
u"""FixJsErbe - eine zu grosse JS-KLASSE ueber Vererbung teilen.

WARUM NICHT MIT EINER ZEILENNUMMER (16.08.2026)
===============================================
Von 35 zu grossen JS-Dateien sind 20 je EINE Klasse: keine freie Funktion, kein
zweiter Einstiegspunkt, nur ein ``export class X`` mit zwanzig bis sechsundzwanzig
Methoden. Der Datei-Schnitt hat dort nichts zu greifen - er meldete 35 mal
denselben nichtssagenden Satz, bis die Diagnose es benannte.

Der richtige Schnitt ist die VERERBUNGSKETTE:

    xyz_basis.js   export class XyzBasis { …die Haelfte der Methoden… }
    xyz.js         export class Xyz extends XyzBasis { …der Rest… }

DER ENTSCHEIDENDE VORTEIL: Kein Aufrufer wandert mit. ``new Xyz()`` bleibt
``new Xyz()``, ``this.irgendwas()`` funktioniert in BEIDE Richtungen, weil
``this`` immer die vollstaendige Instanz ist. Genau das macht diesen Schnitt
risikoaermer als jeden anderen - dieselbe Umstellung lief in dieser Sitzung
rund zwanzig Mal von Hand, ohne einen einzigen Laufzeitfehler.

DIE VIER FALLEN, DIE ES TROTZDEM GIBT
=====================================
    1  ``super()`` fehlt   Der Konstruktor bleibt oben, erbt aber jetzt. Real
                           passiert (ConditionEditor) - die ganze Seite war tot.
    2  Selbstbezug         ``Xyz.KONSTANTE`` in einer wandernden Methode zeigt
                           auf die abgeleitete Klasse, die die Basis nicht kennen
                           darf. Muss ``this.constructor.KONSTANTE`` werden.
    3  Modul-lokaler Name  Braucht eine wandernde Methode eine freie Funktion der
                           Ursprungsdatei, muesste die Basis sie importieren - und
                           die Ursprungsdatei importiert die Basis. Zirkel.
    4  statisches Feld     ``static X = …`` gehoert zu der Klasse, die es
                           deklariert; wandert die Methode, nicht aber das Feld,
                           zeigt der Zugriff ins Leere.

Faellt eine davon, waehlt der Fixer eine andere Methodenmenge - und meldet,
wenn keine bleibt.
"""
import re

from .fixer import Aenderung, Fixer, Vorschau


class Methode:
    """Eine Methode einer JS-Klasse: ihre Zeilen und was sie von aussen braucht."""

    KOPF = re.compile(r"^(\s+)(static\s+)?(async\s+)?(get\s+|set\s+)?"
                      r"([A-Za-z_$][\w$]*)\s*\(")

    def __init__(self, name, zeilen, statisch=False, vorspann=()):
        self.name = name
        #: Kommentarzeilen unmittelbar davor gehoeren zur Methode.
        self.vorspann = list(vorspann)
        self.zeilen = list(zeilen)
        self.statisch = statisch

    @property
    def volle_zeilen(self):
        return self.vorspann + self.zeilen

    @property
    def laenge(self):
        return len(self.volle_zeilen)

    @property
    def text(self):
        return "\n".join(self.volle_zeilen)

    @property
    def ist_konstruktor(self):
        return self.name == "constructor"

    def benutzt(self, namen):
        return {n for n in namen
                if re.search(r"(?<![.\w])%s\b" % re.escape(n), self.text)}


class Klassendatei:
    """Eine JS-Datei, die aus genau einer Klasse besteht - zerlegt in Methoden."""

    def __init__(self, pfad, zeilen=None):
        self.pfad = pfad
        self.zeilen = zeilen if zeilen is not None else \
            pfad.read_text(encoding="utf-8", errors="replace").split("\n")
        self.klasse = ""
        self.erbt = ""
        self.kopf, self.methoden, self.fuss = [], [], []
        self.statische_felder = []
        #: Index der ``class …``-Zeile INNERHALB von ``kopf``.
        self.klassenzeile = -1
        self._zerlegen()

    # ---- zerlegen -----------------------------------------------------------
    def _zerlegen(self):
        anfang = None
        for i, z in enumerate(self.zeilen):
            m = re.match(r"^(?:export\s+)?(?:default\s+)?class\s+(\w+)"
                         r"(?:\s+extends\s+([\w.]+))?", z)
            if m:
                self.klasse, self.erbt, anfang = m.group(1), m.group(2) or "", i
                break
        if anfang is None:
            return
        ende = self._klassenende(anfang)
        self.kopf = self.zeilen[:anfang + 1]
        # WO IM KOPF DIE KLASSENZEILE STEHT, muss gemerkt werden (16.08.2026):
        # ``_methoden_lesen`` haengt statische Felder und Zwischenkommentare
        # hinten an ``kopf`` an, danach ist die Klassenzeile NICHT mehr die
        # letzte. Die erste Fassung schrieb blind ``kopf[-1]`` um - das
        # ``extends`` fehlte, und ``super()`` im Konstruktor war ein
        # SyntaxError. Gefangen hat es das node-Netz, nicht das Auge.
        self.klassenzeile = anfang
        # ``ende`` zeigt HINTER die schliessende Klammer der Klasse. Der Fuss
        # muss sie mitnehmen (``ende - 1``), sonst fehlt sie im Ergebnis - der
        # Rest der Datei landet dann IM Klassenrumpf und ``window.Xyz = Xyz``
        # wirft „Unexpected token '.'" (16.08.2026, vom node-Netz gefangen).
        self.fuss = self.zeilen[ende - 1:]
        self._methoden_lesen(anfang + 1, ende - 1)

    def _klassenende(self, anfang):
        tiefe = 0
        for i in range(anfang, len(self.zeilen)):
            tiefe += self.zeilen[i].count("{") - self.zeilen[i].count("}")
            if tiefe == 0 and i > anfang:
                return i + 1
        return len(self.zeilen)

    def _methoden_lesen(self, von, bis):
        i, offen = von, []
        while i < bis:
            z = self.zeilen[i]
            m = Methode.KOPF.match(z)
            if re.match(r"^\s+static\s+[A-Za-z_$][\w$]*\s*=", z):
                self.statische_felder.append(
                    re.match(r"^\s+static\s+([A-Za-z_$][\w$]*)", z).group(1))
                offen.append(z)
                i += 1
                continue
            if not m or m.group(5) in ("if", "for", "while", "switch", "catch"):
                offen.append(z)
                i += 1
                continue
            ende = self._rumpfende(i, bis)
            vorspann = []
            while offen and (offen[-1].strip().startswith(("//", "*", "/*"))
                             or not offen[-1].strip()):
                vorspann.insert(0, offen.pop())
            self.methoden.append(Methode(m.group(5), self.zeilen[i:ende],
                                         bool(m.group(2)), vorspann))
            self.kopf += offen
            offen = []
            i = ende
        self.kopf += offen

    def _rumpfende(self, i, bis):
        tiefe, gesehen = 0, False
        for j in range(i, bis):
            tiefe += self.zeilen[j].count("{") - self.zeilen[j].count("}")
            gesehen = gesehen or "{" in self.zeilen[j]
            if gesehen and tiefe <= 0:
                return j + 1
        return bis

    # ---- was die Datei ausserhalb der Klasse hat ----------------------------
    @property
    def modul_lokale_namen(self):
        """Freie Funktionen und Konstanten der Datei - die kann die Basis NICHT."""
        text = "\n".join(self.kopf + self.fuss)
        ohne_import = re.sub(r"^import[^;]*;", "", text, flags=re.M | re.S)
        return set(re.findall(
            r"^(?:export\s+)?(?:async\s+)?(?:function|const|let|var)\s+(\w+)",
            ohne_import, re.M))

    @property
    def importzeilen(self):
        """Alle Import-Anweisungen - AUCH die mehrzeiligen.

        Eine lange Namensliste bricht oft um::

            import { backtestKoerper, entwurf, speicherform, zeilen }
                from './tradesystem_dom.js';

        Wer nur Zeilen nimmt, die mit ``import`` beginnen, kopiert die erste
        Haelfte und laesst ``from …`` liegen: „Unexpected reserved word".
        Deshalb wird bis zur Zeile mit dem Semikolon bzw. dem ``from`` gelesen.

        UND KOMMENTARE ZAEHLEN NICHT. Viele Dateien zeigen im Kopfkommentar ihre
        eigene Benutzung::

            /* …
                   import { IbOrderModal } from '/static/…/ib_order_modal.js';
                   const modal = new IbOrderModal();                        */

        Diese Beispielzeile wanderte als echter Import in die Basis - und machte
        aus dem Beispiel einen Zirkel: „Cannot access 'IbOrderModalBasis' before
        initialization", die IB-Seite ohne Order-Dialog (16.08.2026).
        """
        aus, i, im_block = [], 0, False
        while i < len(self.kopf):
            z = self.kopf[i]
            if im_block:
                im_block = "*/" not in z
                i += 1
                continue
            if z.lstrip().startswith("/*") and "*/" not in z:
                im_block = True
                i += 1
                continue
            if re.match(r"^\s*import\b", z) and not z.lstrip().startswith("//"):
                block = [z]
                while (";" not in block[-1] and i + 1 < len(self.kopf)
                       and len(block) < 8):
                    i += 1
                    block.append(self.kopf[i])
                aus += block
            i += 1
        return aus


class Erbteilung:
    """Welche Methoden in die Basis gehen - und was dagegen spricht."""

    GRENZE = 200

    #: Welche Anteile durchprobiert werden, bis beide Haelften passen.
    ANTEILE = (0.5, 0.6, 0.7, 0.8)

    def __init__(self, datei, anteil=0.5):
        self.datei = datei
        self.anteil = anteil
        self.basis_namen = self._waehlen()

    @classmethod
    def beste(cls, datei):
        """Die Teilung, bei der BEIDE Haelften unter die Grenze kommen.

        Mit festem Halbe-Halbe blieb ``tradesystem_config.js`` bei 265 Zeilen
        stehen, waehrend die Basis nur 39 bekam: Konstruktor, statische Methoden
        und alles, was eine freie Funktion der Datei braucht, koennen nicht
        wandern - die verbleibende Auswahl ist oft viel kleiner als die Haelfte.
        Deshalb wird der Anteil erhoeht, bis es passt (16.08.2026).
        """
        versuche = [cls(datei, a) for a in cls.ANTEILE]
        passend = [t for t in versuche if not t.warnungen() and t.beide_passen]
        if passend:
            return passend[0]
        ohne_warnung = [t for t in versuche if not t.warnungen()]
        if ohne_warnung:
            return min(ohne_warnung, key=lambda t: t.groesseres_teil)
        return versuche[0]

    @property
    def groesseres_teil(self):
        rest = self._zeilen(self.rest_methoden) + len(self.datei.kopf) + \
            len(self.datei.fuss)
        basis = self._zeilen(self.basis_methoden) + \
            len(self.datei.importzeilen) + 8
        return max(rest, basis)

    @property
    def beide_passen(self):
        return self.basis_namen and self.groesseres_teil <= self.GRENZE

    @property
    def basisklasse(self):
        return self.datei.klasse + "Basis"

    @property
    def basisdatei(self):
        return "%s_basis.js" % self.datei.pfad.stem

    def _waehlen(self):
        """Von HINTEN auffuellen, bis rund die Haelfte der Zeilen zusammen ist.

        Uebersprungen wird, was nicht wandern darf: der Konstruktor (er bleibt
        bei der abgeleiteten Klasse, sonst braucht sie einen kuenstlichen), jede
        statische Methode (ihr Aufruf ``Xyz.helfer()`` zeigt sonst ins Leere) und
        jede Methode, die einen modul-lokalen Namen der Ursprungsdatei braucht.
        """
        gesamt = sum(m.laenge for m in self.datei.methoden)
        lokal = self.datei.modul_lokale_namen
        gewaehlt, summe = [], 0
        for m in reversed(self.datei.methoden):
            if m.ist_konstruktor or m.statisch or m.benutzt(lokal):
                continue
            if summe >= gesamt * self.anteil:
                break
            gewaehlt.append(m.name)
            summe += m.laenge
        return gewaehlt

    @property
    def basis_methoden(self):
        return [m for m in self.datei.methoden if m.name in self.basis_namen]

    @property
    def rest_methoden(self):
        return [m for m in self.datei.methoden if m.name not in self.basis_namen]

    def _zeilen(self, methoden):
        return sum(m.laenge for m in methoden)

    # ---- die Fallen ---------------------------------------------------------
    def warnungen(self):
        aus = []
        if not self.datei.klasse:
            return ["keine Klasse gefunden"]
        if self.datei.erbt:
            aus.append("erbt bereits von %s — Kette von Hand prüfen"
                       % self.datei.erbt)
        if len(re.findall(r"^(?:export\s+)?class\s+\w+",
                          "\n".join(self.datei.zeilen), re.M)) > 1:
            aus.append("mehrere Klassen in der Datei — erst trennen")
        if not self.basis_namen:
            aus.append(self._warum_keine())
            return aus
        rest = self._zeilen(self.rest_methoden) + len(self.datei.kopf) + \
            len(self.datei.fuss)
        basis = self._zeilen(self.basis_methoden) + len(self.datei.importzeilen) + 8
        if rest > self.GRENZE and basis > self.GRENZE:
            aus.append("lohnt nicht: beide Teile blieben über %d Zeilen "
                       "(%d / %d)" % (self.GRENZE, rest, basis))
        for m in self.basis_methoden:
            if re.search(r"(?<![.\w])super\s*[.(]", m.text):
                aus.append("%s benutzt super — die Basis hat keine Oberklasse"
                           % m.name)
                break
        # ZIRKEL: Zeigt einer der mitwandernden Importe auf die Ursprungsdatei
        # zurueck, ist die Basis beim ``extends`` noch nicht ausgewertet -
        # „Cannot access 'XyzBasis' before initialization", und das Modul ist
        # samt allem, was es exportiert, tot. Node sieht das nicht, es ist
        # gueltige Syntax; erst der Browser meldet es (16.08.2026).
        eigener = self.datei.pfad.name
        for z in self.datei.importzeilen:
            if eigener in z:
                aus.append("Zirkel: ein Import der Basis zeigt auf %s zurück"
                           % eigener)
                break
        # ``Xyz.foo`` in einer wandernden Methode wird ``this.constructor.foo``.
        # Das trifft NUR bei statischen Mitgliedern zu; ist ``foo`` eine
        # Instanzmethode, war der Aufruf schon vorher falsch und die Umschreibung
        # macht daraus einen stillen Laufzeitfehler statt eines sichtbaren.
        statisch = self.statische_namen
        for m in self.basis_methoden:
            fremd = [z for z in re.findall(
                r"(?<![.\w])%s\.([A-Za-z_$][\w$]*)" % re.escape(self.datei.klasse),
                m.text) if z not in statisch]
            if fremd:
                aus.append("%s greift auf %s.%s zu, das nicht statisch ist"
                           % (m.name, self.datei.klasse, fremd[0]))
                break
        return aus

    def _warum_keine(self):
        """Nicht „keine Methode darf wandern", sondern WELCHE woran haengt.

        Der Sammelsatz stand wortgleich unter fuenf verschiedenen Dateien und
        sagte niemandem, wo anzusetzen ist.
        """
        lokal = self.datei.modul_lokale_namen
        gruende, namen = [], []
        for m in self.datei.methoden:
            if m.ist_konstruktor:
                gruende.append("Konstruktor")
            elif m.statisch:
                gruende.append("statisch")
            else:
                gebraucht = m.benutzt(lokal)
                if gebraucht:
                    gruende.append("braucht %s" % ", ".join(sorted(gebraucht)))
                    namen.append(m.name)
        zaehler = {}
        for g in gruende:
            zaehler[g] = zaehler.get(g, 0) + 1
        teile = ["%s (%dx)" % (g, n) if n > 1 else g
                 for g, n in sorted(zaehler.items(), key=lambda x: -x[1])[:3]]
        schwanz = " — z. B. %s" % ", ".join(namen[:2]) if namen else ""
        return "keine Methode darf wandern: %s%s" % ("; ".join(teile), schwanz)

    # ---- der Text -----------------------------------------------------------
    @property
    def statische_namen(self):
        return {m.name for m in self.datei.methoden if m.statisch} | \
            set(self.datei.statische_felder)

    def _im_string(self, zeile, pos):
        """Steht ``pos`` innerhalb eines Anführungszeichen-Paars dieser Zeile?

        Grobe, aber ausreichende Heuristik: eine UNGERADE Zahl Anfuehrungs-
        zeichen davor heisst „mitten drin". Ein Klassenname in einem HTML-String
        darf nicht zu ``this.constructor.`` werden - das waere ein Fehler, den
        keine Syntaxpruefung findet und der erst beim Rendern auffaellt.
        """
        vor = zeile[:pos]
        return any(vor.count(z) % 2 == 1 for z in ("'", '"', "`"))

    def _entselbstbezug(self, zeile):
        """``Xyz.KONST`` -> ``this.constructor.KONST`` (Falle 2, real passiert)."""
        muster = re.compile(r"(?<![.\w])%s\." % re.escape(self.datei.klasse))
        aus, zuletzt = [], 0
        for m in muster.finditer(zeile):
            aus.append(zeile[zuletzt:m.start()])
            aus.append(m.group(0) if self._im_string(zeile, m.start())
                       else "this.constructor.")
            zuletzt = m.end()
        return "".join(aus) + zeile[zuletzt:]

    def basistext(self):
        kopf = ["/* %s — die untere Hälfte von %s."
                % (self.basisklasse, self.datei.pfad.name),
                "   " + "=" * 70,
                "   <WOFÜR steht diese Hälfte? Ein Satz — HANDARBEIT.>",
                "",
                "   Über Vererbung herausgelöst: `this` bleibt die vollständige",
                "   Instanz, deshalb rufen sich beide Hälften weiter gegenseitig.",
                "   " + "=" * 70 + " */"]
        rumpf = []
        for m in self.basis_methoden:
            rumpf += [self._entselbstbezug(z) for z in m.volle_zeilen]
        return "\n".join(kopf + self.datei.importzeilen +
                         ["", "export class %s {" % self.basisklasse] +
                         rumpf + ["}", ""])

    def resttext(self):
        kopf = list(self.datei.kopf)
        bei = self.datei.klassenzeile
        kopf[bei] = re.sub(r"class\s+%s\b" % re.escape(self.datei.klasse),
                           "class %s extends %s" % (self.datei.klasse,
                                                    self.basisklasse),
                           kopf[bei])
        # Der Import gehoert VOR die Klassenzeile, nicht hinter die letzte
        # Import-Zeile: dazwischen koennen Konstanten und Kommentare stehen.
        #
        # ``?v=1`` IST KEIN SCHMUCK: Die Vorlage laedt die Hauptdatei versioniert,
        # ihr relativer Import zieht die Basis aber OHNE Query nach - die kommt
        # dann dauerhaft aus dem Browser-Cache, egal wie oft die Hauptdatei
        # gebumpt wird. Genau daran hing eine weisse Seite (WalkHop/navi.js,
        # 15.06.2026). Beim naechsten Edit an der Basis diese Zahl erhoehen.
        kopf.insert(bei, "import {%s} from './%s?v=1';" % (self.basisklasse,
                                                           self.basisdatei))
        rumpf = []
        for m in self.rest_methoden:
            rumpf += self._mit_super(m) if m.ist_konstruktor else m.volle_zeilen
        return "\n".join(kopf + rumpf + self.datei.fuss)

    @staticmethod
    def _mit_super(methode):
        """``super();`` als erste RUMPF-Zeile des Konstruktors - Falle 1.

        Ohne diese Zeile wirft der Konstruktor beim ersten ``new``, das Modul
        verwirft der Browser komplett, und die ganze Seite ist tot. Genau so
        passiert (ConditionEditor, 16.08.2026).

        ZWEI STELLEN, AN DENEN DIE NAIVE SUCHE DANEBENGREIFT - beide real
        aufgetreten und vom node-Netz gefangen:

            /** @param {{wurzel:string}} opt */     <- geschweifte Klammer im
            constructor(opt) {                         Doc-Kommentar DAVOR

            constructor({ wurzel, status } = {}) {  <- und in den Parametern

        Deshalb wird nur im Rumpf gesucht (ohne Vorspann) und dort die Zeile
        genommen, die AUF ``{`` endet - das ist der Kopf, nie ein Parameter.
        """
        rumpf = list(methode.zeilen)
        if any(re.search(r"(?<![.\w])super\s*\(", z) for z in rumpf):
            return methode.volle_zeilen
        bei = next((i for i, z in enumerate(rumpf) if z.rstrip().endswith("{")),
                   None)
        if bei is None:
            bei = next((i for i, z in enumerate(rumpf) if "{" in z), None)
        if bei is None:
            return methode.volle_zeilen
        folge = rumpf[bei + 1] if bei + 1 < len(rumpf) else ""
        einzug = " " * ((len(folge) - len(folge.lstrip())) or
                        (len(rumpf[bei]) - len(rumpf[bei].lstrip()) + 2))
        return methode.vorspann + rumpf[:bei + 1] + [einzug + "super();"] + \
            rumpf[bei + 1:]


class FixJsErbe(Fixer):
    slug = "fix-jserbe"
    titel = "Große JS-Klasse über Vererbung teilen"
    tut = ("Löst die hintere Hälfte der Methoden als Basisklasse in eine eigene "
           "Datei — die Klasse selbst behält Namen, Konstruktor und Aufrufer.")
    warum = ("20 von 35 zu großen JS-Dateien sind je EINE Klasse; ein Schnitt an "
             "einer Zeilennummer findet dort nichts. Vererbung ist der einzige "
             "Schnitt, bei dem kein Aufrufer mitwandert.")
    grenzen = ("Konstruktor, statische Methoden und alles, was eine freie Funktion "
               "der Datei braucht, bleiben zurück. Die Überschrift der neuen "
               "Datei ist ein Platzhalter.")
    kriterium = 3
    dauer = "5–15 s"

    GRENZE = 200
    RAUS = ("__pycache__", "node_modules", "venv", "pythonVENV", ".git",
            "sicherung", "backup", "archiv", "_web")

    def _kandidaten(self):
        for pfad in sorted(self.wurzel().rglob("*.js")):
            if not self.erlaubt(pfad):
                continue
            zeilen = pfad.read_text(encoding="utf-8", errors="replace").split("\n")
            if len(zeilen) <= self.GRENZE:
                continue
            datei = Klassendatei(pfad, zeilen)
            # SCHWELLE 2, NICHT 4: Eine Datei mit drei sehr langen Methoden ist
            # ein echter Befund - sie taucht nur nicht mehr auf, wenn man sie
            # wegfiltert. ``tradesystem_config.js`` stand nach dem ersten Teilen
            # bei 266 Zeilen in drei Methoden und verschwand still aus der
            # Liste; die Diagnose „keine Methode darf wandern" ist die
            # brauchbarere Antwort (16.08.2026).
            if datei.klasse and len(datei.methoden) >= 2:
                yield datei

    def vorschau(self):
        aenderungen = []
        for datei in self._kandidaten():
            teilung = Erbteilung.beste(datei)
            warnungen = teilung.warnungen()
            was = ("%s (%d Methoden) → %s mit %d Methoden"
                   % (datei.klasse, len(datei.methoden), teilung.basisklasse,
                      len(teilung.basis_methoden)))
            if warnungen:
                aenderungen.append(Aenderung(datei.pfad, was, None, warnungen))
                continue
            aend = Aenderung(datei.pfad, was, teilung.resttext(),
                             begleiter=(datei.pfad.parent / teilung.basisdatei,
                                        teilung.basistext()))
            aend.methodennamen = [m.name for m in datei.methoden]
            aenderungen.append(aend)
        return Vorschau(aenderungen,
                        "Beide Hälften rufen sich weiter gegenseitig — `this` ist "
                        "die vollständige Instanz. Die Überschrift der neuen "
                        "Datei bitte nach dem Anwenden füllen.")

    def pruefen(self, aenderung):
        """Beide Dateien müssen als ES-Modul parsen, und nichts darf fehlen.

        Die Zaehlprobe ist kein Beiwerk: Beim Datei-Schnitt derselben Sitzung
        blieb zweimal eine Methode auf der Strecke, ohne dass irgendetwas rot
        wurde - erst der Klick auf den zugehoerigen Knopf zeigte es.
        """
        fehler, teile = [], [aenderung.pfad]
        if aenderung.begleiter:
            teile.append(aenderung.begleiter[0])
        for pfad in teile:
            fehler += self._parst(pfad)
        if fehler:
            return fehler
        # Der Zirkel ist der einzige Fehler dieser Reihe, den node NICHT sieht:
        # Beide Dateien sind syntaktisch tadellos, erst der Modulgraph kippt.
        if aenderung.begleiter:
            basis = aenderung.begleiter[0]
            for z in basis.read_text(encoding="utf-8").split("\n"):
                if re.match(r"^\s*import\b", z) and aenderung.pfad.name in z:
                    return ["Zirkel: %s importiert %s zurück"
                            % (basis.name, aenderung.pfad.name)]
        vorher = getattr(aenderung, "methodennamen", None)
        if vorher:
            text = "\n".join(p.read_text(encoding="utf-8") for p in teile)
            nachher = set(re.findall(
                r"^\s+(?:static\s+|async\s+|get\s+|set\s+)*"
                r"([A-Za-z_$][\w$]*)\s*\(", text, re.M))
            fehlt = sorted(set(vorher) - nachher)
            if fehlt:
                return ["Methoden verloren: %s" % ", ".join(fehlt)]
        return []

    @staticmethod
    def _parst(pfad):
        """``node --input-type=module --check`` - die EINZIGE verlässliche Form.

        ``node --check <datei>`` behandelt die Datei als CommonJS-Skript und gab
        am 16.08.2026 fuer eine nachweislich kaputte Modul-Datei 0 zurueck; der
        Browser meldete denselben SyntaxError sofort."""
        import subprocess
        try:
            text = pfad.read_text(encoding="utf-8")
        except OSError as e:
            return ["%s nicht lesbar: %s" % (pfad.name, e)]
        try:
            lauf = subprocess.run(["node", "--input-type=module", "--check"],
                                  input=text, capture_output=True, text=True,
                                  timeout=25, encoding="utf-8")
        except (OSError, subprocess.SubprocessError):
            return []                      # ohne node kein Urteil, kein Fehlalarm
        if lauf.returncode != 0:
            kurz = (lauf.stderr or "").strip().split("\n")
            return ["%s parst nicht: %s" % (pfad.name, kurz[-1] if kurz else "?")]
        return []
