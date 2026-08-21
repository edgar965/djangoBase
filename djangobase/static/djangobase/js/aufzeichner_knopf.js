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
/* MIT DERSELBEN ?v=-QUERY IMPORTIEREN (Fehler gemessen 21.08.2026)
 * ---------------------------------------------------------------
 * Hier stand ein statischer Import OHNE Query, waehrend `_shell.html` dieselbe
 * Datei als `aufzeichner.js?v=1787...` laedt. Fuer den Browser sind das ZWEI
 * Module: `aufzeichner.js` wurde zweimal ausgewertet, also lief
 * `aufzeichnerStarten()` zweimal, und es gab ZWEI Aufzeichner mit eigenen
 * Puffern. Beide schrieben dieselben Klicks und Abrufe mit - in der Aufnahme
 * standen neun Schritte doppelt, mit identischen Zeitstempeln.
 *
 * `import.meta.url` traegt die Query DIESES Moduls (das Script-Tag setzt sie).
 * Damit zeigt der dynamische Import auf exakt dieselbe URL wie das Tag: eine
 * Instanz - und das Cache-Busting bleibt erhalten. */
const { aufzeichnerStarten } = await import(
  '/static/djangobase/js/aufzeichner.js' + new URL(import.meta.url).search);

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
    this.box = null;
    this.knopf = null;
  }

  /** Das schwebende Fenster anlegen - einmal je Seite.
   *
   *  NOCH NICHT EINGEHÄNGT (Fehler 21.08.2026): Die erste Fassung hängte den
   *  Knopf sofort ein - gesperrt und grau - und entsperrte ihn, sobald der
   *  Server geantwortet hatte. Auf ``/dax-handel/`` blieb er danach DAUERHAFT
   *  grau: ``disabled`` war false, die Klasse entfernt, die einzige passende
   *  CSS-Regel sagte weiß, und ``getComputedStyle`` lieferte trotzdem #9ca3af.
   *  Nachgewiesen mit einem Klon desselben Elements - der Klon war weiß, das
   *  Original blieb grau. Chrome hatte den Stil nach dem Entsperren nicht neu
   *  berechnet.
   *
   *  Für den Nutzer sah das aus, als sei der Knopf gar nicht da („das popup ist
   *  nicht drin"). Statt gegen die Invalidierung anzukämpfen, entfällt der
   *  Übergang: Das Element kommt fertig ins DOM, mit dem Zustand, den es
   *  behalten soll. Sichtbar wird es dadurch einen Wimpernschlag später - dafür
   *  nie falsch. */
  bauen() {
    if (document.querySelector('[data-djb-aufzeichner-ui]')) return;
    const box = document.createElement('div');
    box.className = 'djb-aufz';
    // Das Attribut ist die Absprache mit ``aufzeichner.js``: Was hier drin
    // geklickt wird, gehört zur Bedienung und nicht in die Aufnahme.
    box.setAttribute('data-djb-aufzeichner-ui', '1');
    box.innerHTML =
      '<button type="button" class="djb-aufz-knopf">'
      + '<span class="djb-aufz-punkt"></span>'
      + '<span class="djb-aufz-text">Aufzeichnen</span></button>';
    this.box = box;
    this.knopf = box.querySelector('button');
    this.knopf.addEventListener('click', () => this.umschalten());
  }

  /** Jetzt sichtbar machen - der Zustand steht fest. */
  einhaengen() {
    if (this.box && !this.box.isConnected) document.body.appendChild(this.box);
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
    this.einhaengen();
  }

  /** Die drei Zustandsbilder - als INLINE-Stil, nicht ueber CSS-Klassen.
   *
   *  WARUM SO HÄSSLICH (belegt 21.08.2026): Auf ``/dax-handel/`` rechnet Chrome
   *  den Stil dieses Elements nach einem Klassen- oder Attributwechsel nicht neu.
   *  Zweimal nachgewiesen: (1) nach dem Entsperren blieb der Knopf grau, obwohl
   *  ``matches(':disabled')`` false war und die einzige passende Regel weiß
   *  sagte; (2) nach ``classList.add('laeuft')`` blieb er weiß, obwohl Klasse
   *  und Beschriftung („Aufnahme 0:04") standen. Ein Klon desselben Elements
   *  bekam jedes Mal die richtige Farbe - das Original nie.
   *
   *  Ein Inline-Stil geht direkt in die Berechnung und kann von keiner
   *  ausgefallenen Invalidierung verschluckt werden. Die Klassen bleiben für
   *  Hover und den blinkenden Punkt gesetzt, und die CSS-Regeln bleiben als
   *  Grundlage stehen - fiele dieses Modul aus, sähe der Knopf trotzdem richtig
   *  aus. */
  static BILD = {
    bereit: { background: '#ffffff', color: '#111111',
              borderColor: 'rgba(0,0,0,.25)', opacity: '.85' },
    laeuft: { background: '#dc2626', color: '#ffffff',
              borderColor: '#7f1d1d', opacity: '1' },
    wartet: { background: '#9ca3af', color: '#f3f4f6',
              borderColor: 'rgba(0,0,0,.25)', opacity: '.6' },
  };

  zeichnen() {
    if (!this.knopf) return;
    const k = this.knopf;
    k.disabled = this.beschaeftigt;
    k.classList.toggle('wartet', this.beschaeftigt);
    k.classList.toggle('laeuft', !!this.laeuft);
    const bild = AufzeichnerKnopf.BILD[
      this.beschaeftigt ? 'wartet' : (this.laeuft ? 'laeuft' : 'bereit')];
    Object.assign(k.style, bild);
    const punkt = k.querySelector('.djb-aufz-punkt');
    // Der Punkt ist ein KIND - dieselbe Invalidierung trifft ihn genauso.
    if (punkt) {
      punkt.style.background = this.laeuft ? '#ffffff' : '#dc2626';
      punkt.style.borderColor = this.laeuft ? 'rgba(255,255,255,.8)'
                                            : 'rgba(0,0,0,.3)';
    }
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
