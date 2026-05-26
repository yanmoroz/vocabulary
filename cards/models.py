from datetime import date

from django.db import models


class Card(models.Model):
    term = models.CharField(max_length=200, unique=True)
    notes_md = models.TextField(blank=True, help_text="Markdown supported")

    ease = models.FloatField(default=2.5)
    interval = models.IntegerField(default=0)
    next_review = models.DateField(default=date.today)
    reps = models.IntegerField(default=0)
    lapses = models.IntegerField(default=0)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.term


class Translation(models.Model):
    card = models.ForeignKey(Card, related_name="translations", on_delete=models.CASCADE)
    text = models.CharField(max_length=300)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text


class Example(models.Model):
    card = models.ForeignKey(Card, related_name="examples", on_delete=models.CASCADE)
    text = models.TextField()
    translation = models.TextField(blank=True)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.text[:60]
