/* Aufzeichner — schreibt mit, was der Nutzer im UI tut.
 * =====================================================
 * AUFTRAG (Edgar, 20.08.2026): „wenn ich den aktiviere, werden logs und
 * aktionen erfasst und gespeichert, damit die Aktionen die ich im UI mache,
 * aufgezeichnet werden."
 *
 * WARUM DIESES MODUL AUF JEDER SEITE LIEGT
 * ----------------------------------------
 * Aufgezeichnet werden Wege, und ein Weg führt über Seiten. Läge der Aufzeichner
 * nur auf der Tests-Seite, wäre die Aufnahme beim ersten Klick auf einen
 * Menüpunkt vorbei — also genau dann, wenn es interessant wird. Ob gerade
 * aufgezeichnet wird, weiß der SERVER; jede Seite fragt es einmal beim Laden.
 *
 * WAS ES KOSTET, WENN NICHTS LÄUFT
 * --------------------------------
 * Eine Abfrage beim Laden, sonst nichts: Ohne laufende Aufnahme werden keine
 * Zuhörer angemeldet und `fetch` bleibt unangetastet. Ein Aufzeichner, der
 * jede Seite verlangsamt, wäre den Nutzen nicht wert.
 *
 * WAS AUFGEZEICHNET WIRD
 * ----------------------
 *   klick     Ziel (stabilste Kennung, s. `_kennung`) + sichtbarer Text
 *   eingabe   Feld + Wert (beim Verlassen, nicht je Tastendruck)
 *   auswahl   <select> + gewählter Wert
 *   seite     Adresse beim Laden und beim Verlassen
 *   abruf     Methode, Pfad und Status jedes fetch — das sind die Prüfpunkte
 *             des späteren Testfalls
 *
 * KEINE PASSWÖRTER. Felder vom Typ `password` und alles, dessen Name auf ein
 * Geheimnis deutet, werden als «…» abgelegt. Diese Datei landet im Projekt und
 * wird später zu Testcode — dort darf nichts Geheimes hineingeraten.
 */
const PFAD = '/hilfe/tests/aufzeichnung/';

/* Wie oft der Puffer zum Server geht. Nicht je Ereignis: Ein Klick, der eine
 * eigene Anfrage auslöst, verdoppelt die Last der Seite und erscheint im
 * Netzwerk-Protokoll neben jeder echten Aktion. */
const TAKT_MS = 3000;

/* Felder, deren Inhalt nie gespeichert wird. */
const GEHEIM = /pass|kennwort|secret|token|api[-_]?key/i;

class Aufzeichner {
  constructor(id, start) {
    this.id = id;
    this.t0 = Date.parse(start) || Date.now();
    this.puffer = [];
    this.timer = null;
    this._fetchEcht = null;
  }

  /* Sekunden seit Beginn — die gemeinsame Zeitachse mit den Server-Logs. */
  _t() { return Math.round((Date.now() - this.t0) / 100) / 10; }

  /** Die stabilste Kennung eines Elements.
   *
   *  Reihenfolge mit Absicht: Eine ID überlebt jeden Umbau, ein
   *  `data-test`-Attribut ist ausdrücklich dafür gesetzt, ein `name` gehört zum
   *  Formular. Erst danach kommt ein Pfad aus Tag und Klasse — der bricht beim
   *  nächsten CSS-Umbau, und genau deshalb steht er hinten. */
  static _kennung(el) {
    if (!el || !el.tagName) return '';
    if (el.id) return '#' + el.id;
    if (el.dataset && el.dataset.test) return '[data-test="' + el.dataset.test + '"]';
    if (el.name) return el.tagName.toLowerCase() + '[name="' + el.name + '"]';
    const klasse = (el.className || '').toString().trim().split(/\s+/)[0];
    return el.tagName.toLowerCase() + (klasse ? '.' + klasse : '');
  }

  static _text(el) {
    const t = (el.innerText || el.value || el.title || '').trim();
    return t.length > 80 ? t.slice(0, 80) + '…' : t;
  }

  static _wert(el) {
    if (el.type === 'password' || GEHEIM.test(el.name || el.id || '')) return '«…»';
    const v = (el.value === undefined ? '' : String(el.value));
    return v.length > 120 ? v.slice(0, 120) + '…' : v;
  }

  merken(ereignis) {
    this.puffer.push(Object.assign({ t: this._t() }, ereignis));
    if (this.puffer.length >= 40) this.senden();      // Stoßverkehr nicht stauen
  }

  async senden() {
    if (!this.puffer.length) return;
    const schritte = this.puffer.splice(0, this.puffer.length);
    try {
      await this._roh(PFAD, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
        body: JSON.stringify({ aktion: 'schritte', id: this.id, schritte }),
      });
    } catch (e) {
      // Verlorene Schritte sind ärgerlich, ein kaputtes UI wäre schlimmer.
      // Deshalb hier kein Wiederholen: Der nächste Puffer geht ohnehin raus.
    }
  }

  /* Der eigene Kanal zum Server — er darf NICHT durch die aufzeichnende
   * Hülle laufen, sonst zeichnet jeder Puffer seinen eigenen Versand auf und
   * die Aufnahme füttert sich selbst. */
  _roh(...args) { return (this._fetchEcht || window.fetch).apply(window, args); }

  starten() {
    this.merken({ art: 'seite', seite: location.pathname + location.search });

    document.addEventListener('click', ev => {
      const el = ev.target.closest('button, a, [role="button"], input[type="checkbox"], input[type="radio"]');
      if (!el) return;
      this.merken({ art: 'klick', ziel: Aufzeichner._kennung(el),
                    text: Aufzeichner._text(el),
                    seite: location.pathname });
    }, true);

    document.addEventListener('change', ev => {
      const el = ev.target;
      if (!el || !el.tagName) return;
      const tag = el.tagName.toLowerCase();
      if (tag === 'select') {
        this.merken({ art: 'auswahl', ziel: Aufzeichner._kennung(el),
                      wert: Aufzeichner._wert(el) });
      } else if (tag === 'input' || tag === 'textarea') {
        this.merken({ art: 'eingabe', ziel: Aufzeichner._kennung(el),
                      wert: Aufzeichner._wert(el) });
      }
    }, true);

    // Jeder Server-Abruf ist ein Prüfpunkt des späteren Tests: Pfad und Status
    // sagen, was funktioniert haben MUSS.
    this._fetchEcht = window.fetch.bind(window);
    const selbst = this;
    window.fetch = async function (...args) {
      const antwort = await selbst._fetchEcht(...args);
      try {
        const url = new URL(typeof args[0] === 'string' ? args[0] : args[0].url,
                            location.origin);
        if (url.pathname !== PFAD) {         // den eigenen Kanal nicht mitschreiben
          const methode = ((args[1] && args[1].method) || 'GET').toUpperCase();
          selbst.merken({ art: 'abruf', methode, pfad: url.pathname,
                          status: antwort.status });
        }
      } catch (e) { /* eine unlesbare URL ist kein Grund, den Abruf zu stören */ }
      return antwort;
    };

    // Beim Verlassen den Rest mitnehmen. `sendBeacon`, weil ein normales fetch
    // beim Entladen abgebrochen wird - genau der Puffer mit dem letzten Klick.
    window.addEventListener('pagehide', () => {
      if (!this.puffer.length) return;
      const daten = JSON.stringify({ aktion: 'schritte', id: this.id,
                                     schritte: this.puffer });
      try { navigator.sendBeacon(PFAD, new Blob([daten], { type: 'application/json' })); }
      catch (e) { /* dann eben nicht - der Weg ist trotzdem aufgezeichnet */ }
    });

    this.timer = setInterval(() => this.senden(), TAKT_MS);
  }
}

function csrf() {
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
}

/* Beim Laden EINMAL fragen, ob eine Aufnahme läuft. Nur dann wird etwas
 * angemeldet - ohne laufende Aufzeichnung bleibt die Seite unberührt. */
export async function aufzeichnerStarten() {
  if (window.__djbAufzeichner) return window.__djbAufzeichner;
  let d;
  try {
    d = await fetch(PFAD, { headers: { 'Accept': 'application/json' } }).then(r => r.json());
  } catch (e) { return null; }
  if (!d || !d.ok || !d.laeuft) return null;
  const a = new Aufzeichner(d.laeuft.id, d.laeuft.start);
  window.__djbAufzeichner = a;
  a.starten();
  return a;
}

aufzeichnerStarten();

export { Aufzeichner };
