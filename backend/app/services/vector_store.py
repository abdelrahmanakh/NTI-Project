from __future__ import annotations

from typing import Any, Sequence

import chromadb


class ChromaVectorStore:
    """
    ChromaDB vector store wrapper.

    Keeps compatibility with the existing retriever API:

        vector_store.search(...)

    and provides:
    - Safe embedding validation
    - Document validation
    - Metadata normalization
    - Dense vector search
    - Persistent ChromaDB storage
    """

    def __init__(
        self,
        persist_directory: str = "./chroma_db",
        collection_name: str = "edu_rag",
    ):
        self.persist_directory = persist_directory
        self.collection_name = collection_name

        self.client = chromadb.PersistentClient(
            path=self.persist_directory
        )

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name
        )

    # ================================================================
    # CHUNK TEXT
    # ================================================================

    @staticmethod
    def _get_chunk_text(chunk: Any) -> str:

        if chunk is None:
            return ""

        if hasattr(chunk, "text"):
            text = chunk.text

        elif isinstance(chunk, dict):
            text = chunk.get("text", "")

        else:
            text = str(chunk)

        if text is None:
            return ""

        return str(text).strip()

    # ================================================================
    # METADATA
    # ================================================================

    @staticmethod
    def _get_chunk_metadata(
        chunk: Any,
        index: int,
    ) -> dict:
        metadata = {}

        # ------------------------------------------------------------
        # 1. Object metadata (if chunk has a .metadata dict)
        # ------------------------------------------------------------
        if hasattr(chunk, "metadata"):
            chunk_metadata = chunk.metadata
            if isinstance(chunk_metadata, dict):
                metadata.update(chunk_metadata)

        # ------------------------------------------------------------
        # 2. Dataclass/Object attributes (FIX FOR PDFs)
        # ------------------------------------------------------------
        # Extract properties directly if the chunk is a class object
        for key in (
            "source", "page", "chunk_id", "type",
            "start_timestamp", "end_timestamp", "start_time", "end_time", "video_id", "url"
        ):
            if hasattr(chunk, key):
                val = getattr(chunk, key)
                if val is not None:
                    metadata[key] = val

        # ------------------------------------------------------------
        # 3. Dictionary metadata (FIX FOR YOUTUBE)
        # ------------------------------------------------------------
        if isinstance(chunk, dict):
            chunk_metadata = chunk.get(
                "metadata",
                {}
            )
            if isinstance(chunk_metadata, dict):
                metadata.update(chunk_metadata)

            for key in (
                "source", "page", "document_id", "chunk_id", "type",
                "start_timestamp", "end_timestamp", "start_time", "end_time", "video_id", "url"
            ):
                if key in chunk and chunk[key] is not None:
                    metadata[key] = chunk[key]

        # ------------------------------------------------------------
        # REQUIRED metadata fallback
        # ------------------------------------------------------------
        if not metadata.get("source"):
            metadata["source"] = "unknown"
        if "page" not in metadata:
            metadata["page"] = "unknown"
        if "chunk_index" not in metadata:
            metadata["chunk_index"] = index

        return metadata

    # ================================================================
    # EMBEDDING VALIDATION
    # ================================================================

    @staticmethod
    def _validate_embeddings(
        embeddings: Sequence[Any],
        expected_count: int,
    ) -> None:

        if embeddings is None:
            raise ValueError(
                "Embedding generation returned None."
            )

        try:
            embedding_count = len(embeddings)

        except TypeError as exc:
            raise ValueError(
                "Embeddings must be a sequence."
            ) from exc

        if embedding_count == 0:
            raise ValueError(
                "Embedding generation returned an empty list []. "
                "No vectors were generated."
            )

        if embedding_count != expected_count:
            raise ValueError(
                "Embedding/chunk count mismatch.\n"
                f"Chunks: {expected_count}\n"
                f"Embeddings: {embedding_count}"
            )

        first_dimension = None

        for index, vector in enumerate(embeddings):

            if vector is None:
                raise ValueError(
                    f"Embedding at index {index} is None."
                )

            try:
                vector_length = len(vector)

            except TypeError as exc:
                raise ValueError(
                    f"Embedding at index {index} "
                    "is not a valid vector."
                ) from exc

            if vector_length == 0:
                raise ValueError(
                    f"Embedding at index {index} is empty."
                )

            if first_dimension is None:
                first_dimension = vector_length

            elif vector_length != first_dimension:
                raise ValueError(
                    "Embedding dimension mismatch.\n"
                    f"Embedding 0: {first_dimension}\n"
                    f"Embedding {index}: {vector_length}"
                )

    # ================================================================
    # ADD DOCUMENTS
    # ================================================================

    def add_documents(
        self,
        chunks: Sequence[Any],
        embeddings: Sequence[Any],
        session_id: str,
    ) -> None:

        if chunks is None:
            raise ValueError(
                "Chunks cannot be None."
            )

        try:
            chunk_count = len(chunks)

        except TypeError as exc:
            raise ValueError(
                "Chunks must be a sequence."
            ) from exc

        if chunk_count == 0:
            raise ValueError(
                "No chunks were created."
            )

        # ------------------------------------------------------------
        # Validate chunk text
        # ------------------------------------------------------------

        valid_chunks = []

        for chunk in chunks:

            text = self._get_chunk_text(chunk)

            if text:
                valid_chunks.append(chunk)

        if len(valid_chunks) != len(chunks):

            raise ValueError(
                "Some chunks contain empty text.\n"
                f"Original chunks: {len(chunks)}\n"
                f"Valid chunks: {len(valid_chunks)}"
            )

        # ------------------------------------------------------------
        # Validate embeddings
        # ------------------------------------------------------------

        self._validate_embeddings(
            embeddings=embeddings,
            expected_count=len(valid_chunks),
        )

        # ------------------------------------------------------------
        # IDs
        # ------------------------------------------------------------

        ids = []

        for index, chunk in enumerate(valid_chunks):

            metadata = self._get_chunk_metadata(
                chunk,
                index,
            )

            chunk_id = metadata.get(
                "chunk_id"
            )

            if not chunk_id:

                source = metadata.get(
                    "source",
                    "unknown",
                )

                page = metadata.get(
                    "page",
                    "unknown",
                )

                chunk_id = (
                    f"{source}"
                    f"_page_{page}"
                    f"_chunk_{index}"
                )

            ids.append(str(chunk_id))

        # ------------------------------------------------------------
        # Documents
        # ------------------------------------------------------------

        documents = [
            self._get_chunk_text(chunk)
            for chunk in valid_chunks
        ]

        # ------------------------------------------------------------
        # Metadata
        # ------------------------------------------------------------

        metadatas = []

        for index, chunk in enumerate(valid_chunks):

            metadata = self._get_chunk_metadata(
                chunk,
                index,
            )

            clean_metadata = {}

            for key, value in metadata.items():

                if value is None:
                    continue

                if isinstance(
                    value,
                    (str, int, float, bool),
                ):
                    clean_metadata[str(key)] = value

                else:
                    clean_metadata[str(key)] = str(
                        value
                    )

            # Retriever requires source
            if not clean_metadata.get("source"):
                clean_metadata["source"] = "unknown"

            clean_metadata["session_id"] = session_id

            metadatas.append(
                clean_metadata
            )

        # ------------------------------------------------------------
        # Final validation
        # ------------------------------------------------------------

        if len(ids) != len(documents):
            raise ValueError(
                "IDs/documents mismatch."
            )

        if len(metadatas) != len(documents):
            raise ValueError(
                "Metadata/documents mismatch."
            )

        if len(embeddings) != len(documents):
            raise ValueError(
                "Embeddings/documents mismatch."
            )

        # ------------------------------------------------------------
        # ChromaDB
        # ------------------------------------------------------------

        self.collection.upsert(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
            embeddings=embeddings,
        )

    # ================================================================
    # SEARCH
    # ================================================================

    def search(
        self,
        query_embedding: Sequence[float],
        top_k: int = 5,
        session_id: str = None,
        **kwargs,
    ) -> dict:

        if query_embedding is None:
            raise ValueError(
                "Query embedding cannot be None."
            )

        try:
            embedding_length = len(query_embedding)

        except TypeError as exc:
            raise ValueError(
                "Query embedding must be a vector."
            ) from exc

        if embedding_length == 0:
            raise ValueError(
                "Query embedding cannot be empty."
            )

        collection_count = self.collection.count()

        if collection_count == 0:
            return {
                "ids": [[]],
                "documents": [[]],
                "metadatas": [[]],
                "distances": [[]],
            }

        n_results = kwargs.get(
            "n_results",
            top_k,
        )

        n_results = max(
            1,
            min(
                int(n_results),
                collection_count,
            ),
        )

        where_clause = {"session_id": session_id} if session_id else None

        return self.collection.query(
            query_embeddings=[
                query_embedding
            ],
            n_results=n_results,
            where=where_clause
        )

    # ================================================================
    # QUERY
    # ================================================================

    def query(
        self,
        query_embedding: Sequence[float],
        n_results: int = 5,
    ) -> dict:

        return self.search(
            query_embedding=query_embedding,
            top_k=n_results,
        )

    # ================================================================
    # COUNT
    # ================================================================

    def count(self) -> int:

        return self.collection.count()

    # ================================================================
    # RESET
    # ================================================================

    def reset(self) -> None:

        self.client.delete_collection(
            name=self.collection_name
        )

        self.collection = (
            self.client.get_or_create_collection(
                name=self.collection_name
            )
        )