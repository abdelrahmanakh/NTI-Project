from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
import json
import asyncio

from app.models.schemas import TutorRequest, Citation

# Import the shared instances
from app.core.dependencies import retriever, tools

router = APIRouter(prefix="/api/tutor", tags=["AI Tutor"])

async def generate_tutor_stream(question: str, top_k: int, session_id: str):
    # 1. Retrieve relevant chunks from vector store
    retrieved_docs = retriever.retrieve(query=question, top_k=top_k, session_id=session_id)
    
    # 2. Package citation metadata and send as the first SSE event
    citations = [
        Citation(
            source=doc.get("source", "unknown"),
            page=doc.get("page", "N/A"),
            snippet=doc.get("text", "")[:200] + "...",
            chunk_id=doc.get("chunk_id"),
            start_timestamp=doc.get("start_timestamp"),
            end_timestamp=doc.get("end_timestamp"),
            url=doc.get("url"),
            video_id=doc.get("video_id"),
        ).model_dump()
        for doc in retrieved_docs
    ]
    
    yield f"data: {json.dumps({'type': 'citations', 'data': citations})}\n\n"
    await asyncio.sleep(0.01)

    # 3. Get the complete answer using your existing synchronous generator method
    try:
        # We run the synchronous generate inside an executor or directly if fast,
        # or use tools.summarize / a custom prompt simulation for the tutor answer.
        # Let's call the generator/tutor logic:
        instruction = f"Act as a patient AI tutor. Student question: {question.strip()}. Provide a direct answer, simple explanation, reasoning, and examples."
        
        # Using your tool's internal prompt building logic or direct generator call:
        answer = tools._generate(instruction=instruction, retrieved_documents=retrieved_docs)
        
        # Simulate typing/streaming effect chunk by chunk for the Next.js frontend UI
        chunk_size = 15
        for i in range(0, len(answer), chunk_size):
            token_chunk = answer[i:i + chunk_size]
            yield f"data: {json.dumps({'type': 'token', 'data': token_chunk})}\n\n"
            await asyncio.sleep(0.02) # Control typing speed smoothness
            
    except Exception as e:
        yield f"data: {json.dumps({'type': 'error', 'data': str(e)})}\n\n"
    
    # Send completion flag
    yield f"data: {json.dumps({'type': 'done'})}\n\n"


@router.post("/chat")
async def chat_tutor(request: TutorRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="Question cannot be empty.")

    return StreamingResponse(
        generate_tutor_stream(request.question, request.top_k or 4, request.session_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
        },
    )