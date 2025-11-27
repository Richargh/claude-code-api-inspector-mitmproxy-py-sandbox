from textwrap import shorten
import re
from pathlib import Path
from typing import Optional

from internal.box import box_wrap
from internal.colors import Colorize, BLUE, RESET, GRAY
from internal.diff import diff_system_prompts
from internal.flows import RequestFlow, Message


def print_request(colorize: Colorize, req_flow: RequestFlow):
    print(f"\n{BLUE}# Request:{RESET}")
    print(f"model:: {req_flow.model}")

    if req_flow.system_prompts:
        print("## System")
        for sys_prompt in req_flow.system_prompts:
            _print_system_prompt(colorize, sys_prompt)

    # Tools (unknown first in green, known in gray)
    if req_flow.tools:
        print(f"## Tools")
        _print_tool_knowledge(req_flow)

        # Show diffs for changed tool descriptions
        for tool_name in req_flow.tools:
            _print_tool_description_diff(colorize, tool_name, req_flow.tool_descriptions.get(tool_name))

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


def _print_message(message: Message, actual_index: int, should_highlight: bool):
    color_start = "" if should_highlight else GRAY
    color_end = "" if should_highlight else RESET
    print(f"{color_start}Msg {actual_index} by {message.role}:{color_end}")
    for content_idx, content in enumerate(message.content):

        if content.type == 'tool_use':
            print(
                f"{color_start}{box_wrap('', header=f'{content.type} {content.tool_name} ', bottom=False)}{color_end}")
        elif content.type == 'tool_result':
            text_preview = shorten(content.text or '', width=200, placeholder='...')
            print(f"{color_start}{box_wrap(text_preview, footer=content.type, top=False)}{color_end}")
        else:
            text_preview = shorten(content.text or '', width=200, placeholder='...')
            print(f"{color_start}{box_wrap(text_preview, header=content.type)}{color_end}")


def _filter_relevant_messages(all_messages: list[Message]) -> tuple[list[Message], Optional[int]]:
    most_recent_user_prompt_index = None
    for index, message in enumerate(all_messages):
        if message.role == 'user':
            for content in message.content:
                if content.type == 'text' and not content.text.startswith("<system"):
                    most_recent_user_prompt_index = index

    max_message_index = len(all_messages)
    min_message_index = max(max_message_index - 10, 0)
    if most_recent_user_prompt_index is None:
        print("! Original user prompt lost in the ether")
    else:
        min_message_index = max(most_recent_user_prompt_index - 1, 0)
    messages_to_show = all_messages[min_message_index:max_message_index]
    return messages_to_show, most_recent_user_prompt_index


def _print_tool_description_diff(colorize: bool, tool_name: str, tool_description: Optional[str]):
    if tool_name in known_tool_descriptions and tool_description is not None:
        known_desc = known_tool_descriptions[tool_name]
        if known_desc != tool_description:
            diff = diff_system_prompts(known_desc, tool_description, colorize)
            if diff:
                print(box_wrap(diff, header=f"Changed Tool Description: {tool_name}"))


def _print_system_prompt(colorize, sys_prompt):
    text_start = sys_prompt.text.split('.')[0]
    if text_start in known_system_prompts:
        known_system_prompt = known_system_prompts[text_start]
        diff = diff_system_prompts(known_system_prompt, sys_prompt.text, colorize)
        if diff == '':
            print(box_wrap(f"{text_start}[...]", header="Known System Prompt"))
        else:
            print(box_wrap(f"{text_start}[...]\n\n{diff}", header="Changed System Prompt"))
    else:
        print(box_wrap(sys_prompt.text, header="Unknown System Prompt"))


def _print_tool_knowledge(req_flow):
    unknown_tools = [t for t in req_flow.tools if t not in KNOWN_TOOLS]
    known_tools = [t for t in req_flow.tools if t in KNOWN_TOOLS]
    tools_display = []
    for t in unknown_tools:
        tools_display.append(f"{BLUE}{t}{RESET}")
    for t in known_tools:
        tools_display.append(f"{GRAY}{t}{RESET}")
    print(f"{', '.join(tools_display)}")


def _load_known_tools() -> set[str]:
    return {
        "Bash",
        "BashOutput",
        "Glob",
        "Grep",
        "Read",
        "Edit",
        "Write",
        "Task",
        "TodoWrite",
        "WebFetch",
        "WebSearch",
        "NotebookEdit",
        "EnterPlanMode",
        "ExitPlanMode",
        "KillShell",
        "AskUserQuestion",
        "Skill",
        "SlashCommand"
    }


KNOWN_TOOLS = _load_known_tools()

def _load_known_system_prompts() -> dict[str, str]:
    internal_dir = Path(__file__).parent
    identity_prompt_path = internal_dir / 'system-prompt-identity.md'
    identity_prompt = identity_prompt_path.read_text()
    identity_prompt_start = identity_prompt.split('.')[0]
    pre_prompt_path = internal_dir / 'system-prompt-pre.md'
    pre_prompt = pre_prompt_path.read_text()
    pre_prompt_start = pre_prompt.split('.')[0]
    standard_prompt_path = internal_dir / 'system-prompt-standard.md'
    standard_prompt = standard_prompt_path.read_text()
    standard_prompt_start = standard_prompt.split('.')[0]
    return {
        identity_prompt_start: identity_prompt,
        pre_prompt_start: pre_prompt,
        standard_prompt_start: standard_prompt
    }

known_system_prompts = _load_known_system_prompts()

def _tool_name_to_filename(tool_name: str) -> str:
    """Convert PascalCase tool name to kebab-case filename."""
    # Insert hyphen before uppercase letters and lowercase them
    kebab = re.sub(r'(?<!^)(?=[A-Z])', '-', tool_name).lower()
    return f"tool-{kebab}-description.md"

def _load_known_tool_descriptions() -> dict[str, str]:
    internal_dir = Path(__file__).parent
    descriptions = {}
    for tool_name in KNOWN_TOOLS:
        filename = _tool_name_to_filename(tool_name)
        filepath = internal_dir / filename
        if filepath.exists():
            descriptions[tool_name] = filepath.read_text()
    return descriptions

known_tool_descriptions = _load_known_tool_descriptions()