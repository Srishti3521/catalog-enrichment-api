from app.services.enrichment import ENRICHED_FIELDS, FIELD_LABELS, _is_filled
from app.services.analytics import get_visibility_summary

MIN_SAMPLES_PER_GROUP = 2  # minimum products needed in each group before trusting a learned weight


def _brand_share_map(visibility_repo) -> dict:
    summary = get_visibility_summary(visibility_repo)
    return {b["brand"].lower(): b["share_of_voice"] for b in summary.get("brands", [])}


def compute_field_weights(product_repo, visibility_repo) -> dict:
    """
    Learns, per GS1 field, how much filling it in is associated with higher
    AI visibility (share of voice) for the brand that product belongs to.

    This is a correlational proxy, not a causal model — visibility checks are
    recorded per brand/query, not per individual product, so outcomes are
    linked to products via their gs1_brand field. Falls back to an equal
    default weight (1.0) for any field without enough linked data to trust
    a learned signal yet, and the model improves as more visibility checks
    and enriched products accumulate.
    """
    products = product_repo.get_all(include_competitors=False)
    brand_shares = _brand_share_map(visibility_repo)

    weights = {}
    diagnostics = {}

    for field in ENRICHED_FIELDS:
        filled_scores = []
        missing_scores = []

        for p in products:
            if not p.gs1_brand:
                continue
            share = brand_shares.get(p.gs1_brand.strip().lower())
            if share is None:
                continue
            if _is_filled(getattr(p, field, None)):
                filled_scores.append(share)
            else:
                missing_scores.append(share)

        if len(filled_scores) >= MIN_SAMPLES_PER_GROUP and len(missing_scores) >= MIN_SAMPLES_PER_GROUP:
            avg_filled = sum(filled_scores) / len(filled_scores)
            avg_missing = sum(missing_scores) / len(missing_scores)
            diff = max(avg_filled - avg_missing, 0.05)  # floor so no field is learned as "harmful" to fill
            weights[field] = round(diff, 3)
            diagnostics[field] = {
                "source": "learned",
                "n_filled": len(filled_scores),
                "n_missing": len(missing_scores),
                "avg_share_filled": round(avg_filled, 3),
                "avg_share_missing": round(avg_missing, 3),
            }
        else:
            weights[field] = 1.0
            diagnostics[field] = {
                "source": "default",
                "n_filled": len(filled_scores),
                "n_missing": len(missing_scores),
                "reason": "insufficient linked visibility data for this field yet",
            }

    return {"weights": weights, "diagnostics": diagnostics}


def compute_weighted_completeness_score(product, weights: dict) -> float:
    total_weight = sum(weights.values())
    if total_weight == 0:
        return 0.0
    earned = sum(
        weights[field] for field in ENRICHED_FIELDS
        if _is_filled(getattr(product, field, None))
    )
    return round(earned / total_weight, 3)


def get_remediation_priorities(product_repo, visibility_repo, limit: int = 10) -> list:
    """
    Ranks products by expected AI-visibility gain per unit of fixing effort —
    a greedy knapsack-style heuristic answering "which products are worth
    fixing first, given limited time?"
    """
    weight_data = compute_field_weights(product_repo, visibility_repo)
    weights = weight_data["weights"]

    products = product_repo.get_all(include_competitors=False)
    ranked = []

    for p in products:
        missing = [f for f in ENRICHED_FIELDS if not _is_filled(getattr(p, f, None))]
        if not missing:
            continue

        expected_impact = sum(weights.get(f, 1.0) for f in missing)
        effort = len(missing)
        priority_score = round(expected_impact / effort, 3) if effort else 0.0

        ranked.append({
            "product_id": p.id,
            "name": p.name,
            "current_completeness_score": p.completeness_score,
            "missing_fields": [FIELD_LABELS.get(f, f) for f in missing],
            "expected_impact": round(expected_impact, 3),
            "effort": effort,
            "priority_score": priority_score,
        })

    ranked.sort(key=lambda r: r["priority_score"], reverse=True)
    return ranked[:limit]