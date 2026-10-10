# zhihu-publisher

`zhihu-publisher` is a Python CLI for rendering Zhihu-compatible Markdown and publishing Zhihu articles, answers, and drafts. The command and Python module are named `zhihupost`.

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

Upload an image separately:

```powershell
zhihupost upload-image .\images\cover.png
```

## Front Matter and Markdown

Supported front matter fields are `title`, `url`, `column`, `title-image`, and `tags`. A missing title is derived from the first body heading. Tags may be a comma-separated string or a YAML string list.

Markdown support includes CommonMark basics, headings, quotes, lists and task lists, tables, code blocks, links and images, math, footnotes, Emoji shortcodes, and `zhihu-link-card:` link cards. Relative images resolve from the Markdown file's directory. SVG images are not supported.

## Development

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
python -m build
```

Tests mock all Zhihu HTTP and OSS requests; they do not publish live content. Licensed under MIT; see [LICENSE](LICENSE).
