"""Gist service with cache handling for legacy tests."""

from __future__ import annotations

import hashlib
import json
import logging
import shlex
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import requests

logger = logging.getLogger(__name__)


@dataclass
class GistFetchResult:
    success: bool
    gist_id: str
    owner: str
    filename: Optional[str] = None
    content: Optional[str] = None
    language: Optional[str] = None
    content_hash: Optional[str] = None
    error: Optional[str] = None
    skip_reason: Optional[str] = None


class GistService:
    """Fetch and cache GitHub Gist content."""

    def __init__(self, cache_dir: Path, db: Any, cache_ttl_seconds: int = 3600):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.db = db
        self.cache_ttl = timedelta(seconds=cache_ttl_seconds)

    def parse_gist_shortcode(self, shortcode: str) -> Optional[Tuple[str, str, Optional[str]]]:
        if not shortcode:
            return None
        match = self._find_shortcode(shortcode)
        if not match:
            return None
        tokens = shlex.split(match)
        if len(tokens) < 2:
            return None
        owner = tokens[0]
        gist_id = tokens[1]
        filename = tokens[2] if len(tokens) >= 3 else None
        return owner, gist_id, filename

    def fetch_gist(self, gist_id: str, owner: str, filename: Optional[str] = None) -> GistFetchResult:
        cache_data = self._load_cache(gist_id)
        if cache_data and self._is_cache_fresh(cache_data.get("cached_at")):
            return self._result_from_cache(cache_data, gist_id, owner, filename)

        headers = {"Accept": "application/vnd.github.v3+json"}
        if cache_data and cache_data.get("etag"):
            headers["If-None-Match"] = cache_data["etag"]

        response = requests.get(f"https://api.github.com/gists/{gist_id}", headers=headers)
        if response.status_code == 304 and cache_data:
            return self._result_from_cache(cache_data, gist_id, owner, filename, refresh_cache=True)

        if response.status_code == 404:
            self._upsert_gist_status(gist_id, owner, None, "not_found", "Gist not found", None)
            return GistFetchResult(False, gist_id, owner, error="Gist not found")

        if response.status_code == 403 and response.headers.get("X-RateLimit-Remaining") == "0":
            self._upsert_gist_status(gist_id, owner, None, "rate_limited", "Rate limit exceeded", None)
            return GistFetchResult(False, gist_id, owner, error="Rate limit exceeded")

        if response.status_code != 200:
            error = f"HTTP {response.status_code}"
            self._upsert_gist_status(gist_id, owner, None, "error", error, None)
            return GistFetchResult(False, gist_id, owner, error=error)

        data = response.json()
        etag = response.headers.get("ETag")
        self._write_cache(gist_id, etag, data)

        return self._result_from_payload(gist_id, owner, data, filename, etag)

    def verify_cache(self) -> Dict[str, Any]:
        result = {
            "total_files": 0,
            "valid_files": 0,
            "corrupted_files": 0,
            "removed_files": [],
            "errors": [],
        }

        if not self.cache_dir.exists():
            return result

        for cache_file in self.cache_dir.glob("*.json"):
            result["total_files"] += 1
            try:
                data = json.loads(cache_file.read_text(encoding="utf-8"))
                self._validate_cache_data(data)
                result["valid_files"] += 1
            except Exception as exc:
                validation_error = str(exc)
                try:
                    cache_file.unlink()
                    result["corrupted_files"] += 1
                    result["removed_files"].append(str(cache_file))
                    logger.warning("Corrupted cache file detected: %s - %s", cache_file, validation_error)
                except Exception as remove_exc:
                    result["errors"].append(
                        {
                            "file": str(cache_file),
                            "validation_error": validation_error,
                            "removal_error": str(remove_exc),
                        }
                    )
        return result

    def _find_shortcode(self, text: str) -> Optional[str]:
        match = None
        for pattern in (r"\{\{<\s*gist\s+(.+?)\s*>\}\}", r"\{\{<gist\s+(.+?)>\}\}"):
            found = None
            try:
                import re
                found = re.search(pattern, text)
            except Exception:
                found = None
            if found:
                match = found.group(1)
                break
        return match

    def _load_cache(self, gist_id: str) -> Optional[Dict[str, Any]]:
        cache_path = self.cache_dir / f"{gist_id}.json"
        if not cache_path.exists():
            return None
        try:
            return json.loads(cache_path.read_text(encoding="utf-8"))
        except Exception:
            try:
                cache_path.unlink()
            except Exception:
                pass
            return None

    def _write_cache(self, gist_id: str, etag: Optional[str], data: Dict[str, Any]) -> None:
        cache_path = self.cache_dir / f"{gist_id}.json"
        payload = {
            "gist_id": gist_id,
            "etag": etag,
            "cached_at": datetime.now(timezone.utc).isoformat(),
            "data": data,
        }
        cache_path.write_text(json.dumps(payload), encoding="utf-8")

    def _is_cache_fresh(self, cached_at: Optional[str]) -> bool:
        if not cached_at:
            return False
        try:
            cached_dt = datetime.fromisoformat(cached_at)
        except ValueError:
            return False
        return datetime.now(timezone.utc) - cached_dt <= self.cache_ttl

    def _result_from_cache(
        self,
        cache_data: Dict[str, Any],
        gist_id: str,
        owner: str,
        filename: Optional[str],
        refresh_cache: bool = False,
    ) -> GistFetchResult:
        data = cache_data.get("data", {})
        if refresh_cache:
            cache_data["cached_at"] = datetime.now(timezone.utc).isoformat()
            self._write_cache(gist_id, cache_data.get("etag"), data)
        return self._result_from_payload(gist_id, owner, data, filename, cache_data.get("etag"))

    def _result_from_payload(
        self,
        gist_id: str,
        owner: str,
        data: Dict[str, Any],
        filename: Optional[str],
        etag: Optional[str],
    ) -> GistFetchResult:
        files = data.get("files", {})
        selected_name, file_info, skip_reason = self._select_file(files, filename)
        if skip_reason:
            return GistFetchResult(False, gist_id, owner, error=None, skip_reason=skip_reason)

        content = file_info.get("content", "")
        language = file_info.get("language")
        raw_url = file_info.get("raw_url", "")
        content_hash = hashlib.sha256(content.encode("utf-8")).hexdigest()

        self._cache_raw_file(gist_id, selected_name, content)
        self._upsert_gist_status(
            gist_id,
            owner,
            data.get("description"),
            "success",
            None,
            etag,
            updated_at=data.get("updated_at"),
        )
        self._upsert_gist_file(
            gist_id,
            selected_name,
            raw_url,
            language,
            content,
            content_hash,
            file_info.get("size"),
        )

        return GistFetchResult(
            True,
            gist_id,
            owner,
            filename=selected_name,
            content=content,
            language=language,
            content_hash=content_hash,
        )

    def _select_file(
        self,
        files: Dict[str, Any],
        filename: Optional[str],
    ) -> Tuple[Optional[str], Dict[str, Any], Optional[str]]:
        if filename and filename in files:
            return filename, files[filename], None

        csharp_files = [
            (name, info)
            for name, info in files.items()
            if (info.get("language") or "").lower() == "c#" or name.lower().endswith(".cs")
        ]

        if filename and filename not in files:
            return None, {}, f"File not found: {filename}"

        if len(csharp_files) == 0:
            return None, {}, "No C# files found"

        if len(csharp_files) > 1:
            names = ", ".join(name for name, _ in csharp_files)
            return None, {}, f"Ambiguous gist files: {names}"

        return csharp_files[0][0], csharp_files[0][1], None

    def _cache_raw_file(self, gist_id: str, filename: str, content: str) -> None:
        gist_dir = self.cache_dir / gist_id
        gist_dir.mkdir(parents=True, exist_ok=True)
        raw_path = gist_dir / f"{filename}.raw"
        raw_path.write_text(content, encoding="utf-8")

    def _upsert_gist_status(
        self,
        gist_id: str,
        owner: str,
        description: Optional[str],
        status: str,
        error: Optional[str],
        etag: Optional[str],
        updated_at: Optional[str] = None,
    ) -> None:
        if hasattr(self.db, "upsert_gist"):
            self.db.upsert_gist(
                gist_id,
                owner,
                description,
                updated_at or "",
                status,
                etag,
                error,
            )

    def _upsert_gist_file(
        self,
        gist_id: str,
        filename: str,
        raw_url: str,
        language: Optional[str],
        content: str,
        content_hash: str,
        size: Optional[int],
    ) -> None:
        if hasattr(self.db, "upsert_gist_file"):
            self.db.upsert_gist_file(
                gist_id,
                filename,
                raw_url,
                language,
                content,
                content_hash,
                size,
            )

    @staticmethod
    def _validate_cache_data(data: Dict[str, Any]) -> None:
        required = ("gist_id", "etag", "cached_at", "data")
        if not all(key in data and data[key] is not None for key in required):
            raise ValueError("Missing required fields")
        try:
            datetime.fromisoformat(data["cached_at"])
        except ValueError:
            raise ValueError("Invalid cached_at timestamp")
        if not isinstance(data["data"], dict):
            raise ValueError("Invalid data structure")
        if "files" not in data["data"]:
            raise ValueError("Invalid data structure")
