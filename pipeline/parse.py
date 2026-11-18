"""Turn one raw HN comment into a classified job post."""

from __future__ import annotations

import html
import re
from dataclasses import dataclass, field
from statistics import median

from . import taxonomy

_TAG = re.compile(r"<[^>]+>")
_BLOCK = re.compile(r"(?i)<p>|<br\s*/?>|</pre>")

_DASH = r"\s*(?:-{1,2}|–|—|to)\s*"
_NUM = r"(\d{2,3}(?:\.\d)?)"
_THOUSANDS = r"(\d{2,3}),(\d{3})(?![,.]?\d)"
# (pattern, is_range, uses_thousands_separator), tried in order; earlier wins on overlap.
_SALARY_PATTERNS = [
    # $120k - $180k, $120K–180K
    (re.compile(rf"\$\s?{_NUM}\s?[kK]{_DASH}\$?\s?{_NUM}\s?[kK]\b"), True, False),
    # $120,000 - $180,000
    (re.compile(rf"\$\s?{_THOUSANDS}{_DASH}\$?\s?{_THOUSANDS}"), True, True),
    # $120-180k, $135-$155k
    (re.compile(rf"\$\s?{_NUM}{_DASH}\$?\s?{_NUM}\s?[kK]\b"), True, False),
    # 120k - 180k USD
    (re.compile(rf"\b{_NUM}\s?[kK]{_DASH}{_NUM}\s?[kK]\s?USD\b"), True, False),
    # $181K base
    (re.compile(rf"\$\s?{_NUM}\s?[kK]\b"), False, False),
    # $178,500
    (re.compile(rf"\$\s?{_THOUSANDS}"), False, True),
]
_NOT_PAY_AFTER = re.compile(
    r"(?i)^\s*(?:USD\s*)?(?:/\s*(?:h(?:ou)?r|mo(?:nth)?|wk|week|day)\b|per\s+(?:hour|month|week|day)\b"
    r"|an?\s+(?:hour|month)\b|hourly|monthly|[MB]\b|MM\b|in\s+(?:funding|revenue|arr)\b"
    r"|(?:[\w-]+\s+)?(?:bonus|stipend|budget|grant|fee|bounty|prize)\b)"
)
_NOT_PAY_BEFORE = re.compile(
    r"(?i)(?:rais\w*|fund\w*|valuation|revenue|arr|bonus|fee|budget|grant|prize|bounty|seed|series \w)\W{0,3}(?:\w+\W+){0,3}$"
)


def html_to_text(raw: str) -> str:
    """HN comment HTML to plain text, keeping paragraph breaks."""
    text = _BLOCK.sub("\n", raw)
    text = _TAG.sub("", text)
    return html.unescape(text).strip()


def salary_ranges(text: str) -> list[tuple[int, int]]:
    """Annual USD salary ranges in a post, in dollars, after plausibility checks."""
    found: list[tuple[int, tuple[int, int]]] = []
    taken: list[tuple[int, int]] = []
    for pattern, is_range, thousands in _SALARY_PATTERNS:
        for m in pattern.finditer(text):
            if any(s < m.end() and m.start() < e for s, e in taken):
                continue
            taken.append((m.start(), m.end()))
            if _NOT_PAY_AFTER.match(text[m.end() : m.end() + 20]):
                continue
            if _NOT_PAY_BEFORE.search(text[max(0, m.start() - 40) : m.start()]):
                continue
            g = m.groups()
            if thousands:
                values = [int(g[i]) * 1000 + int(g[i + 1]) for i in range(0, len(g), 2)]
            else:
                values = [round(float(v) * 1000) for v in g]
            lo, hi = values[0], values[-1]
            ok = (20_000 <= lo <= hi <= 1_000_000 and hi <= lo * 3) if is_range else 40_000 <= lo <= 600_000
            if ok:
                found.append((m.start(), (lo, hi)))
    return [r for _, r in sorted(found)]


@dataclass
class Post:
    text: str
    techs: set[str] = field(default_factory=set)
    remote: bool = False
    hybrid: bool = False
    onsite: bool = False
    salary_mid: float | None = None
    visa_offered: bool = False
    junior: bool = False
    intern: bool = False

    @property
    def arrangement(self) -> str:
        if self.hybrid or (self.remote and self.onsite):
            return "hybrid"
        if self.remote:
            return "remote"
        if self.onsite:
            return "onsite"
        return "unspecified"


def classify(raw_html: str) -> Post:
    text = html_to_text(raw_html)
    post = Post(text=text)
    post.techs = {name for name, rx in taxonomy.TECH.items() if rx.search(text)}
    post.remote = bool(taxonomy.REMOTE.search(text))
    post.hybrid = bool(taxonomy.HYBRID.search(text))
    post.onsite = bool(taxonomy.ONSITE.search(text))
    ranges = salary_ranges(text)
    if ranges:
        post.salary_mid = median((lo + hi) / 2 for lo, hi in ranges)
    post.visa_offered = bool(taxonomy.VISA.search(text)) and not taxonomy.VISA_NEGATED.search(text)
    post.junior = bool(taxonomy.JUNIOR.search(text))
    post.intern = bool(taxonomy.INTERN.search(text))
    return post
