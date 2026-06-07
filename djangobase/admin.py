from django.contrib import admin

from .models import Provider, Teilnehmer


@admin.register(Teilnehmer)
class TeilnehmerAdmin(admin.ModelAdmin):
    list_display = ("user", "sprache", "stadt", "land", "eingeloggt")
    list_filter = ("sprache", "eingeloggt")
    search_fields = ("user__username", "user__email", "user__first_name", "user__last_name")


@admin.register(Provider)
class ProviderAdmin(admin.ModelAdmin):
    list_display = ("user", "anbietername", "verifiziert", "sprache", "stadt")
    list_filter = ("verifiziert", "sprache")
    search_fields = ("user__username", "user__email", "anbietername")
