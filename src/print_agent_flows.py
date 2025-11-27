import json
import re
from textwrap import shorten
from pathlib import Path
from typing import Union

from hidden.colors import RED, GREEN, BLUE, GRAY, RESET, Colorize
from hidden.flows import parse_flow, RequestFlow, ResponseFlow, TextBlock, ToolUseBlock, ServerToolUseBlock, \
    ServerToolResultBlock
from hidden.diff import diff_system_prompts
from hidden.box import box_wrap
from datetime import datetime

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

module_dir = Path(__file__).parent
identity_prompt_path = module_dir / 'hidden' / 'system-prompt-identity.md'
identity_prompt = identity_prompt_path.read_text()
identity_prompt_start = identity_prompt.split('.')[0]
pre_prompt_path = module_dir / 'hidden' / 'system-prompt-pre.md'
pre_prompt = pre_prompt_path.read_text()
pre_prompt_start = pre_prompt.split('.')[0]
standard_prompt_path = module_dir / 'hidden' / 'system-prompt-standard.md'
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
        filepath = module_dir / 'hidden' / filename
        if filepath.exists():
            descriptions[tool_name] = filepath.read_text()
    return descriptions

known_tool_descriptions = _load_known_tool_descriptions()

def response(raw_flow, colorize: Colorize = Colorize.ALL) -> None:
    req_flow, res_flow = parse_flow(raw_flow)
    raw_request_file, raw_response_file = _write_trace(raw_flow, req_flow, res_flow)

    if req_flow.error:
        print(f"{RED}# Request Error:{RESET} {shorten(raw_flow.request.text, width=1000, placeholder='...')}")
        return

    if raw_flow.request:
        _print_request(colorize, req_flow)

    if raw_flow.response:
        _print_response(raw_flow, res_flow)

    print(f"\n# Raw Traces")
    print(f"Written raw request to {raw_request_file}")
    print(f"Written raw response to {raw_response_file}")


def _print_response(raw_flow, res_flow: ResponseFlow):
    if res_flow.error:
        print(f"{RED}# Response Error:{RESET} {shorten(raw_flow.response.text, width=1000, placeholder='...')}")
    elif res_flow.message is not None:
        # SSE response
        print(f"\n{GREEN}# Response{RESET}")
        print(f"model:: {res_flow.message.model}")
        # Extract text from content blocks
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


def _print_request(colorize: Colorize, req_flow: RequestFlow):
    print(f"\n{BLUE}# Request:{RESET}")
    print(f"model:: {req_flow.model}")

    if req_flow.system_prompts:
        print("## System")
        for sys_prompt in req_flow.system_prompts:
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
