from pathlib import Path

from PIL import Image
from google import genai

from app.core.config import GEMINI_API_KEY


class GeminiImageProcessor:

    def __init__(self):
        self.client = genai.Client(
            api_key=GEMINI_API_KEY
        )

        self.model = "gemini-3.5-flash"

    def analyze_image(
        self,
        image_path: str | Path,
        question: str | None = None,
    ) -> str:

        image = Image.open(image_path)

        if question:
            prompt = f"""
You are a helpful multimodal AI assistant.

Analyze the provided image carefully.

Answer the user's question based ONLY on
what can be observed in the image.

User question:
{question}

If the answer cannot be determined from
the image, clearly say that the information
is not available in the image.
"""
        else:
            prompt = """
Analyze this image carefully.

Provide a clear and detailed explanation of:

1. What the image contains
2. The important elements
3. Any visible text
4. Relationships between the elements
5. The overall meaning or purpose

Do not invent information that cannot be
supported by the image.
"""

        response = self.client.models.generate_content(
            model=self.model,
            contents=[
                prompt,
                image,
            ],
        )

        return response.text