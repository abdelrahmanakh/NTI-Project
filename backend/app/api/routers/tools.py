from fastapi import APIRouter, HTTPException
from app.models.schemas import (
    TopicRequest, ModeRequest, PodcastRequest, QuizResponse, FlashcardResponse
)

# Import the shared instances
from app.core.dependencies import retriever, tools, podcast_gen

router = APIRouter(prefix="/api/tools", tags=["Educational Modes"])

@router.post("/summarize")
async def summarize_material(request: ModeRequest):
    """Generates an executive summary of the uploaded materials."""
    docs = retriever.retrieve(
        query="main concepts, summary, overview", 
        top_k=request.top_k or 5,
        session_id=request.session_id  # <--- Added
    )
    if not docs:
        raise HTTPException(status_code=404, detail="No source material found in this chat session.")
        
    summary = tools.summarize(retrieved_documents=docs)
    return {"status": "success", "data": summary}

@router.post("/explain")
async def explain_topic(request: TopicRequest):
    """Explains a specific topic inputted by the user."""
    docs = retriever.retrieve(
        query=request.topic, 
        top_k=request.top_k or 5,
        session_id=request.session_id  # <--- Added
    )
    explanation = tools.explain(topic=request.topic, retrieved_documents=docs)
    return {"status": "success", "topic": request.topic, "data": explanation}

@router.post("/quiz", response_model=QuizResponse)
async def generate_quiz(request: ModeRequest):
    """Generates an interactive multiple-choice quiz."""
    docs = retriever.retrieve(
        query="key facts, important details", 
        top_k=request.top_k or 6,
        session_id=request.session_id  # <--- Added
    )
    
    quiz_data = tools.generate_quiz(retrieved_documents=docs, number_of_questions=5)
    return quiz_data

@router.post("/flashcards", response_model=FlashcardResponse)
async def generate_flashcards(request: ModeRequest):
    """Generates an interactive 3D flashcard deck."""
    docs = retriever.retrieve(
        query="definitions, concepts, terminology", 
        top_k=request.top_k or 6,
        session_id=request.session_id  # <--- Added
    )
    
    flashcards_data = tools.generate_flashcards(retrieved_documents=docs, number_of_cards=10)
    return flashcards_data

@router.post("/study-guide")
async def generate_study_guide(request: ModeRequest):
    """Generates a structured markdown study guide."""
    docs = retriever.retrieve(
        query="core concepts, definitions, relationships", 
        top_k=request.top_k or 8,
        session_id=request.session_id  # <--- Added
    )
    study_guide = tools.generate_study_guide(retrieved_documents=docs)
    return {"status": "success", "data": study_guide}

@router.post("/podcast")
async def generate_podcast(request: PodcastRequest):
    """Generates an engaging, two-host dialogue/script and audio file."""
    docs = retriever.retrieve(
        query=request.topic, 
        top_k=request.top_k or 6,
        session_id=request.session_id  # <--- Added
    )
        
    try:
        script, audio_path = podcast_gen.generate(
            topic=request.topic, 
            retrieved_documents=docs
        )
        audio_url = f"http://localhost:8000/files/podcasts/{audio_path.name}"
        
        return {
            "status": "success", 
            "script": script,
            "audio_url": audio_url
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))