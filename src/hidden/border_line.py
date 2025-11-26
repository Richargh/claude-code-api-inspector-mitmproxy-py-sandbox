def border_line(text: str) -> str:
    """Return text with border line, first line prefixed with >."""
    lines = text.splitlines()
    result = []
    for i, line in enumerate(lines):
        prefix = ">" if i == 0 else " "
        result.append(f"│{prefix}{line}")
    return "\n".join(result)

def border_line_tool_use(name: str, text: str, width: int = 50) -> str:
    """Return tool_use with header showing tool name."""
    header = f"──tool_use {name}─"
    header = header + "─" * (width - len(header))
    lines = [f"│{header}"]
    for line in text.splitlines():
        lines.append(f"│ {line}")
    return "\n".join(lines)

def border_line_tool_result(text: str, width: int = 50) -> str:
    """Return tool_result with footer line."""
    lines = []
    for line in text.splitlines():
        lines.append(f"│ {line}")
    footer = "──tool_result─"
    footer = footer + "─" * (width - len(footer))
    lines.append(f"│{footer}")
    return "\n".join(lines)
