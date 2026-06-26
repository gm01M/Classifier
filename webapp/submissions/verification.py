"""Cross-check the photo classification against the self-reported profile.

The classifier predicts age (as a bucket label like ``"30-39"``) and gender from
the photo. Here we compare those to what the user claimed at onboarding and decide
whether the submission is *consistent*. Age estimation from a single photo is
noisy, so the age check allows a tolerance band before flagging a mismatch.
"""

from __future__ import annotations

import re

from .models import Consistency

# How far (years) the claimed age may fall outside the predicted bucket before we
# call it a mismatch. Generous because photo age-estimation is approximate.
AGE_TOLERANCE_YEARS = 8


def parse_age_bucket(label: str) -> tuple[int, int] | None:
    """Parse an age-bucket label into an inclusive ``(low, high)`` range.

    Handles ``"20-29"``, ``"0-2"``, ``"more than 70"``, ``"60+"``, ``"3-9"``.
    """
    if not label:
        return None
    text = label.lower().strip()
    nums = [int(n) for n in re.findall(r"\d+", text)]
    if not nums:
        return None
    if "more than" in text or "+" in text or ">" in text:
        return (nums[0], 120)
    if len(nums) == 1:
        return (nums[0], nums[0])
    return (min(nums), max(nums))


def _prediction(result: dict, attribute: str) -> dict | None:
    for p in (result or {}).get("predictions", []):
        if p.get("attribute") == attribute:
            return p
    return None


def evaluate(*, claimed_age: int, claimed_gender: str, result: dict) -> tuple[str, dict]:
    """Return ``(consistency_status, details)`` comparing prediction vs profile.

    ``details`` records each sub-check so the admin UI/API can explain *why* a
    submission was flagged.
    """
    reasons: list[str] = []
    details: dict = {"claimed_age": claimed_age, "claimed_gender": claimed_gender}

    # --- Age check ----------------------------------------------------------
    age_pred = _prediction(result, "age")
    age_match: bool | None = None
    if age_pred:
        bucket = parse_age_bucket(str(age_pred.get("label", "")))
        details["predicted_age"] = age_pred.get("label")
        if bucket and claimed_age is not None:
            low, high = bucket
            age_match = (low - AGE_TOLERANCE_YEARS) <= claimed_age <= (high + AGE_TOLERANCE_YEARS)
            if not age_match:
                reasons.append(f"claimed age {claimed_age} vs photo {age_pred.get('label')}")
    details["age_match"] = age_match

    # --- Gender check -------------------------------------------------------
    gender_pred = _prediction(result, "gender")
    gender_match: bool | None = None
    claimed = (claimed_gender or "").lower()
    if gender_pred and claimed in ("male", "female"):
        predicted = str(gender_pred.get("label", "")).lower()
        details["predicted_gender"] = gender_pred.get("label")
        if predicted in ("male", "female"):
            gender_match = predicted == claimed
            if not gender_match:
                reasons.append(f"claimed gender {claimed} vs photo {predicted}")
    details["gender_match"] = gender_match
    details["reasons"] = reasons

    # --- Overall ------------------------------------------------------------
    checks = [m for m in (age_match, gender_match) if m is not None]
    if not checks:
        status = Consistency.UNVERIFIED
    elif all(checks):
        status = Consistency.CONSISTENT
    else:
        status = Consistency.INCONSISTENT
    return status, details
