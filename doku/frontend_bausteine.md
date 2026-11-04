# Frontend-Bausteine: Serverabruf/protokoll.js, Fallen in den Tabellen-Modulen

Aus `CLAUDE.md` ausgelagert am 02.11.2026 (wörtlich). Bei Arbeit an diesem Thema lesen.

## Frontend-Bausteine

### Frontend-Klassen, die dazugehören

`djangobase/static/djangobase/js/serverabruf.js` und `protokoll.js` sind die
**kanonische Fassung** (die Umsteller schreiben Importe auf genau sie).
Konsumenten mit vielen kurzen relativen Importen legen eine Weiterleitung an,
statt zu kopieren:

```js
export { Serverabruf } from '/static/djangobase/js/serverabruf.js';
```

`Serverabruf` prüft `response.ok`, hängt bei Fehlern **Status, Rumpf und
geparstes JSON** an die Ausnahme (`fehler.status/.rumpf/.daten`), setzt den
CSRF-Kopf und kennt `senden`/`formular`/`jsonOderNull`. Cookiename über
`Serverabruf.COOKIENAME` oder `<meta name="csrf-cookie">`.

### Zwei Fallen in den Tabellen-Modulen, beide am 17.08.2026 behoben

`TabellenBreiten` merkte beim Ziehen NUR die angefasste Spalte; nach F5 verteilte
der Browser den Rest neu, und es sah aus wie „nicht gemerkt". Jetzt speichert
`_merkenAlle()` die ganze Gruppe (gelesen aus einer SICHTBAREN Tabelle — in einem
`display:none`-Panel ist jede Breite 0).

`TabellenSortierung` merkte nur den Spalten-INDEX. Kommen Spalten dazu, zeigt er
auf etwas anderes: Nach dem Einfügen von „Nr." und „Kategorie" sortierte die
Seite nach „Nr." (einer `sortAus`-Spalte), und die Bereichs-Abschnitte
verschwanden. Jetzt wird der Spalten-**Key** mitgespeichert, der Index daraus neu
bestimmt, und ein Eintrag auf eine `sortAus`-Spalte wird verworfen.

Regeln von `jsbefunde` stehen in `skills2/jsregeln.py` (eine Klasse je Regel),
der Klammerzähler in `skills2/jsklammern.py` (Template-Strings über mehrere
Zeilen, `} catch (e) {`).

Tests: `djangobase/tests/unit/test_skills2_frontend.py` — je Werkzeug ein Fund
UND eine Gegenprobe, dazu die vier Fehlalarme, die beim Bau aufgefallen sind.
