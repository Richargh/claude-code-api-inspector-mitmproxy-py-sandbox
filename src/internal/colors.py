from enum import Enum

# ANSI color codes
RED = "\033[91m"
GREEN = "\033[92m"
BLUE = "\033[94m"
GRAY = "\033[90m"
RESET = "\033[0m"

class Colorize(Enum):
    ALL = "all"
    NONE = "none"
