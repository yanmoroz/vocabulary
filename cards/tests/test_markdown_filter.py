from django.test import SimpleTestCase

from cards.templatetags.markdown_extras import markdown_filter


class MarkdownFilterTests(SimpleTestCase):
    def test_renders_bold(self):
        self.assertIn("<strong>hi</strong>", markdown_filter("**hi**"))

    def test_renders_fenced_code(self):
        out = markdown_filter("```\nprint(1)\n```")
        self.assertIn("<pre>", out)
        self.assertIn("<code>", out)

    def test_strips_disallowed_tags(self):
        out = markdown_filter("<script>alert(1)</script>**ok**")
        self.assertNotIn("<script>", out)
        self.assertIn("<strong>ok</strong>", out)

    def test_keeps_links_but_only_safe_attrs(self):
        out = markdown_filter('[x](https://example.com "t")')
        self.assertIn('href="https://example.com"', out)
        self.assertIn('title="t"', out)

    def test_handles_empty(self):
        self.assertEqual(markdown_filter(""), "")
        self.assertEqual(markdown_filter(None), "")
