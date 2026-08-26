"""Agent 2: manufacture wrong answers that are worth considering.

Distractor quality is what separates a usable MCQ from a giveaway. Three rules
carry most of the weight:

1. A distractor must be the *same kind of thing* as the answer -- a year against
   a year, a general against a general, a percentage against a percentage.
2. It must be plausibly close but unambiguously wrong. A perturbed number stays
   in the right order of magnitude; a swapped entity comes from the same article
   where possible, so it is on-topic.
3. It must not accidentally be true. For numbers that is guaranteed by
   construction; for entities the caller filters against the source sentence.

When the article itself cannot supply same-type alternatives, small curated
pools of Pakistan/defence general knowledge fill the gap -- still no API call.
"""

from __future__ import annotations

import random
import re
from decimal import Decimal, InvalidOperation

_NUMBER_IN = re.compile(r"\d[\d,]*(?:\.\d+)?")

# Fallback pools: on-topic, mutually exclusive, and safe to use as wrong
# answers because the caller drops any that match the real one.
FALLBACK_POOLS: dict[str, list[str]] = {
    "PERSON": [
        "General Asim Munir", "Admiral Naveed Ashraf", "Air Chief Marshal Zaheer Ahmed Babar",
        "General Qamar Javed Bajwa", "Admiral Amjad Khan Niazi", "General Raheel Sharif",
    ],
    "ORG": [
        "Pakistan Army", "Pakistan Navy", "Pakistan Air Force", "Ministry of Defence",
        "Inter-Services Public Relations", "National Command Authority",
        "Pakistan Aeronautical Complex", "Heavy Industries Taxila",
    ],
    "GPE": [
        "Karachi", "Islamabad", "Lahore", "Rawalpindi", "Quetta", "Peshawar",
        "Gwadar", "Kakul", "Risalpur", "Kohat",
    ],
    "PROPER": [
        "PNS Tughril", "PNS Shahjahan", "JF-17 Thunder", "Al-Khalid", "Babur cruise missile",
        "Shaheen-III", "Ghauri", "Al-Zarrar",
    ],
}

_MONTHS = [
    "January", "February", "March", "April", "May", "June",
    "July", "August", "September", "October", "November", "December",
]


def _format_like(template: str, value: Decimal) -> str:
    """Render ``value`` using the formatting of the original number."""
    text = f"{value:f}"
    if "." in text:
        decimals = len(template.split(".")[1]) if "." in template else 0
        text = f"{value:.{decimals}f}" if decimals else text.split(".")[0]
    if "," in template and len(text.split(".")[0]) > 3:
        whole, _, frac = text.partition(".")
        text = f"{int(whole):,}" + (f".{frac}" if frac else "")
    return text


def numeric(answer: str, count: int = 3, rng: random.Random | None = None) -> list[str]:
    """Perturb the number inside ``answer``, keeping its units and format.

    Multipliers stay inside one order of magnitude so the options remain a real
    choice rather than an obvious outlier.
    """
    rng = rng or random.Random(answer)
    match = _NUMBER_IN.search(answer)
    if not match:
        return []

    raw = match.group(0)
    try:
        value = Decimal(raw.replace(",", ""))
    except InvalidOperation:
        return []

    factors = [Decimal("0.5"), Decimal("0.75"), Decimal("1.25"), Decimal("1.5"), Decimal("2")]
    rng.shuffle(factors)

    seen = {raw}
    out: list[str] = []
    for factor in factors:
        candidate = value * factor
        if candidate <= 0:
            continue
        if value == value.to_integral_value():
            candidate = candidate.to_integral_value()
        text = _format_like(raw, candidate)
        if text in seen:
            continue
        seen.add(text)
        out.append(answer.replace(raw, text, 1))
        if len(out) >= count:
            break

    # Small integers run out of distinct multiples fast; walk outwards instead.
    offset = 1
    while len(out) < count and offset < 12:
        for delta in (offset, -offset):
            candidate = value + delta
            if candidate <= 0:
                continue
            text = _format_like(raw, candidate.to_integral_value() if value == value.to_integral_value() else candidate)
            if text not in seen:
                seen.add(text)
                out.append(answer.replace(raw, text, 1))
            if len(out) >= count:
                break
        offset += 1
    return out[:count]


def date_like(answer: str, count: int = 3, rng: random.Random | None = None) -> list[str]:
    """Shift years and months, staying inside a believable window."""
    rng = rng or random.Random(answer)
    out: list[str] = []
    seen = {answer}

    year_match = re.search(r"\b(1[5-9]\d{2}|20\d{2})\b", answer)
    if year_match:
        year = int(year_match.group(0))
        offsets = [-3, -2, -1, 1, 2, 3, 5]
        rng.shuffle(offsets)
        for offset in offsets:
            candidate = answer.replace(year_match.group(0), str(year + offset), 1)
            if candidate not in seen:
                seen.add(candidate)
                out.append(candidate)
            if len(out) >= count:
                return out

    for month in _MONTHS:
        if month.lower() in answer.lower():
            others = [m for m in _MONTHS if m != month]
            rng.shuffle(others)
            for other in others:
                candidate = re.sub(month, other, answer, count=1, flags=re.IGNORECASE)
                if candidate not in seen:
                    seen.add(candidate)
                    out.append(candidate)
                if len(out) >= count:
                    return out
            break

    day_match = re.match(r"^(\d{1,2})\s", answer)
    if day_match:
        day = int(day_match.group(1))
        for delta in (1, -1, 2, -2, 3):
            candidate_day = day + delta
            if 1 <= candidate_day <= 28:
                candidate = answer.replace(day_match.group(1), str(candidate_day), 1)
                if candidate not in seen:
                    seen.add(candidate)
                    out.append(candidate)
            if len(out) >= count:
                break
    return out[:count]


def _similar_shape(answer: str, candidate: str) -> bool:
    """Keep options visually comparable -- length and word count in the same range."""
    a_words, c_words = len(answer.split()), len(candidate.split())
    if abs(a_words - c_words) > 2:
        return False
    if not answer or not candidate:
        return False
    ratio = len(candidate) / len(answer)
    return 0.45 <= ratio <= 2.2


def entity(
    answer: str,
    *,
    pool: list[str],
    label: str = "PROPER",
    count: int = 3,
    forbid: str = "",
    rng: random.Random | None = None,
) -> list[str]:
    """Pick same-type alternatives, preferring ones from the same article.

    ``forbid`` is the source sentence: anything appearing in it is skipped,
    because a distractor drawn from the same sentence is often quietly true.
    """
    rng = rng or random.Random(answer)
    answer_lower = answer.lower()
    forbid_lower = forbid.lower()

    def usable(candidate: str) -> bool:
        low = candidate.lower()
        if low == answer_lower or low in answer_lower or answer_lower in low:
            return False
        if forbid_lower and low in forbid_lower:
            return False
        return _similar_shape(answer, candidate)

    from_article = [c for c in dict.fromkeys(pool) if usable(c)]
    rng.shuffle(from_article)
    out = from_article[:count]

    if len(out) < count:
        fallback = [c for c in FALLBACK_POOLS.get(label, FALLBACK_POOLS["PROPER"]) if usable(c)]
        rng.shuffle(fallback)
        for candidate in fallback:
            if candidate not in out:
                out.append(candidate)
            if len(out) >= count:
                break

    if len(out) < count and label != "PROPER":
        for candidate in FALLBACK_POOLS["PROPER"]:
            if usable(candidate) and candidate not in out:
                out.append(candidate)
            if len(out) >= count:
                break
    return out[:count]


def build(
    answer: str,
    *,
    kind: str,
    pool: list[str] | None = None,
    label: str = "PROPER",
    count: int = 3,
    forbid: str = "",
    seed: str | None = None,
) -> list[str]:
    """Dispatch to the right strategy for the answer type."""
    rng = random.Random(seed or answer)

    if kind == "numeric":
        out = numeric(answer, count, rng)
    elif kind == "date":
        out = date_like(answer, count, rng)
    else:
        out = entity(answer, pool=pool or [], label=label, count=count, forbid=forbid, rng=rng)

    # A short numeric answer can still fail (e.g. no digits found); fall back to
    # entity-style options rather than returning a two-option question.
    if len(out) < count and kind in {"numeric", "date"}:
        out.extend(
            entity(
                answer,
                pool=pool or [],
                label=label,
                count=count - len(out),
                forbid=forbid,
                rng=rng,
            )
        )

    seen = {answer.lower()}
    unique: list[str] = []
    for candidate in out:
        low = candidate.lower()
        if low not in seen:
            seen.add(low)
            unique.append(candidate)
    return unique[:count]
