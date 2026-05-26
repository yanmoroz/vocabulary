from datetime import date, timedelta

from django.test import TestCase

from cards.models import Card
from cards.srs import apply_rating


class ApplyRatingTests(TestCase):
    def _card(self, **kwargs):
        defaults = {"term": "example"}
        defaults.update(kwargs)
        return Card.objects.create(**defaults)

    def test_again_resets_interval_and_bumps_lapses(self):
        card = self._card(reps=5, interval=20, lapses=1)

        apply_rating(card, 0)

        self.assertEqual(card.reps, 0)
        self.assertEqual(card.interval, 0)
        self.assertEqual(card.lapses, 2)
        self.assertEqual(card.next_review, date.today() + timedelta(days=1))

    def test_first_good_sets_interval_to_one(self):
        card = self._card()  # reps=0, interval=0

        apply_rating(card, 4)

        self.assertEqual(card.interval, 1)
        self.assertEqual(card.reps, 1)
        self.assertEqual(card.next_review, date.today() + timedelta(days=1))

    def test_second_good_sets_interval_to_six(self):
        card = self._card(reps=1, interval=1)

        apply_rating(card, 4)

        self.assertEqual(card.interval, 6)
        self.assertEqual(card.reps, 2)

    def test_subsequent_good_multiplies_by_ease(self):
        card = self._card(reps=2, interval=6, ease=2.5)

        apply_rating(card, 4)

        # round(6 * 2.5) == 15; ease unchanged at quality=4
        self.assertEqual(card.interval, 15)
        self.assertEqual(card.reps, 3)
        self.assertAlmostEqual(card.ease, 2.5)

    def test_easy_increases_ease(self):
        card = self._card(ease=2.5)

        apply_rating(card, 5)

        # +0.1 on quality 5
        self.assertAlmostEqual(card.ease, 2.6)

    def test_hard_decreases_ease(self):
        card = self._card(ease=2.5)

        apply_rating(card, 3)

        # -0.14 on quality 3
        self.assertAlmostEqual(card.ease, 2.36)

    def test_ease_floor(self):
        card = self._card(ease=1.3)

        for _ in range(10):
            apply_rating(card, 3)

        self.assertGreaterEqual(card.ease, 1.3)

    def test_persisted(self):
        card = self._card()

        apply_rating(card, 4)

        card.refresh_from_db()
        self.assertEqual(card.reps, 1)
        self.assertEqual(card.interval, 1)
