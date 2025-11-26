import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from hidden.flows import RequestFlow, ResponseFlow, parse_flow
from hidden.flows import _parse_sse as parse_sse, _parse_sse_response as parse_sse_response


class TestParseFlow(unittest.TestCase):

    def test_parse_flow_extracts_model(self):
        """Test that model is extracted from 1a-pre-request.json."""
        flow = self._create_mock_flow("1a-pre-request.json")

        req_flow, res_flow = parse_flow(flow)

        self.assertEqual(req_flow.model, "claude-haiku-4-5-20250510")

    def test_parse_flow_extracts_messages(self):
        """Test that messages are extracted."""
        flow = self._create_mock_flow("1a-pre-request.json")

        req_flow, res_flow = parse_flow(flow)

        self.assertGreater(len(req_flow.messages), 0)
        self.assertEqual(req_flow.messages[-1].role, "assistant")

    def test_parse_flow_returns_tuple(self):
        """Test that parse_flow returns a tuple of (RequestFlow, ResponseFlow)."""
        flow = self._create_mock_flow("1a-pre-request.json")

        result = parse_flow(flow)

        self.assertIsInstance(result, tuple)
        self.assertEqual(len(result), 2)
        self.assertIsInstance(result[0], RequestFlow)
        self.assertIsInstance(result[1], ResponseFlow)

    def test_parse_flow_handles_invalid_json(self):
        """Test that invalid JSON sets error."""
        flow = MagicMock()
        flow.request = MagicMock()
        flow.request.text = "not valid json"
        flow.response = None

        req_flow, res_flow = parse_flow(flow)

        self.assertIsNotNone(req_flow.error)
        self.assertIsNone(req_flow.model)

    def test_parse_flow_handles_missing_request(self):
        """Test handling when request is None."""
        flow = MagicMock()
        flow.request = None
        flow.response = None

        req_flow, res_flow = parse_flow(flow)

        self.assertIsNone(req_flow.model)
        self.assertIsNone(req_flow.error)

    def test_parse_flow_handles_empty_messages(self):
        """Test handling when messages array is empty."""
        flow = MagicMock()
        flow.request = MagicMock()
        flow.request.text = json.dumps({"model": "test", "messages": []})
        flow.response = None

        req_flow, res_flow = parse_flow(flow)

        self.assertEqual(req_flow.model, "test")
        self.assertEqual(len(req_flow.messages), 0)

    def test_parse_flow_handles_response_invalid_json(self):
        """Test that invalid response JSON sets error."""
        flow = self._create_mock_flow("1a-pre-request.json")
        flow.response = MagicMock()
        flow.response.text = "invalid response json"
        flow.response.headers = {'content-type': 'application/json'}

        req_flow, res_flow = parse_flow(flow)

        self.assertIsNotNone(res_flow.error)

    def test_parse_flow_handles_valid_response(self):
        """Test that valid response JSON doesn't set error."""
        flow = self._create_mock_flow("1a-pre-request.json")
        flow.response = MagicMock()
        flow.response.text = json.dumps({"result": "ok"})
        flow.response.headers = {'content-type': 'application/json'}

        req_flow, res_flow = parse_flow(flow)

        self.assertIsNone(res_flow.error)

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

        self.assertEqual(result.model, 'claude-haiku-4-5-20250510')

    def test_parse_sse_response_combines_text_deltas(self):
        """Test that parse_sse_response combines all text deltas into content block."""
        fixture_path = Path(__file__).parent / "1b-pre-response.json"
        with open(fixture_path) as f:
            sse_text = f.read()

        result = parse_sse_response(sse_text)

        self.assertEqual(len(result.content), 1)
        self.assertEqual(result.content[0].type, 'text')
        self.assertIn('isNewTopic', result.content[0].text)
        self.assertIn('Code', result.content[0].text)
        self.assertIn('Analysis', result.content[0].text)

    def test_parse_sse_response_extracts_stop_reason(self):
        """Test that parse_sse_response extracts stop_reason."""
        fixture_path = Path(__file__).parent / "1b-pre-response.json"
        with open(fixture_path) as f:
            sse_text = f.read()

        result = parse_sse_response(sse_text)

        self.assertEqual(result.stop_reason, 'end_turn')

    def test_parse_sse_response_extracts_token_usage(self):
        """Test that parse_sse_response extracts token counts in usage dataclass."""
        fixture_path = Path(__file__).parent / "1b-pre-response.json"
        with open(fixture_path) as f:
            sse_text = f.read()

        result = parse_sse_response(sse_text)

        self.assertEqual(result.usage.input_tokens, 120)
        self.assertEqual(result.usage.output_tokens, 30)

    def test_parse_sse_response_extracts_message_id(self):
        """Test that parse_sse_response extracts message id."""
        fixture_path = Path(__file__).parent / "1b-pre-response.json"
        with open(fixture_path) as f:
            sse_text = f.read()

        result = parse_sse_response(sse_text)

        self.assertEqual(result.id, 'msg_1234')
        self.assertEqual(result.role, 'assistant')
        self.assertEqual(result.type, 'message')


class TestParseFlowWithSSE(unittest.TestCase):

    def test_parse_flow_with_sse_response(self):
        """Test parse_flow with SSE response from 1b-pre-response.json."""
        flow = self._create_mock_flow("1a-pre-request.json", "1b-pre-response.json")

        req_flow, res_flow = parse_flow(flow)

        self.assertIsNotNone(res_flow.message)
        self.assertEqual(res_flow.message.model, 'claude-haiku-4-5-20250510')
        self.assertEqual(res_flow.message.id, 'msg_1234')
        self.assertEqual(len(res_flow.message.content), 1)
        self.assertIn('isNewTopic', res_flow.message.content[0].text)
        self.assertEqual(res_flow.message.stop_reason, 'end_turn')
        self.assertEqual(res_flow.message.usage.input_tokens, 120)
        self.assertEqual(res_flow.message.usage.output_tokens, 30)

    def test_parse_flow_sse_no_error(self):
        """Test that SSE response doesn't set error."""
        flow = self._create_mock_flow("1a-pre-request.json", "1b-pre-response.json")

        req_flow, res_flow = parse_flow(flow)

        self.assertIsNone(res_flow.error)

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