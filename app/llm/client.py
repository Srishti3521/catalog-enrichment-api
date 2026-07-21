from google import genai
from google.genai import types
import json
import re
import time
from app.core.config import settings

class LLMClient:
    def __init__(self):
        self.client = genai.Client(api_key=settings.LLM_API_KEY)
        self.model = "gemini-flash-lite-latest"

    def enrich(self, name: str, description: str) -> dict:
        prompt = f"""You are a product data enrichment assistant.

Given this product, extract the following fields as JSON:
- material
- use_case
- size_range
- gender
- weather_resistance

Rules:
- Return ONLY valid JSON, nothing else. No explanation, no markdown formatting.
- If a field cannot be reasonably inferred, use null.
- Do not guess wildly — only fill a field if the name/description gives real signal.

Product name: {name}
Product description: {description}
"""

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.models.generate_content(
                    model=self.model,
                    contents=prompt,
                )
                raw_text = response.text.strip()
                return self._parse_response(raw_text)
            except Exception as e:
                if "RESOURCE_EXHAUSTED" in str(e) and attempt < max_retries - 1:
                    wait_time = 15 * (attempt + 1)  # 15s, 30s, 45s
                    print(f"Rate limited, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise

    def _parse_response(self, raw_text: str) -> dict:
        try:
            return json.loads(raw_text)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", raw_text, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    pass
        return {"_parse_failed": True, "_raw_response": raw_text}