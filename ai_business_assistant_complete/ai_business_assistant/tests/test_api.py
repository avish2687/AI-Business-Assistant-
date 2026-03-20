import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch, MagicMock
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from main import app

client = TestClient(app)


def test_root():
    response = client.get("/")
    assert response.status_code == 200
    assert "AI Business Assistant" in response.json()["message"]


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "healthy"


@patch("app.routes.ai_routes.generate_marketing_content")
def test_generate_content(mock_generate):
    mock_generate.return_value = "Mocked marketing content"

    response = client.post("/api/ai/generate-content", json={
        "business_type": "online bakery",
        "goal": "increase sales"
    })
    assert response.status_code == 200
    assert response.json()["response"] == "Mocked marketing content"


@patch("app.routes.ai_routes.analyze_competitors")
def test_competitor_analysis(mock_analyze):
    mock_analyze.return_value = "Mocked competitor analysis"

    response = client.post("/api/ai/competitor-analysis", json={
        "business_type": "fitness app",
        "market": "India"
    })
    assert response.status_code == 200
    assert "analysis" in response.json()


@patch("app.routes.rag_routes.ingest_documents")
def test_rag_ingest(mock_ingest):
    mock_ingest.return_value = {"status": "success", "chunks_stored": 1}

    response = client.post("/api/rag/ingest", json={
        "texts": ["Sample business document text."],
        "sources": ["test.txt"],
        "store_name": "test"
    })
    assert response.status_code == 200
    assert response.json()["status"] == "success"


@patch("app.routes.rag_routes.query_documents")
def test_rag_query(mock_query):
    mock_query.return_value = {
        "answer": "The return policy is 30 days.",
        "sources": ["policy.txt"],
        "retrieved_chunks": 2
    }

    response = client.post("/api/rag/query", json={
        "question": "What is the return policy?",
        "store_name": "test"
    })
    assert response.status_code == 200
    assert "answer" in response.json()
