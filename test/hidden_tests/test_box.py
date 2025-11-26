import unittest
from io import StringIO
from unittest.mock import patch

from hidden.box import print_box
from hidden.colors import GREEN, RESET

class TestPrintBox(unittest.TestCase):
    def test_simple_text(self):
        with patch('sys.stdout', new=StringIO()) as output:
            print_box("hello", width=20)
        self.assertEqual(output.getvalue(), """\
┌──────────────────┐
│ hello            │
└──────────────────┘
""")

    def test_multiline_text(self):
        with patch('sys.stdout', new=StringIO()) as output:
            print_box("line1\nline2", width=20)
        self.assertEqual(output.getvalue(), """\
┌──────────────────┐
│ line1            │
│ line2            │
└──────────────────┘
""")

    def test_wrapping_long_lines(self):
        with patch('sys.stdout', new=StringIO()) as output:
            print_box("aaaaaaaaaaaaaaaaaaaa", width=15)  # 20 a's, inner width is 11
        self.assertEqual(output.getvalue(), """\
┌─────────────┐
│ aaaaaaaaaaa │
│ aaaaaaaaa   │
└─────────────┘
""")

    def test_colored_text_alignment(self):
        with patch('sys.stdout', new=StringIO()) as output:
            print_box(f"{GREEN}hello{RESET}", width=20)
        self.assertEqual(output.getvalue(), f"""\
┌──────────────────┐
│ {GREEN}hello{RESET}            │
└──────────────────┘
""")

    def test_empty_line(self):
        with patch('sys.stdout', new=StringIO()) as output:
            print_box("", width=10)
        self.assertEqual(output.getvalue(), """\
┌────────┐
└────────┘
""")


if __name__ == '__main__':
    unittest.main()
