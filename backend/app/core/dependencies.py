# app/core/dependencies.py
from pathlib import Path

from app.services.vector_store import ChromaVectorStore
from app.services.embeddings import GeminiEmbedder
from app.services.retriever import Retriever
from app.services.generator import HybridGenerator
from app.services.learning_tools import LearningTools
from app.services.podcast import PodcastGenerator
from app.services.ingestion import PDFLoader
from app.services.youtube_processor import YouTubeProcessor
from app.services.chunking import TextChunker
from app.services.image_processor import GeminiImageProcessor

# Directories
DATA_DIR = Path("data")
DATA_DIR.mkdir(parents=True, exist_ok=True)

UPLOAD_DIR = DATA_DIR / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

# 1. Initialize core infrastructure ONE TIME
embedder = GeminiEmbedder()
vector_store = ChromaVectorStore(persist_directory=str(DATA_DIR / "chroma"))
retriever = Retriever(vector_store=vector_store, embedder=embedder)

# 2. Initialize generation tools
generator = HybridGenerator()
tools = LearningTools(generator=generator)
podcast_gen = PodcastGenerator(output_dir=DATA_DIR / "podcasts")

# 3. Initialize ingestion tools
pdf_loader = PDFLoader()
yt_processor = YouTubeProcessor()
chunker = TextChunker()

image_processor = GeminiImageProcessor()