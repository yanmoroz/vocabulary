from datetime import date

from django.contrib.auth.decorators import login_required
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


@login_required
def practice(request):
    if not practice_mod.has_session(request.session):
        practice_mod.start_session(request.session)
    return render(request, "cards/practice.html", {
        "card": practice_mod.current_card(request.session),
        "mode": "practice",
        "progress": practice_mod.progress(request.session),
    })


@login_required
@require_POST
def practice_next(request):
    practice_mod.advance(request.session)
    return render(request, "cards/_card.html", {
        "card": practice_mod.current_card(request.session),
        "mode": "practice",
        "progress": practice_mod.progress(request.session),
    })


@login_required
@require_POST
def practice_restart(request):
    practice_mod.start_session(request.session)
    return render(request, "cards/_card.html", {
        "card": practice_mod.current_card(request.session),
        "mode": "practice",
        "progress": practice_mod.progress(request.session),
    })
