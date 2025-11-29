# journal_api.py
"""
DistilRoBERTa emotional gaming platform with native emotion detection.
Core functionality: Gaming platform -> Journal entry -> DistilRoBERTa emotional analysis -> Data collection 
-> emotion-based gameplay using user emotional sentiment from entries
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from pathlib import Path
from collections import Counter
import logging
import re

# Transformer models
from transformers import pipeline

# Authentication components
from passlib.context import CryptContext
from jose import JWTError, jwt, ExpiredSignatureError
import os
from dotenv import load_dotenv

#Rate limiting
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

#database components (connected to FastAPI server)
from backend.models.database import get_db, User as DBUser, JournalEntry as DBJournalEntry
from sqlalchemy.orm import Session

#Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Weather mapping for Unity using UniStorm weather system
EMOTION_WEATHER_MAP = {
    'joy': {
        'weather': 'Clear',
        'multiplier': 1.0,
        'description': 'Sunny clear skies - joyful emotional state'
    },
    'neutral': {
        'weather': 'Mostly Clear',
        'multiplier': 0.5,
        'description': 'Balanced weather - neutral emotional state'
    },
    'sadness': {
        'weather': 'Rain',
        'multiplier': 0.8,
        'description': 'Gentle rain - processing sadness'
    },
    'anger': {
        'weather': 'Thunderstorm',
        'multiplier': 1.2,
        'description': 'Intense thunderstorm - high anger intensity'
    },
    'fear': {
        'weather': 'Foggy',
        'multiplier': 0.9,
        'description': 'Dense fog - uncertainty and fear'
    },
    'surprise': {
        'weather': 'Partly Cloudy',
        'multiplier': 0.7,
        'description': 'Dynamic weather - unexpected emotions'
    },
    'disgust': {
        'weather': 'Overcast',
        'multiplier': 0.6,
        'description': 'Heavy overcast - aversion and disgust'
    }
}

#Environment configuration
ENV_PATH = Path(__file__).resolve().parents[2] / ".env"   # two levels up
load_dotenv(dotenv_path=ENV_PATH)
SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not found in .env file")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60

# Password hashing
pwd_context = CryptContext(
    schemes=["bcrypt"], 
    deprecated="auto", 
    bcrypt__rounds=12
)
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

#FastAPI app
app = FastAPI(title="DistilRoBERTa Emotional Gaming Platform")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)



# Pydantic models
class JournalEntryInput(BaseModel):
    content: str
    title: Optional[str] = None

class UserCreate(BaseModel):
    username: str
    password: str
    email: Optional[str] = None

class EmotionAnalyzer:
    """
    Emotion analysis engine for Kai gaming platform.
    
    Primary Functions:
        - Detects 7 core emotions from journal text entries
        - Maps emotions to dimensional affect ratings (VAD model)
        - Provides gameplay parameters (combat stats, weather effects)
    
    Technical Architecture:
        Model: j-hartmann/emotion-english-distilroberta-base
               - Pre-trained on 416,809 emotion-labeled texts
               - 7 emotion classes: anger, disgust, fear, joy, neutral, sadness, surprise
               - Returns: emotion label + confidence score (0.0-1.0)
        
        VAD Mapping: Russell's Circumplex Model of Affect (1980)
               - Valence: Positive/negative dimension (-1.0 to +1.0)
               - Arousal: Energy/activation dimension (0.0 to 1.0)
               - Dominance: Not currently used (reserved for future expansion)
               
               Note: Model outputs emotion labels only; VAD scores are derived
               via fixed mappings validated by 40+ years of psychology research.
    
    Design Rationale:
        Fixed VAD mappings (vs. model predictions) chosen because:
        1. Scientific consensus exists (anger is always high-arousal negative)
        2. Faster inference (no additional model calls)
        3. Consistent gameplay (same emotion = same effects)
        4. Tunable per user demographic (cultural differences)
    
    Future Enhancements:
        - Personalized VAD calibration based on user's historical patterns
        - Multi-emotion detection (mixed emotional states)
        - Temporal emotion tracking (mood trends over time)
    
    References:
        Russell, J. A. (1980). A circumplex model of affect. 
        Journal of Personality and Social Psychology, 39(6), 1161-1178.
        
    Last Updated: 2025-11-26
    """
    
    def __init__(self):
        self.model = None
        self.model_name = None
        self.last_error = None
        self.native_emotions = []
        self.emotion_definitions = {}
        
        self._load_model()
        self._initialize_emotion_definitions()
    
    def _load_model(self):
        """Load j-hartmann emotion model for accurate emotion detection"""
        try:
            logger.info("Loading j-hartmann emotion model")
            
            self.model = pipeline(
                "text-classification",
                model="j-hartmann/emotion-english-distilroberta-base",
                device=-1,  # CPU for stability
                return_all_scores=True  # Get all emotions with scores
            )
            
            # Test to discover the model's native emotion vocabulary
            test_phrase = "I am happy and excited"
            
            # Get a sample prediction to understand the structure
            test_result = self.model(test_phrase)
            
            # Extract emotions from the prediction structure
            all_emotions = set()
            if isinstance(test_result, list) and len(test_result) > 0:
                # test_result is a list containing predictions for each input
                predictions = test_result[0] if isinstance(test_result[0], list) else test_result
                for pred in predictions:
                    if isinstance(pred, dict) and 'label' in pred:
                        all_emotions.add(pred['label'])
            
            self.native_emotions = sorted(list(all_emotions))
            self.model_name = "j-hartmann/emotion-english-distilroberta-base"
            logger.info(f"Model loaded! Emotions: {self.native_emotions}")
            
        except Exception as e:
            print(f"Failed to load emotion model: {e}", exc_info=True)
            self.last_error = str(e)
            # Set default emotions if model fails to load (j-hartmann model emotions)
            self.native_emotions = ['anger', 'disgust', 'fear', 'joy', 'neutral', 'sadness', 'surprise']
            self.model_name = "j-hartmann/emotion-english-distilroberta-base (failed)"
    
    def _initialize_emotion_definitions(self):
        """Define characteristics of each native emotion for environmental mapping"""
        self.emotion_definitions = {
            # Positive emotions
            'joy': {'valence': 0.9, 'arousal': 0.7, 'category': 'positive', 'intensity': 'high'},
            
            # Negative emotions
            'anger': {'valence': -0.8, 'arousal': 0.9, 'category': 'negative', 'intensity': 'high'},
            'sadness': {'valence': -0.8, 'arousal': 0.2, 'category': 'negative', 'intensity': 'medium'},
            'fear': {'valence': -0.7, 'arousal': 0.8, 'category': 'negative', 'intensity': 'high'},
            'disgust': {'valence': -0.6, 'arousal': 0.5, 'category': 'negative', 'intensity': 'medium'},
            
            # Neutral/Complex emotions
            'neutral': {'valence': 0.0, 'arousal': 0.2, 'category': 'neutral', 'intensity': 'low'},
            'surprise': {'valence': 0.0, 'arousal': 0.8, 'category': 'neutral', 'intensity': 'high'},
        }
    
    def analyze_journal_entry(self, text: str, debug: bool = False) -> Dict:
        """
        Emotion analysis using j-hartmann model
        Returns all emotions with their confidence scores
        """
        
        if not self.model:
            return self._no_model_response(text)
        
        try:
            # Get ALL emotion predictions
            predictions = self.model(text)
            
            # Handle the prediction structure correctly
            if isinstance(predictions, list) and len(predictions) > 0:
                # predictions is a list, get the first (and only) element
                emotion_scores_list = predictions[0] if isinstance(predictions[0], list) else predictions
            else:
                emotion_scores_list = predictions
            
            # Find the primary emotion (highest confidence)
            top_prediction = max(emotion_scores_list, key=lambda x: x['score'])
            primary_emotion = top_prediction['label']
            primary_confidence = top_prediction['score']
            
            # Create comprehensive emotion scores dictionary
            emotion_scores = {pred['label']: pred['score'] for pred in emotion_scores_list}
            
            # Get emotion characteristics for environmental mapping
            emotion_characteristics = self.emotion_definitions.get(
                primary_emotion, 
                {'valence': 0.0, 'arousal': 0.5, 'category': 'neutral', 'intensity': 'medium'}
            )
            
            # Calculate overall intensity from model confidence
            intensity = primary_confidence
            
            # Enhanced mood categorization using native emotions
            mood_category = self._get_detailed_mood_category(primary_emotion, primary_confidence, emotion_characteristics)
            
            result = {
                'primary_emotion': primary_emotion,
                'intensity': round(intensity, 3),
                'confidence': round(primary_confidence, 3),
                'emotion_scores': {k: round(v, 4) for k, v in emotion_scores.items()},
                'emotion_characteristics': emotion_characteristics,
                'mood_category': mood_category,
                'valence': emotion_characteristics['valence'],
                'arousal': emotion_characteristics['arousal'],
                'analysis_timestamp': datetime.utcnow().isoformat(),
                'analysis_method': 'j_hartmann_distilroberta',
                'total_emotions_detected': len(emotion_scores_list),
                'secondary_emotions': sorted(
                    [(pred['label'], pred['score']) for pred in emotion_scores_list if pred['label'] != primary_emotion],
                    key=lambda x: x[1], reverse=True
                )[:5],
            }
        
            #Add debug info if requested
            if debug:
                result['debug_info'] = {
                    'text_analyzed': text,
                    'model_name': self.model_name,
                    'native_emotion_count': len(self.native_emotions),
                    'text_length': len(text),
                    'emotion_diversity': len([p for p in emotion_scores_list if p['score'] > 0.1])
                }
            
            return result
        
        except Exception as e:
            logger.error(f"Emotion prediction failed: {e}")
            return self._no_model_response(text, str(e))

    def _get_detailed_mood_category(self, emotion: str, confidence: float, characteristics: Dict) -> str:
        """Enhanced mood categorization using emotion characteristics"""
        
        valence = characteristics['valence']
        arousal = characteristics['arousal']
        intensity = characteristics['intensity']
        
        # Create nuanced mood categories based on valence, arousal, and intensity
        if valence >= 0.6:  # Positive emotions
            if arousal >= 0.7 and intensity == 'high':
                return 'euphoric'
            elif arousal >= 0.5:
                return 'energized_positive'
            else:
                return 'calm_positive'
        elif valence <= -0.6:  # Negative emotions
            if arousal >= 0.7 and intensity == 'high':
                return 'intense_negative'
            elif arousal >= 0.5:
                return 'agitated_negative'
            else:
                return 'withdrawn_negative'
        else:  # Neutral range
            if arousal >= 0.6:
                return 'activated_neutral'
            else:
                return 'calm_neutral'
    
    def _no_model_response(self, text: str, error_msg: str = None) -> Dict:
        """Response when model is not available"""
        return {
            'primary_emotion': 'unknown',
            'intensity': 0.0,
            'confidence': 0.0,
            'emotion_scores': {},
            'emotion_characteristics': {'valence': 0.0, 'arousal': 0.0, 'category': 'unknown', 'intensity': 'none'},
            'mood_category': 'unknown',
            'valence': 0.0,
            'arousal': 0.0,
            'analysis_timestamp': datetime.utcnow().isoformat(),
            'analysis_method': 'no_model',
            'total_emotions_detected': 0,
            'secondary_emotions': [],
            'debug_info': {
                'text_analyzed': text,
                'error': error_msg or self.last_error or "Model not loaded",
                'model_status': 'unavailable'
            }
        }
    
    def get_native_emotions_list(self) -> List[str]:
        """Get the complete list of native emotions this model can detect"""
        return self.native_emotions
    
    def get_emotion_characteristics(self, emotion: str) -> Dict:
        """Get characteristics for a specific emotion (for environmental mapping)"""
        return self.emotion_definitions.get(emotion, {
            'valence': 0.0, 'arousal': 0.5, 'category': 'neutral', 'intensity': 'medium'
        })
    
    def get_status(self) -> Dict:
        """Comprehensive processor status"""
        return {
            'model_loaded': self.model is not None,
            'model_name': self.model_name,
            'native_emotions_count': len(self.native_emotions),
            'native_emotions': self.native_emotions,
            'emotion_definitions_loaded': len(self.emotion_definitions),
            'last_error': self.last_error,
            'approach': 'j_hartmann_7_emotions',
            'capabilities': {
                'granular_emotion_detection': True,
                'environmental_mapping': True,
                'individual_personalization': True,
                'emotion_characteristics': True
            }
        }

# Initialize the DistilRoBERTa emotion processor
emotion_processor = EmotionAnalyzer()

# Authentication functions
def verify_password(plain_password: str, hashed_password: str) -> bool:
    #verify password against hash
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    #Hash password using bcrypt
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None):
    #Create JWT access token
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

async def get_current_user(
        token: str = Depends(oauth2_scheme),
        db: Session = Depends(get_db)
) -> DBUser:
    """
    Validate JWT token and return current user from database
    """
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
        
    except ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"}
        )
    except JWTError as e:
        logger.warning(f"JWT decode failed: {e}")
        raise credentials_exception
    
    #Query user from PostgreSQL
    user = db.query(DBUser).filter(DBUser.username == username).first()
    if user is None:
        raise credentials_exception

    return user


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.get("/")
async def root():
    # Health check endpoint
    return {
        "message": "DistilRoBERTa Native Emotion Journal Platform API", 
        "version": "1.0-distilroberta", 
        "status": "active",
        "features": [
            "distilroberta_emotion_detection",
            "7_core_emotions", 
            "granular_emotional_analytics",
            "environmental_mapping_ready",
            "individual_personalization",
            "valence_arousal_dimensions"
        ],
        "emotion_model": {
            "name": emotion_processor.model_name,
            "native_emotions_count": len(emotion_processor.native_emotions),
            "approach": "mapped_model_output_via_VAD",
            "data_collection": "high_granularity_emotional_data"
        }
    }

@app.get("/health")
@limiter.limit("10/minute")
async def health_check(db: Session = Depends(get_db)):
    """
    Health check with database connectivity test
    """
    try:
        db.Execute("SELECT 1")

        model_status = "healthy" if emotion_processor else "unhealthy"


        return {
            "status": "healthy", 
            "model_available": emotion_processor.model is not None,
            "model_name": emotion_processor.model_name,
            "native_emotions_loaded": len(emotion_processor.native_emotions),
            "last_error": emotion_processor.last_error,
            "timestamp": datetime.utcnow().isoformat()
        }
    
    except Exception as e:
        logger.error(f"Health check failed: {e}")
        raise HTTPException(status_code=503, detail="Service unhealthy")

# -----------------------------------------------------------------------------
# Authentication Endpoints
# -----------------------------------------------------------------------------

@app.post("/register")
@limiter.limit("5/hour")
async def register(
    user_data: UserCreate,
    db: Session = Depends(get_db)
):
    """
    Register new user account
    """
    #Validate input
    if not user_data.username or len(user_data.username) < 3:
        raise HTTPException(
            status_code=400,
            detail="Username must be at least 3 characters"
        )
    
    if len(user_data.username) > 50:
        raise HTTPException(
            status_code=400,
            detail="Username cannot exceed 50 characters"
        )
    
    #Validate username format (alphanumeric + underscore/hyphen only. Hardening against SQL injection)
    username_pattern = r'^[a-zA-Z0-9_-]+$'
    if not re.match(username_pattern, user_data.username):
        raise HTTPException(
            status_code=400,
            detail="Username can only contain letters, numbers, underscore, and hyphen"
        )


    if len(user_data.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must be at least 8 characters"
        )

    # Validate password complexity
    if not any(c.isalpha() for c in user_data.password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one letter"
        )
    
    if not any(c.isdigit() for c in user_data.password):
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least one number"
        )
    
    #Validate email format (if provided)
    if user_data.email:
        if user_data.email:
            email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
            if not re.match(email_pattern, user_data.email):
                raise HTTPException(
                    status_code=400,
                    detail="Invalid email format"
                )    
            
    # Check if username already exists
    existing_user = db.query(DBUser).filter(
        DBUser.username == user_data.username
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=400,
            detail="Username already registered"
        )

    #Check if email already exists (if provided)
    if user_data.email:
        existing_email = db.query(DBUser).filter(
            DBUser.email == user_data.email
        ).first()

        if existing_email:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

    #Hash password
    password_hash = get_password_hash(user_data.password)

    #Create new user in PostgreSQL
    new_user = DBUser(
        username=user_data.username,
        email=user_data.email,
        password_hash=password_hash,
        created_at=datetime.utcnow()
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    logger.info(f"New user registered: {user_data.username}")

    return {
        "message": "User registered successfully",
        "username": new_user.username
    }

@app.post("/token")
@limiter.limit("10/minute")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """
    Login and get JWT access token
    """
    username = form_data.username
    password = form_data.password

    # Query user from PostgreSQL
    user = db.query(DBUser).filter(DBUser.username == username).first()

    if not user or not verify_password(password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Update last login timestamp
    user.last_login = datetime.utcnow()
    db.commit()

    #Create JWT token
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": username}, 
        expires_delta=access_token_expires
    )

    logger.info(f"User logged in: {username}")

    return {
        "access_token": access_token,
        "token_type": "bearer",
    }

# -----------------------------------------------------------------------------
# Journal Endpoints
# -----------------------------------------------------------------------------

@app.post("/journal/entry")
@limiter.limit("30/minute")
async def create_journal_entry(
    entry: JournalEntryInput, 
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Submit new journal entry with emotion analysis
    """
    content = entry.content.strip()

    #Validate content
    if not content:
        raise HTTPException(status_code=400, detail="Content cannot be empty")
    
    #5000 magic number just a based estimate of longest entries while maintaining security parameters, will change later if needed
    MAX_CONTENT_LENGTH = 5000
    if len(content) > MAX_CONTENT_LENGTH:
        raise HTTPException(
            status_code=400,
            detail=f"Content exceeds maximum length of {MAX_CONTENT_LENGTH} characters"
        )

    # Analyze emotion
    emotion_result = emotion_processor.analyze_journal_entry(content)

    #Create journal entry in PostgreSQL
    new_entry = DBJournalEntry(
        user_id=current_user.id,
        session_id=f"session_{current_user.username}",
        content=content,
        emotion=emotion_result['primary_emotion'],
        intensity=emotion_result['intensity'],
        valence=emotion_result['valence'],
        arousal=emotion_result['arousal'],
        timestamp=datetime.utcnow()
    )

    db.add(new_entry)
    db.commit()
    db.refresh(new_entry)

    logger.info(
        f"Journal entry created: user={current_user.username}, "
        f"emotion={emotion_result['primary_emotion']}"
    )


    #Return response matching Unity's expected format
    return {
        "message": "Entry saved successfully",
        "entry_id": new_entry.id,
        "emotion_analysis": {
            "primary_emotion": emotion_result['primary_emotion'],
            "intensity": emotion_result['intensity'],
            "confidence": emotion_result['confidence'],
            "valence": emotion_result['valence'],
            "arousal": emotion_result['arousal']
        },
        "weather_effect": EMOTION_WEATHER_MAP.get(
            emotion_result['primary_emotion'], 
            EMOTION_WEATHER_MAP['neutral']
        )
    }

@app.get("/journal/entries")
@limiter.limit("60/minute")
async def get_journal_entries(
    limit: int = 20,
    offset: int = 0,
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve user's journal entries with pagination
    """

    #Validate pagination parameters
    if limit < 1 or limit > 100:
        raise HTTPException(status_code=400, detail="limit must be between 1 and 100")

    if offset < 0:
        raise HTTPException(status_code=400, detail="Offset must be non-negative")
    
    #Query entries from PostgreSQL
    entries = (
        db.query(DBJournalEntry)\
        .filter(DBJournalEntry.user_id == current_user.id)\
        .order_by(DBJournalEntry.timestamp.desc())\
        .offset(offset)\
        .limit(limit)\
        .all()
    )

    #Format response for Unity
    formatted_entries = []
    for entry in entries:
        formatted_entries.append(
            {
                "id": entry.id,
                "content": entry.content,
                "emotion": entry.emotion,
                "intensity": entry.intensity,
                "valence": entry.valence,
                "arousal": entry.arousal,
                "timestamp": entry.timestamp.isoformat(),
                "date_formatted": entry.timestamp.strftime("%B %d, %Y at %I:%M %p")
                if entry.timestamp
                else "",
            }
        )
    
    return formatted_entries

@app.get("/unity/weather-state")
@limiter.limit("120/minute")
async def get_weather_state(
    current_user : DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get current weather state based on user's emotional analysis.
    Maps the most recent journal entry emotion to UniStorm weather type.
    Uses last 5 jourrnal entries from PostgreSQL
    
    Used by Unity game to sync environment with emotional state.
    """
    
    # Get recent journal entries (last 5 for trend analysis)
    recent_entries = (
        db.query(DBJournalEntry)
        .filter(DBJournalEntry.user_id == current_user.id)
        .order_by(DBJournalEntry.timestamp.desc())
        .limit(5)
        .all()
    )
    
    # Default weather if no entries
    if not recent_entries:
        return {
            "weather_type": "Mostly Clear",
            "intensity": 0.5,
            "primary_emotion": "neutral",
            "confidence": 0.5,
            "timestamp": datetime.utcnow().isoformat(),
            "message": "No journal entries found - using default weather"
        }
    
    # Get most recent entry's emotional data
    latest_entry = recent_entries[0]
    latest_emotion = latest_entry.emotion or "neutral"
    intensity = latest_entry.intensity or 0.5
    confidence = intensity
    
    # Map emotion to UniStorm weather
    weather_data = EMOTION_WEATHER_MAP.get(
        latest_emotion,
        {'weather': 'Mostly Clear', 'multiplier': 0.5, 'description': 'Default weather'}
    )
    
    # Calculate final intensity (emotion intensity * weather multiplier)
    final_intensity = min(intensity * weather_data['multiplier'], 1.0)
    
    return {
        "weather_type": weather_data['weather'],
        "intensity": round(final_intensity, 3),
        "emotion": latest_emotion,
        "confidence": round(confidence, 3),
        "timestamp": datetime.utcnow().isoformat(),
        "description": weather_data['description'],
        "entry_count": len(recent_entries),
        "latest_entry_timestamp": latest_entry.timestamp.isoformat()
        if latest_entry.timestamp else ""
    }



@app.get("/journal/stats")
@limiter.limit("30/minute")
async def get_journal_stats(
    current_user: DBUser = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Get statistics about user's journal entries
    """
    # Total entries
    total_entries = db.query(DBJournalEntry)\
        .filter(DBJournalEntry.user_id == current_user.id)\
        .count()
    
    # Emotion distribution
    entries = db.query(DBJournalEntry)\
        .filter(DBJournalEntry.user_id == current_user.id)\
        .all()
    
    emotion_counts = Counter([e.emotion for e in entries])
    
    # Average intensity
    avg_intensity = sum([e.intensity for e in entries]) / len(entries) if entries else 0
    
    # Average valence
    avg_valence = sum([e.valence for e in entries]) / len(entries) if entries else 0
    
    return {
        "total_entries": total_entries,
        "emotion_distribution": dict(emotion_counts),
        "average_intensity": round(avg_intensity, 2),
        "average_valence": round(avg_valence, 2),
        "most_common_emotion": emotion_counts.most_common(1)[0][0] if emotion_counts else "none"
    }

# =============================================================================
# STARTUP EVENT
# =============================================================================

@app.on_event("startup")
async def startup_event():
    """Run on application startup"""
    logger.info("="*60)
    logger.info("Kai Emotional Gaming Platform - Starting Up")
    logger.info("="*60)
    logger.info(f"Emotion Model: {emotion_processor.model_name}")
    logger.info(f"Detected Emotions: {emotion_processor.native_emotions}")
    logger.info(f"Database: PostgreSQL")
    logger.info("="*60)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)