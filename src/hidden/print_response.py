import json
from textwrap import shorten
from typing import Union

from hidden.box import box_wrap
from hidden.colors import RED, RESET, GREEN
from hidden.flows import ResponseFlow, TextBlock, ToolUseBlock, ServerToolUseBlock, ServerToolResultBlock


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
