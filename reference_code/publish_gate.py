"""Pure publication rule reference, Python >=3.11.

Inputs MUST be loaded by a trusted repository after authentication, authorization,
checker signature verification, canonical-check selection and revision locking.
Never construct these objects directly from browser or Agent JSON. The `trusted`
flag below represents that prior boundary; it does not implement cryptography.
This module does not replace database transactions, RLS, RBAC or artifact storage.
"""
from dataclasses import dataclass
from enum import Enum
from typing import Mapping


class Status(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    REVIEW = "REVIEW"


@dataclass(frozen=True)
class Check:
    check_id: str
    code: str  # qualified e.g. question:q1:structure or render:student:preflight
    subject_hash: str
    status: Status
    manual_allowed: bool = False
    trusted: bool = False


@dataclass(frozen=True)
class Resolution:
    check_id: str
    subject_hash: str
    reviewer_id: str
    rationale: str
    trusted: bool = False


@dataclass(frozen=True)
class Approval:
    target_hash: str
    reviewer_id: str
    trusted: bool = False


@dataclass(frozen=True)
class GateResult:
    allowed: bool
    reasons: tuple[str, ...]


def evaluate_publish(
    *,
    content_hash: str,
    required_checks: Mapping[str, str],
    checks: tuple[Check, ...],
    resolutions: tuple[Resolution, ...],
    content_approvals: tuple[Approval, ...],
    render_hashes: tuple[str, ...],
    render_approvals: tuple[Approval, ...],
    authorized_reviewer_ids: frozenset[str],
    content_author_ids: frozenset[str],
    min_content_reviewers: int,
    require_separation: bool,
    complete: bool,
    policy_allows_use: bool,
) -> GateResult:
    """Fail closed. Each required check code must have one canonical current record.

    Historical runs must remain in storage but are not passed as the canonical set.
    The service derives required_checks from frozen policy, never from the Agent.
    """
    reasons: list[str] = []
    if min_content_reviewers < 1:
        raise ValueError("min_content_reviewers must be >= 1")
    if not content_hash or not required_checks or not render_hashes:
        reasons.append("INCOMPLETE_GATE_INPUT")
    if not complete:
        reasons.append("INCOMPLETE_EXAM")
    if not policy_allows_use:
        reasons.append("POLICY_BLOCKED")

    def reviewer_allowed(person: str) -> bool:
        return person in authorized_reviewer_ids and (
            not require_separation or person not in content_author_ids
        )

    by_code: dict[str, Check] = {}
    seen_ids: set[str] = set()
    for check in checks:
        if check.code in by_code or check.check_id in seen_ids:
            reasons.append("DUPLICATE_CANONICAL_CHECK:" + check.code)
        by_code[check.code] = check
        seen_ids.add(check.check_id)
        if not check.trusted:
            reasons.append("UNTRUSTED_CHECK:" + check.code)
        expected = required_checks.get(check.code)
        if expected is None:
            reasons.append("UNDECLARED_CHECK:" + check.code)
        elif check.subject_hash != expected:
            reasons.append("STALE_CHECK:" + check.code)
        if check.status == Status.FAIL:
            reasons.append("UNRESOLVED_FAIL:" + check.code)
        elif check.status == Status.REVIEW:
            resolved = check.manual_allowed and any(
                r.trusted
                and r.check_id == check.check_id
                and r.subject_hash == check.subject_hash
                and reviewer_allowed(r.reviewer_id)
                and bool(r.rationale.strip())
                for r in resolutions
            )
            if not resolved:
                reasons.append("REVIEW_REQUIRED:" + check.code)
        elif check.status != Status.PASS:
            reasons.append("INVALID_STATUS:" + check.code)

    for code in required_checks:
        if code not in by_code:
            reasons.append("MISSING_CHECK:" + code)

    approvers = {
        a.reviewer_id
        for a in content_approvals
        if a.trusted and a.target_hash == content_hash and reviewer_allowed(a.reviewer_id)
    }
    if len(approvers) < min_content_reviewers:
        reasons.append("CONTENT_APPROVALS_INSUFFICIENT")
    for render_hash in set(render_hashes):
        if not any(
            a.trusted and a.target_hash == render_hash and reviewer_allowed(a.reviewer_id)
            for a in render_approvals
        ):
            reasons.append("RENDER_NOT_APPROVED:" + render_hash)
    return GateResult(not reasons, tuple(sorted(set(reasons))))
