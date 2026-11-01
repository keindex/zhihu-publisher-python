# zhihu-publisher

`zhihu-publisher` is a Python CLI for rendering Zhihu-compatible Markdown, publishing Zhihu articles, answers, and drafts, and deleting Zhihu column articles. The command and Python module are named `zhihupost`.

## Install

Requires Python 3.10 or later:

```powershell
python -m pip install -e .
zhihupost --help
```

## Authentication

Run `zhihupost login` and paste the full Cookie header at the hidden prompt. The CLI validates it with the read-only current-user endpoint before saving it to the user configuration directory.

```powershell
zhihupost login
zhihupost whoami
zhihupost logout
```

`ZHIHU_COOKIE` overrides the saved Cookie for temporary sessions and CI. Never commit credentials or include them in logs or shell history.

## Commands

`render` and `publish --dry-run` are local-only operations. They make no Zhihu or OSS requests and require no Cookie:

```powershell
zhihupost render .\article.md > .\article.html
zhihupost publish .\article.md --dry-run
```

Publish or save a draft:

```powershell
zhihupost publish .\article.md
zhihupost publish .\article.md --draft
```

After publishing a new article, the CLI writes its URL back to the Markdown front matter. Existing articles, questions, and answers can be selected with `url`.

Publish a directory recursively. Files are processed in sorted order with a default 60-second delay between files:

```powershell
zhihupost publish-dir .\articles --delay 60
zhihupost publish-dir .\articles --draft --delay 10
```

Delete a column article by ID, article URL, or Markdown file path, using the saved Cookie or `ZHIHU_COOKIE`:

```powershell
zhihupost delete 123
zhihupost delete https://zhuanlan.zhihu.com/p/123
zhihupost delete .\article.md
```

For Markdown files, the target comes from the front matter `url`. After successful deletion, or HTTP 404 indicating the article is already absent, the CLI removes `url` and preserves the local file, body, and other metadata. Files without a `url`, or with a question or answer URL, are skipped. A URL supplied directly must point to a column article.

Delete articles referenced by Markdown files in a directory recursively. The `.md` extension is case-insensitive, files are processed in sorted order, and the default delay is 1.5 seconds. Set a non-negative `--delay` to change it. Processing continues after individual failures and prints a summary; any failure results in exit code 1:

```powershell
zhihupost delete-dir .\articles --delay 1.5
```

Preview targets with `--dry-run`. Previewing requires no Cookie, makes no network requests, and does not delete remote articles or modify local files:

```powershell
zhihupost delete .\article.md --dry-run
zhihupost delete-dir .\articles --dry-run
```

Upload an image separately:

```powershell
zhihupost upload-image .\images\cover.png
```

## Front Matter and Markdown

Supported front matter fields are `title`, `url`, `column`, `title-image`, and `tags`. A missing title is derived from the first body heading. Tags may be a comma-separated string or a YAML string list.

Markdown support includes CommonMark basics, headings, quotes, lists and task lists, tables, code blocks, links and images, math, footnotes, Emoji shortcodes, and `zhihu-link-card:` link cards. Relative images resolve from the Markdown file's directory. SVG images are not supported.

## Agent Skill

### User-invoked

There are no skills restricted to explicit invocation.

### Model-invoked

- [zhihu-publisher](./skills/productivity/zhihu-publisher/SKILL.md): Use `zhihupost` to preview, publish, and update Zhihu content, manage drafts and images, and delete column articles. Invoke it with `$zhihu-publisher` or let the agent select it for a matching task.

See the [skill guide](./docs/productivity/zhihu-publisher.md) for workflows and common questions.

After installing the Python CLI, run the local linking script from the repository root. These commands are copied from [.agents/install-block.md](./.agents/install-block.md).

Windows PowerShell:

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\link-skills.ps1
```

macOS or Linux:

```bash
bash scripts/link-skills.sh
```

The scripts link the skill into both `~/.codex/skills` (or `$CODEX_HOME/skills`) and `~/.agents/skills`. Re-running preserves matching links and refuses conflicting installations. Links follow repository updates; the skill can load on your next turn.

## Development

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
python -m build
```

Tests mock all Zhihu HTTP and OSS requests; they do not publish or delete live content. Licensed under MIT; see [LICENSE](LICENSE).
