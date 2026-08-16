/**
 * Serverabruf — Daten vom Server holen und den Fehlerfall ernst nehmen.
 *
 * KANONISCHE FASSUNG in djangoBase (16.08.2026). Sie liegt hier, weil sie in
 * jedem Projekt gebraucht wird und weil die Umsteller unter
 * `djangobase/umbau/` Importe auf genau diese Klasse schreiben.
 *
 * Einbinden: entweder direkt
 *     import { Serverabruf } from "{% static 'djangobase/js/serverabruf.js' %}";
 * oder — wenn viele Module einen kurzen relativen Pfad nutzen — eine Datei im
 * Projekt, die nur weiterreicht:
 *     export { Serverabruf } from '/static/djangobase/js/serverabruf.js';
 *
 * DER FALL DAHINTER (3DTools): An 125 Stellen stand
 *
 *     const resp = await fetch(adresse);
 *     const daten = await resp.json();
 *
 * ohne jede Prüfung von `resp.ok`. Bei einer 500er-Antwort liefert Django eine
 * HTML-Fehlerseite; `json()` scheitert daran mit "Unexpected token '<'" —
 * einer Meldung, die nichts über die Ursache sagt und aussieht, als sei der
 * eigene Code kaputt. Bei 404 dasselbe.
 */
export class Serverabruf {

    /** So viele Zeichen der Serverantwort kommen in die Meldung. */
    static MELDUNGSLAENGE = 200;

    /**
     * JSON holen. Wirft bei einem Fehlercode.
     * @param adresse  URL
     * @param wahl     wie bei `fetch`
     */
    static async json(adresse, wahl = undefined) {
        const antwort = await fetch(adresse, wahl);
        if (!antwort.ok) throw await Serverabruf._fehler(antwort, adresse);
        return antwort.json();
    }

    /** Text holen. Wirft bei einem Fehlercode. */
    static async text(adresse, wahl = undefined) {
        const antwort = await fetch(adresse, wahl);
        if (!antwort.ok) throw await Serverabruf._fehler(antwort, adresse);
        return antwort.text();
    }

    /**
     * CSRF-Token aus dem Cookie. Django lehnt einen POST ohne ihn mit 403 ab,
     * sobald die Ansicht nicht `csrf_exempt` ist.
     *
     * Umbau 16.08.2026: Dieselbe Zeile stand in vier Fassungen im Projekt —
     * `scene/utils.getCSRFToken` (cookie.split), `animation/speichern.js`
     * (dieselbe Zeile noch einmal), `bvh_studio/export1.js` und
     * `scene/cloth_export.js` (je eine eigene Regex-Variante). Wer einen neuen
     * POST schrieb, entschied jedes Mal neu, ob überhaupt ein Token mitgeht.
     */
    /**
     * Name des CSRF-Cookies. Django erlaubt `CSRF_COOKIE_NAME` zu aendern —
     * ein fest verdrahtetes 'csrftoken' liefert dann einen LEEREN Kopf, und
     * jeder POST endet in 403, obwohl das Cookie da ist. Wer den Namen aendert,
     * setzt ihn hier (oder legt `<meta name="csrf-cookie" content="…">` in die
     * Seite — das wird beim ersten Aufruf gelesen).
     *
     * Befund von Nemotron im Sparring am 16.08.2026.
     */
    static COOKIENAME = 'csrftoken';

    /**
     * Token aus dem Cookie lesen — ohne Regex-Bau.
     *
     * FEHLER 16.08.2026, im Browser gemessen: Erst stand hier
     * `new RegExp('(?:^|;\s*)' + name + '…')`. In einem JS-String ist
     * `\s` nur ein `s`, die Regex suchte also ein Semikolon mit "s" dahinter
     * und fand nie etwas — `csrfToken()` gab konstant '' zurueck, und jeder
     * POST an eine nicht-exempt Ansicht waere mit 403 gescheitert. Deshalb
     * jetzt reines Zerlegen: kein Escape, kein Zweifel.
     */
    static csrfToken() {
        const gesucht = Serverabruf._cookiename() + '=';
        for (const teil of document.cookie.split(';')) {
            const eintrag = teil.trim();
            if (eintrag.startsWith(gesucht)) {
                return decodeURIComponent(eintrag.slice(gesucht.length));
            }
        }
        return '';
    }

    static _cookiename() {
        const marke = document.querySelector('meta[name="csrf-cookie"]');
        return marke?.content || Serverabruf.COOKIENAME;
    }

    /**
     * JSON als POST senden — der häufigste Schreibfall im Projekt, bisher an
     * jeder Stelle mit denselben drei Kopfzeilen ausgeschrieben.
     */
    static async senden(adresse, nutzlast, kopf = {}) {
        return Serverabruf.json(adresse, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json',
                       ...Serverabruf._csrfKopf(), ...kopf },
            body: JSON.stringify(nutzlast),
        });
    }

    /**
     * CSRF-Kopf — aber nur, wenn ein Token da ist.
     *
     * Befund von Gemma im Sparring am 16.08.2026: Ein LEERER
     * `X-CSRFToken`-Kopf ist nicht dasselbe wie kein Kopf. Django nimmt bei
     * einem Formular-POST zwar das Feld `csrfmiddlewaretoken`, aber wer sich
     * darauf verlässt, hat eine Annahme über fremde Middleware im Code. Ein
     * leerer Kopf sagt „hier ist mein Token: nichts" — das ist nie gemeint.
     */
    static _csrfKopf() {
        const token = Serverabruf.csrfToken();
        return token ? { 'X-CSRFToken': token } : {};
    }

    /**
     * FormData als POST senden (Datei-Uploads).
     *
     * Wichtig: KEIN `Content-Type` — den setzt der Browser mitsamt der
     * `boundary`. Wer ihn selbst setzt, macht den Upload serverseitig
     * unlesbar.
     */
    static async formular(adresse, daten, kopf = {}) {
        return Serverabruf.json(adresse, {
            method: 'POST',
            headers: { ...Serverabruf._csrfKopf(), ...kopf },
            body: daten,
        });
    }

    /**
     * JSON holen, aber im Fehlerfall nur warnen und `null` liefern — für
     * Stellen, an denen ein fehlendes Ergebnis kein Grund zum Abbruch ist
     * (Einstellungen, optionale Listen).
     */
    static async jsonOderNull(adresse, wahl = undefined, beiFehler = null) {
        try {
            return await Serverabruf.json(adresse, wahl);
        } catch (fehler) {
            // `beiFehler` bekommt die vollstaendige Ausnahme — mit `status` und
            // `daten`. Ohne sie kann ein Aufrufer nicht unterscheiden, ob der
            // Wert fehlt (404) oder die Anfrage falsch war (400); Befund von
            // Nemotron im Sparring am 16.08.2026.
            if (beiFehler) beiFehler(fehler);
            else console.warn('[Serverabruf]', fehler.message);
            return null;
        }
    }

    /**
     * Ausnahme mit Adresse, Statuscode UND dem Fehlerkoerper des Servers.
     *
     * Befund von Nemotron im Sparring am 16.08.2026: Ein Aufrufer, der vorher
     * `{ok: false, error: "…", code: "DUPLICATE"}` aus `resp.json()` bekam, sah
     * danach nur noch eine auf 200 Zeichen abgeschnittene Zeichenkette — das
     * strukturierte Feld war weg. Bei 200 Django-Ansichten, die einen
     * Fehlerstatus MIT JSON-Koerper liefern, ist das ein echter Verlust.
     *
     * Deshalb liegen jetzt BEIDE Formen an der Ausnahme:
     *   fehler.daten    das geparste JSON, wenn es eines war (sonst null)
     *   fehler.rumpf    der Text, vollstaendig
     *   fehler.message  Kurzfassung fuer Meldungen (Status + Anfang)
     */
    static async _fehler(antwort, adresse) {
        let rumpf = '';
        let daten = null;
        try {
            // `clone()`: Der Koerper ist nur EINMAL lesbar. Ohne die Kopie
            // kaeme ein Aufrufer, der selbst noch lesen will, ins Leere.
            rumpf = await antwort.clone().text();
            daten = JSON.parse(rumpf);
        } catch (leseFehler) {
            if (!rumpf) rumpf = '(Antwort nicht lesbar)';
        }
        const kurz = rumpf.slice(0, Serverabruf.MELDUNGSLAENGE);
        const fehler = new Error(
            `${antwort.status} ${antwort.statusText} bei ${adresse}`
            + (kurz ? ` — ${kurz}` : ''));
        fehler.status = antwort.status;
        fehler.adresse = adresse;
        fehler.rumpf = rumpf;
        fehler.daten = daten && typeof daten === 'object' ? daten : null;
        return fehler;
    }
}
