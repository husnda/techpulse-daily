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
                    return cleaned[:1400]
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
                    article_text = plain[:1200]
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
                        extracted.append(f"- {c.get('author', 'user')}: {c_plain[:220]}")
                if extracted:
                    comments_text = "\n".join(extracted)
        except Exception:
            pass
            
    parts = []
    if article_text:
        parts.append(f"【文章原文节选】: {article_text}")
    if comments_text:
        parts.append(f"【社区热评与争论】:\n{comments_text}")
    return "\n\n".join(parts)

def call_ai_summary(ai_cfg, github_items, hn_items):
    """
    Fetches raw READMEs and HN article/comments in parallel, then calls OpenAI Responses API.
    Outputs accurate category classifications and rich multi-point summaries.
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
        gh_data_list.append(f"仓库全名: {it['full_name']}\n主要语言: {it.get('language')}\n今日新增Star: +{it.get('stars_today', 0)}\nREADME/官方简介: {ctx}\n")
    gh_input_text = "\n---\n".join(gh_data_list)

    hn_data_list = []
    for it in hn_items[:12]:
        ctx = it.get("raw_context") or it.get("title", "")
        hn_data_list.append(f"讨论ID: {it.get('id')}\n标题: {it.get('title')}\n源网站域名: {it.get('domain')}\n点赞/评论数: {it.get('points')}分/{it.get('comments_count')}条\n原文与评论内容: {ctx}\n")
    hn_input_text = "\n---\n".join(hn_data_list)

    system_instructions = (
        "你是一名顶尖技术架构师、前沿科技产品评论家。你的任务是根据提供的 GitHub 真实 README 内容与 Hacker News 真实原文及高赞评论，"
        "提炼一份客观、专业、内容充实的技术早报。严禁空泛编造，务必基于真实内容做深入分析。"
        "你必须只输出纯 JSON 格式（不要使用 markdown 标记包裹，直接返回合法的 JSON 对象）。"
    )

    user_prompt = f"""请阅读以下 GitHub 热门项目的真实 README 与 Hacker News 的真实原文/评论，返回一个合法的 JSON 对象。

JSON 格式要求如下：
{{
  "global_overview": "2-3句话宏观概括今日全球技术圈的最重大动态（纯文本，不要带有###等标题符号，重点词可用**加粗**）。",
  "github_items": {{
    "owner/repo": {{
      "category": "精准分类，从以下挑选最贴切的一个：[AI/智能体, 系统底层, 前端开发, 效率工具, 算法与学习, 移动开发, 数据科学, 安全与网络]",
      "summary": "【核心定位】1句话概括其核心功能与解决的痛点。\n【技术亮点】1句话讲明其架构设计、工作原理或给开发者的启发。"
    }}
  }},
  "hn_items": {{
    "讨论ID": {{
      "category": "精准分类，从以下挑选最贴切的一个：[数码硬件, 游戏娱乐, 人工智能, 商业与收购, 系统架构, 前端生态, 隐私安全, 科技社会, 开发者热议]",
      "summary": "【核心看点】1句话讲清事件本质或原文核心论点。\n【社区争议】1句话概括社区评论区的核心分歧、质疑或延伸启示。"
    }}
  }}
}}

注意：分类务必精准！例如 AirPods/iPhone 必须分类为\"数码硬件\"，游戏相关（如 No Mans Sky / Steam）必须分类为\"游戏娱乐\"，Tailwind/React 归为\"前端开发/前端生态\"，不要笼统归类。

【GitHub 仓库真实数据 (含 README 节选)】
{gh_input_text}

【Hacker News 真实数据 (含 原文及评论节选)】
{hn_input_text}
"""

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "User-Agent": "TechPulse-AI-Summarizer/2.0"
    }

    responses_url = f"{api_base}/responses" if "/v1" in api_base else f"{api_base}/v1/responses"
    responses_payload = {
        "model": model,
        "instructions": system_instructions,
        "input": user_prompt,
        "temperature": ai_cfg.get("temperature", 0.3),
        "max_output_tokens": 3500
    }

    raw_response_text = ""
    try:
        logger.info(f"Calling OpenAI Responses API: {responses_url} (model: {model})")
        req = urllib.request.Request(
            responses_url,
            data=json.dumps(responses_payload).encode("utf-8"),
            headers=headers
        )
        with urllib.request.urlopen(req, timeout=50) as resp:
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
                "max_tokens": 3500
            }
            try:
                chat_req = urllib.request.Request(
                    chat_url,
                    data=json.dumps(chat_payload).encode("utf-8"),
                    headers=headers
                )
                with urllib.request.urlopen(chat_req, timeout=50) as chat_resp:
                    chat_data = json.loads(chat_resp.read().decode("utf-8"))
                    raw_response_text = chat_data["choices"][0]["message"]["content"].strip()
            except Exception as e2:
                logger.error(f"Fallback chat/completions also failed: {e2}")
    except Exception as e:
        logger.warning(f"AI call failed: {e}")

    # 3. Parse JSON from AI response
    if raw_response_text:
        clean_json = raw_response_text.strip()
        m = re.search(r"\{.*\}", clean_json, re.DOTALL)
        if m:
            try:
                parsed = json.loads(m.group(0))
                logger.info(f"Successfully parsed structured AI response with {len(parsed.get('github_items', {}))} GitHub items and {len(parsed.get('hn_items', {}))} HN items.")
                return parsed
            except Exception as pe:
                logger.warning(f"Failed to parse JSON from AI: {pe}")
        return {"global_overview": raw_response_text, "github_items": {}, "hn_items": {}}
        
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
        gh_map = ai_data.get("github_items", {}) or ai_data.get("github_summaries", {})
        hn_map = ai_data.get("hn_items", {}) or ai_data.get("hn_summaries", {})
        
        for it in github_items:
            entry = gh_map.get(it["full_name"], {})
            if isinstance(entry, dict):
                if entry.get("category"):
                    it["topic"] = entry["category"]
                it["ai_summary"] = entry.get("summary", "")
            elif isinstance(entry, str):
                it["ai_summary"] = entry
                
        for it in hn_items:
            entry = hn_map.get(str(it.get("id")), {})
            if isinstance(entry, dict):
                if entry.get("category"):
                    it["topic"] = entry["category"]
                it["ai_summary"] = entry.get("summary", "")
            elif isinstance(entry, str):
                it["ai_summary"] = entry
                
    elif isinstance(ai_data, str):
        ai_overview = ai_data
        
    # Fallback smart summaries if AI summary is empty for any item
    for it in github_items:
        if not it.get("ai_summary"):
            desc = it.get("description") or "开源项目"
            it["ai_summary"] = f"【核心定位】专注于 {it.get('topic', '开源技术')} 领域，采用 {it.get('language')} 构建。\n【关键特性】{desc}"
            
    for it in hn_items:
        if not it.get("ai_summary"):
            it["ai_summary"] = f"【核心看点】来自 {it.get('domain')} 的热议话题，围绕 {it.get('topic')} 展开。\n【讨论热度】获得 {it.get('points')} 点赞与 {it.get('comments_count')} 条社区深入讨论。"
            
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
            clean_ai_md = it['ai_summary'].replace("\n", " ")
            lines.append(f"- **✨ AI 深度解读**: {clean_ai_md}")
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
            clean_ai_md = it['ai_summary'].replace("\n", " ")
            lines.append(f"- **✨ AI 深度解读**: {clean_ai_md}")
        lines.append("")
        
    lines.append("---\n")
    gen_time = data.get("generated_at", "")
    lines.append(f"*本期早报由 TechPulse 自动聚合生成于 {gen_time} ｜ [在线主页](https://husnda.github.io/techpulse-daily/) ｜ [RSS 订阅](https://husnda.github.io/techpulse-daily/feed.xml)*")
    return "\n".join(lines)
