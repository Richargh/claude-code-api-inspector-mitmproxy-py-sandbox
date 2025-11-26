def _wrap_line(line: str, width: int) -> list[str]:
    """Wrap a line to fit within width."""
    inner = width - 2  # account for "│ " prefix
    if len(line) <= inner:
        return [line]
    result = []
    while len(line) > inner:
        result.append(line[:inner])
        line = line[inner:]
    if line:
        result.append(line)
    return result

def border_line(text: str, width: int = 100) -> str:
    """Return text with border line, first line prefixed with >."""
    result = []
    first = True
    for line in text.splitlines():
        wrapped = _wrap_line(line, width)
        for w in wrapped:
            prefix = ">" if first else " "
            first = False
            result.append(f"│{prefix}{w}")
    return "\n".join(result)

def border_line_tool_use(name: str, text: str, width: int = 100) -> str:
    """Return tool_use with header showing tool name."""
    header = f"──tool_use {name}─"
    header = header + "─" * (width - 1 - len(header))
    lines = [f"│{header}"]
    for line in text.splitlines():
        for w in _wrap_line(line, width):
            lines.append(f"│ {w}")
    return "\n".join(lines)

def border_line_tool_result(text: str, width: int = 100) -> str:
    """Return tool_result with footer line."""
    lines = []
    for line in text.splitlines():
        for w in _wrap_line(line, width):
            lines.append(f"│ {w}")
    footer = "──tool_result─"
    footer = footer + "─" * (width - 1 - len(footer))
    lines.append(f"│{footer}")
    return "\n".join(lines)
