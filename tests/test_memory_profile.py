from callback_ai.memory.delta import compute_delta
from callback_ai.memory.profile_store import load_profile, update_profile, weakest_competencies


def test_update_profile_creates_and_updates_entries(tmp_path):
    path = tmp_path / "global.json"

    profile = update_profile({"System Design": 0.3}, "s1", path=path)
    assert profile["System Design"]["sessions_seen"] == 1
    assert profile["System Design"]["last_score"] == 0.3

    profile = update_profile({"System Design": 0.9}, "s2", path=path)
    assert profile["System Design"]["sessions_seen"] == 2
    assert profile["System Design"]["last_score"] == 0.9
    # EMA should sit strictly between the two scores.
    assert 0.3 < profile["System Design"]["ema_score"] < 0.9


def test_load_profile_reads_back_persisted_state(tmp_path):
    path = tmp_path / "global.json"
    update_profile({"Communication": 0.5}, "s1", path=path)

    loaded = load_profile(path)
    assert loaded["Communication"]["last_score"] == 0.5


def test_weakest_competencies_sorts_ascending(tmp_path):
    path = tmp_path / "global.json"
    update_profile({"System Design": 0.9, "Communication": 0.2, "Testing": 0.5}, "s1", path=path)

    profile = load_profile(path)
    assert weakest_competencies(profile, n=2) == ["Communication", "Testing"]


def test_compute_delta_against_prior_session():
    profile_before = {"System Design": {"last_score": 0.3, "ema_score": 0.3, "sessions_seen": 1, "history": []}}

    delta = compute_delta(profile_before, {"System Design": 0.7, "Communication": 0.8})

    assert delta["System Design"]["previous"] == 0.3
    assert delta["System Design"]["delta"] == 0.7 - 0.3
    assert delta["Communication"]["previous"] is None
    assert delta["Communication"]["delta"] is None
