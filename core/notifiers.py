import json
import urllib.request
import urllib.parse
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import Header
import logging
import time
import hmac
import hashlib
import base64

logger = logging.getLogger("TechPulse.Notifiers")

def send_feishu_card(webhook_url, digest_data):
    date_str = digest_data.get("date", "")
    top_hl = digest_data.get("top_highlight", "")
    gh_items = digest_data.get("github_items", [])[:5]
    hn_items = digest_data.get("hn_items", [])[:5]
    ai_overview = digest_data.get("ai_overview")
    
    elements = []
    
    if ai_overview:
        elements.append({
            "tag": "div",
            "text": {
                "tag": "lark_md",
                "content": f"**🧠 今日风向速览：**\n{ai_overview}"
            }
        })
        elements.append({"tag": "hr"})
        
    # GitHub section
    gh_lines = ["**🚀 GitHub 今日高星开源：**"]
    for i, it in enumerate(gh_items, 1):
        stars = f"+{it.get('stars_today', 0):,}"
        gh_lines.append(f"{i}. [{it['full_name']}]({it['url']}) `[{it.get('language', 'Dev')}]` ⭐{stars}\n> {it.get('description', '')[:60]}")
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "\n".join(gh_lines)
        }
    })
    elements.append({"tag": "hr"})
    
    # HN section
    hn_lines = ["**🔥 Hacker News 深度讨论：**"]
    for i, it in enumerate(hn_items, 1):
        hn_lines.append(f"{i}. [{it['title']}]({it['url']})\n> 🔥 {it['points']} pts | 💬 [{it['comments_count']} 评论]({it['hn_url']})")
    elements.append({
        "tag": "div",
        "text": {
            "tag": "lark_md",
            "content": "\n".join(hn_lines)
        }
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
    with urllib.request.urlopen(req, timeout=10) as resp:
        return resp.read().decode("utf-8")

def send_telegram(bot_token, chat_id, digest_data):
    date_str = digest_data.get("date", "")
    gh_items = digest_data.get("github_items", [])[:6]
    hn_items = digest_data.get("hn_items", [])[:6]
    ai_overview = digest_data.get("ai_overview")
    
    lines = [f"<b>🛰️ TechPulse Daily 技术早报 ({date_str})</b>\n"]
    if ai_overview:
        lines.append(f"<b>🧠 今日风向速览：</b>\n<i>{ai_overview}</i>\n")
        
    lines.append("<b>🚀 GitHub Trending 开源热点：</b>")
    for i, it in enumerate(gh_items, 1):
        stars = f"+{it.get('stars_today', 0):,}"
        lines.append(f"{i}. <a href=\"{it['url']}\">{it['full_name']}</a> ({it.get('language', 'Code')}) ⭐ {stars}")
        
    lines.append("\n<b>🔥 Hacker News 极客深度讨论：</b>")
    for i, it in enumerate(hn_items, 1):
        lines.append(f"{i}. <a href=\"{it['url']}\">{it['title']}</a> (🔥 {it['points']} pts / <a href=\"{it['hn_url']}\">{it['comments_count']} 评</a>)")
        
    text = "\n".join(lines)
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        return resp.read().decode("utf-8")

def send_wecom(webhook_url, digest_data):
    date_str = digest_data.get("date", "")
    gh_items = digest_data.get("github_items", [])[:5]
    hn_items = digest_data.get("hn_items", [])[:5]
    
    lines = [f"### 🛰️ TechPulse Daily 技术早报 ({date_str})\n"]
    lines.append("**🚀 GitHub 今日热门：**")
    for i, it in enumerate(gh_items, 1):
        lines.append(f"{i}. [{it['full_name']}]({it['url']}) (`{it.get('language', 'Code')}`) ⭐+{it.get('stars_today', 0)}")
    lines.append("\n**🔥 Hacker News 热帖：**")
    for i, it in enumerate(hn_items, 1):
        lines.append(f"{i}. [{it['title']}]({it['url']}) (🔥{it['points']} / 💬[{it['comments_count']}评]({it['hn_url']}))")
        
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
    gh_items = digest_data.get("github_items", [])[:5]
    hn_items = digest_data.get("hn_items", [])[:5]
    
    lines = [f"### 🛰️ TechPulse Daily 技术早报 ({date_str})\n"]
    lines.append("**🚀 GitHub 今日热门：**")
    for i, it in enumerate(gh_items, 1):
        lines.append(f"- [{it['full_name']}]({it['url']}) ⭐+{it.get('stars_today', 0)}")
    lines.append("\n**🔥 Hacker News 讨论：**")
    for i, it in enumerate(hn_items, 1):
        lines.append(f"- [{it['title']}]({it['url']}) (🔥{it['points']} / 💬[{it['comments_count']}评]({it['hn_url']}))")
        
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
    url = f"{server_url.rstrip('/')}/{device_key}/{urllib.parse.quote(title)}/{urllib.parse.quote(body)}?group=TechPulse"
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
    """Dispatches notifications across all enabled channels."""
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
