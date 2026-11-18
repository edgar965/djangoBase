/* SitzungAbgelaufen - nachgeladene Inhalte, die auf der Anmeldeseite landen.
   ==========================================================================
   Befund assistant 16.11.2026 (Heizung, logs/django.log 12:46): Die Sitzung war abgelaufen. Das
   Nachladen alle 15 s (fetch auf /dashboard/heizung/inhalt/) folgte der Umleitung auf LOGIN_URL,
   bekam die Anmeldeseite mit Status 200 und setzte sie als Inhalt ein. Nach dem Anmelden schickte
   Django den Browser auf next=/dashboard/heizung/inhalt/ - das Fragment ohne Rahmen, Menü und CSS
   (Edgar: „layout zerschossen", „das menü links ist nicht mehr da"). Dieselbe Falle hat jede Seite,
   die per fetch oder HTMX nachlädt; Ansage Edgar: „mach das zentral in djangoBase".

   WAS ES TUT: Endet ein fetch()- oder HTMX-Abruf derselben Herkunft per Umleitung auf der
   Anmeldeseite, wird nichts eingesetzt, und die SEITE lädt neu - deren Umleitung trägt dann
   next=<diese Seite>, nach dem Anmelden steht man wieder dort.

   KEINE NEULADESCHLEIFE: Auch angemeldet leitet manches auf die Anmeldeseite um
   (user_passes_test / staff_member_required bei fehlendem Recht). Deshalb erst die eigene Seite mit
   redirect:'manual' fragen: Leitet SIE um (opaqueredirect), ist die Sitzung weg - neu laden.
   Antwortet sie, geht die Antwort des Abrufs unverändert weiter. Gemessen 16.11.2026 im assistant
   mit Service Worker: fetch ohne Cookie → redirected true, url /admin/login/?next=…, Status 200;
   die eigene Seite mit redirect:'manual' angemeldet basic/200, ohne Cookie opaqueredirect.

   Eingehängt von der AufzeichnungMiddleware in jede HTML-Seite (wie tabellen_auto.js), VOR den
   Aufzeichner-Modulen: Der Aufzeichner umhüllt fetch beim Start und stellt beim Stopp den vorigen
   Stand wieder her - so bleibt diese Hülle darunter erhalten. Die Adresse der Anmeldeseite steht in
   data-djb-anmeldung am eigenen <script> (resolve_url(LOGIN_URL)); fehlt sie, gilt ein Pfad, der auf
   /login/ endet. */

const ECHT = window.fetch.bind(window);

export class SitzungAbgelaufen {
  /** Pfad der Anmeldeseite aus dem eigenen <script>-Tag, sonst leer. */
  static anmeldung() {
    return document.querySelector('script[data-djb-anmeldung]')?.dataset.djbAnmeldung || '';
  }

  /** Liegt die Adresse auf der Anmeldeseite dieser Herkunft? */
  static istAnmeldung(adresse) {
    if (!adresse) return false;
    let ziel;
    try {
      ziel = new URL(adresse, location.href);
    } catch {
      return false;   // stumm gewollt: eine unlesbare Adresse ist keine Anmeldeseite
    }
    if (ziel.origin !== location.origin) return false;
    const pfad = SitzungAbgelaufen.anmeldung();
    if (pfad) return ziel.pathname === new URL(pfad, location.href).pathname;
    return /\/login\/?$/.test(ziel.pathname);
  }

  /** Leitet die eigene Seite jetzt auf die Anmeldung um? Dann ist die Sitzung weg. */
  static async seiteGesperrt() {
    try {
      const antwort = await ECHT(location.href, { redirect: 'manual', cache: 'no-store', credentials: 'same-origin' });
      return antwort.type === 'opaqueredirect';
    } catch {
      return false;   // stumm gewollt: ohne Server keine Aussage - der Abruf selbst meldet seinen Fehler
    }
  }

  static neuLaden() {
    if (SitzungAbgelaufen.laedtNeu) return;
    SitzungAbgelaufen.laedtNeu = true;
    location.reload();
  }

  /** Ersatz für window.fetch. */
  static async abrufen(...argumente) {
    const antwort = await ECHT(...argumente);
    if (!antwort.redirected || !SitzungAbgelaufen.istAnmeldung(antwort.url)) return antwort;
    if (!(await SitzungAbgelaufen.seiteGesperrt())) return antwort;
    SitzungAbgelaufen.neuLaden();
    return new Promise(() => {});   // nichts mehr einsetzen - die Seite lädt neu
  }

  /** htmx:beforeSwap - XMLHttpRequest kennt kein ``redirected``; ``responseURL`` ist die Endadresse. */
  static vorDemTausch(e) {
    const xhr = e.detail?.xhr;
    if (!xhr?.responseURL || !SitzungAbgelaufen.istAnmeldung(xhr.responseURL)) return;
    const gefragt = e.detail.pathInfo?.requestPath || e.detail.requestConfig?.path;
    if (gefragt && SitzungAbgelaufen.istAnmeldung(gefragt)) return;   // die Anmeldeseite selbst abgerufen
    e.detail.shouldSwap = false;
    SitzungAbgelaufen.seiteGesperrt().then((weg) => {
      if (weg) SitzungAbgelaufen.neuLaden();
      else console.warn('[SitzungAbgelaufen] Abruf leitet auf die Anmeldeseite um, die Seite selbst nicht — '
                        + 'nicht eingesetzt:', xhr.responseURL);
    });
  }

  static einschalten() {
    if (window.__djbSitzungAbgelaufen) return;   // zweimal eingebunden (Vorlage und Middleware): einmal genügt
    window.__djbSitzungAbgelaufen = true;
    window.fetch = (...argumente) => SitzungAbgelaufen.abrufen(...argumente);
    document.addEventListener('htmx:beforeSwap', (e) => SitzungAbgelaufen.vorDemTausch(e));
  }
}

SitzungAbgelaufen.einschalten();
