/* TabellenReihenfolge - Spalten an der Ueberschrift greifen und an eine andere Stelle ziehen, je Tabelle gemerkt.
   ==========================================================================
   Eingefuehrt 04.11.2026 fuer StayNestor (Edgar: „Spalten verschiebbar,
   sortierbar, merke dir die Einstellungen pro User“, „mach auch das in
   djangoBase“).

   OPT-IN: ``tabellen_auto.js`` bindet es an eine Tabelle mit
   ``data-spalten-verschieben`` - oder an alle, wenn das Projekt es im
   Speicher-Element einschaltet (``<script id="djb-tabellen"
   data-verschieben="1">``, siehe ``tabellen_speicher.js``).
   ``data-spalten-fest`` nimmt eine Tabelle aus. Ohne beides bleibt jede
   Tabelle wie bisher.

   BEDIENUNG: Ueberschrift mit der Maus greifen und waagerecht ziehen (ab 6 px,
   darunter bleibt es ein Klick = Sortieren); ein Strich zeigt, wo die Spalte
   landet. Nicht gegriffen wird an Feldern, Knoepfen, Links und am Breiten-Griff.

   WIE: Die Zellen werden im DOM umgehaengt - in Kopf, Koerper und Fuss, jede
   Zeile mit genau so vielen Zellen wie der Kopf und ohne ``colspan`` (Zeilen
   wie „Keine Eintraege“ bleiben unberuehrt). Damit stimmen Sortierung (liest
   ``row.cells[idx]``), Breiten (je ``data-key``) und Spaltenwahl weiter.
   Jede Kopfzelle bekommt einen ``data-key`` (vorhanden oder ``i<Position im
   Markup>`` - derselbe Schluessel, unter dem TabellenBreiten die Breite ohnehin
   merkt); gemerkt wird die Folge dieser Schluessel unter
   ``tblReihe:<data-sort-key>`` im TabellenSpeicher. Neue Spalten im Markup
   stellen sich hinter ihren Vorgaenger.

   NACHGELADENE ZEILEN kommen in der Folge des Markups: Ein MutationObserver je
   Tabelle ordnet jede neue Zeile ein (``data-djb-reihe="1"`` = schon geordnet;
   eine umsortierte Zeile behaelt die Marke). Ersetzt Code alle Zellen einer
   Zeile (``tr.innerHTML = …``), gilt sie wieder als Markup-Folge.

   GRENZEN: Mehrzeilige Koepfe und Koepfe mit ``colspan`` bleiben fest. Code,
   der Zellen ueber ihre Position anspricht (``row.cells[3]``, CSS
   ``td:nth-child(3)``), trifft nach dem Umstellen eine andere Spalte - solche
   Tabellen tragen ``data-spalten-fest``. */
import { TabellenRandRollen } from './tabellen_rand_rollen.js';
import { TabellenSpeicher } from './tabellen_speicher.js';

const VORSATZ = 'tblReihe:';
const SCHWELLE_PX = 6;
const NICHT_GREIFEN = 'input, select, textarea, button, a, label, .tb-griff';

export class TabellenReihenfolge {
  /** Darf diese Tabelle Spalten umstellen? */
  static erlaubt(t) {
    if (t.hasAttribute('data-spalten-fest')) return false;
    if (!t.hasAttribute('data-spalten-verschieben') && !TabellenSpeicher.verschieben()) return false;
    return TabellenReihenfolge._kopf(t) !== null;
  }

  /** Die eine Kopfzeile - ``null`` bei mehrzeiligem Kopf, verbundenen Zellen oder nur einer Spalte. */
  static _kopf(t) {
    const k = t.tHead;
    if (!k || k.rows.length !== 1) return null;
    const zeile = k.rows[0];
    if (zeile.cells.length < 2 || [...zeile.cells].some((c) => c.colSpan > 1)) return null;
    return zeile;
  }

  /** Einmal je Tabelle einrichten; ``schluessel`` = ihr ``data-sort-key``. */
  static binden(tabelle, schluessel) {
    if (!tabelle._djbReihe) {
      tabelle._djbReihe = new TabellenReihenfolge(tabelle, schluessel);
      tabelle._djbReihe._einrichten();
    }
    return tabelle._djbReihe;
  }

  constructor(tabelle, schluessel) {
    this.t = tabelle;
    this.k = VORSATZ + schluessel;
    this.quelle = [];   // Schluessel in der Folge des Markups
    this.aktuell = [];  // Schluessel in der angezeigten Folge
    this.beob = null;
  }

  _einrichten() {
    this._kopfLesen(TabellenReihenfolge._kopf(this.t));
    const gemerkt = this._gemerkt();
    if (gemerkt) this._umstellen(this._ziel(gemerkt));
    this.t.classList.add('djb-spalten-verschiebbar');
    this._beobachten();
    this._ziehenBinden();
  }

  /** Schluessel vergeben, Markup-Folge merken; alle passenden Zeilen stehen jetzt in dieser Folge. */
  _kopfLesen(kopf) {
    [...kopf.cells].forEach((th, i) => { if (!th.dataset.key) th.dataset.key = 'i' + i; });
    this.quelle = [...kopf.cells].map((th) => th.dataset.key);
    this.aktuell = this.quelle.slice();
    [...this.t.rows].forEach((z) => { if (this._passend(z)) z.dataset.djbReihe = '1'; });
  }

  _passend(z) {
    return z.children.length === this.quelle.length && ![...z.children].some((c) => c.colSpan > 1);
  }

  _gemerkt() {
    try {
      const liste = JSON.parse(TabellenSpeicher.lesen(this.k) || 'null');
      return Array.isArray(liste) ? liste : null;
    } catch (e) {
      return null;
    }
  }

  /** Gemerkte Folge auf die heutigen Spalten: Weggefallene raus, neue hinter ihren Vorgaenger. */
  _ziel(gemerkt) {
    const da = new Set(this.quelle);
    const ziel = [...new Set(gemerkt)].filter((k) => da.has(k));
    this.quelle.forEach((k, i) => {
      if (ziel.includes(k)) return;
      const vor = this.quelle.slice(0, i).reverse().find((x) => ziel.includes(x));
      ziel.splice(vor === undefined ? 0 : ziel.indexOf(vor) + 1, 0, k);
    });
    return ziel;
  }

  /** Eine Zeile von Folge ``von`` auf Folge ``nach`` umhaengen. */
  static _anordnen(z, von, nach) {
    if (von.join('\u0001') === nach.join('\u0001')) return;
    const zellen = [...z.children];
    const je = {};
    von.forEach((k, i) => { je[k] = zellen[i]; });
    nach.forEach((k) => { if (je[k]) z.appendChild(je[k]); });
  }

  /** Alle Zeilen auf die Folge ``neu`` bringen. */
  _umstellen(neu) {
    if (this.beob) this._abarbeiten(this.beob.takeRecords());   // fremde Aenderungen zuerst
    const kopf = TabellenReihenfolge._kopf(this.t);
    const idx = this.t.dataset.sortIdx;
    const sortiert = kopf && idx !== undefined ? kopf.cells[parseInt(idx, 10)] : null;
    [...this.t.rows].forEach((z) => {
      if (!this._passend(z)) return;
      TabellenReihenfolge._anordnen(z, z.dataset.djbReihe === '1' ? this.aktuell : this.quelle, neu);
      z.dataset.djbReihe = '1';
    });
    this.aktuell = neu.slice();
    // Die Sortierung merkt sich die Spalte als Position (sortIdx) - sie wandert mit.
    if (sortiert) this.t.dataset.sortIdx = [...sortiert.parentNode.cells].indexOf(sortiert);
    if (this.beob) this.beob.takeRecords();                   // eigene Aenderungen nicht beobachten
  }

  _merken() {
    if (this.aktuell.join('\u0001') === this.quelle.join('\u0001')) TabellenSpeicher.entfernen(this.k);
    else TabellenSpeicher.schreiben(this.k, JSON.stringify(this.aktuell));
  }

  // ------------------------------------------------------------ nachgeladene Zeilen

  _beobachten() {
    if (typeof MutationObserver === 'undefined') return;
    this.beob = new MutationObserver((r) => this._abarbeiten(r));
    this.beob.observe(this.t, { childList: true, subtree: true });
  }

  _abarbeiten(eintraege) {
    if (!eintraege.length) return;
    const zeilen = new Set();
    const zellen = new Map();
    for (const e of eintraege) {
      for (const n of e.addedNodes) {
        if (n.nodeType !== 1) continue;
        if (n.tagName === 'TR') zeilen.add(n);
        else if (/^(TBODY|THEAD|TFOOT)$/.test(n.tagName)) [...n.rows].forEach((z) => zeilen.add(z));
        else if (/^T[DH]$/.test(n.tagName) && e.target.tagName === 'TR') {
          zellen.set(e.target, (zellen.get(e.target) || 0) + 1);
        }
      }
    }
    // Alle Zellen einer Zeile neu (tr.innerHTML = …): wieder Markup-Folge.
    zellen.forEach((anzahl, z) => {
      if (anzahl >= z.children.length) { delete z.dataset.djbReihe; zeilen.add(z); }
    });
    const kopf = TabellenReihenfolge._kopf(this.t);
    if (kopf && zeilen.has(kopf) && kopf.dataset.djbReihe !== '1') {
      // Kopf neu gezeichnet: Spalten neu lesen, dann die gemerkte Folge anwenden.
      this._kopfLesen(kopf);
      const gemerkt = this._gemerkt();
      if (gemerkt) this._umstellen(this._ziel(gemerkt));
      return;
    }
    zeilen.forEach((z) => {
      if (!z.isConnected || z.closest('table') !== this.t || z.dataset.djbReihe === '1' || !this._passend(z)) return;
      TabellenReihenfolge._anordnen(z, this.quelle, this.aktuell);
      z.dataset.djbReihe = '1';
    });
    if (this.beob) this.beob.takeRecords();
  }

  // ------------------------------------------------------------ Ziehen

  _ziehenBinden() {
    this.t.addEventListener('mousedown', (e) => {
      if (e.button !== 0) return;
      const kopf = TabellenReihenfolge._kopf(this.t);
      const th = e.target.closest('th');
      if (!kopf || !th || th.parentNode !== kopf || e.target.closest(NICHT_GREIFEN)) return;
      const x0 = e.clientX;
      const y0 = e.clientY;
      let zieht = false;
      let ziel = null;
      const rand = new TabellenRandRollen(this.t, (x) => {
        ziel = this._zielPosition(kopf, x);
        this._strich(kopf, ziel);
      });
      const bewegen = (ev) => {
        if (!zieht) {
          if (Math.abs(ev.clientX - x0) < SCHWELLE_PX && Math.abs(ev.clientY - y0) < SCHWELLE_PX) return;
          zieht = true;
          th.classList.add('djb-spalte-gezogen');
          document.body.classList.add('djb-spalten-zieht');
          try { window.getSelection().removeAllRanges(); } catch (err) { /* egal */ }
        }
        ev.preventDefault();
        ziel = this._zielPosition(kopf, ev.clientX);
        this._strich(kopf, ziel);
        rand.maus(ev.clientX);
      };
      const los = () => {
        document.removeEventListener('mousemove', bewegen);
        document.removeEventListener('mouseup', los);
        rand.stopp();
        if (!zieht) return;
        th.classList.remove('djb-spalte-gezogen');
        document.body.classList.remove('djb-spalten-zieht');
        this._strich(null);
        TabellenReihenfolge._klickSchlucken();
        if (ziel !== null) this._verschieben(th.dataset.key, ziel);
      };
      document.addEventListener('mousemove', bewegen);
      document.addEventListener('mouseup', los);
    });
  }

  /** Vor welcher Spalte (Position) die gezogene landet - ``cells.length`` = ganz rechts. */
  _zielPosition(kopf, x) {
    const zellen = [...kopf.cells];
    for (let i = 0; i < zellen.length; i++) {
      const r = zellen[i].getBoundingClientRect();
      if (x < r.left + r.width / 2) return i;
    }
    return zellen.length;
  }

  /** Der Strich, der die Landestelle zeigt (``kopf`` null = weg). */
  _strich(kopf, pos) {
    let s = document.getElementById('djb-spalte-ziel');
    if (!kopf) { if (s) s.remove(); return; }
    if (!s) {
      s = document.createElement('div');
      s.id = 'djb-spalte-ziel';
      s.className = 'djb-spalte-ziel';
      document.body.appendChild(s);
    }
    const zellen = [...kopf.cells];
    const t = this.t.getBoundingClientRect();
    const x = pos < zellen.length ? zellen[pos].getBoundingClientRect().left
      : zellen[zellen.length - 1].getBoundingClientRect().right;
    const oben = Math.max(t.top, 0);
    s.style.left = Math.round(x) + 'px';
    s.style.top = Math.round(oben) + 'px';
    s.style.height = Math.round(Math.min(t.bottom, window.innerHeight) - oben) + 'px';
  }

  _verschieben(key, vor) {
    const folge = this.aktuell.slice();
    const von = folge.indexOf(key);
    if (von < 0 || vor === von || vor === von + 1) return;
    folge.splice(von, 1);
    folge.splice(vor > von ? vor - 1 : vor, 0, key);
    this._umstellen(folge);
    this._merken();
  }

  /** Nach dem Loslassen feuert der Browser einen Klick auf die Ueberschrift - der wuerde sortieren. */
  static _klickSchlucken() {
    const schlucken = (e) => { e.stopImmediatePropagation(); e.preventDefault(); };
    document.addEventListener('click', schlucken, { capture: true, once: true });
    setTimeout(() => document.removeEventListener('click', schlucken, { capture: true }), 0);
  }
}
