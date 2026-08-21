/* Eine djangoBase-Tabelle im Browser bauen — das Gegenstück zu `_tabelle.html`.
 * ============================================================================
 * DER AUFTRAG (Edgar, 21.08.2026)
 *
 *     „javascript soll auch diese Tabellen mit dem djangoBase tabellen Template
 *      bauen"
 *
 * `_tabelle.html` ist für Zeilen gedacht, die der View fertig liefert. Wer seine
 * Tabelle im Browser aufbaut, hatte bis hierher nur den Hinweis „benutzt die
 * beiden JS-Module direkt" — und baute sein Markup selbst. In ShortLongX tun das
 * 18 Module, jedes mit eigener Schreibweise: mal `class="stats sortable
 * db-rahmen"`, mal `class="results bucket-tbl"`, mal ganz ohne. Was in der
 * einen Tabelle geht, fehlt in der nächsten.
 *
 * Dieses Modul baut dasselbe Markup wie die Vorlage, aus denselben Angaben:
 *
 *     import { dbTabelle } from '/static/djangobase/js/tabelle_bauen.js';
 *
 *     el.innerHTML = dbTabelle({
 *       key: 'meine-seite',
 *       spalten: [{label: 'Modell', key: 'modell'},
 *                 {label: 'Wert', key: 'wert', num: true}],
 *       zeilen: daten.map(d => ({zellen: [
 *         {html: d.name},
 *         {html: de(d.wert), sort: d.wert, klasse: d.wert < 0 ? 'neg' : 'pos'},
 *       ]})),
 *       leer: 'keine Einträge',
 *     });
 *
 * Angebunden wird von selbst: `tabellen_auto.js` sieht die neue Tabelle über
 * seinen MutationObserver und bindet Sortierung und Spaltenbreiten an. Wer
 * sofort binden will, ruft `tabellenBinden(el)`.
 *
 * DIE STRUKTUR IST DIESELBE WIE IN DER VORLAGE
 * --------------------------------------------
 * Gleiche Klassen (`db-tabelle sortable`), gleicher Rahmen
 * (`db-tabelle-rahmen`), gleiche Attribute (`data-sort-key`, `data-key`,
 * `data-sort`, `data-sort-aus`). Damit greifen dieselben Stile und dieselben
 * Module — und der Konformitätstest sieht dieselbe Tabelle wie bei einer
 * server-gerenderten.
 */

/** HTML-Text sichern. Zellen dürfen Markup tragen (`html`), Beschriftungen und
 *  Attribute nicht — dort käme es aus Daten und wäre eine offene Tür. */
export function esc(text) {
  return String(text == null ? '' : text)
    .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;').replace(/'/g, '&#39;');
}

function attribut(name, wert) {
  return (wert === undefined || wert === null || wert === '')
    ? '' : ` ${name}="${esc(wert)}"`;
}

/** Die Kopfzeile.
 *
 *  @param spalten [{label, key, num, titel, sortAus}] — `label` darf HTML sein
 *         (die Vorlage erlaubt es auch: dort steht `|safe`).
 */
function kopf(spalten) {
  const zellen = (spalten || []).map((s, i) => {
    const klassen = [s.num ? 'num' : '', s.klasse || ''].filter(Boolean).join(' ');
    return '<th'
      + (klassen ? ` class="${esc(klassen)}"` : '')
      + attribut('data-key', s.key != null ? s.key : String(i))
      + attribut('title', s.titel)
      + (s.sortAus ? ' data-sort-aus="1"' : '')
      + '>' + (s.label == null ? '' : s.label) + '</th>';
  }).join('');
  return `<thead><tr>${zellen}</tr></thead>`;
}

/** Eine Zelle: `html` wird übernommen, `text` wird gesichert. */
function zelle(z) {
  if (z == null) return '<td></td>';
  if (typeof z !== 'object') return `<td>${esc(z)}</td>`;
  const klassen = [z.num ? 'num' : '', z.klasse || ''].filter(Boolean).join(' ');
  return '<td'
    + (klassen ? ` class="${esc(klassen)}"` : '')
    // ROHWERT ZUM SORTIEREN: Ohne ihn liest das Sortier-Modul den Text. Es
    // erkennt deutsche Zahlen und Brüche, aber „1.234,50 €" neben „—" bleibt
    // Raten. Wer den Wert hat, gibt ihn mit.
    + attribut('data-sort', z.sort)
    + attribut('title', z.titel)
    + '>' + (z.html != null ? z.html : esc(z.text)) + '</td>';
}

function zeile(z) {
  if (Array.isArray(z)) z = { zellen: z };
  const inhalt = (z.zellen || []).map(zelle).join('');
  return '<tr'
    + (z.klasse ? ` class="${esc(z.klasse)}"` : '')
    + attribut('data-id', z.id)
    + (z.gruppe ? ' data-gruppe="1"' : '')
    + `>${inhalt}</tr>`;
}

/**
 *  Eine vollständige djangoBase-Tabelle als HTML-Text.
 *
 *  @param key     Pflicht: Speicher-Schlüssel für Sortierung und Spaltenbreiten.
 *                 Er muss im ganzen Projekt eindeutig sein — zwei Tabellen mit
 *                 demselben Schlüssel teilen sich die gemerkten Breiten, und
 *                 die schmalere übernimmt die der breiteren (belegt 21.08.2026).
 *  @param spalten [{label, key, num, titel, sortAus}]
 *  @param zeilen  [{zellen: [...], klasse, id, gruppe}] oder [[zelle, …]]
 *  @param leer    Text, wenn `zeilen` leer ist
 *  @param klasse  zusätzliche Klassen der <table>
 *  @param rahmen  false = ohne den scrollenden Rahmen
 */
export function dbTabelle({ key, spalten, zeilen, leer, klasse, rahmen } = {}) {
  if (!key) {
    // Kein stiller Rückfall: Ohne Schlüssel merkt sich die Tabelle nichts, und
    // das fiele erst auf, wenn jemand vergeblich eine Spalte zieht.
    throw new Error('dbTabelle: „key" fehlt (Speicher-Schlüssel der Tabelle)');
  }
  if (!(zeilen || []).length && leer) {
    return `<p class="ts-empty">${esc(leer)}</p>`;
  }
  const tabelle = '<table'
    + ` class="db-tabelle sortable${klasse ? ' ' + esc(klasse) : ''}"`
    + ` data-sort-key="${esc(key)}">`
    + kopf(spalten)
    + `<tbody>${(zeilen || []).map(zeile).join('')}</tbody>`
    + '</table>';
  return rahmen === false ? tabelle
                          : `<div class="db-tabelle-rahmen">${tabelle}</div>`;
}

/** Tabelle bauen UND einsetzen — der übliche Fall in einem Schritt.
 *
 *  Bindet anschließend gleich an, statt auf den Beobachter in
 *  `tabellen_auto.js` zu warten: Wer direkt danach Spaltenbreiten setzen oder
 *  sortieren will, fände sonst eine noch ungebundene Tabelle vor.
 */
export async function dbTabelleSetzen(ziel, angaben) {
  const el = (typeof ziel === 'string') ? document.querySelector(ziel) : ziel;
  if (!el) return null;
  el.innerHTML = dbTabelle(angaben);
  try {
    const mod = await import('/static/djangobase/js/tabellen_auto.js'
                             + new URL(import.meta.url).search);
    mod.tabellenBinden(el);
  } catch (e) { /* der Beobachter holt es gleich nach */ }
  return el.querySelector('table');
}
