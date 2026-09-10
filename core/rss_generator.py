import os
import datetime
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
from pathlib import Path
import json

def format_rfc822(dt=None):
    if dt is None:
        dt = datetime.datetime.now(datetime.timezone.utc)
    return dt.strftime("%a, %d %b %Y %H:%M:%S +0000")

def get_language_color(lang):
    colors = {
        "Python": "#3572A5",
        "TypeScript": "#3178c6",
        "JavaScript": "#f1e05a",
        "Rust": "#dea584",
        "Go": "#00ADD8",
        "C++": "#f34b7d",
        "C": "#555555",
        "Java": "#b07219",
        "Shell": "#89e051",
        "HTML": "#e34c26",
        "CSS": "#563d7c",
        "Ruby": "#701516",
        "Swift": "#F05138",
        "Kotlin": "#A97BFF"
    }
    return colors.get(lang, "#64748b")

def generate_html_content(digest_data):
    """Generates clean, aesthetic, highly structured HTML for both Web and RSS reader."""
    date_str = digest_data.get("date", "")
    ai_overview = digest_data.get("ai_overview")
    gh_items = digest_data.get("github_items", [])
    hn_items = digest_data.get("hn_items", [])
    stats = digest_data.get("stats", {})
    
    total_stars = stats.get("total_stars_today", sum(it.get("stars_today", 0) for it in gh_items))
    total_comments = stats.get("total_hn_comments", sum(it.get("comments_count", 0) for it in hn_items))
    
    html = []
    html.append('<div style="font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; color: #1e293b; line-height: 1.6; max-width: 820px; margin: 0 auto;">')
    
    # Header Banner Card
    html.append(f'''
    <div style="background: #0f172a; color: #f8fafc; padding: 20px 24px; border-radius: 6px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 10px;">
            <h1 style="margin: 0; font-size: 20px; font-weight: 700; color: #38bdf8; display: flex; align-items: center; gap: 8px;">🛰️ TechPulse Daily 技术早报</h1>
            <span style="font-family: ui-monospace, SFMono-Regular, monospace; font-size: 13px; background: #1e293b; color: #94a3b8; padding: 4px 10px; border-radius: 4px; border: 1px solid #334155;">{date_str}</span>
        </div>
        <div style="display: flex; gap: 16px; margin-top: 14px; font-size: 13px; color: #cbd5e1; flex-wrap: wrap; border-top: 1px solid #1e293b; padding-top: 12px;">
            <span>📦 <strong>{len(gh_items)}</strong> 个开源趋势项目</span>
            <span>⭐ <strong>+{total_stars:,}</strong> 今日新增 Star</span>
            <span>🔥 <strong>{len(hn_items)}</strong> 篇深度科技讨论</span>
            <span>💬 <strong>{total_comments:,}</strong> 条社区热议</span>
        </div>
    </div>
    ''')
    
    # AI Overview if present
    if ai_overview:
        clean_ai = ai_overview.replace("\n", "<br>")
        html.append(f'''
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-left: 4px solid #16a34a; padding: 16px 20px; border-radius: 6px; margin-bottom: 24px;">
            <div style="font-size: 14px; font-weight: 700; color: #15803d; margin-bottom: 8px; display: flex; align-items: center; gap: 6px;">🧠 今日技术风向速览 (AI 提炼)</div>
            <div style="font-size: 14px; color: #166534; line-height: 1.7;">{clean_ai}</div>
        </div>
        ''')
        
    # GitHub section
    html.append('<div style="margin-bottom: 32px;">')
    html.append('<div style="display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 14px;"><h2 style="margin: 0; font-size: 16px; font-weight: 700; color: #0f172a;">🚀 GitHub Trending 热门开源项目</h2><span style="font-size: 12px; color: #64748b;">按今日 Star 增速排序</span></div>')
    html.append('<div style="display: flex; flex-direction: column; gap: 10px;">')
    for i, it in enumerate(gh_items, 1):
        stars_today = f"+{it.get('stars_today', 0):,}" if it.get('stars_today') else "Trending"
        stars_total = f"{it.get('stars_total', 0):,}" if it.get('stars_total') else "0"
        topic = it.get("topic", "Open Source")
        lang = it.get("language", "General")
        lang_color = get_language_color(lang)
        desc = it.get("description", "无项目描述")
        url = it.get("url", "#")
        full_name = it.get("full_name", "")
        forks = f"{it.get('forks', 0):,}"
        
        html.append(f'''
        <div style="border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px 16px; background: #ffffff; transition: box-shadow 0.15s ease;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 6px;">
                <div style="display: flex; align-items: baseline; gap: 8px; flex-wrap: wrap;">
                    <span style="font-family: ui-monospace, SFMono-Regular, monospace; font-size: 13px; font-weight: 700; color: #64748b;">#{i}</span>
                    <a href="{url}" target="_blank" style="font-size: 15px; font-weight: 600; color: #0284c7; text-decoration: none;">{full_name}</a>
                </div>
                <div style="display: flex; gap: 6px; align-items: center;">
                    <span style="font-size: 11px; background: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 4px; font-weight: 500;">{topic}</span>
                    <span style="font-size: 11px; background: #fafafa; border: 1px solid #e5e7eb; color: #374151; padding: 2px 8px; border-radius: 4px; display: inline-flex; align-items: center; gap: 5px;">
                        <span style="width: 6px; height: 6px; border-radius: 50%; background: {lang_color}; display: inline-block;"></span>
                        {lang}
                    </span>
                </div>
            </div>
            <p style="margin: 0 0 10px 0; font-size: 13.5px; color: #334155; line-height: 1.5;">{escape(desc)}</p>
            <div style="font-size: 12px; color: #64748b; display: flex; gap: 14px; align-items: center; flex-wrap: wrap;">
                <span style="background: #fefce8; color: #a16207; border: 1px solid #fef08a; padding: 2px 8px; border-radius: 4px; font-weight: 600;">⭐ 今日 {stars_today}</span>
                <span>★ {stars_total} stars</span>
                <span>⑂ {forks} forks</span>
            </div>
        </div>
        ''')
    html.append('</div></div>')
    
    # Hacker News section
    html.append('<div>')
    html.append('<div style="display: flex; justify-content: space-between; align-items: baseline; border-bottom: 1px solid #e2e8f0; padding-bottom: 8px; margin-bottom: 14px;"><h2 style="margin: 0; font-size: 16px; font-weight: 700; color: #0f172a;">🔥 Hacker News 科技前沿与深度讨论</h2><span style="font-size: 12px; color: #64748b;">按社区关注与热度排序</span></div>')
    html.append('<div style="display: flex; flex-direction: column; gap: 10px;">')
    for i, it in enumerate(hn_items, 1):
        title = it.get("title", "")
        url = it.get("url", "#")
        hn_url = it.get("hn_url", "#")
        points = f"{it.get('points', 0):,}"
        comments = f"{it.get('comments_count', 0):,}"
        domain = it.get("domain", "news.ycombinator.com")
        topic = it.get("topic", "Tech")
        
        html.append(f'''
        <div style="border: 1px solid #e2e8f0; border-radius: 6px; padding: 14px 16px; background: #ffffff; transition: box-shadow 0.15s ease;">
            <div style="display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 6px;">
                <div style="display: flex; align-items: baseline; gap: 8px;">
                    <span style="font-family: ui-monospace, SFMono-Regular, monospace; font-size: 13px; font-weight: 700; color: #64748b;">#{i}</span>
                    <a href="{url}" target="_blank" style="font-size: 14.5px; font-weight: 600; color: #0f172a; text-decoration: none; line-height: 1.4;">{escape(title)}</a>
                </div>
                <span style="font-size: 11px; background: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 4px; white-space: nowrap;">{topic}</span>
            </div>
            <div style="font-size: 12px; color: #64748b; display: flex; gap: 14px; align-items: center; flex-wrap: wrap;">
                <span style="color: #64748b;">🌐 {domain}</span>
                <span style="background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; padding: 1px 7px; border-radius: 4px; font-weight: 600;">🔥 {points} pts</span>
                <a href="{hn_url}" target="_blank" style="color: #4f46e5; text-decoration: none; font-weight: 500;">💬 {comments} 条热议 →</a>
            </div>
        </div>
        ''')
    html.append('</div></div>')
    
    html.append(f'<div style="margin-top: 28px; padding-top: 14px; border-top: 1px solid #e2e8f0; font-size: 12px; color: #94a3b8; text-align: center;">由 TechPulse 自动化生成于 {digest_data.get("generated_at", "")} ｜ 每日北京时间 08:30 更新</div>')
    html.append('</div>')
    return "\n".join(html)

def generate_rss_xml(history_digests, config):
    """Generates a valid RSS 2.0 XML without duplicate xmlns attributes."""
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
    """Renders a complete, aesthetic HTML page for either index.html or archive/*.html."""
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
        link_bg = "background: #f1f5f9; font-weight: 600; color: #0284c7;" if is_curr else "color: #475569;"
        archive_links.append(f'<li style="margin-bottom: 4px;"><a href="{target_href}" style="display: block; padding: 6px 10px; border-radius: 4px; text-decoration: none; font-size: 12.5px; {link_bg}">📅 {d_str} - {escape(hl)}...</a></li>')
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
        body {{ background: #f8fafc; color: #0f172a; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.5; padding: 16px; }}
        .container {{ max-width: 1040px; margin: 0 auto; }}
        .top-nav {{ display: flex; justify-content: space-between; align-items: center; padding: 12px 20px; background: #ffffff; border-radius: 6px; border: 1px solid #e2e8f0; margin-bottom: 20px; flex-wrap: wrap; gap: 12px; }}
        .brand {{ display: flex; align-items: center; gap: 8px; font-weight: 700; font-size: 16px; color: #0f172a; text-decoration: none; }}
        .nav-actions {{ display: flex; gap: 8px; align-items: center; }}
        .btn {{ display: inline-flex; align-items: center; gap: 5px; padding: 6px 12px; border-radius: 4px; font-size: 12.5px; font-weight: 600; text-decoration: none; cursor: pointer; border: 1px solid transparent; transition: all 0.15s ease; }}
        .btn-rss {{ background: #ea580c; color: #ffffff; }}
        .btn-rss:hover {{ background: #c2410c; }}
        .btn-outline {{ border-color: #cbd5e1; background: #ffffff; color: #334155; }}
        .btn-outline:hover {{ background: #f1f5f9; }}
        .main-layout {{ display: grid; grid-template-columns: 1fr 270px; gap: 20px; }}
        @media (max-width: 820px) {{ .main-layout {{ grid-template-columns: 1fr; }} }}
        .feed-container {{ background: #ffffff; border-radius: 6px; border: 1px solid #e2e8f0; padding: 24px; }}
        .sidebar {{ display: flex; flex-direction: column; gap: 16px; }}
        .side-card {{ background: #ffffff; border-radius: 6px; border: 1px solid #e2e8f0; padding: 16px; }}
        .side-title {{ font-size: 13px; font-weight: 700; color: #0f172a; margin-bottom: 10px; text-transform: uppercase; letter-spacing: 0.3px; display: flex; align-items: center; gap: 6px; }}
        .copy-toast {{ display: none; position: fixed; bottom: 24px; right: 24px; background: #0f172a; color: #f8fafc; padding: 10px 18px; border-radius: 6px; font-size: 13px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); z-index: 99; }}
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
                    <p style="font-size: 12.5px; color: #64748b; margin-bottom: 10px; line-height: 1.5;">支持 NetNewsWire, Reeder, Follow, Feedly 等现代阅读器，每日早晨 08:30 自动拉取更新。</p>
                    <input type="text" id="rssUrl" readonly value="{rss_rel_url}" style="width: 100%; padding: 6px 10px; font-size: 12px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 4px; color: #334155; margin-bottom: 8px;">
                    <button class="btn btn-outline" style="width: 100%; justify-content: center;" onclick="copyRssLink()">点击一键复制链接</button>
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
    
    # 1. Save archive json and md
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
        
    # 2. Collect history digests from archive folder
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
    
    # 3. Generate RSS XML
    feed_filename = config.get("rss", {}).get("feed_filename", "feed.xml")
    xml_content = generate_rss_xml(history_digests, config)
    feed_path = out_dir / feed_filename
    with open(feed_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
        
    rss_alias_path = out_dir / "rss.xml"
    with open(rss_alias_path, "w", encoding="utf-8") as f:
        f.write(xml_content)
            
    # 4. Generate Web Index
    web_content = render_web_page(digest_data, history_digests, config, is_archive=False)
    index_path = out_dir / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(web_content)
        
    # 5. Generate Archive HTML pages
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
