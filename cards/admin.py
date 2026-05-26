from django.contrib import admin

from .models import Card, Example, Translation


class TranslationInline(admin.TabularInline):
    model = Translation
    extra = 1


class ExampleInline(admin.StackedInline):
    model = Example
    extra = 1


@admin.register(Card)
class CardAdmin(admin.ModelAdmin):
    inlines = [TranslationInline, ExampleInline]
    list_display = ("term", "next_review", "reps", "ease", "lapses")
    list_filter = ("next_review",)
    search_fields = ("term", "translations__text", "notes_md")
    readonly_fields = ("created_at", "updated_at")
