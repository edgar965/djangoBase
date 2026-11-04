# Hilfe → Jobs: die Ablauf-Übersicht

Aus `CLAUDE.md` ausgelagert am 02.11.2026 (wörtlich). Bei Arbeit an diesem Thema lesen.

## Hilfe → Jobs: die Ablauf-Übersicht (26.08.2026)

Die Seite hat **zwei Teile mit verschiedenen Fragen**:

| Teil | Frage | Quelle |
|---|---|---|
| oben (alt) | Was tut der Daemon **gerade**? | `djangobase.jobs` — Registry, im Speicher, vom Projekt angemeldet |
| unten (neu) | Was ist **passiert**? | `Jobkatalog` + `Jobverlauf` — Dateien, überleben den Neustart |

Anlass war die Frage, ob ein iPaaS-Werkzeug (n8n, Activepieces) nötig ist.
Antwort: Was fehlte, war keine Ablauf-**Steuerung**, sondern die
Ablauf-**Übersicht** — „welcher Job wann zuletzt lief, wie lange er
brauchte und ob er Fehler warf".

**Vier Klassen, vier Zuständigkeiten:**

- `joberkennung.Joberkennung` — findet die Jobs selbst: die
  Management-Commands der Projekt-Apps plus die angemeldeten Daemons.
  Django-eigene Befehle (`migrate`, `runserver`, …), Namen mit
  führendem `_` und `DJANGOBASE["jobs_ausschluss"]` fallen heraus.
- `jobkatalog.Jobkatalog` — merkt den Bestand in
  `logs/jobkatalog.json`, **Frist ein Tag**. Grund: Für die
  Beschreibung wird jede Befehlsklasse importiert (assistant: 93).
  Der Knopf „Jetzt aktualisieren" erzwingt es sofort.
- `jobverlauf.Jobverlauf` — `logs/joblaeufe.jsonl`, **eine Zeile je
  Lauf**. Anhängen statt Umschreiben, weil Commands eigene Prozesse
  sind und gleichzeitig schreiben; ein Umschreiber würde den anderen
  verlieren.
- `jobuebersicht.Jobuebersicht` — führt beides zusammen. Gescheiterte
  zuerst, dann die Gelaufenen, dann die nie Gelaufenen.

**Die Aufzeichnung** (`jobaufzeichnung.Jobaufzeichnung`) legt sich in
`AppConfig.ready()` um `BaseCommand.execute` — einmal, für alle
Befehle, auch für künftige. Sie **misst nur**: jede Ausnahme wird
notiert und unverändert weitergereicht, jeder Fehler beim Aufzeichnen
verschluckt. Abschalten: `DJANGOBASE_JOBAUFZEICHNUNG = False`.

**Keine Migration** — bewusst. djangoBase steckt in sechs Projekten;
eine Tabelle müsste jedes erst migrieren. Dateien neben den Logs gehen
denselben Weg wie `logs/testhistorie.json`.

Prüfungen: `tests/unit/test_job{verlauf,katalog,uebersicht,aufzeichnung}.py`
— 61 Stück, nach Kriterium 19 („BDD ohne Gherkin") geschrieben: Die
Klasse nennt die Ausgangslage (`EinBestandVonGestern`), die Methode das
erwartete Verhalten (`test_wird_beim_lesen_neu_ermittelt`). Helfer in
`tests/unit/jobwerkzeug.py`.
