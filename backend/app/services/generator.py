import os
import time
from typing import Any, AsyncGenerator, TypeVar, Type, Optional
from pydantic import BaseModel
from google import genai
from groq import Groq
from google.genai import types
from app.core.config import GEMINI_API_KEY, GEMINI_CHAT_MODEL, GROQ_API_KEY, GROQ_CHAT_MODEL, GROQ_FALLBACK_MODEL_1, GROQ_FALLBACK_MODEL_2

GROQ_MODELS = [
    GROQ_CHAT_MODEL,
    GROQ_FALLBACK_MODEL_1,
    GROQ_FALLBACK_MODEL_2,
]

class HybridGenerator:
    """
    Multi-provider LLM generator.

    Priority:
        1. Gemini
        2. Groq Model 1
        3. Groq Model 2
        4. Groq Model 3

    If one provider/model fails, the next one is used.
    """

    def __init__(
        self,
        gemini_model: str = GEMINI_CHAT_MODEL,
        groq_models: Optional[list[str]] = None,
    ):

        # =====================================================
        # GEMINI
        # =====================================================

        self.gemini_model = gemini_model

        self.gemini_client = None

        if GEMINI_API_KEY:

            self.gemini_client = genai.Client(
                api_key=GEMINI_API_KEY
            )

        # =====================================================
        # GROQ
        # =====================================================

        self.groq_client = None

        if GROQ_API_KEY:

            self.groq_client = Groq(
                api_key=GROQ_API_KEY
            )

        # =====================================================
        # FALLBACK MODELS
        # =====================================================

        self.groq_models = groq_models or GROQ_MODELS

    # =========================================================
    # CONTEXT BUILDER
    # =========================================================

    def _build_context(
        self,
        retrieved_documents: list[dict],
    ) -> str:

        context_parts = []

        for i, document in enumerate(
            retrieved_documents,
            start=1,
        ):

            source = document.get(
                "source",
                "unknown",
            )

            page = document.get(
                "page",
                "N/A",
            )

            timestamp_start = document.get(
                "timestamp_start",
                "N/A",
            )

            timestamp_end = document.get(
                "timestamp_end",
                "N/A",
            )

            text = document.get(
                "text",
                "",
            )

            context_parts.append(
                f"""
                SOURCE {i}

                Source: {source}
                Page: {page}
                Timestamp: {timestamp_start} -> {timestamp_end}

                Content:
                {text}
                """
            )

        return "\n".join(context_parts)

    # =========================================================
    # PROMPT
    # =========================================================

    def _build_prompt(
        self,
        question: str,
        context: str,
    ) -> str:

        return f"""
                You are an evidence-grounded AI learning assistant.

                Your job is to answer the user's question using ONLY
                the retrieved context.

                IMPORTANT RULES:

                1. Do not invent information.
                2. Do not use outside knowledge when answering.
                3. If the context is insufficient, say so clearly.
                4. Explain concepts in a clear educational way.
                5. When possible, mention the source.
                6. If the source is a YouTube video and timestamps
                are available, mention the relevant timestamp.
                7. Distinguish facts from explanations.

                USER QUESTION:

                {question}

                RETRIEVED CONTEXT:

                {context}

                ANSWER:
                """

    # =========================================================
    # GEMINI
    # =========================================================

    def _generate_gemini(
        self,
        prompt: str,
    ) -> str:

        if self.gemini_client is None:

            raise RuntimeError(
                "Gemini client is not configured."
            )

        response = (
            self.gemini_client
            .models
            .generate_content(
                model=self.gemini_model,
                contents=prompt,
            )
        )

        if not response.text:

            raise RuntimeError(
                "Gemini returned an empty response."
            )

        return response.text.strip()

    # =========================================================
    # GROQ
    # =========================================================

    def _generate_groq(
        self,
        prompt: str,
        model: str,
    ) -> str:

        if self.groq_client is None:

            raise RuntimeError(
                "Groq client is not configured."
            )

        response = (
            self.groq_client
            .chat
            .completions
            .create(
                model=model,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are an evidence-grounded "
                            "educational AI assistant."
                        ),
                    },
                    {
                        "role": "user",
                        "content": prompt,
                    },
                ],
                temperature=0.2,
            )
        )

        answer = (
            response
            .choices[0]
            .message
            .content
        )

        if not answer:

            raise RuntimeError(
                f"Groq model {model} returned "
                "an empty response."
            )

        return answer.strip()

    # =========================================================
    # MAIN GENERATION
    # =========================================================

    def generate(
        self,
        question: str,
        retrieved_documents: list[dict],
    ) -> str:

        if not retrieved_documents:

            return (
                "I could not find relevant information "
                "in the provided sources."
            )

        context = self._build_context(
            retrieved_documents
        )

        prompt = self._build_prompt(
            question=question,
            context=context,
        )

        errors = []

        # =====================================================
        # 1. TRY GEMINI
        # =====================================================

        if self.gemini_client is not None:

            print(
                "\n[Generator] Trying Gemini..."
            )

            try:

                answer = self._generate_gemini(
                    prompt
                )

                print(
                    "[Generator] ✓ Gemini succeeded."
                )

                return answer

            except Exception as exc:

                error_message = (
                    f"Gemini failed: {exc}"
                )

                print(
                    f"[Generator] ⚠ {error_message}"
                )

                errors.append(
                    error_message
                )

        # =====================================================
        # 2. TRY GROQ MODELS
        # =====================================================

        if self.groq_client is not None:

            for model in self.groq_models:

                print(
                    f"\n[Generator] Trying Groq: {model}"
                )

                try:

                    answer = self._generate_groq(
                        prompt=prompt,
                        model=model,
                    )

                    print(
                        f"[Generator] ✓ Groq succeeded: "
                        f"{model}"
                    )

                    return answer

                except Exception as exc:

                    error_message = (
                        f"Groq {model} failed: {exc}"
                    )

                    print(
                        f"[Generator] ⚠ "
                        f"{error_message}"
                    )

                    errors.append(
                        error_message
                    )

                    # Small delay before next model
                    time.sleep(0.5)

        # =====================================================
        # EVERYTHING FAILED
        # =====================================================

        error_report = "\n".join(
            f"- {error}"
            for error in errors
        )

        raise RuntimeError(
            "All generation providers failed.\n\n"
            f"{error_report}"
        )