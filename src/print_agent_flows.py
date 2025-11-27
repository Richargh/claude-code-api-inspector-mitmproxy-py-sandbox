import json
from textwrap import shorten
from pathlib import Path
from typing import Union

from hidden.colors import RED, GREEN, RESET, Colorize
from hidden.flows import parse_flow, RequestFlow, ResponseFlow, TextBlock, ToolUseBlock, ServerToolUseBlock, \
    ServerToolResultBlock
from hidden.box import box_wrap
from datetime import datetime
from hidden.print_request import print_request


def response(raw_flow, colorize: Colorize = Colorize.ALL) -> None:
    req_flow, res_flow = parse_flow(raw_flow)
    raw_request_file, raw_response_file = _write_trace(raw_flow, req_flow, res_flow)

    if req_flow.error:
        print(f"{RED}# Request Error:{RESET} {shorten(raw_flow.request.text, width=1000, placeholder='...')}")
        return

    if raw_flow.request:
        print_request(colorize, req_flow)

    if raw_flow.response:
        _print_response(raw_flow, res_flow)

    print(f"\n# Raw Traces")
    print(f"Written raw request to {raw_request_file}")
    print(f"Written raw response to {raw_response_file}")


def _print_response(raw_flow, res_flow: ResponseFlow):
    if res_flow.error:
        print(f"{RED}# Response Error:{RESET} {shorten(raw_flow.response.text, width=1000, placeholder='...')}")
    elif res_flow.message is not None:
        print(f"\n{GREEN}# Response{RESET}")
        print(f"model:: {res_flow.message.model}")
        for block in res_flow.message.content:
            _print_response_block(block)
    else:
        print(f"\n{RED}# Strange Response{RESET}")


def _print_response_block(block: Union[TextBlock, ToolUseBlock, ServerToolUseBlock, ServerToolResultBlock]):
    text_content = ''
    if block.type == 'text':
        text_content = block.text
    if block.type == 'tool_use':
        text_content = json.dumps(block.input, indent=2)
    header = block.type
    if block.type == 'tool_use' and hasattr(block, 'name'):
        header = f"{block.type} {block.name}"
    print(box_wrap(shorten(text_content, width=500, placeholder="..."), header=header))


def _write_trace(raw_flow, req_flow: RequestFlow, res_flow: ResponseFlow) -> tuple[Path, Path]:
    now = datetime.now().isoformat()
    raw_request_file = Path(__file__).parent.parent / 'trace' / f"{now}-req.json"
    raw_response_file = Path(__file__).parent.parent / 'trace' / f"{now}-res.json"
    if req_flow.pretty:
        with open(raw_request_file, "w") as f:
            f.write(req_flow.pretty)
    elif raw_flow.request:
        print("Pretty request is missing")
        with open(raw_response_file, "w") as f:
            f.write(raw_flow.request.text)

    if res_flow.pretty:
        with open(raw_response_file, "w") as f:
            f.write(res_flow.pretty)
    elif raw_flow.response:
        print("Pretty response is missing")
        with open(raw_response_file, "w") as f:
            f.write(raw_flow.response.text)
    return raw_request_file, raw_response_file
