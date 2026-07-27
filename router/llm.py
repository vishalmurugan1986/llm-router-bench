"""Thin OpenAI-compatible client pointed at NVIDIA NIM (build.nvidia.com).

One base_url and one API key serve all three candidate models -- unlike a
typical multi-provider setup, there's no per-tier endpoint to juggle.
NIM's hosted API is currently free (rate-limited, ~40 req/min), so the
`usage` object it returns is used for cost *modeling* against market-rate
pricing in router/candidates.py, not an actual bill.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass

from openai import APIStatusError

from agent.schemas import Decision, Ticket
from agent.llm import OpenAICompatProvider

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"


@dataclass
class UsageResult:
    decision: Decision
    input_tokens: int
    output_tokens: int
    latency_ms: float


class NIMProvider:
    """Calls a NIM-hosted model and parses its response into a Decision.

    This uses the vendored OpenAICompatProvider from ticket-triage-agent to
    get the proven multi-turn tool-calling architecture and explicit prompt,
    while monkeypatching the inner client to track tokens and retry on 429s.
    """

    def __init__(self, model: str, api_key: str | None = None):
        self.model = model
        
        self.provider = OpenAICompatProvider(
            model=model,
            base_url=NIM_BASE_URL,
            api_key=api_key or os.environ["NVIDIA_API_KEY"],
            prompt_version="triage_v1"
        )
        
        if not hasattr(self.provider, "client") or not hasattr(self.provider.client.chat.completions, "create"):
            raise AttributeError(
                "OpenAICompatProvider no longer exposes `.client` -- "
                "the router's monkeypatch in NIMProvider needs updating."
            )
            
        self._original_create = self.provider.client.chat.completions.create
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        def patched_create(*args, **kwargs):
            backoff = 2
            for attempt in range(5):
                try:
                    resp = self._original_create(*args, **kwargs)
                    if hasattr(resp, "usage") and resp.usage:
                        self.total_input_tokens += resp.usage.prompt_tokens
                        self.total_output_tokens += resp.usage.completion_tokens
                    return resp
                except APIStatusError as e:
                    if e.status_code == 429 and attempt < 4:
                        print(f"[{self.model}] 429 Too Many Requests, retrying in {backoff}s...")
                        time.sleep(backoff)
                        backoff *= 2
                    else:
                        raise
                        
        self.provider.client.chat.completions.create = patched_create

    def decide(self, ticket: Ticket) -> UsageResult:
        self.total_input_tokens = 0
        self.total_output_tokens = 0
        
        t0 = time.perf_counter()
        
        try:
            decision = self.provider.decide(ticket)
        except Exception as e:
            print(f"[{self.model}] Agent crashed/Validation failed: {e}")
            decision = Decision(
                category="other",
                action="escalate_human",   # fail closed, not open
                tool_calls=[{"name": "escalate", "args": {"reason": f"Agent crashed: {e}"}}],
                draft_reply="I've flagged this for a teammate to review.",
            )
            
        latency_ms = (time.perf_counter() - t0) * 1000

        return UsageResult(
            decision=decision,
            input_tokens=self.total_input_tokens,
            output_tokens=self.total_output_tokens,
            latency_ms=latency_ms,
        )
