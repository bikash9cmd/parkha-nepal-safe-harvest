import json

import boto3
import pytest
from fastapi.testclient import TestClient
from moto import mock_aws


def test_local_api():
    from parkha.api import app

    c = TestClient(app)
    assert c.get("/health").json()["ok"]
    r = c.post("/ask", json={"question": "Is Furadan banned?"}).json()
    assert "banned" in r["answer"] and r["sources"]


@pytest.fixture
def handler(monkeypatch):
    with mock_aws():
        monkeypatch.setenv("AWS_DEFAULT_REGION", "ap-south-1")
        monkeypatch.setenv("PARKHA_LOG_TABLE", "answers")
        boto3.client("dynamodb").create_table(
            TableName="answers",
            KeySchema=[{"AttributeName": "answer_id", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "answer_id", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        import importlib

        from parkha.aws import handlers

        importlib.reload(handlers)
        yield handlers, boto3.resource("dynamodb").Table("answers")


def _event(route, body=None):
    return {"routeKey": route, "body": json.dumps(body) if body is not None else None}


def test_ask_logs_a_redacted_answer(handler):
    h, table = handler
    r = h.api(_event("POST /ask", {"question": "okra aphid, call 9841234567"}), None)
    body = json.loads(r["body"])
    item = table.get_item(Key={"answer_id": body["answer_id"]})["Item"]
    assert "[phone]" in item["question"] and "9841234567" not in item["question"]
    assert item["expires_at"] > item["ts"]


def test_crisis_question_is_not_stored(handler):
    h, table = handler
    body = json.loads(h.api(_event("POST /ask", {"question": "I want to end my life"}), None)["body"])
    item = table.get_item(Key={"answer_id": body["answer_id"]})["Item"]
    assert "question" not in item and item["refusal"] == "crisis"


def test_feedback(handler):
    h, table = handler
    body = json.loads(h.api(_event("POST /ask", {"question": "Is Furadan banned?"}), None)["body"])
    ok = h.api(_event("POST /feedback", {"answer_id": body["answer_id"], "helpful": False, "note": "wrong"}), None)
    assert ok["statusCode"] == 200
    assert table.get_item(Key={"answer_id": body["answer_id"]})["Item"]["helpful"] is False
    missing = h.api(_event("POST /feedback", {"answer_id": "nope", "helpful": True}), None)
    assert missing["statusCode"] == 404


def test_bad_requests(handler):
    h, _ = handler
    assert h.api(_event("POST /ask", {}), None)["statusCode"] == 400
    assert h.api({"routeKey": "POST /ask", "body": "not json"}, None)["statusCode"] == 400
    assert h.api(_event("GET /nope"), None)["statusCode"] == 404
