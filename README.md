# 🛰️ TechPulse Daily - 每日技术热点聚合与订阅服务

> 自动每日抓取 **GitHub Daily Trending** 热门开源项目与 **Hacker News** 极客深度科技讨论，提炼高信息密度的精华内容，生成标准的 **RSS 2.0 订阅源**、**静态 Web 早报**，并支持直推到**飞书、Telegram、企业微信、钉钉、邮件与手机**。

---

## 💡 为什么需要这个服务？

每天的技术资讯非常庞杂，如何在几分钟内掌握全球技术风向？
- **GitHub Daily Trending** 反映了全球开发者正在狂热探索的代码库、开源工具和 AI 新突破。
- **Hacker News** 汇聚了全球顶尖极客对前沿突破、开源趋势、行业变革的高质量一手观点与深度讨论。

**TechPulse** 为此而生：它不仅抓取原始列表，还会进行**去重、质量打分、主题分类（AI/架构/工具/安全等）**，并打包为多端交付格式，让你可以在 RSS 阅读器、手机聊天软件、或网页端随时随地阅读。

---

## ✨ 核心特性

- 🔍 **多源智能聚合**：
  - **GitHub Trending**：按今日 Star 增速（Stars Today）排序，抓取项目定位、主要语言、总星标、Forks 与作者。
  - **Hacker News**：抓取近 24 小时高分（Points）与高讨论度（Comments）热门议题，并保留原文与 HN 评论区双链接。
- 📡 **标准 RSS 2.0 / Atom 订阅**：
  - 生成标准的 `outputs/feed.xml` 与 `outputs/rss.xml`。
  - 每个 Item 内置精心排版的 HTML 卡片与主题标签，排版适配暗色与浅色阅读器。
- 🌐 **精美 Web 阅读界面**：
  - 自动生成自包含、轻量现代的 `outputs/index.html`，支持一键复制 RSS 订阅源，带往期历史归档。
- 📲 **开箱即用的多推送渠道**：
  - **飞书 (Feishu / Lark)**：精美的富文本卡片排版，带不同颜色标签。
  - **Telegram Bot**：HTML 富文本消息直达群组或个人聊天。
  - **企业微信 / 钉钉**：群机器人 Markdown 消息推送。
  - **邮件 (SMTP)**：每日早报 HTML 邮件，适配手机与桌面端。
  - **Bark**：iOS 手机系统级即时弹窗推送。
- 🧠 **可选 AI 智能风向提炼**：
  - 支持 OpenAI / DeepSeek / Ollama 等兼容接口。
  - 提供 2-3 句话的“今日技术风向速览”与核心看点解读；未配置 API Key 时完全自动降级为规则排版，无需担心中断。
- ⏰ **全自动化无人值守**：
  - 提供 **GitHub Actions**（云端 0 成本，每日定时更新并托管至 GitHub Pages）。
  - 提供 **Windows 任务计划程序**（本地后台开机静默定时执行）。
  - 提供 **Docker / Compose**（适合 NAS 或 VPS 部署）。

---

## 📂 项目结构

```text
.
├── config.yaml                    # 配置文件（数据源阈值、推送凭证、RSS 设置等）
├── config.example.yaml            # 配置文件范例
├── requirements.txt               # 运行依赖
├── main.py                        # 主程序入口（支持多种运行与服务模式）
├── core/
│   ├── config.py                  # 配置加载器与默认值
│   ├── fetcher_github.py          # GitHub Trending 抓取与质量解析器
│   ├── fetcher_hackernews.py      # Hacker News 抓取与深度讨论过滤器
│   ├── data_processor.py          # 信息去重、打分、分类与 AI 提炼
│   ├── rss_generator.py           # RSS 2.0 XML、HTML 与历史归档生成器
│   └── notifiers.py               # 飞书、Telegram、企微、钉钉、邮件等推送器
├── scripts/
│   ├── setup_task_windows.ps1     # Windows 任务计划程序一键注册脚本 (pwsh)
│   ├── run_digest.ps1             # Windows 手动运行包装脚本
│   └── test_all.ps1               # 自动化集成测试脚本
├── .github/
│   └── workflows/
│       └── daily_digest.yml       # GitHub Actions 每日全自动运行工作流
├── Dockerfile                     # Docker 镜像构建文件
├── docker-compose.yml             # Docker Compose 一键启动配置
└── outputs/                       # 最终交付与生成成果
    ├── feed.xml                   # RSS 2.0 订阅源文件
    ├── rss.xml                    # RSS 2.0 别名文件
    ├── index.html                 # 响应式 Web 日报静态页面
    ├── latest_digest.md           # 最新一期 Markdown 格式日报
    └── archive/                   # 历史归档目录（含 json 与 md）
```

---

## 🚀 快速开始

### 1. 运行环境
推荐使用 Python 3.10+。项目核心模块采用标准库构建，基本零强制外部依赖：
```bash
pip install -r requirements.txt
```

### 2. 常用运行命令

- **演练测试（抓取并生成文件，不发外部通知）**：
  ```bash
  python main.py --dry-run
  ```

- **正式执行（抓取、生成产物、并分发到配置的通知渠道）**：
  ```bash
  python main.py --run
  ```

- **启动本地 RSS & Web 订阅服务**：
  ```bash
  python main.py --serve --port 8080
  ```
  > 启动后可直接在浏览器访问：
  > - 网页版：`http://127.0.0.1:8080/index.html`
  > - RSS 源：`http://127.0.0.1:8080/feed.xml`

- **测试推送通知配置**：
  ```bash
  python main.py --test-notify
  ```

---

## ⏰ 自动化部署方案（如何做到每日自动发给我？）

### 方案一：GitHub Actions + GitHub Pages（⭐ 最推荐，永久 0 成本、免本地开机）

无需购买任何云服务器，借助 GitHub 免费的 CI/CD 与 Pages 即可全天候无人值守：

1. **新建 GitHub 仓库**并将本项目代码推送到你自己的 GitHub 仓库中。
2. **启用 GitHub Pages**：
   - 进入仓库 -> **Settings** -> **Pages**。
   - Source 选择 **Deploy from a branch**，分支选择 `gh-pages`，路径选 `/(root)`。
3. **（可选）配置推送 Secrets**：
   - 进入仓库 -> **Settings** -> **Secrets and variables** -> **Actions**。
   - 可添加环境变量密钥：
     - `FEISHU_WEBHOOK`：飞书机器人 Webhook 地址
     - `TELEGRAM_BOT_TOKEN` & `TELEGRAM_CHAT_ID`：TG 机器人凭据
     - `WECOM_WEBHOOK`：企业微信机器人 Webhook
     - `OPENAI_API_KEY`：用于开启 AI 总结
4. **效果**：
   - 每天北京时间早上 08:30，GitHub Actions 会自动运行抓取。
   - 你的全局 RSS 订阅地址为：`https://<你的GitHub用户名>.github.io/<仓库名>/feed.xml`。
   - 将该地址添加到你的 NetNewsWire、Follow、Reeder、Feedly 等阅读器中，每日即可自动刷新！

---

### 方案二：Windows 任务计划程序（本地静默运行）

如果你习惯在本地 Windows 电脑上运行，可直接通过本项目提供的 PowerShell 7 脚本一键注册 Windows 任务：

```powershell
# 注册每天早上 08:30 自动静默运行任务
pwsh scripts/setup_task_windows.ps1 -Time "08:30"

# 立即触发一次测试
pwsh scripts/setup_task_windows.ps1 -RunNow

# 如需卸载
pwsh scripts/setup_task_windows.ps1 -Uninstall
```

---

### 方案三：Docker / NAS / 服务器守护进程

如果你有 Linux 服务器、云主机或群晖/QNAP NAS，可以使用 Docker：

```bash
docker compose up -d
```
服务将在后台常驻，每天定时自动聚合，并通过 `http://<NAS_IP>:8080/feed.xml` 提供局域网/公网 RSS 订阅。

---

## ⚙️ 配置说明 (config.yaml)

详见 `config.yaml` 文件内部的完整注释。支持配置项包括：
- `github.max_items`：每次抓取开源项目数量上限（默认 12）。
- `github.min_stars_today`：过滤单日 Star 增速过低的项目（默认 30）。
- `github.languages`：可过滤特定语言（如 `["python", "rust", "go"]`），留空为全语言。
- `hackernews.min_points`：HN 最低点赞门槛（默认 80 points），过滤无意义讨论。
- `ai_summary.enabled`：是否启用 AI 摘要分析（支持任何兼容 OpenAI 协议的模型）。
- `notifications.*`：飞书、Telegram、企业微信、钉钉、邮件、Bark 独立开关与地址。
