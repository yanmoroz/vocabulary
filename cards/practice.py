import random

from .models import Card

EN_RU = "en-ru"
RU_EN = "ru-en"
DIRECTIONS = (EN_RU, RU_EN)


def _q_key(direction: str) -> str:
    return f"practice_queue_{direction}"


def _i_key(direction: str) -> str:
    return f"practice_index_{direction}"


def _prompts_key(direction: str) -> str:
    # Per-session map {card_id: prompt_translation_id} for RU→EN, stable
    # within the session so each card always shows the same prompt while
    # the session lasts.
    return f"practice_prompts_{direction}"


def start_session(session, direction: str) -> None:
    if direction == RU_EN:
        cards = (
            Card.objects.filter(translations__isnull=False)
            .distinct()
            .prefetch_related("translations")
        )
        ids: list[int] = []
        prompts: dict[str, int] = {}
        for card in cards:
            translations = list(card.translations.all())
            if not translations:
                continue
            ids.append(card.id)
            prompts[str(card.id)] = random.choice(translations).id
        session[_prompts_key(direction)] = prompts
    else:
        ids = list(Card.objects.values_list("id", flat=True))
        session.pop(_prompts_key(direction), None)

    random.shuffle(ids)
    session[_q_key(direction)] = ids
    session[_i_key(direction)] = 0


def has_session(session, direction: str) -> bool:
    return _q_key(direction) in session


def current_card(session, direction: str):
    """Return the Card at the current index, skipping deleted IDs.

    Mutates the index to skip past holes so subsequent calls stay consistent.
    Returns None when the queue is exhausted.
    """
    qkey = _q_key(direction)
    ikey = _i_key(direction)
    ids = session.get(qkey) or []
    idx = session.get(ikey, 0)
    while idx < len(ids):
        card = (
            Card.objects
            .filter(pk=ids[idx])
            .prefetch_related("translations", "examples")
            .first()
        )
        if card is not None:
            if session.get(ikey, 0) != idx:
                session[ikey] = idx
            return card
        idx += 1
    if session.get(ikey, 0) != idx:
        session[ikey] = idx
    return None


def advance(session, direction: str) -> None:
    ikey = _i_key(direction)
    session[ikey] = session.get(ikey, 0) + 1


def prompt_translation_for(session, direction: str, card):
    """Return the Translation chosen at session start as the RU→EN prompt for
    this card, falling back to the first translation if the pick is missing
    (deleted translation, pre-existing session before this feature, etc.).
    Returns None for non-RU→EN directions or cards without translations."""
    if direction != RU_EN or card is None:
        return None
    translations = list(card.translations.all())
    if not translations:
        return None
    prompts = session.get(_prompts_key(direction)) or {}
    tr_id = prompts.get(str(card.id))
    if tr_id is not None:
        chosen = next((t for t in translations if t.id == tr_id), None)
        if chosen is not None:
            return chosen
    return translations[0]


def progress(session, direction: str):
    """(current_1indexed, total) — current capped at total when exhausted."""
    ids = session.get(_q_key(direction)) or []
    idx = session.get(_i_key(direction), 0)
    total = len(ids)
    if total == 0:
        return (0, 0)
    return (min(idx + 1, total), total)
