"""Event URL parser.

Fetches event web pages, extracts structured profiles via Sonnet.
"""

import logging
import re
from pathlib import Path
from typing import Any

import httpx

from rcars.analyzer import parse_analysis_response

log = logging.getLogger(__name__)

EVENT_PROMPT_PATH = Path(__file__).parent.parent.parent / "prompts" / "match_event.txt"


def fetch_and_strip_html(url: str, max_chars: int = 50000) -> str | None:
    """Fetch a URL and strip HTML to plain text."""
    try:
        response = httpx.get(url, follow_redirects=True, timeout=30)
        response.raise_for_status()
    except httpx.HTTPError as e:
        log.error("Failed to fetch %s: %s", url, e)
        return None

    html = response.text

    # Strip HTML tags
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()

    return text[:max_chars]


def parse_event_url(
    url: str,
    anthropic_client,
    model: str = "claude-sonnet-4-6",
) -> dict[str, Any] | None:
    """Parse an event URL into a structured profile."""
    page_text = fetch_and_strip_html(url)
    if not page_text:
        return None

    # Use str.replace() to avoid brace conflicts with JSON examples in template
    template = EVENT_PROMPT_PATH.read_text()
    prompt = template.replace("{page_content}", page_text)

    response = anthropic_client.messages.create(
        model=model,
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )

    return parse_analysis_response(response.content[0].text)
