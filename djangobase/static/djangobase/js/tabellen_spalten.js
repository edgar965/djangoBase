/* Spalten einer djangoBase-Tabelle ein- und ausblenden - die Auswahl merkt sich jede Tabelle.
 * ==========================================================================================
 * OPT-IN: Die Vorlage `_tabelle.html` setzt `data-spaltenwahl` nur, wenn der Auftrag
 * `spaltenwahl: True` angibt. Ohne den Schalter bleibt jede Tabelle wie bisher.
 *
 *     <script type="module">
 *       import { TabellenSpalten } from '/static/djangobase/js/tabellen_spalten.js';
 *       TabellenSpalten.binden();
 *     </script>
 *
 * FESTE SPALTEN: `{"key": "auswahl", "fest": True}` bleibt immer sichtbar und steht
 * nicht im Menü (Auswahlkästchen, Schaltflächen in der Kopfzeile).
 *
 * AUSGEBLENDETE SPALTEN bleiben im DOM (nur mit `display:none`). Die Sortierung arbeitet
 * über die Position der Spalte, deshalb bleibt sie auch bei ausgeblendeten Spalten richtig.
 *
 * GEMERKT wird je Tabelle in localStorage unter dem Schlüssel `db-spalten:<data-sort-key>`.
 * Ohne localStorage (private Fenster, gesperrter Speicher) gilt die Standardansicht.
 */

const VORSATZ = 'db-spalten:';

export class TabellenSpalten {
  /** Alle Tabellen unterhalb von `wurzel` einrichten, die `data-spaltenwahl` tragen. */
  static binden(wurzel = document) {
    wurzel.querySelectorAll('table[data-spaltenwahl]').forEach((tabelle) => {
      if (tabelle.dataset.spaltenBunden) return;   // je Tabelle nur einmal
      tabelle.dataset.spaltenBunden = '1';
      TabellenSpalten._einrichten(tabelle);
    });
  }

  /** Die Schlüssel-Spalte der Kopfzeile, leer wenn die Tabelle keine Kopfzeile hat. */
  static _kopf(tabelle) {
    return tabelle.tHead && tabelle.tHead.rows[0] ? [...tabelle.tHead.rows[0].cells] : [];
  }

  static _speicherschluessel(tabelle) {
    return VORSATZ + (tabelle.dataset.sortKey || tabelle.id || 'tabelle');
  }

  static _gemerkt(tabelle) {
    try {
      const roh = localStorage.getItem(TabellenSpalten._speicherschluessel(tabelle));
      return roh ? JSON.parse(roh) : [];
    } catch (e) {
      return [];   // Speicher nicht lesbar: Standardansicht
    }
  }

  static _merken(tabelle, ausgeblendet) {
    try {
      localStorage.setItem(TabellenSpalten._speicherschluessel(tabelle), JSON.stringify(ausgeblendet));
    } catch (e) {
      // Speicher voll oder gesperrt: die Auswahl gilt nur für diese Ansicht
    }
  }

  /** Blendet die Spalten aus, deren Schlüssel in `ausgeblendet` steht. */
  static _anwenden(tabelle, ausgeblendet) {
    const keys = TabellenSpalten._kopf(tabelle).map((th) => th.dataset.key);
    for (const zeile of tabelle.rows) {
      for (let i = 0; i < zeile.cells.length; i++) {
        zeile.cells[i].classList.toggle('db-spalte-aus', ausgeblendet.includes(keys[i]));
      }
    }
  }

  static _einrichten(tabelle) {
    const frei = TabellenSpalten._kopf(tabelle).filter(
      (th) => th.dataset.key && !th.hasAttribute('data-spalte-fest')
    );
    if (!frei.length) return;

    let ausgeblendet = TabellenSpalten._gemerkt(tabelle).filter(
      (key) => frei.some((th) => th.dataset.key === key)
    );

    const leiste = document.createElement('div');
    leiste.className = 'db-spalten-leiste';
    const knopf = document.createElement('button');
    knopf.type = 'button';
    knopf.className = 'db-spalten-knopf';
    knopf.innerHTML = '<i class="bi bi-layout-three-columns"></i> Spalten';
    const menue = document.createElement('div');
    menue.className = 'db-spalten-menue';
    menue.hidden = true;

    for (const th of frei) {
      const zeile = document.createElement('label');
      zeile.className = 'db-spalten-eintrag';
      const kasten = document.createElement('input');
      kasten.type = 'checkbox';
      kasten.value = th.dataset.key;
      kasten.checked = !ausgeblendet.includes(th.dataset.key);
      kasten.addEventListener('change', () => {
        ausgeblendet = frei
          .map((k) => k.dataset.key)
          .filter((key) => !menue.querySelector(`input[value="${CSS.escape(key)}"]`).checked);
        TabellenSpalten._merken(tabelle, ausgeblendet);
        TabellenSpalten._anwenden(tabelle, ausgeblendet);
      });
      zeile.append(kasten, document.createTextNode(' ' + (th.textContent.trim() || th.dataset.key)));
      menue.appendChild(zeile);
    }

    knopf.addEventListener('click', () => { menue.hidden = !menue.hidden; });
    leiste.append(knopf, menue);

    const ziel = tabelle.closest('.db-tabelle-rahmen') || tabelle;
    ziel.parentNode.insertBefore(leiste, ziel);
    TabellenSpalten._anwenden(tabelle, ausgeblendet);
  }
}
