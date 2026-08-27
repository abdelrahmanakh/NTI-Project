from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse, parse_qs
import json
import re

from youtube_transcript_api import YouTubeTranscriptApi


class YouTubeProcessor:
    """
    YouTube transcript processor for RAG.

    Pipeline:

        YouTube URL
            ↓
        Extract video ID
            ↓
        Fetch transcript
            ↓
        Clean transcript
            ↓
        Timestamp-aware chunks
            ↓
        Documents ready for embedding
    """

    def __init__(
        self,
        languages: list[str] | None = None,
        cache_dir: str | Path = "data/youtube_cache",
        chunk_duration: float = 60.0,
    ):
        self.languages = (
            languages
            if languages
            else [
                "en",
                "ar",
            ]
        )

        self.cache_dir = Path(
            cache_dir
        )

        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        self.chunk_duration = (
            chunk_duration
        )

        self.api = (
            YouTubeTranscriptApi()
        )

    # ============================================================
    # VIDEO ID
    # ============================================================

    @staticmethod
    def extract_video_id(
        url: str,
    ) -> str:
        """
        Extract YouTube video ID from common URL formats.

        Supports:

            https://www.youtube.com/watch?v=VIDEO_ID
            https://youtu.be/VIDEO_ID
            https://www.youtube.com/shorts/VIDEO_ID
            https://www.youtube.com/embed/VIDEO_ID
            https://www.youtube.com/live/VIDEO_ID
        """

        if not url:
            raise ValueError(
                "YouTube URL is empty."
            )

        url = url.strip()

        # --------------------------------------------------------
        # youtu.be
        # --------------------------------------------------------

        parsed = urlparse(url)

        if parsed.hostname in {
            "youtu.be",
            "www.youtu.be",
        }:

            video_id = (
                parsed.path
                .strip("/")
                .split("/")
            )

            if video_id:
                return video_id[0]

        # --------------------------------------------------------
        # youtube.com
        # --------------------------------------------------------

        if parsed.hostname in {
            "youtube.com",
            "www.youtube.com",
            "m.youtube.com",
        }:

            # /watch?v=...
            query = parse_qs(
                parsed.query
            )

            if "v" in query:

                return query["v"][0]

            # /shorts/...
            path_parts = [
                part
                for part in parsed.path.split("/")
                if part
            ]

            if path_parts:

                if path_parts[0] in {
                    "shorts",
                    "embed",
                    "live",
                } and len(path_parts) >= 2:

                    return path_parts[1]

        # --------------------------------------------------------
        # Maybe user supplied the ID directly
        # --------------------------------------------------------

        if re.fullmatch(
            r"[A-Za-z0-9_-]{11}",
            url,
        ):

            return url

        raise ValueError(
            "Invalid YouTube URL or video ID.\n"
            "Expected something like:\n"
            "https://www.youtube.com/watch?v=VIDEO_ID"
        )

    # ============================================================
    # CACHE
    # ============================================================

    def _cache_path(
        self,
        video_id: str,
    ) -> Path:

        return (
            self.cache_dir
            / f"{video_id}.json"
        )

    def _load_cache(
        self,
        video_id: str,
    ):

        path = self._cache_path(
            video_id
        )

        if not path.exists():
            return None

        try:

            with open(
                path,
                "r",
                encoding="utf-8",
            ) as file:

                return json.load(file)

        except Exception:

            return None

    def _save_cache(
        self,
        video_id: str,
        data: dict,
    ):

        path = self._cache_path(
            video_id
        )

        with open(
            path,
            "w",
            encoding="utf-8",
        ) as file:

            json.dump(
                data,
                file,
                ensure_ascii=False,
                indent=2,
            )

    # ============================================================
    # CLEAN TEXT
    # ============================================================

    @staticmethod
    def clean_text(
        text: str,
    ) -> str:
        """
        Clean transcript text.
        """

        if not text:
            return ""

        # Remove excessive whitespace
        text = re.sub(
            r"\s+",
            " ",
            text,
        )

        return text.strip()

    # ============================================================
    # FORMAT TIME
    # ============================================================

    @staticmethod
    def format_timestamp(
        seconds: float,
    ) -> str:
        """
        Convert seconds to HH:MM:SS.
        """

        seconds = int(
            max(0, seconds)
        )

        hours = seconds // 3600

        minutes = (
            seconds % 3600
        ) // 60

        secs = (
            seconds % 60
        )

        return (
            f"{hours:02d}:"
            f"{minutes:02d}:"
            f"{secs:02d}"
        )

    # ============================================================
    # FETCH TRANSCRIPT
    # ============================================================

    def fetch_transcript(
        self,
        video_id: str,
    ) -> dict:

        print(
            f"\nFetching YouTube transcript..."
        )

        print(
            f"Video ID: {video_id}"
        )

        print(
            f"Languages: {self.languages}"
        )

        # --------------------------------------------------------
        # Cache
        # --------------------------------------------------------

        cached = self._load_cache(
            video_id
        )

        if cached:

            print(
                "✓ Found cached YouTube transcript."
            )

            return cached

        # --------------------------------------------------------
        # Fetch
        # --------------------------------------------------------

        try:

            transcript = self.api.fetch(
                video_id,
                languages=self.languages,
            )

        except Exception as exc:

            raise RuntimeError(
                "Failed to fetch YouTube transcript.\n"
                f"Video ID: {video_id}\n"
                f"Languages: {self.languages}\n"
                f"Original error: {exc}"
            ) from exc

        # --------------------------------------------------------
        # Convert snippets
        # --------------------------------------------------------

        snippets = []

        for snippet in transcript:

            text = self.clean_text(
                snippet.text
            )

            if not text:
                continue

            start = float(
                snippet.start
            )

            duration = float(
                snippet.duration
            )

            end = (
                start
                + duration
            )

            snippets.append(
                {
                    "text": text,
                    "start": start,
                    "end": end,
                    "duration": duration,
                }
            )

        if not snippets:

            raise ValueError(
                "YouTube transcript was empty."
            )

        data = {
            "video_id": video_id,
            "language": getattr(
                transcript,
                "language",
                None,
            ),
            "language_code": getattr(
                transcript,
                "language_code",
                None,
            ),
            "is_generated": getattr(
                transcript,
                "is_generated",
                None,
            ),
            "snippets": snippets,
        }

        self._save_cache(
            video_id,
            data,
        )

        print(
            f"✓ Transcript fetched."
        )

        print(
            f"✓ Snippets: "
            f"{len(snippets)}"
        )

        return data

    # ============================================================
    # CREATE TIMESTAMP CHUNKS
    # ============================================================

    def create_chunks(
        self,
        transcript_data: dict,
        video_url: str,
    ) -> list[dict]:
        """
        Group transcript snippets into
        timestamp-aware RAG chunks.
        """

        snippets = transcript_data[
            "snippets"
        ]

        video_id = transcript_data[
            "video_id"
        ]

        chunks = []

        current_text = []

        chunk_start = None

        chunk_end = None

        chunk_index = 0

        for snippet in snippets:

            start = float(
                snippet["start"]
            )

            end = float(
                snippet["end"]
            )

            text = snippet["text"]

            if chunk_start is None:

                chunk_start = start

            current_text.append(
                text
            )

            chunk_end = end

            elapsed = (
                chunk_end
                - chunk_start
            )

            if (
                elapsed
                >= self.chunk_duration
            ):

                combined_text = (
                    " ".join(
                        current_text
                    ).strip()
                )

                if combined_text:

                    chunks.append(
                        {
                            "text": combined_text,
                            "page": 0,
                            "source": "youtube",
                            "video_id": video_id,
                            "url": video_url,
                            "start_time": chunk_start,
                            "end_time": chunk_end,
                            "start_timestamp": (
                                self.format_timestamp(
                                    chunk_start
                                )
                            ),
                            "end_timestamp": (
                                self.format_timestamp(
                                    chunk_end
                                )
                            ),
                            "chunk_index": chunk_index,
                        }
                    )

                    chunk_index += 1

                current_text = []

                chunk_start = None

                chunk_end = None

        # --------------------------------------------------------
        # Remaining text
        # --------------------------------------------------------

        if current_text:

            combined_text = (
                " ".join(
                    current_text
                ).strip()
            )

            if combined_text:

                chunks.append(
                    {
                        "text": combined_text,
                        "page": 0,
                        "source": "youtube",
                        "video_id": video_id,
                        "url": video_url,
                        "start_time": chunk_start,
                        "end_time": chunk_end,
                        "start_timestamp": (
                            self.format_timestamp(
                                chunk_start
                            )
                        ),
                        "end_timestamp": (
                            self.format_timestamp(
                                chunk_end
                            )
                        ),
                        "chunk_index": chunk_index,
                    }
                )

        return chunks

    # ============================================================
    # MAIN PROCESSOR
    # ============================================================

    def process(
        self,
        url: str,
    ) -> list[dict]:
        """
        Full YouTube → RAG pipeline.

        Returns documents compatible with
        the existing chunking/vector-store pipeline.
        """

        print(
            "\n"
            + "=" * 70
        )

        print(
            "YOUTUBE PROCESSING"
        )

        print(
            "=" * 70
        )

        # --------------------------------------------------------
        # Extract ID
        # --------------------------------------------------------

        video_id = (
            self.extract_video_id(
                url
            )
        )

        print(
            f"✓ Video ID: {video_id}"
        )

        # --------------------------------------------------------
        # Transcript
        # --------------------------------------------------------

        transcript_data = (
            self.fetch_transcript(
                video_id
            )
        )

        # --------------------------------------------------------
        # Chunks
        # --------------------------------------------------------

        chunks = (
            self.create_chunks(
                transcript_data,
                url,
            )
        )

        if not chunks:

            raise ValueError(
                "No YouTube chunks were created."
            )

        print(
            f"✓ Created YouTube chunks: "
            f"{len(chunks)}"
        )

        print(
            "\nFirst chunk:"
        )

        print(
            chunks[0]["text"][:500]
        )

        print(
            f"\nTimestamp: "
            f"{chunks[0]['start_timestamp']}"
            f" → "
            f"{chunks[0]['end_timestamp']}"
        )

        return chunks