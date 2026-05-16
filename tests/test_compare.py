from fastapi.testclient import TestClient

from app.main import app


def test_compare_grounded():
    with TestClient(app) as client:
        r = client.post(
            "/chat",
            json={
                "messages": [
                    {
                        "role": "user",
                        "content": "What is the difference between OPQ and Verify G+?",
                    }
                ]
            },
        )
    body = r.json()
    assert body["recommendations"] == []
    assert "shl.com" in body["reply"].lower() or "http" in body["reply"].lower()
    assert body["end_of_conversation"] is False
