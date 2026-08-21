/* Die Liste der Aufzeichnungen — im Popup wie im Reiter dieselbe Tabelle.
 * ======================================================================
 * AUFTRAG (Edgar, 20./21.08.2026):
 *
 *     „Vergib dem Test einen Default Namen und speicher den in einer Liste. Die
 *      Liste ist eine sortierbare Tabelle (nimm das djangoBase Template dafür).
 *      Darin IDs, Namen die ich verändern kann, löschen buttons."
 *     „in der liste der aufgezeichneten Tests sollt der Name veränderbar sein.
 *      Die Tabelle sollte von djangoBase tabelle erben, als z.B. Spalten
 *      verschiebbar."
 *
 * `_tabelle.html` ist für Zeilen gedacht, die der View fertig liefert; hier
 * ändern sie sich während einer laufenden Aufnahme sekündlich. Deshalb dieselben
 * Klassen und Attribute (`db-tabelle sortable`, `data-sort-key`) und die beiden
 * JS-Module direkt — genau der Weg, den der Kopf jener Vorlage dafür nennt.
 *
 * EINE KLASSE FÜR BEIDE ORTE (21.08.2026): Vorher baute der Reiter sein eigenes
 * Markup und das Popup ein zweites. Zwei Kopien derselben Tabelle laufen
 * auseinander — die eine bekommt einen neuen Knopf, die andere nicht.
 *
 * BREITEN NUR ÜBER EINE INSTANZ (Fehler 21.08.2026): Hier stand
 * `TabellenBreiten.binden(el)` — eine statische Methode, die es nicht gibt. Der
 * TypeError brach das Zeichnen ab, und die Tabelle hatte NIE ziehbare Spalten.
 */
import { TabellenSortierung } from '/static/djangobase/js/tabellen_sortierung.js';
import { TabellenBreiten } from '/static/djangobase/js/tabellen_breiten.js';

const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;');

const zeit = (iso) => {
  const d = new Date(iso);
  return isNaN(d) ? '–' : d.toLocaleString('de-DE',
    { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
};

const dauer = (s) => {
  const n = Math.round(s || 0);
  return n < 60 ? n + ' s' : Math.floor(n / 60) + ':' + String(n % 60).padStart(2, '0');
};

export class AufzeichnungsListe {
  /**
   *  @param wurzel      Element, in das die Tabelle gezeichnet wird
   *  @param senden      (daten) => Promise — der Kanal zum Server
   *  @param neuladen    () => Promise — nach Umbenennen/Löschen neu holen
   *  @param schluessel  Speicher-Schlüssel für Sortierung und Spaltenbreiten.
   *
   *  EIGENER SCHLÜSSEL JE ORT (21.08.2026): Popup und Reiter zeigen dieselbe
   *  Tabelle, aber in ganz verschiedenen Breiten. Mit einem gemeinsamen
   *  Schlüssel übernahm das 410 px schmale Popup die gezogenen Breiten der
   *  vollen Seite — die Hälfte der Spalten lag außerhalb des Fensters, der
   *  Löschknopf inklusive.
   */
  constructor(wurzel, senden, neuladen, schluessel) {
    this.wurzel = wurzel;
    this.senden = senden;
    this.neuladen = neuladen;
    this.schluessel = schluessel || 'aufzeichnungen';
    this.eng = /popup/.test(this.schluessel);
    this.gebunden = false;
  }

  /** Spalten: [Kopftext, Schlüssel, rechtsbündig, sortiert nicht] */
  static SPALTEN = [
    ['ID', 'id', false, false],
    ['Name', 'name', false, false],
    ['Start', 'start', false, false],
    ['Dauer', 'dauer', true, false],
    ['Schritte', 'schritte', true, false],
    ['Logs', 'logs', true, false],
    ['', 'aktion', false, true],
  ];

  /** Der schmale Satz fürs Popup.
   *
   *  ZWEI SÄTZE, WEIL ZWEI BREITEN (21.08.2026): Im Reiter steht die Tabelle
   *  über die volle Seitenbreite, im Popup in 410 Pixeln. Mit allen sieben
   *  Spalten lagen dort Logs und Löschknopf außerhalb des Fensters — also
   *  genau die Bedienelemente. Alles Weitere steht einen Klick entfernt unter
   *  „Alle Aufzeichnungen". */
  static SPALTEN_ENG = [
    ['ID', 'id', false, false],
    ['Name', 'name', false, false],
    ['Schritte', 'schritte', true, false],
    ['', 'aktion', false, true],
  ];

  /** Welche Zelle gehört zu welchem Spalten-Schlüssel. */
  zelle(e, key) {
    switch (key) {
      case 'id':
        return `<td><code title="${esc(e.id)}">${esc(String(e.id).slice(-6))}</code></td>`;
      case 'name':
        return `<td><input class="au-name" value="${esc(e.name)}" data-id="${esc(e.id)}"`
             + ` title="Name ändern – wird beim Verlassen des Feldes gespeichert"></td>`;
      case 'start':
        return `<td data-sort="${esc(e.start)}">${esc(zeit(e.start))}`
             + `${e.laeuft ? ' <b style="color:#f87171">läuft</b>' : ''}</td>`;
      case 'dauer':
        return `<td class="num" data-sort="${e.dauer_s}">${esc(dauer(e.dauer_s))}</td>`;
      case 'schritte':
        return `<td class="num">${e.n_schritte}</td>`;
      case 'logs':
        return `<td class="num">${e.n_logs}</td>`;
      default:
        return `<td><button type="button" class="djb-aufz-weg au-weg"`
             + ` data-id="${esc(e.id)}" title="Aufzeichnung löschen">✕</button></td>`;
    }
  }

  zeichnen(liste) {
    if (!this.wurzel) return;
    if (!liste.length) {
      this.wurzel.innerHTML =
        '<p class="djb-aufz-lage">Noch keine Aufzeichnung.</p>';
      return;
    }
    const spalten = this.eng ? AufzeichnungsListe.SPALTEN_ENG
                             : AufzeichnungsListe.SPALTEN;
    const kopf = spalten.map(([label, key, num, ohne]) =>
      `<th${num ? ' class="num"' : ''} data-key="${key}"`
      + `${ohne ? ' data-sort-aus="1"' : ''}>${label}</th>`).join('');

    const zeilen = liste.map(e => `<tr data-id="${esc(e.id)}">`
      + spalten.map(([, key]) => this.zelle(e, key)).join('')
      + '</tr>').join('');

    this.wurzel.innerHTML = `<div class="db-tabelle-rahmen">
      <table class="db-tabelle sortable" data-sort-key="${this.schluessel}">
        <thead><tr>${kopf}</tr></thead><tbody>${zeilen}</tbody>
      </table></div>`;

    TabellenSortierung.binden(this.wurzel);
    const t = this.wurzel.querySelector('table');
    if (t) new TabellenBreiten([t], this.schluessel).binden();
    this.binden();
  }

  /** Einmal binden, per Delegation — die Zeilen entstehen bei jeder Änderung neu. */
  binden() {
    if (this.gebunden) return;
    this.gebunden = true;
    this.wurzel.addEventListener('click', async ev => {
      const weg = ev.target.closest('button.au-weg');
      if (!weg) return;
      await this.senden({ aktion: 'loeschen', id: weg.dataset.id });
      await this.neuladen();
    });
    this.wurzel.addEventListener('change', async ev => {
      const feld = ev.target.closest('input.au-name');
      if (!feld) return;
      await this.senden({ aktion: 'name', id: feld.dataset.id, name: feld.value });
      await this.neuladen();
    });
  }
}
