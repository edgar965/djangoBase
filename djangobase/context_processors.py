from .conf import conf


def djangobase(request):
    """Stellt Branding, Farben, Menü und Version in jedem Template bereit."""
    c = conf()
    return {"djangobase": {
        "titel": c["titel"],
        "untertitel": c["untertitel"],
        "logo_icon": c["logo_icon"],
        "farben": c["farben"],
        "menu": c["menu"],
        "version": c["version"],
    }}
