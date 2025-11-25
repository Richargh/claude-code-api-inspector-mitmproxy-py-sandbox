import json
import unittest
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

from print_agent_flows import response

class TableFlowsTest(unittest.TestCase):

    def test_response_extracts_model(self):
        """Test that the correct model is extracted from 1a-pre-request.json."""
        flow = self._create_mock_flow("hidden/1a-pre-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow)
            output = mock_stdout.getvalue()

        self.assertIn("model: claude-haiku-4-5-20250510", output)

    def test_response_extracts_last_message(self):
        """Test that last message is extracted from 1a-pre-request.json."""
        flow = self._create_mock_flow("hidden/1a-pre-request.json", {"result": "ok"})

        with patch('sys.stdout', new_callable=StringIO) as mock_stdout:
            response(flow)
            output = mock_stdout.getvalue()

        # Last message in fixture is assistant with content "{"
        self.assertIn("@assistant", output)
        self.assertIn("{", output)

    def test_response_handles_invalid_json(self):
        """Test that response() handles invalid JSON gracefully."""
        flow = MagicMock()
        flow.request = MagicMock()
        flow.request.url = "http://localhost:3000/mcp"
        flow.request.text = "not valid json"
        flow.response = None

        # Should not raise an exception
        response(flow)


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