from backend.api.emotion_weights import get_emotion_weights

def test_get_emotion_weights():
    emotions = get_emotion_weights("I am happy and excited")
    assert isinstance(emotions, dict)
    assert any(isinstance(v, (int, float)) for v in emotions.values())
