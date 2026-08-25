import pytest

from rcars.services.osspa_sync import (
    OsspaSyncError,
    asset_type_tokens,
    content_id_for,
    derive_osspa_status,
    normalize_row,
    parse_palist_csv,
    scope_rows,
)

CSV_HEADER = (
    "ppid,PAName,Heading,islive,showInCatalog,Summary,metaDesc,metaKeyword,"
    "Vertical,Solutions,Product,ProductType,Image1Url,DetailPage,externalUrl\n"
)


def _csv_row(ppid="275", product_type="PA", detail="rhacs.adoc", islive="TRUE", catalog="TRUE"):
    return (
        f"{ppid},{ppid}-rhacs,Multitenant RHACS,{islive},{catalog},A short summary,"
        f"meta desc,security kubernetes,Financial Services,Security,"
        f"Red Hat Advanced Cluster Security,\"{product_type}\",images/x.png,{detail},\n"
    )


def test_parse_requires_core_header_columns():
    with pytest.raises(OsspaSyncError, match="header missing columns"):
        parse_palist_csv("ppid,PAName\n1,x\n")


def test_parse_strips_whitespace():
    rows = parse_palist_csv(CSV_HEADER + _csv_row())
    assert rows[0]["Heading"] == "Multitenant RHACS"
    assert rows[0]["DetailPage"] == "rhacs.adoc"


def test_asset_type_tokens_splits_and_uppercases():
    assert asset_type_tokens("PA,VP") == ["PA", "VP"]
    assert asset_type_tokens(" pa , vp ") == ["PA", "VP"]
    assert asset_type_tokens("") == []


@pytest.mark.parametrize("product_type", ["PA", "PA,VP", "VP", "SP", "sp"])
def test_scope_keeps_architecture_asset_types(product_type):
    rows = parse_palist_csv(CSV_HEADER + _csv_row(product_type=product_type))
    assert len(scope_rows(rows)) == 1


@pytest.mark.parametrize("product_type", ["Demo", "IE", "PA,IE", "Interactive"])
def test_scope_excludes_demo_and_ie(product_type):
    rows = parse_palist_csv(CSV_HEADER + _csv_row(product_type=product_type))
    assert scope_rows(rows) == []


@pytest.mark.parametrize("detail", ["", "https://redhat.com/x", "notes.md"])
def test_scope_requires_an_adoc_detail_page(detail):
    rows = parse_palist_csv(CSV_HEADER + _csv_row(detail=detail))
    assert scope_rows(rows) == []


def test_scope_ingests_regardless_of_live_status():
    rows = parse_palist_csv(CSV_HEADER + _csv_row(islive="FALSE", catalog="FALSE"))
    assert len(scope_rows(rows)) == 1


def test_scope_last_duplicate_ppid_wins():
    rows = parse_palist_csv(
        CSV_HEADER + _csv_row(detail="first.adoc") + _csv_row(detail="second.adoc"))
    scoped = scope_rows(rows)
    assert len(scoped) == 1
    assert scoped[0]["DetailPage"] == "second.adoc"


def test_scope_skips_non_numeric_ppid():
    rows = parse_palist_csv(CSV_HEADER + _csv_row(ppid="abc"))
    assert scope_rows(rows) == []


@pytest.mark.parametrize(
    "islive,catalog,expected",
    [("TRUE", "TRUE", "prod"), ("TRUE", "FALSE", "dev"),
     ("FALSE", "TRUE", "dev"), ("FALSE", "FALSE", "dev"), ("", "", "dev")],
)
def test_derive_osspa_status(islive, catalog, expected):
    assert derive_osspa_status({"islive": islive, "showInCatalog": catalog}) == expected


def test_content_id_format():
    assert content_id_for(275) == "pa:275"
    assert content_id_for("275") == "pa:275"


def test_normalize_row_builds_the_upsert_payload():
    row = parse_palist_csv(CSV_HEADER + _csv_row(product_type="PA,VP"))[0]
    payload = normalize_row(row)

    assert payload["content_id"] == "pa:275"
    assert payload["ppid"] == 275
    assert payload["pa_name"] == "275-rhacs"
    assert payload["display_name"] == "Multitenant RHACS"
    assert payload["status"] == "prod"
    assert payload["summary"] == "A short summary"
    assert payload["products"] == ["Red Hat Advanced Cluster Security"]
    assert payload["solutions"] == ["Security"]
    assert payload["verticals"] == ["Financial Services"]
    assert payload["topics"] == ["Security", "Financial Services"]
    assert payload["audience"] == ["architect", "developer"]
    assert payload["detail_page"] == "rhacs.adoc"
    assert payload["image_url"] == "images/x.png"
    assert payload["is_live"] is True
    assert payload["show_in_catalog"] is True
    assert payload["asset_type"] == "PA,VP"
    assert payload["meta_keyword"] == "security kubernetes"


def test_normalize_row_dedups_topics_from_solutions_and_verticals():
    csv_text = CSV_HEADER + (
        "9,9-x,X,TRUE,TRUE,s,d,k,Security,\"Security, Application Platform\","
        "OpenShift,PA,i.png,x.adoc,\n")
    payload = normalize_row(parse_palist_csv(csv_text)[0])
    assert payload["topics"] == ["Security", "Application Platform"]
