import unittest

from hidden.box import box_wrap
from hidden.colors import GREEN, RESET

class TestBox(unittest.TestCase):
    def test_simple_text(self):
        self.assertEqual(box_wrap("hello", width=20), """\
┌──────────────────┐
│ hello            │
└──────────────────┘""")

    def test_multiline_text(self):
        self.assertEqual(box_wrap("line1\nline2", width=20), """\
┌──────────────────┐
│ line1            │
│ line2            │
└──────────────────┘""")

    def test_wrapping_long_lines(self):
        self.assertEqual(box_wrap("aaaaaaaaaaaaaaaaaaaa", width=15), """\
┌─────────────┐
│ aaaaaaaaaaa │
│ aaaaaaaaa   │
└─────────────┘""")

    def test_colored_text_alignment(self):
        self.assertEqual(box_wrap(f"{GREEN}hello{RESET}", width=20), f"""\
┌──────────────────┐
│ {GREEN}hello{RESET}            │
└──────────────────┘""")

    def test_empty_line(self):
        self.assertEqual(box_wrap("", width=10), """\
┌────────┐
└────────┘""")


if __name__ == '__main__':
    unittest.main()
