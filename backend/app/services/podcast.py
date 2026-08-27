from pathlib import Path
import hashlib
import json
import re
import wave

from google import genai
from google.genai import types

from app.core.config import GEMINI_API_KEY
from app.services.generator import HybridGenerator


class PodcastGenerator:
    """
    Grounded Educational Podcast Generator.

    Pipeline:

        Retrieved RAG Documents
                    ↓
             Grounded Script
                    ↓
          Gemini / Groq Generator
                    ↓
              Gemini TTS
                    ↓
                 WAV

    Script generation:
        Gemini → Groq fallback chain

    Audio generation:
        Gemini TTS

    Features:
        - RAG grounded
        - PDF aware
        - YouTube timestamp aware
        - Script caching
        - Audio generation
        - WAV output
    """

    def __init__(
        self,
        text_model: str = "gemini-3.6-flash",
        tts_model: str = "gemini-2.5-flash-preview-tts",
        output_dir: str | Path = "data/podcasts",
        cache_dir: str | Path = "data/podcast_cache",
    ):

        self.text_model = text_model
        self.tts_model = tts_model

        # =====================================================
        # GEMINI CLIENT
        # =====================================================

        self.client = None

        if GEMINI_API_KEY:

            self.client = genai.Client(
                api_key=GEMINI_API_KEY
            )

        # =====================================================
        # HYBRID TEXT GENERATOR
        # =====================================================

        self.generator = HybridGenerator(
            gemini_model=text_model,
        )

        # =====================================================
        # DIRECTORIES
        # =====================================================

        self.output_dir = Path(
            output_dir
        )

        self.cache_dir = Path(
            cache_dir
        )

        self.output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # =========================================================
    # CACHE
    # =========================================================

    def _cache_key(
        self,
        topic: str,
        retrieved_documents: list[dict],
    ) -> str:

        content = {
            "topic": topic,
            "documents": [
                {
                    "text": doc.get("text", ""),
                    "source": doc.get("source", ""),
                    "page": doc.get("page", ""),
                    "start_time": doc.get(
                        "start_time",
                        "",
                    ),
                    "end_time": doc.get(
                        "end_time",
                        "",
                    ),
                }
                for doc in retrieved_documents
            ],
        }

        raw = json.dumps(
            content,
            ensure_ascii=False,
            sort_keys=True,
        )

        return hashlib.sha256(
            raw.encode("utf-8")
        ).hexdigest()

    def _cache_path(
        self,
        key: str,
    ) -> Path:

        return (
            self.cache_dir
            / f"{key}.txt"
        )

    def _load_script_cache(
        self,
        key: str,
    ):

        path = self._cache_path(
            key
        )

        if not path.exists():

            return None

        try:

            return path.read_text(
                encoding="utf-8"
            )

        except Exception:

            return None

    def _save_script_cache(
        self,
        key: str,
        script: str,
    ):

        path = self._cache_path(
            key
        )

        path.write_text(
            script,
            encoding="utf-8",
        )

    # =========================================================
    # CONTEXT
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
                "Unknown",
            )

            page = document.get(
                "page",
                "N/A",
            )

            start_timestamp = (
                document.get(
                    "start_timestamp",
                    document.get(
                        "timestamp_start",
                        "N/A",
                    ),
                )
            )

            end_timestamp = (
                document.get(
                    "end_timestamp",
                    document.get(
                        "timestamp_end",
                        "N/A",
                    ),
                )
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

Timestamp:
{start_timestamp} -> {end_timestamp}

Content:
{text}
"""
            )

        return "\n".join(
            context_parts
        )

    # =========================================================
    # PROMPT
    # =========================================================

    def _build_prompt(
        self,
        topic: str,
        context: str,
    ) -> str:

        return f"""
You are an expert educational podcast writer.

Create a short, engaging educational podcast
for a student.

The podcast MUST be grounded ONLY in the
provided evidence.

TOPIC:
{topic}

EVIDENCE:
{context}

RULES:

1. Never invent facts.
2. Never use outside knowledge.
3. If the evidence does not support something,
   do not mention it.
4. Explain difficult concepts simply.
5. Use natural conversational language.
6. Connect related concepts logically.
7. Define technical terminology when useful.
8. Do not mention RAG.
9. Do not mention retrieved documents.
10. Do not mention sources explicitly.
11. Do not use markdown.
12. Do not use tables.
13. Do not use bullet points.
14. Start with an engaging introduction.
15. Explain the core ideas.
16. Give simple examples only if supported
    by the evidence.
17. Finish with a concise recap.
18. If the evidence comes from YouTube and
    timestamps are available, naturally mention
    phrases such as:
    "Around the beginning of the video..."
    rather than reading raw timestamps.
19. Keep the podcast around 3–6 minutes.
20. Write ONLY the spoken script.

TOPIC:
{topic}
"""

    # =========================================================
    # SCRIPT GENERATION
    # =========================================================

    def generate_script(
        self,
        topic: str,
        retrieved_documents: list[dict],
    ) -> str:

        if not retrieved_documents:

            raise ValueError(
                "No retrieved documents available "
                "for podcast generation."
            )

        # -----------------------------------------------------
        # CACHE
        # -----------------------------------------------------

        cache_key = self._cache_key(
            topic,
            retrieved_documents,
        )

        cached_script = (
            self._load_script_cache(
                cache_key
            )
        )

        if cached_script:

            print(
                "✓ Using cached podcast script."
            )

            return cached_script

        # -----------------------------------------------------
        # Context
        # -----------------------------------------------------

        context = self._build_context(
            retrieved_documents
        )

        prompt = self._build_prompt(
            topic=topic,
            context=context,
        )

        print(
            "\n[Podcast] Generating script..."
        )

        # -----------------------------------------------------
        # HYBRID GENERATOR
        # -----------------------------------------------------

        script = self.generator.generate(
            question=prompt,
            retrieved_documents=[
                {
                    "text": context,
                    "source": "podcast_context",
                    "page": "N/A",
                }
            ],
        )

        script = self._clean_script(
            script
        )

        if not script:

            raise ValueError(
                "Podcast script is empty."
            )

        # -----------------------------------------------------
        # SAVE CACHE
        # -----------------------------------------------------

        self._save_script_cache(
            cache_key,
            script,
        )

        print(
            "✓ Podcast script generated."
        )

        return script

    # =========================================================
    # CLEAN SCRIPT
    # =========================================================

    def _clean_script(
        self,
        script: str,
    ) -> str:

        script = re.sub(
            r"[*_#`]",
            "",
            script,
        )

        script = re.sub(
            r"\n{3,}",
            "\n\n",
            script,
        )

        return script.strip()

    # =========================================================
    # SAVE WAV
    # =========================================================

    def _save_wav(
        self,
        pcm_data: bytes,
        output_path: Path,
        sample_rate: int = 24000,
    ):

        with wave.open(
            str(output_path),
            "wb",
        ) as wav:

            wav.setnchannels(1)

            wav.setsampwidth(2)

            wav.setframerate(
                sample_rate
            )

            wav.writeframes(
                pcm_data
            )

    # =========================================================
    # GEMINI TTS
    # =========================================================

    def generate_audio(
        self,
        script: str,
        filename: str = "podcast.wav",
    ) -> Path:

        if self.client is None:

            raise RuntimeError(
                "Gemini API key is not configured. "
                "Gemini TTS requires GEMINI_API_KEY."
            )

        script = self._clean_script(
            script
        )

        if not script:

            raise ValueError(
                "Podcast script is empty."
            )

        output_path = (
            self.output_dir
            / filename
        )

        print(
            "\n[Podcast] Generating audio "
            "with Gemini TTS..."
        )

        response = (
            self.client
            .models
            .generate_content(
                model=self.tts_model,
                contents=script,
                config=types.GenerateContentConfig(
                    response_modalities=[
                        "AUDIO"
                    ],
                    speech_config=(
                        types.SpeechConfig(
                            voice_config=(
                                types.VoiceConfig(
                                    prebuilt_voice_config=(
                                        types.PrebuiltVoiceConfig(
                                            voice_name="Kore"
                                        )
                                    )
                                )
                            )
                        )
                    ),
                ),
            )
        )

        if not response.candidates:

            raise ValueError(
                "No audio response returned."
            )

        parts = (
            response
            .candidates[0]
            .content
            .parts
        )

        audio_data = None

        for part in parts:

            if (
                part.inline_data
                and part.inline_data.data
            ):

                audio_data = (
                    part.inline_data.data
                )

                break

        if not audio_data:

            raise ValueError(
                "Gemini returned no audio data."
            )

        self._save_wav(
            pcm_data=audio_data,
            output_path=output_path,
        )

        print(
            f"✓ Podcast audio saved: "
            f"{output_path}"
        )

        return output_path

    # =========================================================
    # COMPLETE PIPELINE
    # =========================================================

    def generate(
        self,
        topic: str,
        retrieved_documents: list[dict],
        filename: str = "podcast.wav",
    ) -> tuple[str, Path]:

        print(
            "\n"
            + "=" * 70
        )

        print(
            "PODCAST GENERATION"
        )

        print(
            "=" * 70
        )

        # -----------------------------------------------------
        # SCRIPT
        # -----------------------------------------------------

        script = self.generate_script(
            topic=topic,
            retrieved_documents=(
                retrieved_documents
            ),
        )

        # -----------------------------------------------------
        # AUDIO
        # -----------------------------------------------------

        audio_path = self.generate_audio(
            script=script,
            filename=filename,
        )

        return (
            script,
            audio_path,
        )