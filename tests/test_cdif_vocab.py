"""Tests for the CDIF access vocabularies (config/cv1-3 *.ttl) and their API endpoints."""

from fastapi.testclient import TestClient

from app.main import app
from app.services import cdif_vocab

client = TestClient(app)


def by_label(scheme):
    return {c["label"]: c for c in cdif_vocab.load_scheme(scheme)["concepts"]}


def test_schemes_load():
    data = cdif_vocab.all_schemes()
    assert data["actions"]["available"] and data["actions"]["count"] > 0
    assert data["purposes"]["available"] and data["purposes"]["count"] > 0
    assert data["constraints"]["available"] and data["constraints"]["count"] > 0


def test_action_values_prefer_odrl_terms():
    actions = by_label("cv1")
    assert actions["Read"]["value"] == "odrl:read"
    assert actions["DerivativeWorks"]["value"] == "cc:DerivativeWorks"
    assert actions["Download"]["value"] == "cv1:download"  # CDIF-only action


def test_deprecated_action_points_to_policy_term():
    write = by_label("cv1")["Write"]
    assert write["deprecated"] is True
    assert write["replacedBy"] == "odrl:modify"


def test_purposes_map_to_dpv_with_hierarchy():
    academic = by_label("cv2")["AcademicResearch"]
    assert academic["value"] == "dpv:AcademicResearch"
    assert "cv2:ResearchAndDevelopment" in academic["broader"]


def test_policy_warnings():
    policy = {
        "odrl:permission": [{
            "odrl:action": "odrl:write",
            "odrl:constraint": [
                {"odrl:leftOperand": "odrl:purpose", "odrl:operator": "odrl:eq", "odrl:rightOperand": "dpv:AcademicResearch"},
                {"odrl:leftOperand": "odrl:purpose", "odrl:operator": "odrl:eq", "odrl:rightOperand": "dpv:NotAPurpose"},
            ],
        }]
    }
    warnings = cdif_vocab.policy_warnings(policy)
    assert len(warnings) == 2
    assert "deprecated" in warnings[0] and "odrl:modify" in warnings[0]
    assert "dpv:NotAPurpose" in warnings[1]


def test_endpoints():
    r = client.get("/api/policy/vocab/cdif")
    assert r.status_code == 200
    assert set(r.json()) >= {"prefixes", "actions", "purposes", "constraints"}
    assert client.get("/api/policy/vocab/cdif/cv3").json()["count"] > 0
    assert client.get("/api/policy/vocab/cdif/cv9").status_code == 404


def test_validate_returns_warnings():
    policy = {
        "@context": "http://www.w3.org/ns/odrl.jsonld",
        "@type": "Set",
        "odrl:uid": "urn:uuid:test",
        "odrl:permission": [{"odrl:target": "urn:x", "odrl:action": "odrl:write"}],
    }
    r = client.post("/api/policy/validate", json={"policy": policy})
    assert r.status_code == 200
    assert any("deprecated" in w for w in r.json()["warnings"])
