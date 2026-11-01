---
name: zhihu-publisher
description: "使用本地 zhihupost 命令预览、发布和更新 Markdown 到知乎，管理草稿、图片及专栏文章删除。用户要求执行知乎内容操作时使用；仅撰写文章或开发 Python 功能时不使用。"
---

# 知乎发布与文章管理

通过本项目的 `zhihupost` CLI 执行操作，复用其认证、目标校验和本地文件写回逻辑，不另写调用知乎接口的脚本。

## 操作范围

- 用户要求准备、检查或预览时，只执行离线命令。
- 用户已明确要求发布、保存草稿、上传图片或删除时，在指定内容、账号和目标范围内执行。已有授权不重复确认；skill 被加载本身不构成执行远端写操作的授权。
- `--draft` 会上传图片并写入远端草稿，也可能同步话题。需要离线预览时用 `--dry-run`。
- 创建或安装这个 skill 时，只验证命令和离线预览，不发布或删除真实内容。

## 环境与账号

检查 `zhihupost --help`。命令不可用时，可尝试 `python -m zhihupost.cli --help`；没有 `python -m zhihupost` 入口。需要安装时，从用户指定或已核实的项目根目录运行 `python -m pip install .`，不要猜测机器上的仓库位置。

真实操作使用已保存的 Cookie 或 `ZHIHU_COOKIE`。需要核对账号时执行 `zhihupost whoami`；离线预览无需登录，也不调用 `whoami`。

登录用 `zhihupost login` 的隐藏输入。凭据由用户在本地提供；不读取或输出 Cookie 文件内容，不把 Cookie 放进 skill、命令参数、日志或提交。`login --stdin` 只用于已有的安全标准输入来源。认证失败时停止真实操作并报告需要重新登录。

## 预览与发布

```powershell
zhihupost render ".\article.md"
zhihupost publish ".\article.md" --dry-run
zhihupost publish ".\article.md" --draft
zhihupost publish ".\article.md"
```

`render` 和 `publish --dry-run` 不请求知乎或 OSS，不上传图片，也不改源文件。发布预览输出 `skipped` 是正常结果；它不验证账号、远端话题、专栏或图片上传是否可用。

真实发布前读取 Markdown front matter，按 `url` 选择目标：

- 没有 `url`：创建专栏文章。
- `https://zhuanlan.zhihu.com/p/<id>`：更新已有文章。
- `https://www.zhihu.com/question/<id>`：创建回答。
- `https://www.zhihu.com/question/<id>/answer/<id>` 或 `https://www.zhihu.com/answer/<id>`：更新回答。

保留更新目标的 `url`，不要通过清空它来绕过错误，否则会创建新文章。成功创建文章或文章草稿后，CLI 会把 URL 写回 Markdown。

检查这些会影响远端内容的元数据：

- `title` 缺省时从正文首个非空行推导，通常应写明确标题。
- `tags` 可以是逗号分隔字符串或 YAML 字符串列表。它是文章话题的目标全集，省略也会同步为空集并移除原有话题。更新前核对用户希望保留的话题。
- `column` 按专栏标题匹配，找不到时会新建专栏。
- `title-image` 和正文中的相对图片路径相对于 Markdown 所在目录解析；不支持 SVG。

目录发布命令递归处理扩展名不区分大小写的 `.md` 文件，按路径排序，默认文件间隔 60 秒：

```powershell
zhihupost publish-dir ".\articles" --delay 60
zhihupost publish-dir ".\articles" --draft --delay 60
zhihupost upload-image ".\images\cover.png"
```

`publish-dir` 没有 `--dry-run`。需要批量预览时，递归枚举目标目录中的 `.md` 文件，排序后逐个运行 `publish <file> --dry-run`。不要为了预览改用真实目录发布。

## 删除文章

先用对应的 `--dry-run` 检查目标；已有明确删除授权且目标核对一致时，继续执行实际删除。

```powershell
zhihupost delete ".\article.md" --dry-run
zhihupost delete-dir ".\articles" --dry-run
zhihupost delete ".\article.md"
zhihupost delete 123
zhihupost delete https://zhuanlan.zhihu.com/p/123
zhihupost delete-dir ".\articles" --delay 1.5
```

将示例路径和 ID 替换为用户指定的实际目标。删除仅支持专栏文章，不支持问题或回答。

- Markdown 输入从 front matter 的 `url` 取目标；没有 URL 或指向问题、回答时跳过。
- 删除成功或 HTTP 404 时，CLI 移除该 Markdown 的 `url`，保留文件、正文、其他元数据和换行格式。短文章也保留本地文件。
- 按 ID 或 URL 删除时，不会自动查找和修改对应的本地 Markdown。
- `delete-dir` 递归排序，默认间隔 1.5 秒；`--dry-run` 不请求网络、不等待间隔、不修改文件。
- flow mapping、共享 anchor 或 merge 等 YAML 结构无法保真清理时，会在删除前拒绝。保留原文件并报告原因，不绕过校验强行删除。

## 失败与结果

目录发布和删除遇到单个文件失败会继续，存在失败时退出码为 1。汇报成功、跳过、失败数量及失败文件，不把预览计为已发布或已删除。

发布报部分成功时，远端内容可能已经创建或更新。先核对错误中的 ID、本地 `url` 和远端状态，不对缺少 URL 的源文件盲目重试，以免重复创建。

删除报部分成功时，远端文章已不存在，但本地 URL 写回失败。检查文件权限及请求期间的修改，保留并发编辑；确认文件仍对应原目标后再处理本地 URL。HTTP 403、429 或网络错误不代表删除成功，不自动循环重试。
