from dataclasses import dataclass


@dataclass
class DocumentChunk:
    """A chunk of text extracted from a document."""

    text: str
    source: str
    page: int
    chunk_id: str


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