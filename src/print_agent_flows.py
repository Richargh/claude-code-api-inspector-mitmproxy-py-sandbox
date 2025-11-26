from hidden.flows import parse_flow

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
GRAY = "\033[90m"
RESET = "\033[0m"

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


def response(raw_flow) -> None:
    flow = parse_flow(raw_flow)

    if flow.request_error:
        print(f"{RED}# Request Error:{RESET} {raw_flow.request.text[:1000]}")
        return

    if flow.model:
        print(f"\n{BLUE}# Request:{RESET}")
        print(f"model:: {flow.model}")

        # Messages (last 10)
        if flow.messages:
            print("## Messages")
            messages_to_show = flow.messages[-10:]
            for msg in messages_to_show:
                print(f"@{msg.role}:")
                for content in msg.content:
                    if content.type == 'text':
                        text_preview = (content.text or '')[:100]
                        print(f"  > {text_preview}")
                    elif content.type == 'tool_use':
                        print(f"  > [tool_use: {content.tool_name}]")
                    elif content.type == 'tool_result':
                        text_preview = (content.text or '')[:100]
                        print(f"  > [tool_result: {text_preview}]")
        print("---")

        # System prompts
        if flow.system_prompts:
            print("## System")
            for sys_prompt in flow.system_prompts:
                text_preview = sys_prompt.text[:100]
                print(f"> {text_preview}")

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

    if raw_flow.response:
        if flow.response_error:
            print(f"{RED}# Response Error:{RESET} {raw_flow.response.text[:1000]}")
        elif flow.response_text is not None:
            # SSE response
            print(f"\n{GREEN}# Response{RESET}")
            print(f"model:: {flow.response_model}")
            print(f"> {flow.response_text[:500]}")
        else:
            print(f"\n{GREEN}# Strange Response:{RESET}")
            print(f"model:: {flow.model}")

        print('=' * 60)
