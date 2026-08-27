from pathlib import Path
import base64
import json
import re

from pypdf import PdfReader
from google import genai
from google.genai import types
from groq import Groq

from app.core.config import GEMINI_API_KEY


class PDFLoader:
    """
    Hybrid PDF Loader.

    Supports:
        1. Text-based PDFs
        2. Scanned/image-based PDFs
        3. Mixed PDFs

    OCR strategy:

        Gemini Vision
             ↓
        if Gemini fails
             ↓
        Groq Vision
             ↓
        Cache result

    The OCR cache prevents re-processing the
    same PDF repeatedly.
    """

    def __init__(
        self,
        vision_model: str = "gemini-3.6-flash",
        groq_vision_model: str = "qwen/qwen3.6-27b",
        cache_dir: str | Path = "data/ocr_cache",
    ):

        self.vision_model = vision_model

        self.groq_vision_model = (
            groq_vision_model
        )

        # =====================================================
        # GEMINI
        # =====================================================

        self.gemini_client = None

        if GEMINI_API_KEY:

            self.gemini_client = genai.Client(
                api_key=GEMINI_API_KEY
            )

        # =====================================================
        # GROQ
        # =====================================================

        import os

        groq_api_key = os.getenv(
            "GROQ_API_KEY"
        )

        self.groq_client = None

        if groq_api_key:

            self.groq_client = Groq(
                api_key=groq_api_key
            )

        # =====================================================
        # CACHE
        # =====================================================

        self.cache_dir = Path(
            cache_dir
        )

        self.cache_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

    # =========================================================
    # CACHE PATH
    # =========================================================

    def _cache_path(
        self,
        file_path: Path,
    ) -> Path:

        safe_name = re.sub(
            r"[^a-zA-Z0-9_.-]+",
            "_",
            file_path.stem,
        )

        return (
            self.cache_dir
            / f"{safe_name}_ocr.json"
        )

    # =========================================================
    # LOAD CACHE
    # =========================================================

    def _load_cache(
        self,
        file_path: Path,
    ):

        cache_path = self._cache_path(
            file_path
        )

        if not cache_path.exists():

            return None

        try:

            with open(
                cache_path,
                "r",
                encoding="utf-8",
            ) as f:

                data = json.load(f)

            if not isinstance(
                data,
                list,
            ):

                return None

            return data

        except Exception as exc:

            print(
                f"Warning: failed to read "
                f"OCR cache: {exc}"
            )

            return None

    # =========================================================
    # SAVE CACHE
    # =========================================================

    def _save_cache(
        self,
        file_path: Path,
        documents: list[dict],
    ):

        cache_path = self._cache_path(
            file_path
        )

        try:

            with open(
                cache_path,
                "w",
                encoding="utf-8",
            ) as f:

                json.dump(
                    documents,
                    f,
                    ensure_ascii=False,
                    indent=2,
                )

            print(
                f"\n✓ OCR cache saved:"
                f"\n  {cache_path}"
            )

        except Exception as exc:

            print(
                f"Warning: failed to save "
                f"OCR cache: {exc}"
            )

    # =========================================================
    # NORMAL TEXT EXTRACTION
    # =========================================================

    def _extract_text(
        self,
        file_path: Path,
    ) -> list[dict]:

        reader = PdfReader(
            str(file_path)
        )

        documents = []

        for page_number, page in enumerate(
            reader.pages,
            start=1,
        ):

            try:

                text = (
                    page.extract_text()
                    or ""
                )

            except Exception as exc:

                print(
                    f"Warning: text extraction "
                    f"failed on page "
                    f"{page_number}: {exc}"
                )

                text = ""

            text = text.strip()

            if not text:

                continue

            documents.append(
                {
                    "text": text,
                    "page": page_number,
                    "source": file_path.name,
                }
            )

        return documents

    # =========================================================
    # OCR PROMPT
    # =========================================================

    def _ocr_prompt(self) -> str:

        return """
You are an expert OCR and document-understanding system.

The attached PDF is a scanned/image-based educational
document.

Extract the meaningful content from EVERY page.

IMPORTANT:

1. Preserve page order.
2. Preserve headings.
3. Preserve paragraphs.
4. Preserve bullet points.
5. Preserve numbered lists.
6. Preserve tables as readable text.
7. Preserve code snippets when visible.
8. Preserve formulas when reasonably readable.
9. Describe meaningful diagrams, figures, and charts.
10. Do NOT summarize the document.
11. Do NOT answer questions.
12. Do NOT invent information.
13. Return the extracted content only.
14. Clearly separate every page.

Use EXACTLY this format:

--- PAGE 1 ---

content from page 1

--- PAGE 2 ---

content from page 2

--- PAGE 3 ---

content from page 3

Continue until the final page.
"""

    # =========================================================
    # GEMINI OCR
    # =========================================================

    def _ocr_with_gemini(
        self,
        file_path: Path,
    ) -> list[dict]:

        if self.gemini_client is None:

            raise RuntimeError(
                "GEMINI_API_KEY is not configured."
            )

        print(
            "\n----------------------------------------"
        )

        print(
            "OCR PROVIDER: GEMINI"
        )

        print(
            "----------------------------------------"
        )

        pdf_bytes = file_path.read_bytes()

        print(
            f"PDF size: "
            f"{len(pdf_bytes) / (1024 * 1024):.2f} MB"
        )

        response = (
            self.gemini_client
            .models
            .generate_content(
                model=self.vision_model,
                contents=[
                    types.Part.from_bytes(
                        data=pdf_bytes,
                        mime_type="application/pdf",
                    ),
                    self._ocr_prompt(),
                ],
            )
        )

        raw_text = (
            response.text
            or ""
        ).strip()

        if not raw_text:

            raise ValueError(
                "Gemini returned empty OCR output."
            )

        documents = (
            self._parse_page_output(
                raw_text,
                file_path.name,
            )
        )

        if not documents:

            raise ValueError(
                "Gemini OCR produced no documents."
            )

        return documents

    # =========================================================
    # RENDER PDF PAGES
    # =========================================================

    def _render_pdf_pages(
        self,
        file_path: Path,
    ) -> list[bytes]:

        try:

            import pymupdf

        except ImportError:

            try:

                import fitz as pymupdf

            except ImportError as exc:

                raise RuntimeError(
                    "PyMuPDF is required for "
                    "Groq Vision OCR."
                ) from exc

        print(
            "\nRendering PDF pages for "
            "Groq Vision..."
        )

        pdf = pymupdf.open(
            str(file_path)
        )

        images = []

        try:

            for page_number, page in enumerate(
                pdf,
                start=1,
            ):

                pix = page.get_pixmap(
                    matrix=pymupdf.Matrix(
                        1.5,
                        1.5,
                    ),
                    alpha=False,
                )

                image_bytes = pix.tobytes(
                    "jpeg"
                )

                images.append(
                    image_bytes
                )

                print(
                    f"  ✓ Rendered page "
                    f"{page_number}/{len(pdf)} "
                    f"({len(image_bytes) / 1024:.1f} KB)"
                )

        finally:

            pdf.close()

        return images

    # =========================================================
    # GROQ OCR
    # =========================================================

    def _ocr_with_groq(
        self,
        file_path: Path,
    ) -> list[dict]:

        if self.groq_client is None:

            raise RuntimeError(
                "GROQ_API_KEY is not configured."
            )

        print(
            "\n----------------------------------------"
        )

        print(
            "OCR PROVIDER: GROQ VISION"
        )

        print(
            f"Model: {self.groq_vision_model}"
        )

        print(
            "----------------------------------------"
        )

        images = self._render_pdf_pages(
            file_path
        )

        documents = []

        total_pages = len(
            images
        )

        for index, image_bytes in enumerate(
            images,
            start=1,
        ):

            print(
                f"\nOCR page "
                f"{index}/{total_pages}..."
            )

            base64_image = (
                base64.b64encode(
                    image_bytes
                ).decode("utf-8")
            )

            prompt = f"""
You are an expert OCR system.

Extract ALL meaningful content visible
in this document page.

This is page {index} of {total_pages}.

Rules:

- Preserve headings.
- Preserve paragraphs.
- Preserve bullet points.
- Preserve numbered lists.
- Preserve tables as readable text.
- Preserve code when visible.
- Preserve formulas when readable.
- Describe meaningful diagrams briefly.
- Do not summarize.
- Do not invent information.
- Return only the extracted content.
"""

            response = (
                self.groq_client
                .chat
                .completions
                .create(
                    model=self.groq_vision_model,
                    messages=[
                        {
                            "role": "system",
                            "content": (
                                "You are a precise "
                                "OCR and document "
                                "understanding system."
                            ),
                        },
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt,
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": (
                                            "data:image/jpeg;"
                                            "base64,"
                                            f"{base64_image}"
                                        )
                                    },
                                },
                            ],
                        },
                    ],
                    temperature=0.1,
                    max_completion_tokens=4096,
                )
            )

            text = (
                response
                .choices[0]
                .message
                .content
                or ""
            ).strip()

            if not text:

                print(
                    f"  ⚠ Empty OCR result "
                    f"for page {index}"
                )

                continue

            documents.append(
                {
                    "text": text,
                    "page": index,
                    "source": file_path.name,
                }
            )

            print(
                f"  ✓ OCR completed "
                f"for page {index}"
            )

        return documents

    # =========================================================
    # PARSE GEMINI PAGE OUTPUT
    # =========================================================

    def _parse_page_output(
        self,
        text: str,
        source: str,
    ) -> list[dict]:

        pattern = re.compile(
            r"---\s*PAGE\s+(\d+)\s*---",
            re.IGNORECASE,
        )

        matches = list(
            pattern.finditer(text)
        )

        documents = []

        # -----------------------------------------------------
        # No page markers
        # -----------------------------------------------------

        if not matches:

            print(
                "Warning: OCR output did not "
                "contain page markers."
            )

            if text.strip():

                documents.append(
                    {
                        "text": text.strip(),
                        "page": 1,
                        "source": source,
                    }
                )

            return documents

        # -----------------------------------------------------
        # Parse pages
        # -----------------------------------------------------

        for index, match in enumerate(
            matches
        ):

            page_number = int(
                match.group(1)
            )

            start = match.end()

            if index + 1 < len(matches):

                end = matches[
                    index + 1
                ].start()

            else:

                end = len(text)

            page_text = (
                text[start:end]
                .strip()
            )

            if not page_text:

                continue

            documents.append(
                {
                    "text": page_text,
                    "page": page_number,
                    "source": source,
                }
            )

        return documents

    # =========================================================
    # MAIN LOAD
    # =========================================================

    def load(
        self,
        file_path: str | Path,
    ) -> list[dict]:

        file_path = Path(
            file_path
        )

        # =====================================================
        # VALIDATION
        # =====================================================

        if not file_path.exists():

            raise FileNotFoundError(
                f"PDF file not found: "
                f"{file_path}"
            )

        if file_path.suffix.lower() != ".pdf":

            raise ValueError(
                f"Expected a PDF file, "
                f"got: {file_path.suffix}"
            )

        print(
            f"\nLoading PDF: "
            f"{file_path.name}"
        )

        # =====================================================
        # CACHE FIRST
        # =====================================================

        cached_documents = (
            self._load_cache(
                file_path
            )
        )

        if cached_documents:

            print(
                "\n✓ Found cached OCR."
            )

            print(
                f"Using "
                f"{len(cached_documents)} "
                f"cached documents."
            )

            return cached_documents

        # =====================================================
        # LOCAL TEXT EXTRACTION
        # =====================================================

        text_documents = (
            self._extract_text(
                file_path
            )
        )

        print(
            f"Text pages detected: "
            f"{len(text_documents)}"
        )

        # =====================================================
        # TOTAL PAGES
        # =====================================================

        reader = PdfReader(
            str(file_path)
        )

        total_pages = len(
            reader.pages
        )

        print(
            f"Total PDF pages: "
            f"{total_pages}"
        )

        # =====================================================
        # TEXT PDF
        # =====================================================

        if (
            total_pages > 0
            and len(text_documents)
            >= total_pages * 0.7
        ):

            print(
                "\n✓ This appears to be "
                "a text-based PDF."
            )

            return text_documents

        # =====================================================
        # SCANNED PDF
        # =====================================================

        print(
            "\n✓ This appears to be "
            "a scanned/image-based PDF."
        )

        print(
            "\nOCR fallback chain:"
        )

        print(
            "1. Gemini Vision"
        )

        print(
            "2. Groq Vision"
        )

        # =====================================================
        # TRY GEMINI
        # =====================================================

        if self.gemini_client is not None:

            try:

                documents = (
                    self._ocr_with_gemini(
                        file_path
                    )
                )

                if documents:

                    self._save_cache(
                        file_path,
                        documents,
                    )

                    print(
                        "\n✓ Gemini OCR succeeded."
                    )

                    print(
                        f"Loaded documents: "
                        f"{len(documents)}"
                    )

                    return documents

            except Exception as exc:

                print(
                    "\n⚠ Gemini OCR failed."
                )

                print(
                    f"Reason: {exc}"
                )

                print(
                    "\nSwitching to "
                    "Groq Vision..."
                )

        # =====================================================
        # TRY GROQ
        # =====================================================

        if self.groq_client is not None:

            try:

                documents = (
                    self._ocr_with_groq(
                        file_path
                    )
                )

                if documents:

                    self._save_cache(
                        file_path,
                        documents,
                    )

                    print(
                        "\n✓ Groq Vision OCR succeeded."
                    )

                    print(
                        f"Loaded documents: "
                        f"{len(documents)}"
                    )

                    return documents

            except Exception as exc:

                print(
                    "\n❌ Groq Vision OCR failed."
                )

                print(
                    f"Reason: {exc}"
                )

        # =====================================================
        # EVERYTHING FAILED
        # =====================================================

        raise RuntimeError(
            "\n\n❌ PDF OCR failed.\n\n"
            "Both Gemini Vision and Groq "
            "Vision were unable to process "
            "this scanned PDF.\n\n"
            "Possible causes:\n"
            "- Gemini quota exhausted\n"
            "- Groq quota exhausted\n"
            "- Invalid API key\n"
            "- Vision model unavailable\n"
            "- Network/API error\n"
        )