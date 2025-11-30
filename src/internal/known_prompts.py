import re
from pathlib import Path

all_known_tools = {
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

summary_result_start = ("This session is being continued from a previous conversation that ran out of context."
                        " The conversation is summarized below:")


def load_known_system_prompts() -> dict[str, str]:
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


def load_known_summary_prompt() -> tuple[str, str]:
    """Load the summary prompt and return (first_sentence, full_text)."""
    internal_dir = Path(__file__).parent
    summary_prompt_path = internal_dir / 'summary-prompt.md'
    summary_prompt = summary_prompt_path.read_text()
    summary_prompt_start = summary_prompt.split('.')[0]
    return summary_prompt_start, summary_prompt


def load_known_tool_descriptions() -> dict[str, str]:
    internal_dir = Path(__file__).parent
    descriptions = {}
    for tool_name in all_known_tools:
        filename = _tool_name_to_filename(tool_name)
        filepath = internal_dir / filename
        if filepath.exists():
            descriptions[tool_name] = filepath.read_text()
    return descriptions


def _tool_name_to_filename(tool_name: str) -> str:
    """Convert PascalCase tool name to kebab-case filename."""
    # Insert hyphen before uppercase letters and lowercase them
    kebab = re.sub(r'(?<!^)(?=[A-Z])', '-', tool_name).lower()
    return f"tool-{kebab}-description.md"
