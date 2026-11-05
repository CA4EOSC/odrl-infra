"""Tests for GET /api/policy/existing (search box for existing policies in the Policy Builder)."""

from fastapi.testclient import TestClient

from app.main import app
from app.routers import policies

client = TestClient(app)


def get(**params):
    res = client.get("/api/policy/existing", params=params)
    assert res.status_code == 200
    return res.json()


def test_lists_presets_with_full_policy():
    data = get(limit=200)
    presets = {r["preset"]: r for r in data["results"] if r["source"] == "preset"}
    assert set(policies.PRESET_NAMES) <= set(presets)
    gru = presets["duo-0000042"]
    assert gru["uid"] == "duodrl:DUO_0000042"
    assert gru["title"].startswith("DUO_0000042: General Research Use")
    assert gru["policy"]["odrl:permission"]


def test_query_matches_every_word():
    data = get(q="moratorium duo", include_presets=True)
    assert [r["preset"] for r in data["results"] if r["source"] == "preset"] == ["duo-0000024"]
    assert get(q="moratorium nosuchword")["total"] == 0


def test_query_searches_inside_rules():
    # dpv:IdentityVerification only appears as a purpose in the rules of listing-4.2
    data = get(q="dpv:IdentityVerification")
    assert "listing-4.2" in [r["preset"] for r in data["results"]]


def test_stored_policies_listed(monkeypatch):
    stored = {"@type": "Offer", "odrl:uid": "ex:p1", "dcterms:title": "UKDS safeguarded",
              "dcterms:created": "2026-11-01", "odrl:permission": [{"odrl:target": "ex:ds", "odrl:action": "odrl:use"}]}
    monkeypatch.setattr(policies.qdrant_service, "list_documents",
                        lambda collection, limit=500: [{"did": "did:oyd:abc", "json_ld": stored}])
    data = get(q="ukds", include_presets=False)
    assert data["stored_available"] is True
    [r] = data["results"]
    assert (r["uid"], r["source"], r["title"], r["target"]) == ("did:oyd:abc", "stored", "UKDS safeguarded", "ex:ds")


def test_presets_still_listed_when_index_is_down(monkeypatch):
    def down(*a, **k):
        raise ConnectionError("qdrant offline")
    monkeypatch.setattr(policies.qdrant_service, "list_documents", down)
    data = get()
    assert data["stored_available"] is False
    assert data["total"] == len(policies.PRESET_NAMES)
