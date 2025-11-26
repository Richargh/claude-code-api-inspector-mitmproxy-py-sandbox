import json
from textwrap import shorten
from pathlib import Path
from hidden.colors import RED, GREEN, BLUE, GRAY, RESET, Colorize
from hidden.flows import parse_flow
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

def response(raw_flow, colorize: Colorize = Colorize.ALL) -> None:
    flow = parse_flow(raw_flow)
    raw_request_file = Path(__file__).parent.parent / 'trace' / f"{datetime.now().isoformat()}-req.json"
    raw_response_file = Path(__file__).parent.parent / 'trace' / f"{datetime.now().isoformat()}-res.json"
    with open(raw_request_file, "w") as f:
        f.write(flow.raw_request)
    with open(raw_response_file, "w") as f:
        f.write(flow.raw_response)

    if flow.request_error:
        print(f"{RED}# Request Error:{RESET} {raw_flow.request.text[:1000]}")
        return

    if flow.model:
        print(f"\n{BLUE}# Request:{RESET}")
        print(f"model:: {flow.model}")

        if flow.system_prompts:
            print("## System")
            for sys_prompt in flow.system_prompts:
                text_start = sys_prompt.text.split('.')[0]
                if text_start in known_system_prompts:
                    known_system_prompt = known_system_prompts[text_start]
                    diff = diff_system_prompts(known_system_prompt, sys_prompt.text, colorize)
                    if diff == '':
                        print(box_wrap(f"{text_start}[...]", header="Known System Prompt"))
                    else:
                        print(box_wrap(f"{text_start}[...]\n\n{diff}", header="Changed System Prompt"))
                else:
                    print(box_wrap(f"{sys_prompt.text[:100]}[...]", header="Unknown System Prompt"))

        # Tools (unknown first in green, known in gray)
        if flow.tools:
            unknown_tools = [t for t in flow.tools if t not in KNOWN_TOOLS]
            known_tools = [t for t in flow.tools if t in KNOWN_TOOLS]
            tools_display = []
            for t in unknown_tools:
                tools_display.append(f"{BLUE}{t}{RESET}")
            for t in known_tools:
                tools_display.append(f"{GRAY}{t}{RESET}")
            print(f"## Tools")
            print(f"{', '.join(tools_display)}")

        if flow.messages:
            print("## Messages")
            # Find the last user text content that isn't a system-reminder
            last_user_prompt_index = None
            for index, message in enumerate(flow.messages):
                if message.role == 'user':
                    for content in message.content:
                        if content.type == 'text' and not content.text.startswith("<system"):
                            last_user_prompt_index = index

            max_message_index = len(flow.messages)
            min_message_index = max(max_message_index - 10, 0)
            if last_user_prompt_index is None:
                print("! Original user prompt lost in the ether")
            else:
                min_message_index = last_user_prompt_index
            messages_to_show = flow.messages[min_message_index:max_message_index]
            trimmed_message_count = len(messages_to_show)
            if trimmed_message_count > 0:
                print(f"...{trimmed_message_count} more message in context, but trimmed for brevity...")

            for index, message in enumerate(messages_to_show):
                actual_index = min_message_index + index
                is_highlight = last_user_prompt_index == actual_index
                color_start = "" if is_highlight else GRAY
                color_end = "" if is_highlight else RESET
                print(f"{color_start}Msg {actual_index} by {message.role}:{color_end}")
                for content_idx, content in enumerate(message.content):

                    if content.type == 'tool_use':
                        print(f"{color_start}{box_wrap('', header = f'{content.type} {content.tool_name} ', bottom=False)}{color_end}")
                    elif content.type == 'tool_result':
                        text_preview = (content.text or '')[:200]
                        print(f"{color_start}{box_wrap(text_preview, footer=content.type, top=False)}{color_end}")
                    else:
                        text_preview = (content.text or '')[:200]
                        print(f"{color_start}{box_wrap(text_preview, header=content.type)}{color_end}")

    if raw_flow.response:
        if flow.response_error:
            print(f"{RED}# Response Error:{RESET} {raw_flow.response.text[:1000]}")
        elif flow.response_message is not None:
            # SSE response
            print(f"\n{GREEN}# Response{RESET}")
            print(f"model:: {flow.response_message.model}")
            # Extract text from content blocks
            for block in flow.response_message.content:
                text_content = ''
                if block.type == 'text':
                    text_content = block.text
                if block.type == 'tool_use':
                    text_content = json.dumps(block.input, indent=2)
                print(box_wrap(shorten(text_content, width=500, placeholder="..."), header=block.type))
        else:
            print(f"\n{RED}# Strange Response:{RESET}")
            print(f"model:: {flow.model}")

    print(f"Written raw request to {raw_request_file}")
    print(f"Written raw response to {raw_response_file}")
