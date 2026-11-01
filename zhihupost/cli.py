"""Command-line interface for Markdown rendering and Zhihu content management."""

from __future__ import annotations

import argparse
import getpass
import json
import os
import sys
from pathlib import Path
from typing import Any

from .auth import parse_cookie_header, resolve_cookie, validate_cookie
from .batch import BatchSummary, delete_directory, publish_directory
from .client import ZhihuClient
from .config import CookieError, CookieStore
from .deleter import Deleter, DeleteResult
from .document import parse_document
from .images import ImageUploader
from .markdown import render_markdown
from .publisher import Publisher, PublishResult


_KNOWN_COOKIE: str | None = None

# ANSI color codes for terminal output
_GREEN = "\033[32m"
_RED = "\033[31m"
_RESET = "\033[0m"


def _green(text: str) -> str:
    return f"{_GREEN}{text}{_RESET}"


def _red(text: str) -> str:
    return f"{_RED}{text}{_RESET}"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="zhihupost")
    commands = parser.add_subparsers(dest="command", required=True)

    login = commands.add_parser("login", help="Log in to Zhihu")
    login.add_argument("--stdin", action="store_true", help="Read the Cookie header from standard input")
    commands.add_parser("whoami", help="Show the current account")
    commands.add_parser("logout", help="Log out of Zhihu")

    render = commands.add_parser("render", help="Render a Markdown file")
    render.add_argument("file")

    publish = commands.add_parser("publish", help="Publish a Markdown file")
    publish.add_argument("file")
    publish.add_argument("--draft", action="store_true")
    publish.add_argument("--dry-run", action="store_true")

    publish_dir = commands.add_parser("publish-dir", help="Publish Markdown files in a directory")
    publish_dir.add_argument("dir")
    publish_dir.add_argument("--draft", action="store_true")
    publish_dir.add_argument("--delay", type=float, default=60.0, metavar="SECONDS")

    delete = commands.add_parser("delete", help="Delete an article by ID, URL, or Markdown file")
    delete.add_argument("article")
    delete.add_argument("--dry-run", action="store_true", help="Preview without deleting or changing files")

    delete_dir = commands.add_parser("delete-dir", help="Delete articles linked from Markdown files")
    delete_dir.add_argument("dir")
    delete_dir.add_argument("--delay", type=float, default=1.5, metavar="SECONDS")
    delete_dir.add_argument("--dry-run", action="store_true", help="Preview without deleting or changing files")

    upload_image = commands.add_parser("upload-image", help="Upload an image file")
    upload_image.add_argument("file")
    return parser


def main(argv: list[str] | None = None) -> int:
    global _KNOWN_COOKIE
    _KNOWN_COOKIE = None
    args = build_parser().parse_args(argv)
    try:
        if args.command == "login":
            return _login(args)
        if args.command == "whoami":
            return _whoami()
        if args.command == "logout":
            return _logout()
        if args.command == "render":
            return _render(Path(args.file))
        if args.command == "publish":
            return _publish(Path(args.file), draft=args.draft, dry_run=args.dry_run)
        if args.command == "publish-dir":
            return _publish_dir(Path(args.dir), draft=args.draft, delay=args.delay)
        if args.command == "delete":
            return _delete(args.article, dry_run=args.dry_run)
        if args.command == "delete-dir":
            return _delete_dir(Path(args.dir), dry_run=args.dry_run, delay=args.delay)
        if args.command == "upload-image":
            return _upload_image(Path(args.file))
        raise ValueError(f"Unsupported command: {args.command}")
    except Exception as exc:
        print(f"error: {_safe_error(exc)}", file=sys.stderr)
        return 1


def _login(args: argparse.Namespace) -> int:
    cookie = (sys.stdin.read() if args.stdin else getpass.getpass("Zhihu Cookie: ")).strip()
    if not cookie:
        raise CookieError("Cookie is empty")
    _remember_cookie(cookie)
    client = ZhihuClient(cookie)
    try:
        profile = validate_cookie(client)
    finally:
        client.close()
    store = CookieStore()
    store.save(cookie)
    print(_profile_text(profile))
    return 0


def _whoami() -> int:
    cookie = resolve_cookie(CookieStore())
    _remember_cookie(cookie)
    client = ZhihuClient(cookie)
    try:
        profile = client.me()
    finally:
        client.close()
    print(_profile_text(profile))
    return 0


def _logout() -> int:
    CookieStore().remove()
    print("Logged out")
    return 0


def _render(path: Path) -> int:
    document = parse_document(_read_text(path), path)
    print(render_markdown(document.body), end="")
    return 0


def _publish(path: Path, *, draft: bool, dry_run: bool) -> int:
    if dry_run:
        result = Publisher(None, None).publish_file(path, draft=draft, dry_run=True)
        _print_result(result)
        return 0
    client, publisher = _publisher_from_store()
    try:
        result = publisher.publish_file(path, draft=draft)
        _print_result(result)
        return 0
    finally:
        client.close()


def _publish_dir(path: Path, *, draft: bool, delay: float) -> int:
    client, publisher = _publisher_from_store()
    try:
        summary = publish_directory(path, publisher, draft=draft, delay=delay)
        _print_summary(summary)
        return 1 if summary.failed else 0
    finally:
        client.close()


def _upload_image(path: Path) -> int:
    client = _client_from_store()
    try:
        print(ImageUploader(client).upload(str(path), path.parent))
        return 0
    finally:
        client.close()


def _delete(article: str, *, dry_run: bool) -> int:
    client = None if dry_run else _client_from_store()
    try:
        deleter = Deleter(client)
        if "://" in article or (article.isascii() and article.isdecimal()):
            result = deleter.delete_article(article, dry_run=dry_run)
        else:
            result = deleter.delete_file(Path(article), dry_run=dry_run)
        _print_delete_result(result)
        return 0
    finally:
        if client is not None:
            client.close()


def _delete_dir(path: Path, *, dry_run: bool, delay: float) -> int:
    client = None if dry_run else _client_from_store()
    try:
        summary = delete_directory(
            path,
            Deleter(client),
            dry_run=dry_run,
            delay=delay,
            on_result=lambda source, result: _print_delete_result(result, source),
        )
        _print_summary(summary, succeeded_label="would-delete" if dry_run else "succeeded")
        return 1 if summary.failed else 0
    finally:
        if client is not None:
            client.close()


def _print_delete_result(result: DeleteResult, path: Path | None = None) -> None:
    status = _green(result.status) if result.status in {"deleted", "already-deleted"} else result.status
    source = f" ({path})" if path is not None else ""
    detail = f": {result.url}" if result.url else ""
    print(f"{status}{source}{detail}")


def _publisher_from_store():
    client = _client_from_store()
    try:
        uploader = ImageUploader(client)
        return client, Publisher(client, uploader)
    except Exception:
        client.close()
        raise


def _client_from_store():
    cookie = resolve_cookie(CookieStore())
    _remember_cookie(cookie)
    return ZhihuClient(cookie)


def _read_text(path: Path) -> str:
    with path.open("r", encoding="utf-8", newline="") as stream:
        return stream.read()


def _print_result(result: PublishResult) -> None:
    detail = f": {_green(result.url)}" if result.url else ""
    title = f" ({result.title})" if result.title else ""
    status = _green(result.status) if result.status in ("published", "draft") else result.status
    print(f"{status}{title}{detail}")


def _print_summary(summary: BatchSummary, *, succeeded_label: str = "succeeded") -> None:
    print(f"{succeeded_label}: {summary.succeeded}")
    print(f"skipped: {summary.skipped}")
    print(f"failed: {summary.failed}")
    for path, message in summary.failures:
        print(f"failed: {path}: {_red(_safe_error(message))}")


def _profile_text(profile: Any) -> str:
    if not isinstance(profile, dict):
        return "{}"
    safe = {
        key: profile[key]
        for key in ("id", "name", "url_token", "headline")
        if key in profile and isinstance(profile[key], (str, int, float, bool))
    }
    return json.dumps(safe, ensure_ascii=False, sort_keys=True)


def _safe_error(error: object) -> str:
    message = str(error).strip() or error.__class__.__name__
    if _KNOWN_COOKIE:
        message = message.replace(_KNOWN_COOKIE, "[redacted]")
        try:
            for value in parse_cookie_header(_KNOWN_COOKIE).values():
                message = message.replace(value, "[redacted]")
        except (TypeError, ValueError):
            pass
    environment_cookie = os.environ.get("ZHIHU_COOKIE")
    if environment_cookie:
        message = message.replace(environment_cookie, "[redacted]")
        try:
            for value in parse_cookie_header(environment_cookie).values():
                message = message.replace(value, "[redacted]")
        except (TypeError, ValueError):
            pass
    return message


def _remember_cookie(cookie: str) -> None:
    global _KNOWN_COOKIE
    _KNOWN_COOKIE = cookie


if __name__ == "__main__":
    raise SystemExit(main())
