import hmac
import re

from fastapi import HTTPException, Response, status

TOKEN_RE = re.compile(r"^[0-9a-f]{64}$")


def valid_configured_token(token: str) -> bool:
    return bool(TOKEN_RE.fullmatch(token))


def token_matches(provided: str, expected: str) -> bool:
    if not valid_configured_token(expected):
        return False
    if not TOKEN_RE.fullmatch(provided):
        padded = provided[:64].ljust(64, "0")
        hmac.compare_digest(padded, expected)
        return False
    return hmac.compare_digest(provided, expected)


def require_token(provided: str, expected: str) -> None:
    if not token_matches(provided, expected):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=None)


def empty_404() -> Response:
    return Response(status_code=status.HTTP_404_NOT_FOUND, content=b"")
