#!/usr/bin/env python3
"""Personal news digest bot: fetch RSS sources, filter by keywords, send to Telegram."""

import json
import os
import re
import sys
import time
from datetime import datetime, timezone

import feedparser
import requests

SENT_URLS_FILE = "sent_urls.json"
MAX_ARTICLES = 10
FETCH_TIMEOUT = 15

SOURCES = [
    ("Hacker News", "https://hnrss.org/frontpage"),
    ("arXiv cs.CR", "https://export.arxiv.org/rss/cs.CR"),
    ("arXiv cs.AI", "https://export.arxiv.org/rss/cs.AI"),
    ("GitHub Trending Python", "https://mshibanami.github.io/GitHubTrendingRSS/daily/python.xml"),
    ("Latam Fintech Hub", "https://latamfintechhub.com/feed"),
    ("Krebs on Security", "https://krebsonsecurity.com/feed/"),
    ("TLDR Tech", "https://tldr.tech/rss"),
]

KEYWORDS = [
    "fintech", "security", "fraud", "pci", "compliance", "startup",
    "llm", "ai", "machine learning", "payment", "latam", "vulnerability",
    "breach", "automation", "saas",
]


def log(msg: str) -> None:
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{timestamp}] {msg}", flush=True)


def load_sent_urls() -> set:
    if not os.path.exists(SENT_URLS_FILE):
        return set()
    try:
        with open(SENT_URLS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    except (json.JSONDecodeError, OSError) as e:
        log(f"WARNING: could not read {SENT_URLS_FILE}: {e}")
        return set()


def save_sent_urls(urls: set) -> None:
    with open(SENT_URLS_FILE, "w", encoding="utf-8") as f:
        json.dump(sorted(urls), f, indent=2)


def fetch_source(name: str, url: str):
    try:
        response = requests.get(
            url,
            timeout=FETCH_TIMEOUT,
            headers={"User-Agent": "Mozilla/5.0 (compatible; NewsDigestBot/1.0)"},
        )
        response.raise_for_status()
        parsed = feedparser.parse(response.content)
        if parsed.bozo and not parsed.entries:
            log(f"WARNING: feed parse issue for {name}: {parsed.bozo_exception}")
            return []
        log(f"Fetched {len(parsed.entries)} entries from {name}")
        return parsed.entries
    except requests.exceptions.RequestException as e:
        log(f"WARNING: failed to fetch {name} ({url}): {e}")
        return []
    except Exception as e:
        log(f"WARNING: unexpected error fetching {name} ({url}): {e}")
        return []


def matches_keywords(entry) -> bool:
    title = entry.get("title", "") or ""
    summary = entry.get("summary", "") or entry.get("description", "") or ""
    text = f"{title} {summary}".lower()
    return any(keyword.lower() in text for keyword in KEYWORDS)


def get_entry_date(entry) -> str:
    for field in ("published", "updated"):
        if entry.get(field):
            return entry.get(field)
    return "fecha desconocida"


def get_entry_url(entry) -> str:
    return entry.get("link", "") or ""


def escape_markdown_v2(text: str) -> str:
    escape_chars = r"_*[]()~`>#+-=|{}.!"
    return re.sub(f"([{re.escape(escape_chars)}])", r"\\\1", text)


def collect_articles(sent_urls: set):
    articles = []
    seen_urls = set()

    for source_name, source_url in SOURCES:
        entries = fetch_source(source_name, source_url)
        for entry in entries:
            url = get_entry_url(entry)
            if not url:
                continue
            if url in seen_urls or url in sent_urls:
                continue
            if not matches_keywords(entry):
                continue

            seen_urls.add(url)
            articles.append(
                {
                    "title": entry.get("title", "Sin título"),
                    "url": url,
                    "source": source_name,
                    "date": get_entry_date(entry),
                }
            )

            if len(articles) >= MAX_ARTICLES:
                return articles

    return articles


def build_message(articles) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    header = f"📡 *Digest — {escape_markdown_v2(today)}*"

    if not articles:
        return "Sin novedades en este ciclo\\."

    lines = [header, ""]
    for i, article in enumerate(articles, start=1):
        title = escape_markdown_v2(article["title"])
        source = escape_markdown_v2(article["source"])
        date = escape_markdown_v2(article["date"])
        raw_url = article["url"]
        link_text = escape_markdown_v2(raw_url)
        link_url = raw_url.replace("\\", "\\\\").replace(")", "\\)")
        lines.append(f"{i}\\. *{title}*")
        lines.append(f"   {source} · {date}")
        lines.append(f"   🔗 [{link_text}]({link_url})")
        lines.append("")

    return "\n".join(lines).strip()


def send_telegram_message(message: str) -> None:
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not token or not chat_id:
        log("ERROR: TELEGRAM_BOT_TOKEN or TELEGRAM_CHAT_ID not set")
        sys.exit(1)

    api_url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "MarkdownV2",
        "disable_web_page_preview": False,
    }

    try:
        response = requests.post(api_url, json=payload, timeout=FETCH_TIMEOUT)
        response.raise_for_status()
        log("Message sent to Telegram successfully")
    except requests.exceptions.RequestException as e:
        log(f"ERROR: failed to send Telegram message: {e}")
        if e.response is not None:
            log(f"Telegram API response: {e.response.text}")
        sys.exit(1)


def main() -> None:
    log("Starting news digest run")

    sent_urls = load_sent_urls()
    log(f"Loaded {len(sent_urls)} previously sent URLs")

    articles = collect_articles(sent_urls)
    log(f"Collected {len(articles)} new matching articles")

    message = build_message(articles)
    send_telegram_message(message)

    if articles:
        sent_urls.update(article["url"] for article in articles)
        save_sent_urls(sent_urls)
        log(f"Updated {SENT_URLS_FILE} with {len(articles)} new URLs")

    log("Digest run finished")


if __name__ == "__main__":
    main()
