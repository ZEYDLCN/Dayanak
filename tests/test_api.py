from fastapi.testclient import TestClient

from app.main import create_app


def client(service):
    return TestClient(create_app(service))


def test_health(service):
    with client(service) as c:
        body = c.get("/health").json()
    assert body["status"] == "ok" and body["documents"] == 10


def test_documents_lists_versions(service):
    with client(service) as c:
        docs = {d["doc_id"]: d for d in c.get("/documents").json()}
    assert docs["iade-proseduru-v1"]["status"] == "superseded"
    assert docs["iade-proseduru-v2"]["status"] == "current"
    assert "İade Süresi" in docs["iade-proseduru-v2"]["sections"]


def test_ask_contract(service):
    with client(service) as c:
        r = c.post("/ask", json={"question": "İade süresi kaç gün?"})
    assert r.status_code == 200
    body = r.json()
    assert body["answerable"] is True
    assert {"doc_id", "title", "version", "section", "snippet"} <= body["sources"][0].keys()
    assert body["conflicts"][0]["selected_doc_id"] == "iade-proseduru-v2"


def test_ask_unanswerable(service):
    with client(service) as c:
        body = c.post("/ask", json={"question": "Bugün hava nasıl olacak?"}).json()
    assert body["answerable"] is False and body["sources"] == []


def test_ask_validation(service):
    with client(service) as c:
        assert c.post("/ask", json={"question": "ab"}).status_code == 422
        assert c.post("/ask", json={}).status_code == 422
