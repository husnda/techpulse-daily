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

def generate_html_content(digest_data):
    """Generates rich, self-contained HTML for RSS content:encoded and Web reader."""
    date_str = digest_data.get("date", "")
    ai_overview = digest_data.get("ai_overview")
    gh_items = digest_data.get("github_items", [])
    hn_items = digest_data.get("hn_items", [])
    stats = digest_data.get("stats", {})
    
    html = []
    html.append('<div style="font-family: -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, Helvetica, Arial, sans-serif; max-width: 800px; margin: 0 auto; color: #1f2937; line-height: 1.6;">')
    
    # Header card
    html.append(f'''
    <div style="background: linear-gradient(135deg, #1e293b, #0f172a); color: #f8fafc; padding: 24px; border-radius: 12px; margin-bottom: 24px;">
        <h1 style="margin: 0 0 8px 0; font-size: 24px; font-weight: 700; color: #38bdf8;">🛰️ TechPulse Daily 技术早报</h1>
        <div style="font-size: 14px; color: #94a3b8;">📅 日期：{date_str} &nbsp;|&nbsp; ⚡ GitHub 开源热点 & Hacker News 极客精选</div>
    </div>
    ''')
    
    # AI Overview if present
    if ai_overview:
        clean_ai = ai_overview.replace("\n", "<br>")
        html.append(f'''
        <div style="background: #f0fdf4; border-left: 4px solid #22c55e; padding: 16px 20px; border-radius: 0 8px 8px 0; margin-bottom: 24px;">
            <h3 style="margin: 0 0 8px 0; color: #15803d; font-size: 16px;">🧠 今日风向速览 (AI 提炼)</h3>
            <div style="font-size: 14px; color: #166534; line-height: 1.7;">{clean_ai}</div>
        </div>
        ''')
        
    # GitHub section
    html.append('<h2 style="font-size: 18px; color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin: 24px 0 16px 0;">🚀 GitHub Trending 热门开源项目</h2>')
    html.append('<div style="display: flex; flex-direction: column; gap: 12px;">')
    for i, it in enumerate(gh_items, 1):
        stars_today = f"+{it.get('stars_today', 0):,}" if it.get('stars_today') else "Trending"
        stars_total = f"{it.get('stars_total', 0):,}" if it.get('stars_total') else "0"
        topic = it.get("topic", "Open Source")
        lang = it.get("language", "General")
        desc = it.get("description", "无项目描述")
        url = it.get("url", "#")
        full_name = it.get("full_name", "")
        
        html.append(f'''
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; background: #ffffff;">
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
                <a href="{url}" target="_blank" style="font-size: 16px; font-weight: 600; color: #0284c7; text-decoration: none;">{i}. {full_name}</a>
                <span style="font-size: 12px; background: #e0f2fe; color: #0369a1; padding: 2px 8px; border-radius: 12px; font-weight: 500;">{topic}</span>
            </div>
            <p style="margin: 0 0 10px 0; font-size: 14px; color: #475569;">{escape(desc)}</p>
            <div style="font-size: 12px; color: #64748b; display: flex; gap: 16px; flex-wrap: wrap;">
                <span>💻 <strong>{lang}</strong></span>
                <span>⭐ 今日 <strong>{stars_today}</strong></span>
                <span>🌟 总星 <strong>{stars_total}</strong></span>
            </div>
        </div>
        ''')
    html.append('</div>')
    
    # Hacker News section
    html.append('<h2 style="font-size: 18px; color: #0f172a; border-bottom: 2px solid #e2e8f0; padding-bottom: 8px; margin: 32px 0 16px 0;">🔥 Hacker News 科技前沿与深度讨论</h2>')
    html.append('<div style="display: flex; flex-direction: column; gap: 12px;">')
    for i, it in enumerate(hn_items, 1):
        title = it.get("title", "")
        url = it.get("url", "#")
        hn_url = it.get("hn_url", "#")
        points = it.get("points", 0)
        comments = it.get("comments_count", 0)
        domain = it.get("domain", "news.ycombinator.com")
        topic = it.get("topic", "Tech")
        
        html.append(f'''
        <div style="border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 18px; background: #ffffff;">
            <div style="display: flex; justify-content: space-between; align-items: baseline; margin-bottom: 6px;">
                <a href="{url}" target="_blank" style="font-size: 15px; font-weight: 600; color: #0f172a; text-decoration: none;">{i}. {escape(title)}</a>
                <span style="font-size: 11px; background: #f1f5f9; color: #475569; padding: 2px 8px; border-radius: 12px;">{topic}</span>
            </div>
            <div style="font-size: 12px; color: #64748b; display: flex; gap: 14px; flex-wrap: wrap;">
                <span>🌐 <span style="color: #64748b;">{domain}</span></span>
                <span>🔥 <strong style="color: #ea580c;">{points}</strong> points</span>
                <span>💬 <a href="{hn_url}" target="_blank" style="color: #6366f1; text-decoration: underline;">{comments} 条讨论</a></span>
            </div>
        </div>
        ''')
    html.append('</div>')
    
    html.append(f'<div style="margin-top: 24px; padding-top: 12px; border-top: 1px solid #f1f5f9; font-size: 12px; color: #94a3b8; text-align: center;">由 TechPulse 自动化生成于 {digest_data.get("generated_at", "")}</div>')
    html.append('</div>')
    return "\n".join(html)

def generate_rss_xml(history_digests, config):
    ET.register_namespace("atom", "http://www.w3.org/2005/Atom")
    ET.register_namespace("content", "http://purl.org/rss/1.0/modules/content/")
    """Generates a valid RSS 2.0 XML with full HTML encoded content."""
    rss_cfg = config.get("rss", {})
    feed_title = rss_cfg.get("feed_title", "TechPulse Daily")
    feed_desc = rss_cfg.get("feed_description", "Daily Tech Radar")
    feed_link = rss_cfg.get("feed_link", "https://github.com")
    
    rss = ET.Element("rss", {
        "version": "2.0",
        "xmlns:atom": "http://www.w3.org/2005/Atom",
        "xmlns:content": "http://purl.org/rss/1.0/modules/content/"
    })
    channel = ET.SubElement(rss, "channel")
    
    ET.SubElement(channel, "title").text = feed_title
    ET.SubElement(channel, "link").text = feed_link
    ET.SubElement(channel, "description").text = feed_desc
    ET.SubElement(channel, "language").text = "zh-cn"
    ET.SubElement(channel, "lastBuildDate").text = format_rfc822()
    ET.SubElement(channel, "generator").text = "TechPulse Daily Digest Generator"
    
    # Self atom link
    atom_link = ET.SubElement(channel, "{http://www.w3.org/2005/Atom}link", {
        "href": f"{feed_link.rstrip('/')}/feed.xml",
        "rel": "self",
        "type": "application/rss+xml"
    })
    
    for digest in history_digests:
        date_str = digest.get("date", "")
        top_hl = digest.get("top_highlight", "")
        title = f"【{date_str}】技术早报：{top_hl}"
        guid_str = f"techpulse-{date_str}"
        link_url = f"{feed_link.rstrip('/')}#{date_str}"
        
        item = ET.SubElement(channel, "item")
        ET.SubElement(item, "title").text = title
        ET.SubElement(item, "link").text = link_url
        ET.SubElement(item, "guid", {"isPermaLink": "false"}).text = guid_str
        
        # Parse pubDate from date_str or generated_at
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
            dt = dt.replace(hour=8, minute=0, second=0, tzinfo=datetime.timezone.utc)
            pub_date_str = format_rfc822(dt)
        except Exception:
            pub_date_str = format_rfc822()
            
        ET.SubElement(item, "pubDate").text = pub_date_str
        
        # Rich HTML description / content:encoded
        html_body = generate_html_content(digest)
        ET.SubElement(item, "description").text = html_body
        
    xml_bytes = ET.tostring(rss, encoding="utf-8", xml_declaration=True)
    return xml_bytes.decode("utf-8")

def generate_web_index(history_digests, config):
    """Generates an aesthetic standalone index.html for web viewing / GitHub Pages."""
    latest = history_digests[0] if history_digests else {}
    body_html = generate_html_content(latest) if latest else "<p>暂无早报数据</p>"
    feed_filename = config.get("rss", {}).get("feed_filename", "feed.xml")
    
    archive_links = []
    for d in history_digests[:15]:
        d_str = d.get("date", "")
        hl = d.get("top_highlight", "技术要闻")[:25]
        archive_links.append(f'<li style="margin-bottom: 8px;"><a href="archive/{d_str}.html" style="color: #0284c7; text-decoration: none;">📅 {d_str} - {escape(hl)}...</a></li>')
    archive_html = "".join(archive_links)
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TechPulse Daily | GitHub Trending & Hacker News 每日精选早报</title>
    <link rel="alternate" type="application/rss+xml" title="TechPulse RSS Feed" href="{feed_filename}">
    <style>
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{ background: #f8fafc; color: #1e293b; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif; line-height: 1.6; padding: 20px; }}
        .container {{ max-width: 960px; margin: 0 auto; }}
        .top-nav {{ display: flex; justify-content: space-between; align-items: center; padding: 16px 20px; background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; margin-bottom: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); flex-wrap: wrap; gap: 12px; }}
        .brand {{ display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 18px; color: #0f172a; }}
        .nav-actions {{ display: flex; gap: 10px; }}
        .btn {{ display: inline-flex; align-items: center; gap: 6px; padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600; text-decoration: none; cursor: pointer; border: 1px solid transparent; transition: all 0.15s ease; }}
        .btn-rss {{ background: #ea580c; color: #ffffff; }}
        .btn-rss:hover {{ background: #c2410c; }}
        .btn-outline {{ border-color: #cbd5e1; background: #ffffff; color: #475569; }}
        .btn-outline:hover {{ background: #f1f5f9; }}
        .main-layout {{ display: grid; grid-template-columns: 1fr 260px; gap: 24px; }}
        @media (max-width: 768px) {{ .main-layout {{ grid-template-columns: 1fr; }} }}
        .feed-container {{ background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 24px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
        .sidebar {{ display: flex; flex-direction: column; gap: 20px; }}
        .side-card {{ background: #ffffff; border-radius: 12px; border: 1px solid #e2e8f0; padding: 20px; box-shadow: 0 1px 3px rgba(0,0,0,0.04); }}
        .side-title {{ font-size: 14px; font-weight: 700; color: #0f172a; margin-bottom: 12px; text-transform: uppercase; letter-spacing: 0.5px; }}
        .copy-toast {{ display: none; position: fixed; bottom: 20px; right: 20px; background: #0f172a; color: #f8fafc; padding: 10px 16px; border-radius: 8px; font-size: 13px; box-shadow: 0 4px 12px rgba(0,0,0,0.15); }}
    </style>
</head>
<body>
    <div class="container">
        <header class="top-nav">
            <div class="brand">
                <span>🛰️</span>
                <span>TechPulse Daily</span>
            </div>
            <div class="nav-actions">
                <button class="btn btn-rss" onclick="copyRssLink()">📡 复制 RSS 订阅地址</button>
                <a href="{feed_filename}" class="btn btn-outline" target="_blank">查看 RSS 源</a>
            </div>
        </header>
        <div class="main-layout">
            <main class="feed-container">
                {body_html}
            </main>
            <aside class="sidebar">
                <div class="side-card">
                    <h3 class="side-title">📡 RSS 订阅指南</h3>
                    <p style="font-size: 13px; color: #64748b; margin-bottom: 10px;">复制本站 RSS 地址，即可添加到 NetNewsWire, Reeder, Follow, Feedly 或微信阅读器中每日自动收取。</p>
                    <input type="text" id="rssUrl" readonly value="{feed_filename}" style="width: 100%; padding: 6px 10px; font-size: 12px; background: #f8fafc; border: 1px solid #cbd5e1; border-radius: 6px; color: #334155; margin-bottom: 8px;">
                </div>
                <div class="side-card">
                    <h3 class="side-title">🗂 往期早报归档</h3>
                    <ul style="list-style: none; font-size: 13px;">
                        {archive_html}
                    </ul>
                </div>
            </aside>
        </div>
    </div>
    <div id="toast" class="copy-toast">✅ RSS 地址已复制到剪贴板！</div>
    <script>
        function copyRssLink() {{
            const fullUrl = new URL("{feed_filename}", window.location.href).href;
            navigator.clipboard.writeText(fullUrl).then(() => {{
                const toast = document.getElementById("toast");
                toast.style.display = "block";
                setTimeout(() => {{ toast.style.display = "none"; }}, 2500);
            }}).catch(() => {{
                alert("RSS 地址: " + fullUrl);
            }});
        }}
        window.addEventListener("DOMContentLoaded", () => {{
            document.getElementById("rssUrl").value = new URL("{feed_filename}", window.location.href).href;
        }});
    </script>
</body>
</html>'''
    return html

def save_rss_and_web(digest_data, config):
    """Saves feed.xml, rss.xml, latest_digest.md, archive, and index.html into outputs/"""
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
        
    # Latest markdown copy
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
        
    # Also create rss.xml as alias if feed_filename is different
    if feed_filename != "rss.xml":
        with open(out_dir / "rss.xml", "w", encoding="utf-8") as f:
            f.write(xml_content)
            
    # 4. Generate Web Index
    web_content = generate_web_index(history_digests, config)
    index_path = out_dir / "index.html"
    with open(index_path, "w", encoding="utf-8") as f:
        f.write(web_content)
        
    return {
        "feed_xml": str(feed_path),
        "rss_xml": str(out_dir / "rss.xml"),
        "index_html": str(index_path),
        "latest_md": str(latest_md),
        "archive_md": str(md_archive)
    }
