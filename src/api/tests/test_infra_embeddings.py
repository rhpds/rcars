from rcars.services.analyzer import build_infrastructure_embedding_text


def test_build_infrastructure_embedding_text():
    row = {
        "role_name": "ocp4_workload_rhods",
        "description": "Installs OpenShift AI with KServe support.",
        "products": ["OpenShift AI", "KServe"],
        "capabilities": ["model-serving", "notebook-hosting"],
        "category": "ai_ml",
    }
    text = build_infrastructure_embedding_text(row)
    assert "OpenShift AI" in text
    assert "KServe" in text
    assert "model-serving" in text
    assert "ai_ml" in text
    assert "ocp4_workload_rhods" in text


def test_build_infrastructure_embedding_text_minimal():
    row = {
        "role_name": "namespace",
        "description": None,
        "products": [],
        "capabilities": [],
        "category": None,
    }
    text = build_infrastructure_embedding_text(row)
    assert "namespace" in text
