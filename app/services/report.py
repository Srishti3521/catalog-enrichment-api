from datetime import datetime, timezone
from app.llm.client import LLMClient
from app.services.enrichment import check_product_visibility


def generate_benchmark_data(brands: list, queries: list, llm: LLMClient, visibility_repo) -> dict:
    results = []
    for query in queries:
        check_result = check_product_visibility(query, brands, llm, visibility_repo)
        results.append(check_result)

    brand_totals = {b: {"mentions": 0, "checks": 0} for b in brands}
    for r in results:
        mentioned = r.get("mentioned_brands", []) or []
        mentioned_lower = [m.lower() for m in mentioned]
        for b in brands:
            brand_totals[b]["checks"] += 1
            if b.lower() in mentioned_lower:
                brand_totals[b]["mentions"] += 1

    ranking = []
    for b, stats in brand_totals.items():
        share = round(stats["mentions"] / stats["checks"], 2) if stats["checks"] else 0.0
        ranking.append({"brand": b, "mentions": stats["mentions"], "checks": stats["checks"], "share_of_voice": share})
    ranking.sort(key=lambda r: r["share_of_voice"], reverse=True)

    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "brands": brands,
        "queries": queries,
        "ranking": ranking,
        "raw_results": results,
    }


def render_report_html(data: dict) -> str:
    ranking_rows = ""
    for i, r in enumerate(data["ranking"], start=1):
        pct = round(r["share_of_voice"] * 100)
        ranking_rows += f"""
        <tr>
            <td>{i}</td>
            <td><b>{r['brand']}</b></td>
            <td>{r['mentions']} / {r['checks']}</td>
            <td>{pct}%</td>
        </tr>"""

    query_rows = ""
    for r in data["raw_results"]:
        mentioned = ", ".join(r.get("mentioned_brands", []) or []) or "none"
        query_rows += f"""
        <div class="q-block">
            <div class="q-text">"{r.get('query', '')}"</div>
            <div class="q-mentioned">Mentioned: {mentioned}</div>
            <div class="q-answer">{r.get('natural_answer', '')}</div>
        </div>"""

    html = f"""<!DOCTYPE html>
<html><head><meta charset="UTF-8">
<title>AI Visibility Benchmark Report</title>
<style>
  body {{ font-family: -apple-system, sans-serif; background: #1B1F27; color: #EDE8DE; margin: 0; padding: 40px; }}
  h1 {{ color: #E3A857; font-size: 22px; }}
  .meta {{ color: #8B92A0; font-size: 12px; margin-bottom: 30px; }}
  table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; }}
  th, td {{ text-align: left; padding: 10px; border-bottom: 1px solid #3A4150; font-size: 14px; }}
  th {{ color: #8B92A0; font-size: 11px; text-transform: uppercase; }}
  .q-block {{ background: #242933; border: 1px solid #3A4150; border-radius: 6px; padding: 16px; margin-bottom: 12px; }}
  .q-text {{ color: #E3A857; font-weight: 600; margin-bottom: 8px; }}
  .q-mentioned {{ font-size: 12px; color: #7FB69E; margin-bottom: 8px; }}
  .q-answer {{ font-size: 13px; color: #EDE8DE; line-height: 1.5; }}
</style>
</head><body>
  <h1>AI Visibility Benchmark Report</h1>
  <div class="meta">Generated {data['generated_at']} · {len(data['queries'])} queries · {len(data['brands'])} brands watched</div>

  <table>
    <tr><th>Rank</th><th>Brand</th><th>Mentions</th><th>Share of Voice</th></tr>
    {ranking_rows}
  </table>

  <h2 style="color:#E3A857; font-size:16px;">Query-by-query detail</h2>
  {query_rows}
</body></html>"""
    return html