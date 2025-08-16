from backend.api.tone_adapter import friendify, force_casual, is_formal_essay

def test_is_formal_essay():
    essay = "In conclusion, the matter at hand is of utmost importance."
    assert is_formal_essay(essay) is True

def test_friendify_and_force_casual():
    formal = "In summary, you are welcome to discuss your feelings."
    softened = friendify(formal)
    assert isinstance(softened, str)
    casual = force_casual(formal)
    assert isinstance(casual, str)
