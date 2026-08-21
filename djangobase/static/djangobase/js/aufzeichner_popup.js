/* Das Aufzeichnungs-Popup — ein Fenster über jeder Seite.
 * ======================================================
 * AUFTRAG (Edgar, 21.08.2026):
 *
 *     „Ein Popup bauen, das die ganze Zeit über der Webseite ist. Darin ein
 *      Button mit aufzeichnen anzeigen. Der Button ist erstmal weiss. Sobald
 *      man drauf klickt, wird er rot und die Aufzeichnung beginnt. beim
 *      erneuten Klick wird er wieder weiss, und das Fenster mit testaufzeichnen
 *      wird wieder geöffnet, der Test wird gespeichert."
 *
 * Das Fenster hat eine Titelzeile (zugleich Griff zum Verschieben), darin den
 * Knopf, darunter die Liste der Aufzeichnungen — sie klappt nach dem Beenden
 * auf, statt den Nutzer von seiner Seite wegzunavigieren.
 *
 * DIE FARBEN STEHEN INLINE, NICHT IN KLASSEN (belegt 21.08.2026): Auf
 * `/dax-handel/` blieb der Knopf weiß, obwohl Klasse und Beschriftung stimmten.
 * Chrome berechnete den Stil dieses Elements nicht neu; ein frisch eingefügter
 * Klon war jedes Mal richtig. Zusätzlich trägt das CSS keine Transition mehr
 * auf Farben — während einer laufenden Transition liefert der berechnete Stil
 * den Zwischenwert, und auf einer Seite mit dauernd rechnendem Chart kommen die
 * Animationsschritte nicht dran.
 */
import { AufzeichnungsListe } from '/static/djangobase/js/aufzeichner_liste.js';

const PFAD = '/hilfe/tests/aufzeichnung/';
const ORT = 'djb-aufz-ort';        // gemerkte Fensterposition
const ZU = 'djb-aufz-zu';          // eingeklappt ja/nein

const csrf = () => {
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
};

/** Zum Server — IMMER über das echte `fetch`.
 *
 *  `window.fetch` trägt bei laufender Aufnahme die mitschreibende Hülle; ein
 *  Aufruf darüber schriebe den eigenen Steuerbefehl in die Aufnahme. */
const roh = () => (window.__djbAufzeichner?._roh?.bind(window.__djbAufzeichner)
                   || window.fetch);

const senden = (daten) => roh()(PFAD, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
  body: JSON.stringify(daten),
}).then(r => r.json());

/** Die drei Zustandsbilder des Knopfes. */
const BILD = {
  bereit: { background: '#ffffff', color: '#111111',
            borderColor: 'rgba(0,0,0,.3)', opacity: '1' },
  laeuft: { background: '#dc2626', color: '#ffffff',
            borderColor: '#7f1d1d', opacity: '1' },
  wartet: { background: '#9ca3af', color: '#f3f4f6',
            borderColor: 'rgba(0,0,0,.3)', opacity: '.75' },
};

class AufzeichnerPopup {
  constructor() {
    this.laeuft = null;
    this.beschaeftigt = false;
    this.uhr = null;
    this.box = null;
    this.knopf = null;
    this.liste = null;
  }

  /** Das Fenster aufbauen — noch nicht eingehängt (siehe `einhaengen`). */
  bauen() {
    if (document.querySelector('[data-djb-aufzeichner-ui]')) return;
    const box = document.createElement('div');
    box.className = 'djb-aufz';
    // Absprache mit `aufzeichner.js`: Was hier drin geklickt wird, gehört zur
    // Bedienung und nicht in die Aufnahme.
    box.setAttribute('data-djb-aufzeichner-ui', '1');
    box.innerHTML =
      '<div class="djb-aufz-kopf">'
      + '<span class="djb-aufz-titel">Testaufzeichnung</span>'
      + '<button type="button" class="djb-aufz-klapp" title="Ein-/ausklappen">–</button>'
      + '</div>'
      + '<div class="djb-aufz-koerper">'
      + '<button type="button" class="djb-aufz-knopf">'
      + '<span class="djb-aufz-punkt"></span>'
      + '<span class="djb-aufz-text">Aufzeichnen</span></button>'
      + '<p class="djb-aufz-lage"></p>'
      + '<div class="djb-aufz-liste"></div>'
      + '<div class="djb-aufz-fuss">'
      + '<a href="/hilfe/tests/?tab=Aufzeichnen">Alle Aufzeichnungen &rarr;</a>'
      + '</div></div>';

    this.box = box;
    this.knopf = box.querySelector('.djb-aufz-knopf');
    this.lage = box.querySelector('.djb-aufz-lage');
    this.liste = new AufzeichnungsListe(box.querySelector('.djb-aufz-liste'),
                                        senden, () => this.laden(),
                                        'aufzeichnungen-popup');
    this.knopf.addEventListener('click', () => this.umschalten());
    box.querySelector('.djb-aufz-klapp')
       .addEventListener('click', () => this.klappen());
    this.ziehbar(box.querySelector('.djb-aufz-kopf'));
    this.ortLesen();
    if (localStorage.getItem(ZU) === '1') box.classList.add('zu');
  }

  /** Erst einhängen, wenn der Zustand feststeht — kein sichtbarer Übergang. */
  einhaengen() {
    if (this.box && !this.box.isConnected) document.body.appendChild(this.box);
  }

  /* ── Fenster verschieben ───────────────────────────────────────────────── */

  ziehbar(griff) {
    let start = null;
    griff.addEventListener('mousedown', ev => {
      if (ev.target.closest('button')) return;      // der Klapp-Knopf zieht nicht
      const r = this.box.getBoundingClientRect();
      start = { x: ev.clientX, y: ev.clientY, l: r.left, t: r.top };
      ev.preventDefault();
    });
    document.addEventListener('mousemove', ev => {
      if (!start) return;
      // Von rechts/unten auf links/oben umstellen, sobald gezogen wird -
      // sonst zöge das Fenster in die falsche Richtung.
      const l = Math.max(0, Math.min(innerWidth - 60, start.l + ev.clientX - start.x));
      const t = Math.max(0, Math.min(innerHeight - 40, start.t + ev.clientY - start.y));
      Object.assign(this.box.style, { left: l + 'px', top: t + 'px',
                                      right: 'auto', bottom: 'auto' });
    });
    document.addEventListener('mouseup', () => {
      if (!start) return;
      start = null;
      const r = this.box.getBoundingClientRect();
      try { localStorage.setItem(ORT, JSON.stringify({ l: r.left, t: r.top })); }
      catch (e) { /* ohne Speicher eben nicht gemerkt */ }
    });
  }

  ortLesen() {
    let o = null;
    try { o = JSON.parse(localStorage.getItem(ORT) || 'null'); } catch (e) { o = null; }
    if (!o || typeof o.l !== 'number') return;
    // Nur übernehmen, wenn die Stelle im sichtbaren Bereich liegt: Ein Fenster,
    // das auf einem breiten Monitor abgelegt wurde, wäre auf dem Laptop weg.
    if (o.l > innerWidth - 60 || o.t > innerHeight - 40) return;
    Object.assign(this.box.style, { left: o.l + 'px', top: o.t + 'px',
                                    right: 'auto', bottom: 'auto' });
  }

  klappen() {
    const zu = this.box.classList.toggle('zu');
    this.box.querySelector('.djb-aufz-klapp').textContent = zu ? '+' : '–';
    try { localStorage.setItem(ZU, zu ? '1' : '0'); } catch (e) { /* egal */ }
  }

  /* ── Zustand ───────────────────────────────────────────────────────────── */

  async laden() {
    try {
      const d = await roh()(PFAD, { headers: { Accept: 'application/json' } })
        .then(r => r.json());
      this.laeuft = (d && d.ok && d.laeuft) ? d.laeuft : null;
      if (this.liste) this.liste.zeichnen(d && d.liste ? d.liste : []);
    } catch (e) {
      this.laeuft = null;
    }
    this.zeichnen();
    this.einhaengen();
  }

  zeichnen() {
    if (!this.knopf) return;
    const k = this.knopf;
    k.disabled = this.beschaeftigt;
    k.classList.toggle('laeuft', !!this.laeuft);
    Object.assign(k.style, BILD[this.beschaeftigt ? 'wartet'
                                : (this.laeuft ? 'laeuft' : 'bereit')]);
    const punkt = k.querySelector('.djb-aufz-punkt');
    if (punkt) {
      punkt.style.background = this.laeuft ? '#ffffff' : '#dc2626';
      punkt.style.borderColor = this.laeuft ? 'rgba(255,255,255,.8)'
                                            : 'rgba(0,0,0,.3)';
    }
    const text = k.querySelector('.djb-aufz-text');
    k.title = this.laeuft ? 'Aufzeichnung beenden und speichern'
                          : 'Klicks, Eingaben und Server-Abrufe mitschreiben';
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

  /** Weiß → rot → weiß. Beim Beenden klappt die Liste im Fenster auf. */
  async umschalten() {
    if (this.beschaeftigt) return;
    this.beschaeftigt = true;
    this.zeichnen();
    try {
      if (!this.laeuft) {
        const d = await senden({ aktion: 'start', seite: location.pathname });
        if (d && d.ok && d.laeuft) {
          this.laeuft = d.laeuft;
          // Ohne diesen Aufruf begänne die Aufnahme erst beim nächsten
          // Seitenwechsel mitzuschreiben - die Klicks auf DIESER Seite fehlten.
          const mod = await import('/static/djangobase/js/aufzeichner.js'
                                   + new URL(import.meta.url).search);
          await mod.aufzeichnerStarten();
        }
      } else {
        // Den Puffer der laufenden Aufnahme zuerst rausschicken, dann beenden -
        // sonst fehlen dem gespeicherten Testfall die letzten Sekunden.
        const a = window.__djbAufzeichner;
        if (a && a.stoppen) await a.stoppen();
        const d = await senden({ aktion: 'ende', id: this.laeuft.id });
        this.laeuft = null;
        const fertig = d && d.beendet;
        if (this.lage && fertig) {
          this.lage.textContent = 'Gespeichert: ' + fertig.n_schritte
            + ' Schritte, ' + fertig.n_logs + ' Log-Zeilen.';
        }
        this.box.classList.remove('zu');       // Ergebnis nicht hinter „+" verstecken
      }
    } catch (e) {
      if (this.lage) this.lage.textContent = 'Der Server hat nicht geantwortet.';
    } finally {
      this.beschaeftigt = false;
      this.zeichnen();
      await this.laden();
      document.dispatchEvent(new CustomEvent('djb-aufzeichnung-geaendert',
                                             { detail: { von: 'popup' } }));
    }
  }
}

// Wird im Reiter „Aufzeichnen" geschaltet, holt das Popup seinen Zustand nach.
document.addEventListener('djb-aufzeichnung-geaendert', (ev) => {
  if (ev.detail && ev.detail.von === 'popup') return;
  if (window.__djbAufzPopup) window.__djbAufzPopup.laden();
});

export async function aufzeichnerPopup() {
  if (window.__djbAufzPopup) return window.__djbAufzPopup;
  const p = new AufzeichnerPopup();
  window.__djbAufzPopup = p;
  p.bauen();
  await p.laden();
  return p;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => aufzeichnerPopup());
} else {
  aufzeichnerPopup();
}

export { AufzeichnerPopup };
