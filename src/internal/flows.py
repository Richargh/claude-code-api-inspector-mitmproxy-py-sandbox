import json
from dataclasses import dataclass, field, asdict
from typing import Optional, Union

@dataclass
class RequestFlow:
    pretty: Optional[str] = None
    model: Optional[str] = None
    keys: Optional[list[str]] = None
    messages: list['RequestMessage'] = field(default_factory=list)
    system_prompts: list['SystemPrompt'] = field(default_factory=list)
    tools: list[str] = field(default_factory=list)
    tool_descriptions: dict[str, str] = field(default_factory=dict)
    error: Optional[str] = None

@dataclass
class RequestMessage:
    role: str
    content: list['RequestMessageContent'] = field(default_factory=list)

@dataclass
class RequestMessageContent:
    type: str
    text: Optional[str] = None
    tool_name: Optional[str] = None

@dataclass
class SystemPrompt:
    text: str



@dataclass
class ResponseFlow:
    pretty: Optional[str] = None
    error: Optional[str] = None
    message: Optional['ResponseMessage'] = None

@dataclass
class ResponseMessage:
    id: Optional[str] = None
    type: str = 'message'
    role: str = 'assistant'
    model: Optional[str] = None
    content: list[Union['TextBlock', 'ToolUseBlock', 'ServerToolUseBlock', 'ServerToolResultBlock']] = field(default_factory=list)
    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None
    usage: Optional['Usage'] = None
    context_management: Optional[dict] = None

@dataclass
class TextBlock:
    type: str = 'text'
    text: str = ''

@dataclass
class ToolUseBlock:
    type: str = 'tool_use'
    id: Optional[str] = None
    tool_name: Optional[str] = None
    input: Optional[dict] = None

@dataclass
class ServerToolUseBlock:
    type: str = 'server_tool_use'
    id: Optional[str] = None
    tool_name: Optional[str] = None
    input: Optional[dict] = None

@dataclass
class ServerToolResultBlock:
    type: str = 'server_tool_result'
    tool_use_id: Optional[str] = None
    content: Optional[list] = None

@dataclass
class Usage:
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    cache_creation_input_tokens: Optional[int] = None
    cache_read_input_tokens: Optional[int] = None


def parse_flow(raw_flow) -> tuple[RequestFlow, ResponseFlow]:
    """Parse an HTTP flow and return a tuple of (RequestFlow, ResponseFlow)."""
    req_flow = RequestFlow()
    res_flow = ResponseFlow()

    if raw_flow.request:
        try:
            req = json.loads(raw_flow.request.text)
            req_flow.pretty = json.dumps(req, indent=2)
            req_flow.keys = list(req.keys())
            req_flow.model = req.get('model')

            # Parse messages
            messages = req.get('messages', [])
            for msg in messages:
                role = msg.get('role', '')
                content_list = msg.get('content', [])
                parsed_content = []
                if isinstance(content_list, str):
                    # Handle simple string content format
                    parsed_content.append(RequestMessageContent(type='text', text=content_list))
                else:
                    # Handle list of content blocks
                    for item in content_list:
                        item_type = item.get('type', '')
                        if item_type == 'text':
                            parsed_content.append(RequestMessageContent(type='text', text=item.get('text', '')))
                        elif item_type == 'tool_use':
                            parsed_content.append(RequestMessageContent(type='tool_use', tool_name=item.get('name', '')))
                        elif item_type == 'tool_result':
                            parsed_content.append(RequestMessageContent(type='tool_result', text=item.get('content', '')))
                req_flow.messages.append(RequestMessage(role=role, content=parsed_content))

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

    if raw_flow.response:
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
    for index in sorted(content_blocks.keys()):
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