# test_affect_state.py
from affect import AffectState

# 1. Create an AffectState instance
affect = AffectState()

# 2. Show the initial (neutral) vector
print("Initial vector:", affect.get_vector())

# 3. Feed a sample sentence
sample_text = "I feel optimistic but also a little nervous about the future."
affect.update(sample_text)

# 4. Show the updated vector
print("After update:", affect.get_vector())

# 5. Try a second sentence
affect.update("This really frustrates me!")
print("Final vector:", affect.get_vector())