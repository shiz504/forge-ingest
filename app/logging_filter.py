import logging
import re
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

SECRETISH_RE = re.compile(r"^(?:[0-9a-fA-F]{65,}|[A-Za-z0-9+/=_-]{65,})$")
TOKEN_PATH_RE = re.compile(r"^/([0-9a-f]{64,})(/.*)?$")


def redact_path(path: str) -> str:
    parts = urlsplit(path)
    clean_path = TOKEN_PATH_RE.sub(lambda m: "/[REDACTED]" + (m.group(2) or ""), parts.path)
    redacted_query = []
    for key, value in parse_qsl(parts.query, keep_blank_values=True):
        if key in {"include", "exclude"} and SECRETISH_RE.fullmatch(value):
            redacted_query.append((key, "[REDACTED]"))
        else:
            redacted_query.append((key, value))
    return urlunsplit(("", "", clean_path, urlencode(redacted_query), ""))


class TokenRedactionFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for attr in ("path", "raw_path"):
            value = getattr(record, attr, None)
            if isinstance(value, str):
                setattr(record, attr, redact_path(value))
        return True
