"""Sandbox summary generation from infrastructure metadata and workload classifications."""


def build_sandbox_summary(
    display_name: str,
    description: str | None,
    cloud_provider: str | None,
    ocp_version: str | None,
    agd_config: str | None,
    workload_products: list[dict],
) -> dict:
    """Assemble a sandbox summary from infrastructure metadata.

    workload_products: [{product_name, description, category}, ...] from workload_mapping
    Returns dict with: summary, products_json, topics_json
    """
    products = sorted(set(wp["product_name"] for wp in workload_products if wp.get("product_name")))

    topics = set()
    for wp in workload_products:
        if wp.get("category"):
            topics.add(wp["category"])
    if cloud_provider:
        topics.add(f"{cloud_provider} infrastructure")
    if ocp_version:
        topics.add("OpenShift")
    topics = sorted(topics)

    parts = []
    if description:
        parts.append(description.strip().rstrip(".") + ".")

    if cloud_provider and ocp_version:
        parts.append(f"Runs on {cloud_provider} with OpenShift {ocp_version}.")
    elif cloud_provider:
        parts.append(f"Runs on {cloud_provider}.")
    elif ocp_version:
        parts.append(f"Runs on OpenShift {ocp_version}.")

    if agd_config:
        parts.append(f"Infrastructure config: {agd_config}.")

    if products:
        if len(products) <= 3:
            parts.append(f"Includes: {', '.join(products)}.")
        else:
            parts.append(f"Includes {len(products)} products: {', '.join(products[:3])}, and {len(products) - 3} more.")

    summary = " ".join(parts) if parts else f"Sandbox environment: {display_name}."

    return {
        "summary": summary,
        "products_json": products,
        "topics_json": topics,
    }
