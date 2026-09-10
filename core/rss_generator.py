import os
import datetime
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from pathlib import Path
import json
import re

def format_rfc822(dt=None):
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

def format_ai_summary_html(text):
    if not text:
        return ""
    safe = escape(text)
    # Convert 【...】 to <strong>【...】</strong>
    safe = re.sub(r"(【.+?】)", r"<strong style='color: #0f172a;'>\1</strong>", safe)
    # Convert linebreaks to <br>
    safe = safe.replace("\n", "<br>")
    return safe

def generate_html_content(digest_data):
    date_str = digest_data.get("date", "")
    ai_overview = digest_data.get("ai_overview")
    gh_items = digest_data.get("github_items", [])
    hn_items = digest_data.get("hn_items", [])
    stats = digest_data.get("stats", {})
    
    total_stars = stats.get("total_stars_today", sum(it.get("stars_today", 0) for it in gh_items))
    total_comments = stats.get("total_hn_comments", sum(it.get("comments_count", 0) for it in hn_items))
    
    html = []
    html.append('<div style="font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.5; max-width: 820px; margin: 0 auto;">')
    
    # Clean Editorial Top Banner
    html.append(f'''
    <div style="border-bottom: 1px solid #e5e7eb; padding-bottom: 16px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: baseline; flex-wrap: wrap; gap: 8px; margin-bottom: 8px;">
            <h1 style="margin: 0; font-size: 20px; font-weight: 700; color: #0f172a; letter-spacing: 0;">🛰️ TechPulse Daily 技术早报</h1>
            <span style="font-family: ui-monospace, SFMono-Regular, monospace; font-size: 13px; color: #64748b;">{date_str}</span>
        </div>
        <div style="font-size: 12.5px; color: #64748b; display: flex; gap: 12px; flex-wrap: wrap;">
            <span>📦 <strong>{len(gh_items)}</strong> 个开源项目 (+{total_stars:,} Stars)</span>
            <span>·</span>
            <span>🔥 <strong>{len(hn_items)}</strong> 篇深度讨论 ({total_comments:,} 评论)</span>
            <span>·</span>
            <span>每日 08:30 定时更新</span>
        </div>
    </div>
    ''')
    
    # AI Macro Pulse if present
    if ai_overview:
        clean_ai = ai_overview.replace("\n", "<br>")
        clean_ai = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", clean_ai)
        html.append(f'''
        <div style="background: #f8fafc; border-left: 3px solid #0284c7; padding: 14px 18px; border-radius: 4px; margin-bottom: 24px;">
            <div style="font-size: 13px; font-weight: 700; color: #0369a1; margin-bottom: 6px;">🧠 今日技术风向速览</div>
            <div style="font-size: 13.5px; color: #334155; line-height: 1.65;">{clean_ai}</div>
        </div>
        ''')
        
    # GitHub section
    html.append('<div style="margin-bottom: 32px;">')
    html.append('<div style="display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; margin-bottom: 14px;"><h2 style="margin: 0; font-size: 15px; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.3px;">🚀 GitHub Trending 热门开源项目</h2><span style="font-size: 12px; color: #94a3b8;">点击 ✨ 展开 AI 深度解读</span></div>')
    html.append('<div style="display: flex; flex-direction: column; gap: 10px;">')
    for i, it in enumerate(gh_items, 1):
        stars_today = f"+{it.get('stars_today', 0):,}" if it.get('stars_today') else "Trending"
        stars_total = f"{it.get('stars_total', 0):,}" if it.get('stars_total') else "0"
        topic = it.get("topic", "开源技术")
        lang = it.get("language", "General")
        desc = it.get("description", "无项目描述")
        url = it.get("url", "#")
        full_name = it.get("full_name", "")
        forks = f"{it.get('forks', 0):,}"
        ai_sum_html = format_ai_summary_html(it.get("ai_summary", ""))
        
        html.append(f'''
        <div style="border: 1px solid #eaecf0; border-radius: 6px; padding: 14px 16px; background: #ffffff;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; margin-bottom: 6px;">
                <div style="display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;">
                    <span style="font-family: ui-monospace, SFMono-Regular, monospace; font-size: 12.5px; font-weight: 600; color: #94a3b8;">#{i}</span>
                    <a href="{url}" target="_blank" style="font-size: 15px; font-weight: 600; color: #0f172a; text-decoration: none;">{full_name}</a>
                </div>
                <span style="font-size: 11px; background: #f1f5f9; color: #475569; padding: 2px 7px; border-radius: 4px; font-weight: 500; white-space: nowrap;">{topic}</span>
            </div>
            <p style="margin: 0 0 10px 0; font-size: 13.5px; color: #475569; line-height: 1.5;">{escape(desc)}</p>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #64748b; flex-wrap: wrap; gap: 8px;">
                <div style="display: flex; gap: 12px; align-items: center;">
                    <span style="color: #b45309; font-weight: 600;">⭐ {stars_today}</span>
                    <span>·</span>
                    <span>★ {stars_total}</span>
                    <span>·</span>
                    <span>⑂ {forks}</span>
                    <span>·</span>
                    <span>{lang}</span>
                </div>
                <button class="ai-toggle-btn" onclick="toggleAiBox(\'gh-ai-{i}\')" style="background: transparent; border: 1px solid #e2e8f0; color: #475569; padding: 2px 8px; border-radius: 4px; font-size: 11.5px; cursor: pointer;">
                    <span>✨ AI 深度解读</span>
                </button>
            </div>
            <div id="gh-ai-{i}" class="ai-summary-box" style="display: none; margin-top: 10px; padding: 12px 14px; background: #f8fafc; border: 1px solid #e2e8f0; border-left: 3px solid #10b981; border-radius: 4px; font-size: 13px; color: #334155; line-height: 1.65;">
                <div style="font-size: 11px; font-weight: 700; color: #047857; margin-bottom: 6px;">✨ 基于官方 README 核心提炼</div>
                <div>{ai_sum_html}</div>
            </div>
        </div>
        ''')
    html.append('</div></div>')
    
    # Hacker News section
    html.append('<div>')
    html.append('<div style="display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #e5e7eb; padding-bottom: 8px; margin-bottom: 14px;"><h2 style="margin: 0; font-size: 15px; font-weight: 700; color: #0f172a; text-transform: uppercase; letter-spacing: 0.3px;">🔥 Hacker News 科技前沿与深度讨论</h2><span style="font-size: 12px; color: #94a3b8;">点击 ✨ 展开 AI 深度解读</span></div>')
    html.append('<div style="display: flex; flex-direction: column; gap: 10px;">')
    for i, it in enumerate(hn_items, 1):
        title = it.get("title", "")
        url = it.get("url", "#")
        hn_url = it.get("hn_url", "#")
        points = f"{it.get('points', 0):,}"
        comments = f"{it.get('comments_count', 0):,}"
        domain = it.get("domain", "news.ycombinator.com")
        topic = it.get("topic", "科技前沿")
        ai_sum_html = format_ai_summary_html(it.get("ai_summary", ""))
        
        html.append(f'''
        <div style="border: 1px solid #eaecf0; border-radius: 6px; padding: 14px 16px; background: #ffffff;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; margin-bottom: 6px;">
                <div style="display: flex; align-items: baseline; gap: 8px;">
                    <span style="font-family: ui-monospace, SFMono-Regular, monospace; font-size: 12.5px; font-weight: 600; color: #94a3b8;">#{i}</span>
                    <a href="{url}" target="_blank" style="font-size: 15px; font-weight: 600; color: #0f172a; text-decoration: none; line-height: 1.4;">{escape(title)}</a>
                </div>
                <span style="font-size: 11px; background: #f1f5f9; color: #475569; padding: 2px 7px; border-radius: 4px; font-weight: 500; white-space: nowrap;">{topic}</span>
            </div>
            <div style="display: flex; justify-content: space-between; align-items: center; font-size: 12px; color: #64748b; flex-wrap: wrap; gap: 8px; margin-top: 8px;">
                <div style="display: flex; gap: 12px; align-items: center;">
                    <span style="color: #b91c1c; font-weight: 600;">🔥 {points} pts</span>
                    <span>·</span>
                    <a href="{hn_url}" target="_blank" style="color: #4f46e5; text-decoration: none; font-weight: 500;">💬 {comments} 条讨论 →</a>
                    <span>·</span>
                    <span>{domain}</span>
                </div>
                <button class="ai-toggle-btn" onclick="toggleAiBox(\'hn-ai-{i}\')" style="background: transparent; border: 1px solid #e2e8f0; color: #475569; padding: 2px 8px; border-radius: 4px; font-size: 11.5px; cursor: pointer;">
                    <span>✨ AI 深度解读</span>
                </button>
            </div>
            <div id="hn-ai-{i}" class="ai-summary-box" style="display: none; margin-top: 10px; padding: 12px 14px; background: #f8fafc; border: 1px solid #e2e8f0; border-left: 3px solid #3b82f6; border-radius: 4px; font-size: 13px; color: #334155; line-height: 1.65;">
                <div style="font-size: 11px; font-weight: 700; color: #1d4ed8; margin-bottom: 6px;">✨ 基于原文与社区热评深度提炼</div>
                <div>{ai_sum_html}</div>
            </div>
        </div>
        ''')
    html.append('</div></div>')
    
    html.append(f'<div style="margin-top: 28px; padding-top: 14px; border-top: 1px solid #eaecf0; font-size: 12px; color: #94a3b8; text-align: center;">由 TechPulse 自动化生成于 {digest_data.get("generated_at", "")} ｜ 每日 08:30 更新</div>')
    html.append('</div>')
    return "\n".join(html)

def generate_rss_xml(history_digests, config):
    ET.register_namespace("atom", "http://www.w3.org/2005/Atom")
    ET.register_namespace("content", "http://purl.org/rss/1.0/modules/content/")
    
    rss_cfg = config.get("rss", {})
    feed_title = rss_cfg.get("feed_title", "TechPulse Daily")
    feed_desc = rss_cfg.get("feed_description", "Daily Tech Radar")
    feed_link = rss_cfg.get("feed_link", "https://husnda.github.io/techpulse-daily").rstrip("/")
    
    rss = ET.Element("rss", {"version": "2.0"})
    channel = ET.SubElement(rss, "channel")
    
    ET.SubElement(channel, "title").text = feed_title
    ET.SubElement(channel, "link").text = feed_link
    ET.SubElement(channel, "description").text = feed_desc
    ET.SubElement(channel, "language").text = "zh-cn"
    ET.SubElement(channel, "lastBuildDate").text = format_rfc822()
    ET.SubElement(channel, "generator").text = "TechPulse Daily Digest Generator"
    
    atom_link = ET.SubElement(channel, "{http://www.w3.org/2005/Atom}link", {
        "href": f"{feed_link}/feed.xml",
        "rel": "self",
        "type": "application/rss+xml"
    })
    
    for digest in history_digests:
        date_str = digest.get("date", "")
        top_hl = digest.get("top_highlight", "")
        title = f"【{date_str}】技术早报：{top_hl}"
        guid_str = f"techpulse-{date_str}"
        link_url = f"{feed_link}/archive/{date_str}.html"
        
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "link").text = link_url
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = guid_str
        
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            dt = dt.replace(hour=8, minute=0, second=0, tzinfo=datetime.timezone.utc)
            pub_date_str = format_rfc822(dt)
        except Exception:
            pub_date_str = format_rfc822()
            
        ET.SubElement(item, "pubDate").text = pub_date_str
        ET.SubElement(item, "description").text = generate_html_content(digest)
        
    xml_bytes = ET.tostring(rss, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")

def render_web_page(current_digest, history_digests, config, is_archive=False):
    body_html = generate_html_content(current_digest) if current_digest else "<p>暂无早报数据</p>"
    feed_filename = config.get("rss", {}).get("feed_filename", "feed.xml")
    date_str = current_digest.get("date", "")
    
    if is_archive:
        rss_rel_url = f"../{feed_filename}"
        home_rel_url = "../index.html"
        archive_prefix = ""
    else:
        rss_rel_url = feed_filename
        home_rel_url = "index.html"
        archive_prefix = "archive/"
        
    archive_links = []
    for d in history_digests[:15]:
        d_str = d.get("date", "")
        hl = d.get("top_highlight", "技术要闻")[:25]
        target_href = f"{archive_prefix}{d_str}.html" if not is_archive else f"{d_str}.html"
        is_curr = (d_str == date_str)
        link_bg = "background: #f1f5f9; font-weight: 600; color: #0f172a;" if is_curr else "color: #64748b;"
        archive_links.append(f'<li style="margin-bottom: 2px;"><a href="{target_href}" style="display: block; padding: 6px 10px; border-radius: 4px; text-decoration: none; font-size: 12.5px; {link_bg}">📅 {d_str} - {escape(hl)}...</a></li>')
    archive_html = "".join(archive_links)
    
    back_btn_html = f'<a href="{home_rel_url}" class="btn btn-outline">← 返回今日最新</a>' if is_archive else ""
    page_title = f"TechPulse Daily 技术早报 ({date_str})" if is_archive else "TechPulse Daily | GitHub Trending & Hacker News 每日精选早报"
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{page_title}</title>
    <link rel="alternate" type="application/rss+xml" title="TechPulse RSS Feed" href="{rss_rel_url}">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background: #fafafa; color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.5; padding: 16px; }}
        .container {{ max-width: 1040px; margin: 0 auto; }}
        .top-nav {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 18px; background: #ffffff; border-radius: 6px; border: 1px solid #eaecf0; margin-bottom: 18px; flex-wrap: wrap; gap: 12px; }}
        .brand {{ display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 16px; color: #0f172a; text-decoration: none; }}
        .nav-actions {{ display: flex; gap: 8px; align-items: center; }}
        .btn {{ display: inline-flex; align-items: center; gap: 5px; padding: 6px 12px; border-radius: 4px; font-size: 12.5px; font-weight: 500; text-decoration: none; cursor: pointer; border: 1px solid transparent; transition: all 0.15s ease; }}
        .btn-rss {{ background: #0f172a; color: #ffffff; }}
        .btn-rss:hover {{ background: #334155; }}
        .btn-outline {{ border-color: #d1d5db; background: #ffffff; color: #374151; }}
        .btn-outline:hover {{ background: #f3f4f6; }}
        .ai-toggle-btn:hover {{ background: #f1f5f9 !important; border-color: #cbd5e1 !important; color: #0f172a !important; }}
        .main-layout {{ display: grid; grid-template-columns: 1fr 260px; gap: 18px; }}
        @media (max-width: 820px) {{ .main-layout {{ grid-template-columns: 1fr; }} }}
        .feed-container {{ background: #ffffff; border-radius: 6px; border: 1px solid #eaecf0; padding: 24px; }}
        .sidebar {{ display: flex; flex-direction: column; gap: 14px; }}
        .side-card {{ background: #ffffff; border-radius: 6px; border: 1px solid #eaecf0; padding: 16px; }}
        .side-title {{ font-size: 12px; font-weight: 700; color: #64748b; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .copy-toast {{ display: none; position: fixed; bottom: 24px; right: 24px; background: #0f172a; color: #f8fafc; padding: 10px 18px; border-radius: 4px; font-size: 13px; box-shadow: 0 4px 12px rgba(0,0,0,0.12); z-index: 99; }}
    </style>
</head>
<body>
    <div class="container">
        <header class="top-nav">
            <a href="{home_rel_url}" class="brand">
                <span>🛰️</span>
                <span>TechPulse Daily</span>
            </a>
            <div class="nav-actions">
                {back_btn_html}
                <button class="btn btn-rss" onclick="copyRssLink()">📡 复制 RSS 订阅源</button>
                <a href="{rss_rel_url}" class="btn btn-outline" target="_blank">查看原始 XML</a>
            </div>
        </header>
        <div class="main-layout">
            <main class="feed-container">
                {body_html}
            </main>
            <aside class="sidebar">
                <div class="side-card">
                    <div class="side-title">📡 RSS 订阅指南</div>
                    <p style="font-size: 12.5px; color: #64748b; margin-bottom: 10px; line-height: 1.5;">支持 NetNewsWire, Reeder, Follow, Feedly，每日 08:30 自动拉取更新。</p>
                    <input type="text" id="rssUrl" readonly value="{rss_rel_url}" style="width: 100%; padding: 6px 10px; font-size: 12px; background: #f8fafc; border: 1px solid #d1d5db; border-radius: 4px; color: #374151; margin-bottom: 8px;">
                    <button class="btn btn-outline" style="width: 100%; justify-content: center;" onclick="copyRssLink()">点击一键复制</button>
                </div>
                <div class="side-card">
                    <div class="side-title">🗂 往期早报归档</div>
                    <ul style="list-style: none; padding: 0; margin: 0;">
                        {archive_html}
                    </ul>
                </div>
            </aside>
        </div>
    </div>
    <div id="toast" class="copy-toast">✅ RSS 地址已复制到剪贴板！</div>
    <script>
        function toggleAiBox(id) {{
            const box = document.getElementById(id);
            if (!box) return;
            if (box.style.display === "none" || box.style.display === "") {{
                box.style.display = "block";
            }} else {{
                box.style.display = "none";
            }}
        }}
        function copyRssLink() {{
            const fullUrl = new URL("{rss_rel_url}", window.location.href).href;
            navigator.clipboard.writeText(fullUrl).then(() => {{
                const toast = document.getElementById("toast");
                toast.style.display = "block";
                setTimeout(() => {{ toast.style.display = "none"; }}, 2500);
            }}).catch(() => {{
                alert("RSS 地址: " + fullUrl);
            }});
        }}
        window.addEventListener("DOMContentLoaded", () => {{
            document.getElementById("rssUrl").value = new URL("{rss_rel_url}", window.location.href).href;
        }});
    </script>
</body>
</html>'''
    return html

def save_rss_and_web(digest_data, config):
    out_dir = Path(config.get("app", {}).get("output_dir", "outputs"))
    if not out_dir.is_absolute():
        base_dir = Path(__file__).resolve().parent.parent
        out_dir = base_dir / out_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_dir = out_dir / "archive"
    archive_dir.mkdir(parents=True, exist_ok=True)
    
    date_str = digest_data.get("date", datetime.date.today().isoformat())
    
    json_archive = archive_dir / f"{date_str}.json"
    with open(json_archive, "w", encoding="utf-8") as f:
        json.dump(digest_data, f, ensure_ascii=False, indent=2)
        
    from core.data_processor import format_markdown_digest
    md_content = format_markdown_digest(digest_data)
    md_archive = archive_dir / f"{date_str}.md"
    with open(md_archive, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    latest_md = out_dir / "latest_digest.md"
    with open(latest_md, "w", encoding="utf-8") as f:
        f.write(md_content)
        
    history_digests = [digest_data]
    for jf in sorted(archive_dir.glob("*.json"), reverse=True):
        if jf.name == f"{date_str}.json":
            continue
        try:
            with open(jf, "r", encoding="utf-8") as f:
                history_digests.append(json.load(f))
        except Exception:
            pass
            
    max_items = config.get("rss", {}).get("max_feed_items", 30)
    history_digests = history_digests[:max_items]
    
    feed_filename = config.get("rss", {}).get("feed_filename", "feed.xml")
    xml_content = generate_rss_xml(history_digests, config)
    feed_path = out_dir / feed_filename
    with open(feed_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
        
    rss_alias_path = out_dir / "rss.xml"
    with open(rss_alias_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
            
    web_content = render_web_page(digest_data, history_digests, config, is_archive=False)
    index_path = out_dir / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(web_content)
        
    archive_html_paths = []
    for d in history_digests:
        d_date = d.get("date")
        if not d_date:
            continue
        arch_html = render_web_page(d, history_digests, config, is_archive=True)
        arch_path = archive_dir / f"{d_date}.html"
        with open(arch_path, "w", encoding="utf-8") as f:
            f.write(arch_html)
        archive_html_paths.append(str(arch_path))
        
    return {
        "feed_xml": str(feed_path),
        "rss_xml": str(rss_alias_path),
        "index_html": str(index_path),
        "latest_md": str(latest_md),
        "archive_md": str(md_archive),
        "archive_html_count": len(archive_html_paths)
    }
