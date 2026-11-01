from pathlib import Path

import pytest

from zhihupost.batch import BatchSummary, delete_directory
from zhihupost.deleter import DeleteResult


class StubDeleter:
    def __init__(self):
        self.calls = []

    def delete_file(self, path, *, dry_run=False):
        self.calls.append((Path(path), dry_run))
        if path.name == "b.MD":
            raise RuntimeError("mocked failure")
        if path.name == "skip.md":
            return DeleteResult("skipped", None)
        return DeleteResult("would-delete" if dry_run else "deleted", "https://zhuanlan.zhihu.com/p/1")


def test_delete_directory_sorts_recurses_waits_and_continues(tmp_path):
    (tmp_path / "nested").mkdir()
    for relative in ("nested/a.md", "b.MD", "skip.md", "ignore.txt"):
        (tmp_path / relative).write_text("Body", encoding="utf-8")
    sleeps = []
    results = []
    deleter = StubDeleter()
    summary = delete_directory(
        tmp_path, deleter, delay=2, sleep=sleeps.append,
        on_result=lambda path, result: results.append((path.name, result.status)),
    )
    assert [path.relative_to(tmp_path).as_posix() for path, _ in deleter.calls] == [
        "b.MD", "nested/a.md", "skip.md"
    ]
    assert all(not dry_run for _, dry_run in deleter.calls)
    assert sleeps == [2, 2]
    assert results == [("a.md", "deleted"), ("skip.md", "skipped")]
    assert summary == BatchSummary(1, 1, 1, [(tmp_path / "b.MD", "mocked failure")])


def test_delete_directory_dry_run_does_not_sleep(tmp_path):
    for name in ("a.md", "c.md"):
        (tmp_path / name).write_text("Body", encoding="utf-8")
    deleter = StubDeleter()
    summary = delete_directory(
        tmp_path, deleter, dry_run=True,
        sleep=lambda _: pytest.fail("preview must not wait between files"),
    )
    assert summary == BatchSummary(2, 0, 0, [])
    assert all(dry_run for _, dry_run in deleter.calls)


@pytest.mark.parametrize("delay", [-1, float("nan"), float("inf"), -float("inf")])
def test_delete_directory_validates_delay_before_deleting(tmp_path, delay):
    deleter = StubDeleter()
    with pytest.raises(ValueError, match="delay"):
        delete_directory(tmp_path, deleter, delay=delay)
    assert deleter.calls == []


def test_delete_directory_empty_and_single_file_do_not_wait(tmp_path):
    deleter = StubDeleter()
    sleeps = []
    assert delete_directory(tmp_path, deleter, sleep=sleeps.append) == BatchSummary(0, 0, 0, [])
    (tmp_path / "a.md").write_text("Body", encoding="utf-8")
    assert delete_directory(tmp_path, deleter, sleep=sleeps.append).succeeded == 1
    assert sleeps == []


def test_delete_directory_requires_existing_directory(tmp_path):
    deleter = StubDeleter()
    with pytest.raises(ValueError, match="directory"):
        delete_directory(tmp_path / "missing", deleter)
    assert deleter.calls == []


def test_delete_directory_callback_failure_counts_file_once(tmp_path):
    (tmp_path / "a.md").write_text("Body", encoding="utf-8")

    def fail_callback(path, result):
        raise RuntimeError("output failed")

    summary = delete_directory(tmp_path, StubDeleter(), on_result=fail_callback)
    assert summary == BatchSummary(0, 0, 1, [(tmp_path / "a.md", "output failed")])
