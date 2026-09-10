import json
import urllib.request
import urllib.error
import datetime
import logging
import re
import html
import concurrent.futures

logger = logging.getLogger("TechPulse.Processor")

def fetch_github_readme(full_name, timeout=6):
    """Fetches raw README.md for a GitHub repository across common branches."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
    for branch in ["main", "master", "HEAD"]:
        url = f"https://raw.githubusercontent.com/{full_name}/{branch}/README.md"
        try:
            req = urllib.request.Request(url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                text = resp.read().decode("utf-8", errors="ignore")
                if text and len(text) > 40:
                    cleaned = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
                    cleaned = re.sub(r"!\[.*?\]\(.*?\)", "", cleaned)
                    cleaned = re.sub(r"\[!\[.*?\]\(.*?\)\]\(.*?\)", "", cleaned)
                    cleaned = " ".join(cleaned.split())
                    return cleaned[:1200]
        except Exception:
            continue
    return ""

def fetch_hn_context(story_id, article_url, timeout=6):
    """Fetches article page readable text and top community comments from HN."""
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    article_text = ""
    comments_text = ""
    
    if article_url and not article_url.endswith(".pdf") and "news.ycombinator.com" not in article_url:
        try:
            req = urllib.request.Request(article_url, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                raw = resp.read(120000).decode("utf-8", errors="ignore")
                no_scripts = re.sub(r"<script.*?</script>", "", raw, flags=re.DOTALL | re.IGNORECASE)
                no_styles = re.sub(r"<style.*?</style>", "", no_scripts, flags=re.DOTALL | re.IGNORECASE)
                plain = re.sub(r"<[^>]+>", " ", no_styles)
                plain = html.unescape(" ".join(plain.split()))
                if len(plain) > 60:
                    article_text = plain[:1000]
        except Exception:
            pass
            
    if story_id:
        try:
            hn_api = f"https://hn.algolia.com/api/v1/items/{story_id}"
            req = urllib.request.Request(hn_api, headers=headers)
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                children = data.get("children", [])
                extracted = []
                for c in children[:3]:
                    c_text = c.get("text", "") or ""
                    c_plain = re.sub(r"<[^>]+>", " ", c_text)
                    c_plain = html.unescape(" ".join(c_plain.split()))
                    if len(c_plain) > 20:
                        extracted.append(f"- {c.get('author', 'user')}: {c_plain[:180]}")
                if extracted:
                    comments_text = "\n".join(extracted)
        except Exception:
            pass
            
    parts = []
    if article_text:
        parts.append(f"【文章原文节选】: {article_text}")
    if comments_text:
        parts.append(f"【社区高赞热评】:\n{comments_text}")
    return "\n\n".join(parts)

def call_ai_summary(ai_cfg, github_items, hn_items):
    """
    Fetches raw READMEs and HN article/comments in parallel, then calls OpenAI Responses API.
    Returns structured dict with global_overview and per-item summaries.
    """
    api_key = ai_cfg.get("api_key")
    if not api_key:
        return None
    api_base = ai_cfg.get("api_base", "https://api.openai.com/v1").rstrip("/")
    model = str(ai_cfg.get("model", "gpt-4o-mini")).strip()
    
    # 1. Parallel fetch raw contexts for GitHub and HN
    logger.info("Parallel fetching real GitHub READMEs and Hacker News context...")
    with concurrent.futures.ThreadPoolExecutor(max_workers=8) as executor:
        gh_futures = {executor.submit(fetch_github_readme, it["full_name"]): it for it in github_items[:12]}
        hn_futures = {executor.submit(fetch_hn_context, it.get("id"), it.get("url")): it for it in hn_items[:12]}
        
        for fut in concurrent.futures.as_completed(gh_futures):
            item = gh_futures[fut]
            try:
                item["raw_context"] = fut.result()
            except Exception:
                item["raw_context"] = ""
                
        for fut in concurrent.futures.as_completed(hn_futures):
            item = hn_futures[fut]
            try:
                item["raw_context"] = fut.result()
            except Exception:
                item["raw_context"] = ""

    # 2. Build structured prompt
    gh_data_list = []
    for it in github_items[:12]:
        ctx = it.get("raw_context") or it.get("description", "")
        gh_data_list.append(f"仓库: {it['full_name']}\n语言: {it.get('language')}\n今日Star: +{it.get('stars_today', 0)}\nREADME/简介内容: {ctx}\n")
    gh_input_text = "\n---\n".join(gh_data_list)

    hn_data_list = []
    for it in hn_items[:12]:
        ctx = it.get("raw_context") or it.get("title", "")
        hn_data_list.append(f"ID: {it.get('id')}\n标题: {it.get('title')}\n域名: {it.get('domain')}\n点赞/评论: {it.get('points')}分/{it.get('comments_count')}条\n原文与评论节选: {ctx}\n")
    hn_input_text = "\n---\n".join(hn_data_list)

    system_instructions = (
        "你是一名顶尖技术架构师与前沿科技主编。请严格基于提供的 GitHub 仓库真实 README 内容与 Hacker News 原文/讨论，"
        "提炼高信息密度、洞察深刻的技术早报。严禁凭空编造，务必结合真实内容。"
        "你必须只输出纯 JSON 格式（不要输出 markdown 代码块外包装，直接返回 JSON 对象）。"
    )

    user_prompt = f"""请仔细阅读以下今日 GitHub 热门开源项目的真实 README 内容与 Hacker News 讨论热点的真实内容，输出一个合法的 JSON 对象。

JSON 数据结构必须满足以下三个字段：
1. "global_overview": 字符串。用 2-3 句话宏观概括今日全球技术圈的最重大动态与技术风向（纯文本段落，严禁使用 ### 等标题符号，重点词可用 **加粗**）。
2. "github_summaries": 字典。Key 为仓库全名（例如 "owner/repo"），Value 为该项目基于 README 的核心提炼（1-2句话点明其真实解决的核心痛点、运行架构或独特价值）。
3. "hn_summaries": 字典。Key 为讨论 ID 字符串（例如 "49626190"），Value 为该话题基于原文与社区评论的深度提炼（1-2句话提炼讨论的核心争论点或给开发者的深层启示）。

【GitHub 仓库真实数据 (含 README 节选)】
{gh_input_text}

【Hacker News 真实数据 (含 原文及讨论节选)】
{hn_input_text}
"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "TechPulse-AI-Summarizer/2.0"
    }

    # Try Responses API first (/v1/responses)
    responses_url = f"{api_base}/responses" if "/v1" in api_base else f"{api_base}/v1/responses"
    responses_payload = {
        "model": model,
        "instructions": system_instructions,
        "input": user_prompt,
        "temperature": ai_cfg.get("temperature", 0.3),
        "max_output_tokens": 2500
    }

    raw_response_text = ""
    try:
        logger.info(f"Calling OpenAI Responses API: {responses_url} (model: {model})")
        req = urllib.request.Request(
            responses_url,
            data=json.dumps(responses_payload).encode("utf-8"),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=45) as resp:
            res_data = json.loads(resp.read().decode("utf-8"))
            if "output_text" in res_data and res_data["output_text"]:
                raw_response_text = res_data["output_text"].strip()
            else:
                for item in res_data.get("output", []):
                    if item.get("type") == "message":
                        for c in item.get("content", []):
                            if c.get("type") == "output_text" and "text" in c:
                                raw_response_text += c["text"]
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        logger.warning(f"Responses API returned HTTP {e.code}: {err_body}")
        if e.code in (404, 400, 405):
            logger.info("Falling back to legacy /chat/completions endpoint...")
            chat_url = f"{api_base}/chat/completions" if "/v1" in api_base else f"{api_base}/v1/chat/completions"
            chat_payload = {
                "model": model,
                "messages": [
                    {"role": "system", "content": system_instructions},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": ai_cfg.get("temperature", 0.3),
                "max_tokens": 2500
            }
            try:
                chat_req = urllib.request.Request(
                    chat_url,
                    data=json.dumps(chat_payload).encode("utf-8"),
                    headers=headers
                )
                with urllib.request.urlopen(chat_req, timeout=45) as chat_resp:
                    chat_data = json.loads(chat_resp.read().decode("utf-8"))
                    raw_response_text = chat_data["choices"][0]["message"]["content"].strip()
            except Exception as e2:
                logger.error(f"Fallback chat/completions also failed: {e2}")
    except Exception as e:
        logger.warning(f"AI call failed: {e}")

    # 3. Parse JSON from AI response
    if raw_response_text:
        # Clean markdown code block if present
        clean_json = raw_response_text.strip()
        m = re.search(r"\{.*\}", clean_json, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                logger.info(f"Successfully parsed structured AI response with {len(parsed.get('github_summaries', {}))} GitHub summaries and {len(parsed.get('hn_summaries', {}))} HN summaries.")
                return parsed
            except Exception as pe:
                logger.warning(f"Failed to parse JSON from AI: {pe}")
        return {"global_overview": raw_response_text, "github_summaries": {}, "hn_summaries": {}}
        
    return None

def process_daily_digest(github_items, hn_items, config, date_str=None):
    if not date_str:
        date_str = datetime.date.today().isoformat()
    ai_cfg = config.get("ai_summary", {})
    ai_data = None
    if ai_cfg.get("enabled", False):
        ai_data = call_ai_summary(ai_cfg, github_items, hn_items)
        
    ai_overview = ""
    if isinstance(ai_data, dict):
        ai_overview = ai_data.get("global_overview", "")
        gh_sums = ai_data.get("github_summaries", {})
        hn_sums = ai_data.get("hn_summaries", {})
        for it in github_items:
            it["ai_summary"] = gh_sums.get(it["full_name"], "")
        for it in hn_items:
            it["ai_summary"] = hn_sums.get(str(it.get("id")), "")
    elif isinstance(ai_data, str):
        ai_overview = ai_data
        
    # Fallback smart summaries if AI summary is empty for any item
    for it in github_items:
        if not it.get("ai_summary"):
            desc = it.get("description") or "开源项目"
            it["ai_summary"] = f"项目定位于 {it.get('topic', '开发工具')}，采用 {it.get('language')} 构建。主要功能：{desc}"
            
    for it in hn_items:
        if not it.get("ai_summary"):
            it["ai_summary"] = f"来自 {it.get('domain')} 的热议话题（{it.get('points')} 点赞 / {it.get('comments_count')} 讨论），聚焦 {it.get('topic')} 领域的前沿进展与行业探讨。"
            
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
        if it.get('ai_summary'):
            lines.append(f"- **✨ AI 核心解读 (基于 README)**: {it['ai_summary']}")
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
        if it.get('ai_summary'):
            lines.append(f"- **✨ AI 核心解读 (基于原文与热评)**: {it['ai_summary']}")
        lines.append("")
        
    lines.append("---\n")
    gen_time = data.get("generated_at", "")
    lines.append(f"*本期早报由 TechPulse 自动聚合生成于 {gen_time} ｜ [在线主页](https://husnda.github.io/techpulse-daily/) ｜ [RSS 订阅](https://husnda.github.io/techpulse-daily/feed.xml)*")
    return "\n".join(lines)
