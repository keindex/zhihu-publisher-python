# 知乎发布助手

## What it does

[zhihu-publisher](../../skills/productivity/zhihu-publisher/SKILL.md) 让代理使用本地 `zhihupost` CLI 操作知乎内容，包括 Markdown 预览、文章和回答发布与更新、草稿保存、图片上传，以及专栏文章删除。它复用项目的登录和文件写回逻辑。

在本地安装 skill 后，可以用 `$zhihu-publisher` 显式调用；代理也可以在任务匹配时自动选用。真实写操作的授权来自用户当前请求，加载技能本身不会触发发布或删除。

## When to reach for it

- 检查 Markdown 发布到知乎后的呈现效果。
- 把指定 Markdown 发布为文章、回答或草稿，或者更新它已有的知乎 URL。
- 按目录批量发布，或预览并删除指定文章。
- 上传指定图片，获取可供知乎正文使用的图片 URL。

例如：`用 $zhihu-publisher 预览 articles 目录中的 Markdown，不实际发布。`

仅撰写文章正文、修改 Python 代码或处理其他平台内容时，不需要这个 skill。

## Common questions

### 草稿是不是离线预览？

不是。`--draft` 会写入远端并可能上传图片。`render` 和 `publish --dry-run` 才是离线预览，不需要 Cookie；预览结果为 `skipped` 是正常现象。

### 怎样批量预览发布？

`publish-dir` 没有 `--dry-run`，skill 会递归枚举 Markdown，按路径排序并逐个运行 `publish --dry-run`。目录删除则直接支持 `delete-dir --dry-run`。

### 工具怎样判断是新建还是更新？

由 front matter 的 `url` 决定。省略表示新建文章；文章 URL 用于更新文章，问题 URL 用于创建回答，回答 URL 用于更新回答。成功创建文章或文章草稿后，会把 URL 写回源文件。

### 更新文章时哪些元数据需要特别注意？

`tags` 是目标话题全集，省略时也会清除原有话题。`column` 是专栏标题，找不到会新建专栏。相对图片路径以 Markdown 文件所在目录为准，不支持 SVG。

### 删除会删掉本地 Markdown 吗？

不会。按 Markdown 删除成功或返回 HTTP 404 后，工具只移除 front matter 的 `url`，保留正文和其他元数据。按 ID 或链接删除不会自动修改本地 Markdown。问题、回答以及不能保真清理的 YAML 结构不会被强行删除。

### 发布或删除失败后能否直接重试？

先区分失败和部分成功。发布可能已创建远端文章，但写回 URL 失败，盲目重试会重复创建。删除部分成功通常表示远端已不存在，但本地写回失败，应先检查权限和文件修改。

### Cookie 放在哪里？

使用项目保存的登录信息或用户在本地提供的 `ZHIHU_COOKIE`。skill 不保存凭据；登录使用 `zhihupost login` 的隐藏输入，不将 Cookie 放入对话、技能文件或 Git 提交。

## It's working if

- 预览只执行离线命令，源文件与远端状态均保持不变。
- 实际操作使用用户指定的账号、源文件和目标，正确区分发布、更新、草稿与删除。
- 代理理解 `url`、`tags` 和 `column` 的影响，并报告命令结果或批处理汇总。
- 部分成功被明确报告，没有因此重复创建文章或覆盖本地并发编辑。
