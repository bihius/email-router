import re

_DATA_URI = re.compile(
    r"data:[^\s;]+;base64,[A-Za-z0-9+/=\r\n]+",
    re.IGNORECASE,
)
_LONG_BASE64 = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")


def _is_signature_delimiter(line: str) -> bool:
    """True when the line is exactly two ASCII hyphens and optional trailing spaces or tabs.

    That covers RFC 3676 ("-- ") and the common "--". Three or more hyphens,
    a "--" inside a sentence, and a line that has other words do not match.
    """
    content = line.rstrip("\r\n")
    return content.startswith("--") and content[2:].strip(" \t") == ""


def _drop_signature_footer(text: str) -> str:
    """Drop a signature delimiter line and everything after it."""
    lines = text.splitlines(keepends=True)
    for index, line in enumerate(lines):
        if _is_signature_delimiter(line):
            return "".join(lines[:index])
    return text


def text_for_model(message: str) -> str:
    """Drop embedded images and a signature footer before the model sees the ticket.

    A base64 blob can be larger than the context window. A line of "--" or
    "-- " starts a signature; that line and everything after it are omitted.
    Blob stripping runs first. The outbound mail still carries the original
    message.
    """
    without_images = _DATA_URI.sub("[attachment omitted]", message)
    without_images = _LONG_BASE64.sub("[attachment omitted]", without_images)
    without_footer = _drop_signature_footer(without_images)
    collapsed = without_footer.strip()
    return collapsed or "[attachment omitted]"
