import json
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from print_agent_flows import response

class TableFlowsTest(unittest.TestCase):

    def test_response_extracts_model(self):
        """Test that the correct model is extracted from 2a-request.json."""
        flow = self._create_mock_flow("hidden/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow)
            output = mock_stdout.getvalue()

        self.assertIn("model:: claude-opus-4-5-20230415", output)

    def test_response_extracts_messages(self):
        """Test that messages are extracted and displayed."""
        flow = self._create_mock_flow("hidden/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow)
            output = mock_stdout.getvalue()

        self.assertIn("## Messages", output)
        self.assertIn("@user:", output)
        self.assertIn("@assistant:", output)

    def test_response_extracts_tool_use(self):
        """Test that tool_use content is displayed."""
        flow = self._create_mock_flow("hidden/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow)
            output = mock_stdout.getvalue()

        self.assertIn("[tool_use: Read]", output)
        self.assertIn("[tool_use: Edit]", output)

    def test_response_extracts_tool_result(self):
        """Test that tool_result content is displayed."""
        flow = self._create_mock_flow("hidden/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow)
            output = mock_stdout.getvalue()

        self.assertIn("[tool_result:", output)

    def test_response_extracts_system_prompts(self):
        """Test that system prompts are extracted."""
        flow = self._create_mock_flow("hidden/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow)
            output = mock_stdout.getvalue()

        self.assertIn("## System", output)
        self.assertIn("You are Claude Code", output)

    def test_response_extracts_tools(self):
        """Test that tools are extracted and displayed."""
        flow = self._create_mock_flow("hidden/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow)
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
        response(flow)

    def test_shows_only_last_10_messages(self):
        """Test that only the last 10 messages are shown."""
        flow = self._create_mock_flow("hidden/2a-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow)
            output = mock_stdout.getvalue()

        # Count occurrences of "@" which indicates message roles
        role_count = output.count("@user:") + output.count("@assistant:")
        self.assertLessEqual(role_count, 10)


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
