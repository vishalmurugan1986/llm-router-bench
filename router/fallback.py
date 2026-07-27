"""Per-ticket fallback: even after picking a cheapest-viable model globally,
individual tickets can still fail. This is the safety valve.

This module is intentionally simple for v1 -- confidence is proxied by
whether the deterministic checks passed. A real version might use logprobs,
a self-reported confidence field, or a second cheap-model vote.
"""

from __future__ import annotations

from agent.schemas import Decision  # from the harness package
from router.schemas import RouteDecision


def should_fallback(decision: Decision, det_passed: bool) -> bool:
    """Trigger escalation to a stronger model when the cheap model's own
    output looks shaky -- not confident, just plausible for a v1 heuristic:
    empty replies, or a mismatch between category and action are red flags.
    """
    if not det_passed:
        return True
    if not decision.draft_reply.strip():
        return True
    return False


def route_ticket(
    ticket_id: str,
    chosen_model: str,
    fallback_model: str,
    decision: Decision,
    det_passed: bool,
) -> RouteDecision:
    if should_fallback(decision, det_passed):
        return RouteDecision(
            ticket_id=ticket_id,
            chosen_model=fallback_model,
            reason="Primary model output failed a confidence check; escalated.",
            fell_back=True,
            fallback_model=fallback_model,
        )
    return RouteDecision(
        ticket_id=ticket_id,
        chosen_model=chosen_model,
        reason="Cheapest model clearing the quality bar handled it directly.",
    )
