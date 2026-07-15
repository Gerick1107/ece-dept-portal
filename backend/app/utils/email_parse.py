"""Parse recipient email addresses from free text or Excel uploads."""

from __future__ import annotations

import io
import re
from email.utils import parseaddr

import pandas as pd

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")

_EMAIL_HEADER_ALIASES = frozenset(
    {
        "email",
        "e mail",
        "mail",
        "mail id",
        "email id",
        "email address",
        "e mail id",
        "e mail address",
        "emailid",
        "mailid",
        "e-mail",
        "e-mail id",
        "e-mail address",
        "recipient email",
        "recipient",
    }
)


def _normalize_header(text: str) -> str:
    return " ".join(re.sub(r"[^a-z0-9 ]", " ", str(text or "").lower()).split())


def _is_email_header(header: str) -> bool:
    norm = _normalize_header(header)
    if norm in _EMAIL_HEADER_ALIASES:
        return True
    return "email" in norm or norm.endswith(" mail") or norm.startswith("mail ")


def _valid_email(value: str) -> str | None:
    value = value.strip()
    if not value:
        return None
    _, addr = parseaddr(value)
    addr = addr or value
    if _EMAIL_RE.fullmatch(addr):
        return addr.lower()
    return None


def parse_emails_from_text(text: str) -> list[str]:
    """Extract unique emails from comma/newline/semicolon-separated text."""
    seen: set[str] = set()
    out: list[str] = []
    for token in re.split(r"[\s,;\n\r\t|]+", text or ""):
        email = _valid_email(token)
        if email and email not in seen:
            seen.add(email)
            out.append(email)
    return out


def _column_email_ratio(series: pd.Series) -> float:
    values = series.dropna().astype(str).head(50)
    if values.empty:
        return 0.0
    hits = sum(1 for v in values if _valid_email(v))
    return hits / len(values)


def _find_email_column(df: pd.DataFrame) -> str | None:
    for col in df.columns:
        if _is_email_header(str(col)):
            return str(col)
    best_col: str | None = None
    best_ratio = 0.0
    for col in df.columns:
        ratio = _column_email_ratio(df[col])
        if ratio > best_ratio:
            best_ratio, best_col = ratio, str(col)
    if best_col and best_ratio >= 0.5:
        return best_col
    return None


def parse_emails_from_excel(content: bytes) -> list[str]:
    """Read an Excel file and return unique emails from the email column."""
    df = pd.read_excel(io.BytesIO(content))
    if df.empty:
        return []
    col = _find_email_column(df)
    if not col:
        # Last resort: scan every cell
        seen: set[str] = set()
        out: list[str] = []
        for val in df.astype(str).values.flatten():
            email = _valid_email(val)
            if email and email not in seen:
                seen.add(email)
                out.append(email)
        return out
    seen: set[str] = set()
    out: list[str] = []
    for raw in df[col].dropna():
        email = _valid_email(str(raw))
        if email and email not in seen:
            seen.add(email)
            out.append(email)
    return out
