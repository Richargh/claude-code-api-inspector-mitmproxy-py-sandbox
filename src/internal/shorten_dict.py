"""Utility functions for formatting output."""

import json


def shorten_dict(input_dict: dict | None, max_line_length: int = 50) -> str:
    """Format tool input dict with each key on a new line, values shortened in middle.

    Args:
        input_dict: The tool input dictionary to format
        max_line_length: Maximum length for each line before shortening

    Returns:
        Formatted string with one key-value pair per line
    """
    if not input_dict:
        return ''

    lines = []
    for key, value in input_dict.items():
        # Convert value to JSON string (handles nested objects, arrays, etc.)
        if isinstance(value, str):
            value_str = f'"{value}"'
        else:
            value_str = json.dumps(value)

        line = f'"{key}": {value_str}'
        lines.append(_shorten_middle(line, max_line_length))

    return '\n'.join(lines)


def _shorten_middle(text: str, max_length: int = 200) -> str:
    """Shorten text by cutting in the middle with ellipsis.

    If text is longer than max_length, keeps the start and end,
    replacing the middle with '...'.
    """
    if len(text) <= max_length:
        return text
    # Account for the 3 chars of '...'
    available = max_length - 3
    start_len = available // 2
    end_len = available - start_len
    return text[:start_len] + '...' + text[-end_len:]
