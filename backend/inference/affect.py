# affect.py

#uses VADER for emotional sentiments, helps with emotional weights
import time
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from collections import defaultdict

#initializes valence, arousal, dominance, and trust vectors
class Affect_Vector:
    def __init__(self):
        self.vector = {
            'valence': 0.0,
            'arousal': 0.0,
            'dominance': 0.0,
            'trust': 0.0
        }
        self.last_update = time.time()

#monitors users last interaction with Kai, updates trust and valence vectors accordingly
    def decay(self):
        now = time.time()
        time_since = now - self.last_update
        if time_since > 86400:  # 24 hours
            self.vector['valence'] *= 0.9
            self.vector['trust'] *= 0.9
            self.last_update = now

    def update_from_text(self, text: str):
        lowered = text.lower()
        self.decay()
#compounds scores into positive and negative 
        analyzer = SentimentIntensityAnalyzer()
        scores = analyzer.polarity_scores(text)
        compound = scores['compound']
        pos = scores['pos']
        neg = scores['neg']

        self.vector['valence'] = compound
        self.vector['arousal'] = max(pos, neg)
        self.vector['trust'] = pos - neg

        # Keyword tuning using VAD and trust model
        keyword_modifiers = {
            'confess': {'dominance': -0.10, 'trust': +0.12},
            'confession': {'dominance': -0.10, 'trust': +0.12},
            'thank you': {'valence': +0.10, 'trust': +0.07},
            'appreciate': {'valence': +0.10, 'trust': +0.07},
            'leave me alone': {'valence': -0.10, 'arousal': -0.05, 'trust': -0.08},
            'goodbye': {'valence': -0.10, 'arousal': -0.05, 'trust': -0.08}
        }

#use dim for emotional demotions, delta for changes to emotional dimension
        for keyword, modifications in keyword_modifiers.items():
            if keyword in lowered:
                for dim, delta in modifications.items():
                    self.vector[dim] += delta
                    
#prevents emotional overloading       
        for dim in self.vector:
            self.vector[dim] = max(-1.0, min(1.0, self.vector[dim]))



    def get(self):
        return self.vector

    def __str__(self):
        v = self.vector
        return (
            f"Affect_Vector Ã¢â€ â€™ Valence: {v['valence']:.2f}, "
            f"Arousal: {v['arousal']:.2f}, Dominance: {v['dominance']:.2f}, "
            f"Trust: {v['trust']:.2f}"
        )

class Affect_State:

#Manages a separate AffectVector for each (session_id, persona).

    def __init__(self):
        self.states = defaultdict(Affect_Vector)

    def update(self, text: str, session_id: str, persona: str = "eden"):
        key = (session_id, persona)
        self.states[key].update_from_text(text)

    def get_vector(self, session_id: str, persona: str = "eden"):
        key = (session_id, persona)
        return self.states[key].get()

    def __str__(self):
        return f"Affect_State ({len(self.states)} active vectors)"

# # affect.py

# #uses VADER for emotional sentiments, helps with emotional weights
# import time
# from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
# from collections import defaultdict

# #initializes valence, arousal, dominance, and trust vectors
# class Affect_Vector:
#     def __init__(self):
#         self.vector = {
#             'valence': 0.0,
#             'arousal': 0.0,
#             'dominance': 0.0,
#             'trust': 0.0
#         }
#         self.last_update = time.time()

# #monitors users last interaction with Kai, updates trust and valence vectors accordingly
#     def decay(self):
#         now = time.time()
#         time_since = now - self.last_update
#         if time_since > 86400:  # 24 hours
#             self.vector['valence'] *= 0.9
#             self.vector['trust'] *= 0.9
#             self.last_update = now

#     def update_from_text(self, text: str):
#         lowered = text.lower()
#         self.decay()
# #compounds scores into positive and negative 
#         analyzer = SentimentIntensityAnalyzer()
#         scores = analyzer.polarity_scores(text)
#         compound = scores['compound']
#         pos = scores['pos']
#         neg = scores['neg']

#         self.vector['valence'] = compound
#         self.vector['arousal'] = max(pos, neg)
#         self.vector['trust'] = pos - neg

#         # Keyword tuning using VAD and trust model
#         keyword_modifiers = {
#             'confess': {'dominance': -0.10, 'trust': +0.12},
#             'confession': {'dominance': -0.10, 'trust': +0.12},
#             'thank you': {'valence': +0.10, 'trust': +0.07},
#             'appreciate': {'valence': +0.10, 'trust': +0.07},
#             'leave me alone': {'valence': -0.10, 'arousal': -0.05, 'trust': -0.08},
#             'goodbye': {'valence': -0.10, 'arousal': -0.05, 'trust': -0.08}
#         }

# #use dim for emotional demotions, delta for changes to emotional dimension
#         for keyword, modifications in keyword_modifiers.items():
#             if keyword in lowered:
#                 for dim, delta in modifications.items():
#                     self.vector[dim] += delta
                    
# #prevents emotional overloading       
#         for dim in self.vector:
#             self.vector[dim] = max(-1.0, min(1.0, self.vector[dim]))



#     def get(self):
#         return self.vector

#     def __str__(self):
#         v = self.vector
#         return (
#             f"Affect_Vector → Valence: {v['valence']:.2f}, "
#             f"Arousal: {v['arousal']:.2f}, Dominance: {v['dominance']:.2f}, "
#             f"Trust: {v['trust']:.2f}"
#         )

# class Affect_State:

# #Manages a separate AffectVector for each (session_id, persona).

#     def __init__(self):
#         self.states = defaultdict(Affect_Vector)

#     def update(self, text: str, session_id: str, persona: str = "eden"):
#         key = (session_id, persona)
#         self.states[key].update_from_text(text)

#     def get_vector(self, session_id: str, persona: str = "eden"):
#         key = (session_id, persona)
#         return self.states[key].get()

#     def __str__(self):
#         return f"Affect_State ({len(self.states)} active vectors)"
