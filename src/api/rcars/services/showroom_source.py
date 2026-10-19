"""Explicit, stage-specific content ownership, independent of infrastructure."""
from dataclasses import asdict, dataclass, field, replace
from copy import deepcopy

KNOWN_STAGES = frozenset({"dev", "event", "prod", "test"})
SHOWROOM_ANALYSIS_POLICY_VERSION = 1


def analysis_generation(row: dict | None):
    """Observed artifact generation for compare-and-swap, not a new epoch store."""
    if row is None:
        return None
    return deepcopy(tuple(row.get(key) for key in ("analysis_provenance_json", "last_analyzed", "content_hash")))


@dataclass(frozen=True)
class AnalysisSignature:
    scope_key: str
    repo: str
    ref: str | None
    content_path: str | None
    commit: str
    content_hash: str
    context_hash: str
    input_hash: str
    policy_version: int

    def to_dict(self) -> dict:
        return asdict(self)


def signatures_match(left: AnalysisSignature, right: AnalysisSignature) -> bool:
    return left == right and left.policy_version == SHOWROOM_ANALYSIS_POLICY_VERSION


def item_family_key(ci_name: str, stage: str) -> str:
    suffix = f".{stage}"
    return ci_name[:-len(suffix)] if stage in KNOWN_STAGES and ci_name.endswith(suffix) else ci_name


@dataclass(frozen=True)
class ComponentLink:
    target_ci_name: str
    overrides: dict[str, str | None]


@dataclass(frozen=True)
class ContentDeclaration:
    repo: str | None
    ref: str | None
    content_path: str | None
    provided_fields: frozenset[str]


@dataclass(frozen=True)
class SourceNode:
    ci_name: str
    stage: str
    declaration: ContentDeclaration
    links: tuple[ComponentLink, ...]


@dataclass(frozen=True)
class ResolvedShowroom:
    status: str
    owner_ci_name: str | None = None
    scope_key: str | None = None
    repo: str | None = None
    ref: str | None = None
    content_path: str | None = None
    paths: tuple[tuple[str, ...], ...] = ()
    override_origins: dict[str, str] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict:
        data = asdict(self)
        data["paths"] = [list(path) for path in self.paths]
        return data

    @classmethod
    def from_dict(cls, data: dict) -> "ResolvedShowroom":
        return cls(**{**data, "paths": tuple(tuple(path) for path in data.get("paths", ())),
                      "override_origins": dict(data.get("override_origins") or {})})


def effective_showroom_source(item: dict) -> ResolvedShowroom:
    """Curator overrides belong to this target, never to its generic base."""
    raw = item.get("showroom_source_json") or item.get("showroom_source")
    source = ResolvedShowroom.from_dict(raw) if raw else ResolvedShowroom(
        "invalid", error="source_metadata_missing")
    overrides = {}
    if item.get("showroom_url_override"):
        overrides["repo"] = item["showroom_url_override"]
    if item.get("content_path") is not None:
        overrides["content_path"] = item["content_path"]
    if overrides:
        name = item["ci_name"]
        source = replace(source, **overrides,
                         scope_key=item_family_key(name, item.get("stage", "")),
                         override_origins={**source.override_origins, **{key: name for key in overrides}})
        if "repo" in overrides:
            # A curator's explicit source stops traversal just like a local CRD
            # declaration; failed/absent dependency discovery cannot veto it.
            source = replace(source, status="resolved", owner_ci_name=name,
                             paths=((name,),), error=None)
        if any(value is not None and (not isinstance(value, str) or "{{" in value or "{%" in value)
               for value in (source.repo, source.ref, source.content_path)):
            source = replace(source, status="invalid", error="unresolved_curator_override")
    return source


def signature_matches_source(signature: dict, source: ResolvedShowroom) -> bool:
    return (source.status == "resolved"
            and signature.get("policy_version") == SHOWROOM_ANALYSIS_POLICY_VERSION
            and all(signature.get(key) == getattr(source, key)
                    for key in ("scope_key", "repo", "ref", "content_path"))
            and all(signature.get(key) for key in ("commit", "content_hash", "context_hash", "input_hash")))


def analysis_artifacts_complete(analysis: dict, embeddings: list[dict]) -> bool:
    from rcars.services.analyzer import build_module_embedding_text
    if not analysis.get("summary") or analysis.get("modules_json") is None:
        return False
    valid = [row for row in embeddings if row.get("embedding_text")]
    if sum(row["embed_type"] == "summary" for row in valid) != 1:
        return False
    required = [module.get("title", "") for module in analysis["modules_json"]
                if build_module_embedding_text(module).strip()]
    actual = [row.get("module_title", "") for row in valid if row["embed_type"] == "module"]
    return sorted(required) == sorted(actual)


def resolve_showroom_source(root_ci_name: str, nodes: dict[str, SourceNode], *, max_depth: int = 32) -> ResolvedShowroom:
    """Walk to each nearest explicit repo; overrides belong to the nearer node."""
    candidates, paths, errors = [], [], []

    def unresolved(values):
        return any(value is not None and (not isinstance(value, str) or "{{" in value or "{%" in value)
                   for value in values.values())

    def walk(name, path, inherited, origins, scope):
        current_path = (*path, name)
        if name in path or len(current_path) > max_depth or name not in nodes:
            reason = "cycle" if name in path else "depth_exceeded" if len(current_path) > max_depth else "missing_dependency"
            errors.append(f"{reason}: {' -> '.join(current_path)}")
            paths.append(current_path)
            return
        node = nodes[name]
        declaration = node.declaration
        values = {key: getattr(declaration, key) for key in declaration.provided_fields}
        effective = {**values, **inherited}
        if unresolved(effective):
            errors.append(f"unresolved_declaration: {name}")
            paths.append(current_path)
            return
        own_origins = {**{key: name for key in values}, **origins}
        if declaration.repo or inherited.get("repo"):
            if not effective.get("repo"):
                errors.append(f"invalid_repo: {name}")
            else:
                candidates.append((name, scope or item_family_key(name, node.stage), effective, own_origins))
            paths.append(current_path)
            return
        if "repo" in effective:
            errors.append(f"invalid_repo: {name}")
            paths.append(current_path)
            return
        next_scope = scope or (item_family_key(name, node.stage) if values else None)
        if not node.links:
            paths.append(current_path)
        for link in sorted(node.links, key=lambda link: link.target_ci_name):
            overrides = link.overrides
            next_values = {**overrides, **effective}
            if unresolved(next_values):
                errors.append(f"unresolved_override: {name}")
                paths.append((*current_path, link.target_ci_name))
                continue
            walk(link.target_ci_name, current_path, next_values,
                 {**{key: name for key in overrides}, **own_origins},
                 next_scope or (item_family_key(name, node.stage) if overrides else None))

    walk(root_ci_name, (), {}, {}, None)
    provenance_paths = tuple(sorted(set(paths)))
    if errors:
        return ResolvedShowroom("invalid", paths=provenance_paths, error="; ".join(sorted(set(errors))))
    unique = {(owner, scope, values.get("repo"), values.get("ref"), values.get("content_path"))
              for owner, scope, values, _ in candidates}
    if len(unique) > 1:
        return ResolvedShowroom("ambiguous", paths=provenance_paths, error="multiple_content_sources")
    if not candidates:
        return ResolvedShowroom("none", paths=provenance_paths)
    owner, scope, values, origins = candidates[0]
    return ResolvedShowroom("resolved", owner, scope, values.get("repo"), values.get("ref"),
                            values.get("content_path"), provenance_paths, origins)
