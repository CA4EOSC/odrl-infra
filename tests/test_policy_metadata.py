"""dcterms / owl:versionInfo metadata on generated policies."""

from datetime import date

from app.services.policy_metadata import stamp_policy_metadata

TODAY = date(2026, 11, 4)


def test_new_policy_gets_all_dates_and_default_version():
    p = stamp_policy_metadata({"@context": "http://www.w3.org/ns/odrl.jsonld"}, today=TODAY)
    assert p["dcterms:created"] == p["dcterms:modified"] == p["dcterms:issued"] == "2026-11-04"
    assert p["owl:versionInfo"] == "1.0"
    assert p["@context"][0] == "http://www.w3.org/ns/odrl.jsonld"
    assert p["@context"][1] == {"dcterms": "http://purl.org/dc/terms/", "owl": "http://www.w3.org/2002/07/owl#"}


def test_existing_policy_keeps_created_and_issued_but_bumps_modified():
    p = stamp_policy_metadata({
        "@context": ["http://www.w3.org/ns/odrl.jsonld", {"odrl": "http://www.w3.org/ns/odrl/2/"}],
        "dcterms:created": "2026-01-02",
        "dcterms:issued": "2023-10-20T22:15:34Z",
        "dcterms:modified": "2026-01-02",
        "owl:versionInfo": "2.1",
    }, today=TODAY)
    assert p["dcterms:created"] == "2026-01-02"
    assert p["dcterms:issued"] == "2023-10-20"
    assert p["dcterms:modified"] == "2026-11-04"
    assert p["owl:versionInfo"] == "2.1"
    # prefixes merged into the existing local context, not appended twice
    assert len(p["@context"]) == 2
    assert p["@context"][1]["owl"] == "http://www.w3.org/2002/07/owl#"


def test_invalid_dates_are_replaced():
    p = stamp_policy_metadata({"dcterms:created": "yesterday"}, today=TODAY)
    assert p["dcterms:created"] == "2026-11-04"


def test_create_endpoint_stamps_metadata(monkeypatch):
    from fastapi.testclient import TestClient
    from app.main import app
    from app.routers import policies

    # Isolate the stamping from SHACL, which depends on fetching remote contexts.
    seen = {}
    monkeypatch.setattr(policies.Validator, "validate_policy",
                        classmethod(lambda cls, p: (seen.setdefault("p", dict(p)), (True, []))[1]))

    policy = {
        "@context": "http://www.w3.org/ns/odrl.jsonld",
        "@type": "Offer",
        "odrl:uid": "urn:uuid:meta-test",
        "dcterms:creator": "Author/Contributor",
        "dcterms:publisher": "https://ror.org/02nkf1q06",
        "odrl:permission": [{"odrl:target": "http://doi.org/10.5255/UKDA-SN-3936-1", "odrl:action": "odrl:use"}],
    }
    r = TestClient(app).post("/api/policy/create", json={"policy": policy, "anchor_did": False})
    assert r.status_code == 200, r.text
    out = r.json()["policy"]
    today = date.today().isoformat()
    assert out["dcterms:created"] == out["dcterms:modified"] == out["dcterms:issued"] == today
    assert out["dcterms:publisher"] == "https://ror.org/02nkf1q06"
    assert out["owl:versionInfo"] == "1.0"
    # stamped before validation and DID anchoring, so the anchored document carries the dates
    assert seen["p"]["dcterms:issued"] == today
