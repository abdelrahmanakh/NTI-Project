from pydantic import BaseModel, Field
from typing import List, Optional

# --- Ingestion ---
class YouTubeIngestRequest(BaseModel):
    url: str
    session_id: str

# --- Citations & Retrieval ---
class Citation(BaseModel):
    source: str
    page: Optional[int | str] = None
    snippet: str
    chunk_id: Optional[str] = None
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None
    url: Optional[str] = None
    video_id: Optional[str] = None

# --- AI Tutor ---
class TutorRequest(BaseModel):
    question: str
    session_id: str
    top_k: Optional[int] = 4

# --- Quiz Mode ---
class QuizOption(BaseModel):
    option_id: str
    text: str

class QuizQuestion(BaseModel):
    question: str
    options: List[QuizOption]
    correct_option_id: str
    explanation: str

class QuizResponse(BaseModel):
    questions: List[QuizQuestion]

# --- Flashcards Mode ---
class FlashcardItem(BaseModel):
    front: str
    back: str
    concept: Optional[str] = None

class FlashcardResponse(BaseModel):
    flashcards: List[FlashcardItem]

# --- Tool Requests ---
class TopicRequest(BaseModel):
    topic: str
    session_id: str
    top_k: Optional[int] = 5

class ModeRequest(BaseModel):
    session_id: str
    top_k: Optional[int] = 5

class PodcastRequest(BaseModel):
    topic: str
    session_id: str
    top_k: Optional[int] = 5