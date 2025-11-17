# blog2md

`blog2md` 是一个将博客文章提取为纯正文 HTML 并转换为 Markdown 初稿的命令行工具，默认针对 CSDN、Hexo 等常见博客结构做了优化，也兼容大多数标准博客页面。你可以直接在命令行输入文章 URL，即可获得已经清洗干净的正文 HTML 和 Markdown，方便后续整理或发布到其他平台。

## 功能特性

- 自动抓取指定 URL，对网络错误进行友好提示。
- 针对 CSDN 与常见 Hexo 主题优先采用精确选择器。
- 通用启发式提取正文，过滤导航、侧栏、推荐、评论等噪声区域。
- 将正文保存为 `<slug>.html`，并基于 Markdownify 输出 Markdown 草稿。
- 自动生成 slug，若提取失败则提供时间戳兜底命名。

## 安装

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 使用

```bash
python blog2md.py "https://example.com/blog-post"
```

常用参数：

- `--html-out`: 指定正文 HTML 保存路径，默认输出到 `example/<slug>/<slug>.html`
- `--md-out`: 指定 Markdown 输出路径，默认输出到 `example/<slug>/<slug>.md`
- `--timeout`: 请求超时时间，默认 15 秒
- `--user-agent`: 自定义 UA，默认模拟桌面浏览器

运行成功后终端会输出：

- 使用的正文提取策略（命中特定选择器或通用启发式）。
- 提取的字符数，帮助判断是否抓到完整正文。
- HTML/Markdown 文件的保存路径。

## 示例

1. 抓取 CSDN 博客：

   ```bash
   python blog2md.py "https://blog.csdn.net/xxx/article/details/123456" --timeout 20
   ```

2. 抓取 Hexo 搭建的个人博客：

   ```bash
   python blog2md.py "https://yourname.github.io/2024/awesome-post/" --md-out notes/awesome.md
   ```

命令完成后会在终端展示提取方式、字数统计及输出文件路径。若未自定义路径，所有结果会收纳在 `example/<slug>/` 子目录，Markdown 同目录下若包含图片会自动创建 `assets/` 并把图片保存其中，同时将 HTML 与 Markdown 中的图片链接指向对应的本地文件。
