from __future__ import annotations

from typing import Any

from app.services.embeddings import GeminiEmbedder
from app.services.vector_store import ChromaVectorStore


class Retriever:
    """
    Retrieve relevant document chunks using dense vector search.

    Pipeline:

        Query
          ↓
        Gemini Embedding
          ↓
        ChromaDB
          ↓
        Top-K Relevant Chunks
    """

    def __init__(
        self,
        vector_store: ChromaVectorStore,
        embedder: GeminiEmbedder,
        top_k: int = 3,
    ):
        self.vector_store = vector_store
        self.embedder = embedder
        self.top_k = top_k

    # ============================================================
    # RETRIEVE
    # ============================================================

    def retrieve(
        self,
        query: str,
        top_k: int | None = None,
        session_id: str = None,
    ) -> list[dict[str, Any]]:
        """
        Retrieve the most relevant chunks for a query.
        """

        # --------------------------------------------------------
        # Validate query
        # --------------------------------------------------------

        if query is None:
            raise ValueError(
                "Query cannot be None."
            )

        query = str(query).strip()

        if not query:
            raise ValueError(
                "Query cannot be empty."
            )

        # --------------------------------------------------------
        # Determine K
        # --------------------------------------------------------

        k = (
            top_k
            if top_k is not None
            else self.top_k
        )

        k = max(1, int(k))

        # --------------------------------------------------------
        # Generate query embedding
        # --------------------------------------------------------

        query_embedding = self.embedder.embed(
            query
        )

        if not query_embedding:
            raise ValueError(
                "Query embedding generation returned empty result."
            )

        # --------------------------------------------------------
        # Vector search
        # --------------------------------------------------------

        results = self.vector_store.search(
            query_embedding=query_embedding,
            top_k=k,
            session_id=session_id
        )

        # --------------------------------------------------------
        # Safely extract results
        # --------------------------------------------------------

        documents = (
            results.get("documents", [[]])[0]
            if results
            else []
        )

        metadatas = (
            results.get("metadatas", [[]])[0]
            if results
            else []
        )

        distances = (
            results.get("distances", [[]])[0]
            if results
            else []
        )

        # --------------------------------------------------------
        # No results
        # --------------------------------------------------------

        if not documents:
            return []

        # --------------------------------------------------------
        # Build normalized retrieval objects
        # --------------------------------------------------------

        retrieved_documents = []

        for index, document in enumerate(
            documents
        ):

            metadata = (
                metadatas[index]
                if index < len(metadatas)
                and metadatas[index] is not None
                else {}
            )

            distance = (
                distances[index]
                if index < len(distances)
                else None
            )

            retrieved_documents.append(
                {
                    "text": document or "",

                    "source": metadata.get(
                        "source",
                        "unknown",
                    ),

                    "page": metadata.get(
                        "page",
                        "unknown",
                    ),

                    "chunk_id": metadata.get(
                        "chunk_id",
                        f"chunk_{index}",
                    ),
                    "start_timestamp": metadata.get("start_timestamp"),
                    "end_timestamp": metadata.get("end_timestamp"),
                    "url": metadata.get("url"),
                    "video_id": metadata.get("video_id"),
                    "distance": distance,
                }
            )

        return retrieved_documents

    # ============================================================
    # SEARCH
    # ============================================================

    def search(
        self,
        query: str,
        top_k: int | None = None,
    ) -> list[dict[str, Any]]:
        """
        Alias for retrieve().
        """

        return self.retrieve(
            query=query,
            top_k=top_k,
        )