import os
import time
import html
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
# LIMITES (1) — TOTAL DIÁRIO
# ==============================
MAX_TOTAL_DAILY = 15          # total geral (inclui Top 3)
TOP3_COUNT = 3                # top 3 fixo
MAX_AFTER_TOP3 = MAX_TOTAL_DAILY - TOP3_COUNT

# Limite por categoria (para distribuir bem)
CATEGORY_CAPS = {
    "🎮 Games": 4,
    "🤖 IA": 3,
    "🖥 Hardware": 3,
    "🔐 Segurança": 2,
    "📱 Mobile": 2,
    "🧠 Tech Geral": 2,
}

CATEGORY_ORDER = ["🎮 Games", "🤖 IA", "🖥 Hardware", "🔐 Segurança", "📱 Mobile", "🧠 Tech Geral"]

# ==============================
# TELEGRAM (com divisão)
# ==============================
def send_message(text: str) -> None:
    if not TELEGRAM_TOKEN or not CHAT_ID:
        raise ValueError("Secrets não configurados: TELEGRAM_TOKEN / TELEGRAM_CHAT_ID.")

    url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
    MAX_LEN = 3500  # margem

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
# UTIL (6) — mensagem compacta
# ==============================
def clean_url(url: str) -> str:
    # corta parâmetros gigantes (?ftag=...)
    return url.split("?", 1)[0].strip()

def link_line(title: str, url: str) -> str:
    # escape para não quebrar HTML do Telegram
    safe_title = html.escape(title, quote=False)
    safe_url = html.escape(url, quote=True)
    return f'• <a href="{safe_url}">{safe_title}</a>'

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

    if any(word in title_lower for word in ["rtx", "gpu", "cpu", "nvidia", "amd", "intel", "ryzen"]):
        return "🖥 Hardware"

    if any(word in title_lower for word in ["hack", "breach", "malware", "ransomware", "zero-day", "0-day", "cve-"]):
        return "🔐 Segurança"

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
    for attr in ("published_parsed", "updated_parsed"):
        tp = getattr(entry, attr, None)
        if tp:
            try:
                return int(time.mktime(tp))
            except Exception:
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

            link = clean_url(link)
            score = hype_score(title)
            ts = entry_timestamp(entry)
            category = categorize(title, source_name)

            item = {"title": title, "link": link, "score": score, "ts": ts, "category": category}
            grouped[category].append(item)
            all_items.append(item)

    if not all_items:
        send_message("Hoje não consegui puxar notícias.")
        return

    # Ordenação geral (top 3)
    all_sorted = sorted(all_items, key=lambda x: (-x["score"], -x["ts"]))
    top3 = all_sorted[:TOP3_COUNT]
    top3_links = {it["link"] for it in top3}

    # ========== ALERTA DE HYPE (compacto e curto) ==========
    hype_hits = [it for it in all_items if it["score"] >= HYPE_ALERT_THRESHOLD]
    if hype_hits:
        hype_hits.sort(key=lambda x: (-x["score"], -x["ts"]))
        alert_lines = ["<b>🚨 ALERTA DE HYPE</b>\n"]
        for it in hype_hits[:3]:  # menor para não virar spam
            titulo_pt = traduzir_ptbr(it["title"])
            alert_lines.append(link_line(titulo_pt, it["link"]))
        send_message("\n".join(alert_lines).strip())

    # ========== SELEÇÃO LIMITADA (1) ==========
    selected_by_cat = defaultdict(list)
    remaining = MAX_AFTER_TOP3

    for cat in CATEGORY_ORDER:
        if remaining <= 0:
            break

        items = [it for it in grouped.get(cat, []) if it["link"] not in top3_links]
        # ordenar dentro da categoria por hype e recência
        items.sort(key=lambda x: (-x["score"], -x["ts"]))

        cap = CATEGORY_CAPS.get(cat, 2)
        take = min(cap, remaining, len(items))
        if take > 0:
            selected_by_cat[cat].extend(items[:take])
            remaining -= take

    # ========== MENSAGEM PRINCIPAL (compacta) ==========
    lines = ["<b>📰 Tech + Games do Dia (PT-BR)</b>\n"]

    # TOP 3 com links embutidos
    lines.append("<b>🔥 TOP 3 DO DIA</b>")
    for i, it in enumerate(top3, start=1):
        titulo_pt = traduzir_ptbr(it["title"])
        # 1) • <a href="...">Título</a>
        lines.append(f"{i}) {link_line(titulo_pt, it['link'])}")
    lines.append("")

    # Categorias
    for cat in CATEGORY_ORDER:
        items = selected_by_cat.get(cat, [])
        if not items:
            continue
        lines.append(f"<b>{cat}</b>")
        for it in items:
            titulo_pt = traduzir_ptbr(it["title"])
            lines.append(link_line(titulo_pt, it["link"]))
        lines.append("")

    send_message("\n".join(lines).strip())


if __name__ == "__main__":
    main()
