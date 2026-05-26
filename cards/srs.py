from datetime import date, timedelta

from .models import Card


def apply_rating(card: Card, quality: int) -> None:
    """SM-2. quality in {0, 3, 4, 5}."""
    if quality < 3:
        card.reps = 0
        card.interval = 0
        card.lapses += 1
        card.next_review = date.today() + timedelta(days=1)
    else:
        if card.reps == 0:
            card.interval = 1
        elif card.reps == 1:
            card.interval = 6
        else:
            card.interval = round(card.interval * card.ease)

        card.ease = card.ease + (0.1 - (5 - quality) * (0.08 + (5 - quality) * 0.02))
        card.ease = max(1.3, card.ease)
        card.reps += 1
        card.next_review = date.today() + timedelta(days=card.interval)

    card.save()
