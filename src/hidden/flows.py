import json
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class MessageContent:
    type: str
    text: Optional[str] = None
    tool_name: Optional[str] = None

@dataclass
class Message:
    role: str
    content: list[MessageContent] = field(default_factory=list)

@dataclass
class SystemPrompt:
    text: str

@dataclass
class FlowRecord:
    model: Optional[str] = None
    request_keys: Optional[list[str]] = None
    messages: list[Message] = field(default_factory=list)
    system_prompts: list[SystemPrompt] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    request_error: Optional[str] = None
    response_error: Optional[str] = None
    # Response fields from SSE
    response_text: Optional[str] = None
    response_model: Optional[str] = None
    response_stop_reason: Optional[str] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None


def parse_flow(flow) -> FlowRecord:
    """Parse an HTTP flow and return a FlowRecord with extracted data."""
    record = FlowRecord()
    if flow.request:
        try:
            req = json.loads(flow.request.text)
            record.request_keys = list(req.keys())
            record.model = req.get('model')

            # Parse messages
            messages = req.get('messages', [])
            for msg in messages:
                role = msg.get('role', '')
                content_list = msg.get('content', [])
                parsed_content = []
                if isinstance(content_list, str):
                    # Handle simple string content format
                    parsed_content.append(MessageContent(type='text', text=content_list))
                else:
                    # Handle list of content blocks
                    for item in content_list:
                        item_type = item.get('type', '')
                        if item_type == 'text':
                            parsed_content.append(MessageContent(type='text', text=item.get('text', '')))
                        elif item_type == 'tool_use':
                            parsed_content.append(MessageContent(type='tool_use', tool_name=item.get('name', '')))
                        elif item_type == 'tool_result':
                            parsed_content.append(MessageContent(type='tool_result', text=item.get('content', '')))
                record.messages.append(Message(role=role, content=parsed_content))

            # Parse system prompts
            system = req.get('system', [])
            for sys_item in system:
                text = sys_item.get('text', '')
                record.system_prompts.append(SystemPrompt(text=text))

            # Parse tools
            tools = req.get('tools', [])
            for tool in tools:
                name = tool.get('name', '')
                if name:
                    record.tools.append(name)

        except json.JSONDecodeError as e:
            record.request_error = str(e)
        except (KeyError, IndexError, TypeError) as e:
            record.request_error = str(e)

    if flow.response:
        response_text = flow.response.text
        content_type = flow.response.headers.get('content-type', '')
        if 'text/event-stream' in content_type:
            try:
                sse_data = _parse_sse_response(response_text)
                record.response_model = sse_data['model']
                record.response_text = sse_data['text']
                record.response_stop_reason = sse_data['stop_reason']
                record.input_tokens = sse_data['input_tokens']
                record.output_tokens = sse_data['output_tokens']
            except Exception as e:
                record.response_error = str(e)
        else:
            try:
                json.loads(response_text)
            except json.JSONDecodeError as e:
                record.response_error = str(e)

    return record


def _parse_sse_response(text: str) -> dict:
    """Parse SSE response and extract combined content and metadata."""
    events = _parse_sse(text)

    result = {
        'model': None,
        'text': '',
        'stop_reason': None,
        'input_tokens': None,
        'output_tokens': None,
    }

    for event in events:
        data = event.get('data', {})
        if not isinstance(data, dict):
            continue

        event_type = data.get('type')

        if event_type == 'message_start':
            message = data.get('message', {})
            result['model'] = message.get('model')
            usage = message.get('usage', {})
            result['input_tokens'] = usage.get('input_tokens')
            result['output_tokens'] = usage.get('output_tokens')

        elif event_type == 'content_block_delta':
            delta = data.get('delta', {})
            if delta.get('type') == 'text_delta':
                result['text'] += delta.get('text', '')

        elif event_type == 'message_delta':
            delta = data.get('delta', {})
            result['stop_reason'] = delta.get('stop_reason')
            usage = data.get('usage', {})
            if usage.get('output_tokens'):
                result['output_tokens'] = usage.get('output_tokens')

    return result


def _parse_sse(text: str) -> list[dict]:
    """Parse Server-Sent Events text into a list of event dicts."""
    events = []
    current_event = {}

    for line in text.split('\n'):
        line = line.strip()
        if not line:
            continue

        if line.startswith('event:'):
            # If we already have a complete event (has data), save it
            if 'data' in current_event:
                events.append(current_event)
                current_event = {}
            current_event['event'] = line[6:].strip()
        elif line.startswith('data:'):
            data_str = line[5:].strip()
            try:
                current_event['data'] = json.loads(data_str)
            except json.JSONDecodeError:
                current_event['data'] = data_str

    # Don't forget the last event
    if current_event and 'data' in current_event:
        events.append(current_event)

    return events