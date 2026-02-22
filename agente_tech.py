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
# (2) FILTRO ANTI-LIXO
# ==============================
# Títulos que contêm esses termos são descartados.
# Ajuste à vontade conforme seu gosto.
BLOCKLIST = [
    # Política / guerra / economia geral
    "trump", "biden", "election", "senate", "congress", "white house",
    "war", "invasion", "ukraine", "gaza", "israel", "palestine",
    "inflation", "interest rate", "fed", "stock market",

    # Celebridades / fofoca
    "kardashian", "taylor swift", "celebrity", "hollywood", "oscars", "grammys",

    # Conteúdos muito fora de tech/games (você pode ampliar)
    "horoscope", "astrology",
]

def is_blocked(title: str) -> bool:
    t = title.lower()
    return any(b in t for b in BLOCKLIST)

# ==============================
# (3) HYPE 2.0
# ==============================
HYPE_KEYWORDS = {
    # Games / lançamentos
    "gta": 10,
    "rockstar": 8,
    "elden ring": 7,
    "witcher": 7,
    "cyberpunk": 6,

    # Stores / plataformas
    "steam sale": 9,
    "steam": 5,
    "game pass": 6,
    "playstation": 6,
    "ps5": 6,
    "xbox": 5,
    "nintendo": 5,
    "switch": 5,

    # Hardware
    "rtx": 7,
    "nvidia": 7,
    "amd": 6,
    "intel": 5,
    "ryzen": 5,
    "radeon": 5,
    "driver": 4,

    # IA / big tech
    "openai": 8,
    "chatgpt": 7,
    "gpt": 6,
    "anthropic": 6,
    "deepmind": 6,
    "gemini": 6,
    "ai": 3,

    # Segurança (quando é grande)
    "zero-day": 8,
    "0-day": 8,
    "cve-": 7,
    "ransomware": 7,
    "breach": 6,
}

# Palavras que aumentam “importância” (oficial/confirmado/etc.)
BOOST_TERMS = {
    "official": 3,
    "confirmed": 4,
    "launch": 3,
    "release": 3,
    "trailer": 3,
    "update": 2,
    "patch": 2,
    "reveal": 2,
    "announced": 3,
    "new": 1,
}

# Palavras que indicam boato/clickbait -> reduz hype
PENALTY_TERMS = {
    "rumor": 3,
    "reportedly": 2,
    "leak": 2,
    "leaked": 2,
    "might": 1,
    "could": 1,
}

# Bônus por fonte (curadoria: a fonte “pesa”)
SOURCE_BONUS = {
    "ign": 3,
    "pc gamer": 3,
    "gamespot": 2,
    "kotaku": 1,
    "the verge": 2,
    "wired": 2,
    "engadget": 1,
    "techcrunch": 1,
}

HYPE_ALERT_THRESHOLD = 12  # mais exigente agora (antes era 10). Ajuste se quiser.

# ==============================
# LIMITES (sem spam)
# ==============================
MAX_TOTAL_DAILY = 15
TOP3_COUNT = 3
MAX_AFTER_TOP3 = MAX_TOTAL_DAILY - TOP3_COUNT

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
# UTIL (compacto)
# ==============================
def clean_url(url: str) -> str:
    return url.split("?", 1)[0].strip()

def link_line(title: str, url: str) -> str:
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

    if any(word in title_lower for word in ["openai", "chatgpt", "gpt", "anthropic", "deepmind", "gemini", "ai"]):
        return "🤖 IA"

    if any(word in title_lower for word in ["rtx", "gpu", "cpu", "nvidia", "amd", "intel", "ryzen", "radeon", "driver"]):
        return "🖥 Hardware"

    if any(word in title_lower for word in ["hack", "breach", "malware", "ransomware", "zero-day", "0-day", "cve-"]):
        return "🔐 Segurança"

    if any(word in title_lower for word in ["iphone", "android", "samsung", "mobile", "app"]):
        return "📱 Mobile"

    return "🧠 Tech Geral"

# ==============================
# HYPE SCORE (2.0)
# ==============================
def hype_score(title: str, source: str) -> int:
    t = title.lower()
    s = source.lower()

    score = 0

    # base por keywords
    for kw, w in HYPE_KEYWORDS.items():
        if kw in t:
            score += w

    # bônus por termos “fortes”
    for term, w in BOOST_TERMS.items():
        if term in t:
            score += w

    # penalidade por rumor/clickbait
    for term, w in PENALTY_TERMS.items():
        if term in t:
            score -= w

    # bônus por fonte
    for src, w in SOURCE_BONUS.items():
        if src in s:
            score += w

    # nunca negativo
    return max(score, 0)

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

            if is_blocked(title):
                continue

            link = clean_url(link)
            ts = entry_timestamp(entry)
            category = categorize(title, source_name)
            score = hype_score(title, source_name)

            item = {
                "title": title,
                "link": link,
                "score": score,
                "ts": ts,
                "category": category,
                "source": source_name,
            }

            grouped[category].append(item)
            all_items.append(item)

    if not all_items:
        send_message("Hoje não consegui puxar notícias (ou tudo caiu no filtro).")
        return

    # Ordenação geral
    all_sorted = sorted(all_items, key=lambda x: (-x["score"], -x["ts"]))
    top3 = all_sorted[:TOP3_COUNT]
    top3_links = {it["link"] for it in top3}

    # ALERTA DE HYPE (curto)
    hype_hits = [it for it in all_items if it["score"] >= HYPE_ALERT_THRESHOLD]
    if hype_hits:
        hype_hits.sort(key=lambda x: (-x["score"], -x["ts"]))
        alert_lines = ["<b>🚨 ALERTA DE HYPE</b>\n"]
        for it in hype_hits[:3]:
            titulo_pt = traduzir_ptbr(it["title"])
            alert_lines.append(link_line(titulo_pt, it["link"]))
        send_message("\n".join(alert_lines).strip())

    # Seleção limitada por categoria
    selected_by_cat = defaultdict(list)
    remaining = MAX_AFTER_TOP3

    for cat in CATEGORY_ORDER:
        if remaining <= 0:
            break

        items = [it for it in grouped.get(cat, []) if it["link"] not in top3_links]
        items.sort(key=lambda x: (-x["score"], -x["ts"]))

        cap = CATEGORY_CAPS.get(cat, 2)
        take = min(cap, remaining, len(items))
        if take > 0:
            selected_by_cat[cat].extend(items[:take])
            remaining -= take

    # Mensagem principal compacta
    lines = ["<b>📰 Tech + Games do Dia (PT-BR)</b>\n"]

    lines.append("<b>🔥 TOP 3 DO DIA</b>")
    for i, it in enumerate(top3, start=1):
        titulo_pt = traduzir_ptbr(it["title"])
        lines.append(f"{i}) {link_line(titulo_pt, it['link'])}")
    lines.append("")

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
