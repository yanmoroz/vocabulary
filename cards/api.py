import base64
import binascii
import json

from django.contrib.auth import authenticate
from django.db import IntegrityError, transaction
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .models import Card, Example, Translation


def _basic_auth_user(request):
    header = request.META.get("HTTP_AUTHORIZATION", "")
    if not header.startswith("Basic "):
        return None
    try:
        decoded = base64.b64decode(header[6:].strip()).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError, ValueError):
        return None
    if ":" not in decoded:
        return None
    username, password = decoded.split(":", 1)
    user = authenticate(username=username, password=password)
    if user is None or not user.is_active:
        return None
    return user


def _unauthorized():
    resp = JsonResponse({"detail": "Authentication required"}, status=401)
    resp["WWW-Authenticate"] = 'Basic realm="cards"'
    return resp


def _bad_request(detail):
    return JsonResponse({"detail": detail}, status=400)


def _serialize_card(card):
    return {
        "id": card.id,
        "term": card.term,
        "notes_md": card.notes_md,
        "translations": [
            {"id": t.id, "text": t.text, "order": t.order}
            for t in card.translations.all()
        ],
        "examples": [
            {"id": e.id, "text": e.text, "translation": e.translation, "order": e.order}
            for e in card.examples.all()
        ],
        "created_at": card.created_at.isoformat(),
    }


@csrf_exempt
@require_POST
def create_card(request):
    if _basic_auth_user(request) is None:
        return _unauthorized()

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return _bad_request("Request body must be valid JSON")

    if not isinstance(payload, dict):
        return _bad_request("Request body must be a JSON object")

    word = payload.get("word")
    if not isinstance(word, str) or not word.strip():
        return _bad_request("'word' is required and must be a non-empty string")

    notes_md = payload.get("notes_md", "")
    if not isinstance(notes_md, str):
        return _bad_request("'notes_md' must be a string")

    translations = payload.get("translations", [])
    if not isinstance(translations, list) or not all(
        isinstance(t, str) and t.strip() for t in translations
    ):
        return _bad_request("'translations' must be a list of non-empty strings")

    examples = payload.get("examples", [])
    if not isinstance(examples, list):
        return _bad_request("'examples' must be a list of objects")
    for ex in examples:
        if not isinstance(ex, dict):
            return _bad_request("Each example must be an object")
        text = ex.get("text")
        if not isinstance(text, str) or not text.strip():
            return _bad_request("Each example must have a non-empty 'text' string")
        ex_translation = ex.get("translation", "")
        if not isinstance(ex_translation, str):
            return _bad_request("Example 'translation' must be a string")

    try:
        with transaction.atomic():
            card = Card.objects.create(term=word, notes_md=notes_md)
            for index, text in enumerate(translations):
                Translation.objects.create(card=card, text=text, order=index)
            for index, ex in enumerate(examples):
                Example.objects.create(
                    card=card,
                    text=ex["text"],
                    translation=ex.get("translation", ""),
                    order=index,
                )
    except IntegrityError:
        return JsonResponse(
            {"detail": "Card with this word already exists"}, status=409
        )

    return JsonResponse(_serialize_card(card), status=201)
