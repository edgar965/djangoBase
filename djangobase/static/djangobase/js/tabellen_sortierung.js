/* TabellenSortierung - klickbare Tabellenköpfe mit IMMER sichtbaren Pfeilen.
   ==========================================================================
   Für gewöhnliche <table>-Elemente, deren Zeilen schon im DOM stehen - egal ob
   vom Server gerendert oder von JavaScript gebaut. Sortiert wird an Ort und
   Stelle (die <tr> werden umgehängt), es wird also nichts neu gezeichnet und
   keine Datenquelle gebraucht.

   ANSCHLUSS: <table class="sortable" data-sort-key="ki-frei">
   Ohne data-sort-key wird die Sortierung nicht gemerkt - alles andere geht.

       import { TabellenSortierung } from '/static/djangobase/js/tabellen_sortierung.js';
       TabellenSortierung.binden();          // einmal je Seite

   WARUM DIE PFEILE IMMER STEHEN (Ansage Edgar, 11.08.2026)
   -------------------------------------------------------
   Eine Tabelle, die man sortieren kann, sieht ohne Pfeil genauso aus wie eine,
   die man nicht sortieren kann. Deshalb trägt JEDE sortierbare Spalte ein
   gedimmtes ⇅, und die aktive Spalte ein volles ▲/▼.

   WONACH SORTIERT WIRD - in dieser Reihenfolge
   --------------------------------------------
     1. ``data-sort`` an der Zelle (<td data-sort="17.4">17,4 GB</td>)
        Der verlässliche Weg: Der Server schreibt den Rohwert hin, und die
        Anzeige darf beliebig formatiert sein.
     2. Der Zelltext, als DEUTSCHE Zahl gelesen ("1.234,5" -> 1234.5). Erkennt
        sie eine Zahl in BEIDEN verglichenen Zellen, wird numerisch sortiert.
     3. Sonst Text, über localeCompare mit numeric:true ("Kapitel 9" < "Kapitel 10").

   Leere Zellen landen IMMER am Ende - in beiden Richtungen. Ein Feld ohne Wert
   ist keine kleine Zahl; stünde es beim Aufsteigend-Sortieren oben, wäre die
   erste Bildschirmseite voll mit Zeilen ohne Inhalt.

   TEXTAUSWAHL GEHT VOR SORTIEREN: Hat der Nutzer gerade Text markiert, wird der
   Klick verworfen (Befund shortlongx 04.08.2026 - der Neuaufbau warf die Auswahl
   weg, und Kopieren aus den Tabellen war unmöglich).

   Verträgt sich mit TabellenBreiten: Der Ziehgriff wird beim Neuschreiben der
   Kopfzelle gerettet, und ein Klick auf den Griff sortiert nicht mit. */

const SPEICHER = 'dbTabSort:';

export class TabellenSortierung {

  /** Alle sortierbaren Tabellen unterhalb von ``wurzel`` anbinden.
   *
   *  Der Klick-Handler hängt am Dokument (Delegation): Tabellen, die erst
   *  später entstehen, funktionieren dadurch ohne erneutes Binden. Mehrfaches
   *  Aufrufen ist harmlos - der Handler wird nur einmal gesetzt. */
  static binden(wurzel) {
    const w = wurzel || document;
    if (!TabellenSortierung._handler) {
      TabellenSortierung._handler = e => {
        // Markieren geht vor Sortieren.
        const sel = window.getSelection && window.getSelection();
        if (sel && String(sel).length) return;
        if (e.target.closest('.tb-griff')) return;      // Breiten-Ziehen
        const th = e.target.closest('table.sortable thead th');
        if (!th || th.dataset.sortAus !== undefined) return;
        // NUR die unterste Kopfzeile sortiert. Tabellen mit einer GRUPPEN-Zeile
        // darüber (Walk-Forward: „Ergebnis beim Suchen" spannt mehrere Spalten)
        // haben dort th-Elemente mit colspan - deren Index in der Zeile ist
        // nicht der Spaltenindex, ein Klick hätte nach der falschen Spalte
        // sortiert (Befund beim Umbau 11.08.2026).
        if (th.parentNode !== TabellenSortierung._kopfzeile(th.closest('table'))) return;
        TabellenSortierung.sortieren(th);
      };
      document.addEventListener('click', TabellenSortierung._handler);
    }
    w.querySelectorAll('table.sortable').forEach(t => {
      TabellenSortierung._gemerktesAnwenden(t);
      TabellenSortierung.pfeile(t);
      TabellenSortierung.hochkant(t);
    });
  }

  /** Frueher: Ueberschriften hochkant stellen. ZURUECKGENOMMEN am 11.08.2026.
   *
   *  Die Idee war, zu breite Beschriftungen zu drehen statt sie in die
   *  Nachbarspalte laufen zu lassen. Das Ergebnis war schlimmer als das
   *  Problem: Die Kopfzeile richtet sich nach der laengsten gedrehten
   *  Beschriftung und wuchs auf ueber 200 px, mehrzeilige Koepfe („Platte"
   *  ueber „wenn selbst betrieben") standen nebeneinander statt untereinander.
   *
   *  Geloest wird es jetzt im CSS - die Ueberschrift bricht um. Die Methode
   *  bleibt als leerer Aufruf stehen, weil TabellenBreiten sie nach jedem
   *  Ziehen ruft; sie zu entfernen haette dort einen Fehler ausgeloest. */
  static hochkant(_tabelle) {}

  /** Die Zeile mit den ECHTEN Spaltenköpfen: die UNTERSTE des <thead>.
   *
   *  Darüber können Gruppen-Zeilen stehen (th mit colspan). Nur die unterste
   *  Zeile hat je Spalte genau eine Zelle - nur dort stimmt der Index. */
  static _kopfzeile(tabelle) {
    const k = tabelle && tabelle.tHead;
    return (k && k.rows.length) ? k.rows[k.rows.length - 1] : null;
  }

  /** Pfeile in alle Kopfzellen schreiben - ⇅ neutral, ▲/▼ für die aktive Spalte. */
  static pfeile(tabelle) {
    const kopf = TabellenSortierung._kopfzeile(tabelle);
    if (!kopf) return;
    const aktiv = tabelle.dataset.sortIdx === undefined ? -1 : parseInt(tabelle.dataset.sortIdx, 10);
    const auf = tabelle.dataset.sortDir !== 'desc';
    [...kopf.cells].forEach((th, i) => {
      if (th.dataset.sortAus !== undefined) return;    // Spalte ausdrücklich nicht sortierbar
      let span = th.querySelector('.tsort-pfeil');
      if (!span) {
        span = document.createElement('span');
        span.className = 'tsort-pfeil';
        // DIREKT HINTER DIE BESCHRIFTUNG (Ansage 11.08.2026), also in die
        // Inhalts-Hülle, sofern es sie schon gibt: Dann wandert der Pfeil beim
        // Hochkantstellen mit dem Text mit, statt am Zellenrand zurückzubleiben.
        // Sonst vor den Ziehgriff, damit der am rechten Rand bleibt.
        const huelle = th.querySelector(':scope > .tsort-inhalt');
        const griff = th.querySelector('.tb-griff');
        if (huelle) huelle.appendChild(span);
        else if (griff) th.insertBefore(span, griff);
        else th.appendChild(span);
      }
      // EINE Symbolfamilie (Meldung 11.08.2026: „das ist doch ein anderes Pfeil
      // icon"): Vorher stand neben dem schlanken Doppelpfeil ⇅ ein GEFUELLTES
      // Dreieck ▲ - zwei verschiedene Schriftfamilien nebeneinander, und das
      // Dreieck wirkte dadurch doppelt so gross, obwohl beide dieselbe
      // Punktgroesse hatten. Jetzt sind alle drei Zeichen Linienpfeile.
      const ist = (i === aktiv);
      span.textContent = ist ? (auf ? '↑' : '↓') : '↕';
      span.classList.toggle('aktiv', ist);
      th.classList.add('tsort-kopf');
    });
  }

  /** Nach der Spalte dieser Kopfzelle sortieren; erneuter Klick dreht um. */
  static sortieren(th) {
    const tabelle = th.closest('table');
    const koerper = tabelle && tabelle.tBodies[0];
    if (!koerper) return;
    const idx = [...th.parentNode.children].indexOf(th);
    const vorher = tabelle.dataset.sortIdx === undefined ? -1 : parseInt(tabelle.dataset.sortIdx, 10);
    // Gleiche Spalte -> Richtung drehen. Neue Spalte -> aufsteigend beginnen.
    const auf = (idx === vorher) ? tabelle.dataset.sortDir === 'desc' : true;
    TabellenSortierung._anwenden(tabelle, idx, auf);
    TabellenSortierung._merken(tabelle, idx, auf);
    TabellenSortierung.pfeile(tabelle);
  }

  // ------------------------------------------------------------- Mechanik

  static _wert(zelle) {
    if (!zelle) return null;
    // 1. Rohwert vom Server
    if (zelle.dataset && zelle.dataset.sort !== undefined) {
      const roh = zelle.dataset.sort;
      if (roh === '') return null;
      // ÜBER _zahl, NICHT über parseFloat (Befund 11.08.2026): Django rendert
      // Kommazahlen mit deutscher Lokalisierung, aus 0.18 wird „0,18". Für
      // parseFloat endet die Zahl am Komma - jeder Wert wurde zu 0, und die
      // Spalte „Kosten je Frage" sortierte sichtbar gar nicht.
      const z = TabellenSortierung._zahl(roh);
      return z === null ? roh : z;
    }
    const text = (zelle.textContent || '').trim();
    return text === '' ? null : text;
  }

  /** Deutsche Zahl aus einem Text - oder null. "−1.234,5 €" -> -1234.5
   *
   *  ERKENNT AUCH BRÜCHE wie "5/6" (Score, Treffer, erfüllte Kriterien) und
   *  sortiert sie nach ihrem WERT, nicht nach dem Zähler: "3/4" (0,75) steht
   *  damit über "5/8" (0,625). Bei gleichem Nenner - dem Normalfall in einer
   *  Spalte - ist die Reihenfolge dieselbe wie beim Zähler.
   *
   *  Ohne diese Sonderbehandlung würde die Ziffernfilterung aus "5/6" die Zahl
   *  56 machen: beim Sortieren unauffällig falsch, weil das Ergebnis trotzdem
   *  plausibel aussieht (Befund shortlongx 11.08.2026, Buffett-Screener).
   *  Der Bruch muss die GANZE Zelle ausfüllen - "11/08/2026" bleibt damit ein
   *  Datum und wird als Text sortiert. */
  static _zahl(text) {
    if (typeof text === 'number') return text;
    if (typeof text !== 'string') return null;
    const bruch = text.trim().match(/^(-?\d+(?:[.,]\d+)?)\s*\/\s*(\d+(?:[.,]\d+)?)$/);
    if (bruch) {
      const z = parseFloat(bruch[1].replace(',', '.'));
      const n = parseFloat(bruch[2].replace(',', '.'));
      return (n && !isNaN(z)) ? z / n : null;
    }
    // Nur Ziffern, Trenner und Vorzeichen behalten; Minus auch als Gedankenstrich.
    const roh = text.replace(/−|–/g, '-').replace(/[^\d,.\-]/g, '');
    if (!/\d/.test(roh)) return null;
    const z = parseFloat(roh.replace(/\./g, '').replace(',', '.'));
    return isNaN(z) ? null : z;
  }

  static _anwenden(tabelle, idx, auf) {
    const koerper = tabelle.tBodies[0];
    // ABSCHNITTSZEILEN (data-gruppe) sortieren nicht mit: Sie fassen die Zeilen
    // darunter zusammen ("Bereich Musik" in den Testcase-Tabellen). Mitsortiert
    // stuenden sie irgendwo mitten in einer fremden Gruppe. Sie werden entfernt;
    // wer sie braucht, setzt sie im Ereignis `tabelle:sortiert` neu.
    const zeilen = [...koerper.rows].filter(r => {
      if (r.dataset && r.dataset.gruppe !== undefined) { r.remove(); return false; }
      return true;
    });
    const richtung = auf ? 1 : -1;
    zeilen.sort((a, b) => {
      const wa = TabellenSortierung._wert(a.cells[idx]);
      const wb = TabellenSortierung._wert(b.cells[idx]);
      // Leere IMMER ans Ende - unabhängig von der Richtung.
      if (wa === null && wb === null) return 0;
      if (wa === null) return 1;
      if (wb === null) return -1;
      const za = TabellenSortierung._zahl(wa), zb = TabellenSortierung._zahl(wb);
      if (za !== null && zb !== null) return (za - zb) * richtung;
      return String(wa).localeCompare(String(wb), 'de', { numeric: true }) * richtung;
    });
    zeilen.forEach(r => koerper.appendChild(r));
    tabelle.dataset.sortIdx = idx;
    tabelle.dataset.sortDir = auf ? 'asc' : 'desc';
    // Damit Gliederungen, die auf der Reihenfolge beruhen, nachziehen koennen.
    tabelle.dispatchEvent(new CustomEvent('tabelle:sortiert', {
      bubbles: true, detail: { idx: idx, auf: auf },
    }));
  }

  // ---------------------------------------------------------- Merken (F5)

  static _key(tabelle) {
    return tabelle.dataset.sortKey ? SPEICHER + tabelle.dataset.sortKey : null;
  }

  /** Sortierung merken — MIT dem Spalten-Key, nicht nur mit dem Index.
   *
   *  Der Index allein zeigt nach jeder Spaltenänderung auf etwas anderes.
   *  Gemessen am 17.08.2026: Nach dem Einfügen der Spalten „Nr." und
   *  „Kategorie" rutschte „Bereich" von Position 1 auf 3 — die gemerkte
   *  Sortierung sortierte danach nach „Nr.", einer Spalte, die gar nicht
   *  sortierbar ist. Sichtbare Folge: Die Bereichs-Abschnitte verschwanden,
   *  weil die Seite dachte, es sei nach etwas anderem sortiert. */
  static _merken(tabelle, idx, auf) {
    const k = TabellenSortierung._key(tabelle);
    if (!k) return;
    const kopf = TabellenSortierung._kopfzeile(tabelle);
    const th = kopf && kopf.cells[idx];
    const sk = th && th.dataset.key ? th.dataset.key : '';
    try {
      localStorage.setItem(k, JSON.stringify({ idx: idx, auf: auf, key: sk }));
    } catch (e) {}
  }

  static _gemerktesAnwenden(tabelle) {
    const k = TabellenSortierung._key(tabelle);
    if (!k) return;
    let s = null;
    try { s = JSON.parse(localStorage.getItem(k) || 'null'); } catch (e) { return; }
    if (!s || typeof s.idx !== 'number' || s.idx < 0) return;
    const kopf = TabellenSortierung._kopfzeile(tabelle);
    if (!kopf) return;
    let idx = s.idx;
    // Der KEY entscheidet, nicht der Index: Spalten kommen dazu und wandern.
    if (s.key) {
      idx = [...kopf.cells].findIndex(th => th.dataset.key === s.key);
      if (idx < 0) { TabellenSortierung.vergessen(tabelle); return; }
    } else if (s.idx >= kopf.cells.length) {
      // Alter Eintrag ohne Key und die Spaltenzahl passt nicht mehr — lieber
      // gar nicht sortieren als nach der falschen Spalte.
      TabellenSortierung.vergessen(tabelle);
      return;
    }
    // Eine Spalte, die ausdrücklich nicht sortiert (Kästchen, Nr., Run), darf
    // auch aus dem Speicher nicht sortieren.
    if (kopf.cells[idx] && kopf.cells[idx].dataset.sortAus !== undefined) {
      TabellenSortierung.vergessen(tabelle);
      return;
    }
    TabellenSortierung._anwenden(tabelle, idx, !!s.auf);
  }

  /** Gemerkte Sortierung einer Tabelle vergessen. */
  static vergessen(tabelle) {
    const k = TabellenSortierung._key(tabelle);
    if (k) { try { localStorage.removeItem(k); } catch (e) {} }
  }
}

// AUCH GLOBAL (nicht nur als ES-Modul-Export): TabellenBreiten ruft nach dem
// Ziehen ``window.TabellenSortierung.hochkant`` auf, um die Ueberschriften neu
// auszurichten. Ein harter Import waere die falsche Richtung - die Breiten
// funktionieren auch ohne Sortierung, und zwei Module, die sich gegenseitig
// importieren, sind eine Ringabhaengigkeit, die Node beim Testen zerlegt.
if (typeof window !== 'undefined') window.TabellenSortierung = TabellenSortierung;
