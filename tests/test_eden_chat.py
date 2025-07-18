import pytest
from backend.persona.kai_persona import build_prompt as build_kai_prompt
from backend.persona.eden_persona import build_prompt as build_eden_prompt

def test_kai_build_prompt():
    user_msg = "How are you?"
    history_block = "You: Hi Kai!\nKai: I'm good!\n"
    prompt = build_kai_prompt(user_message=user_msg, history_block=history_block)
    assert isinstance(prompt, str)
    assert "How are you?" in prompt

def test_eden_build_prompt():
    user_msg = "How are you?"
    history_block = "You: Hi Eden!\nEden: Hello dear.\n"
    prompt = build_eden_prompt(user_message=user_msg, history_block=history_block)
    assert isinstance(prompt, str)
    assert "How are you?" in prompt
