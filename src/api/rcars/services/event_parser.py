"""Event URL parser.

Fetches event web pages, follows links to schedule/program/tracks pages,
and extracts structured profiles via Sonnet.
"""

import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

import httpx

from rcars.services.analyzer import parse_analysis_response

log = logging.getLogger(__name__)

EVENT_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "match_event.txt"

# URL path patterns that indicate schedule/program/content pages
_CONTENT_PATH_PATTERNS = re.compile(
    r'/(schedule|program|agenda|tracks?|sessions?|talks?|speakers?|themes?|topics?'
    r'|co-located|featured|keynotes?|workshops?|about)(/|$)',
    re.IGNORECASE,
)


_HTTP_HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible)",
}


def _fetch_html(url: str, timeout: int = 30) -> str | None:
    """Fetch a URL and return raw HTML, or None on failure."""
    try:
        response = httpx.get(url, follow_redirects=True, timeout=timeout,
                             headers=_HTTP_HEADERS)
        response.raise_for_status()
        return response.text
    except httpx.HTTPError as e:
        log.warning("event_parser: failed to fetch %s: %s", url, e)
        return None


def _strip_html(html: str) -> str:
    """Strip HTML tags, scripts, and styles to plain text."""
    text = re.sub(r"<script[^>]*>.*?</script>", "", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _extract_links(html: str, base_url: str) -> list[str]:
    """Extract absolute URLs from HTML anchor tags."""
    base_domain = urlparse(base_url).netloc
    links = []
    seen = set()
    for match in re.finditer(r'<a\s[^>]*href=["\']([^"\']+)["\']', html, re.IGNORECASE):
        href = match.group(1)
        # Skip anchors, javascript, mailto
        if href.startswith(("#", "javascript:", "mailto:")):
            continue
        absolute = urljoin(base_url, href)
        # Stay on same domain
        if urlparse(absolute).netloc != base_domain:
            continue
        # Normalize — strip fragment and trailing slash for dedup
        normalized = absolute.split("#")[0].rstrip("/")
        if normalized not in seen:
            seen.add(normalized)
            links.append(normalized)
    return links


def _find_content_pages(links: list[str], base_url: str, max_pages: int = 3) -> list[str]:
    """Filter links to those that look like schedule/program/content pages."""
    base_normalized = base_url.rstrip("/")
    content_links = []
    for link in links:
        if link == base_normalized:
            continue
        parsed = urlparse(link)
        if _CONTENT_PATH_PATTERNS.search(parsed.path):
            content_links.append(link)
    return content_links[:max_pages]


def fetch_event_content(url: str, max_chars: int = 80000) -> str | None:
    """Fetch an event landing page and key subpages, return combined plain text.

    Follows links to schedule, program, tracks, talks, and similar pages
    on the same domain to gather richer event context.
    """
    log.info("event_parser: fetching landing page %s", url)
    landing_html = _fetch_html(url)
    if not landing_html:
        return None

    landing_text = _strip_html(landing_html)
    sections = [f"=== Landing Page: {url} ===\n{landing_text}"]
    total_chars = len(landing_text)

    # Find and fetch content subpages
    links = _extract_links(landing_html, url)
    content_pages = _find_content_pages(links, url)

    if content_pages:
        log.info("event_parser: found %d content pages: %s",
                 len(content_pages), [urlparse(u).path for u in content_pages])
    else:
        log.info("event_parser: no content subpages found, using landing page only")

    for page_url in content_pages:
        if total_chars >= max_chars:
            log.info("event_parser: reached %d char limit, skipping remaining pages", max_chars)
            break
        page_html = _fetch_html(page_url)
        if not page_html:
            continue
        page_text = _strip_html(page_html)
        path = urlparse(page_url).path
        section = f"\n\n=== Subpage: {path} ===\n{page_text}"
        sections.append(section)
        total_chars += len(section)
        log.info("event_parser: fetched %s (%d chars)", path, len(page_text))

    combined = "\n".join(sections)
    return combined[:max_chars]


def parse_event_url(
    url: str,
    settings,
    model: str = "claude-sonnet-4-6",
) -> dict[str, Any] | None:
    """Parse an event URL into a structured profile.

    Fetches the landing page and key subpages (schedule, tracks, etc.)
    to build a comprehensive understanding of the event.
    """
    page_text = fetch_event_content(url)
    if not page_text:
        return None

    log.info("event_parser: sending %d chars to %s for analysis", len(page_text), model)

    template = EVENT_PROMPT_PATH.read_text()
    prompt = template.replace("{page_content}", page_text)

    from rcars.config import call_llm
    llm_result = call_llm(settings, model=model, messages=[{"role": "user", "content": prompt}], max_tokens=4096)

    input_tokens = llm_result.input_tokens
    output_tokens = llm_result.output_tokens
    log.info("event_parser: response received (in=%d out=%d tokens, provider=%s)",
             input_tokens, output_tokens, llm_result.provider)

    result = parse_analysis_response(llm_result.text)
    if result:
        log.info("event_parser: parsed event=%s themes=%s",
                 result.get("event_name"), result.get("themes"))
    return result
