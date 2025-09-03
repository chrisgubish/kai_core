# journal_api.py
"""
Enhanced emotional journal platform with BERTweet emotion detection.
Core functionality: Journal entry -> BERTweet emotional analysis -> Dashboard visualization
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json
import uuid
import re
import torch
from pathlib import Path
from collections import Counter

# Reuse existing components
from backend.inference.affect import Affect_State
from backend.memory.memory_store import Memory_Store
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Transformer models
from transformers import pipeline, AutoTokenizer, AutoModelForSequenceClassification

# Authentication components
from passlib.context import CryptContext
from jose import JWTError, jwt
import os
from dotenv import load_dotenv

load_dotenv()
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

pwd_context = CryptContext(schemes=["bcrypt"], deprecated='auto')
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

app = FastAPI(title="BERTweet Enhanced Emotional Journal Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
affect_analyzer = Affect_State()
memory_store = Memory_Store()
sentiment_analyzer = SentimentIntensityAnalyzer()
users_db = {}

# Pydantic models
class JournalEntry(BaseModel):
    content: str
    title: Optional[str] = None

class User(BaseModel):
    username: str
    email: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

# Authentication functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise credentials_exception
    except JWTError:
        raise credentials_exception
    
    user = users_db.get(username)
    if user is None:
        raise credentials_exception
    return user

# BERTweet-based emotion processing
class BERTweetEmotionProcessor:
    """
    BERTweet-based emotion detection for modern language patterns
    Optimized for social media and contemporary language use
    """
    
    def __init__(self):
        self.sentiment_analyzer = SentimentIntensityAnalyzer()
        self.bertweet_model = None
        self.fallback_model = None
        
        # Load BERTweet model
        self._load_bertweet_model()
        
        # Fallback pattern matching for edge cases
        self.emotion_patterns = {
            'happy': {
                'direct': ['happy', 'joy', 'joyful', 'excited', 'thrilled', 'elated', 
                          'cheerful', 'delighted', 'ecstatic', 'euphoric', 'blissful', 'blessed'],
                'modern': ['lit', 'fire', 'amazing', 'awesome', 'incredible', 'perfect', 'best day ever'],
                'social': ['so happy', 'cant even', 'literally the best', 'living my best life']
            },
            'sad': {
                'direct': ['sad', 'depressed', 'down', 'blue', 'melancholy', 'heartbroken', 
                          'dejected', 'despondent', 'gloomy', 'devastated'],
                'modern': ['dead inside', 'broken', 'shattered', 'crushed', 'destroyed'],
                'social': ['big sad', 'sad vibes', 'not okay', 'cant deal']
            },
            'mad': {
                'direct': ['angry', 'mad', 'furious', 'irate', 'livid', 'enraged', 
                          'pissed', 'outraged', 'incensed'],
                'modern': ['heated', 'triggered', 'done with', 'over it', 'fed up'],
                'social': ['big mad', 'so done', 'absolutely not', 'are you kidding me']
            },
            'anxious': {
                'direct': ['anxious', 'worried', 'nervous', 'stressed', 'panicked', 
                          'uneasy', 'apprehensive', 'tense', 'overwhelmed'],
                'modern': ['lowkey stressed', 'highkey worried', 'freaking out', 'losing it'],
                'social': ['stress levels', 'panic mode', 'cant handle', 'too much']
            },
            'fear': {
                'direct': ['afraid', 'scared', 'terrified', 'frightened', 'fearful', 
                          'petrified', 'horrified'],
                'modern': ['shook', 'spooked', 'terrifying', 'nightmare fuel'],
                'social': ['so scared', 'actually terrified', 'worst fear', 'heart stopped']
            },
            'calm': {
                'direct': ['calm', 'peaceful', 'relaxed', 'serene', 'tranquil', 
                          'content', 'centered', 'balanced'],
                'modern': ['zen', 'chill', 'good vibes', 'at peace', 'grounded'],
                'social': ['feeling zen', 'totally calm', 'inner peace', 'so peaceful']
            }
        }
        
        # Modern language intensity modifiers
        self.intensity_modifiers = {
            'extreme': ['literally', 'absolutely', 'completely', 'totally', 'utterly', 
                       'beyond', 'cant even', 'so much', 'way too'],
            'high': ['really', 'very', 'super', 'hella', 'mad', 'lowkey', 'highkey', 
                    'pretty', 'quite', 'really really'],
            'moderate': ['kinda', 'sorta', 'somewhat', 'a bit', 'a little', 'kind of'],
            'mild': ['slightly', 'barely', 'just a touch', 'mildly']
        }
    
    def _load_bertweet_model(self):
        """Load BERTweet model for emotion detection"""
        try:
            print("Loading BERTweet model for emotion detection...")
            
            # Primary BERTweet model (optimized for Twitter/social media)
            self.bertweet_model = pipeline(
                "text-classification",
                model="cardiffnlp/twitter-roberta-base-emotion",
                device=0 if torch.cuda.is_available() else -1
            )
            print("BERTweet model loaded successfully")
            
        except Exception as e:
            print(f"Failed to load BERTweet model: {e}")
            print("Attempting to load fallback DistilRoBERTa model...")
            
            try:
                # Fallback to DistilRoBERTa if BERTweet fails
                self.fallback_model = pipeline(
                    "text-classification",
                    model="j-hartmann/emotion-english-distilroberta-base",
                    device=0 if torch.cuda.is_available() else -1
                )
                print("Fallback DistilRoBERTa model loaded")
                
            except Exception as e2:
                print(f"Failed to load fallback model: {e2}")
                print("WARNING: No transformer models available. Using pattern matching only.")
    
    def analyze_journal_entry(self, text: str) -> Dict:
        """
        Comprehensive analysis using BERTweet and pattern matching
        """
        
        # Preprocess text for social media patterns
        processed_text = self._preprocess_social_media_text(text)
        
        # Get VADER baseline sentiment
        vader_scores = self.sentiment_analyzer.polarity_scores(text)
        
        # BERTweet emotion detection
        bertweet_emotions = {}
        if self.bertweet_model:
            bertweet_emotions = self._bertweet_prediction(processed_text)
        elif self.fallback_model:
            bertweet_emotions = self._fallback_prediction(processed_text)
        
        # Pattern-based emotion detection for validation
        pattern_emotions = self._pattern_detection(text.lower())
        
        # Combine BERTweet and pattern results
        final_emotions = self._combine_predictions(bertweet_emotions, pattern_emotions)
        
        # Handle negations in text
        final_emotions = self._handle_negations(text, final_emotions)
        
        # Determine primary emotion
        primary_emotion, confidence = self._get_primary_emotion(final_emotions, vader_scores)
        
        # Calculate intensity using modern language patterns
        intensity = self._calculate_modern_intensity(text, vader_scores)
        
        # Determine mood category
        mood_category = self._get_mood_category(primary_emotion, intensity, vader_scores['compound'])
        
        return {
            'primary_emotion': primary_emotion,
            'intensity': round(intensity, 2),
            'confidence': round(confidence, 2),
            'emotion_scores': {k: round(v, 2) for k, v in final_emotions.items()},
            'sentiment_scores': vader_scores,
            'mood_category': mood_category,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'analysis_method': 'bertweet' if self.bertweet_model else 'fallback_distilroberta' if self.fallback_model else 'pattern_only'
        }
    
    def _preprocess_social_media_text(self, text: str) -> str:
        """
        Preprocess text to handle social media and modern language patterns
        """
        
        # Handle repeated characters (sooo -> soo, reallyyy -> reallyy)
        text = re.sub(r'(.)\1{3,}', r'\1\1', text)
        
        # Expand common social media abbreviations
        social_expansions = {
            'ngl': 'not gonna lie',
            'tbh': 'to be honest', 
            'tbf': 'to be fair',
            'omg': 'oh my god',
            'omfg': 'oh my f***ing god',
            'wtf': 'what the f***',
            'lol': 'laugh out loud',
            'lmao': 'laughing my a** off',
            'rofl': 'rolling on floor laughing',
            'rn': 'right now',
            'af': 'as f***',
            'fr': 'for real',
            'irl': 'in real life',
            'lowkey': 'somewhat',
            'highkey': 'really',
            'deadass': 'seriously',
            'periodt': 'period',
            'no cap': 'no lie',
            'bet': 'okay',
            'say less': 'I understand',
            'its giving': 'it seems like',
            'slay': 'amazing',
            'periodt': 'absolutely'
        }
        
        # Replace abbreviations
        words = text.split()
        processed_words = []
        
        for word in words:
            # Clean punctuation for lookup
            clean_word = re.sub(r'[^\w\s]', '', word.lower())
            
            if clean_word in social_expansions:
                processed_words.append(social_expansions[clean_word])
            else:
                processed_words.append(word)
        
        processed_text = ' '.join(processed_words)
        
        # Handle emoji text representations
        emoji_text = {
            ':)': 'happy',
            ':-)': 'happy',
            ':(': 'sad',
            ':-(': 'sad',
            ':D': 'very happy',
            ':-D': 'very happy',
            ':P': 'playful',
            ':-P': 'playful',
            ':/': 'confused',
            ':-/': 'confused',
            '>:(': 'angry',
            '>:-(': 'angry'
        }
        
        for emoji, emotion in emoji_text.items():
            processed_text = processed_text.replace(emoji, f' {emotion} ')
        
        return processed_text
    
    def _bertweet_prediction(self, text: str) -> Dict[str, float]:
        """Get emotion predictions from BERTweet"""
        try:
            predictions = self.bertweet_model(text)
            
            # Map BERTweet emotion labels to our categories
            emotion_mapping = {
                'joy': 'happy',
                'optimism': 'happy',
                'love': 'happy',
                'sadness': 'sad',
                'pessimism': 'sad',
                'grief': 'sad',
                'anger': 'mad',
                'annoyance': 'mad',
                'disapproval': 'mad',
                'fear': 'fear',
                'nervousness': 'anxious',
                'surprise': 'anxious',
                'confusion': 'anxious',
                'neutral': 'calm',
                'approval': 'calm',
                'relief': 'calm',
                'trust': 'calm',
                'admiration': 'happy',
                'excitement': 'happy',
                'gratitude': 'happy',
                'pride': 'happy',
                'caring': 'happy',
                'curiosity': 'calm',
                'desire': 'anxious',
                'disappointment': 'sad',
                'disapproval': 'mad',
                'disgust': 'mad',
                'embarrassment': 'anxious',
                'remorse': 'sad',
                'realization': 'calm'
            }
            
            emotion_scores = {}
            for pred in predictions:
                label = pred['label'].lower()
                mapped_emotion = emotion_mapping.get(label, 'neutral')
                score = pred['score']
                
                if mapped_emotion in emotion_scores:
                    emotion_scores[mapped_emotion] = max(emotion_scores[mapped_emotion], score)
                else:
                    emotion_scores[mapped_emotion] = score
            
            return emotion_scores
            
        except Exception as e:
            print(f"BERTweet prediction failed: {e}")
            return {}
    
    def _fallback_prediction(self, text: str) -> Dict[str, float]:
        """Fallback DistilRoBERTa prediction if BERTweet unavailable"""
        try:
            predictions = self.fallback_model(text)
            
            emotion_mapping = {
                'joy': 'happy',
                'sadness': 'sad',
                'anger': 'mad',
                'fear': 'fear',
                'surprise': 'anxious',
                'disgust': 'mad',
                'love': 'happy',
                'optimism': 'happy',
                'pessimism': 'sad'
            }
            
            emotion_scores = {}
            for pred in predictions:
                label = pred['label'].lower()
                mapped_emotion = emotion_mapping.get(label, 'neutral')
                score = pred['score']
                
                if mapped_emotion in emotion_scores:
                    emotion_scores[mapped_emotion] = max(emotion_scores[mapped_emotion], score)
                else:
                    emotion_scores[mapped_emotion] = score
            
            return emotion_scores
            
        except Exception as e:
            print(f"Fallback prediction failed: {e}")
            return {}
    
    def _pattern_detection(self, text: str) -> Dict[str, float]:
        """Enhanced pattern matching including modern language"""
        emotion_scores = {}
        
        for emotion, pattern_groups in self.emotion_patterns.items():
            score = 0.0
            
            # Check all pattern types
            for pattern_type, patterns in pattern_groups.items():
                for pattern in patterns:
                    if pattern in text:
                        # Weight different pattern types
                        if pattern_type == 'direct':
                            score += 1.0
                        elif pattern_type == 'modern':
                            score += 0.9  # High weight for modern language
                        elif pattern_type == 'social':
                            score += 0.8  # High weight for social media language
            
            if score > 0:
                emotion_scores[emotion] = score
        
        # Normalize scores
        if emotion_scores:
            max_score = max(emotion_scores.values())
            emotion_scores = {k: v/max_score for k, v in emotion_scores.items()}
        
        return emotion_scores
    
    def _combine_predictions(self, bertweet_scores: Dict, pattern_scores: Dict) -> Dict[str, float]:
        """Combine BERTweet and pattern predictions"""
        
        if not bertweet_scores:
            return pattern_scores
        
        if not pattern_scores:
            return bertweet_scores
        
        # Weighted combination (favor BERTweet for modern language understanding)
        combined = {}
        all_emotions = set(bertweet_scores.keys()) | set(pattern_scores.keys())
        
        for emotion in all_emotions:
            bertweet_score = bertweet_scores.get(emotion, 0)
            pattern_score = pattern_scores.get(emotion, 0)
            
            # BERTweet gets higher weight (75%) for better modern language understanding
            combined[emotion] = (bertweet_score * 0.75) + (pattern_score * 0.25)
        
        return combined
    
    def _handle_negations(self, text: str, emotion_scores: Dict) -> Dict:
        """Handle negation patterns that might flip emotions"""
        text_lower = text.lower()
        
        # Modern negation patterns
        negation_patterns = [
            r"not\s+(\w+)", r"no\s+(\w+)", r"never\s+(\w+)", r"don't\s+(\w+)",
            r"can't\s+(\w+)", r"won't\s+(\w+)", r"shouldn't\s+(\w+)",
            r"not really\s+(\w+)", r"definitely not\s+(\w+)", r"absolutely not\s+(\w+)"
        ]
        
        negated_words = set()
        for pattern in negation_patterns:
            matches = re.findall(pattern, text_lower)
            negated_words.update(matches)
        
        # Reduce scores for negated emotions
        for emotion, patterns in self.emotion_patterns.items():
            for pattern_group in patterns.values():
                if any(word in negated_words for word in pattern_group):
                    if emotion in emotion_scores:
                        emotion_scores[emotion] *= 0.3
        
        return emotion_scores
    
    def _get_primary_emotion(self, emotion_scores: Dict, vader_scores: Dict) -> tuple[str, float]:
        """Determine primary emotion and confidence"""
        
        if not emotion_scores:
            # VADER-based fallback
            compound = vader_scores['compound']
            if compound >= 0.3:
                return 'happy', abs(compound)
            elif compound <= -0.3:
                return 'sad', abs(compound)
            else:
                return 'neutral', 0.5
        
        primary_emotion = max(emotion_scores, key=emotion_scores.get)
        confidence = emotion_scores[primary_emotion]
        
        # Minimum confidence threshold
        if confidence < 0.2:
            return 'neutral', confidence
        
        return primary_emotion, confidence
    
    def _calculate_modern_intensity(self, text: str, vader_scores: Dict) -> float:
        """Calculate intensity considering modern language patterns"""
        
        # Base intensity from VADER
        base_intensity = abs(vader_scores['compound'])
        
        # Modern language intensity indicators
        intensity_boost = 0.0
        text_lower = text.lower()
        
        # Check intensity modifiers
        for level, modifiers in self.intensity_modifiers.items():
            for modifier in modifiers:
                if modifier in text_lower:
                    if level == 'extreme':
                        intensity_boost = max(intensity_boost, 0.4)
                    elif level == 'high':
                        intensity_boost = max(intensity_boost, 0.3)
                    elif level == 'moderate':
                        intensity_boost = max(intensity_boost, 0.2)
                    elif level == 'mild':
                        intensity_boost = max(intensity_boost, 0.1)
        
        # Punctuation intensity (modern usage)
        exclamation_boost = min(0.4, text.count('!') * 0.15)  # Higher weight for exclamations
        question_boost = min(0.2, text.count('?') * 0.1)
        
        # All caps words (social media emphasis)
        caps_words = len(re.findall(r'\b[A-Z]{2,}\b', text))
        caps_boost = min(0.3, caps_words * 0.15)
        
        # Character repetition (sooo, reallyyy)
        repeated_chars = len(re.findall(r'(.)\1{2,}', text.lower()))
        repeat_boost = min(0.2, repeated_chars * 0.1)
        
        # Modern intensity phrases
        modern_intensity = [
            'literally', 'actually', 'honestly', 'seriously', 'genuinely',
            'cant even', 'so much', 'way too', 'hella', 'mad', 'deadass'
        ]
        modern_boost = min(0.2, sum(0.05 for phrase in modern_intensity if phrase in text_lower))
        
        # Combine all factors
        final_intensity = base_intensity + intensity_boost + exclamation_boost + question_boost + caps_boost + repeat_boost + modern_boost
        
        return max(0.1, min(1.0, final_intensity))
    
    def _get_mood_category(self, emotion: str, intensity: float, compound: float) -> str:
        """Determine mood category"""
        
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
            if compound >= 0.3:
                return 'positive'
            elif compound <= -0.3:
                return 'negative'
            else:
                return 'neutral'

# Initialize BERTweet emotion processor
emotion_processor = BERTweetEmotionProcessor()

# Authentication endpoints
@app.post("/register")
async def register(user_data: UserCreate):
    if user_data.username in users_db:
        raise HTTPException(status_code=400, detail="Username already registered")
    
    hashed_password = get_password_hash(user_data.password)
    user_id = str(uuid.uuid4())
    users_db[user_data.username] = {
        "id": user_id,
        "username": user_data.username,
        "email": user_data.email,
        "hashed_password": hashed_password,
        "created_at": datetime.utcnow().isoformat()
    }
    return {"message": "User registered successfully", "user_id": user_id}

@app.post("/token")
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    user = users_db.get(form_data.username)
    if not user or not verify_password(form_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user["username"]}, expires_delta=access_token_expires
    )
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": user["id"]
    }

# BERTweet-enhanced journal entry endpoint
@app.post("/journal/entry")
async def create_journal_entry(entry: JournalEntry, current_user: dict = Depends(get_current_user)):
    """Process journal entry with BERTweet emotional analysis"""
    
    # Analyze with BERTweet processor
    emotional_analysis = emotion_processor.analyze_journal_entry(entry.content)
    
    # Store entry with BERTweet analysis
    session_id = f"user_{current_user['id']}"
    memory_store.save(
        speaker="user",
        message=entry.content,
        emotion=emotional_analysis['primary_emotion'],
        tags=[
            f"emotion:{emotional_analysis['primary_emotion']}",
            f"intensity:{emotional_analysis['intensity']}",
            f"confidence:{emotional_analysis['confidence']}",
            f"mood:{emotional_analysis['mood_category']}",
            f"method:{emotional_analysis['analysis_method']}",
            "journal_entry",
            "bertweet_analyzed"
        ],
        session_id=session_id
    )
    
    return {
        "status": "success",
        "analysis": emotional_analysis,
        "entry_id": str(uuid.uuid4()),
        "timestamp": datetime.utcnow().isoformat()
    }

# BERTweet testing endpoint
@app.post("/journal/test-emotion")
async def test_emotion_detection(test_data: dict, current_user: dict = Depends(get_current_user)):
    """Test BERTweet emotion detection with sample texts"""
    
    test_text = test_data.get('text', '')
    if not test_text:
        raise HTTPException(status_code=400, detail="No text provided for testing")
    
    result = emotion_processor.analyze_journal_entry(test_text)
    
    return {
        "input_text": test_text,
        "analysis": result,
        "timestamp": datetime.utcnow().isoformat()
    }

# Enhanced dashboard with BERTweet metrics
@app.get("/dashboard/overview")
async def get_dashboard_overview(current_user: dict = Depends(get_current_user)):
    """Get BERTweet-enhanced emotional analysis overview"""
    session_id = f"user_{current_user['id']}"
    
    recent_entries = memory_store.get_recent(
        limit=100, 
        session_id=session_id,
        tag_filter=["journal_entry"]
    )
    
    if not recent_entries:
        return {"message": "No journal entries found"}
    
    # Process entries with BERTweet metrics
    emotion_counts = {}
    confidence_scores = []
    intensity_scores = []
    daily_summaries = {}
    method_usage = {}
    bertweet_entries = 0
    
    for entry in recent_entries:
        entry_emotion = entry.get('emotion', 'neutral')
        entry_date = entry['timestamp'][:10]
        
        # Count emotions
        emotion_counts[entry_emotion] = emotion_counts.get(entry_emotion, 0) + 1
        
        # Check if analyzed with BERTweet
        if "bertweet_analyzed" in entry.get('tags', []):
            bertweet_entries += 1
        
        # Extract metrics from tags
        for tag in entry.get('tags', []):
            if tag.startswith('confidence:'):
                confidence_scores.append(float(tag.split(':')[1]))
            elif tag.startswith('intensity:'):
                intensity_scores.append(float(tag.split(':')[1]))
            elif tag.startswith('method:'):
                method = tag.split(':')[1]
                method_usage[method] = method_usage.get(method, 0) + 1
        
        # Daily summaries
        if entry_date not in daily_summaries:
            daily_summaries[entry_date] = {
                'entries': 0,
                'emotions': [],
                'avg_intensity': 0,
                'avg_confidence': 0
            }
        
        daily_summaries[entry_date]['entries'] += 1
        daily_summaries[entry_date]['emotions'].append(entry_emotion)
    
    # Calculate averages
    avg_confidence = sum(confidence_scores) / len(confidence_scores) if confidence_scores else 0
    avg_intensity = sum(intensity_scores) / len(intensity_scores) if intensity_scores else 0
    
    return {
        "total_entries": len(recent_entries),
        "emotion_breakdown": emotion_counts,
        "daily_summaries": daily_summaries,
        "most_common_emotion": max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral",
        "analysis_period": "last_30_days",
        "bertweet_metrics": {
            "bertweet_analyzed_entries": bertweet_entries,
            "bertweet_coverage": f"{(bertweet_entries/len(recent_entries)*100):.1f}%" if recent_entries else "0%",
            "average_confidence": round(avg_confidence, 2),
            "average_intensity": round(avg_intensity, 2),
            "analysis_methods_used": method_usage
        }
    }

# Topic analysis endpoint
@app.get("/dashboard/topics")
async def get_topic_analysis(current_user: dict = Depends(get_current_user)):
    """Analyze emotional patterns around topics using BERTweet insights"""
    session_id = f"user_{current_user['id']}"
    
    entries = memory_store.get_recent(
        limit=100,
        session_id=session_id,
        tag_filter=["journal_entry"]
    )
    
    # Topic extraction with modern language awareness
    topic_emotions = {}
    modern_topics = ['work', 'family', 'friends', 'relationship', 'health', 'money', 'school', 'social media', 'dating', 'career']
    
    for entry in entries:
        text = entry['message'].lower()
        entry_emotion = entry.get('emotion', 'neutral')
        
        for topic in modern_topics:
            if topic in text:
                if topic not in topic_emotions:
                    topic_emotions[topic] = {}
                topic_emotions[topic][entry_emotion] = topic_emotions[topic].get(entry_emotion, 0) + 1
    
    return {
        "topic_emotional_patterns": topic_emotions,
        "analysis_note": "Based on BERTweet-enhanced keyword detection in journal entries"
    }

# BERTweet comprehensive testing endpoint
@app.get("/journal/run-tests")
async def run_bertweet_tests(current_user: dict = Depends(get_current_user)):
    """Run comprehensive tests on BERTweet emotion detection"""
    
    # Modern language test cases optimized for BERTweet
    test_cases = [
        # Standard emotions
        ("I'm absolutely thrilled about my promotion! This is the best day ever!", "happy"),
        ("I'm completely devastated by this loss. Nothing will ever be the same.", "sad"),
        ("I'm so incredibly angry about this injustice! This is totally unfair!", "mad"),
        ("I'm really worried about tomorrow's presentation. What if everything goes wrong?", "anxious"),
        ("I'm absolutely terrified of what might happen next. I can't stop shaking.", "fear"),
        ("I feel completely at peace with this decision. Everything is in harmony.", "calm"),
        
        # Modern/social media language (BERTweet's strength)
        ("lowkey stressed about this situation ngl", "anxious"),
        ("I'm literally dead from exhaustion but happy about the results", "happy"),
        ("This whole thing is giving me major anxiety vibes", "anxious"),
        ("So mad rn, this is absolutely ridiculous!!!", "mad"),
        ("actually terrified about what's coming next tbh", "fear"),
        ("feeling blessed and grateful today, everything is perfect", "happy"),
        ("big sad energy today, can't even deal", "sad"),
        ("totally zen mode after that meditation session", "calm"),
        ("deadass panicking about this deadline fr", "anxious"),
        ("this is literally the worst thing ever, I can't", "sad"),
        
        # Negations
        ("I'm not angry, just disappointed", "sad"),
        ("Not feeling anxious anymore, pretty calm actually", "calm"),
        ("definitely not happy about this situation", "mad"),
        
        # Edge cases
        ("Everything is fine.", "neutral"),
        ("Today was okay I guess", "neutral")
    ]
    
    correct_predictions = 0
    total_tests = len(test_cases)
    detailed_results = []
    
    for text, expected_emotion in test_cases:
        result = emotion_processor.analyze_journal_entry(text)
        predicted_emotion = result['primary_emotion']
        
        is_correct = predicted_emotion == expected_emotion
        if is_correct:
            correct_predictions += 1
        
        detailed_results.append({
            "text": text,
            "expected": expected_emotion,
            "predicted": predicted_emotion,
            "correct": is_correct,
            "confidence": result['confidence'],
            "intensity": result['intensity'],
            "method": result['analysis_method'],
            "all_emotions": result['emotion_scores']
        })
    
    accuracy = (correct_predictions / total_tests) * 100
    
    return {
        "test_summary": {
            "total_tests": total_tests,
            "correct_predictions": correct_predictions,
            "accuracy": f"{accuracy:.1f}%",
            "model_used": emotion_processor.bertweet_model is not None,
            "bertweet_available": emotion_processor.bertweet_model is not None,
            "fallback_used": emotion_processor.fallback_model is not None and emotion_processor.bertweet_model is None
        },
        "detailed_results": detailed_results,
        "modern_language_performance": {
            "modern_cases": [r for r in detailed_results if any(phrase in r['text'].lower() 
                           for phrase in ['lowkey', 'ngl', 'literally', 'rn', 'tbh', 'deadass', 'fr'])],
            "modern_accuracy": f"{sum(1 for r in detailed_results if any(phrase in r['text'].lower() for phrase in ['lowkey', 'ngl', 'literally', 'rn', 'tbh', 'deadass', 'fr']) and r['correct']) / max(1, sum(1 for r in detailed_results if any(phrase in r['text'].lower() for phrase in ['lowkey', 'ngl', 'literally', 'rn', 'tbh', 'deadass', 'fr']))) * 100:.1f}%"
        },
        "timestamp": datetime.utcnow().isoformat()
    }

# Model status endpoint
@app.get("/journal/model-status")
async def get_model_status(current_user: dict = Depends(get_current_user)):
    """Get current model status and capabilities"""
    
    return {
        "bertweet_loaded": emotion_processor.bertweet_model is not None,
        "fallback_loaded": emotion_processor.fallback_model is not None,
        "current_method": emotion_processor.bertweet_model and "bertweet" or emotion_processor.fallback_model and "distilroberta" or "pattern_only",
        "gpu_available": torch.cuda.is_available(),
        "device_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
        "recommended_action": "BERTweet loaded successfully" if emotion_processor.bertweet_model else "Consider installing transformers for better accuracy",
        "supported_emotions": ["happy", "sad", "mad", "anxious", "fear", "calm", "neutral"],
        "modern_language_support": emotion_processor.bertweet_model is not None,
        "timestamp": datetime.utcnow().isoformat()
    }

# Health check and info endpoints
@app.get("/")
def root():
    return {
        "message": "BERTweet Enhanced Emotional Journal Platform API", 
        "version": "2.0-bertweet", 
        "status": "active",
        "features": [
            "bertweet_emotion_detection",
            "modern_language_support", 
            "social_media_preprocessing",
            "pattern_matching_fallback",
            "confidence_scoring"
        ],
        "model_status": {
            "primary": "BERTweet (cardiffnlp/twitter-roberta-base-emotion)",
            "fallback": "DistilRoBERTa",
            "pattern_matching": "Enhanced with modern language"
        }
    }

@app.get("/health")
def health_check():
    return {
        "status": "healthy", 
        "bertweet_available": emotion_processor.bertweet_model is not None,
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# # journal_platform.py
# """
# Simplified emotional journal platform using existing codebase components.
# Core functionality: Journal entry -> Emotional analysis -> Dashboard visualization
# """

# from fastapi import FastAPI, Request, Depends, HTTPException, status
# from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
# from fastapi.middleware.cors import CORSMiddleware
# from fastapi.responses import HTMLResponse
# from fastapi.staticfiles import StaticFiles
# from pydantic import BaseModel
# from datetime import datetime, timedelta
# from typing import List, Dict, Optional
# import json
# import uuid
# from pathlib import Path

# # Reuse existing components
# from backend.inference.affect import Affect_State
# from backend.memory.memory_store import Memory_Store
# from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# # Authentication components (reused from persona_api.py)
# from passlib.context import CryptContext
# from jose import JWTError, jwt
# import os
# from dotenv import load_dotenv

# load_dotenv()
# SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-here")
# ALGORITHM = "HS256"
# ACCESS_TOKEN_EXPIRE_MINUTES = 30

# pwd_context = CryptContext(schemes=["bcrypt"], deprecated='auto')
# oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# app = FastAPI(title="Emotional Journal Platform")

# app.add_middleware(
#     CORSMiddleware,
#     allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
#     allow_credentials=True,
#     allow_methods=["*"],
#     allow_headers=["*"],
# )

# # Initialize components
# affect_analyzer = Affect_State()
# memory_store = Memory_Store()
# sentiment_analyzer = SentimentIntensityAnalyzer()
# users_db = {}

# # Pydantic models
# class JournalEntry(BaseModel):
#     content: str
#     title: Optional[str] = None

# class User(BaseModel):
#     username: str
#     email: Optional[str] = None

# class UserCreate(BaseModel):
#     username: str
#     password: str
#     email: Optional[str] = None

# # Authentication functions (reused)
# def verify_password(plain_password, hashed_password):
#     return pwd_context.verify(plain_password, hashed_password)

# def get_password_hash(password):
#     return pwd_context.hash(password)

# def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
#     to_encode = data.copy()
#     if expires_delta:
#         expire = datetime.utcnow() + expires_delta
#     else:
#         expire = datetime.utcnow() + timedelta(minutes=15)
#     to_encode.update({"exp": expire})
#     encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
#     return encoded_jwt

# async def get_current_user(token: str = Depends(oauth2_scheme)):
#     credentials_exception = HTTPException(
#         status_code=status.HTTP_401_UNAUTHORIZED,
#         detail="Could not validate credentials",
#         headers={"WWW-Authenticate": "Bearer"},
#     )
#     try:
#         payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
#         username: str = payload.get("sub")
#         if username is None:
#             raise credentials_exception
#     except JWTError:
#         raise credentials_exception
    
#     user = users_db.get(username)
#     if user is None:
#         raise credentials_exception
#     return user

# # Simplified emotion processing
# class SimpleEmotionProcessor:
#     def __init__(self):
#         self.sentiment_analyzer = SentimentIntensityAnalyzer()
        
#     def analyze_journal_entry(self, text: str) -> Dict:
#         """Simplified emotional analysis for user-friendly display"""
#         # VADER sentiment analysis
#         sentiment_scores = self.sentiment_analyzer.polarity_scores(text)
        
#         # Simplified emotion categories
#         primary_emotion = self._get_primary_emotion(sentiment_scores, text)
        
#         # Emotional intensity (0-1 scale)
#         intensity = abs(sentiment_scores['compound'])
        
#         return {
#             'primary_emotion': primary_emotion,
#             'intensity': round(intensity, 2),
#             'sentiment_scores': sentiment_scores,
#             'mood_category': self._get_mood_category(sentiment_scores['compound']),
#             'analysis_timestamp': datetime.utcnow().isoformat()
#         }
    
#     def _get_primary_emotion(self, sentiment_scores: Dict, text: str) -> str:
#         """Determine primary emotion from text analysis"""
#         text_lower = text.lower()
        
#         # Keyword-based emotion detection for simplicity
#         emotion_keywords = {
#             'happy': ['happy', 'joy', 'excited', 'great', 'awesome', 'wonderful', 'love', 'amazing'],
#             'sad': ['sad', 'depressed', 'down', 'upset', 'hurt', 'cry', 'lonely', 'grief'],
#             'mad': ['angry', 'mad', 'furious', 'annoyed', 'frustrated', 'irritated', 'rage'],
#             'anxious': ['worried', 'anxious', 'nervous', 'scared', 'fear', 'stress', 'panic'],
#             'calm': ['calm', 'peaceful', 'relaxed', 'content', 'serene', 'tranquil']
#         }
        
#         # Count keyword matches
#         emotion_scores = {}
#         for emotion, keywords in emotion_keywords.items():
#             score = sum(1 for keyword in keywords if keyword in text_lower)
#             if score > 0:
#                 emotion_scores[emotion] = score
        
#         # If keyword matching found emotions, use highest scoring
#         if emotion_scores:
#             return max(emotion_scores, key=emotion_scores.get)
        
#         # Fallback to sentiment-based categorization
#         compound = sentiment_scores['compound']
#         if compound >= 0.3:
#             return 'happy'
#         elif compound <= -0.3:
#             return 'sad'
#         else:
#             return 'neutral'
    
#     def _get_mood_category(self, compound_score: float) -> str:
#         """Convert compound score to simple mood category"""
#         if compound_score >= 0.5:
#             return 'very_positive'
#         elif compound_score >= 0.1:
#             return 'positive'
#         elif compound_score >= -0.1:
#             return 'neutral'
#         elif compound_score >= -0.5:
#             return 'negative'
#         else:
#             return 'very_negative'

# emotion_processor = SimpleEmotionProcessor()

# # Authentication endpoints
# @app.post("/register")
# async def register(user_data: UserCreate):
#     if user_data.username in users_db:
#         raise HTTPException(status_code=400, detail="Username already registered")
    
#     hashed_password = get_password_hash(user_data.password)
#     user_id = str(uuid.uuid4())
#     users_db[user_data.username] = {
#         "id": user_id,
#         "username": user_data.username,
#         "email": user_data.email,
#         "hashed_password": hashed_password,
#         "created_at": datetime.utcnow().isoformat()
#     }
#     return {"message": "User registered successfully", "user_id": user_id}

# @app.post("/token")
# async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
#     user = users_db.get(form_data.username)
#     if not user or not verify_password(form_data.password, user["hashed_password"]):
#         raise HTTPException(
#             status_code=status.HTTP_401_UNAUTHORIZED,
#             detail="Incorrect username or password",
#             headers={"WWW-Authenticate": "Bearer"},
#         )
    
#     access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
#     access_token = create_access_token(
#         data={"sub": user["username"]}, expires_delta=access_token_expires
#     )
#     return {
#         "access_token": access_token,
#         "token_type": "bearer",
#         "user_id": user["id"]
#     }

# # Journal entry endpoint
# @app.post("/journal/entry")
# async def create_journal_entry(entry: JournalEntry, current_user: dict = Depends(get_current_user)):
#     """Process journal entry and return emotional analysis"""
    
#     # Analyze emotional content
#     emotional_analysis = emotion_processor.analyze_journal_entry(entry.content)
    
#     # Store entry with analysis
#     session_id = f"user_{current_user['id']}"
#     memory_store.save(
#         speaker="user",
#         message=entry.content,
#         emotion=emotional_analysis['primary_emotion'],
#         tags=[
#             f"emotion:{emotional_analysis['primary_emotion']}",
#             f"intensity:{emotional_analysis['intensity']}",
#             f"mood:{emotional_analysis['mood_category']}",
#             "journal_entry"
#         ],
#         session_id=session_id
#     )
    
#     return {
#         "status": "success",
#         "analysis": emotional_analysis,
#         "entry_id": str(uuid.uuid4()),
#         "timestamp": datetime.utcnow().isoformat()
#     }

# # Dashboard data endpoint
# @app.get("/dashboard/overview")
# async def get_dashboard_overview(current_user: dict = Depends(get_current_user)):
#     """Get emotional analysis overview for dashboard"""
#     session_id = f"user_{current_user['id']}"
    
#     # Get recent entries (last 30 days)
#     recent_entries = memory_store.get_recent(
#         limit=100, 
#         session_id=session_id,
#         tag_filter=["journal_entry"]
#     )
    
#     if not recent_entries:
#         return {"message": "No journal entries found"}
    
#     # Process entries for dashboard
#     emotion_counts = {}
#     mood_trends = []
#     daily_summaries = {}
    
#     for entry in recent_entries:
#         # Count emotions
#         for tag in entry.get('tags', []):
#             if tag.startswith('emotion:'):
#                 emotion = tag.split(':')[1]
#                 emotion_counts[emotion] = emotion_counts.get(emotion, 0) + 1
        
#         # Daily summaries
#         entry_date = entry['timestamp'][:10]  # YYYY-MM-DD
#         if entry_date not in daily_summaries:
#             daily_summaries[entry_date] = {
#                 'entries': 0,
#                 'emotions': [],
#                 'avg_intensity': 0
#             }
        
#         daily_summaries[entry_date]['entries'] += 1
        
#         # Extract emotion and intensity from tags
#         for tag in entry.get('tags', []):
#             if tag.startswith('emotion:'):
#                 daily_summaries[entry_date]['emotions'].append(tag.split(':')[1])
#             elif tag.startswith('intensity:'):
#                 intensity = float(tag.split(':')[1])
#                 current_avg = daily_summaries[entry_date]['avg_intensity']
#                 count = daily_summaries[entry_date]['entries']
#                 daily_summaries[entry_date]['avg_intensity'] = (current_avg * (count-1) + intensity) / count
    
#     return {
#         "total_entries": len(recent_entries),
#         "emotion_breakdown": emotion_counts,
#         "daily_summaries": daily_summaries,
#         "most_common_emotion": max(emotion_counts, key=emotion_counts.get) if emotion_counts else "neutral",
#         "analysis_period": "last_30_days"
#     }

# # Topic analysis endpoint
# @app.get("/dashboard/topics")
# async def get_topic_analysis(current_user: dict = Depends(get_current_user)):
#     """Analyze emotional patterns around specific topics/keywords"""
#     session_id = f"user_{current_user['id']}"
    
#     entries = memory_store.get_recent(
#         limit=100,
#         session_id=session_id,
#         tag_filter=["journal_entry"]
#     )
    
#     # Simple keyword-based topic extraction
#     topic_emotions = {}
#     common_topics = ['work', 'family', 'friends', 'relationship', 'health', 'money', 'school']
    
#     for entry in entries:
#         text = entry['message'].lower()
#         entry_emotion = entry.get('emotion', 'neutral')
        
#         for topic in common_topics:
#             if topic in text:
#                 if topic not in topic_emotions:
#                     topic_emotions[topic] = {}
#                 topic_emotions[topic][entry_emotion] = topic_emotions[topic].get(entry_emotion, 0) + 1
    
#     return {
#         "topic_emotional_patterns": topic_emotions,
#         "analysis_note": "Based on keyword detection in journal entries"
#     }

# # Health check and info
# @app.get("/")
# def root():
#     return {"message": "Emotional Journal Platform API", "version": "1.0", "status": "active"}

# @app.get("/health")
# def health_check():
#     return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}

# # # Static file serving for dashboard frontend
# # app.mount("/static", StaticFiles(directory="static"), name="static")

# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run(app, host="0.0.0.0", port=8000)