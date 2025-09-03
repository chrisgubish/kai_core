# enhanced_journal_processor.py
"""
Enhanced emotion processing system for journal entries
Replaces SimpleEmotionProcessor with better detection capabilities
"""

import re
import time
from typing import Dict, List, Tuple, Optional
from collections import Counter
from datetime import datetime
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

class EnhancedJournalProcessor:
    """
    Improved emotion detection for journal entries
    Combines multiple approaches for better accuracy
    """
    
    def __init__(self, use_transformers: bool = False):
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.use_transformers = use_transformers
        
        # Initialize transformer models if requested
        if use_transformers:
            try:
                from transformers import pipeline
                self.emotion_pipeline = pipeline(
                    "text-classification",
                    model="j-hartmann/emotion-english-distilroberta-base",
                    device=-1  # Use CPU for compatibility
                )
                print("Transformer model loaded successfully")
            except Exception as e:
                print(f"Failed to load transformer model: {e}")
                print("Falling back to pattern-based detection")
                self.use_transformers = False
        
        # Comprehensive emotion patterns
        self.emotion_patterns = {
            'happy': {
                'direct': ['happy', 'joy', 'joyful', 'excited', 'thrilled', 'elated', 
                          'cheerful', 'delighted', 'ecstatic', 'euphoric', 'blissful'],
                'phrases': ['feel great', 'on top of the world', 'over the moon', 
                           'walking on air', 'cloud nine', 'best day ever'],
                'indicators': ['laughing', 'smiling', 'celebrating', 'amazing', 
                              'wonderful', 'fantastic', 'awesome', 'perfect'],
                'contexts': ['accomplished', 'achieved', 'succeeded', 'won', 'celebration']
            },
            'sad': {
                'direct': ['sad', 'depressed', 'down', 'blue', 'melancholy', 
                          'heartbroken', 'dejected', 'despondent', 'gloomy'],
                'phrases': ['feeling down', 'in the dumps', 'heavy heart', 
                           'want to cry', 'feel empty', 'rock bottom'],
                'indicators': ['crying', 'tears', 'lonely', 'hopeless', 'grief', 
                              'loss', 'missing', 'disappointed'],
                'contexts': ['failed', 'lost', 'ended', 'goodbye', 'rejection']
            },
            'mad': {
                'direct': ['angry', 'mad', 'furious', 'irate', 'livid', 'enraged', 
                          'pissed', 'outraged', 'incensed'],
                'phrases': ['seeing red', 'boiling mad', 'fed up', 'had enough', 
                           'last straw', 'driving me crazy'],
                'indicators': ['frustrated', 'annoyed', 'irritated', 'rage', 
                              'fury', 'heated', 'steaming'],
                'contexts': ['unfair', 'injustice', 'betrayed', 'lied', 'cheated']
            },
            'anxious': {
                'direct': ['anxious', 'worried', 'nervous', 'stressed', 'panicked', 
                          'uneasy', 'apprehensive', 'tense'],
                'phrases': ['on edge', 'butterflies in stomach', 'can\'t stop thinking', 
                           'mind racing', 'what if', 'overthinking'],
                'indicators': ['panic', 'overwhelmed', 'tension', 'restless', 
                              'insomnia', 'racing thoughts'],
                'contexts': ['presentation', 'interview', 'test', 'deadline', 'unknown']
            },
            'fear': {
                'direct': ['afraid', 'scared', 'terrified', 'frightened', 'fearful', 
                          'petrified', 'horrified'],
                'phrases': ['scared stiff', 'heart pounding', 'blood ran cold', 
                           'shaking with fear', 'paralyzed with fear'],
                'indicators': ['nightmare', 'phobia', 'trembling', 'avoiding', 
                              'hiding', 'dread'],
                'contexts': ['danger', 'threat', 'horror', 'disaster', 'accident']
            },
            'calm': {
                'direct': ['calm', 'peaceful', 'relaxed', 'serene', 'tranquil', 
                          'content', 'centered', 'balanced'],
                'phrases': ['at peace', 'feeling zen', 'completely relaxed', 
                           'inner peace', 'clear mind'],
                'indicators': ['meditated', 'breathing deeply', 'stillness', 
                              'harmony', 'grounded'],
                'contexts': ['meditation', 'nature', 'quiet', 'solitude', 'reflection']
            }
        }
        
        # Intensity modifiers
        self.intensity_words = {
            'extreme': ['extremely', 'incredibly', 'absolutely', 'completely', 
                       'totally', 'utterly', 'beyond', 'overwhelming'],
            'high': ['very', 'really', 'quite', 'pretty', 'fairly', 'rather', 
                    'intensely', 'deeply'],
            'moderate': ['somewhat', 'kind of', 'sort of', 'a bit', 'a little', 
                        'moderately'],
            'mild': ['slightly', 'barely', 'hardly', 'just a touch', 'mildly']
        }
        
        # Negation patterns
        self.negation_patterns = [
            r"not\s+(\w+)", r"no\s+(\w+)", r"never\s+(\w+)", r"don't\s+(\w+)",
            r"can't\s+(\w+)", r"won't\s+(\w+)", r"shouldn't\s+(\w+)"
        ]
    
    def analyze_journal_entry(self, text: str) -> Dict:
        """
        Comprehensive analysis of journal entry
        Returns detailed emotion analysis
        """
        
        # Clean and prepare text
        cleaned_text = self._preprocess_text(text)
        
        # Get VADER baseline
        vader_scores = self.sentiment_analyzer.polarity_scores(text)
        
        # Pattern-based emotion detection
        emotion_scores = self._detect_emotions_by_patterns(cleaned_text)
        
        # Transformer-based detection (if available)
        if self.use_transformers:
            transformer_emotions = self._detect_emotions_by_transformer(text)
            emotion_scores = self._combine_emotion_scores(emotion_scores, transformer_emotions)
        
        # Handle negations
        emotion_scores = self._handle_negations(text, emotion_scores)
        
        # Determine primary emotion
        primary_emotion, confidence = self._get_primary_emotion(emotion_scores, vader_scores)
        
        # Calculate intensity
        intensity = self._calculate_intensity(text, primary_emotion, vader_scores)
        
        # Determine mood category
        mood_category = self._get_mood_category(primary_emotion, intensity, vader_scores['compound'])
        
        return {
            'primary_emotion': primary_emotion,
            'intensity': round(intensity, 2),
            'confidence': round(confidence, 2),
            'emotion_scores': {k: round(v, 2) for k, v in emotion_scores.items()},
            'sentiment_scores': vader_scores,
            'mood_category': mood_category,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'analysis_method': 'transformer' if self.use_transformers else 'pattern_enhanced'
        }
    
    def _preprocess_text(self, text: str) -> str:
        """Clean and prepare text for analysis"""
        # Convert to lowercase
        text_lower = text.lower()
        
        # Handle contractions
        contractions = {
            "i'm": "i am", "you're": "you are", "it's": "it is",
            "can't": "cannot", "won't": "will not", "don't": "do not",
            "isn't": "is not", "wasn't": "was not", "weren't": "were not"
        }
        
        for contraction, expansion in contractions.items():
            text_lower = text_lower.replace(contraction, expansion)
        
        return text_lower
    
    def _detect_emotions_by_patterns(self, text: str) -> Dict[str, float]:
        """Detect emotions using pattern matching"""
        emotion_scores = {}
        
        for emotion, patterns in self.emotion_patterns.items():
            score = 0.0
            
            # Direct word matches (highest weight)
            for word in patterns['direct']:
                if word in text:
                    score += 1.0
            
            # Phrase matches (high weight)
            for phrase in patterns['phrases']:
                if phrase in text:
                    score += 0.8
            
            # Indicator matches (medium weight)
            for indicator in patterns['indicators']:
                if indicator in text:
                    score += 0.6
            
            # Context matches (lower weight)
            for context in patterns['contexts']:
                if context in text:
                    score += 0.4
            
            if score > 0:
                emotion_scores[emotion] = score
        
        # Normalize scores
        if emotion_scores:
            max_score = max(emotion_scores.values())
            emotion_scores = {k: v/max_score for k, v in emotion_scores.items()}
        
        return emotion_scores
    
    def _detect_emotions_by_transformer(self, text: str) -> Dict[str, float]:
        """Detect emotions using transformer model"""
        try:
            predictions = self.emotion_pipeline(text)
            
            # Map model labels to our emotions
            label_mapping = {
                'joy': 'happy',
                'sadness': 'sad',
                'anger': 'mad',
                'fear': 'fear',
                'surprise': 'anxious',  # Map surprise to anxious
                'disgust': 'mad',       # Map disgust to mad
                'love': 'happy',        # Map love to happy
                'optimism': 'happy',
                'pessimism': 'sad'
            }
            
            emotion_scores = {}
            for pred in predictions:
                label = pred['label'].lower()
                mapped_emotion = label_mapping.get(label, 'neutral')
                score = pred['score']
                
                if mapped_emotion in emotion_scores:
                    emotion_scores[mapped_emotion] = max(emotion_scores[mapped_emotion], score)
                else:
                    emotion_scores[mapped_emotion] = score
            
            return emotion_scores
            
        except Exception as e:
            print(f"Transformer detection failed: {e}")
            return {}
    
    def _combine_emotion_scores(self, pattern_scores: Dict, transformer_scores: Dict) -> Dict:
        """Combine pattern and transformer emotion scores"""
        combined = {}
        all_emotions = set(pattern_scores.keys()) | set(transformer_scores.keys())
        
        for emotion in all_emotions:
            pattern_score = pattern_scores.get(emotion, 0)
            transformer_score = transformer_scores.get(emotion, 0)
            
            # Weight transformer scores higher if available
            if transformer_score > 0:
                combined[emotion] = (transformer_score * 0.7) + (pattern_score * 0.3)
            else:
                combined[emotion] = pattern_score
        
        return combined
    
    def _handle_negations(self, text: str, emotion_scores: Dict) -> Dict:
        """Handle negations in text that might flip emotions"""
        text_lower = text.lower()
        
        # Check for negation patterns
        negated_emotions = set()
        for pattern in self.negation_patterns:
            matches = re.findall(pattern, text_lower)
            for match in matches:
                # Check if the negated word relates to an emotion
                for emotion, patterns in self.emotion_patterns.items():
                    if match in patterns['direct'] or match in patterns['indicators']:
                        negated_emotions.add(emotion)
        
        # Reduce scores for negated emotions
        for emotion in negated_emotions:
            if emotion in emotion_scores:
                emotion_scores[emotion] *= 0.3  # Significantly reduce but don't eliminate
        
        return emotion_scores
    
    def _get_primary_emotion(self, emotion_scores: Dict, vader_scores: Dict) -> Tuple[str, float]:
        """Determine primary emotion and confidence"""
        
        if not emotion_scores:
            # Fallback to VADER-based emotion
            compound = vader_scores['compound']
            if compound >= 0.3:
                return 'happy', abs(compound)
            elif compound <= -0.3:
                return 'sad', abs(compound)
            else:
                return 'neutral', 0.5
        
        # Get emotion with highest score
        primary_emotion = max(emotion_scores, key=emotion_scores.get)
        confidence = emotion_scores[primary_emotion]
        
        # Require minimum confidence threshold
        if confidence < 0.3:
            return 'neutral', confidence
        
        return primary_emotion, confidence
    
    def _calculate_intensity(self, text: str, emotion: str, vader_scores: Dict) -> float:
        """Calculate emotional intensity"""
        
        # Base intensity from VADER
        base_intensity = abs(vader_scores['compound'])
        
        # Intensity modifiers from text
        intensity_boost = 0.0
        text_lower = text.lower()
        
        for level, words in self.intensity_words.items():
            for word in words:
                if word in text_lower:
                    if level == 'extreme':
                        intensity_boost = max(intensity_boost, 0.4)
                    elif level == 'high':
                        intensity_boost = max(intensity_boost, 0.3)
                    elif level == 'moderate':
                        intensity_boost = max(intensity_boost, 0.2)
                    elif level == 'mild':
                        intensity_boost = max(intensity_boost, 0.1)
        
        # Punctuation indicators
        exclamation_boost = min(0.3, text.count('!') * 0.1)
        question_boost = min(0.2, text.count('?') * 0.05)
        
        # Capitalization indicators
        caps_words = len(re.findall(r'\b[A-Z]{2,}\b', text))
        caps_boost = min(0.2, caps_words * 0.1)
        
        # Repeated characters (sooo, reallyyy)
        repeated_boost = min(0.15, len(re.findall(r'(.)\1{2,}', text.lower())) * 0.05)
        
        # Combine all factors
        final_intensity = base_intensity + intensity_boost + exclamation_boost + question_boost + caps_boost + repeated_boost
        
        return max(0.1, min(1.0, final_intensity))
    
    def _get_mood_category(self, emotion: str, intensity: float, compound: float) -> str:
        """Determine overall mood category"""
        
        positive_emotions = ['happy', 'calm']
        negative_emotions = ['sad', 'mad', 'anxious', 'fear']
        
        if emotion in positive_emotions:
            if intensity >= 0.7:
                return 'very_positive'
            elif intensity >= 0.4:
                return 'positive'
            else:
                return 'neutral'
        elif emotion in negative_emotions:
            if intensity >= 0.7:
                return 'very_negative'
            elif intensity >= 0.4:
                return 'negative'
            else:
                return 'neutral'
        else:
            # Use compound score for neutral emotions
            if compound >= 0.3:
                return 'positive'
            elif compound <= -0.3:
                return 'negative'
            else:
                return 'neutral'

# Testing and validation functions
class JournalAnalysisTester:
    """Test the enhanced journal processor with various inputs"""
    
    def __init__(self, processor: EnhancedJournalProcessor):
        self.processor = processor
    
    def run_comprehensive_tests(self):
        """Run comprehensive tests on the emotion processor"""
        
        test_cases = [
            # Clear emotions
            ("I'm absolutely thrilled about my promotion! This is the best day ever!", "happy"),
            ("I'm completely devastated by this loss. Nothing will ever be the same.", "sad"),
            ("I'm so incredibly angry about this injustice! This is totally unfair!", "mad"),
            ("I'm really worried about tomorrow's presentation. What if everything goes wrong?", "anxious"),
            ("I'm absolutely terrified of what might happen next. I can't stop shaking.", "fear"),
            ("I feel completely at peace with this decision. Everything is in harmony.", "calm"),
            
            # Modern language patterns
            ("lowkey stressed about this situation ngl", "anxious"),
            ("I'm literally dead from exhaustion but happy about the results", "happy"),
            ("This whole thing is giving me major anxiety vibes", "anxious"),
            ("So mad rn, this is absolutely ridiculous!!!", "mad"),
            
            # Complex/mixed emotions
            ("I'm happy about the opportunity but nervous about the responsibility", "anxious"),
            ("Sad to leave but excited for the new adventure", "happy"),
            ("Not feeling great today, kinda down and unmotivated", "sad"),
            
            # Negations
            ("I'm not angry, just disappointed", "sad"),
            ("Not feeling anxious anymore, pretty calm actually", "calm"),
            ("I don't feel sad, more like frustrated", "mad"),
            
            # Edge cases
            ("Everything is fine.", "neutral"),
            ("Today was okay I guess", "neutral"),
            ("", "neutral")
        ]
        
        print("Running Enhanced Journal Processor Tests")
        print("=" * 50)
        
        correct_predictions = 0
        total_tests = len(test_cases)
        
        for i, (text, expected_emotion) in enumerate(test_cases, 1):
            result = self.processor.analyze_journal_entry(text)
            predicted_emotion = result['primary_emotion']
            
            is_correct = predicted_emotion == expected_emotion
            if is_correct:
                correct_predictions += 1
            
            print(f"\nTest {i}: {'✓' if is_correct else '✗'}")
            print(f"Text: {text[:60]}{'...' if len(text) > 60 else ''}")
            print(f"Expected: {expected_emotion} | Predicted: {predicted_emotion}")
            print(f"Intensity: {result['intensity']:.2f} | Confidence: {result['confidence']:.2f}")
            
            if result['emotion_scores']:
                print(f"All emotions: {result['emotion_scores']}")
        
        accuracy = (correct_predictions / total_tests) * 100
        print(f"\n{'='*50}")
        print(f"Overall Accuracy: {accuracy:.1f}% ({correct_predictions}/{total_tests})")
        print(f"Analysis Method: {result.get('analysis_method', 'unknown')}")
        
        return accuracy

# Example usage and testing
if __name__ == "__main__":
    # Test with pattern-based detection
    print("Testing with Pattern-Based Detection:")
    processor_patterns = EnhancedJournalProcessor(use_transformers=False)
    tester_patterns = JournalAnalysisTester(processor_patterns)
    accuracy_patterns = tester_patterns.run_comprehensive_tests()
    
    print("\n" + "="*60)
    
    # Test with transformer if available
    print("Testing with Transformer Models:")
    processor_transformers = EnhancedJournalProcessor(use_transformers=True)
    tester_transformers = JournalAnalysisTester(processor_transformers)
    accuracy_transformers = tester_transformers.run_comprehensive_tests()
    
    print(f"\n{'='*60}")
    print("COMPARISON SUMMARY:")
    print(f"Pattern-Based Accuracy: {accuracy_patterns:.1f}%")
    print(f"Transformer Accuracy: {accuracy_transformers:.1f}%")