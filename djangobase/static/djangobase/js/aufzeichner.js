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
import { Basiswurzel } from '/static/djangobase/js/basiswurzel.js';

const PFAD = Basiswurzel.weg('tests/aufzeichnung/');

/* Wie oft der Puffer zum Server geht. Nicht je Ereignis: Ein Klick, der eine
 * eigene Anfrage auslöst, verdoppelt die Last der Seite und erscheint im
 * Netzwerk-Protokoll neben jeder echten Aktion. */
const TAKT_MS = 3000;

/* Felder, deren Inhalt nie gespeichert wird. */
const GEHEIM = /pass|kennwort|secret|token|api[-_]?key/i;

/* Die eigene Bedienung zeichnet sich NICHT selbst auf. Ohne das stünde in jeder
 * Aufnahme als erster Schritt der Klick auf „Aufzeichnen" und als letzter der
 * auf „Beenden" - zwei Schritte, die der erzeugte Testfall nachspielen würde,
 * und die mit dem aufgezeichneten Weg nichts zu tun haben. */
const EIGEN = '[data-djb-aufzeichner-ui]';

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
    const einfach = el.tagName.toLowerCase() + (klasse ? '.' + klasse : '');
    return Aufzeichner._eindeutig(el, einfach);
  }

  /** Aus einem mehrdeutigen Selektor einen eindeutigen machen.
   *
   *  DAS PROBLEM (21.08.2026): `button.dax-tab` gibt es auf der Dax-Seite
   *  viermal. Der Abspieler löste das über den sichtbaren TEXT auf - und nahm
   *  bei gleichem Text den ersten Treffer. Dann klickt er den falschen Knopf,
   *  ohne dass jemand es merkt: Der Schritt gilt als ausgeführt, der Testfall
   *  als grün, und geprüft wurde etwas anderes.
   *
   *  Zwei Stufen, in dieser Reihenfolge:
   *
   *  1. **Anker mit ID davor.** Findet sich ein Vorfahr mit ``id``, wird er
   *     vorangestellt (`#panel button.dax-tab`). Das überlebt einen Umbau
   *     besser als eine Positionsangabe - ein neuer Knopf DAVOR verschiebt
   *     keinen Index.
   *  2. **Position als letzte Rettung.** Bleibt es mehrdeutig, kommt die
   *     laufende Nummer unter den Treffern dazu (``nr``). Sie ist zerbrechlich,
   *     aber ehrlich: Sie zeigt auf genau ein Element.
   *
   *  Ist der einfache Selektor schon eindeutig, bleibt er unverändert - jede
   *  Zusatzangabe wäre eine weitere Stelle, die beim nächsten Umbau bricht. */
  static _eindeutig(el, einfach) {
    try {
      if (document.querySelectorAll(einfach).length <= 1) return einfach;
    } catch (e) {
      return einfach;                    // unbrauchbarer Selektor - nicht schlimmer machen
    }
    for (let v = el.parentElement; v; v = v.parentElement) {
      if (!v.id) continue;
      const mitAnker = '#' + v.id + ' ' + einfach;
      try {
        if (document.querySelectorAll(mitAnker).length === 1) return mitAnker;
      } catch (e) { /* weiter oben suchen */ }
      break;                             // der nächste Anker reicht oder keiner
    }
    return einfach;                      // Position trägt ``_nr`` bei (s. merken)
  }

  /** Der wievielte Treffer des Selektors ist dieses Element? (-1 = unbekannt) */
  static _nr(el, ziel) {
    if (!ziel) return -1;
    try {
      const alle = [...document.querySelectorAll(ziel)];
      return alle.length > 1 ? alle.indexOf(el) : -1;
    } catch (e) {
      return -1;
    }
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

  /** Ein Ereignis vormerken - Wiederholungen desselben Abrufs verdichtet.
   *
   *  WARUM VERDICHTET (gemessen 21.08.2026): Auf der Paper-Seite fragt die
   *  Oberfläche im SEKUNDENTAKT nach Konto, Automatik und Chart. Sechs Sekunden
   *  Klicken ergaben deshalb **115 Schritte**, von denen rund hundert derselbe
   *  Poll waren. Ein daraus gebauter Testfall prüfte hundertmal dasselbe und
   *  vergäbe den Blick auf die zwei Klicks, um die es ging.
   *
   *  Zusammengefasst wird nur, was DIREKT hintereinander kommt und in Methode,
   *  Pfad und Status übereinstimmt - dann steht ``n`` dafür, wie oft. Ein
   *  Poll, der plötzlich 500 liefert, bricht die Kette und bleibt sichtbar;
   *  genau der wäre die interessante Zeile. Klicks und Eingaben werden NIE
   *  zusammengefasst: Zweimal auf denselben Knopf ist etwas anderes als einmal. */
  merken(ereignis) {
    const letzter = this.puffer[this.puffer.length - 1];
    if (ereignis.art === 'abruf' && letzter && letzter.art === 'abruf'
        && letzter.methode === ereignis.methode && letzter.pfad === ereignis.pfad
        && letzter.status === ereignis.status) {
      letzter.n = (letzter.n || 1) + 1;
      letzter.t_bis = this._t();
      return;
    }
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
      if (!el || el.closest(EIGEN)) return;
      const ziel = Aufzeichner._kennung(el);
      const nr = Aufzeichner._nr(el, ziel);
      this.merken({ art: 'klick', ziel, text: Aufzeichner._text(el),
                    seite: location.pathname,
                    ...(nr >= 0 ? { nr } : {}) });
    }, true);

    document.addEventListener('change', ev => {
      const el = ev.target;
      if (!el || !el.tagName || el.closest(EIGEN)) return;
      const tag = el.tagName.toLowerCase();
      const ziel = Aufzeichner._kennung(el);
      const nr = Aufzeichner._nr(el, ziel);
      const zusatz = nr >= 0 ? { nr } : {};
      if (tag === 'select') {
        this.merken({ art: 'auswahl', ziel, wert: Aufzeichner._wert(el), ...zusatz });
      } else if (tag === 'input' || tag === 'textarea') {
        this.merken({ art: 'eingabe', ziel, wert: Aufzeichner._wert(el), ...zusatz });
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

    // Beim Verlassen den Rest mitnehmen - mit `keepalive`, NICHT mit
    // `sendBeacon` (Fehler gemessen 21.08.2026).
    //
    // `sendBeacon` kann keine Header setzen, also auch kein X-CSRFToken. Der
    // Endpunkt ist bewusst nicht csrf_exempt (er schreibt eine Datei ins
    // Projekt) und hat jeden Beacon mit **403** abgewiesen - im Serverlog
    // sichtbar als einzelne 403-Zeile am Ende jeder Aufnahme. Folge: Bei jedem
    // Seitenwechsel gingen bis zu drei Sekunden verloren, und zwar genau die um
    // den Klick herum, der die Navigation ausgeloest hat. In der Gegenprobe
    // fehlte der Startpunkt `/dax-handel/` komplett.
    //
    // `fetch(..., {keepalive: true})` ueberlebt das Entladen genauso, darf aber
    // Header tragen. Grenze sind 64 KB - ein Puffer mit hoechstens 40 Schritten
    // liegt weit darunter.
    window.addEventListener('pagehide', () => {
      // ERST ENTNEHMEN, DANN SENDEN (Fehler gefunden 21.08.2026): Hier stand
      // ``schritte: this.puffer`` ohne Leeren. Der Beacon ging raus, der Puffer
      // blieb voll - und wenn danach noch ein Timer-Tick kam (oder die Seite
      // doch nicht entladen wurde), schickte ``senden`` denselben Inhalt ein
      // zweites Mal. In einer Aufnahme über zwei Seiten standen daraufhin sieben
      // Schritte doppelt, mit identischen Zeitstempeln: derselbe Klick, zweimal
      // - im erzeugten Testfall wäre er zweimal nachgefahren worden.
      if (this.timer) { clearInterval(this.timer); this.timer = null; }
      if (!this.puffer.length) return;
      const schritte = this.puffer.splice(0, this.puffer.length);
      try {
        this._roh(PFAD, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
          body: JSON.stringify({ aktion: 'schritte', id: this.id, schritte }),
          keepalive: true,
        });
      } catch (e) { /* dann eben nicht - der Weg ist trotzdem aufgezeichnet */ }
    });

    this.timer = setInterval(() => this.senden(), TAKT_MS);
  }

  /** Aufnahme beenden, ohne die Seite neu zu laden.
   *
   *  DIE HUELLE MUSS ZURUECK (sonst bleibt sie fuer immer liegen): Beim Start
   *  ersetzt ``starten`` das globale ``fetch`` durch eine mitschreibende
   *  Fassung. Wer nur den Timer abschaltet, laesst diese Huelle stehen - sie
   *  meldet dann an eine beendete Aufnahme, und die naechste Aufnahme legt eine
   *  ZWEITE Huelle darueber. Nach drei Laeufen liefe jeder Abruf der Seite durch
   *  drei Schichten.
   *
   *  Der Rest des Puffers geht noch raus: Der letzte Klick ist meistens der
   *  interessanteste - er ist der Grund, warum aufgezeichnet wurde. */
  async stoppen() {
    if (this.timer) { clearInterval(this.timer); this.timer = null; }
    if (this._fetchEcht) { window.fetch = this._fetchEcht; this._fetchEcht = null; }
    await this.senden();
    if (window.__djbAufzeichner === this) window.__djbAufzeichner = null;
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
