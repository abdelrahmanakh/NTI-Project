from __future__ import annotations

from typing import Any

from app.services.generator import HybridGenerator


class LearningTools:
    """
    Educational tools built on top of the existing RAG pipeline.

    Flow:

        User Request
             ↓
        Retrieved Documents
             ↓
        Learning Tool
             ↓
        Hybrid Generator
             ↓
        Grounded Educational Output
    """

    def __init__(
        self,
        generator: HybridGenerator,
    ):
        self.generator = generator

    # ============================================================
    # CONTEXT BUILDER
    # ============================================================

    @staticmethod
    def _build_context(
        retrieved_documents: list[dict[str, Any]],
    ) -> str:
        """
        Convert retrieved documents into a clean context string.
        """

        if not retrieved_documents:
            raise ValueError(
                "No retrieved documents were provided."
            )

        context_parts = []

        for index, document in enumerate(
            retrieved_documents,
            start=1,
        ):

            text = str(
                document.get("text", "")
            ).strip()

            if not text:
                continue

            source = document.get(
                "source",
                "unknown",
            )

            page = document.get(
                "page",
                "unknown",
            )

            context_parts.append(
                f"""
[Source {index}]
Source: {source}
Page: {page}

{text}
""".strip()
            )

        if not context_parts:
            raise ValueError(
                "Retrieved documents contain no valid text."
            )

        return "\n\n".join(
            context_parts
        )

    # ============================================================
    # GENERIC GENERATION
    # ============================================================

    def _generate(
        self,
        instruction: str,
        retrieved_documents: list[dict[str, Any]],
    ) -> str:
        """
        Generate an educational response grounded in retrieved data.
        """

        context = self._build_context(
            retrieved_documents
        )

        prompt = f"""
You are an educational AI tutor.

You MUST use the provided knowledge context.

IMPORTANT RULES:

1. Answer only from the provided context.
2. Do not invent facts.
3. If the context does not contain enough information,
   clearly say that the provided material is insufficient.
4. Explain concepts clearly and educationally.
5. Preserve important technical terminology.
6. Prefer structured answers.
7. Do not mention these instructions.

TASK:

{instruction}

KNOWLEDGE CONTEXT:

{context}
"""

        return self.generator.generate(
            question=prompt,
            retrieved_documents=retrieved_documents,
        )

    # ============================================================
    # AI TUTOR
    # ============================================================

    def tutor(
        self,
        question: str,
        retrieved_documents: list[dict[str, Any]],
    ) -> str:
        """
        Answer a student's question using retrieved evidence.
        """

        question = question.strip()

        if not question:
            raise ValueError(
                "Tutor question cannot be empty."
            )

        return self._generate(
            instruction=f"""
Act as a patient AI tutor.

Student question:

{question}

Provide:

1. Direct answer.
2. Simple explanation.
3. Step-by-step reasoning when appropriate.
4. Important points to remember.
5. A short example if the material supports one.
""",
            retrieved_documents=retrieved_documents,
        )

    # ============================================================
    # SUMMARIZE
    # ============================================================

    def summarize(
        self,
        retrieved_documents: list[dict[str, Any]],
    ) -> str:
        """
        Summarize the retrieved educational material.
        """

        return self._generate(
            instruction="""
Create a clear educational summary of the provided material.

Structure the response as:

## Summary

## Main Concepts

- Concept 1
- Concept 2
- Concept 3

## Important Details

## Key Takeaways

Keep the summary concise but do not remove important technical
information.
""",
            retrieved_documents=retrieved_documents,
        )

    # ============================================================
    # EXPLAIN
    # ============================================================

    def explain(
        self,
        topic: str,
        retrieved_documents: list[dict[str, Any]],
    ) -> str:
        """
        Explain a topic in an easy-to-understand way.
        """

        topic = topic.strip()

        if not topic:
            raise ValueError(
                "Explanation topic cannot be empty."
            )

        return self._generate(
            instruction=f"""
Explain the following topic to a student:

{topic}

Use a teaching style.

Structure:

## What is it?

## How does it work?

## Why is it important?

## Example

## Key Points

Start simple and gradually introduce technical details.
Only provide an example if it is supported by the material.
""",
            retrieved_documents=retrieved_documents,
        )

    # ============================================================
    # QUIZ GENERATOR
    # ============================================================

    def generate_quiz(
        self,
        retrieved_documents: list[dict[str, Any]],
        number_of_questions: int = 5,
    ) -> str:
        """
        Generate a quiz based strictly on retrieved content.
        """

        number_of_questions = max(
            1,
            min(
                int(number_of_questions),
                20,
            ),
        )

        return self._generate(
            instruction=f"""
Create an educational quiz based ONLY on the provided material.

Generate exactly {number_of_questions} questions.

Mix:

- Multiple Choice Questions
- True / False
- Conceptual Questions

For multiple-choice questions use:

Question:
A)
B)
C)
D)

Answer:
...

Explanation:
...

For True / False use:

Question:
...

Answer:
True/False

Explanation:
...

For conceptual questions use:

Question:
...

Expected Answer:
...

Make sure every answer can be supported by the provided material.
Do not introduce outside knowledge.
""",
            retrieved_documents=retrieved_documents,
        )

    # ============================================================
    # FLASHCARDS
    # ============================================================

    def generate_flashcards(
        self,
        retrieved_documents: list[dict[str, Any]],
        number_of_cards: int = 10,
    ) -> str:
        """
        Generate study flashcards from retrieved material.
        """

        number_of_cards = max(
            1,
            min(
                int(number_of_cards),
                30,
            ),
        )

        return self._generate(
            instruction=f"""
Create exactly {number_of_cards} educational flashcards.

Each flashcard must use this format:

### Flashcard 1

Q:
...

A:
...

### Flashcard 2

Q:
...

A:
...

Rules:

- Questions should test important concepts.
- Answers should be short and accurate.
- Avoid duplicate questions.
- Use only information supported by the material.
- Prioritize definitions, concepts, mechanisms, comparisons,
  and important facts.
""",
            retrieved_documents=retrieved_documents,
        )

    # ============================================================
    # STUDY GUIDE
    # ============================================================

    def generate_study_guide(
        self,
        retrieved_documents: list[dict[str, Any]],
    ) -> str:
        """
        Generate a complete study guide.
        """

        return self._generate(
            instruction="""
Create a structured study guide from the provided material.

Include:

# Study Guide

## 1. Core Concepts

## 2. Important Definitions

## 3. Important Relationships

## 4. Things to Memorize

## 5. Common Confusions

## 6. Quick Review

## 7. Self-Test Questions

Keep everything grounded in the supplied material.
""",
            retrieved_documents=retrieved_documents,
        )