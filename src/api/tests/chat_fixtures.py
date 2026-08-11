"""Seeded fixture catalog for chat tests (also a foundation for the broader
testing backlog item — keep it generic)."""
import hashlib

from rcars.db.database import Database

FIXTURE_ITEMS = [
    # (ci_name, display_name, category, summary, products)
    ("lb2144-ansible-eda", "LB2144 Event-Driven Ansible", "Labs",
     "Hands-on lab for Event-Driven Ansible automation.", ["Ansible Automation Platform"]),
    ("lb2145-ansible-basics", "LB2145 Ansible Automation Basics", "Labs",
     "Intro lab covering Ansible playbooks and roles.", ["Ansible Automation Platform"]),
    ("ocpvirt-migration", "OpenShift Virtualization Migration", "Labs",
     "Migrate VMs from VMware to OpenShift Virtualization.", ["OpenShift Virtualization"]),
    ("ocpvirt-roadshow", "OpenShift Virtualization Roadshow", "Demos",
     "Demo of OpenShift Virtualization features.", ["OpenShift Virtualization"]),
    ("rhel-security", "RHEL Security Hardening", "Labs",
     "RHEL system hardening and compliance lab.", ["Red Hat Enterprise Linux"]),
    ("sap-hana-demo", "SAP HANA on RHEL Demo", "Demos",
     "Demo of SAP HANA deployment on RHEL.", ["Red Hat Enterprise Linux", "SAP"]),
]


def fake_embedding(text: str, prefix: str = "") -> list[float]:
    """Deterministic 768-dim unit vector from the text hash. Signature is
    monkeypatch-compatible with analyzer.generate_embedding(text, prefix=...)."""
    h = hashlib.sha256(text.encode()).digest()
    vals = [((h[i % 32] + i * 7) % 97) / 97.0 for i in range(768)]
    norm = sum(v * v for v in vals) ** 0.5
    return [v / norm for v in vals]


def seed_chat_fixtures(db: Database) -> dict[str, str]:
    ids: dict[str, str] = {}
    for ci_name, display, category, summary, products in FIXTURE_ITEMS:
        cid = db.upsert_babylon_catalog_item({
            "ci_name": ci_name, "display_name": display, "category": category,
            "stage": "prod", "catalog_namespace": "babylon-catalog-prod",
            "showroom_url": f"https://github.com/example/{ci_name}",
            "is_prod": True, "is_published": False,
        })
        ids[ci_name] = cid
        db.upsert_showroom_analysis({
            "content_id": cid, "summary": summary,
            "products_json": products, "topics_json": [category.lower()],
            "content_hash": f"hash-{ci_name}",
        })
        db.store_embedding(cid, "lab", "babylon", "summary", summary, fake_embedding(summary))

    edges = [
        (ids["lb2144-ansible-eda"], ids["lb2145-ansible-basics"], 2, 3),
        (ids["ocpvirt-migration"], ids["ocpvirt-roadshow"], 2, 2),
        (ids["rhel-security"], ids["sap-hana-demo"], 1, 2),
    ]
    with db.pool.connection() as conn:
        for a, b, sp, st in edges:
            conn.execute(
                """INSERT INTO overlap_candidates (content_id_a, content_id_b, shared_products, shared_topics, computed_at)
                   VALUES (%s, %s, %s, %s, NOW()) ON CONFLICT (content_id_a, content_id_b) DO NOTHING""",
                (a, b, sp, st))
        conn.execute(
            """INSERT INTO babylon_item_workloads (content_id, workload_fqcn, workload_role, workload_collection)
               VALUES (%s, %s, %s, %s) ON CONFLICT (content_id, workload_fqcn) DO NOTHING""",
            (ids["ocpvirt-migration"], "rhpds.ocpvirt.setup", "setup_virt", "rhpds.ocpvirt"))
        for ci, provisions, cost in [("lb2144-ansible-eda", 40, 12.5), ("lb2145-ansible-basics", 8, 30.0),
                                     ("ocpvirt-migration", 120, 9.0)]:
            conn.execute(
                """INSERT INTO performance_channels
                   (content_id, channel, provisions, avg_cost_per_provision, closed_amount, windowed_metrics)
                   VALUES (%s, 'rhdp', %s, %s, 50000, %s::jsonb)
                   ON CONFLICT (content_id, channel) DO NOTHING""",
                (ids[ci], provisions, cost,
                 f'{{"3m": {{"provisions": {provisions}}}, "12m": {{"provisions": {provisions * 3}}}}}'))
        conn.commit()
    return ids
