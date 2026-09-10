import json
import urllib.request
import urllib.parse
import smtplib
import html
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import logging
import time
import hmac
import hashlib
import base64
import re

logger = logging.getLogger("TechPulse.Notifiers")

def format_inline_markdown(text):
    if not text:
        return ""
    safe = html.escape(text)
    # Convert **bold** to <b>bold</b>
    safe = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", safe)
    # Convert *italic* to <i>italic</i>
    safe = re.sub(r"(?<!\w)\*([^*]+?)\*(?!\w)", r"<i>\1</i>", safe)
    # Convert `code` to <code>code</code>
    safe = re.sub(r"`([^`]+?)`", r"<code>\1</code>", safe)
    return safe

def markdown_to_telegram_html(text):
    """Converts markdown text to clean Telegram-compatible HTML, stripping raw markdown artifacts."""
    if not text:
        return ""
    # Strip code block wrappers
    clean = re.sub(r"^```[a-zA-Z]*\n?", "", text.strip())
    clean = re.sub(r"\n?```$", "", clean)
    
    lines = clean.splitlines()
    output = []
    for l in lines:
        stripped = l.strip()
        if not stripped:
            output.append("")
            continue
        # Strip markdown hr like --- or ***
        if re.match(r"^-{3,}$", stripped) or re.match(r"^\*{3,}$", stripped):
            continue
        # Headers: ### or #### -> <b>Header</b>
        header_m = re.match(r"^(#{1,6})\s+(.+)$", stripped)
        if header_m:
            h_text = header_m.group(2)
            output.append(f"<b>{format_inline_markdown(h_text)}</b>")
            continue
        # Bullet points: * or -
        list_m = re.match(r"^[\*\-+]\s+(.+)$", stripped)
        if list_m:
            item_text = list_m.group(1)
            output.append(f"• {format_inline_markdown(item_text)}")
            continue
        # Blockquotes >
        quote_m = re.match(r"^>\s+(.+)$", stripped)
        if quote_m:
            q_text = quote_m.group(1)
            output.append(f"<i>{format_inline_markdown(q_text)}</i>")
            continue
        output.append(format_inline_markdown(l))
        
    return "\n".join(output).strip()

def send_feishu_card(webhook_url, digest_data):
    date_str = digest_data.get("date", "")
    top_hl = digest_data.get("top_highlight", "")
    gh_items = digest_data.get("github_items", [])[:6]
    hn_items = digest_data.get("hn_items", [])[:6]
    ai_overview = digest_data.get("ai_overview")
    stats = digest_data.get("stats", {})
    
    elements = []
    
    total_stars = f"+{stats.get('total_stars_today', 0):,}"
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": f"📅 **日期**：{date_str}  |  ⚡ **今日Star增速**：⭐ {total_stars}  |  💬 **HN社区热度**：{stats.get('total_hn_comments', 0):,} 条"
        }
    })
    elements.append({"tag": "hr"})
    
    if ai_overview:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**🧠 今日风向速览 (AI 提炼)**\n{ai_overview}"
            }
        })
        elements.append({"tag": "hr"})
        
    # GitHub section
    gh_lines = ["**🚀 GitHub 今日高星开源精选 (基于 README 解读)：**"]
    for i, it in enumerate(gh_items, 1):
        stars = f"+{it.get('stars_today', 0):,}"
        lang = it.get('language', 'Dev')
        ai_txt = it.get('ai_summary') or it.get('description', '暂无描述')
        gh_lines.append(f"{i}. [{it['full_name']}]({it['url']}) `[{lang}]` ⭐ **{stars}**\n> 💡 **核心解读**：{ai_txt}")
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "\n".join(gh_lines)
        }
    })
    elements.append({"tag": "hr"})
    
    # HN section
    hn_lines = ["**🔥 Hacker News 极客深度热议 (基于 原文/热评 提炼)：**"]
    for i, it in enumerate(hn_items, 1):
        domain = it.get('domain', 'news')
        ai_txt = it.get('ai_summary') or '社区深度讨论'
        hn_lines.append(f"{i}. [{it['title']}]({it['url']}) `[{domain}]` (🔥 **{it['points']}** pts / 💬 [{it['comments_count']} 评]({it['hn_url']}))\n> 💡 **深度看点**：{ai_txt}")
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "\n".join(hn_lines)
        }
    })
    elements.append({"tag": "hr"})
    
    elements.append({
        "tag": "action",
        "actions": [
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "🌐 查看在线完整版"},
                "type": "primary",
                "url": "https://husnda.github.io/techpulse-daily/"
            },
            {
                "tag": "button",
                "text": {"tag": "plain_text", "content": "📡 RSS 订阅源"},
                "type": "default",
                "url": "https://husnda.github.io/techpulse-daily/feed.xml"
            }
        ]
    })
    
    card_payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"🛰️ TechPulse Daily 技术早报 ({date_str})"
                },
                "template": "blue"
            },
            "elements": elements
        }
    }
    
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(card_payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=12) as resp:
        return resp.read().decode("utf-8")

def send_telegram(bot_token, chat_id, digest_data):
    bot_token = str(bot_token).strip()
    chat_id = str(chat_id).strip()
    date_str = digest_data.get("date", "")
    gh_items = digest_data.get("github_items", [])[:6]
    hn_items = digest_data.get("hn_items", [])[:6]
    ai_overview = digest_data.get("ai_overview")
    stats = digest_data.get("stats", {})
    
    lines = [
        f"🛰️ <b>TechPulse Daily 技术早报</b> ｜ <code>{date_str}</code>",
        "━━━━━━━━━━━━━━━━━━"
    ]
    
    # 1. Clean rendered AI Overview without raw markdown artifacts
    if ai_overview:
        rendered_ai = markdown_to_telegram_html(ai_overview)
        lines.append(f"🧠 <b>今日风向速览：</b>\n{rendered_ai}\n")
        lines.append("━━━━━━━━━━━━━━━━━━")
        
    # 2. GitHub section with real README-based summaries
    lines.append("🚀 <b>GitHub 今日高星精选 (基于 README 解读)</b>\n")
    for i, it in enumerate(gh_items, 1):
        stars = f"+{it.get('stars_today', 0):,}"
        total = f"{it.get('stars_total', 0):,}"
        safe_name = html.escape(it.get('full_name', ''))
        safe_lang = html.escape(it.get('language', 'Code'))
        safe_topic = html.escape(it.get('topic', 'Dev'))
        
        lines.append(f"<b>{i}. <a href=\"{it['url']}\">{safe_name}</a></b> <code>{safe_lang}</code>")
        lines.append(f"   ⭐ 今日 <b>{stars}</b> ｜ 总星 {total} ｜ 🏷️ <i>{safe_topic}</i>")
        
        ai_sum = it.get('ai_summary')
        if ai_sum:
            safe_ai_sum = html.escape(ai_sum)
            lines.append(f"   💡 <b>核心解读</b>：<i>{safe_ai_sum}</i>")
        elif it.get('description'):
            safe_desc = html.escape(it['description'][:70])
            lines.append(f"   <i>{safe_desc}</i>")
        lines.append("")
        
    lines.append("━━━━━━━━━━━━━━━━━━")
    # 3. Hacker News section with real article/discussion summaries
    lines.append("🔥 <b>Hacker News 深度热议 (基于 原文/热评 解读)</b>\n")
    for i, it in enumerate(hn_items, 1):
        safe_title = html.escape(it.get('title', ''))
        safe_domain = html.escape(it.get('domain', 'news'))
        safe_topic = html.escape(it.get('topic', 'Tech'))
        points = it.get('points', 0)
        comments = it.get('comments_count', 0)
        
        lines.append(f"<b>{i}. <a href=\"{it['url']}\">{safe_title}</a></b> <code>{safe_domain}</code>")
        lines.append(f"   🔥 <b>{points}</b> pts ｜ 💬 <a href=\"{it['hn_url']}\"><b>{comments}</b> 条讨论</a> ｜ 🏷️ <i>{safe_topic}</i>")
        
        ai_sum = it.get('ai_summary')
        if ai_sum:
            safe_ai_sum = html.escape(ai_sum)
            lines.append(f"   💡 <b>深度看点</b>：<i>{safe_ai_sum}</i>")
        lines.append("")
        
    lines.append("━━━━━━━━━━━━━━━━━━")
    lines.append('🌐 <a href="https://husnda.github.io/techpulse-daily/">查看在线完整版</a> ｜ 📡 <a href="https://husnda.github.io/techpulse-daily/feed.xml">RSS 订阅</a>')
    
    html_text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    
    payload_html = {
        "chat_id": chat_id,
        "text": html_text,
        "parse_mode": "HTML",
        "link_preview_options": {"is_disabled": True}
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(payload_html).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        logger.warning(f"Telegram HTML send failed ({err_body}), trying plain text fallback...")
        
        # Clean plain text fallback without HTML tags
        plain_lines = [
            f"🛰️ TechPulse Daily 技术早报 ({date_str})",
            "----------------------------------"
        ]
        if ai_overview:
            clean_plain_ai = re.sub(r"[*#`]", "", ai_overview)
            plain_lines.append(f"今日风向速览：\n{clean_plain_ai}\n")
            plain_lines.append("----------------------------------")
        plain_lines.append("🚀 GitHub 开源热点精选：")
        for i, it in enumerate(gh_items, 1):
            stars = f"+{it.get('stars_today', 0):,}"
            ai_sum = it.get('ai_summary') or it.get('description', '')
            plain_lines.append(f"{i}. {it['full_name']} [{it.get('language', 'Code')}] ⭐{stars}\n   解读: {ai_sum}\n   {it['url']}")
        plain_lines.append("\n🔥 Hacker News 深度讨论精选：")
        for i, it in enumerate(hn_items, 1):
            ai_sum = it.get('ai_summary') or ''
            plain_lines.append(f"{i}. {it['title']} (🔥{it['points']} / 💬{it['comments_count']}评)\n   看点: {ai_sum}\n   {it['url']}")
        plain_lines.append("\n----------------------------------")
        plain_lines.append("完整版: https://husnda.github.io/techpulse-daily/ | RSS: https://husnda.github.io/techpulse-daily/feed.xml")
            
        payload_plain = {
            "chat_id": chat_id,
            "text": "\n".join(plain_lines),
            "link_preview_options": {"is_disabled": True}
        }
        req_plain = urllib.request.Request(
            url,
            data=json.dumps(payload_plain).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        try:
            with urllib.request.urlopen(req_plain, timeout=15) as resp_plain:
                return resp_plain.read().decode("utf-8")
        except urllib.error.HTTPError as e2:
            err2 = e2.read().decode("utf-8", errors="ignore")
            raise Exception(f"Telegram API Error {e2.code}: {err2}")

def send_wecom(webhook_url, digest_data):
    date_str = digest_data.get("date", "")
    gh_items = digest_data.get("github_items", [])[:6]
    hn_items = digest_data.get("hn_items", [])[:6]
    ai_overview = digest_data.get("ai_overview")
    
    lines = [f"### 🛰️ TechPulse Daily 技术早报 ({date_str})\n"]
    if ai_overview:
        lines.append(f"> **今日风向速览**：{ai_overview}\n")
    lines.append("**🚀 GitHub 今日热门开源 (基于 README 解读)：**")
    for i, it in enumerate(gh_items, 1):
        stars = f"+{it.get('stars_today', 0):,}"
        ai_txt = it.get('ai_summary') or it.get('description', '')[:60]
        lines.append(f"{i}. [{it['full_name']}]({it['url']}) (`{it.get('language', 'Code')}`) ⭐ **{stars}**\n> 💡 {ai_txt}")
    lines.append("\n**🔥 Hacker News 深度讨论：**")
    for i, it in enumerate(hn_items, 1):
        ai_txt = it.get('ai_summary') or '社区深度讨论'
        lines.append(f"{i}. [{it['title']}]({it['url']}) (🔥**{it['points']}** / 💬[{it['comments_count']}评]({it['hn_url']}))\n> 💡 {ai_txt}")
    lines.append("\n---")
    lines.append("[🌐 查看在线完整早报](https://husnda.github.io/techpulse-daily/)  |  [📡 RSS 订阅源](https://husnda.github.io/techpulse-daily/feed.xml)")
        
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "content": "\n".join(lines)
        }
    }
    req = urllib.request.Request(
        webhook_url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8")

def send_dingtalk(webhook_url, secret, digest_data):
    url = webhook_url
    if secret:
        timestamp = str(round(time.time() * 1000))
        secret_enc = secret.encode("utf-8")
        string_to_sign = f"{timestamp}\n{secret}"
        string_to_sign_enc = string_to_sign.encode("utf-8")
        hmac_code = hmac.new(secret_enc, string_to_sign_enc, digestmod=hashlib.sha256).digest()
        sign = urllib.parse.quote_plus(base64.b64encode(hmac_code))
        url = f"{webhook_url}&timestamp={timestamp}&sign={sign}"
        
    date_str = digest_data.get("date", "")
    gh_items = digest_data.get("github_items", [])[:6]
    hn_items = digest_data.get("hn_items", [])[:6]
    ai_overview = digest_data.get("ai_overview")
    
    lines = [f"### 🛰️ TechPulse Daily 技术早报 ({date_str})\n"]
    if ai_overview:
        lines.append(f"> **今日风向**：{ai_overview}\n")
    lines.append("**🚀 GitHub 今日热门：**")
    for i, it in enumerate(gh_items, 1):
        stars = f"+{it.get('stars_today', 0):,}"
        ai_txt = it.get('ai_summary') or it.get('description', '')[:60]
        lines.append(f"- [{it['full_name']}]({it['url']}) ⭐**{stars}** (`{it.get('language', 'Code')}`)\n  💡 {ai_txt}")
    lines.append("\n**🔥 Hacker News 讨论：**")
    for i, it in enumerate(hn_items, 1):
        ai_txt = it.get('ai_summary') or ''
        lines.append(f"- [{it['title']}]({it['url']}) (🔥**{it['points']}** / 💬[{it['comments_count']}评]({it['hn_url']}))\n  💡 {ai_txt}")
    lines.append("\n---")
    lines.append("[🌐 查看在线完整早报](https://husnda.github.io/techpulse-daily/)  |  [📡 RSS 订阅源](https://husnda.github.io/techpulse-daily/feed.xml)")
        
    payload = {
        "msgtype": "markdown",
        "markdown": {
            "title": f"TechPulse Daily ({date_str})",
            "text": "\n".join(lines)
        }
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8")

def send_bark(server_url, device_key, digest_data):
    date_str = digest_data.get("date", "")
    top_hl = digest_data.get("top_highlight", "今日技术早报已送达")[:40]
    title = f"🛰️ TechPulse Daily ({date_str})"
    body = f"头条：{top_hl}"
    web_url = "https://husnda.github.io/techpulse-daily/"
    url = f"{server_url.rstrip('/')}/{device_key}/{urllib.parse.quote(title)}/{urllib.parse.quote(body)}?group=TechPulse&url={urllib.parse.quote(web_url)}"
    req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8")

def send_email(email_cfg, digest_data):
    from core.rss_generator import generate_html_content
    from core.data_processor import format_markdown_digest
    
    host = email_cfg.get("smtp_host")
    port = email_cfg.get("smtp_port", 465)
    use_ssl = email_cfg.get("use_ssl", True)
    sender = email_cfg.get("sender_email")
    password = email_cfg.get("sender_password")
    receivers = email_cfg.get("receiver_emails", [])
    
    if not (host and sender and password and receivers):
        logger.warning("Email configuration incomplete, skipping email send.")
        return False
        
    date_str = digest_data.get("date", "")
    subject = f"🛰️ TechPulse Daily 技术早报 ({date_str}) - {digest_data.get('top_highlight', '')[:30]}"
    
    msg = MIMEMultipart("alternative")
    msg["Subject"] = Header(subject, "utf-8")
    msg["From"] = Header(f"TechPulse <{sender}>", "utf-8")
    msg["To"] = Header(", ".join(receivers), "utf-8")
    
    plain_text = format_markdown_digest(digest_data)
    html_text = generate_html_content(digest_data)
    
    msg.attach(MIMEText(plain_text, "plain", "utf-8"))
    msg.attach(MIMEText(html_text, "html", "utf-8"))
    
    if use_ssl:
        server = smtplib.SMTP_SSL(host, port, timeout=15)
    else:
        server = smtplib.SMTP(host, port, timeout=15)
        server.starttls()
        
    server.login(sender, password)
    server.sendmail(sender, receivers, msg.as_string())
    server.quit()
    return True

def dispatch_notifications(digest_data, config):
    notif_cfg = config.get("notifications", {})
    results = {}
    
    # Feishu
    feishu = notif_cfg.get("feishu", {})
    if feishu.get("enabled") and feishu.get("webhook_url"):
        try:
            send_feishu_card(feishu["webhook_url"], digest_data)
            results["feishu"] = "success"
            logger.info("Feishu notification sent successfully.")
        except Exception as e:
            logger.error(f"Feishu notification failed: {e}")
            results["feishu"] = f"failed: {e}"
            
    # Telegram
    tg = notif_cfg.get("telegram", {})
    if tg.get("enabled") and tg.get("bot_token") and tg.get("chat_id"):
        try:
            send_telegram(tg["bot_token"], tg["chat_id"], digest_data)
            results["telegram"] = "success"
            logger.info("Telegram notification sent successfully.")
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")
            results["telegram"] = f"failed: {e}"
            
    # WeCom
    wecom = notif_cfg.get("wecom", {})
    if wecom.get("enabled") and wecom.get("webhook_url"):
        try:
            send_wecom(wecom["webhook_url"], digest_data)
            results["wecom"] = "success"
            logger.info("WeCom notification sent successfully.")
        except Exception as e:
            logger.error(f"WeCom notification failed: {e}")
            results["wecom"] = f"failed: {e}"
            
    # DingTalk
    ding = notif_cfg.get("dingtalk", {})
    if ding.get("enabled") and ding.get("webhook_url"):
        try:
            send_dingtalk(ding["webhook_url"], ding.get("secret", ""), digest_data)
            results["dingtalk"] = "success"
            logger.info("DingTalk notification sent successfully.")
        except Exception as e:
            logger.error(f"DingTalk notification failed: {e}")
            results["dingtalk"] = f"failed: {e}"
            
    # Bark
    bark = notif_cfg.get("bark", {})
    if bark.get("enabled") and bark.get("device_key"):
        try:
            send_bark(bark.get("server_url", "https://api.day.app"), bark["device_key"], digest_data)
            results["bark"] = "success"
            logger.info("Bark notification sent successfully.")
        except Exception as e:
            logger.error(f"Bark notification failed: {e}")
            results["bark"] = f"failed: {e}"
            
    # Email
    email = notif_cfg.get("email", {})
    if email.get("enabled"):
        try:
            send_email(email, digest_data)
            results["email"] = "success"
            logger.info("Email notification sent successfully.")
        except Exception as e:
            logger.error(f"Email notification failed: {e}")
            results["email"] = f"failed: {e}"
            
    return results
