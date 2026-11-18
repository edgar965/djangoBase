/* TabellenBreitenGemeinsam - EINE Breitengruppe fuer alle Tabellen unter einem
   Element mit ``data-spalten-gemeinsam`` (Ansage Edgar 11.11.2026, assistant
   Heizung: „die spalten der djangoTabellen sollen alle synchron geändert werden
   für alle Tabellen auf der Seite" und „ziehe ich spalte 1, sind alle spalten 1
   in allen Tabellen mitgezogen usw"). ``tabellen_auto.js`` nimmt jede Tabelle
   darunter mit ``aufnehmen()`` auf. Opt-in: ohne das Attribut bleibt jede
   Tabelle fuer sich wie bisher.

   - Synchron nach POSITION, nicht nach data-key: Schluessel ist die Stelle der
     Spalte unter den sichtbaren Kopfzellen (``p0``, ``p1`` …). Ausgeblendete
     Spalten zaehlen nicht mit.
   - SOFORT gleich, nicht erst nach dem ersten Ziehen. Vorgabe je Position: die
     groesste natuerliche Breite (Inhalt ohne Umbruch, ``max-content``) aus allen
     Tabellen, hoechstens ``MAX_VORGABE_PX``. Aus dem zusammengedrueckten
     Auto-Layout einer Tabelle (erster Versuch 11.11.2026) wurde „Name" 70 px breit
     und die zweispaltige CCU-Tabelle unlesbar. Gemerkte Breiten (nach dem Ziehen)
     gehen immer vor.
   - VERBORGENE Tabellen (anderer Reiter, display:none) messen 0 px. Sie werden
     erst gebunden, wenn sie sichtbar werden (ResizeObserver); hat sich die
     Vorgabe inzwischen geaendert, bekommen sie dann die neue.
   - Ersetzte Tabellen (Inhalt per innerHTML neu) fallen beim naechsten
     ``aufnehmen()`` heraus. */
import { TabellenBreiten } from './tabellen_breiten.js';
import { TabellenSpeicher } from './tabellen_speicher.js';

export class TabellenBreitenGemeinsam extends TabellenBreiten {
  /** Breiter wird eine Vorgabe nicht - ein langer Hinweistext soll keine Spalte sprengen. */
  static MAX_VORGABE_PX = 360;

  constructor(key) {
    super([], key);
    this.vorgabe = {};   // Position -> px
    this.fassung = 0;    // zaehlt jede Aenderung der Vorgabe; jede Tabelle merkt sich ihre
    this.beobachter = typeof ResizeObserver === 'undefined' ? null
      : new ResizeObserver(eintraege => eintraege.forEach(e => this._sichtbarGeworden(e.target)));
  }

  static sichtbar(el) {
    return !!el && el.isConnected && el.getClientRects().length > 0 && el.offsetWidth > 0;
  }

  /** Eine Tabelle in die Gruppe aufnehmen, binden und angleichen. */
  aufnehmen(t) {
    this.ts = this.ts.filter(x => x.isConnected && x !== t);
    this.ts.push(t);
    if (this.beobachter) this.beobachter.observe(t);
    this._bindenEine(t);
  }

  binden() {
    this.ts.forEach(t => this._bindenEine(t));
    return this;
  }

  /** Position unter den sichtbaren Kopfzellen der Zeile. */
  _sk(th, i) {
    const p = [...th.parentElement.cells].filter(c => !this._aus(c)).indexOf(th);
    return p < 0 ? 'aus' + i : 'p' + p;
  }

  _aus(th) {
    return th.hidden || th.classList.contains('db-spalte-aus') || getComputedStyle(th).display === 'none';
  }

  _sichtbar() {
    return this.ts.filter(t => TabellenBreitenGemeinsam.sichtbar(t));
  }

  _sichtbarGeworden(t) {
    if (!TabellenBreitenGemeinsam.sichtbar(t)) return;
    if (t.dataset.djbBreitenOffen === '1') this._bindenEine(t);
    else if (t.dataset.djbBreitenFassung !== String(this.fassung)) this._anwenden([t]);
  }

  /** ``binden()`` der Basisklasse fuer EINE Tabelle (Griffe), Vorgabe ergaenzen, angleichen. */
  _bindenEine(t) {
    if (!TabellenBreitenGemeinsam.sichtbar(t)) {
      t.dataset.djbBreitenOffen = '1';
      return;
    }
    delete t.dataset.djbBreitenOffen;
    this._mit([t], () => super.binden());
    this._beitragen(t);
    this._anwenden(this._sichtbar());
  }

  /** Natuerliche Breiten der Tabelle in die Vorgabe (je Position das Groessere). */
  _beitragen(t) {
    const gemessen = this._messen(t);
    let neu = false;
    Object.entries(gemessen).forEach(([sk, px]) => {
      if (px > (this.vorgabe[sk] || 0)) {
        this.vorgabe[sk] = px;
        neu = true;
      }
    });
    if (neu) this.fassung += 1;
  }

  /** Breiten je Position bei ``max-content`` - eingefrorene Breiten dafuer kurz loesen. */
  _messen(t) {
    const ths = this._ths(t);
    const alt = { layout: t.style.tableLayout, breite: t.style.width, spalten: ths.map(th => th.style.width) };
    t.style.tableLayout = 'auto';
    t.style.width = 'max-content';
    ths.forEach(th => { th.style.width = ''; });
    const gemessen = {};
    ths.forEach((th, i) => {
      const sk = this._sk(th, i);
      if (!sk.startsWith('p')) return;
      const px = Math.round(th.getBoundingClientRect().width);
      gemessen[sk] = Math.min(TabellenBreitenGemeinsam.MAX_VORGABE_PX, Math.max(TabellenBreiten.MIN_PX, px));
    });
    t.style.tableLayout = alt.layout;
    t.style.width = alt.breite;
    ths.forEach((th, i) => { th.style.width = alt.spalten[i]; });
    return gemessen;
  }

  /** Vorgabe und gemerkte Breiten auf die Tabellen setzen. */
  _anwenden(tabellen) {
    const breiten = { ...this.vorgabe, ...(TabellenSpeicher.anpassen() ? this._laden() : {}) };
    tabellen.forEach(t => {
      t.style.tableLayout = 'fixed';
      this._ths(t).forEach((th, i) => {
        const px = breiten[this._sk(th, i)];
        if (px) th.style.width = px + 'px';
        else if (!parseFloat(th.style.width)) th.style.width = TabellenBreiten.MIN_PX + 'px';
      });
      this._summeSetzen(t);
      this._hochkantPruefen(t);
      t.dataset.djbBreitenFassung = String(this.fassung);
    });
  }

  _einfrieren() {
    this._mit(this._sichtbar(), () => super._einfrieren());
  }

  _setzen(sk, px) {
    this._mit(this._sichtbar(), () => super._setzen(sk, px));
  }

  /** ``f`` mit voruebergehend anderer Tabellenliste - die Basisklasse arbeitet auf ``this.ts``. */
  _mit(tabellen, f) {
    const alle = this.ts;
    this.ts = tabellen;
    try {
      f();
    } finally {
      this.ts = alle;
    }
  }

  /** Nach dem Ziehen: Breite je Position aus der ersten sichtbaren Tabelle, die sie hat. */
  _merkenAlle() {
    const b = this._laden();
    const gesehen = new Set();
    this._sichtbar().forEach(t => this._ths(t).forEach((th, i) => {
      const sk = this._sk(th, i);
      if (gesehen.has(sk) || !sk.startsWith('p')) return;
      gesehen.add(sk);
      const px = Math.round(th.getBoundingClientRect().width);
      if (px >= TabellenBreiten.MIN_PX) b[sk] = px;
    }));
    TabellenSpeicher.schreiben(this.key, JSON.stringify(b));
    this.fassung += 1;   // verborgene Tabellen holen sich die neuen Breiten beim Sichtbarwerden
    this._anwenden(this._sichtbar());
  }

  /** Doppelklick auf einen Griff: gemerkte Breiten weg, Vorgabe neu messen. */
  zuruecksetzen() {
    super.zuruecksetzen();
    this.vorgabe = {};
    this.fassung += 1;
    const sichtbar = this._sichtbar();
    sichtbar.forEach(t => this._beitragen(t));
    this._anwenden(sichtbar);
  }
}
