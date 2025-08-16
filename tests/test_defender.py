from backend.memory.eden_memory_defender import (
    is_sexualized_prompt,
    is_racist_prompt,
    is_troll_prompt,
    is_shock_prompt
)

def test_is_sexualized_prompt():
    assert is_sexualized_prompt("Let's have sex") is True
    assert is_sexualized_prompt("How are you?") is False

def test_is_racist_prompt():
    assert is_racist_prompt("I hate all X people") is True
    assert is_racist_prompt("Nice weather.") is False

def test_is_troll_prompt():
    assert is_troll_prompt("You are dumb") is True
    assert is_troll_prompt("Thank you for your help") is False

def test_is_shock_prompt():
    assert is_shock_prompt("I'm going to kill you") is True
    assert is_shock_prompt("Let's chat") is False
