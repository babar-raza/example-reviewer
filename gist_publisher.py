"""Compatibility gist publisher for legacy tests."""

from __future__ import annotations

import hashlib
import logging
from typing import Any, Dict, Optional

import requests

logger = logging.getLogger(__name__)


class GistPublisher:
    """Simple GitHub Gist publisher for tests."""

    def __init__(self, owner: str, token: str, db: Any, is_public: bool = True):
        self.owner = owner
        self.token = token
        self.db = db
        self.is_public = is_public

    def publish_gist(
        self,
        snippet_id: int,
        code_content: str,
        filename: str,
        description: str,
        old_gist_id: Optional[str] = None,
        old_owner: Optional[str] = None,
    ) -> Dict[str, Any]:
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
        }
        payload = {
            "description": description,
            "public": self.is_public,
            "files": {filename: {"content": code_content}},
        }
        response = requests.post("https://api.github.com/gists", headers=headers, json=payload)
        if response.status_code == 401:
            error = "Unauthorized"
            self._save_publication(snippet_id, None, filename, None, None, "failed", error, code_content, old_gist_id, old_owner)
            return {"success": False, "gist_id": None, "error": error}
        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            error = "Rate limit exceeded"
            self._save_publication(snippet_id, None, filename, None, None, "failed", error, code_content, old_gist_id, old_owner)
            return {"success": False, "gist_id": None, "error": error}
        if response.status_code != 201:
            error = f"HTTP {response.status_code}"
            self._save_publication(snippet_id, None, filename, None, None, "failed", error, code_content, old_gist_id, old_owner)
            return {"success": False, "gist_id": None, "error": error}

        data = response.json()
        gist_id = data.get("id")
        html_url = data.get("html_url")
        raw_url = None
        files = data.get("files", {})
        if filename in files:
            raw_url = files[filename].get("raw_url")
        elif files:
            raw_url = next(iter(files.values())).get("raw_url")

        self._save_publication(
            snippet_id,
            gist_id,
            filename,
            html_url,
            raw_url,
            "success",
            None,
            code_content,
            old_gist_id,
            old_owner,
        )

        logger.info("Published gist ...%s", self.token[-4:])
        return {"success": True, "gist_id": gist_id, "html_url": html_url, "raw_url": raw_url}

    def _save_publication(
        self,
        snippet_id: int,
        new_gist_id: Optional[str],
        filename: str,
        html_url: Optional[str],
        raw_url: Optional[str],
        status: str,
        error: Optional[str],
        code_content: str,
        old_gist_id: Optional[str],
        old_owner: Optional[str],
    ) -> None:
        code_hash = hashlib.sha256(code_content.encode("utf-8")).hexdigest()
        data = {
            "snippet_id": snippet_id,
            "old_gist_id": old_gist_id,
            "old_gist_owner": old_owner,
            "old_gist_filename": filename,
            "new_gist_id": new_gist_id or "",
            "new_gist_owner": self.owner,
            "new_gist_filename": filename,
            "new_gist_url": html_url or "",
            "new_gist_raw_url": raw_url or "",
            "status": status,
            "error_message": error,
            "code_hash": code_hash,
        }
        if hasattr(self.db, "save_gist_publication"):
            self.db.save_gist_publication(data)
