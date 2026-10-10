# zhihu-publisher

`zhihu-publisher` 是一个 Python 命令行工具，可在本地渲染适配知乎的 Markdown，并发布或保存知乎文章、回答和草稿。命令名和 Python 模块名为 `zhihupost`。

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

## 开发与测试

```powershell
python -m pip install -e ".[test]"
python -m pytest -q
python -m build
```

自动化测试会 mock 知乎 HTTP 和 OSS 请求，不会发布真实内容。

## 许可证

MIT，详见 [LICENSE](LICENSE)。
