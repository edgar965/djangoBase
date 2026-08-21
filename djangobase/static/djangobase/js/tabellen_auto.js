/* Tabellen automatisch anbinden — Sortierung und ziehbare Spaltenbreiten.
 * ======================================================================
 * DER BEFUND (21.08.2026, Konformitätsprüfung)
 *
 *     6 von 91 Datentabellen tragen kein class="sortable"
 *     91 von 91 tragen kein data-sort-key
 *
 * Die zweite Zahl ist die interessante: In ShortLongX gab es 14 Stellen, die
 * `TabellenSortierung`/`TabellenBreiten` je Seite von Hand anbinden — und
 * keine einzige Tabelle mit gemerkten Spaltenbreiten. Der Grund ist nicht
 * Nachlässigkeit, sondern Aufwand: Wer eine neue Seite baut, denkt an die
 * Daten, nicht an zwei Zeilen Anbindung am Ende jeder Datei.
 *
 * DESHALB HIER STATT DORT
 * -----------------------
 * Dieses Modul bindet beim Laden ALLE passenden Tabellen der Seite an. Es kommt
 * über dieselbe Middleware wie die Testaufzeichnung, liegt also auf jeder Seite
 * jedes djangoBase-Projekts. Damit ist eine Tabelle konform, sobald sie
 * `class="sortable"` trägt — der Rest passiert von selbst.
 *
 * DER SCHLÜSSEL WIRD ABGELEITET, WENN KEINER DASTEHT
 * --------------------------------------------------
 * `TabellenBreiten` merkt Breiten unter einem Schlüssel. Fehlt `data-sort-key`,
 * wird einer gebaut — aus der `id` der Tabelle, sonst aus Seitenpfad und
 * Position. Beides ist stabil über Neuladen hinweg; eine Tabelle, die ihre
 * Position wechselt, verliert ihre gemerkten Breiten, und das ist das mildeste
 * denkbare Verhalten.
 *
 * Ein ausdrückliches `data-sort-key` hat immer Vorrang — es überlebt auch ein
 * Umsortieren der Seite.
 */
import { TabellenSortierung } from '/static/djangobase/js/tabellen_sortierung.js';
import { TabellenBreiten } from '/static/djangobase/js/tabellen_breiten.js';

/** Ein stabiler Speicher-Schlüssel für diese Tabelle. */
function schluessel(tabelle, nr) {
  if (tabelle.dataset.sortKey) return tabelle.dataset.sortKey;
  if (tabelle.id) return 'auto-' + tabelle.id;
  // Seitenpfad ohne Query: Ein Datumsfilter in der Adresse darf die gemerkten
  // Breiten nicht wegwerfen.
  return 'auto' + location.pathname.replace(/[^\w]+/g, '-') + '-' + nr;
}

/** Alle Tabellen unterhalb von `wurzel` anbinden.
 *
 *  Mehrfach aufrufbar: Seiten, die ihre Tabellen nachladen, rufen es nach dem
 *  Zeichnen erneut. `TabellenSortierung` und `TabellenBreiten` erkennen beide,
 *  was sie schon gebunden haben.
 */
export function tabellenBinden(wurzel) {
  const w = wurzel || document;
  try {
    TabellenSortierung.binden(w);
  } catch (e) {
    // Eine kaputte Anbindung darf die Seite nicht mitnehmen - die Tabelle
    // funktioniert ohne Sortierung weiter.
  }
  w.querySelectorAll('table.sortable, table[data-sort-key]').forEach((t, nr) => {
    if (t.dataset.djbGebunden === '1') return;
    t.dataset.djbGebunden = '1';
    const k = schluessel(t, nr);
    if (!t.dataset.sortKey) t.dataset.sortKey = k;
    try {
      new TabellenBreiten([t], k).binden();
    } catch (e) { /* siehe oben */ }
  });
}

// Auch nachgeladene Tabellen erwischen: Wer seine Zeilen per fetch holt, ruft
// `tabellenBinden()` entweder selbst - oder dieser Beobachter tut es.
function beobachten() {
  if (typeof MutationObserver === 'undefined' || !document.body) return;
  let geplant = false;
  new MutationObserver((aenderungen) => {
    if (geplant) return;
    const neu = aenderungen.some(a => [...a.addedNodes].some(
      n => n.nodeType === 1 && (n.matches?.('table') || n.querySelector?.('table'))));
    if (!neu) return;
    geplant = true;
    // Gebündelt: Eine Tabelle, die zeilenweise wächst, löste sonst hundert
    // Bindungsläufe aus.
    setTimeout(() => { geplant = false; tabellenBinden(); }, 120);
  }).observe(document.body, { childList: true, subtree: true });
}

function los() {
  tabellenBinden();
  beobachten();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', los);
} else {
  los();
}

export { schluessel };
