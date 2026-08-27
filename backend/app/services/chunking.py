from dataclasses import dataclass
from typing import Optional

@dataclass
class DocumentChunk:
    """A unified chunk extracted from any document or media."""
    text: str
    source: str
    page: int | str
    chunk_id: str
    url: Optional[str] = None
    video_id: Optional[str] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    start_timestamp: Optional[str] = None
    end_timestamp: Optional[str] = None


class TextChunker:
    """Split documents into overlapping text chunks."""

    def __init__(
        self,
        chunk_size: int = 500,
        chunk_overlap: int = 100,
    ):
        if chunk_overlap >= chunk_size:
            raise ValueError(
                "chunk_overlap must be smaller than chunk_size"
            )

        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def split(
        self,
        documents: list[dict],
    ) -> list[DocumentChunk]:

        chunks = []

        for document in documents:

            text = document["text"]
            source = document["source"]
            page = document["page"]

            start = 0
            chunk_index = 0

            while start < len(text):

                end = start + self.chunk_size

                chunk_text = text[start:end].strip()

                if chunk_text:

                    chunk_id = (
                        f"{source}_"
                        f"page_{page}_"
                        f"chunk_{chunk_index}"
                    )

                    chunks.append(
                        DocumentChunk(
                            text=chunk_text,
                            source=source,
                            page=page,
                            chunk_id=chunk_id,
                        )
                    )

                start += (
                    self.chunk_size
                    - self.chunk_overlap
                )

                chunk_index += 1

        return chunks
    
class VideoChunker:
    """Split video transcripts into timestamp-aware duration chunks."""
    def __init__(self, chunk_duration: float = 60.0):
        self.chunk_duration = chunk_duration

    @staticmethod
    def format_timestamp(seconds: float) -> str:
        seconds = int(max(0, seconds))
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"

    def split(self, transcript_data: dict, video_url: str) -> list[DocumentChunk]:
        snippets = transcript_data["snippets"]
        video_id = transcript_data["video_id"]
        
        chunks = []
        current_text = []
        chunk_start = None
        chunk_end = None
        chunk_index = 0

        for snippet in snippets:
            start = float(snippet["start"])
            end = float(snippet["end"])
            text = snippet["text"]

            if chunk_start is None:
                chunk_start = start

            current_text.append(text)
            chunk_end = end
            elapsed = chunk_end - chunk_start

            if elapsed >= self.chunk_duration:
                combined_text = " ".join(current_text).strip()
                if combined_text:
                    chunks.append(
                        DocumentChunk(
                            text=combined_text,
                            source="youtube",
                            page=0,
                            chunk_id=f"youtube_{video_id}_chunk_{chunk_index}",
                            url=video_url,
                            video_id=video_id,
                            start_time=chunk_start,
                            end_time=chunk_end,
                            start_timestamp=self.format_timestamp(chunk_start),
                            end_timestamp=self.format_timestamp(chunk_end)
                        )
                    )
                    chunk_index += 1
                current_text = []
                chunk_start = None

        # Handle remaining text
        if current_text:
            combined_text = " ".join(current_text).strip()
            if combined_text:
                chunks.append(
                    DocumentChunk(
                        text=combined_text,
                        source="youtube",
                        page=0,
                        chunk_id=f"youtube_{video_id}_chunk_{chunk_index}",
                        url=video_url,
                        video_id=video_id,
                        start_time=chunk_start,
                        end_time=chunk_end,
                        start_timestamp=self.format_timestamp(chunk_start),
                        end_timestamp=self.format_timestamp(chunk_end)
                    )
                )

        return chunks