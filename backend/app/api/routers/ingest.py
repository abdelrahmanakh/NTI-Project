from fastapi import APIRouter, UploadFile, File, HTTPException, Form
import shutil
from app.models.schemas import YouTubeIngestRequest

# Import the shared instances
from app.core.dependencies import (
    pdf_loader, yt_processor, chunker, embedder, vector_store, UPLOAD_DIR, image_processor
)

router = APIRouter(prefix="/api/ingest", tags=["Ingestion"])

@router.post("/pdf")
async def ingest_pdf(file: UploadFile = File(...), session_id: str = Form(...)):
    if not file.filename.endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are supported.")
    
    # Save the file temporarily
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
    
    try:
        # 1. Parse the PDF
        documents = pdf_loader.load(file_path)
        
        # 2. Split into chunks
        chunks = chunker.split(documents)
        
        # 3. Generate embeddings
        texts_to_embed = [chunk.text for chunk in chunks]
        embeddings = embedder.embed_batch(texts_to_embed)
        
        # 4. Store in ChromaDB
        vector_store.add_documents(chunks, embeddings, session_id=session_id)
        
        return {"status": "success", "message": f"Successfully ingested {file.filename}", "chunks_processed": len(chunks)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/youtube")
async def ingest_youtube(request: YouTubeIngestRequest):
    try:
        # 1. Parse YouTube transcript & create timestamp-aware chunks
        # Your YouTubeProcessor already handles chunking internally
        chunks_data = yt_processor.process(request.url)
        
        # 2. Generate embeddings
        texts_to_embed = [chunk["text"] for chunk in chunks_data]
        embeddings = embedder.embed_batch(texts_to_embed)
        
        # 3. Store in ChromaDB
        vector_store.add_documents(chunks_data, embeddings, session_id=request.session_id)
        
        return {"status": "success", "message": "Successfully ingested YouTube video", "chunks_processed": len(chunks_data)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.post("/clear")
async def clear_database():
    """
    Wipes all documents and embeddings from ChromaDB.
    Useful for starting a new chat session from scratch.
    """
    try:
        vector_store.reset()
        
        # Optional: You can also delete the uploaded files and caches here
        import shutil
        if UPLOAD_DIR.exists():
            shutil.rmtree(UPLOAD_DIR)
            UPLOAD_DIR.mkdir()
            
        return {
            "status": "success", 
            "message": "Database and vector collections have been completely reset."
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear database: {str(e)}")
    
@router.get("/count")
async def get_document_count():
    count = vector_store.count()
    return {"status": "success", "total_documents": count}

# 2. Add this new route below your existing /pdf route
@router.post("/image")
async def ingest_image(file: UploadFile = File(...), session_id: str = Form(...)):
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Only image files are supported.")
    
    # Save the file temporarily (this also allows the frontend to preview it later)
    file_path = UPLOAD_DIR / file.filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # 1. Ask Gemini Vision to extract all meaningful text and context from the image
        image_description = image_processor.analyze_image(file_path)
        
        # 2. Package it as a document so the chunker understands it
        documents = [{
            "text": f"Image Description ({file.filename}):\n{image_description}",
            "page": 1,
            "source": file.filename
        }]
        
        # 3. Split into chunks (if the description is long)
        chunks = chunker.split(documents)
        
        # 4. Generate embeddings
        texts_to_embed = [chunk.text for chunk in chunks]
        embeddings = embedder.embed_batch(texts_to_embed)
        
        # 5. Store in ChromaDB
        vector_store.add_documents(chunks, embeddings, session_id=session_id)
        
        return {"status": "success", "message": f"Successfully ingested {file.filename}", "chunks_processed": len(chunks)}
    
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/session/{session_id}")
async def clear_session(session_id: str):
    vector_store.collection.delete(where={"session_id": session_id})
    return {"status": "success"}