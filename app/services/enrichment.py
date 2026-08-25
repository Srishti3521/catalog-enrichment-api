import asyncio
import csv
import io
import json
import math
from app.llm.client import LLMClient
from app.repositories.product_repo import ProductRepository
from app.repositories.job_repo import JobRepository
from app.core.database import SessionLocal

ENRICHED_FIELDS = [
    "gs1_upper_material_type", "gs1_sporting_activity_type", "gs1_target_consumer_gender",
    "gs1_is_waterproof", "gs1_product_feature_benefit", "gs1_consumer_lifestage",
    "gs1_fastening_type", "gs1_footwear_upper_type", "gs1_is_patterned", "gs1_is_thermal",
    "gs1_style_description", "gs1_storage_instructions", "gs1_recycling_instructions",
    "differentiators",
]

BOOLEAN_FIELDS = {"gs1_is_waterproof", "gs1_is_patterned", "gs1_is_thermal"}


def _to_string(value):
    if isinstance(value, list):
        return ", ".join(str(v) for v in value)
    return value


def _is_filled(value):
    """A boolean False is a real, meaningful answer — only None/empty counts as missing."""
    if value is None:
        return False
    if isinstance(value, str) and value.strip() == "":
        return False
    return True


def compute_completeness_score(enriched_data: dict) -> float:
    filled = sum(1 for field in ENRICHED_FIELDS if _is_filled(enriched_data.get(field)))
    return round(filled / len(ENRICHED_FIELDS), 2)


def flag_needs_review(enriched_data: dict, completeness_score: float = None) -> bool:
    vague_values = {"various", "unknown", "n/a", "unclear", "assorted"}
    for field in ENRICHED_FIELDS:
        if field in BOOLEAN_FIELDS:
            continue
        value = enriched_data.get(field)
        if isinstance(value, list):
            value = ", ".join(str(v) for v in value)
        if value and str(value).strip().lower() in vague_values:
            return True
    if completeness_score is not None and completeness_score < 0.7:
        return True
    return False


FIELD_LABELS = {
    "gs1_upper_material_type": "upper material",
    "gs1_sporting_activity_type": "sporting activity type",
    "gs1_target_consumer_gender": "target consumer gender",
    "gs1_is_waterproof": "waterproof status",
    "gs1_product_feature_benefit": "product feature benefit",
    "gs1_consumer_lifestage": "consumer lifestage",
    "gs1_fastening_type": "fastening type",
    "gs1_footwear_upper_type": "footwear upper type",
    "gs1_is_patterned": "patterned status",
    "gs1_is_thermal": "thermal status",
    "gs1_style_description": "style description",
    "gs1_storage_instructions": "storage instructions",
    "gs1_recycling_instructions": "recycling instructions",
    "differentiators": "differentiators",
}


def build_gap_summary(enriched_data: dict) -> tuple:
    missing = [field for field in ENRICHED_FIELDS if not _is_filled(enriched_data.get(field))]

    if not missing:
        return "", "This listing has all GS1-aligned attributes filled in, giving AI systems and retail systems strong signal to recommend it confidently."

    labels = [FIELD_LABELS[f] for f in missing]
    if len(labels) == 1:
        joined = labels[0]
    elif len(labels) == 2:
        joined = f"{labels[0]} and {labels[1]}"
    else:
        joined = ", ".join(labels[:-1]) + f", and {labels[-1]}"

    summary = (
        f"This listing is missing {joined}, which limits how confidently AI systems "
        f"can match and recommend it for related searches."
    )
    return ", ".join(missing), summary


def to_schema_org(product) -> dict:
    """Formats an enriched product as schema.org/Product JSON-LD using real GS1 namespace properties."""
    additional_properties = []

    def add(name, value):
        if _is_filled(value):
            additional_properties.append({"@type": "PropertyValue", "name": name, "value": value})

    add("gs1:upperMaterialType", product.gs1_upper_material_type)
    add("gs1:sportingActivityType", product.gs1_sporting_activity_type)
    add("gs1:targetConsumerGender", product.gs1_target_consumer_gender)
    add("gs1:isWaterproof", product.gs1_is_waterproof)
    add("gs1:consumerLifestage", product.gs1_consumer_lifestage)
    add("gs1:footwearFasteningType", product.gs1_fastening_type)
    add("gs1:footwearUpperType", product.gs1_footwear_upper_type)
    add("gs1:isPatterned", product.gs1_is_patterned)
    add("gs1:isThermal", product.gs1_is_thermal)
    add("gs1:styleDescription", product.gs1_style_description)
    add("gs1:colourDescription", product.gs1_colour_description)
    add("gs1:size", product.gs1_size)
    add("gs1:brand", product.gs1_brand)
    add("gs1:countryOfOrigin", product.gs1_country_of_origin)
    add("gs1:seasonName", product.gs1_season_name)
    add("gs1:netWeight", product.gs1_net_weight)

    schema = {
        "@context": {"@vocab": "https://schema.org/", "gs1": "https://gs1.org/voc/"},
        "@type": "Product",
        "name": product.name,
        "description": product.description,
        "additionalProperty": additional_properties,
    }

    if product.gs1_product_feature_benefit:
        schema["keywords"] = product.gs1_product_feature_benefit

    return schema


def cosine_similarity(vec_a, vec_b):
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = math.sqrt(sum(a * a for a in vec_a))
    norm_b = math.sqrt(sum(b * b for b in vec_b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def enrich_and_save(name: str, description: str, llm: LLMClient, repo: ProductRepository,
                     price: float = None, currency: str = None, availability: str = None,
                     rating: float = None, gs1_colour_description: str = None,
                     gs1_size: str = None, gs1_referenced_file: str = None,
                     gs1_brand: str = None, gs1_country_of_origin: str = None,
                     gs1_season_name: str = None, gs1_net_weight: str = None,
                     is_competitor: bool = False, job_id: str = None) -> dict:
    enriched_data = llm.enrich(name, description)

    base_record = {
        "name": name,
        "description": description,
        "price": price,
        "currency": currency,
        "availability": availability,
        "rating": rating,
        "gs1_colour_description": gs1_colour_description,
        "gs1_size": gs1_size,
        "gs1_referenced_file": gs1_referenced_file,
        "gs1_brand": gs1_brand,
        "gs1_country_of_origin": gs1_country_of_origin,
        "gs1_season_name": gs1_season_name,
        "gs1_net_weight": gs1_net_weight,
        "is_competitor": is_competitor,
        "job_id": job_id,
    }

    if enriched_data.get("_parse_failed"):
        product_record = {
            **base_record,
            "gs1_upper_material_type": None,
            "gs1_sporting_activity_type": None,
            "gs1_target_consumer_gender": None,
            "gs1_is_waterproof": None,
            "gs1_product_feature_benefit": None,
            "gs1_consumer_lifestage": None,
            "gs1_fastening_type": None,
            "gs1_footwear_upper_type": None,
            "gs1_is_patterned": None,
            "gs1_is_thermal": None,
            "gs1_style_description": None,
            "gs1_storage_instructions": None,
            "gs1_recycling_instructions": None,
            "differentiators": None,
            "completeness_score": 0.0,
            "needs_review": True,
            "status": "enrichment_failed",
            "missing_fields": ", ".join(ENRICHED_FIELDS),
            "gap_summary": "Enrichment failed, so no attributes could be extracted from this listing.",
            "embedding": None,
        }
        return repo.save(product_record)

    score = compute_completeness_score(enriched_data)
    needs_review = flag_needs_review(enriched_data, completeness_score=score)
    missing_fields, gap_summary = build_gap_summary(enriched_data)

    product_record = {
        **base_record,
        "gs1_upper_material_type": _to_string(enriched_data.get("gs1_upper_material_type")),
        "gs1_sporting_activity_type": _to_string(enriched_data.get("gs1_sporting_activity_type")),
        "gs1_target_consumer_gender": _to_string(enriched_data.get("gs1_target_consumer_gender")),
        "gs1_is_waterproof": enriched_data.get("gs1_is_waterproof"),
        "gs1_product_feature_benefit": _to_string(enriched_data.get("gs1_product_feature_benefit")),
        "gs1_consumer_lifestage": _to_string(enriched_data.get("gs1_consumer_lifestage")),
        "gs1_fastening_type": _to_string(enriched_data.get("gs1_fastening_type")),
        "gs1_footwear_upper_type": _to_string(enriched_data.get("gs1_footwear_upper_type")),
        "gs1_is_patterned": enriched_data.get("gs1_is_patterned"),
        "gs1_is_thermal": enriched_data.get("gs1_is_thermal"),
        "gs1_style_description": _to_string(enriched_data.get("gs1_style_description")),
        "gs1_storage_instructions": _to_string(enriched_data.get("gs1_storage_instructions")),
        "gs1_recycling_instructions": _to_string(enriched_data.get("gs1_recycling_instructions")),
        "differentiators": _to_string(enriched_data.get("differentiators")),
        "completeness_score": score,
        "needs_review": needs_review,
        "status": "completed",
        "missing_fields": missing_fields,
        "gap_summary": gap_summary,
    }

    embedding_text = f"{name}. {description}. {_to_string(enriched_data.get('gs1_product_feature_benefit')) or ''}"
    try:
        embedding_vector = llm.embed_text(embedding_text)
        product_record["embedding"] = json.dumps(embedding_vector)
    except Exception as e:
        print(f"EMBEDDING FAILED for {name}: {e}")
        product_record["embedding"] = None

    return repo.save(product_record)


async def process_batch(file_bytes: bytes, job_id: str, llm: LLMClient):
    db = SessionLocal()
    JobRepository(db).update_progress(job_id, status="processing")
    db.close()

    try:
        decoded = file_bytes.decode("utf-8")
    except UnicodeDecodeError:
        decoded = file_bytes.decode("latin-1")

    reader = csv.DictReader(io.StringIO(decoded))
    rows = list(reader)

    semaphore = asyncio.Semaphore(1)

    def process_row_sync(row):
        db = SessionLocal()
        try:
            repo = ProductRepository(db)
            job_repo = JobRepository(db)
            try:
                name = row.get("name", "").strip()
                description = row.get("description", "").strip()
                if not name or not description:
                    raise ValueError("Missing name or description")

                def safe_float(value):
                    try:
                        return float(value) if value not in (None, "", "null") else None
                    except (ValueError, TypeError):
                        return None

                price = safe_float(row.get("price"))
                currency = row.get("currency", "").strip() or None
                availability = row.get("availability", "").strip() or None
                rating = safe_float(row.get("avg_rating", row.get("rating")))
                gs1_colour_description = row.get("color", row.get("colour", "")).strip() or None
                gs1_size = row.get("available_sizes", row.get("size", "")).strip() or None
                gs1_referenced_file = row.get("url", "").strip() or None
                gs1_brand = row.get("brand", "").strip() or None
                gs1_country_of_origin = row.get("country_of_origin", "").strip() or None
                gs1_season_name = row.get("season", "").strip() or None
                gs1_net_weight = row.get("net_weight", "").strip() or None

                enrich_and_save(
                    name, description, llm, repo,
                    price=price, currency=currency, availability=availability, rating=rating,
                    gs1_colour_description=gs1_colour_description, gs1_size=gs1_size,
                    gs1_referenced_file=gs1_referenced_file, gs1_brand=gs1_brand,
                    gs1_country_of_origin=gs1_country_of_origin, gs1_season_name=gs1_season_name,
                    gs1_net_weight=gs1_net_weight, job_id=job_id,
                )
                job_repo.update_progress(job_id, completed=1)
            except Exception as e:
                print(f"ROW FAILED: {row.get('name', 'unknown')} — {type(e).__name__}: {e}")
                db.rollback()
                job_repo.update_progress(job_id, failed=1)
        finally:
            db.close()

    async def process_row(row):
        async with semaphore:
            await asyncio.to_thread(process_row_sync, row)

    await asyncio.gather(*(process_row(row) for row in rows))

    db = SessionLocal()
    JobRepository(db).update_progress(job_id, status="completed")
    db.close()


def compare_products(product_a, product_b, llm: LLMClient) -> dict:
    def to_dict(p):
        return {
            "name": p.name,
            "gs1_upper_material_type": p.gs1_upper_material_type,
            "gs1_sporting_activity_type": p.gs1_sporting_activity_type,
            "gs1_target_consumer_gender": p.gs1_target_consumer_gender,
            "gs1_is_waterproof": p.gs1_is_waterproof,
            "gs1_product_feature_benefit": p.gs1_product_feature_benefit,
            "gs1_consumer_lifestage": p.gs1_consumer_lifestage,
            "differentiators": p.differentiators,
        }

    a_dict = to_dict(product_a)
    b_dict = to_dict(product_b)

    result = llm.compare(a_dict, b_dict)

    if result.get("_parse_failed"):
        return {
            "product_a": product_a.name,
            "product_b": product_b.name,
            "likely_recommended": None,
            "reasoning": "Comparison could not be completed due to a parsing error.",
            "product_a_gaps": [],
            "product_b_gaps": [],
        }

    raw_recommendation = result.get("likely_recommended")
    if raw_recommendation == "product_a":
        recommended_name = product_a.name
    elif raw_recommendation == "product_b":
        recommended_name = product_b.name
    else:
        recommended_name = "tie"

    return {
        "product_a": product_a.name,
        "product_b": product_b.name,
        "likely_recommended": recommended_name,
        "reasoning": result.get("reasoning"),
        "product_a_gaps": result.get("product_a_gaps", []),
        "product_b_gaps": result.get("product_b_gaps", []),
    }


def match_and_compare(competitor_name: str, competitor_description: str, llm: LLMClient, repo: ProductRepository) -> dict:
    query_text = f"{competitor_name}. {competitor_description}"
    query_vector = llm.embed_text(query_text)

    all_products = repo.get_all(include_competitors=False)
    scored = []
    for p in all_products:
        if not p.embedding:
            continue
        try:
            p_vector = json.loads(p.embedding)
        except (json.JSONDecodeError, TypeError):
            continue
        scored.append((cosine_similarity(query_vector, p_vector), p))

    if not scored:
        return {
            "matched_product_id": None,
            "similarity": 0.0,
            "comparison": None,
            "message": "No embedded products in your catalog yet — enrich some products first.",
        }

    scored.sort(key=lambda x: x[0], reverse=True)
    best_score, best_product = scored[0]

    confidence = "strong" if best_score >= 0.75 else "weak" if best_score < 0.6 else "moderate"
    confidence_note = (
        "This is a strong match — the two products are genuinely comparable."
        if confidence == "strong" else
        "This is a weak match — no closely related product exists in your catalog yet, so treat this comparison with caution."
        if confidence == "weak" else
        "This is a moderate match — related, but not a close equivalent."
    )

    competitor_obj = enrich_and_save(competitor_name, competitor_description, llm, repo, is_competitor=True)
    comparison = compare_products(competitor_obj, best_product, llm)

    return {
        "competitor_name": competitor_name,
        "matched_product_id": best_product.id,
        "matched_product_name": best_product.name,
        "similarity": round(best_score, 3),
        "match_confidence": confidence,
        "match_confidence_note": confidence_note,
        "comparison": comparison,
    }


def check_product_visibility(query: str, watched_brands: list, llm: LLMClient, repo) -> dict:
    result = llm.check_visibility(query, watched_brands)

    if result.get("_parse_failed"):
        record = repo.save(
            query=query,
            watched_brands=", ".join(watched_brands),
            raw_response=result.get("_raw_response", ""),
            mentioned_brands="",
            reasoning="Could not parse LLM response.",
        )
        return {
            "id": record.id,
            "query": query,
            "mentioned_brands": [],
            "reasoning": "Could not parse LLM response.",
        }

    natural_answer = result.get("natural_answer", "")
    mentioned = result.get("mentioned_brands", [])
    reasoning = result.get("reasoning", "")

    record = repo.save(
        query=query,
        watched_brands=", ".join(watched_brands),
        raw_response=natural_answer,
        mentioned_brands=", ".join(mentioned) if mentioned else "",
        reasoning=reasoning,
    )

    return {
        "id": record.id,
        "query": query,
        "watched_brands": watched_brands,
        "mentioned_brands": mentioned,
        "natural_answer": natural_answer,
        "reasoning": reasoning,
        "created_at": record.created_at,
    }


def get_brand_visibility_history(brand: str, repo) -> dict:
    checks = repo.get_history_for_brand(brand)

    if not checks:
        return {"brand": brand, "total_checks": 0, "mentioned_count": 0, "share_of_voice": 0.0, "history": []}

    mentioned_count = 0
    history = []
    for check in checks:
        mentioned_brands = [b.strip().lower() for b in (check.mentioned_brands or "").split(",")]
        was_mentioned = brand.lower() in mentioned_brands
        if was_mentioned:
            mentioned_count += 1
        history.append({
            "query": check.query,
            "mentioned": was_mentioned,
            "created_at": check.created_at,
        })

    share_of_voice = round(mentioned_count / len(checks), 2)

    return {
        "brand": brand,
        "total_checks": len(checks),
        "mentioned_count": mentioned_count,
        "share_of_voice": share_of_voice,
        "history": history,
    }