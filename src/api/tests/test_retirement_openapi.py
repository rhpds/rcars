from rcars.api.app import create_app
from rcars.config import Settings


def test_retirement_contract_is_discoverable_in_swagger():
    schema = create_app(Settings(database_url="postgresql://unused/unused")).openapi()
    retirement = {path: operations for path, operations in schema["paths"].items() if path.startswith("/api/v1/analysis/retirement")}
    assert sum(len(operations) for operations in retirement.values()) == 13
    for operations in retirement.values():
        for operation in operations.values():
            assert operation["tags"] == ["Retirement"]
    for suffix in ("notify", "start", "link-jira"):
        operation = retirement[f"/api/v1/analysis/retirement/workflow/{{base_name}}/{suffix}"]["put"]
        assert "Admin-only" in operation["description"]
    check = retirement["/api/v1/analysis/retirement/workflow/{base_name}/check-prs"]["post"]
    response = check["responses"]["200"]["content"]["application/json"]["schema"]
    model = schema["components"]["schemas"][response["$ref"].split("/")[-1]]
    assert {"pr_statuses", "jira_status", "deleted", "workflow"} <= model["properties"].keys()
