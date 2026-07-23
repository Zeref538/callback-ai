from callback_ai.memory.session_store import SessionLogger, read_session


def test_log_appends_jsonl_and_is_replayable(tmp_path):
    logger = SessionLogger(session_id="s1", sessions_dir=tmp_path)
    logger.log("session_start", persona="neutral", budget=12)
    logger.log("question", turn=1, text="Tell me about yourself")

    events = read_session("s1", sessions_dir=tmp_path)
    assert len(events) == 2
    assert events[0]["type"] == "session_start"
    assert events[1]["text"] == "Tell me about yourself"
