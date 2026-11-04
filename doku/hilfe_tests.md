# Hilfe → Tests: Laufzeiten, Kategorie und Bereich, Live-Lauf, Webmodul, Konformitätsprüfungen

Aus `CLAUDE.md` ausgelagert am 02.11.2026 (wörtlich). Bei Arbeit an diesem Thema lesen.

## Hilfe → Tests

### Testlaufzeiten je Testcase (Hilfe → Tests)

`testdauern.Dauern` hängt `--durations 0` an (nur wenn der Interpreter des
Projekts Python 3.12+ ist — sonst bricht der Lauf an einem unbekannten Argument
ab) und liest die Laufzeiten aus der Ausgabe. `testhistorie.Testhistorie` hält
die **letzten vier Läufe je Testcase und je Suite** mit Datum/Uhrzeit in
`BASE_DIR/logs/testhistorie.json` (keine DB — die Seite muss auch beim
Neuaufbau der Test-DB Zahlen zeigen). `testtabelle.Testtabelle` baut daraus die
sortierbare Tabelle (`_tabelle.html`): Testcase · letzte · Ø · Trend ·
letzte 4 Läufe · Run. Trend erst ab 25 % Abweichung, alles darunter ist Rauschen.

Fehlt `DJANGOBASE["test_discover"]`, leitet die Seite die Labels aus denselben
`test_befehle` ab — die Einzeltest-Reiter stehen damit in JEDEM Projekt. Die
Discovery ist 10 Minuten gecacht (sie importiert jedes Testmodul).

### Zwei Einteilungen: Kategorie und Bereich (17.08.2026)

**Kategorie** = wie getestet wird (`unit`, `component`, `ui`, `automated`,
`performance`, `longrunner`). Sie ist der ORDNER `app/tests/<art>/`; die
Combo-Box „Verschieben" hängt die Testdatei um (`testverschieben.Verschieber`).

**Bereich** = was getestet wird (Chat, Mail, Musik …). Den gibt **das Projekt**
an, in `settings.py` oder unter Einstellungen → djangoBase (Feldtyp `zeilen`,
eine Angabe je Zeile):

    DJANGOBASE["test_bereiche"] = [
        {"slug": "musik", "name": "Musik", "praefixe": ["search.tests.musik"],
         "beschreibung": "…"},          # oder: "musik | Musik | search.tests.musik | …"
    ]

Ohne Angabe wird der Bereich aus dem Ordner abgeleitet (`app/tests/<bereich>/
<art>/`, sonst die App). Die REIHENFOLGE der Angabe ist die Reihenfolge in der
Tabelle; dasselbe gilt für `test_kategorien` („unit | Unit", nur bekannte Slugs).

Darstellung: **EINE Tabelle je Kategorie**, Bereich als eigene Spalte, Zeilen
danach vorsortiert, vor jedem Bereich eine Abschnittszeile mit „Auswählen" und
„Bereich ausführen". Sortiert der Nutzer nach einer anderen Spalte, nimmt
`tabellen_sortierung.js` die Abschnittszeilen heraus (`data-gruppe`) und meldet
`tabelle:sortiert`; `tests_bereiche.js` setzt sie zurück, sobald wieder nach
Bereich sortiert wird.

**Ein Bereich, dessen Präfix über anderen liegt** (`search.tests` über
`search.tests.chat`), ist KEIN Verschiebeziel — sonst landet die Datei in
`search/tests/<art>/` und verschwindet aus der Gliederung. Genau das ist am
17.08.2026 einmal passiert (`Bereiche.ziele`).

Projektseiten mit eigenem Runner nehmen `Testtabelle(..., run_modus="knopf")`
(rendert `<button data-run=…>` statt `?run=`-Link) und setzen
`data-tests-auswahl="ereignis"` auf einen Vorfahren; die Auswahl meldet dann
`tests:auswahl-lauf` statt zu posten. Laufzeiten aus einem fremden Runner gehen
über `testmitschrift.Mitschrift` in dieselbe Historie.

**Statische Dateien:** Vorlagen hängen `?v={{ djangobase.statik_v }}` an Skripte
UND an ES-Importe (`statik.Statik` = jüngste mtime der djangoBase-JS/CSS). Ohne
das liefert der Browser-Cache alte Module — gemessen: mit Cache-Buster kam die
neue Fassung, ohne die alte, bei frisch aktiviertem Service Worker.

**Logging:** Testläufe und Verschiebungen loggen auf `djangobase.tests` (nicht
`django` — dort hängt `django.server` mit jeder Anfrage). Ein Konsument, der
nichts konfiguriert, sieht davon nichts; im assistant liegt dafür
`djangobase.log` samt Eintrag in `log_sources`.

### Live-Lauf und Spalte „Nr." (17.08.2026)

**Live-Lauf:** `POST /hilfe/tests/strom/` (`teststrom.Teststrom`) fährt die
geprüften Ziele und streamt JSON-Zeilen: `start` → `log`/`progress` → `summary`.
`tests_strom.js` fängt Run-Link, „Alle ausführen", „Bereich ausführen" und die
Checkbox-Auswahl ab, schreibt ✓/✗ in **alle** Zeilen mit dieser Test-ID (der
Fall steht im Kategorie-Reiter UND in „Alle") und am Ende die Laufzeiten. Die
`?run=`-Links bleiben im HTML — ohne das Modul läuft es wie vorher mit
Seitenwechsel.

**Der Prozess darf nie zurückbleiben — drei Netze, nicht eins** (18.08.2026
nachgezogen; das `finally` allein deckte den Fall nicht ab):

1. `readline()` blockiert, also kommt `GeneratorExit` erst beim nächsten `yield`.
   Ein Test, der hängt und nichts ausgibt, hätte den Prozess endlos gehalten →
   **Wächter-Thread** (`threading.Timer`) beendet nach Ablauf der Frist ohne auf
   Ausgabe zu warten. Gemessen an einem Prozess, der eine Zeile schreibt und dann
   schläft: Abbruch nach 6,2 s bei Frist 6 s (vorher: 300 s).
2. `kill()` trifft nur den einen Prozess; ein Testlauf hat Kinder
   (`ProcessPoolExecutor`), und auf Windows sterben die NICHT mit dem Eltern-
   prozess → `testtoeter.Toeter` beendet den **Baum** (`taskkill /F /T` bzw.
   `os.killpg`; dafür startet der Lauf auf POSIX mit `start_new_session=True`).
3. Endet der SERVER mitten im Lauf, wäre der Testprozess verwaist → `atexit`.

Nebenbefund derselben Runde: `OpenProcess` gelingt auf Windows auch für einen
BEENDETEN Prozess, solange noch ein Handle offen ist. „Läuft der noch?" fragt
deshalb `GetExitCodeProcess` (259 = `STILL_ACTIVE`) — sonst hätte eine vergessene
Sperre bis zur Frist gehalten.

**EIN Lauf zur Zeit** über `testsperre.Laufsperre`: eine Datei
(`logs/teststrom.lock`, `O_EXCL`) mit der Server-PID. Die JS-Sperre der ersten
Fassung galt nur für den EINEN Tab — ein zweiter Tab startete munter einen
zweiten Lauf auf derselben Testdatenbank. Stirbt der Server, gilt die Sperre
nicht mehr (PID-Prüfung), spätestens nach `FRIST` verfällt sie. Der Knopf
**„Abbrechen"** (`POST … {"abbrechen": true}`) beendet Baum und Sperre — ohne ihn
hielte ein hängender Lauf eine Stunde.

Den Fortschritt aus der Ausgabe liest `testzeilen.Testzeilen` — drei gemessene
Fallen: Name und Ergebnis stehen nicht in einer Zeile, Zeitstempel können mitten
in der Zeile stehen, und bei Tests mit Docstring zeigt `-v 2` dessen erste Zeile
statt des Namens.

**Was ausgeführt werden darf** steht an EINER Stelle: `testziele.Testziele`
(entdeckte Test-IDs, Slugs konfigurierter Befehle, Karten-Labels; Form geprüft).
Seiten-Lauf und Live-Lauf benutzen sie gemeinsam.

**Spalte „Nr.":** der Platz in der Tabelle, änderbar.
`POST /hilfe/tests/nummer/` bekommt Kennung, Nummer und die aktuell angezeigte
Reihenfolge des Abschnitts; `testreihenfolge.Reihenfolge` ordnet um und speichert
`logs/testreihenfolge.json`. Erst die Antwort hängt die Zeilen um — sonst gäbe es
zwei Meinungen darüber, wo ein Test steht. Die Nummer gilt INNERHALB des
Bereichs und wandert beim Verschieben mit. Sie ist keine
Ausführungsreihenfolge — `manage.py test` bestimmt die selbst.

**Spaltenordnung** (in `Testtabelle.SPALTEN`, und `testzeiten.js` muss dazu
passen — Test `test_js_kennt_dieselben_spalten`):
Auswahl · Nr. · Kategorie · Bereich · Testcase · Ziel · letzte · Ø · Trend ·
letzte 4 Läufe · Run.

### JS in der Testsuite: `djangobase.testhelfer.Webmodul`

Lädt ein ES-Modul der Seite in Node — spiegelt die Importkette und biegt
absolute `/static/…`-Pfade um (die Node sonst als `A:\static\…` sucht) sowie
`?v=`-Anhänge. Ein Import ins Leere wirft, statt still zu überspringen. Ausnahme
(20.10.2026): ein nackter Paketname der Importkarte (`three/addons/…/X.js`) ist keine
Datei der Seite — ihn löst Node beim Laden auf und wirft dann selbst.

### Konformitätsprüfungen: `djangobase.tests.konform` (21.08.2026)

Neun Testdateien, die im KONSUMENTEN laufen (`manage.py test
djangobase.tests.konform`) und fragen: erbt dieses Projekt djangoBase wirklich?
Alle ohne Datenbank (`SimpleTestCase`, `databases = []`) — geprüft werden
Einstellungen, Vorlagen und Quelltext, nicht Daten.

**Ein Wirt, der kein Konsument ist, sagt das** (18.09.2026): `DJANGOBASE_KONFORM =
False` in seinen Settings — dann überspringen die Klassen auf `konform/basis.py
KonformTest` mit Grund, statt 19 rote Fälle über ein Projekt ohne Vorlagen, Menü
und LOGGING zu melden. So steht es im Prüf-Wirt `A:\tmp_dbhost`. Die
`GegenprobeTest`-Klassen (trifft das Muster das Gemeinte?) laufen überall.

**Was sie durchsuchen dürfen, entscheidet `tests/konform/quellen.py`** — eine
Stelle für alle Prüfer. Draußen bleiben: `TABU`-Ordner (Umgebungen, Caches),
das djangoBase-Paket selbst, `MEDIA_ROOT` und alles aus dem neuen Schlüssel
`DJANGOBASE_KONFORM_AUS` (Pfad-Teilstrings). Gelaufen wird mit `os.walk` und
Ast-Abschnitt VOR dem Abstieg; das Ergebnis liegt im Zwischenspeicher.

Der erste Lauf im `assistant` meldete **199 Verstöße, davon 6 echt**: 111 aus
dem Chrome-Profil eines Verkaufs-Werkzeugs, 56 Vorlagen aus demselben Ordner,
23 JS-Dateien aus der Virensuche-Quarantäne (Dateien, welche die App
UNTERSUCHT). Laufzeit 81 s, weil `rglob` durch 84.442 archivierte Mails lief —
je Suchmuster und je Testmethode erneut. Nach dem Umbau: 102 Tests, **1,0 s**.

Drei Prüfer waren zudem selbst falsch geeicht (alle mit Gegenprobe repariert):

| Fehlalarm | Ursache | Jetzt |
|---|---|---|
| „Seitenleiste leer" | nur `menu` gefragt | `sidebar_template` zählt genauso |
| „Modul nirgends gebunden" | unter `BASE_DIR` gesucht | `tabellen_auto.js` zählt |
| Kontrastfehler in Prosa | `pre|code` im ganzen Dokument | nur `<style>`-Blöcke |

Umgekehrt hatte `test_statik` einen **blinden Fleck**: Es sah nur Adressen, die
selbst auf `.js` enden — `src="{% static 'app/x.js' %}?v=3"` bricht am inneren
Anführungszeichen ab. Damit war die häufigste Django-Schreibweise unsichtbar.
