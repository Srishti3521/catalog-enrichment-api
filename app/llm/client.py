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
- key_features (a short list of 2-4 standout features, as a single comma-separated string)
- target_audience (who this product is best suited for, e.g. "casual runners", "professional athletes")
- differentiators (what makes this product distinct from similar products, based only on the given description)

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
    def compare(self, product_a: dict, product_b: dict) -> dict:
        prompt = f"""You are an AI shopping assistant evaluator.

Given two enriched product profiles below, determine which one an AI shopping assistant would more likely recommend for a relevant shopping query, and explain why — based only on the structured information provided, not on brand reputation or price.

Product A:
Name: {product_a['name']}
Material: {product_a['material']}
Use case: {product_a['use_case']}
Size range: {product_a['size_range']}
Gender: {product_a['gender']}
Weather resistance: {product_a['weather_resistance']}
Key features: {product_a['key_features']}
Target audience: {product_a['target_audience']}
Differentiators: {product_a['differentiators']}

Product B:
Name: {product_b['name']}
Material: {product_b['material']}
Use case: {product_b['use_case']}
Size range: {product_b['size_range']}
Gender: {product_b['gender']}
Weather resistance: {product_b['weather_resistance']}
Key features: {product_b['key_features']}
Target audience: {product_b['target_audience']}
Differentiators: {product_b['differentiators']}

Return ONLY valid JSON in this exact shape, nothing else:
{{
  "likely_recommended": "product_a" or "product_b" or "tie",
  "reasoning": "a short paragraph explaining the decision, referencing specific missing or present attributes",
  "product_a_gaps": ["list of fields product A is missing that product B has"],
  "product_b_gaps": ["list of fields product B is missing that product A has"]
}}
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
                    wait_time = 15 * (attempt + 1)
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
    
    def check_visibility(self, query: str, watched_brands: list[str]) -> dict:
        brands_str = ", ".join(watched_brands)
        prompt = f"""You are simulating how an AI shopping assistant would answer a real customer's question.

Answer this shopping question naturally, as if a customer asked you directly, recommending real, specific products or brands:

"{query}"

After answering naturally, also return a structured analysis. Respond in this exact JSON shape, nothing else, no markdown:

{{
  "natural_answer": "your natural, realistic shopping recommendation response as a normal AI assistant would give",
  "mentioned_brands": ["list of brand names from this set that you genuinely mentioned in your natural_answer: {brands_str}"],
  "reasoning": "one sentence on why you did or didn't mention brands from that watched list"
}}
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
                    wait_time = 15 * (attempt + 1)
                    print(f"Rate limited, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise