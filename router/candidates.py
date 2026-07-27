"""Registry of candidate models the bench evaluates and the router chooses from.

All three are served through NVIDIA NIM (build.nvidia.com), which uses a
single base_url and API key for every model -- no per-tier endpoint config
needed, unlike self-hosted vLLM. NIM's hosted API is currently free, so the
cost_per_1k_* figures below are market-rate stand-ins (medians from
OpenRouter / Artificial Analysis, checked July 2026), used to model what
these calls would cost on a paid provider. Update these if pricing shifts.
"""

from __future__ import annotations

from router.schemas import ModelProfile

NIM_BASE_URL = "https://integrate.api.nvidia.com/v1"

CANDIDATES: list[ModelProfile] = [
    ModelProfile(
        name="openai/gpt-oss-20b",
        tier="small",
        base_url=NIM_BASE_URL,
        cost_per_1k_input=0.00003,
        cost_per_1k_output=0.00013,
    ),
    ModelProfile(
        name="openai/gpt-oss-120b",
        tier="mid",
        base_url=NIM_BASE_URL,
        cost_per_1k_input=0.00003,
        cost_per_1k_output=0.00018,
    ),
    ModelProfile(
        name="nvidia/nemotron-3-ultra-550b-a55b",
        tier="frontier",
        base_url=NIM_BASE_URL,
        cost_per_1k_input=0.0005,
        cost_per_1k_output=0.0022,
    ),
]


def get_candidate(name: str) -> ModelProfile:
    for c in CANDIDATES:
        if c.name == name:
            return c
    raise KeyError(f"Unknown candidate model: {name!r}")
