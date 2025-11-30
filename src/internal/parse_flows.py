from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any

from mitmproxy import http


@dataclass
class RequestFlow:
    pretty: str | None = None
    model: str | None = None
    keys: list[str] | None = None
    messages: list[RequestMessage] = field(default_factory=list)
    system_prompts: list[SystemPrompt] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    tool_descriptions: dict[str, str] = field(default_factory=dict)
    error: str | None = None

@dataclass
class RequestMessage:
    role: str
    content: list[
        TextBlock | ToolUseBlock | ToolResultBlock | ServerToolUseBlock | ServerToolResultBlock
    ] = field(default_factory=list)

@dataclass
class SystemPrompt:
    text: str



@dataclass
class ResponseFlow:
    pretty: str | None = None
    error: str | None = None
    message: ResponseMessage | None = None

@dataclass
class ResponseMessage:
    id: str | None = None
    type: str = 'message'
    role: str = 'assistant'
    model: str | None = None
    content: list[
        TextBlock | ToolUseBlock | ServerToolUseBlock | ServerToolResultBlock
    ] = field(default_factory=list)
    stop_reason: str | None = None
    stop_sequence: str | None = None
    usage: Usage | None = None
    context_management: dict | None = None

@dataclass
class TextBlock:
    type: str = 'text'
    text: str = ''

@dataclass
class ToolUseBlock:
    type: str = 'tool_use'
    id: str | None = None
    tool_name: str | None = None
    input: dict | None = None

@dataclass
class ServerToolUseBlock:
    type: str = 'server_tool_use'
    id: str | None = None
    tool_name: str | None = None
    input: dict | None = None

@dataclass
class ServerToolResultBlock:
    type: str = 'server_tool_result'
    tool_use_id: str | None = None
    content: list | None = None

@dataclass
class ToolResultBlock:
    type: str = 'tool_result'
    tool_use_id: str | None = None
    content: str | None = None

@dataclass
class Usage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    cache_creation_input_tokens: int | None = None
    cache_read_input_tokens: int | None = None


def parse_flow(raw_flow: http.HTTPFlow) -> tuple[RequestFlow, ResponseFlow]:
    """Parse an HTTP flow and return a tuple of (RequestFlow, ResponseFlow)."""
    req_flow = RequestFlow()
    res_flow = ResponseFlow()

    if raw_flow.request and raw_flow.request.text:
        _parse_request(req_flow, raw_flow.request.text)

    if raw_flow.response and raw_flow.response.text:
        _parse_response(res_flow, raw_flow.response.text, raw_flow.response.headers.get('content-type', ''))

    return req_flow, res_flow


def _parse_request(req_flow: RequestFlow, request_text: str) -> None:
    """Parse request JSON and populate req_flow."""
    try:
        req = json.loads(request_text)
        req_flow.pretty = json.dumps(req, indent=2)
        req_flow.keys = list(req.keys())
        req_flow.model = req.get('model')
        req_flow.messages = _parse_messages(req.get('messages', []))
        req_flow.system_prompts = _parse_system_prompts(req.get('system', []))
        _parse_tools(req_flow, req.get('tools', []))
    except json.JSONDecodeError as e:
        req_flow.error = str(e)
    except (KeyError, IndexError, TypeError) as e:
        req_flow.error = str(e)


def _parse_response(res_flow: ResponseFlow, response_text: str, content_type: str) -> None:
    """Parse response and populate res_flow."""
    if 'text/event-stream' in content_type:
        try:
            sse_data = _parse_sse_response(response_text)
            res_flow.pretty = json.dumps(asdict(sse_data), indent=2) + "\n" + response_text
            res_flow.message = sse_data
        except Exception as e:
            res_flow.error = str(e)
    else:
        try:
            json.loads(response_text)
        except json.JSONDecodeError as e:
            res_flow.error = str(e)


def _parse_messages(messages: list[dict]) -> list[RequestMessage]:
    """Parse raw message dicts into RequestMessage objects."""
    return [
        RequestMessage(
            role=msg.get('role', ''),
            content=_parse_content_list(msg.get('content', [])))
        for msg in messages
    ]


def _parse_content_list(content_list: str | list) -> list:
    """Parse content into a list of typed blocks."""
    if isinstance(content_list, str):
        return [TextBlock(text=content_list)]
    return [_parse_content_block(item) for item in content_list]


def _parse_content_block(
    item: dict,
) -> TextBlock | ToolUseBlock | ToolResultBlock | ServerToolUseBlock | ServerToolResultBlock:
    """Create a content block from a dict."""
    block_type = item.get('type', '')
    if block_type == 'text':
        return TextBlock(text=item.get('text', ''))
    if block_type == 'tool_use':
        return ToolUseBlock(
            id=item.get('id'),
            tool_name=item.get('name'),
            input=item.get('input'))
    if block_type == 'tool_result':
        return ToolResultBlock(
            tool_use_id=item.get('tool_use_id'),
            content=item.get('content'))
    if block_type == 'server_tool_use':
        return ServerToolUseBlock(
            id=item.get('id'),
            tool_name=item.get('name'),
            input=item.get('input'))
    if block_type == 'server_tool_result':
        return ServerToolResultBlock(
            tool_use_id=item.get('tool_use_id'),
            content=item.get('content'))
    return TextBlock()


def _parse_system_prompts(system: list[dict]) -> list[SystemPrompt]:
    """Parse system prompt dicts into SystemPrompt objects."""
    return [SystemPrompt(text=s.get('text', '')) for s in system]


def _parse_tools(req_flow: RequestFlow, tools: list[dict]) -> None:
    """Parse tools and populate req_flow.tools and req_flow.tool_descriptions."""
    for tool in tools:
        name = tool.get('name', '')
        if name:
            req_flow.tools.append(name)
            if desc := tool.get('description', ''):
                req_flow.tool_descriptions[name] = desc


def _parse_sse_response(text: str) -> ResponseMessage:
    """Parse SSE response and reconstruct full message with all content blocks."""
    events = _parse_sse(text)
    result = ResponseMessage()
    usage_data: dict = {}
    content_blocks: dict = {}

    for event in events:
        data = event.get('data', {})
        if not isinstance(data, dict):
            continue
        event_type = data.get('type')
        if event_type == 'message_start':
            _handle_message_start(result, usage_data, data)
        elif event_type == 'content_block_start':
            _handle_content_block_start(content_blocks, data)
        elif event_type == 'content_block_delta':
            _handle_content_block_delta(content_blocks, data)
        elif event_type == 'message_delta':
            _handle_message_delta(result, usage_data, data)

    result.usage = _create_usage(usage_data)
    result.content = _finalize_content_blocks(content_blocks)
    return result


def _handle_message_start(result: ResponseMessage, usage_data: dict, data: dict) -> None:
    """Handle message_start SSE event."""
    message = data.get('message', {})
    result.id = message.get('id')
    result.model = message.get('model')
    result.role = message.get('role', 'assistant')
    usage_data.update(message.get('usage', {}))


def _handle_content_block_start(content_blocks: dict, data: dict) -> None:
    """Handle content_block_start SSE event."""
    index = data.get('index')
    block = data.get('content_block', {})
    block_type = block.get('type')
    content_blocks[index] = {
        'type': block_type,
        'text': '' if block_type == 'text' else None,
        'id': block.get('id'),
        'name': block.get('name'),
        'input': '' if block_type in ('tool_use', 'server_tool_use') else None,
        'tool_use_id': block.get('tool_use_id'),
        'content': block.get('content'),
    }


def _handle_content_block_delta(content_blocks: dict, data: dict) -> None:
    """Handle content_block_delta SSE event."""
    index = data.get('index')
    delta = data.get('delta', {})
    if index not in content_blocks:
        return
    if delta.get('type') == 'text_delta':
        content_blocks[index]['text'] += delta.get('text', '')
    elif delta.get('type') == 'input_json_delta':
        content_blocks[index]['input'] += delta.get('partial_json', '')


def _handle_message_delta(result: ResponseMessage, usage_data: dict, data: dict) -> None:
    """Handle message_delta SSE event."""
    delta = data.get('delta', {})
    result.stop_reason = delta.get('stop_reason')
    result.stop_sequence = delta.get('stop_sequence')
    usage_data.update(data.get('usage', {}))
    if 'context_management' in data:
        result.context_management = data['context_management']


def _create_usage(usage_data: dict) -> Usage:
    """Create Usage dataclass from usage data dict."""
    return Usage(
        input_tokens=usage_data.get('input_tokens'),
        output_tokens=usage_data.get('output_tokens'),
        cache_creation_input_tokens=usage_data.get('cache_creation_input_tokens'),
        cache_read_input_tokens=usage_data.get('cache_read_input_tokens'),
    )


def _finalize_content_blocks(content_blocks: dict) -> list:
    """Convert accumulated block data into typed block objects."""
    result = []
    for index in sorted(k for k in content_blocks if k is not None):
        block = content_blocks[index]
        result.append(_finalize_block(block))
    return result


def _finalize_block(block: dict) -> TextBlock | ToolUseBlock | ServerToolUseBlock | ServerToolResultBlock:
    """Convert a single accumulated block dict into a typed block object."""
    block_type = block['type']
    if block_type == 'text':
        return TextBlock(text=block['text'])
    if block_type in ('tool_use', 'server_tool_use'):
        input_data = _parse_json_input(block['input'])
        cls = ToolUseBlock if block_type == 'tool_use' else ServerToolUseBlock
        return cls(
            id=block['id'],
            tool_name=block['name'],
            input=input_data)
    if block_type == 'web_search_tool_result':
        return ServerToolResultBlock(
            type='web_search_tool_result',
            tool_use_id=block['tool_use_id'],
            content=block['content']
        )
    return TextBlock()


def _parse_json_input(input_str: str | None) -> dict[str, Any] | None:
    """Parse JSON input string, returning empty dict on failure."""
    if not input_str:
        return {}
    try:
        result: dict[str, Any] = json.loads(input_str)
        return result
    except json.JSONDecodeError:
        return {}


def _parse_sse(text: str) -> list[dict[str, Any]]:
    """Parse Server-Sent Events text into a list of event dicts."""
    events: list[dict[str, Any]] = []
    current_event: dict[str, Any] = {}

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
