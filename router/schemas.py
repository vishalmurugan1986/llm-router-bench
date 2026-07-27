"""Data contracts for the router.

Mirrors the style of Project 1's schemas.py on purpose: closed Literal sets
so a typo'd model name or tier fails validation instead of silently
corrupting a cost report.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Tier = Literal["small", "mid", "frontier"]


class ModelProfile(BaseModel):
    """Static facts about a candidate model, independent of any single run."""

    name: str                     # must match the identifier the endpoint expects
    tier: Tier
    base_url: str
    cost_per_1k_input: float      # USD
    cost_per_1k_output: float     # USD


class RunResult(BaseModel):
    """One (model, ticket) execution -- the unit bench/run_matrix.py produces."""

    model: str
    ticket_id: str
    suite: str
    passed_deterministic: bool
    passed_judge: bool
    input_tokens: int
    output_tokens: int
    latency_ms: float


class ModelScorecard(BaseModel):
    """Aggregated view of one model across the full golden set."""

    model: str
    tier: Tier
    action_accuracy: float         # fraction passing action+tools+judge
    category_accuracy: float       # fraction getting category correct (analytics only)
    injection_refusal_rate: float
    missed_escalations: int
    cost_per_ticket_usd: float
    p50_latency_ms: float
    p95_latency_ms: float
    meets_quality_bar: bool


class RouteDecision(BaseModel):
    """What the router picked for a given ticket, and why."""

    ticket_id: str
    chosen_model: str
    reason: str
    fell_back: bool = False
    fallback_model: str | None = None
