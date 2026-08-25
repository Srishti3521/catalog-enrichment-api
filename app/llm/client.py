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
        prompt = f"""You are a product data enrichment assistant that structures footwear/apparel product data according to the GS1 Web Vocabulary standard.

Given this product, extract the following fields as JSON:
- gs1_upper_material_type (the material(s) used for the upper part of the footwear/apparel, e.g. "mesh", "leather")
- gs1_sporting_activity_type (the sporting/use activity the product is intended for, e.g. "running", "football")
- gs1_target_consumer_gender (e.g. "male", "female", "unisex")
- gs1_is_waterproof (true, false, or null if not mentioned — whether the product claims waterproofing)
- gs1_product_feature_benefit (2-4 standout features/benefits as a single comma-separated string)
- gs1_consumer_lifestage (who this product is designed for, e.g. "adult", "youth")
- gs1_fastening_type (how the product fastens, e.g. "laces", "velcro", "slip-on", or null if not footwear/not mentioned)
- gs1_footwear_upper_type ("open" or "closed", or null if not footwear/not mentioned)
- gs1_is_patterned (true, false, or null if not mentioned — whether the product has a patterned design)
- gs1_is_thermal (true, false, or null if not mentioned — whether the product is thermal/insulated)
- gs1_style_description (a short phrase describing the style, e.g. "athletic", "casual lifestyle")
- gs1_storage_instructions (care/storage instructions if mentioned, else null)
- gs1_recycling_instructions (recycling instructions if mentioned, else null)
- differentiators (what makes this specific product distinct from similar products, based only on the given description)

Rules:
- Return ONLY valid JSON, nothing else. No explanation, no markdown formatting.
- If a field cannot be reasonably inferred, use null.
- For boolean fields, use true/false only when the description gives real signal; otherwise null. Do not default to false when unsure — use null.
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
                    wait_time = 15 * (attempt + 1)
                    print(f"Rate limited, waiting {wait_time}s before retry...")
                    time.sleep(wait_time)
                else:
                    raise

    def compare(self, product_a: dict, product_b: dict) -> dict:
        prompt = f"""You are an AI shopping assistant evaluator.

Given two enriched product profiles below, determine which one an AI shopping assistant would more likely recommend for a relevant shopping query, and explain why — based only on the structured information provided, not on brand reputation or price.

Always refer to each product by its actual name in your reasoning — never use generic labels like "Product A" or "Product B".

{product_a['name']}:
Material: {product_a['material']}
Use case: {product_a['use_case']}
Size range: {product_a['size_range']}
Gender: {product_a['gender']}
Weather resistance: {product_a['weather_resistance']}
Key features: {product_a['key_features']}
Target audience: {product_a['target_audience']}
Differentiators: {product_a['differentiators']}

{product_b['name']}:
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
  "reasoning": "a short paragraph explaining the decision, referring to each product by its actual name given above, never as 'Product A' or 'Product B'",
  "product_a_gaps": ["list of fields the first product is missing that the second has"],
  "product_b_gaps": ["list of fields the second product is missing that the first has"]
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

    def embed_text(self, text: str) -> list:
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = self.client.models.embed_content(
                    model="gemini-embedding-001",
                    contents=text,
                )
                embedding_obj = response.embeddings[0]
                return list(embedding_obj.values)
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