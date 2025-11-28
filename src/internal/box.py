import re

from internal.colors import RESET

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')

def box_wrap(
    text: str,
    width: int = 100,
    header: str | None = None,
    footer: str | None = None,
    top: bool = True,
    bottom: bool = True
) -> str:
    """Return text inside an ASCII box.

    Args:
        text: The content to display
        width: Total width of the box
        header: Optional label for the top border (e.g., "text" or "tool_use Bash")
        footer: Optional label for the bottom border (e.g., "tool_result")
        top: Whether to show the top border
        bottom: Whether to show the bottom border
    """
    inner = width - 4
    lines = []

    # Top border
    if top:
        if header:
            label = f"─{header}─"
            remaining = width - 2 - len(label)
            lines.append("┌" + label + "─" * remaining + "┐")
        else:
            lines.append("┌" + "─" * (width - 2) + "┐")

    # Content
    for line in text.splitlines():
        # Wrap long lines while preserving ANSI codes
        while _visible_len(line) > inner:
            cut = 0
            visible = 0
            while visible < inner and cut < len(line):
                if line[cut:cut+2] == '\x1b[':
                    end = line.find('m', cut)
                    cut = end + 1 if end != -1 else cut + 1
                else:
                    visible += 1
                    cut += 1
            chunk = line[:cut]
            reset = RESET if '\x1b[' in chunk else ''
            lines.append("│ " + chunk + reset + " " * (inner - visible) + " │")
            line = line[cut:]
        pad = inner - _visible_len(line)
        lines.append("│ " + line + " " * pad + " │")

    # Bottom border
    if bottom:
        if footer:
            label = f"──{footer}─"
            remaining = width - 2 - len(label)
            lines.append("└" + label + "─" * remaining + "┘")
        else:
            lines.append("└" + "─" * (width - 2) + "┘")

    return "\n".join(lines)

def _visible_len(s: str) -> int:
    """Return the visible length of a string, ignoring ANSI escape codes."""
    return len(ANSI_ESCAPE.sub('', s))
