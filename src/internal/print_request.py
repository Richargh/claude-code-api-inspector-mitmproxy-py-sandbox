import json
from textwrap import shorten

from internal.box import box_wrap
from internal.colors import BLUE, GRAY, RESET
from internal.diff import diff_system_prompts
from internal.flow_config import FlowConfig
from internal.flows import (
    RequestFlow,
    RequestMessage,
    ServerToolResultBlock,
    ServerToolUseBlock,
    SystemPrompt,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from internal.known_prompts import known_tools, load_known_system_prompts, load_known_tool_descriptions

KNOWN_TOOLS = known_tools
known_system_prompts = load_known_system_prompts()
known_tool_descriptions = load_known_tool_descriptions()

def print_request(req_flow: RequestFlow, config: FlowConfig) -> None:
    print(f"\n{BLUE}# Request:{RESET}")
    print(f"model:: {req_flow.model}")

    if req_flow.system_prompts:
        print("## System")
        for sys_prompt in req_flow.system_prompts:
            _print_system_prompt(config, sys_prompt)

    # Tools (unknown first in green, known in gray)
    if req_flow.tools:
        print("## Tools")
        _print_tool_knowledge(req_flow)

        # Show diffs for changed tool descriptions
        for tool_name in req_flow.tools:
            _print_tool_description_diff(tool_name, req_flow.tool_descriptions.get(tool_name), config)

    if req_flow.messages:
        print("## Messages")
        # Find the last user text content that isn't a system-reminder
        messages_to_show, most_recent_user_prompt_index = _filter_relevant_messages(req_flow.messages)
        start_message_index = len(req_flow.messages) - len(messages_to_show)
        if start_message_index > 0:
            print(f"...{start_message_index} more message in context, but trimmed to focus on current prompt...")

        for index, message in enumerate(messages_to_show):
            actual_index = start_message_index + index
            should_highlight = most_recent_user_prompt_index == actual_index
            _print_message(message, actual_index, should_highlight)


def _print_message(message: RequestMessage, actual_index: int, should_highlight: bool) -> None:
    color_start = "" if should_highlight else GRAY
    color_end = "" if should_highlight else RESET
    print(f"{color_start}Msg {actual_index} by {message.role}:{color_end}")
    for content in message.content:
        if isinstance(content, (ToolUseBlock, ServerToolUseBlock)):
            input_preview = shorten(json.dumps(content.input) if content.input else '', width=200, placeholder='...')
            header = f'{content.type} {content.tool_name} '
            print(f"{color_start}{box_wrap(input_preview, header=header, bottom=False)}{color_end}")
        elif isinstance(content, ToolResultBlock):
            text_preview = shorten(str(content.content) if content.content else '', width=200, placeholder='...')
            print(f"{color_start}{box_wrap(text_preview, footer=content.type, top=False)}{color_end}")
        elif isinstance(content, ServerToolResultBlock):
            text_preview = shorten(str(content.content) if content.content else '', width=200, placeholder='...')
            print(f"{color_start}{box_wrap(text_preview, footer=content.type, top=False)}{color_end}")
        elif isinstance(content, TextBlock):
            text_preview = shorten(content.text or '', width=200, placeholder='...')
            print(f"{color_start}{box_wrap(text_preview, header=content.type)}{color_end}")
        else:
            # Fallback for any other content type
            text_preview = shorten(getattr(content, 'text', '') or '', width=200, placeholder='...')
            print(f"{color_start}{box_wrap(text_preview, header=getattr(content, 'type', 'unknown'))}{color_end}")


def _filter_relevant_messages(all_messages: list[RequestMessage]) -> tuple[list[RequestMessage], int | None]:
    most_recent_user_prompt_index = None
    for index, message in enumerate(all_messages):
        if message.role == 'user':
            for content in message.content:
                if isinstance(content, TextBlock) and content.text and not content.text.startswith("<system"):
                    most_recent_user_prompt_index = index

    max_message_index = len(all_messages)
    min_message_index = max(max_message_index - 10, 0)
    if most_recent_user_prompt_index is None:
        print("! Original user prompt lost in the ether")
    else:
        min_message_index = max(most_recent_user_prompt_index - 1, 0)
    messages_to_show = all_messages[min_message_index:max_message_index]
    return messages_to_show, most_recent_user_prompt_index


def _print_tool_description_diff(tool_name: str, tool_description: str | None, config: FlowConfig) -> None:
    if tool_name in known_tool_descriptions and tool_description is not None:
        known_desc = known_tool_descriptions[tool_name]
        if known_desc != tool_description:
            diff = diff_system_prompts(known_desc, tool_description, config)
            if diff:
                print(box_wrap(diff, header=f"Changed Tool Description: {tool_name}"))


def _print_system_prompt(config: FlowConfig, sys_prompt: SystemPrompt) -> None:
    text_start = sys_prompt.text.split('.')[0]
    if text_start in known_system_prompts:
        known_system_prompt = known_system_prompts[text_start]
        diff = diff_system_prompts(known_system_prompt, sys_prompt.text, config)
        if diff == '':
            print(box_wrap(f"{text_start}[...]", header="Known System Prompt"))
        else:
            print(box_wrap(f"{text_start}[...]\n\n{diff}", header="Changed System Prompt"))
    else:
        print(box_wrap(sys_prompt.text, header="Unknown System Prompt"))


def _print_tool_knowledge(req_flow: RequestFlow) -> None:
    unknown_tools = [t for t in req_flow.tools if t not in KNOWN_TOOLS]
    known_tools = [t for t in req_flow.tools if t in KNOWN_TOOLS]
    tools_display = []
    for t in unknown_tools:
        tools_display.append(f"{BLUE}{t}{RESET}")
    for t in known_tools:
        tools_display.append(f"{GRAY}{t}{RESET}")
    print(f"{', '.join(tools_display)}")
