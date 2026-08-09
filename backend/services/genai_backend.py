"""
Where Gemini calls go: Vertex AI, or the AI Studio (Generative Language) API.

Both backends speak the same `generateContent` request and response shape, so the only
things that differ are the URL and how the call is authenticated:

* **Vertex AI** — `{location}-aiplatform.googleapis.com`, authenticated with an OAuth
  bearer token from Application Default Credentials. On Cloud Run that is the service
  account attached to the service, with no key material anywhere. This is the path to use
  when the billing/credits live on a GCP project.
* **AI Studio** — `generativelanguage.googleapis.com` with `?key=<API key>`. Simpler for
  local work, but the quota belongs to whichever account minted the key.

Selection is by `AI_BACKEND` (`vertex` | `studio`). Left unset, Vertex is used when a
project is configured, otherwise the API key.
"""
from __future__ import annotations

import logging
import os
import threading
from typing import Dict, Optional, Tuple

from dotenv import load_dotenv

# Load .env here too rather than relying on config.py having been imported first: the
# offline scripts and tests import this module directly, and a missing GOOGLE_CLOUD_PROJECT
# silently produces a malformed Vertex URL instead of an error. load_dotenv is idempotent.
load_dotenv()

logger = logging.getLogger(__name__)

_SCOPE = "https://www.googleapis.com/auth/cloud-platform"

_creds = None
_creds_lock = threading.Lock()


def project() -> str:
    return os.getenv("GOOGLE_CLOUD_PROJECT", "") or ""


def location() -> str:
    return os.getenv("VERTEX_AI_LOCATION", "us-central1") or "us-central1"


def api_key() -> str:
    return os.getenv("GEMINI_API_KEY", "") or ""


def backend() -> str:
    """'vertex' or 'studio'. Explicit AI_BACKEND wins; otherwise infer from what's configured."""
    choice = (os.getenv("AI_BACKEND", "") or "").strip().lower()
    if choice in ("vertex", "studio"):
        return choice
    if project() and not api_key():
        return "vertex"
    return "studio" if api_key() else "vertex"


def is_vertex() -> bool:
    return backend() == "vertex"


def endpoint(model: str) -> str:
    """Full generateContent URL for the active backend."""
    if not is_vertex():
        return f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

    loc = location()
    host = "aiplatform.googleapis.com" if loc == "global" else f"{loc}-aiplatform.googleapis.com"
    return (f"https://{host}/v1/projects/{project()}/locations/{loc}"
            f"/publishers/google/models/{model}:generateContent")


def _access_token() -> Optional[str]:
    """Bearer token from Application Default Credentials, refreshed when stale."""
    global _creds
    try:
        from google.auth import default as google_auth_default
        from google.auth.transport.requests import Request as GoogleAuthRequest
    except ImportError:
        logger.error("google-auth is not installed; cannot authenticate to Vertex AI")
        return None

    with _creds_lock:
        if _creds is None:
            try:
                _creds, detected_project = google_auth_default(scopes=[_SCOPE])
            except Exception as e:
                logger.error(f"No Application Default Credentials for Vertex AI: {e}")
                return None
            # ADC often knows the project even when the env var wasn't set.
            if detected_project and not project():
                os.environ["GOOGLE_CLOUD_PROJECT"] = detected_project

        if not _creds.valid:
            try:
                _creds.refresh(GoogleAuthRequest())
            except Exception as e:
                logger.error(f"Failed to refresh Vertex AI credentials: {e}")
                return None
        return _creds.token


def request_args(model: str) -> Tuple[str, Dict[str, str]]:
    """
    Return ``(url, headers)`` ready for a POST.

    On the AI Studio path the key is carried in the query string; on Vertex it is a bearer
    token, so callers must not append `?key=` themselves.
    """
    headers = {"Content-Type": "application/json"}

    if is_vertex():
        # Token first: fetching it can discover the project from ADC, which the URL needs.
        token = _access_token()
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return endpoint(model), headers

    return f"{endpoint(model)}?key={api_key()}", headers


def describe() -> str:
    """One line for the startup log."""
    if is_vertex():
        return f"Vertex AI (project={project() or '<unset>'}, location={location()})"
    key = api_key()
    return f"AI Studio API (key ...{key[-6:]})" if key else "AI Studio API (no key configured!)"
