"""The only place that decides when two Showroom analyses are "the same".

Two owner functions, everything else calls them:

* ``compute_content_hash`` -- same Showroom content. Equal hash of the selected,
  filtered files the LLM reads. Ref names, tags and CI names never count.
* ``compute_analysis_config`` -- same analysis setup for Showroom content. Prompt
  template, vocabulary block, model, policy version and entity content type.
* ``compute_description_analysis_config`` -- the same for a catalog description,
  whose prompt still carries the item fields.

An analysis may be reused when ``content_hash`` and ``analysis_config`` (and the
entity content type) are equal. ``repo + resolved commit + content_path`` is only
a pre-clone shortcut to find a known hash without cloning; it is never identity.

Pull, never push: a scan looks for a donor for itself. Reuse never sets card
identity (that comes from the catalog families, not from scan reuse).
"""
import hashlib
import json
import re

from rcars.services.showroom_source import SHOWROOM_ANALYSIS_POLICY_VERSION


def fingerprint(*values) -> str:
    return hashlib.sha256(json.dumps(values, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()


def canonical_content(content: str) -> str:
    """The exact text hashed is also the text sent to the analysis model."""
    text = "\n".join(line.rstrip() for line in content.splitlines())
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def compute_content_hash(files: dict[str, str]) -> str:
    """Deterministic SHA-256 of Showroom content files.

    Whitespace is normalized so trailing spaces, blank-line differences and line
    endings do not change the hash. Files are sorted by name.
    """
    h = hashlib.sha256()
    for filename in sorted(files.keys()):
        h.update(filename.encode())
        h.update(b"\x00")
        h.update(canonical_content(files[filename]).encode())
        h.update(b"\x00")
    return h.hexdigest()


# Boilerplate-only content is rejected before the LLM and never gets a hash. This
# is the hash of "no files"; it must never become a shared key.
EMPTY_CONTENT_HASH = compute_content_hash({})


def compute_analysis_config(entity_content_type: str, model: str) -> str:
    """Digest of everything except the content that shapes the LLM result.

    The content prompt carries only content plus the entity content type (through
    the vocabulary block), so item identity -- CI name, display name, category,
    product, scope key -- is deliberately absent. Two items with the same content
    and content type therefore share one analysis_config and may reuse one
    analysis across CIs and stages.
    """
    from rcars.services import analyzer
    system, _ = analyzer.build_analysis_prompt({}, entity_content_type=entity_content_type)
    return fingerprint(system, model, SHOWROOM_ANALYSIS_POLICY_VERSION)


def compute_description_analysis_config(ci_name: str, display_name: str, category: str,
                                        product: str, entity_content_type: str, model: str) -> str:
    """Analysis setup for description-based analyses.

    The description prompt still names the item and sends its fields to the LLM,
    so those fields remain part of its identity. This is separate from the
    content-only Showroom ``compute_analysis_config``. Description analyses are
    per item and are never Showroom donors.
    """
    from rcars.services import analyzer
    system, _ = analyzer.build_analysis_prompt({}, entity_content_type=entity_content_type)
    item_context = [ci_name, display_name, category, product]
    return fingerprint(system, item_context, model, SHOWROOM_ANALYSIS_POLICY_VERSION)


def pre_clone_key(repo: str, commit: str, content_path: str | None, analysis_config: str,
                  entity_content_type: str) -> str:
    """Queue and lock key known before cloning: same files, same analysis setup."""
    return fingerprint("showroom-pre-clone", repo, commit, content_path or None, analysis_config,
                       entity_content_type)


def _signature(row: dict) -> dict:
    return (row.get("analysis_provenance_json") or {}).get("signature") or {}


def _donor_signature(row: dict, analysis_config: str, entity_content_type: str) -> dict | None:
    """The donor's signature when its hash, config, policy and type are usable."""
    signature, stored_hash = _signature(row), row.get("content_hash")
    if not signature or not stored_hash or stored_hash == EMPTY_CONTENT_HASH:
        return None
    if signature.get("content_hash") != stored_hash:
        return None
    if signature.get("context_hash") != analysis_config:
        return None
    if signature.get("policy_version") != SHOWROOM_ANALYSIS_POLICY_VERSION:
        return None
    if row.get("entity_content_type") != entity_content_type:
        return None
    if str(signature.get("repo") or "").startswith("description:"):
        return None  # description analyses are per item, never Showroom donors
    return signature


def donor_matches_content(row: dict, *, content_hash: str, analysis_config: str,
                          entity_content_type: str) -> bool:
    """Post-clone rule: same content_hash + analysis_config, from any CI and stage."""
    if not content_hash or content_hash == EMPTY_CONTENT_HASH:
        return False
    return (_donor_signature(row, analysis_config, entity_content_type) is not None
            and row.get("content_hash") == content_hash)


def donor_matches_commit(row: dict, *, repo: str, commit: str, content_path: str | None,
                         analysis_config: str, entity_content_type: str) -> bool:
    """Pre-clone shortcut: same repo + commit + content_path + analysis_config.

    The same commit and path always select the same files, so the donor's stored
    content_hash is the hash this item would compute after cloning.
    """
    signature = _donor_signature(row, analysis_config, entity_content_type)
    return (signature is not None and bool(commit)
            and signature.get("repo") == repo and signature.get("commit") == commit
            and (signature.get("content_path") or None) == (content_path or None))
