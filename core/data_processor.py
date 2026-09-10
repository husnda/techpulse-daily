import json
import urllib.request
import datetime
import logging

logger = logging.getLogger("TechPulse.Processor")

def call_ai_summary(ai_cfg, github_items, hn_items):
    api_key = ai_cfg.get("api_key")
    if not api_key:
        return None
    api_base = ai_cfg.get("api_base", "https://api.openai.com/v1").rstrip("/")
    model = ai_cfg.get("model", "gpt-4o-mini")
    
    gh_lines = []
    for it in github_items[:8]:
        gh_lines.append(f"- {it['full_name']} ({it['language']}, +{it['stars_today']}今日星标): {it['description']}")
    gh_text = "\n".join(gh_lines)

    hn_lines = []
    for it in hn_items[:8]:
        hn_lines.append(f"- {it['title']} ({it['points']}点赞, {it['comments_count']}讨论): {it['url']}")
    hn_text = "\n".join(hn_lines)
    
    prompt = f"""你是一名资深技术总监与敏锐的科技趋势分析师。请根据以下今日 GitHub Trending 热门项目与 Hacker News 头条讨论，生成一份高信息密度的简报。

要求：
1. 提取 2-3 句话的【今日科技风向速览】（概括今天全球极客和开源社区最关注的重大动态）。
2. 从中挑选 3 个最值得关注的开源项目，用一句话点明其核心价值/解决什么痛点。
3. 从中挑选 3 个最具讨论深度的技术/产业热点，用一句话点明争议或核心看点。
4. 语言精炼生动、客观专业，直接输出 Markdown 格式，不要冗余客套话。

【GitHub 今日精选】
{gh_text}

【Hacker News 今日精选】
{hn_text}
"""
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a professional tech radar and engineering curator."},
            {"role": "user", "content": prompt}
        ],
        "temperature": ai_cfg.get("temperature", 0.3),
        "max_tokens": 1000
    }
    try:
        req = urllib.request.Request(
            f"{api_base}/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {api_key}"
            }
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            return res_data["choices"][0]["message"]["content"].strip()
    except Exception as e:
        logger.warning(f"AI summarization failed ({e}), continuing with rule-based formatting.")
        return None

def process_daily_digest(github_items, hn_items, config, date_str=None):
    if not date_str:
        date_str = datetime.date.today().isoformat()
    ai_cfg = config.get("ai_summary", {})
    ai_overview = None
    if ai_cfg.get("enabled", False):
        ai_overview = call_ai_summary(ai_cfg, github_items, hn_items)
    top_story = hn_items[0]["title"] if hn_items else (github_items[0]["full_name"] if github_items else "今日技术精选")
    return {
        "date": date_str,
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "top_highlight": top_story,
        "ai_overview": ai_overview,
        "github_items": github_items,
        "hn_items": hn_items,
        "stats": {
            "github_count": len(github_items),
            "hn_count": len(hn_items),
            "total_stars_today": sum(it.get("stars_today", 0) for it in github_items),
            "total_hn_points": sum(it.get("points", 0) for it in hn_items)
        }
    }

def format_markdown_digest(data):
    date = data["date"]
    lines = [
        f"# 🛰️ TechPulse Daily 技术早报 ({date})\n",
        "> 聚合 GitHub Daily Trending 开源热点与 Hacker News 极客高分讨论\n"
    ]
    if data.get("ai_overview"):
        lines.append("## 🧠 今日技术风向速览 (AI 提炼)\n")
        lines.append(data["ai_overview"] + "\n")
        lines.append("---\n")
    lines.append("## 🚀 GitHub Trending 热门开源项目\n")
    if not data["github_items"]:
        lines.append("*今日暂无抓取到的 GitHub 趋势数据*\n")
    for i, it in enumerate(data["github_items"], 1):
        stars_today = f"+{it['stars_today']:,}" if it.get('stars_today') else "Trending"
        stars_total = f"{it['stars_total']:,}" if it.get('stars_total') else "0"
        topic_tag = f" `[{it['topic']}]`" if it.get('topic') else ""
        lang_tag = f"**{it['language']}**" if it.get('language') != "N/A" else "General"
        lines.append(f"### {i}. [{it['full_name']}]({it['url']}){topic_tag}")
        lines.append(f"- **语言**: {lang_tag} | **今日增速**: ⭐ {stars_today} | **总星标**: {stars_total} | **Forks**: {it['forks']:,}")
        if it.get('description'):
            lines.append(f"- **简介**: {it['description']}")
        lines.append("")
    lines.append("---\n")
    lines.append("## 🔥 Hacker News 科技前沿与深度讨论\n")
    if not data["hn_items"]:
        lines.append("*今日暂无抓取到的 Hacker News 数据*\n")
    for i, it in enumerate(data["hn_items"], 1):
        topic_tag = f" `[{it['topic']}]`" if it.get('topic') else ""
        domain = it.get("domain", "news.ycombinator.com")
        lines.append(f"### {i}. [{it['title']}]({it['url']}){topic_tag}")
        lines.append(f"- **来源**: `{domain}` | **热度**: 🔥 {it['points']} points | **评论**: 💬 [{it['comments_count']} 条讨论]({it['hn_url']})")
        lines.append("")
    lines.append("---\n")
    gen_time = data.get("generated_at", "")
    lines.append(f"*本期早报由 TechPulse 自动聚合生成于 {gen_time}*")
    return "\n".join(lines)
