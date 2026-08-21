/* Abspieler — fährt eine Aufzeichnung im UI nach.
 * ==============================================
 * ANSAGE (Edgar, 21.08.2026):
 *
 *     „Kannst du in der Liste bei jedeM Testcase auch einen Play Button
 *      einblenden, der die Aktionen ausführt, also das UI steuert?"
 *     „der abspieler kann auch auf der Hauptseite sein (unter dem Aufnahme), du
 *      kannst einen Button ‚Abspieler anzeigen' genau so bauen auf der Test
 *      Seite, wie den anderen"
 *
 * Bedient wird er also an zwei Stellen: über den Play-Knopf einer Zeile in der
 * Liste, oder über den Bereich in der Sidebar (Auswahl + Abspielen). Angezeigt
 * wird der Fortschritt immer im Sidebar-Bereich — er steht auf jeder Seite und
 * verdeckt nichts.
 *
 * WARUM DER ZUSTAND IM SPEICHER DES BROWSERS LIEGT
 * ------------------------------------------------
 * Eine Aufzeichnung führt über Seiten. Beim ersten `seite`-Schritt navigiert
 * der Abspieler — und damit ist sein eigener JavaScript-Kontext weg, mitten im
 * Ablauf. Der Fortschritt (welche Aufnahme, welcher Schritt) muss deshalb
 * dorthin, wo er eine Navigation überlebt: in den `localStorage`. Auf jeder
 * Seite sieht dieses Modul beim Laden nach, ob ein Lauf offen ist, und macht
 * an genau der Stelle weiter.
 *
 * WAS NACHGEFAHREN WIRD — UND WAS NICHT
 * -------------------------------------
 *   seite     -> `location.href`, wenn wir nicht schon dort sind
 *   klick     -> Element über den aufgezeichneten Selektor suchen und klicken
 *   eingabe   -> Wert setzen und `input`+`change` auslösen
 *   auswahl   -> dasselbe für `<select>`
 *   abruf     -> NICHT nachgefahren. Ein GET wäre harmlos, aber ein POST würde
 *                die Wirkung von damals ein zweites Mal auslösen. Abrufe sind
 *                Prüfpunkte, keine Aktionen; sie entstehen ohnehin von selbst,
 *                wenn die Klicks sie auslösen.
 *
 * MEHRDEUTIGE SELEKTOREN
 * ----------------------
 * Der Aufzeichner nimmt die stabilste Kennung, die er findet — bei einem Knopf
 * ohne id/name ist das `button.dax-tab`, und davon gibt es auf einer Seite
 * mehrere. Deshalb wird bei mehreren Treffern der mit dem aufgezeichneten TEXT
 * genommen. Findet sich keiner, wird der Schritt übersprungen und gezählt: Ein
 * Abspieler, der auf gut Glück irgendeinen Knopf drückt, ist gefährlicher als
 * einer, der zugibt, dass er etwas nicht gefunden hat.
 */
const PFAD = '/hilfe/tests/aufzeichnung/';
const LAUF = 'djb-aufz-lauf';       // {id, i, fehler, name} — überlebt Navigation
const WEG = 'djb-absp-weg';         // Bereich ausgeblendet ja/nein

/* Pause zwischen zwei Schritten. Ein UI braucht Zeit: Klicks lösen Abrufe aus,
 * Tabs bauen sich auf. Die aufgezeichneten Abstände nachzuspielen wäre die
 * andere Möglichkeit — sie würde eine Aufnahme mit Nachdenkpausen aber ebenso
 * lange abspielen, wie sie gedauert hat. */
const PAUSE_MS = 450;

/* Nach einer Navigation: so lange auf das Zielelement warten, bevor der Schritt
 * als „nicht gefunden" gilt. Seiten dieses Projekts bauen Teile ihres DOM erst
 * nach dem ersten Datenabruf auf. */
const WARTEN_MS = 4000;

const lies = () => {
  try { return JSON.parse(localStorage.getItem(LAUF) || 'null'); }
  catch (e) { return null; }
};

const schreib = (o) => {
  try {
    if (o) localStorage.setItem(LAUF, JSON.stringify(o));
    else localStorage.removeItem(LAUF);
  } catch (e) { /* ohne Speicher kein Abspielen über Seiten hinweg */ }
};

const schlafen = (ms) => new Promise(r => setTimeout(r, ms));

const esc = (t) => String(t == null ? '' : t)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;');

export class Abspieler {
  /** Einen Lauf beginnen — von der Liste oder aus dem Bereich. */
  static async starten(id, name) {
    schreib({ id, i: 0, fehler: 0, name: name || id });
    Abspieler.bereichZeigen();
    await Abspieler.weiter();
  }

  static abbrechen() {
    schreib(null);
    Abspieler.zeichnen();
  }

  /** Auf jeder Seite beim Laden: Läuft ein Abspielvorgang? */
  static async fortsetzen() {
    Abspieler.binden();
    Abspieler.zeichnen();
    if (lies()) await Abspieler.weiter();
  }

  /** Den nächsten Schritt ausführen — und den danach, bis eine Navigation kommt. */
  static async weiter() {
    let lauf = lies();
    if (!lauf) return;
    const daten = await fetch(PFAD + '?id=' + encodeURIComponent(lauf.id),
                              { headers: { Accept: 'application/json' } })
      .then(r => r.json()).catch(() => null);
    if (!daten || !daten.ok) { Abspieler.abbrechen(); return; }
    const schritte = daten.schritte || [];

    while (true) {
      lauf = lies();
      if (!lauf) return;                       // abgebrochen
      if (lauf.i >= schritte.length) {
        schreib(null);
        Abspieler.zeichnen({ fertig: lauf, gesamt: schritte.length });
        return;
      }
      Abspieler.zeichnen({ lauf, gesamt: schritte.length, schritt: schritte[lauf.i] });

      // Der Zähler wird VOR dem Ausführen erhöht: Navigiert der Schritt, ist
      // dieser Kontext gleich weg — und beim nächsten Laden soll der FOLGENDE
      // Schritt drankommen, nicht derselbe noch einmal.
      const s = schritte[lauf.i];
      schreib({ ...lauf, i: lauf.i + 1 });

      const weiterlaufen = await Abspieler.schritt(s, lauf);
      if (!weiterlaufen) return;               // Navigation: der Rest kommt drüben
      await schlafen(PAUSE_MS);
    }
  }

  /** Einen einzelnen Schritt ausführen. -> false, wenn navigiert wurde. */
  static async schritt(s, lauf) {
    if (s.art === 'abruf') return true;        // Prüfpunkt, keine Aktion

    if (s.art === 'seite') {
      const ziel = s.seite || '/';
      if (location.pathname + location.search === ziel) return true;
      location.href = ziel;
      return false;
    }

    const el = await Abspieler.finden(s);
    if (!el) {
      schreib({ ...lies(), fehler: (lauf.fehler || 0) + 1 });
      return true;
    }

    if (s.art === 'klick') { el.click(); return true; }

    if (s.art === 'eingabe' || s.art === 'auswahl') {
      // Passwörter stehen als «…» in der Aufnahme — sie werden nie gesetzt.
      if (s.wert === '«…»') return true;
      if (el.type === 'checkbox' || el.type === 'radio') {
        el.checked = (s.wert === 'true' || s.wert === '1' || s.wert === 'on');
      } else {
        el.value = s.wert == null ? '' : s.wert;
      }
      el.dispatchEvent(new Event('input', { bubbles: true }));
      el.dispatchEvent(new Event('change', { bubbles: true }));
    }
    return true;
  }

  /** Das Element zum Schritt — mit Warten und Textabgleich. */
  static async finden(s) {
    if (!s.ziel) return null;
    const frist = Date.now() + WARTEN_MS;
    while (Date.now() < frist) {
      let treffer = [];
      try { treffer = [...document.querySelectorAll(s.ziel)]; } catch (e) { return null; }
      // Die eigene Bedienung nie treffen — sonst hält sich ein Lauf selbst an.
      treffer = treffer.filter(el => !el.closest('[data-djb-aufzeichner-ui]'));
      if (treffer.length === 1) return treffer[0];
      if (treffer.length > 1) {
        const text = (s.text || '').trim();
        return treffer.find(el => (el.textContent || '').trim() === text) || treffer[0];
      }
      await schlafen(200);
    }
    return null;
  }

  /* ── Der Bereich in der Sidebar ────────────────────────────────────────── */

  static box() { return document.getElementById('djb-absp'); }

  static bereichZeigen() {
    try { localStorage.setItem(WEG, '0'); } catch (e) { /* egal */ }
    const b = Abspieler.box();
    if (b) b.hidden = false;
  }

  static binden() {
    const b = Abspieler.box();
    if (!b || b.dataset.gebunden === '1') return;
    b.dataset.gebunden = '1';
    b.querySelector('.djb-absp-knopf').addEventListener('click', async () => {
      if (lies()) { Abspieler.abbrechen(); return; }
      const wahl = b.querySelector('.djb-absp-wahl');
      const id = wahl.value;
      if (!id) return;
      await Abspieler.starten(id, wahl.options[wahl.selectedIndex].textContent);
    });
    b.querySelector('.djb-aufz-zuknopf').addEventListener('click', () => {
      if (lies()) return;                      // während eines Laufs gesperrt
      try { localStorage.setItem(WEG, '1'); } catch (e) { /* egal */ }
      b.hidden = true;
    });
    Abspieler.wahlFuellen();
  }

  /** Die Auswahlliste mit den vorhandenen Aufzeichnungen füllen. */
  static async wahlFuellen() {
    const b = Abspieler.box();
    if (!b) return;
    const wahl = b.querySelector('.djb-absp-wahl');
    const d = await fetch(PFAD, { headers: { Accept: 'application/json' } })
      .then(r => r.json()).catch(() => null);
    const liste = (d && d.ok && d.liste) ? d.liste.filter(e => e.n_schritte > 0) : [];
    const vorher = wahl.value;
    wahl.innerHTML = liste.length
      ? liste.map(e => `<option value="${esc(e.id)}">${esc(e.name)}`
                     + ` (${e.n_schritte})</option>`).join('')
      : '<option value="">keine Aufzeichnung</option>';
    if (vorher) wahl.value = vorher;
  }

  /** Knopf, Auswahl und Fortschrittszeile auf den Stand bringen. */
  static zeichnen(stand) {
    const b = Abspieler.box();
    if (!b) return;
    const lauf = lies();
    const knopf = b.querySelector('.djb-absp-knopf');
    const text = b.querySelector('.djb-absp-text');
    const wahl = b.querySelector('.djb-absp-wahl');
    const lage = b.querySelector('.djb-absp-lage');
    const x = b.querySelector('.djb-aufz-zuknopf');

    // Inline gesetzt, nicht über Klassen: Chrome hat den Stil eines solchen
    // Elements schon einmal nach einem Klassenwechsel nicht neu berechnet.
    Object.assign(knopf.style, lauf
      ? { background: '#dc2626', color: '#ffffff', borderColor: '#7f1d1d' }
      : { background: '#ffffff', color: '#111111', borderColor: 'rgba(0,0,0,.3)' });
    text.textContent = lauf ? 'Abbrechen' : 'Abspielen';
    b.querySelector('.djb-absp-pfeil').textContent = lauf ? '■' : '▶';
    wahl.disabled = !!lauf;
    x.disabled = !!lauf;                       // wie beim Aufnahme-Bereich
    x.title = lauf ? 'Erst den Lauf beenden' : 'Bereich ausblenden';

    if (stand && stand.fertig) {
      const f = stand.fertig.fehler || 0;
      lage.innerHTML = 'fertig · <b>' + stand.gesamt + '</b> Schritte'
        + (f ? ' · <span class="djb-absp-fehler">' + f + ' nicht gefunden</span>' : '');
    } else if (stand && stand.lauf) {
      const s = stand.schritt || {};
      lage.innerHTML = '<b>' + (stand.lauf.i + 1) + '/' + stand.gesamt + '</b> · '
        + esc(s.art || '') + ' ' + esc((s.ziel || s.seite || '').slice(0, 28));
    } else if (!lauf && !stand) {
      lage.textContent = '';
    }

    let weg = null;
    try { weg = localStorage.getItem(WEG); } catch (e) { weg = null; }
    // Ausgeblendet bleibt ausgeblendet — außer es läuft gerade etwas.
    b.hidden = (weg !== '0' && !lauf);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', () => Abspieler.fortsetzen());
} else {
  Abspieler.fortsetzen();
}
