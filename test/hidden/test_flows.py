import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from flows import FlowRecord, parse_flow, parse_sse, parse_sse_response


class TestParseFlow(unittest.TestCase):

    def test_parse_flow_extracts_model(self):
        """Test that model is extracted from 1a-pre-request.json."""
        flow = self._create_mock_flow("1a-pre-request.json")

        record = parse_flow(flow)

        self.assertEqual(record.model, "claude-haiku-4-5-20250510")

    def test_parse_flow_extracts_last_message_role(self):
        """Test that last message role is extracted."""
        flow = self._create_mock_flow("1a-pre-request.json")

        record = parse_flow(flow)

        self.assertEqual(record.last_message_role, "assistant")

    def test_parse_flow_extracts_last_message_text(self):
        """Test that last message text is extracted."""
        flow = self._create_mock_flow("1a-pre-request.json")

        record = parse_flow(flow)

        self.assertEqual(record.last_message_text, "{")

    def test_parse_flow_returns_flow_record(self):
        """Test that parse_flow returns a FlowRecord instance."""
        flow = self._create_mock_flow("1a-pre-request.json")

        record = parse_flow(flow)

        self.assertIsInstance(record, FlowRecord)

    def test_parse_flow_handles_invalid_json(self):
        """Test that invalid JSON sets request_error."""
        flow = MagicMock()
        flow.request = MagicMock()
        flow.request.text = "not valid json"
        flow.response = None

        record = parse_flow(flow)

        self.assertIsNotNone(record.request_error)
        self.assertIsNone(record.model)

    def test_parse_flow_handles_missing_request(self):
        """Test handling when request is None."""
        flow = MagicMock()
        flow.request = None
        flow.response = None

        record = parse_flow(flow)

        self.assertIsNone(record.model)
        self.assertIsNone(record.request_error)

    def test_parse_flow_handles_empty_messages(self):
        """Test handling when messages array is empty."""
        flow = MagicMock()
        flow.request = MagicMock()
        flow.request.text = json.dumps({"model": "test", "messages": []})
        flow.response = None

        record = parse_flow(flow)

        self.assertEqual(record.model, "test")
        self.assertIsNone(record.last_message_role)

    def test_parse_flow_handles_response_invalid_json(self):
        """Test that invalid response JSON sets response_error."""
        flow = self._create_mock_flow("1a-pre-request.json")
        flow.response = MagicMock()
        flow.response.text = "invalid response json"
        flow.response.headers = {'content-type': 'application/json'}

        record = parse_flow(flow)

        self.assertIsNotNone(record.response_error)

    def test_parse_flow_handles_valid_response(self):
        """Test that valid response JSON doesn't set error."""
        flow = self._create_mock_flow("1a-pre-request.json")
        flow.response = MagicMock()
        flow.response.text = json.dumps({"result": "ok"})
        flow.response.headers = {'content-type': 'application/json'}

        record = parse_flow(flow)

        self.assertIsNone(record.response_error)

    def _create_mock_flow(self, request_file, response_file=None):
        """Helper to create a mock flow from fixture files."""
        fixture_path = Path(__file__).parent / request_file
        with open(fixture_path) as f:
            request_data = json.load(f)

        flow = MagicMock()
        flow.request = MagicMock()
        flow.request.text = json.dumps(request_data)

        if response_file:
            response_path = Path(__file__).parent / response_file
            with open(response_path) as f:
                flow.response = MagicMock()
                flow.response.text = f.read()
        else:
            flow.response = None

        return flow


class TestParseSSE(unittest.TestCase):

    def test_parse_sse_extracts_events(self):
        """Test that parse_sse extracts events from 1b-pre-response.json."""
        fixture_path = Path(__file__).parent / "1b-pre-response.json"
        with open(fixture_path) as f:
            sse_text = f.read()

        events = parse_sse(sse_text)

        self.assertGreater(len(events), 0)
        self.assertEqual(events[0]['event'], 'message_start')

    def test_parse_sse_parses_json_data(self):
        """Test that parse_sse parses JSON in data fields."""
        fixture_path = Path(__file__).parent / "1b-pre-response.json"
        with open(fixture_path) as f:
            sse_text = f.read()

        events = parse_sse(sse_text)

        # First event should have parsed JSON data
        self.assertIsInstance(events[0]['data'], dict)
        self.assertEqual(events[0]['data']['type'], 'message_start')

    def test_parse_sse_response_extracts_model(self):
        """Test that parse_sse_response extracts model from SSE."""
        fixture_path = Path(__file__).parent / "1b-pre-response.json"
        with open(fixture_path) as f:
            sse_text = f.read()

        result = parse_sse_response(sse_text)

        self.assertEqual(result['model'], 'claude-haiku-4-5-20250510')

    def test_parse_sse_response_combines_text_deltas(self):
        """Test that parse_sse_response combines all text deltas."""
        fixture_path = Path(__file__).parent / "1b-pre-response.json"
        with open(fixture_path) as f:
            sse_text = f.read()

        result = parse_sse_response(sse_text)

        self.assertIn('isNewTopic', result['text'])
        self.assertIn('Code', result['text'])
        self.assertIn('Analysis', result['text'])

    def test_parse_sse_response_extracts_stop_reason(self):
        """Test that parse_sse_response extracts stop_reason."""
        fixture_path = Path(__file__).parent / "1b-pre-response.json"
        with open(fixture_path) as f:
            sse_text = f.read()

        result = parse_sse_response(sse_text)

        self.assertEqual(result['stop_reason'], 'end_turn')

    def test_parse_sse_response_extracts_token_usage(self):
        """Test that parse_sse_response extracts token counts."""
        fixture_path = Path(__file__).parent / "1b-pre-response.json"
        with open(fixture_path) as f:
            sse_text = f.read()

        result = parse_sse_response(sse_text)

        self.assertEqual(result['input_tokens'], 120)
        self.assertEqual(result['output_tokens'], 30)


class TestParseFlowWithSSE(unittest.TestCase):

    def test_parse_flow_with_sse_response(self):
        """Test parse_flow with SSE response from 1b-pre-response.json."""
        flow = self._create_mock_flow("1a-pre-request.json", "1b-pre-response.json")

        record = parse_flow(flow)

        self.assertEqual(record.response_model, 'claude-haiku-4-5-20250510')
        self.assertIn('isNewTopic', record.response_text)
        self.assertEqual(record.response_stop_reason, 'end_turn')
        self.assertEqual(record.input_tokens, 120)
        self.assertEqual(record.output_tokens, 30)

    def test_parse_flow_sse_no_error(self):
        """Test that SSE response doesn't set response_error."""
        flow = self._create_mock_flow("1a-pre-request.json", "1b-pre-response.json")

        record = parse_flow(flow)

        self.assertIsNone(record.response_error)

    def _create_mock_flow(self, request_file, response_file=None):
        """Helper to create a mock flow from fixture files."""
        fixture_path = Path(__file__).parent / request_file
        with open(fixture_path) as f:
            request_data = json.load(f)

        flow = MagicMock()
        flow.request = MagicMock()
        flow.request.text = json.dumps(request_data)

        if response_file:
            response_path = Path(__file__).parent / response_file
            with open(response_path) as f:
                flow.response = MagicMock()
                flow.response.text = f.read()
                flow.response.headers = {'content-type': 'text/event-stream'}
        else:
            flow.response = None

        return flow


if __name__ == '__main__':
    unittest.main()