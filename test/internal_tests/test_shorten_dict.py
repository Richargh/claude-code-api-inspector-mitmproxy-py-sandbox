import unittest

from internal.shorten_dict import shorten_dict


class TestFormatToolInput(unittest.TestCase):
    def test_none_returns_empty(self):
        self.assertEqual(
            shorten_dict(None),
            "")

    def test_empty_dict_returns_empty(self):
        self.assertEqual(
            shorten_dict({}),
            "")

    def test_single_string_value(self):
        self.assertEqual(
            shorten_dict({"a": "1"}),
            """\
"a": "1"\
""")

    def test_multiple_keys_on_separate_lines(self):
        self.assertEqual(
            shorten_dict({"a": "1", "b": "2"}),
            """\
"a": "1"
"b": "2"\
""")

    def test_nested_dict_flattened(self):
        self.assertEqual(
            shorten_dict({"config": {"key": "value"}}),
            """\
"config": {"key": "value"}\
""")

    def test_long_value_shortened_in_middle(self):
        self.assertEqual(
            shorten_dict(
                {"file_path": "/Users/richardgross/Documents/GIT/Localbox/claude-eval-mitmproxy/README.adoc"},
                max_line_length=40),
            '"file_path": "/Use...mproxy/README.adoc"')

    def test_short_value_not_shortened(self):
        self.assertEqual(
            shorten_dict({"cmd": "ls"}, max_line_length=50),
            '"cmd": "ls"')

    def test_multi_line_value_shortened_in_middle(self):
        self.assertEqual(
            shorten_dict(
                {"names": "- Taylor\n- Jon\n- Alex\n- Shannon\n- Fly"},
                max_line_length=40),
            '"names": "- Taylor...ex\n- Shannon\n- Fly"')

    def test_multiple_long_values(self):
        self.assertEqual(
            shorten_dict({
                "file": "/very/long/path/to/some/file.txt",
                "dest": "/another/very/long/destination/path.txt"
            }, max_line_length=30),
            """\
"file": "/ver...some/file.txt"
"dest": "/ano...tion/path.txt"\
""")


if __name__ == '__main__':
    unittest.main()
