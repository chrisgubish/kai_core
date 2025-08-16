import pytest
from backend.inference.affect import Affect_State

def test_affect_state_update_and_get_vector():
    affect = Affect_State()
    session_id = "testsession"
    persona = "kai"
    affect.update("Hello!", session_id=session_id, persona=persona)
    vec = affect.get_vector(session_id=session_id, persona=persona)
    assert isinstance(vec, dict)
    assert "trust" in vec
