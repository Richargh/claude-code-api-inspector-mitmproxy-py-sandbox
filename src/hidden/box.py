import re
from hidden.colors import RESET

ANSI_ESCAPE = re.compile(r'\x1b\[[0-9;]*m')

def print_box(text: str, width: int = 100) -> None:
    """Print text inside an ASCII box."""
    inner = width - 4
    print("┌" + "─" * (width - 2) + "┐")
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
            print("│ " + chunk + reset + " " * (inner - visible) + " │")
            line = line[cut:]
        pad = inner - _visible_len(line)
        print("│ " + line + " " * pad + " │")
    print("└" + "─" * (width - 2) + "┘")

def _visible_len(s: str) -> int:
    """Return the visible length of a string, ignoring ANSI escape codes."""
    return len(ANSI_ESCAPE.sub('', s))
