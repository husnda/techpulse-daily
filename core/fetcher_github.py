import urllib.request
import re
import html
import time
import logging

logger = logging.getLogger("TechPulse.GitHub")

def clean_int(val_str):
    if not val_str:
        return 0
    clean = re.sub(r'[^0-9]', '', str(val_str))
    return int(clean) if clean else 0

def infer_topic(name, desc, lang):
    text = f"{name} {desc} {lang}".lower()
    if any(k in text for k in ["llm", "gpt", "agent", "prompt", "diffusion", "rag", "transformer", "deepseek", "openai", "claude", "embedding", "model"]):
        return "AI / LLM"
    if any(k in text for k in ["docker", "kubernetes", "k8s", "linux", "kernel", "os", "system", "c++", "rust", "database", "redis", "postgres"]):
        return "Systems / Infra"
    if any(k in text for k in ["react", "vue", "nextjs", "frontend", "css", "tailwind", "ui", "web", "html", "svelte"]):
        return "Web / Frontend"
    if any(k in text for k in ["security", "vulnerability", "exploit", "cve", "auth", "crypto", "hack"]):
        return "Security"
    if any(k in text for k in ["cli", "terminal", "tool", "workflow", "automation", "devops", "git"]):
        return "Dev Tools"
    return "Open Source"

def fetch_trending_page(language=None, timeout=20):
    url = "https://github.com/trending"
    if language:
        url = f"https://github.com/trending/{language}?since=daily"
    else:
        url = f"https://github.com/trending?since=daily"

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8"
    }

    req = urllib.request.Request(url, headers=headers)
    
    # Retry up to 3 times
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                if resp.status == 200:
                    return resp.read().decode('utf-8', errors='ignore')
        except Exception as e:
            logger.warning(f"GitHub fetch attempt {attempt} failed: {e}")
            if attempt < 3:
                time.sleep(2 * attempt)
            else:
                logger.error(f"Failed to fetch GitHub trending ({url}) after 3 attempts.")
                return None
    return None

def parse_trending_html(html_content):
    if not html_content:
        return []
    
    articles = re.findall(r'<article class="Box-row[^"]*".*?</article>', html_content, re.DOTALL)
    results = []
    
    for art in articles:
        # Repo name & owner
        repo_m = re.search(r'<h2[^>]*>.*?href="/([^/\s]+/[^/\s"]+)"', art, re.DOTALL)
        if not repo_m:
            continue
        full_name = repo_m.group(1).strip()
        parts = full_name.split("/")
        owner = parts[0] if len(parts) > 0 else ""
        name = parts[1] if len(parts) > 1 else full_name
        
        # Description
        desc_m = re.search(r'<p class="col-9[^"]*"[^>]*>(.*?)</p>', art, re.DOTALL)
        raw_desc = desc_m.group(1).strip() if desc_m else ""
        desc = html.unescape(re.sub(r'<[^>]+>', '', raw_desc)).strip()
        
        # Language
        lang_m = re.search(r'itemprop="programmingLanguage">([^<]+)<', art)
        lang = lang_m.group(1).strip() if lang_m else "N/A"
        
        # Total Stars
        stars_m = re.search(r'href="[^"]+/stargazers"[^>]*>.*?([0-9,]+)\s*</a>', art, re.DOTALL)
        stars_total_str = stars_m.group(1).strip() if stars_m else "0"
        stars_total = clean_int(stars_total_str)
        
        # Forks
        forks_m = re.search(r'href="[^"]+/forks"[^>]*>.*?([0-9,]+)\s*</a>', art, re.DOTALL)
        forks_str = forks_m.group(1).strip() if forks_m else "0"
        forks = clean_int(forks_str)
        
        # Stars today
        stars_today_m = re.search(r'([0-9,]+)\s+stars today', art)
        stars_today_str = stars_today_m.group(1).strip() if stars_today_m else "0"
        stars_today = clean_int(stars_today_str)
        
        topic = infer_topic(full_name, desc, lang)
        
        results.append({
            "source": "github",
            "name": name,
            "owner": owner,
            "full_name": full_name,
            "url": f"https://github.com/{full_name}",
            "description": desc,
            "language": lang,
            "stars_today": stars_today,
            "stars_total": stars_total,
            "forks": forks,
            "topic": topic
        })
        
    return results

def get_github_trending(config):
    gh_cfg = config.get("github", {})
    if not gh_cfg.get("enabled", True):
        return []
    
    max_items = gh_cfg.get("max_items", 12)
    min_stars = gh_cfg.get("min_stars_today", 30)
    languages = gh_cfg.get("languages", [])
    
    all_repos = []
    seen = set()
    
    # 1. Fetch overall trending
    html_content = fetch_trending_page(None)
    items = parse_trending_html(html_content)
    for it in items:
        if it["full_name"] not in seen:
            seen.add(it["full_name"])
            all_repos.append(it)
            
    # 2. Fetch specific languages if configured
    for lang in languages:
        time.sleep(1)
        lang_html = fetch_trending_page(lang)
        lang_items = parse_trending_html(lang_html)
        for it in lang_items:
            if it["full_name"] not in seen:
                seen.add(it["full_name"])
                all_repos.append(it)
                
    # Filter by min_stars_today and sort by stars_today descending
    filtered = [r for r in all_repos if r["stars_today"] >= min_stars or r["stars_today"] == 0]
    # In case stars_today wasn't parsed or low, fallback to keeping top
    if not filtered:
        filtered = all_repos
    filtered.sort(key=lambda x: (x["stars_today"], x["stars_total"]), reverse=True)
    
    return filtered[:max_items]
