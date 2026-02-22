import os
import feedparser
import requests
from collections import defaultdict
from deep_translator import GoogleTranslator

# ==============================
# CONFIG (GitHub Secrets)
# ==============================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

# ==============================
# RSS FEEDS
# ==============================

RSS_FEEDS = [
    # TECH
    "https://techcrunch.com/feed/",
    "https://www.theverge.com/rss/index.xml",
    "https://www.wired.com/feed/rss",
    "https://www.engadget.com/rss.xml",

    # GAMES
    "https://www.ign.com/rss",
    "https://kotaku.com/rss",
    "https://www.gamespot.com/feeds/news/",
    "https://www.pcgamer.com/rss/",
]

# ==============================
# TELEGRAM
# ==============================

def send_message(text: str) -> None:
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise ValueError("Secrets não configurados.")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }

    response = requests.post(url, json=payload, timeout=30)
    response.raise_for_status()

# ==============================
# TRADUÇÃO
# ==============================

def traduzir_ptbr(texto: str) -> str:
    try:
        return GoogleTranslator(source="auto", target="pt").translate(texto)
    except Exception:
        return texto

# ==============================
# CATEGORIZAÇÃO
# ==============================

def categorize(title: str, source: str) -> str:
    source_lower = source.lower()
    title_lower = title.lower()

    # 🎮 Se for site de games
    if any(site in source_lower for site in ["ign", "kotaku", "gamespot", "pc gamer"]):
        return "🎮 Games"

    # 🤖 IA
    if any(word in title_lower for word in ["ai", "artificial intelligence", "openai", "chatgpt", "gpt"]):
        return "🤖 IA"

    # 🖥 Hardware
    if any(word in title_lower for word in ["rtx", "gpu", "cpu", "nvidia", "amd", "intel", "ryzen"]):
        return "🖥 Hardware"

    # 🔐 Segurança
    if any(word in title_lower for word in ["hack", "breach", "malware", "ransomware", "security"]):
        return "🔐 Segurança"

    # 📱 Mobile
    if any(word in title_lower for word in ["iphone", "android", "samsung", "mobile", "app"]):
        return "📱 Mobile"

    # 🧠 Default Tech
    return "🧠 Tech Geral"

# ==============================
# MAIN
# ==============================

def main():
    grouped = defaultdict(list)

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        source_name = feed.feed.get("title", "Fonte")

        for entry in feed.entries[:10]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()

            if title and link:
                category = categorize(title, source_name)
                grouped[category].append({
                    "title": title,
                    "link": link
                })

    if not grouped:
        send_message("Hoje não consegui puxar notícias.")
        return

    message = "<b>📰 Tech + Games do Dia (PT-BR)</b>\n\n"

    order = ["🎮 Games", "🤖 IA", "🖥 Hardware", "🔐 Segurança", "📱 Mobile", "🧠 Tech Geral"]

    for category in order:
        items = grouped.get(category, [])
        if not items:
            continue

        message += f"<b>{category}</b>\n"

        for item in items[:5]:  # limite por categoria
            titulo_pt = traduzir_ptbr(item["title"])
            message += f"• {titulo_pt}\n{item['link']}\n\n"

    send_message(message)

if __name__ == "__main__":
    main()
