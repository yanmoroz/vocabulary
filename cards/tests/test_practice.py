from django.contrib.auth.models import User
from django.test import RequestFactory, TestCase
from django.urls import reverse

from cards import practice
from cards.models import Card


def _make_cards(n):
    return [Card.objects.create(term=f"t{i}") for i in range(n)]


class PracticeHelpersTests(TestCase):
    def setUp(self):
        # RequestFactory + manually attached session dict, no client / middleware.
        self.req = RequestFactory().get("/")
        self.req.session = {}

    def test_start_session_shuffles_all_cards(self):
        cards = _make_cards(10)
        practice.start_session(self.req.session)

        queue = self.req.session[practice.QUEUE_KEY]
        self.assertEqual(sorted(queue), sorted(c.id for c in cards))
        self.assertEqual(self.req.session[practice.INDEX_KEY], 0)

    def test_current_card_returns_first_then_advances(self):
        _make_cards(3)
        practice.start_session(self.req.session)
        queue = self.req.session[practice.QUEUE_KEY]

        first = practice.current_card(self.req.session)
        self.assertEqual(first.id, queue[0])

        practice.advance(self.req.session)
        second = practice.current_card(self.req.session)
        self.assertEqual(second.id, queue[1])

    def test_missing_card_in_queue_is_skipped(self):
        cards = _make_cards(2)
        # Inject a deleted ID at the front; current_card should skip to next.
        bad_id = max(c.id for c in cards) + 999
        self.req.session[practice.QUEUE_KEY] = [bad_id, cards[0].id]
        self.req.session[practice.INDEX_KEY] = 0

        card = practice.current_card(self.req.session)

        self.assertEqual(card.id, cards[0].id)
        # Index was bumped past the hole.
        self.assertEqual(self.req.session[practice.INDEX_KEY], 1)

    def test_progress_returns_one_indexed_position_and_total(self):
        _make_cards(3)
        practice.start_session(self.req.session)

        self.assertEqual(practice.progress(self.req.session), (1, 3))

        practice.advance(self.req.session)
        self.assertEqual(practice.progress(self.req.session), (2, 3))

        practice.advance(self.req.session)
        practice.advance(self.req.session)  # past end
        self.assertEqual(practice.progress(self.req.session), (3, 3))

    def test_progress_zero_when_no_cards(self):
        practice.start_session(self.req.session)
        self.assertEqual(practice.progress(self.req.session), (0, 0))


class PracticeViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="u", password="p")
        self.client.force_login(self.user)

    def test_practice_view_creates_queue_on_first_visit(self):
        _make_cards(3)

        resp = self.client.get(reverse("practice"))

        self.assertEqual(resp.status_code, 200)
        self.assertIn(practice.QUEUE_KEY, self.client.session)
        self.assertEqual(len(self.client.session[practice.QUEUE_KEY]), 3)
        self.assertContains(resp, "Card 1 of 3")
        self.assertContains(resp, "practice/next/")

    def test_practice_view_resumes_existing_session(self):
        cards = _make_cards(3)
        s = self.client.session
        s[practice.QUEUE_KEY] = [c.id for c in cards]
        s[practice.INDEX_KEY] = 1
        s.save()

        resp = self.client.get(reverse("practice"))

        self.assertEqual(self.client.session[practice.INDEX_KEY], 1)
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
        s[practice.QUEUE_KEY] = [target.id, cards[1].id]
        s[practice.INDEX_KEY] = 0
        s.save()

        self.client.post(reverse("practice_next"))

        target.refresh_from_db()
        self.assertEqual(target.reps, 5)
        self.assertEqual(target.ease, 2.7)
        self.assertEqual(target.interval, 10)
        self.assertEqual(target.lapses, 3)
        self.assertEqual(target.next_review, prev_next_review)

    def test_completion_when_queue_exhausted(self):
        cards = _make_cards(1)
        s = self.client.session
        s[practice.QUEUE_KEY] = [cards[0].id]
        s[practice.INDEX_KEY] = 0
        s.save()

        resp = self.client.post(reverse("practice_next"))

        self.assertContains(resp, "Session complete")
        self.assertContains(resp, "Start over")
        self.assertContains(resp, "practice/restart/")

    def test_restart_rebuilds_queue(self):
        _make_cards(4)
        s = self.client.session
        s[practice.QUEUE_KEY] = [1, 2, 3, 4]
        s[practice.INDEX_KEY] = 3
        s.save()

        resp = self.client.post(reverse("practice_restart"))

        self.assertEqual(resp.status_code, 200)
        self.assertEqual(self.client.session[practice.INDEX_KEY], 0)
        self.assertEqual(len(self.client.session[practice.QUEUE_KEY]), 4)

    def test_practice_view_with_no_cards_shows_empty_state(self):
        resp = self.client.get(reverse("practice"))

        self.assertContains(resp, "No cards yet")
