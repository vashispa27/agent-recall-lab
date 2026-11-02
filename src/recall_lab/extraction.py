"""Candidate extraction contract; proposals are untrusted until reviewed."""

import re
from collections.abc import Iterable
from dataclasses import dataclass
from typing import Protocol

from recall_lab.core import redact


@dataclass(frozen=True)
class CandidateProposal:
    body: str
    # Ordered source event IDs: failed command, explicit correction, successful command.
    evidence: tuple[str, str, str]


class CandidateExtractor(Protocol):
    provider_id: str

    def extract(self, trace: dict) -> Iterable[CandidateProposal]: ...


class CorrectionRuleExtractor:
    """Deterministic ordering baseline, not a causal or safety assessment."""

    provider_id = "explicit-correction-v1"

    def extract(self, trace: dict) -> Iterable[CandidateProposal]:
        events = trace["events"]
        for i, event in enumerate(events):
            if event["action"] != "correction":
                continue
            failures = [e for e in events[:i] if e["action"] == "command" and e["exit_code"] != 0]
            successes = [
                e for e in events[i + 1 :] if e["action"] == "command" and e["exit_code"] == 0
            ]
            if failures and successes:
                yield CandidateProposal(
                    event["text"], (failures[-1]["id"], event["id"], successes[0]["id"])
                )


def validate_provider(provider: CandidateExtractor) -> str:
    identity = getattr(provider, "provider_id", None)
    if not isinstance(identity, str) or not re.fullmatch(r"[a-z0-9][a-z0-9._-]{0,79}", identity):
        raise ValueError("Invalid extraction provider identity")
    return identity


def validate_proposal(proposal: CandidateProposal, trace: dict) -> CandidateProposal:
    """Check references against the original stored trace, never provider-mutated input."""
    if (
        not isinstance(proposal, CandidateProposal)
        or not isinstance(proposal.body, str)
        or not proposal.body.strip()
        or not isinstance(proposal.evidence, tuple)
        or len(proposal.evidence) != 3
        or not all(isinstance(x, str) for x in proposal.evidence)
    ):
        raise ValueError("Invalid candidate proposal")
    events = trace["events"]
    positions = {e["id"]: i for i, e in enumerate(events)}
    if any(identity not in positions for identity in proposal.evidence):
        raise ValueError("Candidate evidence must reference source events")
    a, b, c = [positions[identity] for identity in proposal.evidence]
    if not (
        a < b < c
        and events[a]["action"] == "command"
        and events[a]["exit_code"] != 0
        and events[b]["action"] == "correction"
        and events[c]["action"] == "command"
        and events[c]["exit_code"] == 0
    ):
        raise ValueError("Candidate evidence must be ordered failure, correction, success")
    return CandidateProposal(redact(proposal.body), proposal.evidence)
