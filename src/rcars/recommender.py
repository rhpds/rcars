"""RCARS recommendation engine.

Combines pgvector semantic search with Sonnet ranking.
"""

import logging
from pathlib import Path
from typing import Any

from rcars.analyzer import generate_embedding, parse_analysis_response
from rcars.db import Database

log = logging.getLogger(__name__)

RECOMMEND_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "recommend.txt"


def format_candidate(item: dict[str, Any], analysis: dict[str, Any] | None) -> str:
    """Format a candidate item for the ranking prompt."""
    parts = [
        f"CI Name: {item['ci_name']}",
        f"Display Name: {item.get('display_name', '')}",
        f"Category: {item.get('category', '')}",
        f"Product: {item.get('product', '')}",
        f"Stage: {item.get('stage', '')}",
    ]

    if item.get("is_published") and item.get("base_ci_name"):
        parts.append("Type: Virtual CI (orders via this name)")
    elif item.get("published_ci_name"):
        parts.append(f"Type: Base CI (order via {item['published_ci_name']})")

    if analysis:
        parts.append(f"Content Type: {analysis.get('content_type', '')}")
        parts.append(f"Summary: {analysis.get('summary', '')}")
        parts.append(f"Difficulty: {analysis.get('difficulty', '')}")
        parts.append(f"Duration: {analysis.get('estimated_duration_min', '?')} min")
        parts.append(f"Topics: {', '.join(analysis.get('topics_json', []) or [])}")
        parts.append(f"Products: {', '.join(analysis.get('products_json', []) or [])}")
        parts.append(f"Audience: {', '.join(analysis.get('audience_json', []) or [])}")

        objectives = analysis.get("learning_objectives_json", {})
        if isinstance(objectives, dict):
            stated = objectives.get("stated", [])
            inferred = objectives.get("inferred", [])
            if stated:
                parts.append(f"Stated Objectives: {'; '.join(stated)}")
            if inferred:
                parts.append(f"Inferred Objectives: {'; '.join(inferred)}")

    return "\n".join(parts)


def recommend(
    query: str,
    db: Database,
    anthropic_client,
    model: str = "claude-sonnet-4-6",
    limit: int = 15,
    prod_only: bool = True,
) -> dict[str, Any] | None:
    """Run a recommendation query.

    1. Generate embedding for query
    2. Search pgvector for top candidates
    3. Enrich with analysis data
    4. Send to Sonnet for ranking
    5. Return ranked results
    """
    # Generate query embedding
    query_embedding = generate_embedding(query)

    # Search for candidates
    candidates = db.search_embeddings(
        query_embedding=query_embedding,
        limit=limit,
        prod_only=prod_only,
    )

    if not candidates:
        log.warning("No candidates found for query: %s", query[:100])
        return None

    # Enrich with analysis data
    formatted_candidates = []
    for i, candidate in enumerate(candidates, 1):
        ci_name = candidate["ci_name"]
        analysis = db.get_showroom_analysis(ci_name)
        formatted = format_candidate(candidate, analysis)
        formatted_candidates.append(f"--- Candidate {i} ---\n{formatted}")

    candidates_text = "\n\n".join(formatted_candidates)

    # Build ranking prompt — use str.replace() to avoid brace conflicts
    template = RECOMMEND_PROMPT_PATH.read_text()
    prompt = (
        template
        .replace("{request_description}", query)
        .replace("{candidates}", candidates_text)
    )

    # Call Sonnet for ranking
    response = anthropic_client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    result = parse_analysis_response(response.content[0].text)
    if not result:
        log.error("Failed to parse recommendation response")
        return None

    return result
