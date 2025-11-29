from textwrap import shorten

from mitmproxy import http

from internal.box import box_wrap
from internal.colors import GREEN, RED, RESET
from internal.flows import ResponseFlow, ServerToolResultBlock, ServerToolUseBlock, TextBlock, ToolUseBlock
from internal.shorten_dict import shorten_dict


def print_response(raw_flow: http.HTTPFlow, res_flow: ResponseFlow) -> None:
    if res_flow.error:
        response_text = raw_flow.response.text if raw_flow.response and raw_flow.response.text else ""
        print(f"{RED}# Response Error:{RESET} {shorten(response_text, width=1000, placeholder='...')}")
    elif res_flow.message is not None:
        print(f"\n{GREEN}# Response{RESET}")
        print(f"model:: {res_flow.message.model}")
        for block in res_flow.message.content:
            _print_response_block(block)
    else:
        print(f"\n{RED}# Strange Response{RESET}")


def _print_response_block(block: TextBlock | ToolUseBlock | ServerToolUseBlock | ServerToolResultBlock) -> None:
    text_content = ''
    if isinstance(block, TextBlock):
        text_content = shorten(block.text, width=500, placeholder="...")
    elif isinstance(block, (ToolUseBlock, ServerToolUseBlock)):
        text_content = shorten_dict(block.input)
    header = block.type
    if isinstance(block, (ToolUseBlock, ServerToolUseBlock)) and block.tool_name:
        header = f"{block.type} {block.tool_name}"
    print(box_wrap(text_content, header=header))
