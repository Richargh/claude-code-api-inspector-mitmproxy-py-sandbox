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
        try:
            req = json.loads(raw_flow.request.text)
            req_flow.pretty = json.dumps(req, indent=2)
            req_flow.keys = list(req.keys())
            req_flow.model = req.get('model')

            # Parse messages
            messages = req.get('messages', [])
            for msg in messages:
                message = RequestMessage(role=msg.get('role', ''), content=[])
                content_list = msg.get('content', [])
                if isinstance(content_list, str):
                    # Handle simple string content format
                    message.content.append(TextBlock(text=content_list))
                else:
                    # Handle list of content blocks
                    for item in content_list:
                        item_type = item.get('type', '')
                        if item_type == 'text':
                            message.content.append(TextBlock(text=item.get('text', '')))
                        elif item_type == 'tool_use':
                            message.content.append(ToolUseBlock(
                                id=item.get('id'),
                                tool_name=item.get('name'),
                                input=item.get('input'),
                            ))
                        elif item_type == 'tool_result':
                            message.content.append(ToolResultBlock(
                                tool_use_id=item.get('tool_use_id'),
                                content=item.get('content'),
                            ))
                        elif item_type == 'server_tool_use':
                            message.content.append(ServerToolUseBlock(
                                id=item.get('id'),
                                tool_name=item.get('name'),
                                input=item.get('input'),
                            ))
                        elif item_type == 'server_tool_result':
                            message.content.append(ServerToolResultBlock(
                                tool_use_id=item.get('tool_use_id'),
                                content=item.get('content'),
                            ))
                req_flow.messages.append(message)

            # Parse system prompts
            system = req.get('system', [])
            for sys_item in system:
                text = sys_item.get('text', '')
                req_flow.system_prompts.append(SystemPrompt(text=text))

            # Parse tools
            tools = req.get('tools', [])
            for tool in tools:
                name = tool.get('name', '')
                if name:
                    req_flow.tools.append(name)
                    description = tool.get('description', '')
                    if description:
                        req_flow.tool_descriptions[name] = description

        except json.JSONDecodeError as e:
            req_flow.error = str(e)
        except (KeyError, IndexError, TypeError) as e:
            req_flow.error = str(e)

    if raw_flow.response and raw_flow.response.text:
        response_text = raw_flow.response.text
        content_type = raw_flow.response.headers.get('content-type', '')
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

    return (req_flow, res_flow)


def _parse_sse_response(text: str) -> ResponseMessage:
    """Parse SSE response and reconstruct full message with all content blocks."""
    events = _parse_sse(text)

    result = ResponseMessage()
    usage_data = {}
    content_blocks = {}  # Track blocks by index

    for event in events:
        data = event.get('data', {})
        if not isinstance(data, dict):
            continue

        event_type = data.get('type')

        if event_type == 'message_start':
            message = data.get('message', {})
            result.id = message.get('id')
            result.model = message.get('model')
            result.role = message.get('role', 'assistant')
            usage_data = message.get('usage', {})

        elif event_type == 'content_block_start':
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

        elif event_type == 'content_block_delta':
            index = data.get('index')
            delta = data.get('delta', {})
            if index in content_blocks:
                if delta.get('type') == 'text_delta':
                    content_blocks[index]['text'] += delta.get('text', '')
                elif delta.get('type') == 'input_json_delta':
                    content_blocks[index]['input'] += delta.get('partial_json', '')

        elif event_type == 'message_delta':
            delta = data.get('delta', {})
            result.stop_reason = delta.get('stop_reason')
            result.stop_sequence = delta.get('stop_sequence')
            usage_data.update(data.get('usage', {}))
            if 'context_management' in data:
                result.context_management = data['context_management']

    # Create Usage dataclass
    result.usage = Usage(
        input_tokens=usage_data.get('input_tokens'),
        output_tokens=usage_data.get('output_tokens'),
        cache_creation_input_tokens=usage_data.get('cache_creation_input_tokens'),
        cache_read_input_tokens=usage_data.get('cache_read_input_tokens'),
    )

    # Finalize content blocks
    for index in sorted(k for k in content_blocks.keys() if k is not None):
        block = content_blocks[index]
        if block['type'] == 'text':
            result.content.append(TextBlock(text=block['text']))
        elif block['type'] == 'tool_use':
            try:
                input_data = json.loads(block['input']) if block['input'] else {}
            except json.JSONDecodeError:
                input_data = block['input']
            result.content.append(ToolUseBlock(
                id=block['id'],
                tool_name=block['name'],
                input=input_data,
            ))
        elif block['type'] == 'server_tool_use':
            try:
                input_data = json.loads(block['input']) if block['input'] else {}
            except json.JSONDecodeError:
                input_data = block['input']
            result.content.append(ServerToolUseBlock(
                id=block['id'],
                tool_name=block['name'],
                input=input_data,
            ))
        elif block['type'] == 'web_search_tool_result':
            result.content.append(ServerToolResultBlock(
                type='web_search_tool_result',
                tool_use_id=block['tool_use_id'],
                content=block['content'],
            ))

    return result


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
