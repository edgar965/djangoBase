/**
 * djangoBase BreitenGreifer - ziehbarer Greifer zwischen zwei Spalten.
 *
 * Der Greifer steht zwischen dem linken Bereich und dem Bereich rechts davon.
 * Nach links ziehen macht den rechten Bereich breiter, nach rechts schmaler.
 * Doppelklick setzt die Standardbreite, die Pfeiltasten verändern sie in
 * 20-px-Schritten.
 *
 * OPT-IN: Nur wo eine Vorlage das Modul einbindet und binden() aufruft.
 *
 * Verwendung (Vorlage mit {% load fassung %}):
 *   <script type="module">
 *     import { BreitenGreifer } from '{% fassungspfad "djangobase/js/breiten_greifer.js" %}';
 *     BreitenGreifer.binden(greifer, rechts, { zeile, schluessel, min, minLinks, anteil });
 *   </script>
 *
 * Optionen:
 *   zeile       gemeinsamer Behälter (Flex-Zeile). Standard: Elternelement von rechts.
 *   schluessel  Teil des localStorage-Schlüssels "db-breite:<schluessel>".
 *               Standard: id von rechts.
 *   min         Mindestbreite des rechten Bereichs in px (Standard 280).
 *   minLinks    Mindestbreite des linken Bereichs in px (Standard 380).
 *   anteil      Standardbreite des rechten Bereichs als Anteil der Zeile (Standard 0.4).
 *
 * Die Breite steht als flex-basis in px am rechten Bereich. Gespeichert wird im
 * Browser; ohne Speicher gilt die Standardbreite.
 */
export class BreitenGreifer {
    static CSS = `
.db-breiten-greifer { flex: 0 0 14px; align-self: stretch; cursor: col-resize;
  position: relative; touch-action: none; user-select: none; }
.db-breiten-greifer::before { content: ''; position: absolute; top: 0; bottom: 0;
  left: 50%; width: 3px; transform: translateX(-50%); border-radius: 2px;
  background: var(--ov10, rgba(128, 128, 128, 0.3)); transition: background 0.15s; }
.db-breiten-greifer:hover::before, .db-breiten-greifer:focus-visible::before,
.db-breiten-greifer.zieht::before { background: var(--accent, #3b82f6); }
.db-breiten-greifer:focus-visible { outline: none; }
body.db-breite-zieht, body.db-breite-zieht * { cursor: col-resize !important; user-select: none !important; }
`;

    /** CSS einmal je Seite einhängen (mehrfaches binden() bleibt wirkungslos). */
    static _stilSetzen() {
        if (document.getElementById('db-breiten-greifer-css')) return;
        const s = document.createElement('style');
        s.id = 'db-breiten-greifer-css';
        s.textContent = this.CSS;
        document.head.appendChild(s);
    }

    /** Greifer an den rechten Bereich binden. Gibt den Greifer zurück. */
    static binden(greifer, rechts, optionen = {}) {
        if (!greifer || !rechts || greifer.dataset.breiteGebunden === '1') return null;
        greifer.dataset.breiteGebunden = '1';
        this._stilSetzen();
        greifer.classList.add('db-breiten-greifer');
        greifer.setAttribute('role', 'separator');
        greifer.setAttribute('aria-orientation', 'vertical');
        greifer.setAttribute('aria-label', 'Breite ändern');
        greifer.tabIndex = 0;

        const zeile = optionen.zeile || rechts.parentElement;
        const min = optionen.min ?? 280;
        const minLinks = optionen.minLinks ?? 380;
        const anteil = optionen.anteil ?? 0.4;
        const schluessel = 'db-breite:' + (optionen.schluessel || rechts.id || 'rechts');

        const hoechst = () => Math.max(min, zeile.clientWidth - minLinks - greifer.offsetWidth);
        const klemmen = (w) => Math.max(min, Math.min(hoechst(), Math.round(w)));
        const setzen = (w) => {
            const neu = klemmen(w);
            rechts.style.flex = `0 0 ${neu}px`;
            return neu;
        };
        const standard = () => zeile.clientWidth * anteil;
        const speichern = (w) => {
            try {
                localStorage.setItem(schluessel, String(w));
            } catch (e) {
                // Ohne Speicher (privates Fenster, gesperrt) gilt beim nächsten Laden der Standard.
            }
        };

        let gespeichert = NaN;
        try {
            gespeichert = parseInt(localStorage.getItem(schluessel), 10);
        } catch (e) {
            // siehe speichern()
        }
        let aktuell = setzen(Number.isFinite(gespeichert) ? gespeichert : standard());

        greifer.addEventListener('pointerdown', (e) => {
            if (e.button !== 0) return;
            const startX = e.clientX;
            const startBreite = aktuell;
            greifer.setPointerCapture(e.pointerId);
            greifer.classList.add('zieht');
            document.body.classList.add('db-breite-zieht');
            const bewegen = (ev) => { aktuell = setzen(startBreite + (startX - ev.clientX)); };
            const loslassen = () => {
                greifer.removeEventListener('pointermove', bewegen);
                greifer.removeEventListener('pointerup', loslassen);
                greifer.removeEventListener('pointercancel', loslassen);
                greifer.classList.remove('zieht');
                document.body.classList.remove('db-breite-zieht');
                speichern(aktuell);
            };
            greifer.addEventListener('pointermove', bewegen);
            greifer.addEventListener('pointerup', loslassen);
            greifer.addEventListener('pointercancel', loslassen);
            e.preventDefault();
        });

        greifer.addEventListener('dblclick', () => {
            aktuell = setzen(standard());
            speichern(aktuell);
        });

        greifer.addEventListener('keydown', (e) => {
            if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return;
            aktuell = setzen(aktuell + (e.key === 'ArrowLeft' ? 20 : -20));
            speichern(aktuell);
            e.preventDefault();
        });

        // Schrumpft das Fenster, passt sich der Bereich an, ohne den gespeicherten Wert zu verlieren.
        window.addEventListener('resize', () => { aktuell = setzen(aktuell); });
        return greifer;
    }
}
