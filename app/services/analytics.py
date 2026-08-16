def get_catalog_summary(repo) -> dict:
    products = repo.get_all(include_competitors=False)
    total = len(products)

    if total == 0:
        return {
            "total_products": 0,
            "avg_completeness_score": 0.0,
            "needs_review_count": 0,
            "score_distribution": {"low": 0, "moderate": 0, "high": 0},
        }

    avg_score = round(sum(p.completeness_score or 0 for p in products) / total, 2)
    needs_review_count = sum(1 for p in products if p.needs_review)

    low = sum(1 for p in products if (p.completeness_score or 0) < 0.4)
    moderate = sum(1 for p in products if 0.4 <= (p.completeness_score or 0) < 0.7)
    high = sum(1 for p in products if (p.completeness_score or 0) >= 0.7)

    return {
        "total_products": total,
        "avg_completeness_score": avg_score,
        "needs_review_count": needs_review_count,
        "score_distribution": {"low": low, "moderate": moderate, "high": high},
    }


def get_visibility_summary(visibility_repo) -> dict:
    checks = visibility_repo.get_all()

    if not checks:
        return {"total_checks": 0, "brands": []}

    brand_stats = {}
    for check in checks:
        watched = [b.strip() for b in (check.watched_brands or "").split(",") if b.strip()]
        mentioned = [b.strip().lower() for b in (check.mentioned_brands or "").split(",") if b.strip()]
        for brand in watched:
            key = brand.lower()
            if key not in brand_stats:
                brand_stats[key] = {"brand": brand, "checks": 0, "mentions": 0}
            brand_stats[key]["checks"] += 1
            if key in mentioned:
                brand_stats[key]["mentions"] += 1

    brands = []
    for stat in brand_stats.values():
        share = round(stat["mentions"] / stat["checks"], 2) if stat["checks"] else 0.0
        brands.append({
            "brand": stat["brand"],
            "checks": stat["checks"],
            "mentions": stat["mentions"],
            "share_of_voice": share,
        })
    brands.sort(key=lambda b: b["share_of_voice"], reverse=True)

    return {"total_checks": len(checks), "brands": brands}