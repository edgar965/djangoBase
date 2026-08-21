/* Der Aufzeichnen-Knopf, der über JEDER Seite schwebt.
 * ===================================================
 * AUFTRAG (Edgar, 21.08.2026, Nachtrag zum 20.08.):
 *
 *     „Ein Popup bauen, das die ganze Zeit über der Webseite ist. Darin ein
 *      Button mit aufzeichnen anzeigen. Der Button ist erstmal weiss. Sobald
 *      man drauf klickt, wird er rot und die Aufzeichnung beginnt. beim
 *      erneuten Klick wird er wieder weiss, und das Fenster mit testaufzeichnen
 *      wird wieder geöffnet, der Test wird gespeichert."
 *
 * WARUM DAS NÖTIG WAR
 * -------------------
 * Der Knopf stand vorher nur im Reiter „Aufzeichnen" unter Hilfe → Tests. Damit
 * war das Werkzeug für seinen eigenen Zweck unbrauchbar: Aufgezeichnet werden
 * sollen die Wege durch die Anwendung, und zu einem Weg gehört, dass man die
 * Tests-Seite verlässt. Wer erst dorthin navigieren muss, um zu starten, kann
 * nie den Weg aufzeichnen, der ihn interessiert.
 *
 * DREI ZUSTÄNDE, NICHT ZWEI
 * -------------------------
 *   grau     der Server hat noch nicht geantwortet - unbekannt, ob etwas läuft
 *   weiß     bereit
 *   rot      Aufnahme läuft (mit mitlaufender Dauer, damit man eine vergessene
 *            Aufnahme sieht, statt sie erst am 40-Minuten-Testfall zu bemerken)
 *
 * Der graue Zwischenzustand ist Absicht: Ein Knopf, der sofort „Aufzeichnen"
 * anbietet, würde bei laufender Aufnahme eine zweite starten wollen und
 * scheitern - er verspräche etwas anderes, als er tut.
 */
import { aufzeichnerStarten } from '/static/djangobase/js/aufzeichner.js';

const PFAD = '/hilfe/tests/aufzeichnung/';
const ZIEL = '/hilfe/tests/?tab=Aufzeichnen';

const csrf = () => {
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
};

/** Zum Server - IMMER über das echte ``fetch``.
 *
 *  ``window.fetch`` trägt bei laufender Aufnahme die mitschreibende Hülle; ein
 *  Aufruf darüber würde den eigenen Steuerbefehl in die Aufnahme schreiben. */
const senden = (daten) => (window.__djbAufzeichner?._roh?.bind(window.__djbAufzeichner)
                           || window.fetch)(PFAD, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
  body: JSON.stringify(daten),
}).then(r => r.json());

class AufzeichnerKnopf {
  constructor() {
    this.laeuft = null;          // {id, start} oder null
    this.beschaeftigt = false;
    this.uhr = null;
    this.knopf = null;
  }

  /** Das schwebende Fenster anlegen - einmal je Seite. */
  bauen() {
    if (document.querySelector('[data-djb-aufzeichner-ui]')) return;
    const box = document.createElement('div');
    box.className = 'djb-aufz';
    // Das Attribut ist die Absprache mit ``aufzeichner.js``: Was hier drin
    // geklickt wird, gehört zur Bedienung und nicht in die Aufnahme.
    box.setAttribute('data-djb-aufzeichner-ui', '1');
    box.innerHTML =
      '<button type="button" class="djb-aufz-knopf" disabled>'
      + '<span class="djb-aufz-punkt"></span>'
      + '<span class="djb-aufz-text">Aufzeichnen</span></button>';
    document.body.appendChild(box);
    this.knopf = box.querySelector('button');
    this.knopf.addEventListener('click', () => this.umschalten());
  }

  /** Beim Laden einmal fragen, was Sache ist. */
  async stand() {
    try {
      const roh = window.__djbAufzeichner?._roh?.bind(window.__djbAufzeichner) || window.fetch;
      const d = await roh(PFAD, { headers: { Accept: 'application/json' } }).then(r => r.json());
      this.laeuft = (d && d.ok && d.laeuft) ? d.laeuft : null;
    } catch (e) {
      this.laeuft = null;                 // ohne Server kein Knopf-Versprechen
    }
    this.zeichnen();
  }

  zeichnen() {
    if (!this.knopf) return;
    const k = this.knopf;
    k.disabled = this.beschaeftigt;
    k.classList.toggle('laeuft', !!this.laeuft);
    k.title = this.laeuft
      ? 'Aufzeichnung läuft - klicken zum Beenden und Speichern'
      : 'Aktionen und Logs mitschreiben, um daraus einen Testfall zu bauen';
    const text = k.querySelector('.djb-aufz-text');
    if (!this.laeuft) {
      text.textContent = 'Aufzeichnen';
      if (this.uhr) { clearInterval(this.uhr); this.uhr = null; }
      return;
    }
    const t0 = Date.parse(this.laeuft.start) || Date.now();
    const tick = () => {
      const s = Math.max(0, Math.round((Date.now() - t0) / 1000));
      text.textContent = 'Aufnahme ' + Math.floor(s / 60) + ':'
                       + String(s % 60).padStart(2, '0');
    };
    tick();
    if (!this.uhr) this.uhr = setInterval(tick, 1000);
  }

  /** Weiß → rot → weiß. Beim Beenden geht es zur Liste. */
  async umschalten() {
    if (this.beschaeftigt) return;
    this.beschaeftigt = true;
    this.zeichnen();
    try {
      if (!this.laeuft) {
        const d = await senden({ aktion: 'start', seite: location.pathname });
        // ``_start`` antwortet mit ``laeuft`` (dasselbe ``kurz()`` wie GET) -
        // nicht mit ``eintrag``; das trägt nur ``_name``.
        if (d && d.ok && d.laeuft) {
          this.laeuft = d.laeuft;
          // Ohne diesen Aufruf begänne die Aufnahme erst beim nächsten
          // Seitenwechsel mitzuschreiben - die Klicks auf DIESER Seite,
          // also die, für die man gerade gestartet hat, fehlten.
          await aufzeichnerStarten();
        }
      } else {
        // Puffer der laufenden Aufnahme zuerst rausschicken, dann beenden -
        // sonst fehlen dem gespeicherten Testfall die letzten Sekunden.
        const a = window.__djbAufzeichner;
        if (a && a.stoppen) await a.stoppen();
        await senden({ aktion: 'ende', id: this.laeuft.id });
        this.laeuft = null;
        this.zeichnen();
        location.href = ZIEL;
        return;
      }
    } catch (e) {
      // Ein gescheiterter Steuerbefehl darf die Seite nicht lahmlegen; der
      // nächste Klick fragt ohnehin neu.
    } finally {
      this.beschaeftigt = false;
      this.zeichnen();
      // Der Reiter „Aufzeichnen" zeigt denselben Zustand. Ohne diese Meldung
      // stünde dort weiter „Aufzeichnen", während der schwebende Knopf schon
      // rot ist - zwei Schalter, die sich widersprechen.
      document.dispatchEvent(new CustomEvent('djb-aufzeichnung-geaendert',
                                             { detail: { von: 'knopf' } }));
    }
  }
}

export async function aufzeichnerKnopf() {
  if (window.__djbAufzKnopf) return window.__djbAufzKnopf;
  const k = new AufzeichnerKnopf();
  window.__djbAufzKnopf = k;
  k.bauen();
  await k.stand();
  return k;
}

// Umgekehrt: Wird im Reiter geschaltet, holt der Knopf seinen Zustand nach.
document.addEventListener('djb-aufzeichnung-geaendert', (ev) => {
  if (ev.detail && ev.detail.von === 'knopf') return;      // die eigene Meldung
  const k = window.__djbAufzKnopf;
  if (k) k.stand();
});

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => aufzeichnerKnopf());
} else {
  aufzeichnerKnopf();
}

export { AufzeichnerKnopf };
