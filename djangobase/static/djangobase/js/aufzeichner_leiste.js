/* Testaufzeichnung — der Bereich links oben im Hauptmenü.
 * ======================================================
 * ANSAGE (Edgar, 21.08.2026):
 *
 *     „wir können die aufzeichnung auch in einem Bereich links oben im
 *      Hauptmenü machen, mit einem X zum Beenden (X nur aktivierbar wenn die
 *      Aufzeichnung beendet ist)."
 *     „Im popup brauch ich NUR den Aufnahmen / beenden Button und eine
 *      Sekundenanzeige" … „du kannst dir schritte im Testfenster behalten"
 *
 * WARUM DER BEREICH UND NICHT DAS POPUP
 * -------------------------------------
 * Davor war das ein schwebendes Fenster. Es hat an einem Tag vier Fehler
 * produziert, die ALLE daher kamen, dass es ein Overlay über einer arbeitenden
 * Seite war:
 *
 *   1. Die Farb-Transition fror ein — auf `/dax-handel/` blieb der Knopf weiß,
 *      obwohl sein Inline-Stil rot war. Während einer laufenden Transition
 *      liefert der berechnete Stil den Zwischenwert, und auf einer Seite, die
 *      ununterbrochen einen Chart zeichnet, kommen die Animationsschritte nicht
 *      dran.
 *   2. Chrome berechnete den Stil des Elements nach einem Klassenwechsel nicht
 *      neu; ein frisch eingefügter Klon war jedes Mal richtig.
 *   3. Position und Größe mussten gemerkt und gegen fremde Bildschirmgrößen
 *      abgesichert werden.
 *   4. z-index gegen die Chart-Fenster des Projekts.
 *
 * Als Bereich in der Sidebar ist nichts davon nötig: Das Markup kommt fertig
 * vom Server (`_sidebar.html`), dieses Modul setzt nur noch Zustand und
 * Beschriftung. Über die djangoBase-Shell liegt die Sidebar auf jeder Seite —
 * die Aufnahme lässt sich also weiterhin überall starten, und sie läuft über
 * Seitenwechsel hinweg.
 */
const PFAD = '/hilfe/tests/aufzeichnung/';
const WEG = 'djb-aufz-weg';        // Bereich ausgeblendet ja/nein
const ZIEL = '/hilfe/tests/?tab=Aufzeichnen';   // wohin es nach dem Beenden geht

/* Wie oft die Schrittzahl beim Server nachgefragt wird. Die Sekunden laufen
 * lokal weiter; nur die SCHRITTE kennt der Server. */
const TAKT_MS = 2000;

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

const holen = (daten) => (daten
  ? roh()(PFAD, { method: 'POST',
                  headers: { 'Content-Type': 'application/json',
                             'X-CSRFToken': csrf() },
                  body: JSON.stringify(daten) })
  : roh()(PFAD, { headers: { Accept: 'application/json' } })).then(r => r.json());

/** Die drei Zustandsbilder des Knopfes — inline gesetzt, nicht über Klassen.
 *
 *  Das stammt aus der Popup-Zeit (Chrome berechnete den Stil nicht neu) und
 *  bleibt: Es kostet nichts und nimmt der Anzeige jede Abhängigkeit davon, ob
 *  eine Style-Invalidierung durchkommt. */
const BILD = {
  bereit: { background: '#ffffff', color: '#111111', borderColor: 'rgba(0,0,0,.3)' },
  laeuft: { background: '#dc2626', color: '#ffffff', borderColor: '#7f1d1d' },
  wartet: { background: '#9ca3af', color: '#f3f4f6', borderColor: 'rgba(0,0,0,.3)' },
};

class AufzeichnerLeiste {
  constructor(wurzel) {
    this.box = wurzel;
    this.knopf = wurzel.querySelector('.djb-aufz-knopf');
    this.zuknopf = wurzel.querySelector('.djb-aufz-zuknopf');
    this.zaehler = wurzel.querySelector('.djb-aufz-zaehler');
    this.laeuft = null;
    this.beschaeftigt = false;
    this.uhr = null;
    this.takt = null;
    this.knopf.addEventListener('click', () => this.umschalten());
    this.zuknopf.addEventListener('click', () => this.ausblenden());
  }

  /** X: Bereich weg. Zurück über Hilfe → Tests → Aufzeichnen. */
  ausblenden() {
    // Während einer Aufnahme ist das X gesperrt (Ansage) - hier nochmal
    // geprüft, damit ein Tastatur-Klick auf den gesperrten Knopf ins Leere
    // läuft statt eine laufende Aufnahme unsichtbar zu machen.
    if (this.laeuft) return;
    try { localStorage.setItem(WEG, '1'); } catch (e) { /* ohne Speicher eben nicht */ }
    this.box.hidden = true;
  }

  async laden() {
    try {
      const d = await holen();
      this.laeuft = (d && d.ok && d.laeuft) ? d.laeuft : null;
    } catch (e) {
      this.laeuft = null;
    }
    this.zeichnen();
  }

  zeichnen() {
    const k = this.knopf;
    k.disabled = this.beschaeftigt;
    k.classList.toggle('laeuft', !!this.laeuft);
    Object.assign(k.style, BILD[this.beschaeftigt ? 'wartet'
                                : (this.laeuft ? 'laeuft' : 'bereit')]);
    const punkt = k.querySelector('.djb-aufz-punkt');
    if (punkt) {
      punkt.style.background = this.laeuft ? '#ffffff' : '#dc2626';
      punkt.style.borderColor = this.laeuft ? 'rgba(255,255,255,.8)' : 'rgba(0,0,0,.3)';
    }
    k.querySelector('.djb-aufz-text').textContent = this.laeuft ? 'Beenden' : 'Aufnahme';
    k.title = this.laeuft ? 'Aufzeichnung beenden und speichern'
                          : 'Klicks, Eingaben und Server-Abrufe mitschreiben';

    // „X nur aktivierbar wenn die Aufzeichnung beendet ist" (Ansage).
    this.zuknopf.disabled = !!this.laeuft;
    this.zuknopf.title = this.laeuft
      ? 'Erst die Aufzeichnung beenden'
      : 'Bereich ausblenden (zurück über Hilfe → Tests → Aufzeichnen)';

    // Ausgeblendet bleibt ausgeblendet - AUSSER es läuft eine Aufnahme. Eine
    // Aufnahme, die niemand sieht, schreibt sonst stundenlang mit.
    let weg = null;
    try { weg = localStorage.getItem(WEG); } catch (e) { weg = null; }
    this.box.hidden = (weg === '1' && !this.laeuft);

    this.zaehlerLaufen();
  }

  /** Sekunden und Schritte. */
  zaehlerLaufen() {
    if (this.uhr) { clearInterval(this.uhr); this.uhr = null; }
    if (this.takt) { clearInterval(this.takt); this.takt = null; }
    if (!this.laeuft) return;          // nach dem Ende bleibt die Bilanz stehen

    const t0 = Date.parse(this.laeuft.start) || Date.now();
    const zeigen = () => {
      const s = Math.max(0, Math.round((Date.now() - t0) / 1000));
      const n = this.laeuft ? this.laeuft.n_schritte : 0;
      this.zaehler.innerHTML = '<b>' + Math.floor(s / 60) + ':'
        + String(s % 60).padStart(2, '0') + '</b> · ' + n + ' Schritte';
    };
    zeigen();
    this.uhr = setInterval(zeigen, 1000);
    const meiner = () => this.takt === kennung;
    const kennung = setInterval(async () => {
      try {
        const d = await holen();
        // NUR SCHREIBEN, WENN DIESER TAKT NOCH GILT: Beim Beenden war ein
        // Aufruf schon unterwegs, kam nach dem Abschalten zurück und
        // überschrieb die Meldung „gespeichert · N Schritte" wieder mit der
        // laufenden Sekundenzahl.
        if (!meiner()) return;
        if (d && d.ok && d.laeuft) { this.laeuft = d.laeuft; zeigen(); }
      } catch (e) { /* ein verpasster Takt ist kein Grund für eine Meldung */ }
    }, TAKT_MS);
    this.takt = kennung;
  }

  /** Weiß → rot → weiß. */
  async umschalten() {
    if (this.beschaeftigt) return;
    this.beschaeftigt = true;
    this.zeichnen();
    try {
      if (!this.laeuft) {
        const d = await holen({ aktion: 'start', seite: location.pathname });
        if (d && d.ok && d.laeuft) {
          this.laeuft = d.laeuft;
          // Ohne diesen Aufruf begänne die Aufnahme erst beim nächsten
          // Seitenwechsel mitzuschreiben — die Klicks auf DIESER Seite fehlten.
          const mod = await import('/static/djangobase/js/aufzeichner.js'
                                   + new URL(import.meta.url).search);
          await mod.aufzeichnerStarten();
        }
      } else {
        // Den Puffer der laufenden Aufnahme zuerst rausschicken, dann beenden —
        // sonst fehlen dem gespeicherten Testfall die letzten Sekunden.
        const a = window.__djbAufzeichner;
        if (a && a.stoppen) await a.stoppen();
        const d = await holen({ aktion: 'ende', id: this.laeuft.id });
        this.laeuft = null;
        this.beschaeftigt = false;
        this.zeichnen();
        const fertig = d && d.beendet;
        if (fertig) {
          this.zaehler.innerHTML = 'gespeichert · <b>' + fertig.n_schritte
            + '</b> Schritte';
        }
        document.dispatchEvent(new CustomEvent('djb-aufzeichnung-geaendert',
                                               { detail: { von: 'leiste' } }));
        // ZUR LISTE (Ansage 21.08.2026): „bei Klick auf Beenden soll der Tab
        // wechseln zu /hilfe/tests/, im Tab Aufzeichnen, damit ich den
        // Testcase sehe." Der kurze Aufschub lässt die Meldung „gespeichert ·
        // N Schritte" noch sichtbar werden - sonst wäre sie zwischen Klick und
        // Navigation nie zu lesen.
        setTimeout(() => { location.href = ZIEL; }, 600);
        return;
      }
    } catch (e) {
      this.zaehler.textContent = 'Der Server hat nicht geantwortet.';
    }
    this.beschaeftigt = false;
    this.zeichnen();
    document.dispatchEvent(new CustomEvent('djb-aufzeichnung-geaendert',
                                           { detail: { von: 'leiste' } }));
  }
}

// Wird im Reiter „Aufzeichnen" geschaltet, holt der Bereich seinen Zustand nach.
document.addEventListener('djb-aufzeichnung-geaendert', (ev) => {
  if (ev.detail && ev.detail.von === 'leiste') return;
  if (window.__djbAufzLeiste) window.__djbAufzLeiste.laden();
});

export async function aufzeichnerLeiste() {
  if (window.__djbAufzLeiste) return window.__djbAufzLeiste;
  const wurzel = document.getElementById('djb-aufz');
  if (!wurzel) return null;              // Seite ohne djangoBase-Sidebar
  const l = new AufzeichnerLeiste(wurzel);
  window.__djbAufzLeiste = l;
  await l.laden();
  return l;
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => aufzeichnerLeiste());
} else {
  aufzeichnerLeiste();
}

export { AufzeichnerLeiste };
