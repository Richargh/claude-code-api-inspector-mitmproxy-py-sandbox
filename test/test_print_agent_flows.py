import json
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from internal.colors import GRAY, BLUE, RESET
from internal.flow_config import FlowConfig
from print_agent_flows import response


class TableFlowsTest(unittest.TestCase):

    def test_response_extracts_model(self):
        """Test that the correct model is extracted from 2a-request.json."""
        flow = self._create_mock_flow("internal_tests/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow, FlowConfig(write_trace=False))
            output = mock_stdout.getvalue()

        self.assertIn("model:: claude-opus-4-5-20230415", output)

    def test_response_extracts_messages(self):
        """Test that messages are extracted and displayed."""
        flow = self._create_mock_flow("internal_tests/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow, FlowConfig(write_trace=False))
            output = mock_stdout.getvalue()

        self.assertIn("## Messages", output)
        self.assertIn("by user:", output)
        self.assertIn("by assistant:", output)

    def test_response_extracts_tool_use(self):
        """Test that tool_use content is displayed."""
        flow = self._create_mock_flow("internal_tests/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow, FlowConfig(write_trace=False))
            output = mock_stdout.getvalue()

        # Tool names appear in box headers like "┌─tool_use Read ─"
        self.assertIn("tool_use Read", output)
        self.assertIn("tool_use Edit", output)

    def test_response_extracts_tool_result(self):
        """Test that tool_result content is displayed."""
        flow = self._create_mock_flow("internal_tests/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow, FlowConfig(write_trace=False))
            output = mock_stdout.getvalue()

        self.assertIn("tool_result", output)

    def test_response_extracts_system_prompts(self):
        """Test that system prompts are extracted."""
        flow = self._create_mock_flow("internal_tests/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow, FlowConfig(write_trace=False))
            output = mock_stdout.getvalue()

        self.assertIn("## System", output)
        self.assertIn("You are Claude Code", output)

    def test_response_extracts_tools(self):
        """Test that tools are extracted and displayed."""
        flow = self._create_mock_flow("internal_tests/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow, FlowConfig(write_trace=False))
            output = mock_stdout.getvalue()

        self.assertIn("## Tools", output)
        self.assertIn("Task", output)

    def test_response_handles_invalid_json(self):
        """Test that response() handles invalid JSON gracefully."""
        flow = MagicMock()
        flow.request = MagicMock()
        flow.request.url = "http://localhost:3000/mcp"
        flow.request.text = "not valid json"
        flow.response = None

        # Should not raise an exception
        response(flow, FlowConfig(write_trace=False))

    def test_shows_only_last_10_messages(self):
        """Test that only the last 10 messages are shown."""
        flow = self._create_mock_flow("internal_tests/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow, FlowConfig(write_trace=False))
            output = mock_stdout.getvalue()

        # Count occurrences of "by user:" and "by assistant:" which indicate message roles
        role_count = output.count("by user:") + output.count("by assistant:")
        self.assertLessEqual(role_count, 10)

    def test_highlights_only_last_user_text_not_system(self):
        """Test that only the last user text (not starting with <system) is highlighted."""
        flow = self._create_mock_flow("internal_tests/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow, FlowConfig(write_trace=False))
            output = mock_stdout.getvalue()

        # The last non-system user text is "This line should also extract..."
        # It should NOT be preceded by GRAY
        last_user_text = "This line should also extract"
        self.assertIn(last_user_text, output)
        self.assertNotIn(f"{GRAY}┌─text", output.split(last_user_text)[0].split('\n')[-2])

        # Other user texts like "Where is x?" should be in GRAY
        self.assertIn(f"{GRAY}┌─text", output)

    def test_detects_conversation_summary(self):
        """Test that auto-generated conversation summaries are detected and displayed with special header."""

        # Create a request with a conversation summary in a user message
        request_data = {
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text":
                                "This session is being continued from a previous conversation that ran out of context."
                                " The conversation is summarized below:"
                                "\n\nAnalysis:\n[summary content here]"
                        }
                    ]
                }
            ]
        }

        flow = MagicMock()
        flow.request = MagicMock()
        flow.request.url = "http://localhost:3000"
        flow.request.text = json.dumps(request_data)
        flow.response = None

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow, FlowConfig(write_trace=False))
            output = mock_stdout.getvalue()

        self.assertIn(f"┌─{BLUE}conversation summary{RESET}──────────────────────────", output)

    def _create_mock_flow(self, request_file, response_data=None):
        """Helper to create a mock mitmproxy HTTPFlow."""
        fixture_path = Path(__file__).parent / request_file
        with open(fixture_path) as f:
            request_data = json.load(f)

        flow = MagicMock()
        flow.request = MagicMock()
        flow.request.url = "http://localhost:3000"
        flow.request.text = json.dumps(request_data)

        if response_data:
            flow.response = MagicMock()
            flow.response.text = json.dumps(response_data)
        else:
            flow.response = None

        return flow


if __name__ == '__main__':
    unittest.main()
