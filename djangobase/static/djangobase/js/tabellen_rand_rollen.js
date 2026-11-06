/* TabellenRandRollen - rollt eine breite Tabelle mit, solange die Maus beim Spaltenziehen am Rand steht.
   ==========================================================================
   Eingefuehrt 05.11.2026 (shortlongx, Edgar: „Spalten sind nicht verschiebbar“).

   DER FALL: Die Tabelle ist breiter als ihr Rollbereich, die letzte Spalte soll
   neben eine linke. Quelle und Ziel sind nie zugleich zu sehen, und mit einer
   festen (sticky) ersten Spalte liegen die Nachbarn beim Greifen sogar UNTER ihr:
   gemessen landete „vs Buy/Hold“ neun Spalten rechts vom Ziel, naeher kam man
   nicht. Der Rand zaehlt deshalb ab dem rechten Ende der festen Spalten.

   Rollt, was die Tabelle rollt (naechster Vorfahre mit overflow-x auto/scroll,
   der wirklich breiter ist); ist die Tabelle ganz zu sehen, tut die Klasse nichts. */

const RAND_PX = 70;
const SCHRITT_PX = 12;
const TAKT_MS = 30;     // Uhr statt requestAnimationFrame: auf der schweren Seite gemessen nur 2 Bilder je Sekunde

export class TabellenRandRollen {
  /** ``nachSchritt(x)`` laeuft nach jedem Rollschritt: Die Spalten sind unter der stehenden Maus weitergewandert. */
  constructor(tabelle, nachSchritt) {
    this.kopf = tabelle.tHead.rows[0];
    this.nachSchritt = nachSchritt;
    this.roller = TabellenRandRollen._roller(tabelle);
    this.x = 0;
    this.uhr = 0;
  }

  static _roller(tabelle) {
    for (let e = tabelle.parentElement; e; e = e.parentElement) {
      const o = getComputedStyle(e).overflowX;
      if ((o === 'auto' || o === 'scroll') && e.scrollWidth > e.clientWidth) return e;
    }
    return null;
  }

  /** Linker Rand der sichtbaren Spalten: hinter festen Spalten, sonst die Kante des Rollbereichs. */
  _linkerRand() {
    let rand = this.roller.getBoundingClientRect().left;
    for (const c of this.kopf.cells) {
      if (getComputedStyle(c).position === 'sticky') rand = Math.max(rand, c.getBoundingClientRect().right);
    }
    return rand;
  }

  /** Mausposition melden; die Uhr laeuft ab der ersten Bewegung bis ``stopp``. */
  maus(x) {
    this.x = x;
    if (this.roller && !this.uhr) this.uhr = setInterval(() => this._schritt(), TAKT_MS);
  }

  _schritt() {
    const r = this.roller;
    const richtung = this.x < this._linkerRand() + RAND_PX ? -1
      : this.x > r.getBoundingClientRect().right - RAND_PX ? 1 : 0;
    if (!richtung) return;
    const vorher = r.scrollLeft;
    r.scrollLeft = vorher + richtung * SCHRITT_PX;
    if (r.scrollLeft !== vorher) this.nachSchritt(this.x);
  }

  stopp() {
    clearInterval(this.uhr);
    this.uhr = 0;
    this.roller = null;
  }
}
