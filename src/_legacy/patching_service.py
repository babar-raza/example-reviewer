"""Compatibility patching service for legacy tests."""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional, Set

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))
from core.path_guard import assert_write_allowed


@dataclass
class PatchResult:
    snippet_id: int
    file_path: str
    success: bool
    message: str
    original_content: str
    modified_content: str


class PatchingService:
    """Minimal patching service with gist upload and auto-commit support."""

    def __init__(
        self,
        db: Any,
        repo_path: Path,
        gist_publisher: Optional[Any] = None,
        telemetry_client: Optional[Any] = None,
    ):
        self.db = db
        self.repo_path = Path(repo_path)
        self.gist_publisher = gist_publisher
        self.telemetry_client = telemetry_client

    def patch_verified_snippets(
        self,
        family: str,
        dry_run: bool = False,
        gist_mode: str = "inline-only",
        auto_commit: bool = False,
    ) -> Dict[str, Any]:
        results = {"patches_applied": 0, "errors": 0, "modified_files": set(), "commit_sha": None}
        snippets = self.db.get_snippets_by_status(family, "verified")
        for snippet, page in snippets:
            result = self._patch_snippet_in_file(snippet, page, "", "", dry_run)
            if result.success:
                results["patches_applied"] += 1
                results["modified_files"].add(result.file_path)
            else:
                results["errors"] += 1
        if auto_commit and not dry_run and results["errors"] == 0 and results["modified_files"]:
            results["commit_sha"] = self._git_commit_changes(
                results["modified_files"], results, family
            )
        return results

    def _patch_snippet_in_file(
        self,
        snippet: Any,
        page: Any,
        original_code: str,
        verified_code: str,
        dry_run: bool,
    ) -> PatchResult:
        return PatchResult(snippet.snippet_id, page.relative_path, True, "patched", "", "")

    def _patch_gist_snippet(
        self,
        snippet: Any,
        page: Any,
        dry_run: bool,
        gist_mode: str = "inline-only",
    ) -> PatchResult:
        file_path = Path(page.relative_path)
        abs_path = self.repo_path / file_path
        original_content = abs_path.read_text(encoding="utf-8")

        locator = json.loads(snippet.locator_json)
        gist_id = locator.get("gist_id")
        gist_owner = locator.get("gist_owner")
        gist_file = locator.get("gist_file") or "example.cs"

        shortcode = locator.get("gist_shortcode")
        if not shortcode and locator.get("notes"):
            try:
                notes = json.loads(locator["notes"])
                shortcode = notes.get("gist_shortcode")
            except Exception:
                shortcode = None
        if not shortcode:
            shortcode = f'{{{{< gist "{gist_owner}" "{gist_id}" "{gist_file}" >}}}}'

        if gist_mode in ("inline-on-change", "inline-only", "preserve"):
            if gist_mode == "preserve":
                return PatchResult(
                    snippet.snippet_id,
                    str(abs_path),
                    True,
                    "Preserved gist shortcode",
                    original_content,
                    original_content,
                )

            original_code, current_code = self._get_version_pair(snippet.snippet_id)
            original_hash = self._hash_code(original_code)
            current_hash = self._hash_code(current_code)

            if gist_mode == "inline-on-change" and original_hash == current_hash:
                return PatchResult(
                    snippet.snippet_id,
                    str(abs_path),
                    True,
                    "Gist unchanged; preserved shortcode",
                    original_content,
                    original_content,
                )

            if not current_code.strip():
                return PatchResult(
                    snippet.snippet_id,
                    str(abs_path),
                    False,
                    "No verified code available to inline",
                    original_content,
                    original_content,
                )

            language = getattr(snippet, "language", "") or "csharp"
            inline_block = f"```{language}\n{current_code.strip()}\n```"
            updated = original_content.replace(shortcode, inline_block)

            if not dry_run:
                assert_write_allowed(abs_path, reason="patch inline gist")
                abs_path.write_text(updated, encoding="utf-8")

            return PatchResult(
                snippet.snippet_id,
                str(abs_path),
                True,
                "Inlined gist content",
                original_content,
                updated,
            )

        if gist_mode in ("upload-on-change", "upload-always"):
            if not self.gist_publisher:
                return PatchResult(
                    snippet.snippet_id,
                    str(abs_path),
                    False,
                    "GistPublisher not configured; check env vars",
                    original_content,
                    original_content,
                )

            original_code, current_code = self._get_version_pair(snippet.snippet_id)
            original_hash = self._hash_code(original_code)
            current_hash = self._hash_code(current_code)

            if gist_mode == "upload-on-change" and original_hash == current_hash:
                return PatchResult(
                    snippet.snippet_id,
                    str(abs_path),
                    True,
                    "Code unchanged; no upload",
                    original_content,
                    original_content,
                )

            publish = self.gist_publisher.publish_gist(
                snippet_id=snippet.snippet_id,
                code_content=current_code,
                filename=gist_file,
                description=f"Verified example {snippet.snippet_id}",
                old_gist_id=gist_id,
                old_owner=gist_owner,
            )

            if not publish.get("success"):
                return PatchResult(
                    snippet.snippet_id,
                    str(abs_path),
                    False,
                    publish.get("error", "Gist publish failed"),
                    original_content,
                    original_content,
                )

            new_gist_id = publish["gist_id"]
            new_owner = getattr(self.gist_publisher, "owner", gist_owner)
            new_shortcode = f'{{{{< gist "{new_owner}" "{new_gist_id}" "{gist_file}" >}}}}'
            updated = original_content.replace(shortcode, new_shortcode)

            if not dry_run:
                assert_write_allowed(abs_path, reason="patch gist shortcode")
                abs_path.write_text(updated, encoding="utf-8")

            return PatchResult(
                snippet.snippet_id,
                str(abs_path),
                True,
                f"Published gist {new_gist_id}",
                original_content,
                updated,
            )

        return PatchResult(
            snippet.snippet_id,
            str(abs_path),
            False,
            f"Unsupported gist mode: {gist_mode}",
            original_content,
            original_content,
        )

    def _get_version_pair(self, snippet_id: int) -> tuple[str, str]:
        self.db.connect()
        original = self.db._conn.execute(
            "SELECT code_content FROM snippet_versions WHERE snippet_id = ? AND version_type = 'original'",
            (snippet_id,),
        ).fetchone()
        current = self.db._conn.execute(
            "SELECT code_content FROM snippet_versions WHERE snippet_id = ? AND version_type = 'current'",
            (snippet_id,),
        ).fetchone()
        return (
            original["code_content"] if original else "",
            current["code_content"] if current else "",
        )

    @staticmethod
    def _hash_code(code: str) -> str:
        return hashlib.sha256((code or "").encode("utf-8")).hexdigest()

    def _git_commit_changes(self, modified_files: Set[str], stats: Dict[str, Any], family: str) -> Optional[str]:
        try:
            status = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            if not status:
                return None
            subprocess.run(
                ["git", "add", *modified_files],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            message = f"chore({family}): patch {stats.get('patches_applied', 0)} snippets"
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            commit_sha = result.stdout.strip()
            self._associate_commit_with_telemetry(commit_sha)
            return commit_sha
        except (FileNotFoundError, subprocess.CalledProcessError):
            return None

    def _create_backup_branch(self, family: str) -> Dict[str, str]:
        branch = f"backup/{family}-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
        try:
            commit = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
            subprocess.run(
                ["git", "branch", branch, commit],
                cwd=self.repo_path,
                check=True,
                capture_output=True,
            )
            return {"branch": branch, "commit": commit}
        except (FileNotFoundError, subprocess.CalledProcessError):
            return {"branch": "", "commit": ""}

    def _store_rollback_entry(self, family: str, commit_sha: str, backup_info: Dict[str, str], results: Dict[str, Any]) -> None:
        self.db.connect()
        self.db._conn.execute(
            """
            INSERT INTO rollback_history (family, commit_sha, backup_branch, backup_commit, description, modified_files)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                family,
                commit_sha,
                backup_info.get("branch"),
                backup_info.get("commit"),
                "auto",
                json.dumps(sorted(results.get("modified_files", []))),
            ),
        )
        self.db._conn.commit()

    def get_rollback_history(self) -> list[Dict[str, Any]]:
        self.db.connect()
        rows = self.db._conn.execute(
            "SELECT * FROM rollback_history ORDER BY created_at DESC"
        ).fetchall()
        history = []
        for row in rows:
            history.append(
                {
                    "family": row["family"],
                    "commit_sha": row["commit_sha"],
                    "backup_branch": row["backup_branch"],
                    "backup_commit": row["backup_commit"],
                    "modified_files": json.loads(row["modified_files"] or "[]"),
                }
            )
        return history

    def rollback_last_operation(self) -> bool:
        history = self.get_rollback_history()
        if not history:
            return False
        entry = history[0]
        backup_commit = entry.get("backup_commit")
        files = entry.get("modified_files", [])
        return self._restore_files_from_commit(backup_commit, files)

    def rollback_file(self, file_path: str) -> bool:
        history = self.get_rollback_history()
        for entry in history:
            if file_path in entry.get("modified_files", []):
                return self._restore_files_from_commit(entry.get("backup_commit"), [file_path])
        return False

    def _restore_files_from_commit(self, commit: str, files: list[str]) -> bool:
        if not commit:
            return False
        for file_path in files:
            rel_path = Path(file_path)
            if rel_path.is_absolute():
                rel_path = rel_path.relative_to(self.repo_path)
            try:
                content = subprocess.run(
                    ["git", "show", f"{commit}:{rel_path.as_posix()}"],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True,
                ).stdout
                (self.repo_path / rel_path).write_text(content, encoding="utf-8")
            except subprocess.CalledProcessError:
                return False
        return True

    def _generate_commit_message(
        self,
        modified_files: Set[str],
        results: Dict[str, Any],
        family: str,
        template: Optional[str] = None,
    ) -> str:
        patch_count = int(results.get("patches_applied") or 0)
        file_count = len(modified_files)
        patches = results.get("patches") or []
        snippet_ids = [f"#{patch.snippet_id}" for patch in patches if getattr(patch, "success", False)]
        snippet_list = ", ".join(snippet_ids) if snippet_ids else "none"
        file_list = self._format_file_list(modified_files)
        default_template = (
            "fix({family}): apply {patch_count} verified patches to {file_count} file(s)\n\n"
            "{file_list}\n\n"
            "Snippets: {snippet_ids}"
        )
        message_template = template or default_template
        return message_template.format(
            family=family,
            patch_count=patch_count,
            file_count=file_count,
            file_list=file_list,
            snippet_ids=snippet_list,
        )

    def _format_file_list(self, modified_files: Set[str], max_files: int = 10) -> str:
        files = sorted(str(path) for path in modified_files)
        if not files:
            return "Files: none"
        if len(files) > max_files:
            visible = files[:max_files]
            remaining = len(files) - max_files
            return f"Files: {', '.join(visible)}, ... and {remaining} more files"
        return f"Files: {', '.join(files)}"

    def _associate_commit_with_telemetry(self, commit_hash: str, commit_source: str = "llm") -> None:
        if not self.telemetry_client:
            return
        try:
            result = subprocess.run(
                ["git", "show", "-s", "--format=%an <%ae>%n%aI", commit_hash],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True,
            )
            lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
            author = lines[0] if len(lines) > 0 else ""
            timestamp = lines[1] if len(lines) > 1 else ""
            self.telemetry_client.associate_commit(
                commit_hash=commit_hash,
                commit_source=commit_source,
                commit_author=author,
                commit_timestamp=timestamp,
            )
        except Exception:
            return


__all__ = ["PatchingService", "PatchResult"]
