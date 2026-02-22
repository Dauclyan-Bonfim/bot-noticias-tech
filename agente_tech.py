import feedparser
import requests
from deep_translator import GoogleTranslator

TELEGRAM_TOKEN = "8446631368:AAGJ4r2Uv_nwCM1-eKWHpqp6-Tk_JTAiN5k"
CHAT_ID = "6254368463"

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

def send_message(text: str) -> None:
    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "disable_web_page_preview": True
    }
    requests.post(url, json=payload, timeout=30)

def traduzir_ptbr(texto: str) -> str:
    try:
        return GoogleTranslator(source="auto", target="pt").translate(texto)
    except Exception:
        return texto

def main():
    items = []

    for feed_url in RSS_FEEDS:
        feed = feedparser.parse(feed_url)
        for entry in feed.entries[:10]:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            if title and link:
                items.append((title, link))

    if not items:
        send_message("Hoje não consegui puxar notícias. Tenta novamente mais tarde.")
        return

    message = "📰 Tech + Games do Dia (PT-BR):\n\n"

    for i, (title, link) in enumerate(items[:15], start=1):
        titulo_pt = traduzir_ptbr(title)
        message += f"{i}) {titulo_pt}\n{link}\n\n"

    send_message(message)

if __name__ == "__main__":
    main()