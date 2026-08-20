/* Reiter „Aufzeichnen" — Schalter und Liste der Aufzeichnungen.
 * ==============================================================
 * AUFTRAG (Edgar, 20.08.2026): „Ein Aufzeichnen Button soll erscheinen, der
 * deaktiviert ist. wenn ich den aktiviere, werden logs und aktionen erfasst …
 * Mit Klick auf beenden ist die Aufzeichnung beendet. Vergib dem Test einen
 * Default Namen und speicher den in einer Liste. Die Liste ist eine sortierbare
 * Tabelle (nimm das djangoBase Template dafür). Darin IDs, Namen die ich
 * verändern kann, löschen buttons."
 *
 * WARUM DER SCHALTER ZUERST GESPERRT IST
 * --------------------------------------
 * Er wird erst freigegeben, wenn der Server geantwortet hat. Bis dahin ist
 * unbekannt, ob schon eine Aufnahme läuft — und ein Knopf, der in diesem
 * Moment „Aufzeichnen" anbietet, würde eine zweite starten wollen und
 * scheitern. Ein gesperrter Knopf, der gleich darauf die Wahrheit zeigt, ist
 * ehrlicher als ein sofort klickbarer, der etwas anderes tut als er sagt.
 *
 * DIE TABELLE WIRD IM BROWSER GEBAUT
 * ----------------------------------
 * `_tabelle.html` ist für Zeilen gedacht, die der View fertig liefert; hier
 * ändern sie sich während einer laufenden Aufnahme sekündlich. Deshalb dieselben
 * Klassen und Attribute (`db-tabelle sortable`, `data-sort-key`) und die beiden
 * JS-Module direkt — genau der Weg, den der Kopf jener Vorlage dafür nennt.
 */
import { TabellenSortierung } from '/static/djangobase/js/tabellen_sortierung.js';
import { TabellenBreiten } from '/static/djangobase/js/tabellen_breiten.js';

const PFAD = '/hilfe/tests/aufzeichnung/';

const csrf = () => {
  const m = document.cookie.match(/(?:^|;\s*)csrftoken=([^;]+)/);
  return m ? decodeURIComponent(m[1]) : '';
};

const senden = (daten) => fetch(PFAD, {
  method: 'POST',
  headers: { 'Content-Type': 'application/json', 'X-CSRFToken': csrf() },
  body: JSON.stringify(daten),
}).then(r => r.json());

const esc = (s) => String(s == null ? '' : s)
  .replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;')
  .replace(/"/g, '&quot;');

/** Sekunden lesbar: 47 s, 2:05 min. */
const dauer = (s) => (s < 60) ? Math.round(s) + ' s'
  : Math.floor(s / 60) + ':' + String(Math.round(s % 60)).padStart(2, '0') + ' min';

const zeit = (iso) => {
  const d = new Date(iso);
  return isNaN(d) ? '—' : d.toLocaleString('de-DE',
    { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
};

class Reiter {
  constructor() {
    this.schalter = document.getElementById('au-schalter');
    this.lage = document.getElementById('au-lage');
    this.tabelle = document.getElementById('au-tabelle');
    this.laeuft = null;
    this.ticker = null;
  }

  async laden() {
    const d = await fetch(PFAD, { headers: { Accept: 'application/json' } })
      .then(r => r.json()).catch(() => null);
    if (!d || !d.ok) {
      if (this.lage) this.lage.textContent = 'Zustand nicht abrufbar.';
      return;
    }
    this.laeuft = d.laeuft;
    this.zeichnen(d.liste || []);
  }

  zeichnen(liste) {
    this.schalterSetzen();
    if (this.tabelle) {
      this.tabelle.innerHTML = this.tabelleHtml(liste);
      TabellenSortierung.binden(this.tabelle);
      TabellenBreiten.binden(this.tabelle);
    }
  }

  schalterSetzen() {
    const b = this.schalter;
    if (!b) return;
    b.disabled = false;                       // ab jetzt kennt er die Wahrheit
    if (this.laeuft) {
      b.textContent = '⏹ Aufzeichnung beenden';
      b.classList.add('btn-danger');
      b.classList.remove('btn-outline-light');
      this.tickerStarten();
    } else {
      b.textContent = '⏺ Aufzeichnen';
      b.classList.remove('btn-danger');
      b.classList.add('btn-outline-light');
      this.tickerStoppen();
      if (this.lage) this.lage.textContent = '';
    }
  }

  /* Während der Aufnahme sekündlich zeigen, was zusammenkommt — sonst sieht
   * man dem Knopf nicht an, ob überhaupt etwas ankommt. */
  tickerStarten() {
    if (this.ticker) return;
    const zeigen = async () => {
      const d = await fetch(PFAD, { headers: { Accept: 'application/json' } })
        .then(r => r.json()).catch(() => null);
      if (!d || !d.ok || !d.laeuft) return;
      this.laeuft = d.laeuft;
      if (this.lage) {
        this.lage.textContent = 'läuft seit ' + dauer(d.laeuft.dauer_s)
          + ' · ' + d.laeuft.n_schritte + ' Schritte';
      }
    };
    zeigen();
    this.ticker = setInterval(zeigen, 2000);
  }

  tickerStoppen() {
    if (this.ticker) { clearInterval(this.ticker); this.ticker = null; }
  }

  tabelleHtml(liste) {
    if (!liste.length) {
      return '<p class="ts-empty">Noch keine Aufzeichnung. Der Knopf oben startet eine.</p>';
    }
    const kopf = [
      ['ID', 'id', false], ['Name', 'name', false], ['Start', 'start', false],
      ['Dauer', 'dauer', true], ['Schritte', 'schritte', true],
      ['Logs', 'logs', true], ['', 'aktion', false],
    ].map(([label, key, num]) =>
      `<th${num ? ' class="num"' : ''} data-key="${key}"${key === 'aktion' ? ' data-sort-aus="1"' : ''}>${label}</th>`
    ).join('');

    const zeilen = liste.map(e => `<tr data-id="${esc(e.id)}">
      <td><code>${esc(e.id)}</code></td>
      <td><input class="au-name" value="${esc(e.name)}" data-id="${esc(e.id)}"
                 title="Name ändern – wird beim Verlassen des Feldes gespeichert"></td>
      <td data-sort="${esc(e.start)}">${esc(zeit(e.start))}${e.laeuft ? ' <b class="pos">läuft</b>' : ''}</td>
      <td class="num" data-sort="${e.dauer_s}">${esc(dauer(e.dauer_s))}</td>
      <td class="num">${e.n_schritte}</td>
      <td class="num">${e.n_logs}</td>
      <td><button type="button" class="btn btn-sm btn-outline-danger au-weg"
                  data-id="${esc(e.id)}" title="Aufzeichnung löschen">🗑</button></td>
    </tr>`).join('');

    return `<div class="db-tabelle-rahmen">
      <table class="db-tabelle sortable" data-sort-key="aufzeichnungen">
        <thead><tr>${kopf}</tr></thead><tbody>${zeilen}</tbody>
      </table></div>`;
  }

  binden() {
    if (this.schalter) {
      this.schalter.addEventListener('click', async () => {
        this.schalter.disabled = true;       // kein zweiter Klick, bis es steht
        if (this.laeuft) {
          await senden({ aktion: 'ende' });
        } else {
          await senden({ aktion: 'start', seite: location.pathname });
        }
        await this.laden();
      });
    }
    if (!this.tabelle) return;
    // Delegation: Die Zeilen entstehen neu, sobald sich etwas ändert.
    this.tabelle.addEventListener('click', async ev => {
      const weg = ev.target.closest('button.au-weg');
      if (!weg) return;
      await senden({ aktion: 'loeschen', id: weg.dataset.id });
      await this.laden();
    });
    this.tabelle.addEventListener('change', async ev => {
      const feld = ev.target.closest('input.au-name');
      if (!feld) return;
      await senden({ aktion: 'name', id: feld.dataset.id, name: feld.value });
      await this.laden();
    });
  }
}

const reiter = new Reiter();
reiter.binden();
reiter.laden();

export { Reiter };
