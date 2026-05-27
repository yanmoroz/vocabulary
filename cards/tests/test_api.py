import base64
import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from cards.models import Card, Example, Translation


def _basic_auth_header(username: str, password: str) -> str:
    token = base64.b64encode(f"{username}:{password}".encode()).decode()
    return "Basic " + token


class CreateCardApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.url = reverse("api_card_create")
        self.auth = _basic_auth_header("u", "p")

    def _post(self, payload, auth=None):
        kwargs = {
            "data": json.dumps(payload),
            "content_type": "application/json",
        }
        if auth is not None:
            kwargs["HTTP_AUTHORIZATION"] = auth
        return self.client.post(self.url, **kwargs)

    def test_unauthorized_without_auth_header(self):
        resp = self._post({"word": "hello"})
        self.assertEqual(resp.status_code, 401)
        self.assertIn("WWW-Authenticate", resp.headers)

    def test_unauthorized_with_wrong_password(self):
        resp = self._post({"word": "hello"}, auth=_basic_auth_header("u", "wrong"))
        self.assertEqual(resp.status_code, 401)

    def test_bad_request_on_malformed_json(self):
        resp = self.client.post(
            self.url,
            data="{not json",
            content_type="application/json",
            HTTP_AUTHORIZATION=self.auth,
        )
        self.assertEqual(resp.status_code, 400)

    def test_bad_request_when_word_missing(self):
        resp = self._post({"translations": ["x"]}, auth=self.auth)
        self.assertEqual(resp.status_code, 400)

    def test_bad_request_when_word_blank(self):
        resp = self._post({"word": "   "}, auth=self.auth)
        self.assertEqual(resp.status_code, 400)

    def test_bad_request_when_translations_not_list_of_strings(self):
        resp = self._post(
            {"word": "hello", "translations": [123]}, auth=self.auth
        )
        self.assertEqual(resp.status_code, 400)

    def test_bad_request_when_example_missing_text(self):
        resp = self._post(
            {"word": "hello", "examples": [{"translation": "t"}]},
            auth=self.auth,
        )
        self.assertEqual(resp.status_code, 400)

    def test_creates_card_with_all_fields(self):
        payload = {
            "word": "ubiquitous",
            "translations": ["повсеместный", "вездесущий"],
            "examples": [
                {
                    "text": "Smartphones are ubiquitous.",
                    "translation": "Смартфоны повсеместны.",
                },
                {"text": "ubiquitous tools", "translation": ""},
            ],
            "notes_md": "From Latin _ubique_",
        }

        resp = self._post(payload, auth=self.auth)

        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        # term gets capitalized by Card.save() via normalize_user_text
        self.assertEqual(body["term"], "Ubiquitous")
        self.assertEqual(body["notes_md"], "From Latin _ubique_")
        self.assertEqual(len(body["translations"]), 2)
        self.assertEqual(body["translations"][0]["text"], "Повсеместный")
        self.assertEqual(body["translations"][0]["order"], 0)
        self.assertEqual(body["translations"][1]["order"], 1)
        self.assertEqual(len(body["examples"]), 2)
        self.assertEqual(body["examples"][0]["order"], 0)
        self.assertEqual(body["examples"][1]["order"], 1)

        card = Card.objects.get(pk=body["id"])
        self.assertEqual(card.term, "Ubiquitous")
        self.assertEqual(Translation.objects.filter(card=card).count(), 2)
        self.assertEqual(Example.objects.filter(card=card).count(), 2)

    def test_creates_card_with_only_word(self):
        resp = self._post({"word": "minimal"}, auth=self.auth)
        self.assertEqual(resp.status_code, 201)
        body = resp.json()
        self.assertEqual(body["term"], "Minimal")
        self.assertEqual(body["translations"], [])
        self.assertEqual(body["examples"], [])
        self.assertEqual(body["notes_md"], "")

    def test_conflict_on_duplicate_term(self):
        Card.objects.create(term="duplicate")
        resp = self._post({"word": "duplicate"}, auth=self.auth)
        self.assertEqual(resp.status_code, 409)
