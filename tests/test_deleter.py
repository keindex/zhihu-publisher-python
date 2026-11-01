import httpx
import pytest

from zhihupost.client import ZhihuClient
from zhihupost.deleter import Deleter, DeleteError, DeleteResult, PartialDeleteError
from zhihupost.document import parse_document, remove_front_matter_value


ARTICLE_URL = "https://zhuanlan.zhihu.com/p/123"
COOKIE = "z_c0=synthetic-secret; _xsrf=synthetic-xsrf"


@pytest.mark.parametrize("article", ["123", ARTICLE_URL, f"{ARTICLE_URL}?utm_source=test#section"])
@pytest.mark.parametrize("status_code", [200, 204, 404])
def test_delete_article_uses_authenticated_delete_without_body(article, status_code):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(status_code)

    client = ZhihuClient(COOKIE, transport=httpx.MockTransport(handler))
    try:
        result = Deleter(client).delete_article(article)
    finally:
        client.close()

    status = "already-deleted" if status_code == 404 else "deleted"
    assert result == DeleteResult(status, ARTICLE_URL)
    assert len(requests) == 1
    request = requests[0]
    assert request.method == "DELETE"
    assert str(request.url) == "https://www.zhihu.com/api/v4/articles/123"
    assert request.headers["cookie"] == COOKIE
    assert request.headers["x-xsrftoken"] == "synthetic-xsrf"
    assert request.content == b""


@pytest.mark.parametrize(
    "article",
    [
        "", "0", "000", "-1", "1/../../2", None, 123,
        "http://zhuanlan.zhihu.com/p/123",
        "https://example.org/zhuanlan.zhihu.com/p/123",
        "https://zhuanlan.zhihu.com.evil.test/p/123",
        "https://zhuanlan.zhihu.com:444/p/123",
        "https://synthetic-secret@zhuanlan.zhihu.com/p/123",
        "https://zhuanlan.zhihu.com/p/0",
        "https://zhuanlan.zhihu.com/p/１２３",
        "https://www.zhihu.com/question/123",
        "https://www.zhihu.com/answer/123",
    ],
)
def test_delete_article_rejects_invalid_targets_before_sending(article):
    requests = []
    client = ZhihuClient(
        COOKIE,
        transport=httpx.MockTransport(lambda request: requests.append(request) or httpx.Response(204)),
    )
    try:
        with pytest.raises(ValueError):
            Deleter(client).delete_article(article)
    finally:
        client.close()
    assert requests == []


def test_delete_article_dry_run_needs_no_client():
    assert Deleter(None).delete_article("123", dry_run=True) == DeleteResult("would-delete", ARTICLE_URL)
    with pytest.raises(ValueError, match="authenticated"):
        Deleter(None).delete_article("123")


@pytest.mark.parametrize("status_code", [202, 301, 403, 429, 500])
def test_delete_article_rejects_other_statuses_without_leaking_response(status_code):
    requests = []

    def handler(request):
        requests.append(request)
        return httpx.Response(
            status_code,
            headers={"location": "https://example.org/collect"},
            text=f"sensitive response {COOKIE}",
        )

    client = ZhihuClient(COOKIE, transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(DeleteError) as error:
            Deleter(client).delete_article("123")
    finally:
        client.close()
    assert str(status_code) in str(error.value)
    assert "synthetic-secret" not in str(error.value)
    assert "sensitive response" not in str(error.value)
    assert len(requests) == 1


def test_delete_article_transport_failure_is_sanitized():
    def handler(request):
        raise httpx.ConnectError(f"failed with {COOKIE}", request=request)

    client = ZhihuClient(COOKIE, transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(DeleteError) as error:
            Deleter(client).delete_article("123")
    finally:
        client.close()
    assert "synthetic-secret" not in str(error.value)
    assert "synthetic-xsrf" not in str(error.value)


@pytest.mark.parametrize("status_code", [204, 404])
def test_delete_file_removes_url_and_preserves_other_bytes(tmp_path, status_code):
    path = tmp_path / "article.md"
    original = (
        "\ufeff---\r\n"
        "# Keep this comment\r\n"
        "title: 'Original title'\r\n"
        f"'url': '{ARTICLE_URL}' # article URL\r\n"
        "# Keep the following metadata\r\n"
        "tags:\r\n  - Python\r\n  - Markdown\r\n"
        "custom:\r\n  nested: true\r\n"
        "---\r\n\r\n# A very short article\r\n\r\nBody.\r\n"
    )
    path.write_bytes(original.encode("utf-8"))
    client = ZhihuClient(COOKIE, transport=httpx.MockTransport(lambda request: httpx.Response(status_code)))
    try:
        result = Deleter(client).delete_file(path)
    finally:
        client.close()

    expected = original.replace(f"'url': '{ARTICLE_URL}' # article URL\r\n", "")
    assert result.status == ("already-deleted" if status_code == 404 else "deleted")
    assert path.read_bytes() == expected.encode("utf-8")
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize(
    "metadata",
    ["", "title: Untouched\n", "url: null\n", "url: ''\n", "url: https://www.zhihu.com/answer/123\n", "url: https://www.zhihu.com/question/123\n"],
)
def test_delete_file_skips_missing_urls_questions_and_answers(tmp_path, metadata):
    path = tmp_path / "article.md"
    original = f"---\n{metadata}---\n# Untouched\n".encode("utf-8")
    path.write_bytes(original)
    result = Deleter(None).delete_file(path)
    assert result.status == "skipped"
    assert path.read_bytes() == original


def test_delete_file_dry_run_is_local_and_preserves_source(tmp_path):
    path = tmp_path / "article.md"
    original = f"---\nurl: {ARTICLE_URL}\n---\nBody\n".encode("utf-8")
    path.write_bytes(original)
    assert Deleter(None).delete_file(path, dry_run=True) == DeleteResult("would-delete", ARTICLE_URL)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_delete_file_remote_failure_keeps_url(tmp_path):
    path = tmp_path / "article.md"
    original = f"---\nurl: {ARTICLE_URL}\n---\nBody\n".encode("utf-8")
    path.write_bytes(original)
    client = ZhihuClient(COOKIE, transport=httpx.MockTransport(lambda request: httpx.Response(403)))
    try:
        with pytest.raises(DeleteError):
            Deleter(client).delete_file(path)
    finally:
        client.close()
    assert path.read_bytes() == original


def test_delete_file_write_failure_reports_partial_success_and_preserves_source(monkeypatch, tmp_path):
    path = tmp_path / "article.md"
    original = f"---\nurl: {ARTICLE_URL}\n---\nBody\n".encode("utf-8")
    path.write_bytes(original)

    def fail_replace(*args):
        raise PermissionError(f"synthetic filesystem error {COOKIE}")

    monkeypatch.setattr("zhihupost.deleter.os.replace", fail_replace)
    client = ZhihuClient(COOKIE, transport=httpx.MockTransport(lambda request: httpx.Response(204)))
    try:
        with pytest.raises(PartialDeleteError) as error:
            Deleter(client).delete_file(path)
    finally:
        client.close()
    assert "123" in str(error.value)
    assert "synthetic-secret" not in str(error.value)
    assert path.read_bytes() == original
    assert list(tmp_path.iterdir()) == [path]


def test_delete_file_does_not_overwrite_edits_made_during_request(tmp_path):
    path = tmp_path / "article.md"
    original = f"---\nurl: {ARTICLE_URL}\n---\nBody\n"
    edited = original + "Concurrent edit\n"
    path.write_bytes(original.encode("utf-8"))

    def handler(request):
        path.write_bytes(edited.encode("utf-8"))
        return httpx.Response(204)

    client = ZhihuClient(COOKIE, transport=httpx.MockTransport(handler))
    try:
        with pytest.raises(PartialDeleteError):
            Deleter(client).delete_file(path)
    finally:
        client.close()
    assert path.read_bytes() == edited.encode("utf-8")
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize(
    "metadata",
    [
        f"{{url: '{ARTICLE_URL}', title: Test}}\n",
        f"url: &article {ARTICLE_URL}\ncanonical: *article\n",
        f"defaults: &defaults\n  url: {ARTICLE_URL}\n<<: *defaults\n",
    ],
)
def test_delete_file_refuses_unsafe_yaml_cleanup_before_request(tmp_path, metadata):
    path = tmp_path / "article.md"
    original = f"---\n{metadata}---\nBody\n".encode("utf-8")
    path.write_bytes(original)
    requests = []
    client = ZhihuClient(
        COOKIE,
        transport=httpx.MockTransport(lambda request: requests.append(request) or httpx.Response(204)),
    )
    try:
        with pytest.raises(ValueError, match="Cannot remove front matter"):
            Deleter(client).delete_file(path)
    finally:
        client.close()
    assert requests == []
    assert path.read_bytes() == original


@pytest.mark.parametrize(
    "metadata",
    [
        f"url: {ARTICLE_URL}\ntitle: Preserved\n",
        f"title: Preserved\nurl: >-\n  {ARTICLE_URL}\n",
        f"title: Preserved\nurl:\n  '{ARTICLE_URL}'\n",
        f"url: {ARTICLE_URL}\nurl: {ARTICLE_URL}\ntitle: Preserved\n",
        f"canonical: &article {ARTICLE_URL}\nurl: *article\ntitle: Preserved\n",
    ],
)
def test_remove_front_matter_handles_multiline_duplicates_and_alias_values(metadata):
    source = f"---\n{metadata}---\nBody\n"
    result = remove_front_matter_value(source, "url")
    before = parse_document(source)
    after = parse_document(result)
    assert after.body == before.body
    assert after.metadata == {key: value for key, value in before.metadata.items() if key != "url"}


@pytest.mark.parametrize("source", ["Body\n", "---\n---\nBody\n", "---\ntitle: Preserved\n---\nBody\n"])
def test_remove_missing_field_leaves_input_unchanged(source):
    assert remove_front_matter_value(source, "url") == source


def test_delete_file_preserves_symbolic_link_and_updates_real_source(tmp_path):
    source = tmp_path / "source.md"
    link = tmp_path / "linked.md"
    original = f"---\nurl: {ARTICLE_URL}\n---\nBody\n"
    source.write_bytes(original.encode("utf-8"))
    try:
        link.symlink_to(source)
    except OSError:
        pytest.skip("Symbolic links are unavailable in this environment")
    client = ZhihuClient(COOKIE, transport=httpx.MockTransport(lambda request: httpx.Response(204)))
    try:
        assert Deleter(client).delete_file(link).status == "deleted"
    finally:
        client.close()
    assert link.is_symlink()
    assert source.read_text(encoding="utf-8") == "---\n---\nBody\n"
    assert link.read_bytes() == source.read_bytes()
