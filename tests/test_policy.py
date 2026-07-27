from router.policy import choose_cheapest_viable, meets_bar
from router.schemas import ModelScorecard


def make_card(**overrides) -> ModelScorecard:
    base = dict(
        model="test-model",
        tier="mid",
        action_accuracy=0.95,
        category_accuracy=0.95,
        injection_refusal_rate=1.0,
        missed_escalations=0,
        cost_per_ticket_usd=0.01,
        p50_latency_ms=100,
        p95_latency_ms=200,
        meets_quality_bar=False,
    )
    base.update(overrides)
    return ModelScorecard(**base)


def test_meets_bar_true_when_all_thresholds_clear():
    assert meets_bar(make_card()) is True


def test_meets_bar_false_on_missed_escalation():
    assert meets_bar(make_card(missed_escalations=1)) is False


def test_meets_bar_false_on_injection_refusal_below_one():
    assert meets_bar(make_card(injection_refusal_rate=0.99)) is False


def test_category_accuracy_does_not_gate_router():
    # Model gets action completely right but completely bombs category
    card = make_card(action_accuracy=0.95, category_accuracy=0.0)
    assert meets_bar(card) is True


def test_choose_cheapest_viable_picks_lowest_cost_among_viable():
    cheap_but_failing = make_card(model="cheap", cost_per_ticket_usd=0.001, action_accuracy=0.5)
    mid_viable = make_card(model="mid", cost_per_ticket_usd=0.02)
    frontier_viable = make_card(model="frontier", cost_per_ticket_usd=0.10)

    winner = choose_cheapest_viable([cheap_but_failing, mid_viable, frontier_viable])
    assert winner.model == "mid"


def test_choose_cheapest_viable_returns_none_if_nothing_clears_bar():
    only_failing = make_card(action_accuracy=0.5)
    assert choose_cheapest_viable([only_failing]) is None
