# zhihu-publisher

`zhihu-publisher` 是一个 Python 命令行工具，可在本地渲染适配知乎的 Markdown，发布或保存知乎文章、回答和草稿，以及删除知乎专栏文章。命令名和 Python 模块名为 `zhihupost`。

## 安装

需要 Python 3.10 或更高版本：

```powershell
python -m pip install -e .
zhihupost --help
```

## 登录

运行登录命令后，在隐藏输入提示中粘贴完整 Cookie。程序只使用只读的当前用户接口验证，验证成功后才将 Cookie 保存到当前用户配置目录：

```powershell
zhihupost login
zhihupost whoami
zhihupost logout
```

也可以使用环境变量 `ZHIHU_COOKIE`；它会覆盖保存的 Cookie，适合临时会话或 CI。请勿把 Cookie 提交到仓库、命令历史或日志中。

```powershell
$env:ZHIHU_COOKIE = Get-Content -Raw .\cookie.txt
zhihupost whoami
Remove-Item Env:ZHIHU_COOKIE
```

## 命令

本地渲染和 dry-run 不访问知乎或 OSS，也不需要 Cookie：

```powershell
zhihupost render .\article.md > .\article.html
zhihupost publish .\article.md --dry-run
```

发布、更新或保存为草稿：

```powershell
zhihupost publish .\article.md
zhihupost publish .\article.md --draft
```

成功发布新文章后，CLI 会把文章 URL 写回 Markdown front matter。现有知乎文章、问题和回答可通过 `url` 字段指定更新目标。

递归处理目录中的 Markdown 文件，默认在相邻文件之间等待 60 秒：

```powershell
zhihupost publish-dir .\articles --delay 60
zhihupost publish-dir .\articles --draft --delay 10
```

删除专栏文章，支持文章 ID、文章链接或 Markdown 文件路径，复用已保存的 Cookie 或 `ZHIHU_COOKIE`：

```powershell
zhihupost delete 123
zhihupost delete https://zhuanlan.zhihu.com/p/123
zhihupost delete .\article.md
```

Markdown 文件从 front matter 的 `url` 读取目标。远端删除成功或接口返回 HTTP 404（文章已不存在）后，程序移除 `url` 字段，保留本地文件、正文和其他元数据。没有 `url` 的文件，以及 `url` 指向问题或回答的文件会跳过；直接输入链接时只接受专栏文章链接。

递归删除目录中 `.md` 文件对应的专栏文章（扩展名不区分大小写），按文件路径排序，默认间隔 1.5 秒，可用非负的 `--delay` 调整。单个文件失败后继续处理，其余文件的结果会汇总；存在失败时退出码为 1：

```powershell
zhihupost delete-dir .\articles --delay 1.5
```

执行前可用 `--dry-run` 查看目标。预览不需要 Cookie，不访问网络，也不删除远端文章或修改本地文件：

```powershell
zhihupost delete .\article.md --dry-run
zhihupost delete-dir .\articles --dry-run
```

单独上传图片：

```powershell
zhihupost upload-image .\images\cover.png
```

## Front Matter

支持 `title`、`url`、`column`、`title-image` 和 `tags`。标题缺省时从正文第一个标题推导。标签可以使用逗号分隔字符串或 YAML 字符串列表：

```yaml
---
title: 示例文章
url: https://zhuanlan.zhihu.com/p/123
column: 示例专栏
title-image: ./images/cover.png
tags: Python, Markdown
# 或者：
# tags:
#   - Python
#   - Markdown
---
```

`url` 支持知乎专栏文章、问题和回答链接。发布新文章时可省略 `url`；回答问题时使用问题或回答链接。

## Markdown 支持

支持 CommonMark 常用语法、标题、引用、列表和任务列表、表格、代码块、链接和图片、数学公式、脚注、Emoji shortcode，以及 `zhihu-link-card:` 链接卡片。相对图片路径相对于 Markdown 文件所在目录解析；SVG 图片不支持。

## Agent Skill

### User-invoked

目前没有仅限用户显式调用的技能。

### Model-invoked

- [zhihu-publisher](./skills/productivity/zhihu-publisher/SKILL.md)：通过 `zhihupost` 预览、发布和更新知乎内容，管理草稿、图片及专栏文章删除。可显式使用 `$zhihu-publisher`，也支持按任务自动选用。

使用说明见 [知乎发布助手](./docs/productivity/zhihu-publisher.md)。

安装 Python CLI 后，从仓库根目录运行本地链接脚本。以下命令与 [.agents/install-block.md](./.agents/install-block.md) 保持一致。

Windows PowerShell：

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\scripts\link-skills.ps1
```

macOS 或 Linux：

```bash
bash scripts/link-skills.sh
```

脚本把技能链接到 `~/.codex/skills`（或 `$CODEX_HOME/skills`）和 `~/.agents/skills`，重复运行会保留现有链接，不覆盖冲突安装。技能随仓库更新，下轮对话即可加载。

## 开发与测试

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
python -m build
```

自动化测试会 mock 知乎 HTTP 和 OSS 请求，不会发布或删除真实内容。

## 许可证

MIT，详见 [LICENSE](LICENSE)。
