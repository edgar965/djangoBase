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
 *   abruf     -> GEPRÜFT, nicht nachgefahren. Ein POST würde seine Wirkung ein
 *                zweites Mal auslösen. Verglichen wird, was die nachgefahrenen
 *                Klicks von selbst auslösen (siehe `beobachten`).
 *
 * MEHRDEUTIGE SELEKTOREN
 * ----------------------
 * Der Aufzeichner nimmt die stabilste Kennung, die er findet — bei einem Knopf
 * ohne id/name ist das `button.dax-tab`, und davon gibt es auf einer Seite
 * mehrere. Er macht sie deshalb selbst eindeutig (Anker mit ID davor, sonst
 * die laufende Nummer als `nr`); hier gewinnt diese Nummer. Bleibt nur der
 * Text und ist auch der mehrdeutig, wird NICHT geraten, sondern der Schritt als
 * Fehlschlag gezählt: Ein falscher Klick geht als grün durch, ein gemeldeter
 * Fehlschlag nicht.
 */
import { Basiswurzel } from '/static/djangobase/js/basiswurzel.js';

const PFAD = Basiswurzel.weg('tests/aufzeichnung/');
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

/* ── Was WIRKLICH abgerufen wurde ──────────────────────────────────────────
 *
 * PUNKT 2 (Edgar, 21.08.2026): „Der Abspieler prueft nichts."
 *
 * Bis hierher fuhr er Klicks nach und meldete hoechstens „nicht gefunden". Die
 * aufgezeichneten Abrufe - Pfad und Status - lagen ungenutzt daneben, obwohl
 * genau sie die Zusicherung tragen, die aus einer Aufnahme wirklich folgt:
 * „Nach DIESEM Klick kam /api/ib/trade-chart/ mit 200."
 *
 * Deshalb legt sich der Abspieler dieselbe Huelle um `window.fetch` wie der
 * Aufzeichner und fuehrt Buch. Bei jedem `abruf`-Schritt wird verglichen; was
 * fehlt oder mit anderem Status kam, zaehlt als abweichend und steht am Ende
 * in der Bilanz.
 *
 * WARUM NICHT NACHFAHREN: Ein aufgezeichnetes POST wuerde seine Wirkung ein
 * zweites Mal ausloesen - eine Order, ein geloeschtes System. Geprueft wird,
 * was die nachgefahrenen KLICKS von selbst ausloesen. */
const GESEHEN = [];
let _fetchEcht = null;

function beobachten() {
  if (_fetchEcht) return;
  _fetchEcht = window.fetch.bind(window);
  window.fetch = async function (...args) {
    const antwort = await _fetchEcht(...args);
    try {
      const url = new URL(typeof args[0] === 'string' ? args[0] : args[0].url,
                          location.origin);
      if (url.pathname !== PFAD) {          // den eigenen Kanal nicht mitzaehlen
        GESEHEN.push({
          methode: ((args[1] && args[1].method) || 'GET').toUpperCase(),
          pfad: url.pathname,
          status: antwort.status,
        });
        if (GESEHEN.length > 400) GESEHEN.splice(0, GESEHEN.length - 400);
      }
    } catch (e) { /* eine unlesbare URL ist kein Grund, den Abruf zu stoeren */ }
    return antwort;
  };
}

/** Kam dieser Abruf - und mit welchem Ergebnis?
 *
 *  Gesucht wird ueber die GANZE Seite hinweg, nicht nur seit dem letzten
 *  Klick: Ein Abruf, den das Laden der Seite ausloest, steht in der Aufnahme
 *  vor dem ersten Klick, kommt beim Abspielen aber waehrend der Navigation.
 *  Ein Treffer wird verbraucht (`weg`), damit zwei gleiche Erwartungen nicht
 *  von einem einzigen Abruf erfuellt werden. */
function abrufPruefen(s) {
  // EIN POLL IST KEINE STÜCKZAHL (Fehlalarm gemessen 21.08.2026): Steht in der
  // Aufnahme ``n > 1``, war das ein wiederkehrender Abruf im Sekundentakt -
  // fünfmal Chart, neunmal Automatik. Der Abspieler läuft schneller durch und
  // sieht davon weniger; die erste Fassung meldete deshalb „kam nicht", obwohl
  // der Pfad sehr wohl geantwortet hatte. Bei einem Poll zählt: kam er
  // überhaupt, und mit welchem Status. Nur ein EINZELNER Abruf wird verbraucht,
  // damit zwei getrennte Erwartungen nicht von einem Treffer erfüllt werden.
  const poll = (s.n || 1) > 1;
  const passt = g => g.pfad === s.pfad && g.methode === (s.methode || 'GET');
  const i = GESEHEN.findIndex(g => passt(g) && (poll || !g.weg));
  if (i < 0) return { fehlt: true };
  if (!poll) GESEHEN[i].weg = true;
  const ist = GESEHEN[i].status;
  return (s.status == null || ist === s.status)
    ? { ok: true }
    : { status: ist, erwartet: s.status };
}

export class Abspieler {
  /** Einen Lauf beginnen — von der Liste oder aus dem Bereich. */
  static async starten(id, name) {
    schreib({ id, i: 0, fehler: 0, abweichungen: [], name: name || id });
    Abspieler.bereichZeigen();
    beobachten();
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
    // Die Huelle MUSS vor dem ersten Schritt stehen, sonst entgehen ihr die
    // Abrufe, die das Laden dieser Seite ausloest - und genau die stehen in
    // der Aufnahme direkt hinter dem `seite`-Schritt.
    if (lies()) { beobachten(); await Abspieler.weiter(); }
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
    if (s.art === 'abruf') {
      // Erst kurz Luft lassen: Der Klick davor hat den Abruf gerade erst
      // angestossen, und `fetch` braucht seine Zeit.
      await schlafen(400);
      const urteil = abrufPruefen(s);
      if (!urteil.ok) {
        const stand = lies();
        if (stand) {
          const abw = (stand.abweichungen || []).concat([{
            pfad: s.pfad,
            was: urteil.fehlt ? 'kam nicht'
                              : urteil.status + ' statt ' + urteil.erwartet,
          }]);
          schreib({ ...stand, abweichungen: abw.slice(0, 40) });
        }
      }
      return true;
    }

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
        // DIE NUMMER GEWINNT (21.08.2026): Der Aufzeichner legt sie nur an,
        // wenn sein Selektor mehrdeutig blieb - dann zeigt sie auf genau ein
        // Element. Vorher entschied allein der Text, und bei zwei Knöpfen mit
        // gleicher Beschriftung wurde der erste geklickt: Der Schritt galt als
        // ausgeführt, geprüft wurde etwas anderes.
        if (typeof s.nr === 'number' && treffer[s.nr]) return treffer[s.nr];
        const text = (s.text || '').trim();
        const passend = treffer.filter(el => (el.textContent || '').trim() === text);
        if (passend.length === 1) return passend[0];
        // Weder Nummer noch eindeutiger Text: NICHT raten. Ein falscher Klick
        // ist schlimmer als ein gemeldeter Fehlschlag.
        return null;
      }
      await schlafen(200);
    }
    return null;
  }

  /* ── Der Bereich in der Sidebar ────────────────────────────────────────── */

  /** Der Bereich — aus der Sidebar, oder selbst angelegt.
   *
   *  Wie beim Aufnahme-Bereich: Projekte mit eigener Basis-Vorlage erben
   *  ``_sidebar.html`` nicht (Befund aus CamTrack, 21.08.2026). Fehlt das
   *  Markup, entsteht es hier — schwebend unter dem Aufnahme-Bereich. */
  static box() {
    let b = document.getElementById('djb-absp');
    if (b || !document.body) return b;
    b = document.createElement('div');
    b.className = 'djb-aufz djb-absp djb-aufz-frei djb-absp-frei';
    b.id = 'djb-absp';
    b.hidden = true;
    b.setAttribute('data-djb-aufzeichner-ui', '1');
    b.innerHTML =
      '<div class="djb-aufz-kopf">'
      + '<span class="djb-aufz-titel">Abspieler</span>'
      + '<button type="button" class="djb-aufz-zuknopf" title="Bereich ausblenden">'
      + '\u00d7</button></div>'
      + '<select class="djb-absp-wahl"></select>'
      + '<button type="button" class="djb-absp-knopf">'
      + '<span class="djb-absp-pfeil">\u25b6</span>'
      + '<span class="djb-absp-text">Abspielen</span></button>'
      + '<p class="djb-aufz-zaehler djb-absp-lage"></p>';
    document.body.appendChild(b);
    return b;
  }

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
      const abw = (stand.fertig.abweichungen || []).length;
      const gut = !f && !abw;
      lage.innerHTML = (gut ? '✓ ' : '') + 'fertig · <b>' + stand.gesamt
        + '</b> Schritte'
        + (f ? ' · <span class="djb-absp-fehler">' + f + ' nicht gefunden</span>' : '')
        + (abw ? ' · <span class="djb-absp-fehler" title="'
                 + esc((stand.fertig.abweichungen || [])
                       .map(a => a.pfad + ': ' + a.was).join('\n'))
                 + '">' + abw + ' Abruf' + (abw === 1 ? '' : 'e')
                 + ' abweichend</span>' : '');
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
