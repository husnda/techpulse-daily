import os
import json
from pathlib import Path

try:
    import yaml
except ImportError:
    try:
        from ruamel.yaml import YAML
        _yaml_loader = YAML(typ='safe')
        class _YamlWrapper:
            @staticmethod
            def safe_load(stream):
                return _yaml_loader.load(stream)
            @staticmethod
            def dump(data, stream=None):
                if stream:
                    _yaml_loader.dump(data, stream)
                else:
                    from io import StringIO
                    s = StringIO()
                    _yaml_loader.dump(data, s)
                    return s.getvalue()
        yaml = _YamlWrapper()
    except ImportError:
        yaml = None

DEFAULT_CONFIG = {
    "app": {
        "title": "TechPulse Daily",
        "tagline": "GitHub Trending & Hacker News 每日精选早报",
        "language": "zh-CN",
        "output_dir": "outputs"
    },
    "github": {
        "enabled": True,
        "max_items": 12,
        "languages": [],  # Empty means all languages. e.g. ["python", "rust", "go"]
        "min_stars_today": 30
    },
    "hackernews": {
        "enabled": True,
        "max_items": 12,
        "min_points": 80,
        "time_range_hours": 24
    },
    "rss": {
        "enabled": True,
        "feed_title": "TechPulse Daily | GitHub Trending & Hacker News 精选",
        "feed_description": "每日聚合 GitHub Daily Trending 开源项目与 Hacker News 高分深度技术讨论",
        "feed_link": "https://github.com",
        "feed_filename": "feed.xml",
        "max_feed_items": 30
    },
    "ai_summary": {
        "enabled": False,
        "provider": "openai",  # "openai", "deepseek", "ollama", "custom"
        "api_base": "https://api.openai.com/v1",
        "api_key": "",
        "model": "gpt-4o-mini",
        "temperature": 0.3
    },
    "notifications": {
        "feishu": {
            "enabled": False,
            "webhook_url": ""
        },
        "telegram": {
            "enabled": False,
            "bot_token": "",
            "chat_id": ""
        },
        "wecom": {
            "enabled": False,
            "webhook_url": ""
        },
        "dingtalk": {
            "enabled": False,
            "webhook_url": "",
            "secret": ""
        },
        "bark": {
            "enabled": False,
            "device_key": "",
            "server_url": "https://api.day.app"
        },
        "email": {
            "enabled": False,
            "smtp_host": "smtp.qq.com",
            "smtp_port": 465,
            "use_ssl": True,
            "sender_email": "",
            "sender_password": "",
            "receiver_emails": []
        }
    }
}

def _deep_merge(source, destination):
    for key, value in source.items():
        if isinstance(value, dict) and isinstance(destination.get(key), dict):
            _deep_merge(value, destination[key])
        else:
            destination[key] = value
    return destination

def load_config(config_path="config.yaml"):
    base_dir = Path(__file__).resolve().parent.parent
    path = Path(config_path)
    if not path.is_absolute():
        path = base_dir / path

    config = json.loads(json.dumps(DEFAULT_CONFIG))

    # Try YAML first, then JSON
    if path.exists():
        try:
            with open(path, "r", encoding="utf-8") as f:
                if yaml and (path.suffix in (".yaml", ".yml")):
                    user_cfg = yaml.safe_load(f) or {}
                else:
                    user_cfg = json.load(f) or {}
            config = _deep_merge(user_cfg, config)
        except Exception as e:
            print(f"[Warning] Failed to parse {path}: {e}. Using default config.")
    else:
        json_path = path.with_suffix(".json")
        if json_path.exists():
            try:
                with open(json_path, "r", encoding="utf-8") as f:
                    user_cfg = json.load(f) or {}
                config = _deep_merge(user_cfg, config)
            except Exception as e:
                print(f"[Warning] Failed to parse {json_path}: {e}.")

    # Environment variable overrides
    if os.getenv("FEISHU_WEBHOOK"):
        config["notifications"]["feishu"]["enabled"] = True
        config["notifications"]["feishu"]["webhook_url"] = os.getenv("FEISHU_WEBHOOK")
        
    if os.getenv("TELEGRAM_BOT_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"):
        config["notifications"]["telegram"]["enabled"] = True
        config["notifications"]["telegram"]["bot_token"] = os.getenv("TELEGRAM_BOT_TOKEN")
        config["notifications"]["telegram"]["chat_id"] = os.getenv("TELEGRAM_CHAT_ID")
        
    if os.getenv("WECOM_WEBHOOK"):
        config["notifications"]["wecom"]["enabled"] = True
        config["notifications"]["wecom"]["webhook_url"] = os.getenv("WECOM_WEBHOOK")

    if os.getenv("DINGTALK_WEBHOOK"):
        config["notifications"]["dingtalk"]["enabled"] = True
        config["notifications"]["dingtalk"]["webhook_url"] = os.getenv("DINGTALK_WEBHOOK")
        if os.getenv("DINGTALK_SECRET"):
            config["notifications"]["dingtalk"]["secret"] = os.getenv("DINGTALK_SECRET")

    if os.getenv("BARK_DEVICE_KEY"):
        config["notifications"]["bark"]["enabled"] = True
        config["notifications"]["bark"]["device_key"] = os.getenv("BARK_DEVICE_KEY")

    if os.getenv("OPENAI_API_KEY"):
        config["ai_summary"]["enabled"] = True
        config["ai_summary"]["api_key"] = os.getenv("OPENAI_API_KEY")
    if os.getenv("OPENAI_API_BASE"):
        config["ai_summary"]["api_base"] = os.getenv("OPENAI_API_BASE")
    if os.getenv("AI_MODEL"):
        config["ai_summary"]["model"] = os.getenv("AI_MODEL")

    return config
