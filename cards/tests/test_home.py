from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class HomeViewTests(TestCase):
    def test_redirects_anonymous_to_login(self):
        resp = self.client.get(reverse("home"))
        self.assertEqual(resp.status_code, 302)
        self.assertIn("/accounts/login/", resp.headers["Location"])

    def test_shows_review_and_practice_links_when_authed(self):
        User.objects.create_user(username="u", password="p")
        self.client.login(username="u", password="p")

        resp = self.client.get(reverse("home"))

        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, reverse("review"))
        self.assertContains(resp, reverse("practice", kwargs={"direction": "en-ru"}))
        self.assertContains(resp, reverse("practice", kwargs={"direction": "ru-en"}))
        self.assertContains(resp, "Review")
        self.assertContains(resp, "Practice EN to RU")
        self.assertContains(resp, "Practice RU to EN")
