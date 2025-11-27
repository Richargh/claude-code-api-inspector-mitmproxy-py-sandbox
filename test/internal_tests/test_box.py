import unittest

from internal.box import box_wrap
from internal.colors import GREEN, RESET

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

    def test_with_header(self):
        self.assertEqual(box_wrap("hello", width=20, header="text"), """\
┌─text─────────────┐
│ hello            │
└──────────────────┘""")

    def test_with_footer(self):
        self.assertEqual(box_wrap("hello", width=20, footer="tool_result"), """\
┌──────────────────┐
│ hello            │
└──tool_result─────┘""")

    def test_with_header_and_footer(self):
        self.assertEqual(box_wrap("hello", width=20, header="tool_use Bash", footer="tool_result"), """\
┌─tool_use Bash────┐
│ hello            │
└──tool_result─────┘""")

    def test_no_top_border(self):
        self.assertEqual(box_wrap("hello", width=20, top=False), """\
│ hello            │
└──────────────────┘""")

    def test_no_bottom_border(self):
        self.assertEqual(box_wrap("hello", width=20, bottom=False), """\
┌──────────────────┐
│ hello            │""")

    def test_tool_use_to_tool_result(self):
        """Test connecting tool_use (no bottom) to tool_result (no top)."""
        tool_use = box_wrap("command: ls", width=20, header="tool_use Bash", bottom=False)
        tool_result = box_wrap("output", width=20, top=False, footer="tool_result")
        self.assertEqual(tool_use, """\
┌─tool_use Bash────┐
│ command: ls      │""")
        self.assertEqual(tool_result, """\
│ output           │
└──tool_result─────┘""")


if __name__ == '__main__':
    unittest.main()
