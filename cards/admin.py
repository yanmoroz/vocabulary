from adminsortable2.admin import (
    SortableAdminBase,
    SortableStackedInline,
    SortableTabularInline,
)
from django.contrib import admin
from django.db import models
from django.forms import Textarea
from django.shortcuts import get_object_or_404, render
from django.urls import path

from .models import Card, Example, Translation


class TranslationInline(SortableTabularInline):
    model = Translation
    extra = 0


class ExampleInline(SortableStackedInline):
    model = Example
    extra = 0
    formfield_overrides = {
        models.TextField: {"widget": Textarea(attrs={"rows": 2})},
    }


@admin.register(Card)
class CardAdmin(SortableAdminBase, admin.ModelAdmin):
    inlines = [TranslationInline, ExampleInline]
    list_display = ("term", "next_review", "reps", "ease", "lapses")
    list_filter = ("next_review",)
    search_fields = ("term", "translations__text", "notes_md")
    readonly_fields = ("created_at", "updated_at")

    class Media:
        css = {"all": ("admin/css/card_admin.css",)}

    def get_urls(self):
        return [
            path(
                "<int:object_id>/preview/",
                self.admin_site.admin_view(self.preview_view),
                name="cards_card_preview",
            ),
        ] + super().get_urls()

    def preview_view(self, request, object_id):
        card = get_object_or_404(
            Card.objects.prefetch_related("translations", "examples"),
            pk=object_id,
        )
        response = render(request, "cards/preview.html", {"card": card})
        response["X-Frame-Options"] = "SAMEORIGIN"
        return response
