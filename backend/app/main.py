from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pathlib import Path
import mimetypes
mimetypes.add_type("application/pdf", ".pdf")
# Add this import:
from app.api.routers import ingest, tutor, tools

app = FastAPI(title="EduRAG API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

data_dir = Path(__file__).parent.parent / "data"
data_dir.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(data_dir)), name="files")

# Include the new ingestion router
app.include_router(ingest.router)
app.include_router(tutor.router)
app.include_router(tools.router)

@app.get("/")
async def root():
    return {"status": "ok", "message": "EduRAG API is running."}

@app.get("/api/files/{filename}")
async def serve_file_inline(filename: str):
    file_path = data_dir / "uploads" / filename
    if not file_path.exists():
        raise HTTPException(status_code=404, detail="File not found")
    
    # 1. Dynamically guess the mime type based on the file extension (.pdf, .png, .jpg)
    mime_type, _ = mimetypes.guess_type(str(file_path))
    
    # Fallback just in case it can't figure it out
    if mime_type is None:
        mime_type = "application/octet-stream"
    
    # 2. Return the file with the correct dynamic media_type
    return FileResponse(
        path=file_path,
        media_type=mime_type,
        content_disposition_type="inline", 
        filename=filename
    )