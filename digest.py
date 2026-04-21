import os
import json
import datetime
import time
import feedparser
import requests

# ─────────────────────────────────────────
# CONFIGURACIÓN DE FUENTES
# ─────────────────────────────────────────

SOURCES = [
    # Internacionales (en inglés)
    {"url": "https://rss.arxiv.org/rss/cs.AI",                                                    "lang": "en", "name": "Arxiv cs.AI"},
    {"url": "https://rss.arxiv.org/rss/cs.LG",                                                    "lang": "en", "name": "Arxiv cs.LG"},
    {"url": "https://www.deeplearning.ai/the-batch/feed/",                                         "lang": "en", "name": "The Batch"},
    {"url": "https://venturebeat.com/category/ai/feed/",                                           "lang": "en", "name": "VentureBeat AI"},
    {"url": "https://www.technologyreview.com/topic/artificial-intelligence/feed",                 "lang": "en", "name": "MIT Tech Review"},
    # Españolas (en español)
    {"url": "https://www.technologyreview.es/feed/",                                               "lang": "es", "name": "MIT Tech Review ES"},
    {"url": "https://www.xataka.com/tag/inteligencia-artificial/feed",                            "lang": "es", "name": "Xataka IA"},
    {"url": "https://hipertextual.com/feed",                                                       "lang": "es", "name": "Hipertextual"},
    {"url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/tecnologia/portada","lang": "es", "name": "El País Tecnología"},
]

MAX_PER_SOURCE = 2
MAX_SEEN_URLS  = 500
SEEN_URLS_FILE = "seen_urls.json"
GROQ_MODEL     = "llama-3.1-8b-instant"


# ─────────────────────────────────────────
# 1. CACHE DE URLs YA VISTAS
# ─────────────────────────────────────────

def load_seen_urls():
    if os.path.exists(SEEN_URLS_FILE):
        with open(SEEN_URLS_FILE, "r", encoding="utf-8") as f:
            return set(json.load(f))
    return set()


def save_seen_urls(seen: set, new_urls: list):
    combined = list(seen) + new_urls
    combined = combined[-MAX_SEEN_URLS:]
    with open(SEEN_URLS_FILE, "w", encoding="utf-8") as f:
        json.dump(combined, f, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────
# 2. FETCH DE RSS
# ─────────────────────────────────────────

def fetch_articles(seen_urls: set) -> list:
    articles = []
    for source in SOURCES:
        try:
            feed = feedparser.parse(source["url"])
            count = 0
            for entry in feed.entries:
                if count >= MAX_PER_SOURCE:
                    break
                url = entry.get("link", "")
                if not url or url in seen_urls:
                    continue
                summary = entry.get("summary", "") or entry.get("description", "")
                summary = summary.replace("<p>", "").replace("</p>", " ").strip()[:400]
                articles.append({
                    "title":  entry.get("title", "Sin título"),
                    "url":    url,
                    "summary": summary,
                    "lang":   source["lang"],
                    "source": source["name"],
                })
                count += 1
        except Exception as e:
            print(f"[WARN] Error al leer {source['name']}: {e}")

    print(f"[INFO] {len(articles)} artículos nuevos encontrados")
    return articles


# ─────────────────────────────────────────
# 3. RESUMEN CON GROQ (UNA SOLA LLAMADA)
# ─────────────────────────────────────────

def build_prompt(articles: list) -> str:
    lines = []
    for i, a in enumerate(articles, 1):
        lines.append(
            f"{i}. [{a['source']} | {a['lang'].upper()}] {a['title']}\n"
            f"   URL: {a['url']}\n"
            f"   Snippet: {a['summary'][:200]}\n"
        )
    articles_text = "\n".join(lines)

    return f"""Eres un editor técnico especializado en inteligencia artificial.
Tienes {len(articles)} artículos de noticias de IA, en inglés (EN) y español (ES).

Tu tarea:
1. Selecciona los 2 más relevantes e impactantes para profesionales de tecnología e IA.
2. Incluye al menos 1 fuentes en español y 1 en inglés entre los elegidos.
3. Escribe TODOS los resúmenes en español, independientemente del idioma original.
4. Cada resumen debe tener 2-3 frases claras y directas.

Devuelve ÚNICAMENTE un JSON válido con este esquema exacto, sin texto adicional:
{{
  "items": [
    {{
      "title": "Título atractivo en español",
      "summary": "Resumen de 2-3 frases en español.",
      "url": "URL original del artículo"
    }}
  ]
}}

Artículos disponibles:
{articles_text}"""


def summarize_with_groq(articles: list) -> list:
    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY no está definida en las variables de entorno")

    prompt = build_prompt(articles)
    url = "https://api.groq.com/openai/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    payload = {
        "model": GROQ_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.3
    }

    response = requests.post(url, json=payload, headers=headers, timeout=60)
    response.raise_for_status()

    raw = response.json()["choices"][0]["message"]["content"].strip()
    print(f"[DEBUG] Respuesta de Groq: {raw[:200]}")
    if not raw:
        raise ValueError("Groq devolvió una respuesta vacía")
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
    raw = raw.strip()

    data = json.loads(raw)
    items = data.get("items", [])
    print(f"[INFO] Groq seleccionó {len(items)} artículos")
    return items


# ─────────────────────────────────────────
# 4. GENERAR HTML
# ─────────────────────────────────────────

def generate_html(items: list):
    today     = datetime.date.today().strftime("%d/%m/%Y")
    today_iso = datetime.date.today().isoformat()

    cards = ""
    for item in items:
        cards += f"""
            <article class="card">
                <h2>{item['title']}</h2>
                <p>{item['summary']}</p>
                <a href="{item['url']}" target="_blank" rel="noopener">Leer más →</a>
            </article>"""

    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="Resumen diario de los avances más importantes en inteligencia artificial">
    <title>🤖 Resumen IA — {today}</title>
    <style>
        *, *::before, *::after {{ box-sizing: border-box; margin: 0; padding: 0; }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: #0f0f1a;
            color: #e0e0e0;
            min-height: 100vh;
            padding: 0 16px 48px;
        }}

        header {{
            max-width: 760px;
            margin: 0 auto;
            padding: 40px 0 24px;
            border-bottom: 1px solid #2a2a3e;
            margin-bottom: 32px;
        }}

        header h1 {{
            font-size: clamp(1.4rem, 4vw, 2rem);
            font-weight: 700;
            color: #ffffff;
            display: flex;
            align-items: center;
            gap: 12px;
        }}

        .badge {{
            font-size: 0.75rem;
            background: #1e3a5f;
            color: #60a5fa;
            padding: 4px 10px;
            border-radius: 20px;
            font-weight: 500;
            white-space: nowrap;
        }}

        .subtitle {{
            margin-top: 8px;
            font-size: 0.9rem;
            color: #6b7280;
        }}

        main {{
            max-width: 760px;
            margin: 0 auto;
            display: flex;
            flex-direction: column;
            gap: 16px;
        }}

        .card {{
            background: #1a1a2e;
            border: 1px solid #2a2a3e;
            border-radius: 14px;
            padding: 24px 28px;
            transition: border-color 0.2s, transform 0.2s;
        }}

        .card:hover {{
            border-color: #4a90d9;
            transform: translateY(-2px);
        }}

        .card h2 {{
            font-size: 1.05rem;
            font-weight: 600;
            color: #ffffff;
            line-height: 1.4;
            margin-bottom: 10px;
        }}

        .card p {{
            font-size: 0.9rem;
            color: #9ca3af;
            line-height: 1.65;
            margin-bottom: 16px;
        }}

        .card a {{
            display: inline-flex;
            align-items: center;
            gap: 6px;
            font-size: 0.85rem;
            font-weight: 500;
            color: #60a5fa;
            text-decoration: none;
            padding: 6px 14px;
            border: 1px solid #1e3a5f;
            border-radius: 6px;
            transition: background 0.2s, color 0.2s;
        }}

        .card a:hover {{
            background: #1e3a5f;
            color: #93c5fd;
        }}

        footer {{
            max-width: 760px;
            margin: 40px auto 0;
            text-align: center;
            font-size: 0.78rem;
            color: #4b5563;
        }}
    </style>
</head>
<body>
    <header>
        <h1>🤖 Resumen IA <span class="badge">{today}</span></h1>
        <p class="subtitle">Los avances más relevantes en inteligencia artificial, seleccionados y resumidos automáticamente</p>
    </header>

    <main>
        {cards}
    </main>

    <footer>
        Generado automáticamente con Groq + Llama 3.1 &middot;
        Fuentes: Arxiv, The Batch, VentureBeat, MIT Tech Review, Xataka, Hipertextual, El País &middot;
        Actualizado cada mañana de lunes a viernes
    </footer>
</body>
</html>"""

    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)
    print(f"[INFO] index.html generado con {len(items)} artículos")


def generate_no_news_html():
    today = datetime.date.today().strftime("%d/%m/%Y")
    html = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <title>Resumen IA — {today}</title>
    <style>
        body {{ font-family: sans-serif; background:#0f0f1a; color:#e0e0e0;
                display:flex; align-items:center; justify-content:center; min-height:100vh; }}
        p {{ font-size:1.2rem; color:#6b7280; }}
    </style>
</head>
<body><p>🤖 No hay artículos nuevos hoy ({today}). Vuelve mañana.</p></body>
</html>"""
    with open("index.html", "w", encoding="utf-8") as f:
        f.write(html)


# ─────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────

def main():
    print("[START] Iniciando bot de resumen de IA")

    seen_urls = load_seen_urls()
    print(f"[INFO] {len(seen_urls)} URLs ya vistas cargadas")

    articles = fetch_articles(seen_urls)

    if not articles:
        print("[INFO] Sin artículos nuevos. Generando página de aviso.")
        generate_no_news_html()
        return

    items = summarize_with_groq(articles)

    if not items:
        print("[WARN] Groq no devolvió artículos.")
        generate_no_news_html()
        return

    generate_html(items)

    new_urls = [a["url"] for a in articles]
    save_seen_urls(seen_urls, new_urls)
    print(f"[INFO] {len(new_urls)} URLs guardadas en {SEEN_URLS_FILE}")
    print("[DONE] Bot finalizado correctamente")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"[ERROR] {e}")
        raise
