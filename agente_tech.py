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
# HYPE SETTINGS
# ==============================
# Quanto maior o peso, mais "hype" a palavra gera
HYPE_KEYWORDS = {
    # Games / lançamentos
    "gta": 10,
    "rockstar": 8,
    "elder scrolls": 7,
    "witcher": 7,
    "fromsoftware": 7,
    "elden ring": 7,
    "cyberpunk": 6,
    "red dead": 6,
    "trailer": 5,
    "release": 5,
    "launch": 5,
    "beta": 4,
    "leak": 6,
    "rumor": 4,

    # Plataformas / stores
    "steam": 5,
    "steam sale": 9,
    "epic": 4,
    "game pass": 6,
    "playstation": 5,
    "ps5": 6,
    "xbox": 5,
    "nintendo": 5,
    "switch": 5,

    # Hardware
    "nvidia": 7,
    "amd": 6,
    "intel": 5,
    "rtx": 7,
    "radeon": 5,
    "ryzen": 5,
    "driver": 4,

    # IA / Big Tech
    "openai": 8,
    "chatgpt": 7,
    "gpt": 6,
    "anthropic": 6,
    "deepmind": 6,
    "gemini": 6,
    "ai": 3,  # genérico (baixo)
    "artificial intelligence": 5,

    # Segurança (quando é grande)
    "zero-day": 8,
    "0-day": 8,
    "cve-": 7,
    "ransomware": 7,
    "breach": 6,
}

# Threshold para disparar alerta separado
HYPE_ALERT_THRESHOLD = 10

# ==============================
# TELEGRAM
# ==============================
def send_message(text: str) -> None:
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise ValueError("Secrets não configurados: TELEGRAM_TOKEN / TELEGRAM_CHAT_ID.")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    payload = {
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True
    }
    r = requests.post(url, json=payload, timeout=30)
    r.raise_for_status()

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

    # Se for site de games
    if any(site in source_lower for site in ["ign", "kotaku", "gamespot", "pc gamer"]):
        return "🎮 Games"

    # IA
    if any(word in title_lower for word in ["openai", "chatgpt", "gpt", "anthropic", "deepmind", "gemini", "ai", "artificial intelligence"]):
        return "🤖 IA"

    # Hardware
    if any(word in title_lower for word in ["rtx", "gpu", "cpu", "nvidia", "amd", "intel", "ryzen", "radeon", "driver"]):
        return "🖥 Hardware"

    # Segurança
    if any(word in title_lower for word in ["hack", "breach", "malware", "ransomware", "security", "zero-day", "0-day", "cve-"]):
        return "🔐 Segurança"

    # Mobile
    if any(word in title_lower for word in ["iphone", "android", "samsung", "mobile", "app"]):
        return "📱 Mobile"

    return "🧠 Tech Geral"

# ==============================
# HYPE SCORE
# ==============================
def hype_score(title: str) -> int:
    t = title.lower()
    score = 0
    for kw, w in HYPE_KEYWORDS.items():
        if kw in t:
            score += w
    return score

def entry_timestamp(entry) -> int:
    # tenta pegar published_parsed / updated_parsed
    for attr in ("published_parsed", "updated_parsed"):
        tp = getattr(entry, attr, None)
        if tp:
            try:
                return int(time.mktime(tp))
            except Exception:
                pass
    return 0

# ==============================
# MESSAGE BUILDERS
# ==============================
def build_hype_alert(items):
    # pega só os que bateram threshold
    alert_items = [it for it in items if it["score"] >= HYPE_ALERT_THRESHOLD]
    if not alert_items:
        return None

    alert_items.sort(key=lambda x: (-x["score"], -x["ts"]))
    lines = ["<b>🚨 ALERTA DE HYPE</b>\n"]
    for it in alert_items[:6]:
        titulo_pt = traduzir_ptbr(it["title"])
        lines.append(f"• {titulo_pt}\n{it['link']}\n")
    return "\n".join(lines).strip()

def build_daily_message(grouped, top3, top3_links):
    order = ["🎮 Games", "🤖 IA", "🖥 Hardware", "🔐 Segurança", "📱 Mobile", "🧠 Tech Geral"]

    msg = ["<b>📰 Tech + Games do Dia (PT-BR)</b>\n"]

    # TOP 3
    msg.append("<b>🔥 TOP 3 DO DIA</b>")
    for i, it in enumerate(top3, start=1):
        titulo_pt = traduzir_ptbr(it["title"])
        # Se quiser, dá pra mostrar score: f"(Hype {it['score']})"
        msg.append(f"{i}) {titulo_pt}\n{it['link']}\n")
    msg.append("")

    # Categorias (evita duplicar o top3)
    for cat in order:
        items = grouped.get(cat, [])
        # remove top3
        items = [it for it in items if it["link"] not in top3_links]
        if not items:
            continue

        msg.append(f"<b>{cat}</b>")
        for it in items[:5]:
            titulo_pt = traduzir_ptbr(it["title"])
            msg.append(f"• {titulo_pt}\n{it['link']}\n")
        msg.append("")

    return "\n".join(msg).strip()

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

            cat = categorize(title, source_name)
            score = hype_score(title)
            ts = entry_timestamp(entry)

            item = {"title": title, "link": link, "score": score, "ts": ts, "source": source_name}
            grouped[cat].append(item)
            all_items.append(item)

    if not all_items:
        send_message("Hoje não consegui puxar notícias.")
        return

    # TOP 3 = maior hype score; desempate por mais recente
    all_items_sorted = sorted(all_items, key=lambda x: (-x["score"], -x["ts"]))
    top3 = all_items_sorted[:3]
    top3_links = {it["link"] for it in top3}

    # 1) ALERTA DE HYPE (se existir)
    alert_msg = build_hype_alert(all_items)
    if alert_msg:
        send_message(alert_msg)

    # 2) RESUMO DO DIA
    daily_msg = build_daily_message(grouped, top3, top3_links)
    send_message(daily_msg)

if __name__ == "__main__":
    main()
