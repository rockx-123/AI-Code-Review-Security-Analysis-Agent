"""
Shared scanning utilities for Java heuristic analysis (both code-quality and security agents).

Java has no parser available in this environment (no javac guarantee — see
app/services/syntax_validator.py's own fallback for the same constraint), so Java detectors here
work directly on source text. `mask_strings_and_comments` is the one piece of real rigor this
gives them: it replaces the *contents* of string/char literals and comments with spaces (keeping
line breaks and overall length intact, so line numbers and brace positions stay accurate)
without touching anything else. That means brace-depth tracking and keyword search run against
this masked text and can't be fooled by a `{` or `if(` sitting inside a string or a comment.
"""
from __future__ import annotations


def mask_strings_and_comments(code: str) -> str:
    out = []
    i = 0
    n = len(code)
    in_line_comment = False
    in_block_comment = False
    in_string = False
    in_char = False
    escape = False

    while i < n:
        ch = code[i]
        nxt = code[i + 1] if i + 1 < n else ""

        if ch == "\n":
            in_line_comment = False
            out.append("\n")
            i += 1
            continue

        if in_line_comment or in_block_comment:
            if in_block_comment and ch == "*" and nxt == "/":
                out.append("  ")
                i += 2
                in_block_comment = False
                continue
            out.append(" ")
            i += 1
            continue

        if in_string:
            out.append(" " if ch != "\\" else " ")
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if in_char:
            out.append(" ")
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "'":
                in_char = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            out.append("  ")
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            out.append("  ")
            i += 2
            continue
        if ch == '"':
            in_string = True
            out.append(" ")
            i += 1
            continue
        if ch == "'":
            in_char = True
            out.append(" ")
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out)


def find_matching_brace(masked: str, open_brace_index: int) -> int:
    """Given the index of an opening `{` in masked text, return the index of its matching `}`."""
    depth = 0
    for i in range(open_brace_index, len(masked)):
        if masked[i] == "{":
            depth += 1
        elif masked[i] == "}":
            depth -= 1
            if depth == 0:
                return i
    return len(masked) - 1


def line_of(text: str, index: int) -> int:
    return text.count("\n", 0, index) + 1


def mask_comments_only(code: str) -> str:
    """
    Like `mask_strings_and_comments`, but leaves string/char literal contents (and their
    delimiting quotes) untouched — only comments are blanked out.

    The security detectors need this instead of the full masking: they specifically inspect
    *what's inside* string literals (a hardcoded secret's value, a SQL keyword inside a query
    string, a hash algorithm name passed as an argument). Blanking string contents — correct for
    the code-quality agent's brace-matching, where a `{` inside a string must not be mistaken
    for a real code brace — would erase exactly the content these rules need to match against.
    Comments still need masking here too, so a vulnerability pattern mentioned in a comment
    (rather than actually present in code) doesn't produce a false positive.
    """
    out = []
    i = 0
    n = len(code)
    in_line_comment = False
    in_block_comment = False
    in_string = False
    in_char = False
    escape = False

    while i < n:
        ch = code[i]
        nxt = code[i + 1] if i + 1 < n else ""

        if ch == "\n":
            in_line_comment = False
            out.append("\n")
            i += 1
            continue

        if in_line_comment or in_block_comment:
            if in_block_comment and ch == "*" and nxt == "/":
                out.append("  ")
                i += 2
                in_block_comment = False
                continue
            out.append(" ")
            i += 1
            continue

        if in_string:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            i += 1
            continue

        if in_char:
            out.append(ch)
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == "'":
                in_char = False
            i += 1
            continue

        if ch == "/" and nxt == "/":
            in_line_comment = True
            out.append("  ")
            i += 2
            continue
        if ch == "/" and nxt == "*":
            in_block_comment = True
            out.append("  ")
            i += 2
            continue
        if ch == '"':
            in_string = True
            out.append(ch)
            i += 1
            continue
        if ch == "'":
            in_char = True
            out.append(ch)
            i += 1
            continue

        out.append(ch)
        i += 1

    return "".join(out)
