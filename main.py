#!/usr/bin/env python3
import sys
import os
import time
import argparse
import logging
import datetime
from pathlib import Path
import http.server
import socketserver

from core.config import load_config
from core.fetcher_github import get_github_trending
from core.fetcher_hackernews import get_hackernews_top
from core.data_processor import process_daily_digest, format_markdown_digest
from core.rss_generator import save_rss_and_web
from core.notifiers import dispatch_notifications

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%H:%M:%S"
)
logger = logging.getLogger("TechPulse.Main")

def run_pipeline(config, dry_run=False):
    logger.info("==================================================")
    logger.info("🚀 启动 TechPulse Daily 技术早报数据聚合管道...")
    logger.info("==================================================")
    
    # 1. Fetch GitHub Trending
    logger.info("[1/4] 抓取 GitHub Daily Trending 开源项目...")
    gh_items = get_github_trending(config)
    logger.info(f"      成功获取 {len(gh_items)} 个优质开源项目。")
    
    # 2. Fetch Hacker News
    logger.info("[2/4] 抓取 Hacker News 极客深度科技讨论...")
    hn_items = get_hackernews_top(config)
    logger.info(f"      成功获取 {len(hn_items)} 篇高赞热门讨论。")
    
    if not gh_items and not hn_items:
        logger.error("未获取到任何数据，请检查网络连接或数据源配置。")
        return None
        
    # 3. Process & Summarize
    logger.info("[3/4] 进行数据去重、深度提炼与内容结构化...")
    digest_data = process_daily_digest(gh_items, hn_items, config)
    
    # 4. Generate RSS & Web pages
    logger.info("[4/4] 生成 RSS 2.0 订阅源、HTML Web 页面与 Markdown 归档...")
    saved_files = save_rss_and_web(digest_data, config)
    for k, v in saved_files.items():
        logger.info(f"      - {k}: {v}")
        
    # 5. Dispatch notifications
    if dry_run:
        logger.info("[Dry Run] 已开启演练模式，跳过推送通道发送。")
    else:
        logger.info("检查并派发推送通知...")
        results = dispatch_notifications(digest_data, config)
        if results:
            for ch, status in results.items():
                logger.info(f"      - 通道 [{ch}]: {status}")
        else:
            logger.info("      当前未启用任何第三方推送渠道（可在 config.yaml 中配置飞书/TG/邮件等）。")
            
    logger.info("==================================================")
    logger.info("✅ 今日技术早报聚合与生成全部顺利完成！")
    logger.info("==================================================")
    return digest_data

def serve_rss(output_dir, port=8080):
    out_path = Path(output_dir).resolve()
    if not out_path.exists():
        out_path.mkdir(parents=True, exist_ok=True)
        
    os.chdir(str(out_path))
    handler = http.server.SimpleHTTPRequestHandler
    
    print(f"\n🛰️  TechPulse 本地 RSS & Web 订阅服务已启动！")
    print(f"📡  RSS 订阅源地址:  http://127.0.0.1:{port}/feed.xml")
    print(f"🌐  网页阅读版入口:  http://127.0.0.1:{port}/index.html")
    print(f"⏹️  按 Ctrl+C 可停止服务\n")
    
    with socketserver.TCPServer(("", port), handler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n服务已停止。")

def daemon_loop(config, target_time_str="08:30"):
    logger.info(f"启动定时守护模式，将在每天北京时间 {target_time_str} 自动执行...")
    target_hour, target_minute = map(int, target_time_str.split(":"))
    last_run_date = None
    
    while True:
        now = datetime.datetime.now()
        current_date = now.date()
        
        if now.hour == target_hour and now.minute == target_minute and last_run_date != current_date:
            logger.info(f"到达预定时间 {target_time_str}，开始执行今日抓取任务...")
            try:
                run_pipeline(config, dry_run=False)
                last_run_date = current_date
            except Exception as e:
                logger.error(f"任务执行异常: {e}", exc_info=True)
                
        time.sleep(30)

def test_notifications(config):
    logger.info("正在向已启用的渠道发送测试消息...")
    fake_digest = {
        "date": datetime.date.today().isoformat(),
        "generated_at": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "top_highlight": "TechPulse 连接测试消息",
        "ai_overview": "这是一条通道连通性测试消息。当你收到这条消息时，说明你的通知配置已完全就绪！",
        "github_items": [{
            "name": "TechPulse",
            "full_name": "example/tech-pulse",
            "url": "https://github.com",
            "description": "每日自动从 GitHub Trending 与 Hacker News 抓取并精选技术热点",
            "language": "Python",
            "stars_today": 999,
            "stars_total": 8888,
            "forks": 666,
            "topic": "AI / Tools"
        }],
        "hn_items": [{
            "id": "12345",
            "title": "Show HN: TechPulse Daily Digest Service",
            "url": "https://news.ycombinator.com",
            "hn_url": "https://news.ycombinator.com",
            "points": 500,
            "comments_count": 120,
            "domain": "news.ycombinator.com",
            "topic": "Show HN"
        }]
    }
    results = dispatch_notifications(fake_digest, config)
    for ch, res in results.items():
        logger.info(f"通道 [{ch}]: {res}")
    if not results:
        logger.warning("当前没有检测到任何已启用的通知渠道。请检查 config.yaml 中的 enabled: true。")

def main():
    parser = argparse.ArgumentParser(description="TechPulse Daily - GitHub Trending & Hacker News 每日精选早报")
    parser.add_argument("--config", default="config.yaml", help="配置文件路径 (默认: config.yaml)")
    parser.add_argument("--run", action="store_true", help="立即运行一次完整的抓取、生成与推送流程")
    parser.add_argument("--dry-run", action="store_true", help="演练模式：抓取并生成文件，但不发送外部通知")
    parser.add_argument("--serve", action="store_true", help="启动本地 HTTP 服务器供 RSS 阅读器订阅")
    parser.add_argument("--port", type=int, default=8080, help="本地 HTTP 服务端口 (默认: 8080)")
    parser.add_argument("--daemon", action="store_true", help="常驻守护模式，每日定时自动运行")
    parser.add_argument("--time", default="08:30", help="守护模式下的每日触发时间 (默认: 08:30)")
    parser.add_argument("--test-notify", action="store_true", help="测试已配置的通知渠道连通性")
    
    args = parser.parse_args()
    config = load_config(args.config)
    
    if args.serve:
        out_dir = config.get("app", {}).get("output_dir", "outputs")
        serve_rss(out_dir, port=args.port)
    elif args.daemon:
        daemon_loop(config, target_time_str=args.time)
    elif args.test_notify:
        test_notifications(config)
    else:
        # Default action is run
        dry = args.dry_run
        run_pipeline(config, dry_run=dry)

if __name__ == "__main__":
    main()
