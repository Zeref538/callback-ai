from callback_ai.memory.delta import compute_delta


def test_compute_delta_against_prior_session():
    delta = compute_delta({"System Design": 0.3}, {"System Design": 0.7, "Communication": 0.8})

    assert delta["System Design"]["previous"] == 0.3
    assert delta["System Design"]["delta"] == 0.7 - 0.3
    assert delta["Communication"]["previous"] is None
    assert delta["Communication"]["delta"] is None
