import random

from .models import Card

QUEUE_KEY = "practice_queue"
INDEX_KEY = "practice_index"


def start_session(session) -> None:
    ids = list(Card.objects.values_list("id", flat=True))
    random.shuffle(ids)
    session[QUEUE_KEY] = ids
    session[INDEX_KEY] = 0


def has_session(session) -> bool:
    return QUEUE_KEY in session


def current_card(session):
    """Return the Card at the current index, skipping deleted IDs.

    Mutates the index to skip past holes so subsequent calls stay consistent.
    Returns None when the queue is exhausted.
    """
    ids = session.get(QUEUE_KEY) or []
    idx = session.get(INDEX_KEY, 0)
    while idx < len(ids):
        card = (
            Card.objects
            .filter(pk=ids[idx])
            .prefetch_related("translations", "examples")
            .first()
        )
        if card is not None:
            if session.get(INDEX_KEY, 0) != idx:
                session[INDEX_KEY] = idx
            return card
        idx += 1
    if session.get(INDEX_KEY, 0) != idx:
        session[INDEX_KEY] = idx
    return None


def advance(session) -> None:
    session[INDEX_KEY] = session.get(INDEX_KEY, 0) + 1


def progress(session):
    """(current_1indexed, total) — current capped at total when exhausted."""
    ids = session.get(QUEUE_KEY) or []
    idx = session.get(INDEX_KEY, 0)
    total = len(ids)
    if total == 0:
        return (0, 0)
    return (min(idx + 1, total), total)
