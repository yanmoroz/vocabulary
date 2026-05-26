from datetime import date

from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST

from . import practice as practice_mod
from .models import Card
from .srs import apply_rating


def _next_due_card():
    return (
        Card.objects
        .filter(next_review__lte=date.today())
        .prefetch_related("translations", "examples")
        .order_by("next_review", "id")
        .first()
    )


def _validate_direction(direction: str) -> None:
    if direction not in practice_mod.DIRECTIONS:
        raise Http404("Unknown practice direction")


@login_required
def home(request):
    return render(request, "home.html")


@login_required
def review(request):
    return render(request, "cards/review.html", {
        "card": _next_due_card(),
        "mode": "review",
    })


@login_required
@require_POST
def rate(request, card_id: int, quality: int):
    card = get_object_or_404(Card, pk=card_id)
    apply_rating(card, quality)
    return render(request, "cards/_card.html", {
        "card": _next_due_card(),
        "mode": "review",
    })


def _practice_context(session, direction: str) -> dict:
    card = practice_mod.current_card(session, direction)
    return {
        "card": card,
        "mode": "practice",
        "direction": direction,
        "progress": practice_mod.progress(session, direction),
        "prompt_translation": practice_mod.prompt_translation_for(session, direction, card),
    }


@login_required
def practice(request, direction: str):
    _validate_direction(direction)
    if not practice_mod.has_session(request.session, direction):
        practice_mod.start_session(request.session, direction)
    return render(request, "cards/practice.html", _practice_context(request.session, direction))


@login_required
@require_POST
def practice_next(request, direction: str):
    _validate_direction(direction)
    practice_mod.advance(request.session, direction)
    return render(request, "cards/_card.html", _practice_context(request.session, direction))


@login_required
@require_POST
def practice_restart(request, direction: str):
    _validate_direction(direction)
    practice_mod.start_session(request.session, direction)
    return render(request, "cards/_card.html", _practice_context(request.session, direction))
