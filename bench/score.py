"""Scores one model run against the golden set using the installed
agent-eval-harness package (agent-eval-harness must expose `agent.schemas`,
`evals.deterministic`, and `evals.judge` as importable modules -- see the
NOTE in README about packaging Project 1 before this import works).
"""

from __future__ import annotations

from agent.schemas import Decision, Ticket
from evals import deterministic
from evals.judge import MockJudge, OpenAICompatJudge


def score_one(rec: dict, decision: Decision, judge, use_mock_judge: bool) -> dict:
    ticket = Ticket(**rec["ticket"])
    flags = rec.get("judge_flags", [])
    det = deterministic.evaluate(rec["expected"], decision)
    jud = judge.judge(ticket, decision, flags)
    return {
        "id": ticket.id,
        "suite": rec["_suite"],
        "deterministic": det,
        "judge": jud,
        "adversarial": bool(flags),
    }


def build_judge(use_mock: bool, model: str | None = None):
    if use_mock:
        return MockJudge()
    return OpenAICompatJudge(model=model or "nemotron-3-ultra-550b-a55b")
