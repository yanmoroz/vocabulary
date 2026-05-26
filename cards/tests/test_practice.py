import uuid

from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from cards import practice
from cards.models import Card, Translation


EN_RU = practice.EN_RU
RU_EN = practice.RU_EN


def _make_cards(n, with_translations=False):
    # uuid prefix keeps terms unique even when called multiple times per test
    prefix = uuid.uuid4().hex[:6]
    cards = [Card.objects.create(term=f"{prefix}-{i}") for i in range(n)]
    if with_translations:
        for c in cards:
            Translation.objects.create(card=c, text=f"tr-{c.id}")
    return cards


class PracticeHelpersTests(TestCase):
    def setUp(self):
        self.req = RequestFactory().get("/")
        self.req.session = {}

    def test_start_session_shuffles_all_cards(self):
        cards = _make_cards(10)
        practice.start_session(self.req.session, EN_RU)

        queue = self.req.session[practice._q_key(EN_RU)]
        self.assertEqual(sorted(queue), sorted(c.id for c in cards))
        self.assertEqual(self.req.session[practice._i_key(EN_RU)], 0)

    def test_ru_en_session_only_includes_cards_with_translations(self):
        with_tr = _make_cards(3, with_translations=True)
        _make_cards(2)  # without translations — should be excluded

        practice.start_session(self.req.session, RU_EN)

        queue = self.req.session[practice._q_key(RU_EN)]
        self.assertEqual(sorted(queue), sorted(c.id for c in with_tr))

    def test_current_card_returns_first_then_advances(self):
        _make_cards(3)
        practice.start_session(self.req.session, EN_RU)
        queue = self.req.session[practice._q_key(EN_RU)]

        first = practice.current_card(self.req.session, EN_RU)
        self.assertEqual(first.id, queue[0])

        practice.advance(self.req.session, EN_RU)
        second = practice.current_card(self.req.session, EN_RU)
        self.assertEqual(second.id, queue[1])

    def test_missing_card_in_queue_is_skipped(self):
        cards = _make_cards(2)
        bad_id = max(c.id for c in cards) + 999
        self.req.session[practice._q_key(EN_RU)] = [bad_id, cards[0].id]
        self.req.session[practice._i_key(EN_RU)] = 0

        card = practice.current_card(self.req.session, EN_RU)

        self.assertEqual(card.id, cards[0].id)
        self.assertEqual(self.req.session[practice._i_key(EN_RU)], 1)

    def test_progress_returns_one_indexed_position_and_total(self):
        _make_cards(3)
        practice.start_session(self.req.session, EN_RU)

        self.assertEqual(practice.progress(self.req.session, EN_RU), (1, 3))

        practice.advance(self.req.session, EN_RU)
        self.assertEqual(practice.progress(self.req.session, EN_RU), (2, 3))

        practice.advance(self.req.session, EN_RU)
        practice.advance(self.req.session, EN_RU)
        self.assertEqual(practice.progress(self.req.session, EN_RU), (3, 3))

    def test_progress_zero_when_no_cards(self):
        practice.start_session(self.req.session, EN_RU)
        self.assertEqual(practice.progress(self.req.session, EN_RU), (0, 0))

    def test_sessions_for_different_directions_are_independent(self):
        _make_cards(2, with_translations=True)

        practice.start_session(self.req.session, EN_RU)
        practice.advance(self.req.session, EN_RU)
        # ru-en session not started yet
        self.assertFalse(practice.has_session(self.req.session, RU_EN))

        practice.start_session(self.req.session, RU_EN)
        # both exist and have independent indices
        self.assertEqual(self.req.session[practice._i_key(EN_RU)], 1)
        self.assertEqual(self.req.session[practice._i_key(RU_EN)], 0)


class PracticeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.client.force_login(self.user)

    def _practice_url(self, direction):
        return reverse("practice", kwargs={"direction": direction})

    def _next_url(self, direction):
        return reverse("practice_next", kwargs={"direction": direction})

    def _restart_url(self, direction):
        return reverse("practice_restart", kwargs={"direction": direction})

    def test_practice_view_creates_queue_on_first_visit(self):
        _make_cards(3)

        resp = self.client.get(self._practice_url(EN_RU))

        self.assertEqual(resp.status_code, 200)
        self.assertIn(practice._q_key(EN_RU), self.client.session)
        self.assertEqual(len(self.client.session[practice._q_key(EN_RU)]), 3)
        self.assertContains(resp, "Card 1 of 3")
        self.assertContains(resp, f"/practice/{EN_RU}/next/")

    def test_practice_view_resumes_existing_session(self):
        cards = _make_cards(3)
        s = self.client.session
        s[practice._q_key(EN_RU)] = [c.id for c in cards]
        s[practice._i_key(EN_RU)] = 1
        s.save()

        resp = self.client.get(self._practice_url(EN_RU))

        self.assertEqual(self.client.session[practice._i_key(EN_RU)], 1)
        self.assertContains(resp, "Card 2 of 3")

    def test_next_does_not_mutate_srs_state(self):
        cards = _make_cards(2)
        target = cards[0]
        target.reps = 5
        target.ease = 2.7
        target.interval = 10
        target.lapses = 3
        target.save()
        prev_next_review = target.next_review

        s = self.client.session
        s[practice._q_key(EN_RU)] = [target.id, cards[1].id]
        s[practice._i_key(EN_RU)] = 0
        s.save()

        self.client.post(self._next_url(EN_RU))

        target.refresh_from_db()
        self.assertEqual(target.reps, 5)
        self.assertEqual(target.ease, 2.7)
        self.assertEqual(target.interval, 10)
        self.assertEqual(target.lapses, 3)
        self.assertEqual(target.next_review, prev_next_review)

    def test_completion_when_queue_exhausted(self):
        cards = _make_cards(1)
        s = self.client.session
        s[practice._q_key(EN_RU)] = [cards[0].id]
        s[practice._i_key(EN_RU)] = 0
        s.save()

        resp = self.client.post(self._next_url(EN_RU))

        self.assertContains(resp, "Session complete")
        self.assertContains(resp, "Start over")
        self.assertContains(resp, f"/practice/{EN_RU}/restart/")

    def test_restart_rebuilds_queue(self):
        _make_cards(4)
        s = self.client.session
        s[practice._q_key(EN_RU)] = [1, 2, 3, 4]
        s[practice._i_key(EN_RU)] = 3
        s.save()

        resp = self.client.post(self._restart_url(EN_RU))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.session[practice._i_key(EN_RU)], 0)
        self.assertEqual(len(self.client.session[practice._q_key(EN_RU)]), 4)

    def test_practice_view_with_no_cards_shows_empty_state(self):
        resp = self.client.get(self._practice_url(EN_RU))
        self.assertContains(resp, "No cards yet")

    def test_ru_en_prompt_is_a_translation_and_term_is_in_reveal(self):
        card = Card.objects.create(term="harsh")
        Translation.objects.create(card=card, text="суровый", order=0)
        Translation.objects.create(card=card, text="резкий", order=1)

        resp = self.client.get(self._practice_url(RU_EN))

        self.assertEqual(resp.status_code, 200)
        # both translations are in the markup (one as prompt, the other under
        # "Other translations" in the hidden reveal — either can be the prompt).
        # Translation.save() capitalizes the first letter.
        self.assertContains(resp, "Суровый")
        self.assertContains(resp, "Резкий")
        # the term is in the reveal (Card.save() capitalizes the first letter)
        self.assertContains(resp, "Harsh")
        # the chosen prompt is recorded in the session
        prompts = self.client.session[practice._prompts_key(RU_EN)]
        chosen_id = prompts[str(card.id)]
        self.assertIn(chosen_id, list(card.translations.values_list("id", flat=True)))

    def test_ru_en_prompt_is_stable_across_requests(self):
        card = Card.objects.create(term="harsh")
        Translation.objects.create(card=card, text="суровый", order=0)
        Translation.objects.create(card=card, text="резкий", order=1)
        Translation.objects.create(card=card, text="жесткий", order=2)

        # First visit establishes the session and the prompt pick
        self.client.get(self._practice_url(RU_EN))
        chosen_id = self.client.session[practice._prompts_key(RU_EN)][str(card.id)]
        chosen_text = card.translations.get(pk=chosen_id).text

        # Multiple subsequent requests must show the same prompt
        for _ in range(5):
            resp = self.client.get(self._practice_url(RU_EN))
            # The .term div wraps the prompt in a <span>
            self.assertIn(
                f'<div class="term"><span>{chosen_text}</span></div>',
                resp.content.decode(),
            )

    def test_ru_en_empty_when_no_card_has_translations(self):
        _make_cards(3)  # no translations

        resp = self.client.get(self._practice_url(RU_EN))

        self.assertContains(resp, "No cards with translations")

    def test_unknown_direction_404s(self):
        resp = self.client.get("/practice/de-en/")
        self.assertEqual(resp.status_code, 404)
