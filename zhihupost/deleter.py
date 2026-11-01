"""Delete Zhihu articles through an injected API client."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path
import re
import stat
import tempfile
from typing import Literal

from .client import ZhihuAPIError
from .document import classify_target, parse_document, remove_front_matter_value


@dataclass(frozen=True)
class DeleteResult:
    status: Literal["deleted", "already-deleted", "would-delete", "skipped"]
    url: str | None


class DeleteError(RuntimeError):
    """Sanitized error raised for a failed delete operation."""


class PartialDeleteError(DeleteError):
    """The remote article is gone but its local URL could not be removed."""


class Deleter:
    def __init__(self, client):
        self.client = client

    def delete_article(self, article: str, *, dry_run: bool = False) -> DeleteResult:
        """Delete one article selected by its numeric ID or Zhihu URL."""
        if not isinstance(article, str):
            raise ValueError("Article must be a positive numeric ID or Zhihu article URL")
        article = article.strip()
        if re.fullmatch(r"[0-9]+", article):
            if not article.strip("0"):
                raise ValueError("Article ID must be positive")
            url = f"https://zhuanlan.zhihu.com/p/{article}"
        else:
            url = article
        target = classify_target(url)
        if (
            target.kind != "article"
            or not target.article_id
            or not re.fullmatch(r"[0-9]+", target.article_id)
            or not target.article_id.strip("0")
        ):
            raise ValueError("Only Zhihu articles can be deleted; provide an article ID or URL")
        url = f"https://zhuanlan.zhihu.com/p/{target.article_id}"
        if dry_run:
            return DeleteResult("would-delete", url)
        if self.client is None:
            raise ValueError("An authenticated client is required to delete articles")

        try:
            response = self.client.request(
                "DELETE", f"https://www.zhihu.com/api/v4/articles/{target.article_id}"
            )
        except ZhihuAPIError as exc:
            if exc.status_code == 404:
                return DeleteResult("already-deleted", url)
            raise DeleteError(f"Article deletion failed: {exc}") from None
        except Exception:
            raise DeleteError("Article deletion request failed") from None
        if response.status_code == 404:
            return DeleteResult("already-deleted", url)
        if response.status_code not in (200, 204):
            raise DeleteError(f"Article deletion returned HTTP {response.status_code}")
        return DeleteResult("deleted", url)

    def delete_file(self, path: Path, *, dry_run: bool = False) -> DeleteResult:
        """Delete a Markdown file's article and then remove its URL field."""
        path = Path(path).resolve(strict=True)
        with path.open("r", encoding="utf-8", newline="") as stream:
            text = stream.read()
        document = parse_document(text, path)
        url = document.metadata.get("url")
        if url is None or url == "":
            return DeleteResult("skipped", None)
        target = classify_target(url)
        if target.kind != "article":
            return DeleteResult("skipped", url)

        updated = remove_front_matter_value(text, "url")
        result = self.delete_article(url, dry_run=dry_run)
        if not dry_run:
            try:
                _write_source(path, text, updated)
            except Exception:
                raise PartialDeleteError(
                    f"Article {target.article_id} is deleted but its URL could not be "
                    "removed from the Markdown file; check the file and retry"
                ) from None
        return result


def _write_source(path: Path, original: str, updated: str) -> None:
    """Replace a source file atomically without overwriting concurrent edits."""
    descriptor, name = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="") as stream:
            stream.write(updated)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, stat.S_IMODE(path.stat().st_mode))
        with path.open("r", encoding="utf-8", newline="") as stream:
            if stream.read() != original:
                raise ValueError("Markdown file changed during deletion")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)
