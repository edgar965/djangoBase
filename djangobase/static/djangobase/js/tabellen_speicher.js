/* TabellenSpeicher - wo die Tabellen ihre Einstellungen merken.
   ==========================================================================
   Spaltenbreiten (``tblBreiten:``), Sortierung (``dbTabSort:``), ausgeblendete
   Spalten (``db-spalten:``) und Spaltenreihenfolge (``tblReihe:``) - jeweils
   ein Text (JSON) unter einem Schluessel je Tabelle.

   OHNE WEITERES: localStorage wie bisher (je Browser).

   DAS ELEMENT ``#djb-tabellen`` (``{% djb_tabellen %}`` in ``_shell.html``,
   ``templatetags/djangobase_tabellen.py``) traegt die Schalter aus
   Einstellungen -> Tabellen: ``data-verschieben`` (Spalten umstellen,
   ``tabellen_reihenfolge.js``, Vorgabe aus) und ``data-anpassen`` (Breiten
   ziehen und merken, Vorgabe an). Fehlt es, gelten die Vorgaben.

   JE BENUTZER (04.11.2026 fuer StayNestor - Edgar: „merke dir die
   Einstellungen pro User“, „kannst du in djangobase machen, da es auch andere
   nutzen ggf.“; ``DJANGOBASE["tabellen_je_benutzer"] = True``): Dann steht im
   Element ``data-url`` und als Inhalt die Einstellungen des angemeldeten
   Benutzers (``TabellenEinstellung``), und jede Aenderung geht als POST
   ``{"schluessel": …, "wert": …}`` (``wert: null`` = vergessen) an
   ``data-url`` (``TabellenEinstellungSpeichern``).

   Was der Browser schon gemerkt hat, der Server aber noch nicht kennt, wird
   beim ersten Lesen einmal uebernommen und hochgeladen - wer umstellt,
   verliert seine gezogenen Breiten nicht.

   EIN ZUSTAND FUER ALLE MODULINSTANZEN: Dieselbe Datei kann unter zwei
   Adressen geladen sein (``/static/…`` und ``/statik/v-…/…``), dann gibt es
   zwei Klassen. Der Zustand liegt deshalb an ``window``, nicht an der Klasse -
   sonst laese die eine Instanz einen Wert, den die andere laengst geaendert
   hat. */

const ZUSTAND = '__djbTabellenSpeicher';

export class TabellenSpeicher {
  /** Der gemeinsame Zustand: ``null`` = nur localStorage, sonst {url, csrf, daten, verschieben, gesendet}. */
  static _zustand() {
    if (typeof window === 'undefined') return null;
    if (window[ZUSTAND] !== undefined) return window[ZUSTAND];
    let z = null;
    const el = typeof document !== 'undefined' && document.getElementById('djb-tabellen');
    if (el) {
      let daten = {};
      try { daten = JSON.parse(el.textContent || '{}') || {}; } catch (e) { daten = {}; }
      z = {
        url: el.dataset.url || '',
        csrf: el.dataset.csrf || TabellenSpeicher._cookie('csrftoken'),
        daten: daten,
        verschieben: el.dataset.verschieben === '1',
        anpassen: el.dataset.anpassen !== '0',
        gesendet: Object.assign({}, daten),
      };
    }
    window[ZUSTAND] = z;
    return z;
  }

  static _cookie(name) {
    const m = document.cookie.match(new RegExp('(?:^|; )' + name + '=([^;]*)'));
    return m ? decodeURIComponent(m[1]) : '';
  }

  /** Speichert der Server je Benutzer? */
  static jeBenutzer() {
    const z = TabellenSpeicher._zustand();
    return !!(z && z.url);
  }

  /** Spalten umstellen fuer alle Tabellen eingeschaltet? (Vorgabe aus) */
  static verschieben() {
    const z = TabellenSpeicher._zustand();
    return !!(z && z.verschieben);
  }

  /** Spaltenbreiten ziehen und merken? (Vorgabe an; Einstellungen -> Tabellen) */
  static anpassen() {
    const z = TabellenSpeicher._zustand();
    return !z || z.anpassen;
  }

  static _lokal(k) {
    try { return localStorage.getItem(k); } catch (e) { return null; }
  }

  /** Der gemerkte Text unter ``k`` - oder ``null``. */
  static lesen(k) {
    const z = TabellenSpeicher._zustand();
    if (!z || !z.url) return TabellenSpeicher._lokal(k);
    if (Object.prototype.hasOwnProperty.call(z.daten, k)) return z.daten[k];
    const lokal = TabellenSpeicher._lokal(k);
    if (lokal !== null) {               // einmalige Uebernahme aus dem Browser
      z.daten[k] = lokal;
      TabellenSpeicher._senden(z, k, lokal);
    }
    return lokal;
  }

  static schreiben(k, wert) {
    try { localStorage.setItem(k, wert); } catch (e) { /* Speicher voll/gesperrt */ }
    const z = TabellenSpeicher._zustand();
    if (!z || !z.url) return;
    z.daten[k] = wert;
    TabellenSpeicher._senden(z, k, wert);
  }

  static entfernen(k) {
    try { localStorage.removeItem(k); } catch (e) { /* egal */ }
    const z = TabellenSpeicher._zustand();
    if (!z || !z.url) return;
    delete z.daten[k];
    TabellenSpeicher._senden(z, k, null);
  }

  /** Sofort, aber nur bei geaendertem Wert (``TabellenBreiten._merkenAlle``
   *  schreibt bei jedem Loslassen alle Breiten). ``keepalive`` traegt die
   *  Anfrage auch ueber ein sofortiges Neuladen der Seite hinweg. */
  static _senden(z, k, wert) {
    if (z.gesendet[k] === wert || (wert === null && !(k in z.gesendet))) return;
    if (wert === null) delete z.gesendet[k];
    else z.gesendet[k] = wert;
    fetch(z.url, {
      method: 'POST',
      credentials: 'same-origin',
      keepalive: true,
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': z.csrf },
      body: JSON.stringify({ schluessel: k, wert: wert }),
    }).then((r) => {
      if (!r.ok) console.warn('[djangoBase] Tabellen-Einstellung %s nicht gespeichert: HTTP %s', k, r.status);
    }).catch(() => {
      console.warn('[djangoBase] Tabellen-Einstellung %s nicht gespeichert: keine Verbindung', k);
    });
  }
}
