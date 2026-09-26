import re

_DATA_URI = re.compile(
    r"data:[^\s;]+;base64,[A-Za-z0-9+/=\r\n]+",
    re.IGNORECASE,
)
_LONG_BASE64 = re.compile(r"[A-Za-z0-9+/]{200,}={0,2}")


def text_for_model(message: str) -> str:
    """Drop embedded images before the model sees the ticket.

    A base64 footer can be larger than the context window. The outbound mail
    still carries the original message.
    """
    without_images = _DATA_URI.sub("[attachment omitted]", message)
    without_images = _LONG_BASE64.sub("[attachment omitted]", without_images)
    collapsed = without_images.strip()
    return collapsed or "[attachment omitted]"
