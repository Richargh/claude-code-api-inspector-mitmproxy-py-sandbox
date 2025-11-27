from textwrap import shorten
import re
from pathlib import Path

from internal.box import box_wrap
from internal.colors import Colorize, BLUE, RESET, GRAY
from internal.diff import diff_system_prompts
from internal.flows import RequestFlow


def print_request(colorize: Colorize, req_flow: RequestFlow):
    print(f"\n{BLUE}# Request:{RESET}")
    print(f"model:: {req_flow.model}")

    if req_flow.system_prompts:
        print("## System")
        for sys_prompt in req_flow.system_prompts:
            _print_system_prompt(colorize, sys_prompt)

    # Tools (unknown first in green, known in gray)
    if req_flow.tools:
        unknown_tools = [t for t in req_flow.tools if t not in KNOWN_TOOLS]
        known_tools = [t for t in req_flow.tools if t in KNOWN_TOOLS]
        tools_display = []
        for t in unknown_tools:
            tools_display.append(f"{BLUE}{t}{RESET}")
        for t in known_tools:
            tools_display.append(f"{GRAY}{t}{RESET}")
        print(f"## Tools")
        print(f"{', '.join(tools_display)}")

        # Show diffs for changed tool descriptions
        for tool_name in req_flow.tools:
            if tool_name in known_tool_descriptions and tool_name in req_flow.tool_descriptions:
                known_desc = known_tool_descriptions[tool_name]
                actual_desc = req_flow.tool_descriptions[tool_name]
                if known_desc != actual_desc:
                    diff = diff_system_prompts(known_desc, actual_desc, colorize)
                    if diff:
                        print(box_wrap(diff, header=f"Changed Tool Description: {tool_name}"))

    if req_flow.messages:
        print("## Messages")
        # Find the last user text content that isn't a system-reminder
        last_user_prompt_index = None
        for index, message in enumerate(req_flow.messages):
            if message.role == 'user':
                for content in message.content:
                    if content.type == 'text' and not content.text.startswith("<system"):
                        last_user_prompt_index = index

        max_message_index = len(req_flow.messages)
        min_message_index = max(max_message_index - 10, 0)
        if last_user_prompt_index is None:
            print("! Original user prompt lost in the ether")
        else:
            min_message_index = max(last_user_prompt_index - 1, 0)
        messages_to_show = req_flow.messages[min_message_index:max_message_index]
        if min_message_index > 0:
            print(f"...{min_message_index} more message in context, but trimmed to focus on current prompt...")

        for index, message in enumerate(messages_to_show):
            actual_index = min_message_index + index
            is_highlight = last_user_prompt_index == actual_index
            color_start = "" if is_highlight else GRAY
            color_end = "" if is_highlight else RESET
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


# Known tools that should be shown in gray
KNOWN_TOOLS = {
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
known_system_prompts = {
    identity_prompt_start: identity_prompt,
    pre_prompt_start: pre_prompt,
    standard_prompt_start: standard_prompt
}

def _tool_name_to_filename(tool_name: str) -> str:
    """Convert PascalCase tool name to kebab-case filename."""
    # Insert hyphen before uppercase letters and lowercase them
    kebab = re.sub(r'(?<!^)(?=[A-Z])', '-', tool_name).lower()
    return f"tool-{kebab}-description.md"

def _load_known_tool_descriptions() -> dict[str, str]:
    """Load known tool descriptions from files."""
    descriptions = {}
    for tool_name in KNOWN_TOOLS:
        filename = _tool_name_to_filename(tool_name)
        filepath = internal_dir / filename
        if filepath.exists():
            descriptions[tool_name] = filepath.read_text()
    return descriptions

known_tool_descriptions = _load_known_tool_descriptions()