import unittest

from hidden.border_line import border_line, border_line_tool_use, border_line_tool_result


class TestBorderLine(unittest.TestCase):
    def test_single_line(self):
        self.assertEqual(border_line("First line", width=20), """\
│>First line""")

    def test_multiline(self):
        self.assertEqual(border_line("First line\nSecond line\nThird line", width=20), """\
│>First line
│ Second line
│ Third line""")

    def test_wrapping(self):
        self.assertEqual(border_line("aaaaaaaaaaaaaaaaaa", width=12), """\
│>aaaaaaaaaa
│ aaaaaaaa""")


class TestBorderLineToolUse(unittest.TestCase):
    def test_tool_use(self):
        self.assertEqual(border_line_tool_use("Bash", "command: ls", width=40), """\
│──tool_use Bash────────────────────────
│ command: ls""")

    def test_tool_use_multiline(self):
        self.assertEqual(border_line_tool_use("Read", "file: test.py\nlines: 100", width=40), """\
│──tool_use Read────────────────────────
│ file: test.py
│ lines: 100""")

    def test_tool_use_wrapping(self):
        self.assertEqual(border_line_tool_use("Bash", "aaaaaaaaaaaaaaaaaaaaaa", width=15), """\
│──tool_use Bash─
│ aaaaaaaaaaaaa
│ aaaaaaaaa""")


class TestBorderLineToolResult(unittest.TestCase):
    def test_tool_result(self):
        self.assertEqual(border_line_tool_result("output data", width=40), """\
│ output data
│──tool_result──────────────────────────""")

    def test_tool_result_multiline(self):
        self.assertEqual(border_line_tool_result("line 1\nline 2\nline 3", width=40), """\
│ line 1
│ line 2
│ line 3
│──tool_result──────────────────────────""")

    def test_tool_result_wrapping(self):
        self.assertEqual(border_line_tool_result("aaaaaaaaaaaaaaaaaaaaaa", width=15), """\
│ aaaaaaaaaaaaa
│ aaaaaaaaa
│──tool_result─""")


if __name__ == '__main__':
    unittest.main()
