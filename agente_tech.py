import os
import time
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
# HYPE KEYWORDS
# ==============================
HYPE_KEYWORDS = {
    "gta": 10,
    "rockstar": 8,
    "elden ring": 7,
    "witcher": 7,
    "cyberpunk": 6,
    "steam sale": 9,
    "steam": 5,
    "playstation": 6,
    "ps5": 6,
    "xbox": 5,
    "nintendo": 5,
    "rtx": 7,
    "nvidia": 7,
    "amd": 6,
    "intel": 5,
    "openai": 8,
    "chatgpt": 7,
    "gpt": 6,
    "ai": 3,
    "ransomware": 7,
    "zero-day": 8,
    "cve-": 7,
}

HYPE_ALERT_THRESHOLD = 10

# ==============================
# TELEGRAM (COM DIVISÃO)
# ==============================
def send_message(text: str) -> None:
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise ValueError("Secrets não configurados.")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    MAX_LEN = 3500

    lines = text.split("\n")
    chunks = []
    current = ""

    for line in lines:
        if len(current) + len(line) + 1 > MAX_LEN:
            chunks.append(current.strip())
            current = line + "\n"
        else:
            current += line + "\n"

    if current.strip():
        chunks.append(current.strip())

    for part in chunks:
        payload = {
            "chat_id": CHAT_ID,
            "text": part,
            "parse_mode": "HTML",
            "disable_web_page_preview": True
        }
        r = requests.post(url, json=payload, timeout=30)
        r.raise_for_status()
        time.sleep(1)

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

    if any(site in source_lower for site in ["ign", "kotaku", "gamespot", "pc gamer"]):
        return "🎮 Games"

    if any(word in title_lower for word in ["openai", "chatgpt", "gpt", "ai"]):
        return "🤖 IA"

    if any(word in title_lower for word in ["rtx", "gpu", "cpu", "nvidia", "amd", "intel"]):
        return "🖥 Hardware"

    if any(word in title_lower for word in ["hack", "breach", "malware", "ransomware", "zero-day", "cve-"]):
        return "🔐 Segurança"

    if any(word in title_lower for word in ["iphone", "android", "samsung"]):
        return "📱 Mobile"

    return "🧠 Tech Geral"

# ==============================
# HYPE SCORE
# ==============================
def hype_score(title: str) -> int:
    t = title.lower()
    score = 0
    for kw, weight in HYPE_KEYWORDS.items():
        if kw in t:
            score += weight
    return score

def entry_timestamp(entry) -> int:
    tp = getattr(entry, "published_parsed", None)
    if tp:
        try:
            return int(time.mktime(tp))
        except:
            pass
    return 0

# ==============================
# MAIN
# ==============================
def main():
    grouped = defaultdict(list)
    all_items = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        source_name = feed.feed.get("title", "Fonte")

        for entry in feed.entries[:10]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()

            if not title or not link:
                continue

            score = hype_score(title)
            ts = entry_timestamp(entry)
            category = categorize(title, source_name)

            item = {
                "title": title,
                "link": link,
                "score": score,
                "ts": ts
            }

            grouped[category].append(item)
            all_items.append(item)

    if not all_items:
        send_message("Hoje não consegui puxar notícias.")
        return

    # Ordena por hype + data
    all_items_sorted = sorted(all_items, key=lambda x: (-x["score"], -x["ts"]))

    top3 = all_items_sorted[:3]
    top3_links = {it["link"] for it in top3}

    # ALERTA DE HYPE
    hype_items = [it for it in all_items if it["score"] >= HYPE_ALERT_THRESHOLD]
    if hype_items:
        hype_items = sorted(hype_items, key=lambda x: (-x["score"], -x["ts"]))
        alert_msg = "<b>🚨 ALERTA DE HYPE</b>\n\n"
        for it in hype_items[:6]:
            titulo_pt = traduzir_ptbr(it["title"])
            alert_msg += f"• {titulo_pt}\n{it['link']}\n\n"
        send_message(alert_msg)

    # MENSAGEM PRINCIPAL
    message = "<b>📰 Tech + Games do Dia (PT-BR)</b>\n\n"

    message += "<b>🔥 TOP 3 DO DIA</b>\n"
    for i, it in enumerate(top3, start=1):
        titulo_pt = traduzir_ptbr(it["title"])
        message += f"{i}) {titulo_pt}\n{it['link']}\n\n"

    order = ["🎮 Games", "🤖 IA", "🖥 Hardware", "🔐 Segurança", "📱 Mobile", "🧠 Tech Geral"]

    for category in order:
        items = [it for it in grouped.get(category, []) if it["link"] not in top3_links]
        if not items:
            continue

        message += f"<b>{category}</b>\n"
        for it in items[:5]:
            titulo_pt = traduzir_ptbr(it["title"])
            message += f"• {titulo_pt}\n{it['link']}\n\n"

    send_message(message)

if __name__ == "__main__":
    main()
