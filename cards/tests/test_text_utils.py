from django.test import SimpleTestCase, TestCase

from cards.models import Card, Example, Translation
from cards.text_utils import normalize_user_text, strip_markdown


class StripMarkdownTests(SimpleTestCase):
    def test_removes_bold(self):
        self.assertEqual(strip_markdown("**hello**"), "hello")

    def test_removes_italic_and_code(self):
        self.assertEqual(strip_markdown("*hi* and `code`"), "hi and code")

    def test_removes_link_keeps_text(self):
        self.assertEqual(strip_markdown("[click](https://x.test)"), "click")

    def test_removes_heading(self):
        self.assertEqual(strip_markdown("# Title"), "Title")

    def test_unescapes_entities(self):
        self.assertEqual(strip_markdown("Tom & Jerry"), "Tom & Jerry")

    def test_handles_empty(self):
        self.assertEqual(strip_markdown(""), "")
        self.assertEqual(strip_markdown(None), "")


class NormalizeUserTextTests(SimpleTestCase):
    def test_strips_surrounding_whitespace(self):
        self.assertEqual(normalize_user_text("  hello  "), "Hello")

    def test_capitalizes_first_letter_only(self):
        self.assertEqual(normalize_user_text("hello WORLD"), "Hello WORLD")

    def test_strips_markdown_and_capitalizes(self):
        self.assertEqual(normalize_user_text("**bold** word"), "Bold word")

    def test_empty_stays_empty(self):
        self.assertEqual(normalize_user_text(""), "")
        self.assertEqual(normalize_user_text("   "), "")
        self.assertEqual(normalize_user_text(None), "")


class CardSaveTests(TestCase):
    def test_normalizes_term_on_save(self):
        card = Card.objects.create(term="  **run** ")
        self.assertEqual(card.term, "Run")

    def test_does_not_touch_notes_md(self):
        card = Card.objects.create(term="run", notes_md="  **bold** notes ")
        self.assertEqual(card.notes_md, "  **bold** notes ")


class TranslationSaveTests(TestCase):
    def test_normalizes_on_save(self):
        card = Card.objects.create(term="run")
        t = Translation.objects.create(card=card, text="  **бегать** ")
        self.assertEqual(t.text, "Бегать")


class ExampleSaveTests(TestCase):
    def test_normalizes_text_and_translation(self):
        card = Card.objects.create(term="run")
        ex = Example.objects.create(
            card=card,
            text="  *he* runs ",
            translation="  он **бежит**  ",
        )
        self.assertEqual(ex.text, "He runs")
        self.assertEqual(ex.translation, "Он бежит")

    def test_blank_translation_stays_blank(self):
        card = Card.objects.create(term="run")
        ex = Example.objects.create(card=card, text="he runs", translation="")
        self.assertEqual(ex.translation, "")
