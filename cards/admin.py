from adminsortable2.admin import (
    SortableAdminBase,
    SortableStackedInline,
    SortableTabularInline,
)
from django.contrib import admin
from django.db import models
from django.forms import Textarea

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
