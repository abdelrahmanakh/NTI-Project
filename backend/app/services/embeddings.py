# ============================================================
# Gemini EduRAG - Embeddings
# ============================================================

import time
from typing import Iterable

from google import genai

from app.core.config import (
    GEMINI_API_KEY,
    GEMINI_EMBED_MODEL,
)


class GeminiEmbedder:
    """
    Generate text embeddings using Gemini.

    Features:
        - Single text embedding
        - Batch embedding
        - Empty-text protection
        - Retry handling
        - 429 / transient error handling
        - Output validation
        - Stable text -> embedding alignment
    """

    def __init__(
        self,
        model: str | None = None,
        max_retries: int = 3,
        retry_delay: float = 2.0,
    ):

        # ====================================================
        # CONFIG
        # ====================================================

        if not GEMINI_API_KEY:

            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        self.model = (
            model
            or GEMINI_EMBED_MODEL
        )

        self.max_retries = max(
            1,
            int(max_retries),
        )

        self.retry_delay = max(
            0.1,
            float(retry_delay),
        )

        # ====================================================
        # CLIENT
        # ====================================================

        self.client = genai.Client(
            api_key=GEMINI_API_KEY
        )

    # =========================================================
    # TEXT VALIDATION
    # =========================================================

    @staticmethod
    def _validate_text(
        text: str,
    ) -> str:
        """
        Normalize and validate one text.
        """

        if text is None:

            raise ValueError(
                "Embedding text cannot be None."
            )

        if not isinstance(
            text,
            str,
        ):

            text = str(text)

        text = text.strip()

        if not text:

            raise ValueError(
                "Embedding text cannot be empty."
            )

        return text

    # =========================================================
    # RESPONSE VALIDATION
    # =========================================================

    @staticmethod
    def _extract_embedding(
        response,
    ) -> list[float]:
        """
        Safely extract one embedding from Gemini response.
        """

        if response is None:

            raise RuntimeError(
                "Gemini embedding response is None."
            )

        embeddings = getattr(
            response,
            "embeddings",
            None,
        )

        if not embeddings:

            raise RuntimeError(
                "Gemini returned no embeddings."
            )

        first_embedding = embeddings[0]

        values = getattr(
            first_embedding,
            "values",
            None,
        )

        if values is None:

            raise RuntimeError(
                "Gemini returned an embedding "
                "without values."
            )

        values = list(values)

        if not values:

            raise RuntimeError(
                "Gemini returned an empty embedding."
            )

        return values

    # =========================================================
    # RETRY
    # =========================================================

    def _embed_with_retry(
        self,
        text: str,
    ) -> list[float]:
        """
        Generate one embedding with retries.
        """

        last_error = None

        for attempt in range(
            1,
            self.max_retries + 1,
        ):

            try:

                response = (
                    self.client
                    .models
                    .embed_content(
                        model=self.model,
                        contents=text,
                    )
                )

                return self._extract_embedding(
                    response
                )

            except Exception as exc:

                last_error = exc

                print(
                    f"[Embeddings] "
                    f"Attempt {attempt}/"
                    f"{self.max_retries} failed: "
                    f"{exc}"
                )

                if attempt < self.max_retries:

                    delay = (
                        self.retry_delay
                        * (2 ** (attempt - 1))
                    )

                    time.sleep(
                        delay
                    )

        raise RuntimeError(
            "Failed to generate embedding "
            f"after {self.max_retries} attempts. "
            f"Original error: {last_error}"
        )

    # =========================================================
    # SINGLE EMBEDDING
    # =========================================================

    def embed(
        self,
        text: str,
    ) -> list[float]:
        """
        Generate an embedding for one text.
        """

        text = self._validate_text(
            text
        )

        embedding = (
            self._embed_with_retry(
                text
            )
        )

        if not embedding:

            raise RuntimeError(
                "Generated embedding is empty."
            )

        return embedding

    # =========================================================
    # BATCH EMBEDDING
    # =========================================================

    def embed_batch(
        self,
        texts: list[str],
    ) -> list[list[float]]:
        """
        Generate embeddings for multiple texts.

        Empty input returns an empty list intentionally,
        but callers must never pass that result to Chroma.
        """

        # -----------------------------------------------------
        # Input validation
        # -----------------------------------------------------

        if texts is None:

            raise ValueError(
                "texts cannot be None."
            )

        if not isinstance(
            texts,
            list,
        ):

            texts = list(texts)

        if len(texts) == 0:

            raise ValueError(
                "Cannot generate embeddings for "
                "an empty text list."
            )

        # -----------------------------------------------------
        # Normalize texts
        # -----------------------------------------------------

        normalized_texts = []

        for index, text in enumerate(
            texts
        ):

            try:

                normalized_texts.append(
                    self._validate_text(
                        text
                    )
                )

            except Exception as exc:

                raise ValueError(
                    f"Invalid text at index "
                    f"{index}: {exc}"
                ) from exc

        # -----------------------------------------------------
        # Generate
        # -----------------------------------------------------

        embeddings = []

        total = len(
            normalized_texts
        )

        print(
            "\n"
            + "=" * 70
        )

        print(
            "GEMINI EMBEDDINGS"
        )

        print(
            "=" * 70
        )

        print(
            f"Texts: {total}"
        )

        print(
            f"Model: {self.model}"
        )

        for index, text in enumerate(
            normalized_texts,
            start=1,
        ):

            print(
                f"Embedding "
                f"{index}/{total}..."
            )

            embedding = (
                self._embed_with_retry(
                    text
                )
            )

            if not embedding:

                raise RuntimeError(
                    f"Gemini returned an empty "
                    f"embedding for text "
                    f"{index}/{total}."
                )

            embeddings.append(
                embedding
            )

        # -----------------------------------------------------
        # Final validation
        # -----------------------------------------------------

        if not embeddings:

            raise RuntimeError(
                "Embedding generation completed "
                "but returned zero embeddings."
            )

        if len(embeddings) != len(
            normalized_texts
        ):

            raise RuntimeError(
                "Embedding count mismatch: "
                f"{len(normalized_texts)} texts "
                f"but {len(embeddings)} embeddings."
            )

        dimension = len(
            embeddings[0]
        )

        if dimension == 0:

            raise RuntimeError(
                "Embedding dimension is zero."
            )

        for index, embedding in enumerate(
            embeddings
        ):

            if not embedding:

                raise RuntimeError(
                    f"Embedding {index} is empty."
                )

            if len(embedding) != dimension:

                raise RuntimeError(
                    "Embedding dimension mismatch: "
                    f"embedding 0 has dimension "
                    f"{dimension}, while embedding "
                    f"{index} has dimension "
                    f"{len(embedding)}."
                )

        print(
            "\n✓ Embeddings generated."
        )

        print(
            f"✓ Count: {len(embeddings)}"
        )

        print(
            f"✓ Dimension: {dimension}"
        )

        return embeddings