import difflib

from internal.colors import RED, GREEN, RESET, Colorize
from internal.flow_config import FlowConfig


def diff_system_prompts(prompt1: str, prompt2: str, config: FlowConfig) -> str:
    """Compare two system prompts and return a unified diff of the differences."""
    lines1 = prompt1.splitlines(keepends=True)
    lines2 = prompt2.splitlines(keepends=True)

    diff = difflib.unified_diff(lines1, lines2, fromfile='previous', tofile='current', lineterm='')

    if config.colorize == Colorize.NONE:
        return ''.join(diff)

    colored_lines = []
    for line in diff:
        if line.startswith('+') and not line.startswith('+++'):
            colored_lines.append(f"{GREEN}{line}{RESET}")
        elif line.startswith('-') and not line.startswith('---'):
            colored_lines.append(f"{RED}{line}{RESET}")
        else:
            colored_lines.append(line)

    return ''.join(colored_lines)
