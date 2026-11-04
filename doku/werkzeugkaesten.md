# Werkzeugkästen skills / skills2 / umbau, Review-Werkzeug, Bauformen aus gunSlinger, ruff

Aus `CLAUDE.md` ausgelagert am 02.11.2026 (wörtlich). Bei Arbeit an diesem Thema lesen.

## Werkzeugkästen (skills / skills2 / umbau)

Drei Pakete, drei Zwecke — nicht vermischen:

| Paket | Was drin ist | Aufruf |
|---|---|---|
| `djangobase/skills/` | 12 Python-/Endpunkt-Werkzeuge (3DTools-Durchgang) | Hilfe→Skills |
| `djangobase/skills2/` | Python-Prüfer + **6 Frontend-Prüfer** (JS/Vorlagen) | Hilfe→Skills2 |
| `djangobase/umbau/` | Werkzeuge, die Quelltext **ändern** — kein Web-Knopf | `python -m djangobase.umbau.<name>` |

### Die sechs Frontend-Prüfer in skills2 (16.08.2026, aus 3DTools)

| Kennung | Findet | Belegter Fall |
|---|---|---|
| `jssyntax` | kaputte ES-Module (kopiert nach `.mjs`, dann `node --check`) | 3 Dateien mit Import mitten in einem Import — als `.js` grün, als `.mjs` rot |
| `jswaisen` | Module, die niemand lädt; Importe ins Leere | 3 verwaiste Module, die Funktionen anmeldeten → 3 tote Seitenzweige |
| `jsregistrierung` | `fn.x()` ohne `fn.x = …` | 4 Namen gerufen, nie angemeldet |
| `jsfaenger` | werfende Server-Abrufe ohne `try` | 16 von 101; zwei direkt hinter einem Nutzerklick |
| `jsfunktionen` | Funktionen ab N Zeilen (`skills2_funktionsgrenze`) | `loadClothUI` mit 245 Zeilen |
| `jsbefunde` | 10 zählbare Auffälligkeiten in `.js`/`.html` | 3.290 Befunde erhoben, davon `.ok`-Prüfung 71→0, `console.log` 144→0, `var` 157→0 |
| `jsstumm` | verschluckte Rückmeldungen: Meldung hängt an einem fehlenden Element, `catch` ohne Inhalt, `.catch(() => {})`, `if (!antwort.ok) return;` | assistant 67 → 0. Anlass: ein Sync-Knopf gab 31 s keine Rückmeldung, weil `if (!el) return;` in der Anzeige-Methode stand (17.08.2026) |

### Fixer, der schreibt: `fix-ausnahme` (17.08.2026, aus assistant)

Setzt in stumme `except`-Blöcke einen Log-Aufruf — Stufe aus dem Code abgeleitet
(`debug` bei `continue` in Schleifen, `warning` bei erwarteten Typen wie
ValueError/KeyError, `exception` mit Traceback bei `except Exception`) — und
`# stumm gewollt: <Grund>` bei ImportError/KeyboardInterrupt. Die Meldung nennt
nur Funktionsname und Typ, nie Variablen: So kann durch den Umbau nichts
Geheimes ins Log geraten. Im Projekt assistant: 636 Blöcke in 205 Modulen,
`protokoll` 656 → 0, danach 649 Tests grün.

**Netz (nicht verhandelbar):** `compile()`, „`protokoll` sieht hier weniger", UND
die Frage, ob der Name `logging` modulweit gebunden ist. Der letzte Punkt kostete
einen Vorfall: In `mail/models.py` stand weiter unten `import logging as
_logging`; der Fixer hielt das für den Import, die Datei kompilierte, und die
Anwendung startete nicht mehr (`NameError`).

### Hilfe → Review: Werkzeug statt Modell (31.08.2026)

`review_partner` kennt neben `ziel: "lokal"|"online"` jetzt **`ziel: "werkzeug"`**
(`djangobase/review/werkzeug_partner.py`). Statt eines Chat-Endpunkts wird ein
lokales Programm gestartet, das den **Git-Stand** liest und Befunde ausgibt —
eingerichtet ist die CodeRabbit-CLI in shortlongx.

```python
{"slug": "coderabbit", "name": "CodeRabbit", "ziel": "werkzeug",
 "modell": "CodeRabbit CLI",
 "befehl": [r"C:\Users\<du>\AppData\Local\Programs\coderabbit\cr.exe", "review"],
 "wurzel": r"A:\meinprojekt",          # das Repository, nicht review_wurzel
 "auswahlen": [{"wert": "uncommitted", "name": "Arbeitsstand",
                "argumente": ["--uncommitted"]}, …],
 "umgebung": {"LOCALAPPDATA": r"C:\Users\<du>\AppData\Local"},
 "schluessel_datei": r"C:\Users\<du>\.coderabbit_key",   # Rückfall
 "schluessel_argument": "--api-key"}
```

Vier Dinge, die dabei Zeit gekostet haben und in jedem Projekt wiederkommen:

- **Bereiche gelten nicht.** Das Werkzeug liest den Diff, nicht die
  Bereichsdateien. Die Seite blendet Bereiche und Nachfass-Vorlagen aus und
  zeigt stattdessen die Auswahl, WELCHER Stand geprüft wird. Ein Häkchen, das
  nichts bewirkt, ist schlimmer als keins.
- **EIN Werkzeug, EIN Faden** — auch bei drei angehakten Bereichen. Sonst
  dreimal dasselbe Ergebnis und dreimal Kontingent (CodeRabbit frei: 3 Läufe/h,
  Pro 5, Pro+ 10).
- **Läuft der Server als Dienst, ist `Path.home()` das Dienstkonto-Profil**
  (`C:\Windows\system32\config\systemprofile`). Befehlspfade nie daraus
  ableiten, und die Anmeldung des Werkzeugs liegt dort auch nicht — dafür
  `umgebung` mit `LOCALAPPDATA` auf das echte Profil.
- **Aus dem Browser kommt nur der Schlüssel einer vorbereiteten Auswahl**, nie
  ein Argument. Der Befehl steht ausschließlich in der Konfiguration.

### Drei Bauformen aus gunSlinger (18.09.2026)

Anlass: `A:\gunSlinger` (pytest, kein Django) hatte drei Dinge, die unsere
Django-Projekte nur als Text kannten. Ansage Edgar: „baue das in djangoBase ein".

| Bauform | Datei | Was sie tut |
|---|---|---|
| **Strukturregeln als Test** | `strukturtests.py` | `from djangobase.strukturtests import *` in `<app>/tests/automated/test_struktur.py`. Macht aus den Befunden von `skills/dateigroesse` und `skills/klassenjedatei` Zusicherungen — **keine eigene Eichung**, die Fehlalarm-Lehren der Werkzeuge gelten weiter. Auf Wunsch `test_je_klasse` (gunSlinger-Regel). **Ratsche:** `DJANGOBASE["struktur"]["bestand"]` = `{"groesse": [...], "klassen": [...], "tests": [...]}` — bekannte Verstöße, ausdrücklich; rot für alles Neue UND für jeden Eintrag, der kein Verstoß mehr ist. Die Liste kann nur schrumpfen. |
| **Netzverbot im Prüflauf** | `netzsperre.py`, `testlaeufer.py` | **Nur im Prüflauf** (19.09.2026): `tests/__init__.py` richtet Sperre und Ablageumleitung nur ein, wenn `im_prueflauf()` wahr ist (`_TestState.saved_data`) — Hilfe → Tests importiert das Paket über `build_suite` IM SERVER, und der hatte danach kein Netz mehr (SchweizerMakler, Immobiliensuche). Sitzt an `socket.socket.connect` (trifft httpx, requests, smtplib, imaplib) UND an `sock_connect` der asyncio-Loops (der Proactor-Loop auf Windows geht am Socket vorbei). Loopback bleibt offen (Postgres, LiveServer). Ausweg für den einen Fall: `with Netzsperre.erlaubt():`; dauerhaft `DJANGOBASE_NETZ_ERLAUBT = [...]`; je Lauf aus mit `DJANGOBASE_NETZSPERRE = False`. Für Konsumenten: `TEST_RUNNER = "djangobase.testlaeufer.Testlaeufer"` (richtet auch die Ablageumleitung ein); wer einen eigenen Läufer hat (assistant), erbt davon oder ruft `Netzsperre.einrichten()` in `setup_test_environment`. djangoBase-eigene Suite: eingehängt in `tests/__init__.py`, 1805 Tests ohne einen gesperrten Zugriff. |
| **Zeit als injizierbare Pause** | `pause.py` | `Pause().warten(s)` statt `time.sleep(s)`; `Pause.sofort()` im Test wartet nicht, zählt aber (`gewartet`, `gesamt`); `abbrechen()` beendet auch eine 90-s-Pause augenblicklich (Event). Erste Nutzer: `store._Sperre` (Test läuft jetzt mit allen 20 Versuchen statt heruntergedrehten 2) und `uebersetzung`. Neue Wartezeit im Paket nimmt diese Klasse, nicht `time.sleep`. |

Warum ein Läufer und keine Basisklasse: Eine Basisklasse erreicht nur, wer von
ihr erbt. Genau der Prüffall mit `unittest.TestCase` ist der, der nach draußen
telefoniert. `setup_test_environment` läuft einmal je Prozess, für alle.

### ruff als Werkzeug (18.09.2026)

Vierte Bauform aus gunSlinger: `skills/ruffbefunde.py` (Hilfe → Skills → „ruff",
direkt hinter `code-qualitaet`) fährt `ruff check` und `ruff format --check`
über dieselbe Dateimenge wie jedes andere Werkzeug (Ausschlussliste,
`.gitignore`, in Stapeln, weil Windows die Befehlszeile bei 32 k kappt) und
ordnet die Antworten ein: undefinierte/doppelte Namen und Syntaxfehler
`fehler`, B/UP/F-Rest `warnung`, E/W/I und „ungeformt" `hinweis`. F401 und
F541 werden nur gezählt — die führen `tote-importe` und `fix-fzeichenkette`.

**Regeln:** eigene Konfiguration des Projekts (`ruff.toml`, `.ruff.toml`,
`[tool.ruff]` in `pyproject.toml`) schlägt die Vorgabe **`djangobase/ruff_vorgabe.toml`**
(110 Zeichen, E/W/F/I/B/UP, Migrationen/`__init__`/Settings ausgenommen). Die
Vorgabe hat bewusst KEIN `target-version`: mit festem `py310` meldete ruff im
assistant (Python 3.14) 58 „Syntaxfehler" — f-String-Umbrüche seit 3.12. Das
Werkzeug übergibt die Version des laufenden Interpreters. UP009/UP025/UP031
(`coding`-Kopf, `u""`, `%`-Formatierung) sind aus: 86–96 % aller Meldungen in
assistant/HumanBodyWeb/djangoBase, eine Hausschrift, die keiner beanstandet hat.

Was sonst noch dazugehört: `ruff` steht im Extra `codequalitaet` und muss in der
Umgebung des **Projekts** liegen (`sys.executable -m ruff`); fehlt es, ist das
Ergebnis ein `FEHLER` mit Installationshinweis, kein leeres Grün — und der
Anlassfall-Check übernimmt seit heute den Hinweis „FEHLER: …" eines
Befund-Werkzeugs als Grund statt „blind: 0 statt 2" zu melden.
Prüfungen: `tests/unit/test_skills_ruff.py` (drei Zustände wie bei
`code-qualitaet`; Ausgabeform von `format --check` bis 0.15 und ab 0.16).

**djangoBase selbst ist seit dem 18.09.2026 ruff-sauber** (`ruff check .` und
`ruff format --check .` über 444 Dateien, Konfiguration `[tool.ruff]` in
`pyproject.toml` → `extend = "djangobase/ruff_vorgabe.toml"`). Beides gehört vor
jeden Commit; ruff liegt im gunSlinger-venv oder nach `pip install ruff` im
Prüf-Wirt. Die Vorgabe heißt bewusst NICHT `ruff.toml`: Eine Datei dieses
Namens im Paketordner hätte ruff als nächstgelegene Konfiguration für das
Paket genommen und die `pyproject.toml` darüber ignoriert (so geschehen — die
Ausnahme für `ki/messungen.py` griff nicht). Ergänzungen dort über
`[tool.ruff.lint.extend-per-file-ignores]`, sonst ersetzen sie die Ausnahmen
der Vorgabe. Was der Umbau nebenbei fand: 18 tote Importe, 35 Variablen namens
`l`, ein `raise` ohne `from`, ein `yield`-Schleifchen — alles behoben.

**Konsumenten (19.09.2026):** WalkHop, Roomguest, HumanBodyWeb, shortlongx und
assistant haben je eine `ruff.toml` (`extend` auf die Vorgabe, `target-version`
des Interpreters) und sind formatiert; die sicheren Fixes sind eingespielt.
Zwei Lehren daraus: (1) **`ruff check --fix` entfernt keine Importe mehr**
(`unfixable = ["F401"]` in der Vorgabe) — in shortlongx war
`from .assets import ASSETS` ein Re-Export, `manage.py check` starb mit
ImportError. (2) **Anführungszeichen sind Projektsache**: HumanBodyWeb und
assistant schreiben einfache und haben `[format] quote-style = "single"` in
ihrer `ruff.toml`; die Vorgabe (doppelt) brach dort 13 Tests, die den Quelltext
lesen und `'…'`-Ausdrücke suchen. Vor einem Format-Lauf über ein Projekt also:
Quote-Stil messen (`git grep -c "'"` gegen `'"'`) und die Suite danach fahren —
oder, wo Tests verboten sind (shortlongx), wenigstens prüfen, ob Zeichenketten
aus Tests noch im Quelltext vorkommen.
