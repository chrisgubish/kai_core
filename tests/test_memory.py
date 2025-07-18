from backend.memory.memory_store import Memory_Store

def test_memory_store_save_and_get():
    store = Memory_Store()
    session = "testsession"
    store.save("user", "Hello!", "neutral", ["input"], session_id=session)
    history = store.get_recent(limit=1, session_id=session)
    assert isinstance(history, list)
    assert history[0]["message"] == "Hello!"

def test_memory_store_clear():
    store = Memory_Store()
    session = "testsession"
    store.save("user", "Test", "neutral", ["input"], session_id=session)
    store.clear(session)
    history = store.get_recent(session_id=session)
    assert len(history) == 0
