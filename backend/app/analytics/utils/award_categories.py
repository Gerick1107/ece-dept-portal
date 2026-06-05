"""Classify faculty awards into analytics categories."""

from __future__ import annotations

CATEGORIES: list[tuple[str, tuple[str, ...]]] = [
    ("Best Paper / Demo / Poster", ("best paper", "best demo", "best poster", "best tutorial")),
    ("Teaching Excellence", ("teaching excellence", "educator award", "outstanding educator")),
    (
        "Research & Fellowship",
        ("research excellence", "fellowship", "serb", "dean", "chair position", "institute chair"),
    ),
    (
        "Conference Leadership",
        ("chair", "panelist", "keynote", "invited speaker", "session co-chair", "organiz"),
    ),
    (
        "Competitive Award & Grant",
        ("winner", "first place", "scholarship", "grant", "felicitation", "qualify", "runners up", "3rd prize"),
    ),
    ("Membership & Elevation", ("senior member", "elevated", "fellow")),
]


def classify_award(award_text: str) -> str:
    lower = (award_text or "").lower()
    for category, keywords in CATEGORIES:
        if any(kw in lower for kw in keywords):
            return category
    return "Other"
