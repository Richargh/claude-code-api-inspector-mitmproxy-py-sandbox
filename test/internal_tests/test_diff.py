import unittest
from pathlib import Path

from internal.diff import diff_system_prompts, Colorize
from internal.flow_config import FlowConfig


class DiffSystemPromptsTest(unittest.TestCase):

    def test_identical_prompts_return_empty(self):
        """Test that identical prompts return an empty string."""
        prompt = "Hello\nWorld"
        result = diff_system_prompts(prompt, prompt, FlowConfig(colorize=Colorize.NONE))
        self.assertEqual(result, '')

    def test_additions_show_plus_lines(self):
        """Test that additions are shown with + lines."""
        prompt1 = "Hello"
        prompt2 = "Hello\nWorld"
        result = diff_system_prompts(prompt1, prompt2, FlowConfig(colorize=Colorize.NONE))
        self.assertIn('+World', result)

    def test_deletions_show_minus_lines(self):
        """Test that deletions are shown with - lines."""
        prompt1 = "Hello\nWorld"
        prompt2 = "Hello"
        result = diff_system_prompts(prompt1, prompt2, FlowConfig(colorize=Colorize.NONE))
        self.assertIn('-World', result)

    def test_modifications_show_both(self):
        """Test that modifications show both + and - lines."""
        prompt1 = "Hello\nWorld"
        prompt2 = "Hello\nPlanet"
        result = diff_system_prompts(prompt1, prompt2, FlowConfig(colorize=Colorize.NONE))
        self.assertIn('-World', result)
        self.assertIn('+Planet', result)

    def test_with_fixture_files(self):
        """Test with the actual fixture files."""
        fixtures_dir = Path(__file__).parent
        prompt1_path = fixtures_dir / 'system-prompt-1.md'
        prompt2_path = fixtures_dir / 'system-prompt-2.md'

        prompt1 = prompt1_path.read_text()
        prompt2 = prompt2_path.read_text()
        result = diff_system_prompts(prompt1, prompt2, FlowConfig(colorize=Colorize.NONE))
        # Verify diff contains expected changes
        self.assertIn('-Platform: surprise', result)
        self.assertIn('+Platform: Neo', result)
        self.assertIn('-Current branch: master', result)
        self.assertIn('+Current branch: trunk', result)

        expected = (
            "--- previous+++ current@@ -123,9 +123,9 @@ <env>\n"
            " Working directory: phoenix/\n"
            " Is directory a git repo: Yes\n"
            "-Platform: surprise\n"
            "-OS Version: Surprise 9.0.0.1\n"
            "-Today's date: 2020-10-14\n"
            "+Platform: Neo\n"
            "+OS Version: Neo 0.9.9.9\n"
            "+Today's date: 2022-10-14\n"
            " </env>\n"
            " You are powered by the model named Opus 3.5. The exact model ID is claude-opus-3-5-20201002.\n"
            " \n"
            "@@ -151,7 +151,7 @@ </example>\n"
            " \n"
            " gitStatus: This is the git status at the start of the conversation. Note that this status is a snapshot in time, and will not update during the conversation.\n"
            "-Current branch: master\n"
            "+Current branch: trunk\n"
            " \n"
            " Main branch (you will usually use this for PRs): trunk\n"
            " \n"
            "@@ -159,6 +159,4 @@ D  README.md\n"
            " \n"
            " Recent commits:\n"
            "-abee9a23de [P-123][P-abc] Enable thread popouts in the browser (#3444)\n"
            "-0d181ca215 Push Proxy Authentication (#3555)\n"
            "-c89450e2cf Update to Vitest (#3666)+123456 [P-adc] Not doing a thing."
        )
        self.assertEqual(result, expected)


if __name__ == '__main__':
    unittest.main()
