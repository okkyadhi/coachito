"""Tennis curriculum seed-data integrity.

Pure-data checks (no DB) guarding the tennis bundle authored from
tennis-skill-framework-v0.1.md sections 4-7 against drift:

- 29 skills with the sec.4 category split (14 tech / 7 tact / 4 phys / 4 mental)
- exactly 5 descriptors per skill on the locked 1-5 scale
- descriptor + tier-requirement skill codes all resolve to a real skill
- every code is TENNIS_-prefixed and unique
- tier requirements cover the six graduating tiers with valid min levels
"""

from __future__ import annotations

import json
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"


def _load(name: str) -> list[dict]:  # type: ignore[type-arg]
    with open(DATA / name) as f:
        return json.load(f)  # type: ignore[no-any-return]


SKILLS = _load("skills_tennis.json")
DESCRIPTORS = _load("descriptors_tennis.json")
TIERS = _load("tiers_tennis.json")
REQUIREMENTS = _load("tier_requirements_tennis.json")

SKILL_CODES = {s["code"] for s in SKILLS}


def test_skill_count_and_category_split() -> None:
    assert len(SKILLS) == 29
    by_cat: dict[str, int] = {}
    for s in SKILLS:
        by_cat[s["category"]] = by_cat.get(s["category"], 0) + 1
    assert by_cat == {"technical": 14, "tactical": 7, "physical": 4, "mental": 4}


def test_skill_codes_unique_and_prefixed() -> None:
    assert len(SKILL_CODES) == len(SKILLS), "duplicate skill code"
    for s in SKILLS:
        assert s["code"].startswith("TENNIS_"), s["code"]
        # Bilingual labels present and non-empty.
        for key in ("name_en", "name_id", "short_label_en", "short_label_id"):
            assert s.get(key), f"{s['code']} missing {key}"


def test_display_order_is_dense_1_to_29() -> None:
    orders = sorted(s["display_order"] for s in SKILLS)
    assert orders == list(range(1, 30))


def test_five_descriptors_per_skill_on_locked_scale() -> None:
    seen: dict[str, set[int]] = {}
    for d in DESCRIPTORS:
        assert d["skill_code"] in SKILL_CODES, f"orphan descriptor {d['skill_code']}"
        assert 1 <= d["level"] <= 5
        assert d["description_en"].strip()
        assert d["description_id"].strip()
        seen.setdefault(d["skill_code"], set()).add(d["level"])
    assert len(DESCRIPTORS) == 145
    for code in SKILL_CODES:
        assert seen.get(code) == {1, 2, 3, 4, 5}, f"{code} missing levels"


def test_tiers_mirror_padel_seven() -> None:
    codes = [t["code"] for t in TIERS]
    assert codes == [
        "BEGINNER",
        "LOWER_BRONZE",
        "BRONZE",
        "SILVER",
        "GOLD",
        "PLATINUM",
        "DIAMOND",
    ]


def test_requirements_reference_real_skills_and_graduating_tiers() -> None:
    tier_codes = [b["tier_code"] for b in REQUIREMENTS]
    # BEGINNER is the entry tier — no graduation requirements.
    assert tier_codes == [
        "LOWER_BRONZE",
        "BRONZE",
        "SILVER",
        "GOLD",
        "PLATINUM",
        "DIAMOND",
    ]
    for block in REQUIREMENTS:
        for req in block["requirements"]:
            assert req["skill_code"] in SKILL_CODES, req["skill_code"]
            assert 1 <= req["min_level"] <= 5


def test_requirements_are_monotonic_per_skill() -> None:
    """A skill's min level must not drop as tiers rise — graduation is
    cumulative, never regressive."""
    order = ["LOWER_BRONZE", "BRONZE", "SILVER", "GOLD", "PLATINUM", "DIAMOND"]
    by_tier = {b["tier_code"]: b for b in REQUIREMENTS}
    prev: dict[str, int] = {}
    for tier in order:
        for req in by_tier[tier]["requirements"]:
            code, lvl = req["skill_code"], req["min_level"]
            assert lvl >= prev.get(code, 0), (
                f"{code} regresses at {tier}: {prev.get(code)} -> {lvl}"
            )
            prev[code] = lvl
