/**
 * djangoBase Sidebar-Toggle — Collapse (Desktop) + Drawer (Mobile).
 * Portiert aus dem Assistant (mail/js/base/SidebarToggle.js), ohne
 * ES-Modul-Abhaengigkeit.
 *
 * - Desktop (>768px): Toggle klappt die Sidebar ein/aus; Zustand wird in
 *   localStorage['djangobase.sidebarCollapsed'] gemerkt.
 * - Mobile (<=768px): Toggle oeffnet die Sidebar als Drawer; Klick auf den
 *   Hintergrund schliesst sie wieder.
 *
 * Der Topbar-Button in _shell.html ruft window.toggleSidebar() auf.
 * Der eingeklappte Zustand wird zusaetzlich schon im <head> (Pre-Paint)
 * wiederhergestellt, um Flackern zu vermeiden.
 */
(function () {
    var MOBILE = 768;
    var KEY = 'djangobase.sidebarCollapsed';

    function istMobil() {
        return window.matchMedia('(max-width: ' + MOBILE + 'px)').matches;
    }

    function toggle() {
        if (istMobil()) {
            document.body.classList.toggle('sidebar-mobile-open');
            return;
        }
        var collapsed = document.body.classList.toggle('sidebar-collapsed');
        try { localStorage.setItem(KEY, collapsed ? '1' : '0'); } catch (e) {}
    }

    // Gespeicherten eingeklappten Zustand wiederherstellen.
    try {
        if (localStorage.getItem(KEY) === '1') {
            document.body.classList.add('sidebar-collapsed');
        }
    } catch (e) {}

    // Klick auf den abgedunkelten Hintergrund (Mobile) schliesst den Drawer.
    document.addEventListener('click', function (e) {
        if (!document.body.classList.contains('sidebar-mobile-open')) return;
        if (e.target.closest('.sidebar')) return;
        if (e.target.closest('#sidebar-toggle')) return;
        document.body.classList.remove('sidebar-mobile-open');
    });

    // Global fuer den inline-onclick im Topbar.
    window.toggleSidebar = toggle;
})();
