from textwrap import shorten

from mitmproxy import http

from internal.box import box_wrap
from internal.colors import BLUE, GRAY, RED, RESET
from internal.diff import diff_system_prompts
from internal.flow_config import FlowConfig
from internal.known_prompts import (
    all_known_tools,
    load_known_summary_prompt,
    load_known_system_prompts,
    load_known_tool_descriptions,
    summary_result_start,
)
from internal.parse_flows import (
    RequestFlow,
    RequestMessage,
    ServerToolResultBlock,
    ServerToolUseBlock,
    SystemPrompt,
    TextBlock,
    ToolResultBlock,
    ToolUseBlock,
)
from internal.shorten_dict import shorten_dict

KNOWN_TOOLS = all_known_tools
known_system_prompts = load_known_system_prompts()
known_tool_descriptions = load_known_tool_descriptions()
summary_prompt_start, known_summary_prompt = load_known_summary_prompt()
# Extract first sentence from summary_result_start for matching
summary_result_first_sentence = summary_result_start.split('.')[0]


def format_request(raw_flow: http.HTTPFlow, req_flow: RequestFlow, config: FlowConfig) -> str:
    lines: list[str] = []
    lines.append(f"\n{BLUE}# Request:{RESET}")
    lines.append(f"model:: {req_flow.model}")

    if req_flow.error:
        request_text = raw_flow.request.text if raw_flow.request and raw_flow.request.text else ""
        lines.append(f"{RED}# Request Error:{RESET} {shorten(request_text, width=1000, placeholder='...')}")
        return '\n'.join(lines)

    if req_flow.system_prompts:
        lines.append("## System")
        for sys_prompt in req_flow.system_prompts:
            lines.append(_format_system_prompt(config, sys_prompt))

    # Tools (unknown first in green, known in gray)
    if req_flow.tools:
        lines.append("## Tools")
        lines.append(_format_tool_knowledge(req_flow))

        # Show diffs for changed tool descriptions
        for tool_name in req_flow.tools:
            diff = _format_tool_description_diff(tool_name, req_flow.tool_descriptions.get(tool_name), config)
            if diff:
                lines.append(diff)

    if req_flow.messages:
        lines.append("## Messages")
        # Find the last user text content that isn't a system-reminder
        messages_to_show, most_recent_user_prompt_index, warning = _filter_relevant_messages(req_flow.messages)
        start_message_index = len(req_flow.messages) - len(messages_to_show)
        if warning:
            lines.append(warning)
        if start_message_index > 0:
            lines.append(f"...{start_message_index} more message in context, but trimmed to focus on current prompt...")

        for index, message in enumerate(messages_to_show):
            actual_index = start_message_index + index
            should_highlight = most_recent_user_prompt_index == actual_index
            lines.append(_format_message(message, actual_index, should_highlight, config))

    return '\n'.join(lines)


def _format_message(message: RequestMessage, actual_index: int, should_highlight: bool, config: FlowConfig) -> str:
    lines: list[str] = []
    color_start = "" if should_highlight else GRAY
    color_end = "" if should_highlight else RESET
    lines.append(f"{color_start}Msg {actual_index} by {message.role}:{color_end}")
    for content in message.content:
        if isinstance(content, (ToolUseBlock, ServerToolUseBlock)):
            input_formatted = shorten_dict(content.input)
            header = f'{content.type} {content.tool_name} '
            lines.append(f"{color_start}{box_wrap(input_formatted, header=header, bottom=False)}{color_end}")
        elif isinstance(content, ToolResultBlock):
            text_preview = shorten(str(content.content) if content.content else '', width=200, placeholder='...')
            lines.append(f"{color_start}{box_wrap(text_preview, footer=content.type, top=False)}{color_end}")
        elif isinstance(content, ServerToolResultBlock):
            text_preview = shorten(str(content.content) if content.content else '', width=200, placeholder='...')
            lines.append(f"{color_start}{box_wrap(text_preview, footer=content.type, top=False)}{color_end}")
        elif isinstance(content, TextBlock):
            text_start = (content.text or '').split('.')[0]
            if text_start == summary_result_first_sentence:
                lines.append(_format_summary_result(content.text))
            elif text_start == summary_prompt_start:
                lines.append(_format_summary_prompt(content.text, config))
            else:
                text_preview = shorten(content.text or '', width=200, placeholder='...')
                lines.append(f"{color_start}{box_wrap(text_preview, header=content.type)}{color_end}")
        else:
            # Fallback for any other content type
            text_preview = shorten(getattr(content, 'text', '') or '', width=200, placeholder='...')
            boxed_preview = box_wrap(text_preview, header=getattr(content, 'type', 'unknown'))
            lines.append(f"{color_start}{boxed_preview}{color_end}")
    return '\n'.join(lines)


def _filter_relevant_messages(all_messages: list[RequestMessage]) -> tuple[
    list[RequestMessage], int | None, str | None
]:
    most_recent_user_prompt_index = None
    warning: str | None = None
    for index, message in enumerate(all_messages):
        if message.role == 'user':
            for content in message.content:
                if isinstance(content, TextBlock) and content.text and not content.text.startswith("<system"):
                    most_recent_user_prompt_index = index

    max_message_index = len(all_messages)
    min_message_index = max(max_message_index - 10, 0)
    if most_recent_user_prompt_index is None:
        warning = "! Original user prompt lost in the ether"
    else:
        min_message_index = max(most_recent_user_prompt_index - 1, 0)
    messages_to_show = all_messages[min_message_index:max_message_index]
    return messages_to_show, most_recent_user_prompt_index, warning


def _format_tool_description_diff(tool_name: str, tool_description: str | None, config: FlowConfig) -> str | None:
    if tool_name in known_tool_descriptions and tool_description is not None:
        known_desc = known_tool_descriptions[tool_name]
        if known_desc != tool_description:
            diff = diff_system_prompts(known_desc, tool_description, config)
            if diff:
                return box_wrap(diff, header=f"Changed Tool Description: {tool_name}")
    return None


def _format_system_prompt(config: FlowConfig, sys_prompt: SystemPrompt) -> str:
    text_start = sys_prompt.text.split('.')[0]
    if text_start in known_system_prompts:
        known_system_prompt = known_system_prompts[text_start]
        diff = diff_system_prompts(known_system_prompt, sys_prompt.text, config)
        if diff == '':
            return box_wrap(f"{text_start}[...]", header="Known System Prompt")
        else:
            return box_wrap(f"{text_start}[...]\n\n{diff}", header="Changed System Prompt")
    else:
        return box_wrap(sys_prompt.text, header="Unknown System Prompt")


def _format_summary_prompt(text: str, config: FlowConfig) -> str:
    """Format a known summary prompt with diff if changed."""
    text_start = text.split('.')[0]
    diff = diff_system_prompts(known_summary_prompt, text, config)
    if diff == '':
        return box_wrap(f"{text_start}[...]", header=f"{BLUE}summary prompt{RESET}")
    else:
        return box_wrap(f"{text_start}[...]\n\n{diff}", header="summary prompt (changed)")


def _format_summary_result(text: str) -> str:
    """Format an auto-generated conversation summary (truncated)."""
    text_preview = shorten(text, width=200, placeholder='...')
    return box_wrap(text_preview, header=f"{BLUE}conversation summary{RESET}")


def _format_tool_knowledge(req_flow: RequestFlow) -> str:
    unknown_tools = [t for t in req_flow.tools if t not in KNOWN_TOOLS]
    known_tools = [t for t in req_flow.tools if t in KNOWN_TOOLS]
    tools_display = []
    for t in unknown_tools:
        tools_display.append(f"{BLUE}{t}{RESET}")
    for t in known_tools:
        tools_display.append(f"{GRAY}{t}{RESET}")
    return f"{', '.join(tools_display)}"
