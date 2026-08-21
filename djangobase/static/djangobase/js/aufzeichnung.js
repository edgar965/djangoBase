/* Reiter „Aufzeichnen" — Schalter und Liste der Aufzeichnungen.
 * ==============================================================
 * AUFTRAG (Edgar, 20.08.2026): „Ein Aufzeichnen Button soll erscheinen, der
 * deaktiviert ist. wenn ich den aktiviere, werden logs und aktionen erfasst …
 * Mit Klick auf beenden ist die Aufzeichnung beendet. Vergib dem Test einen
 * Default Namen und speicher den in einer Liste. Die Liste ist eine sortierbare
 * Tabelle (nimm das djangoBase Template dafür). Darin IDs, Namen die ich
 * verändern kann, löschen buttons."
 *
 * WARUM DER SCHALTER ZUERST GESPERRT IST
 * --------------------------------------
 * Er wird erst freigegeben, wenn der Server geantwortet hat. Bis dahin ist
 * unbekannt, ob schon eine Aufnahme läuft — und ein Knopf, der in diesem
 * Moment „Aufzeichnen" anbietet, würde eine zweite starten wollen und
 * scheitern. Ein gesperrter Knopf, der gleich darauf die Wahrheit zeigt, ist
 * ehrlicher als ein sofort klickbarer, der etwas anderes tut als er sagt.
 *
 * DIE TABELLE WIRD IM BROWSER GEBAUT
 * ----------------------------------
 * `_tabelle.html` ist für Zeilen gedacht, die der View fertig liefert; hier
 * ändern sie sich während einer laufenden Aufnahme sekündlich. Deshalb dieselben
 * Klassen und Attribute (`db-tabelle sortable`, `data-sort-key`) und die beiden
 * JS-Module direkt — genau der Weg, den der Kopf jener Vorlage dafür nennt.
 */
import { AufzeichnungsListe } from '/static/djangobase/js/aufzeichner_liste.js';

const PFAD = '/hilfe/tests/aufzeichnung/';

const csrf = () => {
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
};

const senden = (daten) => fetch(PFAD, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
  body: JSON.stringify(daten),
}).then(r => r.json());

/** Sekunden lesbar: 47 s, 2:05 min. — Das Tabellen-Markup liegt seit dem
 *  21.08.2026 in ``aufzeichner_liste.js``; hier bleibt nur, was die Statuszeile
 *  über der Tabelle braucht. */
const dauer = (s) => (s < 60) ? Math.round(s) + ' s'
  : Math.floor(s / 60) + ':' + String(Math.round(s % 60)).padStart(2, '0') + ' min';

class Reiter {
  constructor() {
    this.schalter = document.getElementById('au-schalter');
    this.lage = document.getElementById('au-lage');
    this.tabelle = document.getElementById('au-tabelle');
    this.laeuft = null;
    this.ticker = null;
  }

  async laden() {
    const d = await fetch(PFAD, { headers: { Accept: 'application/json' } })
      .then(r => r.json()).catch(() => null);
    if (!d || !d.ok) {
      if (this.lage) this.lage.textContent = 'Zustand nicht abrufbar.';
      return;
    }
    this.laeuft = d.laeuft;
    this.zeichnen(d.liste || []);
  }

  zeichnen(liste) {
    this.schalterSetzen();
    if (this.tabelle) {
      // DIESELBE KLASSE WIE IM POPUP (21.08.2026): Vorher baute dieser Reiter
      // sein eigenes Tabellen-Markup, das Popup ein zweites. Zwei Kopien
      // derselben Tabelle laufen auseinander - die eine bekommt einen neuen
      // Knopf, die andere nicht.
      if (!this._liste) {
        this._liste = new AufzeichnungsListe(this.tabelle, senden,
                                             () => this.laden(), 'aufzeichnungen');
      }
      this._liste.zeichnen(liste);
    }
  }

  /** Der Knopf BLENDET NUR EIN - er startet keine Aufnahme mehr.
   *
   *  ANSAGE (Edgar, 21.08.2026): „der Button ‚Aufzeichnen' im Tab soll nur den
   *  Bereich im Menü oben links einblenden, die Aufnahme aber NICHT starten."
   *
   *  Das trennt sauber: Gestartet wird an EINER Stelle - im Bereich selbst, der
   *  auf jeder Seite steht. Vorher gab es zwei Schalter für dieselbe Sache, und
   *  wer im Reiter startete, sah die Aufnahme danach nur dort mitlaufen. */
  schalterSetzen() {
    const b = this.schalter;
    if (!b) return;
    b.disabled = false;
    b.classList.remove('btn-danger');
    b.classList.add('btn-outline-light');
    const da = Reiter.bereichSichtbar();
    b.textContent = da ? '✓ Bereich ist eingeblendet'
                       : '⏺ Aufzeichnung einblenden';
    b.title = da
      ? 'Der Bereich steht links oben im Menü - dort wird die Aufnahme gestartet'
      : 'Blendet den Bereich links oben im Menü ein (startet noch nichts)';
    if (this.laeuft) this.tickerStarten(); else this.tickerStoppen();
    if (!this.laeuft && this.lage) this.lage.textContent = '';
  }

  /** Steht der Bereich in der Sidebar gerade sichtbar da? */
  static bereichSichtbar() {
    const el = document.getElementById('djb-aufz');
    return !!el && !el.hidden;
  }

  /* Während der Aufnahme sekündlich zeigen, was zusammenkommt — sonst sieht
   * man dem Knopf nicht an, ob überhaupt etwas ankommt. */
  tickerStarten() {
    if (this.ticker) return;
    const zeigen = async () => {
      const d = await fetch(PFAD, { headers: { Accept: 'application/json' } })
        .then(r => r.json()).catch(() => null);
      if (!d || !d.ok || !d.laeuft) return;
      this.laeuft = d.laeuft;
      if (this.lage) {
        this.lage.textContent = 'läuft seit ' + dauer(d.laeuft.dauer_s)
          + ' · ' + d.laeuft.n_schritte + ' Schritte';
      }
    };
    zeigen();
    this.ticker = setInterval(zeigen, 2000);
  }

  tickerStoppen() {
    if (this.ticker) { clearInterval(this.ticker); this.ticker = null; }
  }


  binden() {
    if (this.schalter) {
      this.schalter.addEventListener('click', () => {
        // NUR EINBLENDEN (Ansage 21.08.2026) - gestartet wird im Bereich selbst.
        try { localStorage.setItem('djb-aufz-weg', '0'); } catch (e) { /* egal */ }
        const el = document.getElementById('djb-aufz');
        if (el) el.hidden = false;
        this.schalterSetzen();
        document.dispatchEvent(new CustomEvent('djb-aufzeichnung-geaendert',
                                               { detail: { von: 'reiter' } }));
      });
      document.addEventListener('djb-aufzeichnung-geaendert', (ev) => {
        if (ev.detail && ev.detail.von === 'reiter') return;
        this.laden();
      });
    }
    // Umbenennen und Löschen bindet die Listen-Klasse selbst.
  }
}

const reiter = new Reiter();
reiter.binden();
reiter.laden();

export { Reiter };
