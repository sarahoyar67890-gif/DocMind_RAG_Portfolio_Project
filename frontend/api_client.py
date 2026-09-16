"""
api_client.py — Thin HTTP client the Streamlit frontend uses to talk to the
DocMind FastAPI backend. No RAG logic lives here or anywhere in the
frontend — this file only makes requests and translates errors into plain
messages the UI can show.
"""

import os
import requests

BACKEND_URL = os.environ.get("BACKEND_URL", "http://localhost:8000")
REQUEST_TIMEOUT = 120  # seconds; document processing / LLM calls can take a while


class APIError(Exception):
    """Raised with a clean, user-facing message extracted from the backend's
    error response."""


def _handle_response(response: requests.Response) -> dict:
    if response.ok:
        return response.json()
    try:
        detail = response.json().get("detail", "Unknown error.")
    except Exception:
        detail = f"Backend returned status {response.status_code}."
    raise APIError(detail)


def check_health() -> dict:
    try:
        resp = requests.get(f"{BACKEND_URL}/health", timeout=10)
        return _handle_response(resp)
    except requests.exceptions.ConnectionError:
        raise APIError(f"Can't reach the backend at {BACKEND_URL}. Is it running?")
    except requests.exceptions.Timeout:
        raise APIError("Backend health check timed out.")


def upload_document(file_bytes: bytes, filename: str) -> dict:
    try:
        files = {"file": (filename, file_bytes, "application/pdf")}
        resp = requests.post(f"{BACKEND_URL}/documents/upload", files=files, timeout=REQUEST_TIMEOUT)
        return _handle_response(resp)
    except requests.exceptions.ConnectionError:
        raise APIError(f"Can't reach the backend at {BACKEND_URL}. Is it running?")
    except requests.exceptions.Timeout:
        raise APIError("Document processing timed out. Try a smaller file.")


def list_documents() -> dict:
    try:
        resp = requests.get(f"{BACKEND_URL}/documents", timeout=15)
        return _handle_response(resp)
    except requests.exceptions.ConnectionError:
        raise APIError(f"Can't reach the backend at {BACKEND_URL}. Is it running?")


def select_documents(document_ids: list[str]) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/documents/select",
            json={"document_ids": document_ids},
            timeout=15,
        )
        return _handle_response(resp)
    except requests.exceptions.ConnectionError:
        raise APIError(f"Can't reach the backend at {BACKEND_URL}. Is it running?")


def delete_document(document_id: str) -> dict:
    try:
        resp = requests.delete(f"{BACKEND_URL}/documents/{document_id}", timeout=15)
        return _handle_response(resp)
    except requests.exceptions.ConnectionError:
        raise APIError(f"Can't reach the backend at {BACKEND_URL}. Is it running?")


def get_insights(document_id: str) -> dict:
    try:
        resp = requests.post(
            f"{BACKEND_URL}/documents/insights",
            json={"document_id": document_id},
            timeout=REQUEST_TIMEOUT,
        )
        return _handle_response(resp)
    except requests.exceptions.ConnectionError:
        raise APIError(f"Can't reach the backend at {BACKEND_URL}. Is it running?")
    except requests.exceptions.Timeout:
        raise APIError("Generating the document overview timed out.")


def ask_question(question: str, document_ids: list[str] = None, top_k: int = None) -> dict:
    try:
        payload = {"question": question}
        if document_ids:
            payload["document_ids"] = document_ids
        if top_k:
            payload["top_k"] = top_k
        resp = requests.post(f"{BACKEND_URL}/query", json=payload, timeout=REQUEST_TIMEOUT)
        return _handle_response(resp)
    except requests.exceptions.ConnectionError:
        raise APIError(f"Can't reach the backend at {BACKEND_URL}. Is it running?")
    except requests.exceptions.Timeout:
        raise APIError("The request timed out waiting for an answer.")
