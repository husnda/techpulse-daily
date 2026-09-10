import urllib.request
import json
import time
import re
import logging
from urllib.parse import urlparse

logger = logging.getLogger("TechPulse.HackerNews")

def extract_domain(url):
    try:
        if not url:
            return "news.ycombinator.com"
        netloc = urlparse(url).netloc
        netloc = re.sub(r'^www\.', '', netloc)
        return netloc or "news.ycombinator.com"
    except Exception:
        return "news.ycombinator.com"

def infer_hn_topic(title, url):
    text = f"{title} {url}".lower()
    if title.startswith("Show HN:"):
        return "Show HN"
    if title.startswith("Ask HN:"):
        return "Ask HN"
    if any(k in text for k in ["ai", "llm", "gpt", "deepseek", "claude", "openai", "model", "transformer", "neural", "anthropic", "machine learning"]):
        return "AI & ML"
    if any(k in text for k in ["linux", "kernel", "rust", "c++", "database", "postgres", "compiler", "cpu", "memory", "systems"]):
        return "Systems & Infra"
    if any(k in text for k in ["security", "vulnerability", "malware", "hack", "cve", "breach", "exploit", "privacy"]):
        return "Security & Privacy"
    if any(k in text for k in ["apple", "google", "microsoft", "amazon", "meta", "nvidia", "intel", "shopify"]):
        return "Tech Giants"
    if any(k in text for k in ["startup", "acquisition", "funding", "ipo", "layoff", "remote", "career"]):
        return "Business & Work"
    return "Tech & Science"

def fetch_hn_algolia(time_range_hours=24, min_points=80, hits_per_page=40):
    now = int(time.time())
    start_time = now - (time_range_hours * 3600)
    
    # 1. Fetch stories with score > min_points in last 24h
    url_filtered = f"https://hn.algolia.com/api/v1/search?tags=story&numericFilters=created_at_i>{start_time},points>{min_points}&hitsPerPage={hits_per_page}"
    # 2. Fetch front_page stories as backup/supplement
    url_front = f"https://hn.algolia.com/api/v1/search?tags=front_page&hitsPerPage=30"
    
    headers = {"User-Agent": "Mozilla/5.0 (TechPulse Daily Digest)"}
    
    stories_map = {}
    
    for api_url in [url_filtered, url_front]:
        try:
            req = urllib.request.Request(api_url, headers=headers)
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for hit in data.get("hits", []):
                    story_id = hit.get("objectID")
                    if not story_id:
                        continue
                    title = hit.get("title") or "Untitled"
                    url = hit.get("url") or f"https://news.ycombinator.com/item?id={story_id}"
                    points = hit.get("points") or 0
                    comments = hit.get("num_comments") or 0
                    author = hit.get("author") or "unknown"
                    created_at_i = hit.get("created_at_i") or now
                    
                    stories_map[story_id] = {
                        "source": "hackernews",
                        "id": story_id,
                        "title": title,
                        "url": url,
                        "hn_url": f"https://news.ycombinator.com/item?id={story_id}",
                        "domain": extract_domain(url),
                        "points": points,
                        "comments_count": comments,
                        "author": author,
                        "created_at_i": created_at_i,
                        "topic": infer_hn_topic(title, url)
                    }
        except Exception as e:
            logger.warning(f"Failed to query Algolia API ({api_url}): {e}")
            
    return list(stories_map.values())

def fetch_hn_firebase_fallback(limit=30):
    """Fallback if Algolia is unreachable"""
    logger.info("Using Firebase fallback for Hacker News...")
    headers = {"User-Agent": "Mozilla/5.0 (TechPulse)"}
    try:
        req = urllib.request.Request("https://hacker-news.firebaseio.com/v0/topstories.json", headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            top_ids = json.loads(resp.read().decode('utf-8'))[:limit]
            
        results = []
        for item_id in top_ids[:15]:
            try:
                item_req = urllib.request.Request(f"https://hacker-news.firebaseio.com/v0/item/{item_id}.json", headers=headers)
                with urllib.request.urlopen(item_req, timeout=5) as item_resp:
                    item_data = json.loads(item_resp.read().decode('utf-8'))
                    if not item_data or item_data.get("type") != "story":
                        continue
                    url = item_data.get("url") or f"https://news.ycombinator.com/item?id={item_id}"
                    title = item_data.get("title") or "Untitled"
                    results.append({
                        "source": "hackernews",
                        "id": str(item_id),
                        "title": title,
                        "url": url,
                        "hn_url": f"https://news.ycombinator.com/item?id={item_id}",
                        "domain": extract_domain(url),
                        "points": item_data.get("score") or 0,
                        "comments_count": item_data.get("descendants") or 0,
                        "author": item_data.get("by") or "unknown",
                        "created_at_i": item_data.get("time") or int(time.time()),
                        "topic": infer_hn_topic(title, url)
                    })
            except Exception:
                continue
        return results
    except Exception as e:
        logger.error(f"Firebase fallback also failed: {e}")
        return []

def get_hackernews_top(config):
    hn_cfg = config.get("hackernews", {})
    if not hn_cfg.get("enabled", True):
        return []
        
    max_items = hn_cfg.get("max_items", 12)
    min_points = hn_cfg.get("min_points", 80)
    time_range = hn_cfg.get("time_range_hours", 24)
    
    stories = fetch_hn_algolia(time_range_hours=time_range, min_points=min_points)
    if not stories:
        stories = fetch_hn_firebase_fallback(limit=30)
        
    # Deduplicate stories by normalized title
    deduped = []
    seen_titles = set()
    for s in stories:
        norm_title = re.sub(r'[^a-zA-Z0-9]', '', s["title"].lower())
        if norm_title in seen_titles:
            continue
        seen_titles.add(norm_title)
        deduped.append(s)
        
    # Sort by engagement score: points + 1.2 * comments
    deduped.sort(key=lambda x: (x["points"] + int(x["comments_count"] * 1.2)), reverse=True)
    return deduped[:max_items]
