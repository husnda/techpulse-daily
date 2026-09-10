import json
import urllib.request
import urllib.error
import datetime
import logging

logger = logging.getLogger("TechPulse.Processor")

def call_ai_summary(ai_cfg, github_items, hn_items):
    """
    Calls OpenAI Responses API (/v1/responses) with fallback to /chat/completions.
    Extracts high-signal Chinese tech digest.
    """
    api_key = ai_cfg.get("api_key")
    if not api_key:
        return None
    api_base = ai_cfg.get("api_base", "https://api.openai.com/v1").rstrip("/")
    model = ai_cfg.get("model", "gpt-4o-mini")
    
    gh_lines = []
    for it in github_items[:8]:
        stars_today = f"+{it.get('stars_today', 0):,}"
        gh_lines.append(f"- {it['full_name']} [{it.get('language', 'General')} / {it.get('topic', 'Dev')}]: 今日星标 {stars_today}，总星 {it.get('stars_total', 0):,}。简介: {it.get('description', '')}")
    gh_text = "\n".join(gh_lines)

    hn_lines = []
    for it in hn_items[:8]:
        hn_lines.append(f"- {it['title']} [{it.get('domain', 'news')} / {it.get('topic', 'Tech')}]: 🔥 {it['points']} 分, 💬 {it['comments_count']} 条讨论。原链接: {it['url']}")
    hn_text = "\n".join(hn_lines)
    
    system_instructions = "你是一名资深技术架构师与敏锐的技术趋势分析师。你的职责是为开发者提炼每日全球开源界与极客圈最高价值的信息。"
    
    user_prompt = f"""请根据今天 GitHub Daily Trending 的热门开源项目与 Hacker News 的前沿头条讨论，撰写一份结构精炼、信息密度极高的【今日技术风向早报】。

要求：
1. 【今日核心观察】：用 2-3 句话提炼今日全球技术圈最值得关注的重大事件或技术趋势（直切要害，不做客套陈述）。
2. 【精选开源项目】：挑选 2-3 个最具突破性或实用价值的 GitHub 开源项目，每项用一句话讲清楚“它解决了什么关键痛点/适合什么场景”。
3. 【深度讨论与争议】：挑选 2-3 个 Hacker News 焦点讨论，每项用一句话概括“核心争论点或行业启示”。
4. 输出简洁严谨的 Markdown 格式。

【GitHub 今日热门数据】
{gh_text}

【Hacker News 今日讨论数据】
{hn_text}
"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "TechPulse-AI-Summarizer/2.0"
    }

    # 1. First attempt: OpenAI Responses API (/v1/responses)
    responses_url = f"{api_base}/responses" if "/v1" in api_base else f"{api_base}/v1/responses"
    responses_payload = {
        "model": model,
        "instructions": system_instructions,
        "input": user_prompt,
        "temperature": ai_cfg.get("temperature", 0.3),
        "max_output_tokens": 1000
    }
    
    try:
        logger.info(f"Calling OpenAI Responses API: {responses_url} (model: {model})")
        req = urllib.request.Request(
            responses_url,
            data=json.dumps(responses_payload).encode("utf-8"),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=35) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            
            if "output_text" in res_data and res_data["output_text"]:
                return res_data["output_text"].strip()
                
            for item in res_data.get("output", []):
                if item.get("type") == "message":
                    for c in item.get("content", []):
                        if c.get("type") == "output_text" and "text" in c:
                            return c["text"].strip()
                            
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        logger.warning(f"Responses API returned HTTP {e.code}: {err_body}")
        
        # Fallback to /chat/completions if /responses is not supported by endpoint/proxy
        if e.code in (404, 400, 405):
            logger.info("Falling back to legacy /chat/completions endpoint for compatibility...")
            chat_url = f"{api_base}/chat/completions" if "/v1" in api_base else f"{api_base}/v1/chat/completions"
            chat_payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": ai_cfg.get("temperature", 0.3),
                "max_tokens": 1000
            }
            try:
                chat_req = urllib.request.Request(
                    chat_url,
                    data=json.dumps(chat_payload).encode("utf-8"),
                    headers=headers
                )
                with urllib.request.urlopen(chat_req, timeout=35) as chat_resp:
                    chat_data = json.loads(chat_resp.read().decode("utf-8"))
                    return chat_data["choices"][0]["message"]["content"].strip()
            except Exception as e2:
                logger.error(f"Fallback chat/completions also failed: {e2}")
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
            "total_hn_points": sum(it.get("points", 0) for it in hn_items),
            "total_hn_comments": sum(it.get("comments_count", 0) for it in hn_items)
        }
    }

def format_markdown_digest(data):
    date = data["date"]
    stats = data.get("stats", {})
    gh_count = stats.get("github_count", len(data.get("github_items", [])))
    hn_count = stats.get("hn_count", len(data.get("hn_items", [])))
    stars_today_sum = stats.get("total_stars_today", 0)
    comments_sum = stats.get("total_hn_comments", 0)
    
    lines = [
        f"# 🛰️ TechPulse Daily 技术早报 ({date})\n",
        f"> ⚡ 本期精选 **{gh_count}** 个 GitHub 热门开源项目 (今日 +{stars_today_sum:,} Stars) 与 **{hn_count}** 篇 Hacker News 深度讨论 ({comments_sum:,} 条评论)\n"
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
        lines.append(f"- **语言**: {lang_tag} ｜ **今日增速**: ⭐ {stars_today} ｜ **总星标**: {stars_total} ｜ **Forks**: {it['forks']:,}")
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
        lines.append(f"- **来源**: `{domain}` ｜ **热度**: 🔥 {it['points']:,} points ｜ **深度讨论**: 💬 [{it['comments_count']:,} 条讨论]({it['hn_url']})")
        lines.append("")
        
    lines.append("---\n")
    gen_time = data.get("generated_at", "")
    lines.append(f"*本期早报由 TechPulse 自动聚合生成于 {gen_time} ｜ [在线主页](https://husnda.github.io/techpulse-daily/) ｜ [RSS 订阅](https://husnda.github.io/techpulse-daily/feed.xml)*")
    return "\n".join(lines)
