import httpx
import pytest

from zhihupost import cli
from zhihupost.client import ZhihuClient


def test_delete_parser_flags_and_directory_defaults():
    single = cli.build_parser().parse_args(["delete", "123", "--dry-run"])
    batch = cli.build_parser().parse_args(["delete-dir", "articles", "--dry-run"])
    assert (single.article, single.dry_run) == ("123", True)
    assert (batch.dir, batch.delay, batch.dry_run) == ("articles", 1.5, True)


@pytest.mark.parametrize("target", ["123", "https://zhuanlan.zhihu.com/p/123", "article.md"])
def test_delete_dry_run_is_local(monkeypatch, tmp_path, capsys, target):
    if target == "article.md":
        path = tmp_path / target
        path.write_text("---\nurl: https://zhuanlan.zhihu.com/p/123\n---\nBody\n", encoding="utf-8")
        target = str(path)
        original = path.read_bytes()
    monkeypatch.setattr(cli, "_client_from_store", lambda: pytest.fail("dry-run must not authenticate"))
    assert cli.main(["delete", target, "--dry-run"]) == 0
    assert "would-delete: https://zhuanlan.zhihu.com/p/123" in capsys.readouterr().out
    if target.endswith("article.md"):
        assert path.read_bytes() == original


@pytest.mark.parametrize("status", [200, 204, 404, 403])
def test_delete_uses_stored_client_and_closes_it(monkeypatch, capsys, status):
    requests = []
    client = ZhihuClient(
        "z_c0=synthetic",
        transport=httpx.MockTransport(
            lambda request: requests.append(request) or httpx.Response(status)
        ),
    )
    monkeypatch.setattr(cli, "_client_from_store", lambda: client)
    assert cli.main(["delete", "123"]) == (1 if status == 403 else 0)
    assert [request.method for request in requests] == ["DELETE"]
    assert client._client.is_closed
    output = capsys.readouterr()
    if status == 403:
        assert "403" in output.err
        assert "deleted" not in output.out
    else:
        assert ("already-deleted" if status == 404 else "deleted") in output.out


def test_delete_dir_dry_run_lists_targets_and_summary_without_authentication(monkeypatch, tmp_path, capsys):
    article = tmp_path / "article.md"
    article.write_text("---\nurl: https://zhuanlan.zhihu.com/p/42\n---\nBody\n", encoding="utf-8")
    original = article.read_bytes()
    (tmp_path / "new.md").write_text("# Unpublished", encoding="utf-8")
    monkeypatch.setattr(cli, "_client_from_store", lambda: pytest.fail("dry-run must not authenticate"))
    assert cli.main(["delete-dir", str(tmp_path), "--dry-run"]) == 0
    output = capsys.readouterr().out
    assert "https://zhuanlan.zhihu.com/p/42" in output
    assert "article.md" in output
    assert "would-delete: 1" in output
    assert "skipped: 1" in output
    assert "failed: 0" in output
    assert article.read_bytes() == original


def test_delete_dir_continues_after_failure_and_redacts_cookie(monkeypatch, tmp_path, capsys):
    for name, article_id in [("a.md", "1"), ("b.md", "2")]:
        (tmp_path / name).write_text(
            f"---\nurl: https://zhuanlan.zhihu.com/p/{article_id}\n---\nBody\n", encoding="utf-8"
        )
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(403 if request.url.path.endswith("/1") else 204)

    client = ZhihuClient("z_c0=synthetic-secret", transport=httpx.MockTransport(handler))
    monkeypatch.setattr(cli, "_client_from_store", lambda: client)
    assert cli.main(["delete-dir", str(tmp_path), "--delay", "0"]) == 1
    assert len(requests) == 2
    assert client._client.is_closed
    output = capsys.readouterr()
    assert "succeeded: 1" in output.out
    assert "failed: 1" in output.out
    assert "synthetic-secret" not in output.out + output.err
    assert "url:" in (tmp_path / "a.md").read_text(encoding="utf-8")
    assert "url:" not in (tmp_path / "b.md").read_text(encoding="utf-8")


def test_delete_invalid_input_fails_without_dispatch(monkeypatch, capsys):
    client = ZhihuClient(
        "z_c0=synthetic", transport=httpx.MockTransport(lambda request: pytest.fail("invalid target"))
    )
    monkeypatch.setattr(cli, "_client_from_store", lambda: client)
    assert cli.main(["delete", "https://www.zhihu.com/answer/123"]) == 1
    assert "Only Zhihu articles" in capsys.readouterr().err
    assert client._client.is_closed
