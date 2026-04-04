import os
import datetime
import json
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from dotenv import load_dotenv
import httpx
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from cachetools import TTLCache

load_dotenv()

# --- НАСТРОЙКИ ЗАЩИТЫ ---
USER_RATE_LIMIT = "20/minute"  # Лимит для одного IP
CACHE_TTL = 60  # Время жизни кэша (1 минута)
CACHE_SIZE = 100  # Макс. кол-во записей в кэше
# ------------------------

# Инициализация лимитера
limiter = Limiter(key_func=get_remote_address)
app = FastAPI()
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Инициализация кэша в оперативной памяти
data_cache = TTLCache(maxsize=CACHE_SIZE, ttl=CACHE_TTL)

API_TOKEN = os.getenv("PANDASCORE_TOKEN")
BASE_URL = "https://api.pandascore.co"
UTC_OFFSET = int(os.getenv("UTC_OFFSET", 3))

GAME_COLORS = {
    "dota-2": "#ff4444", "cs-go": "#de9b35", "league-of-legends": "#c89b3c",
    "valorant": "#ff4655", "overwatch": "#ff9800", "default": "#bb86fc"
}

SEO_CONFIG = {
    "yesterday": {"title": "Результаты вчерашних матчей",
                  "description": "Архив прошедших киберспортивных матчей и результаты."},
    "today": {"title": "Киберспорт сегодня: Расписание и счет LIVE",
              "description": "Прямые трансляции и актуальный счет текущих матчей."},
    "tomorrow": {"title": "Расписание матчей на завтра",
                 "description": "Анонсы и время начала предстоящих киберспортивных встреч."}
}


async def get_data(day: str):
    if day in data_cache:
        return data_cache[day]

    delta = {"yesterday": -1, "today": 0, "tomorrow": 1}.get(day, 0)
    target = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=delta)
    start = target.replace(hour=0, minute=0, second=0).isoformat().replace("+00:00", "Z")
    end = target.replace(hour=23, minute=59, second=59).isoformat().replace("+00:00", "Z")

    headers = {"Authorization": f"Bearer {API_TOKEN}", "Accept": "application/json"}
    params = {"range[begin_at]": f"{start},{end}", "sort": "begin_at", "per_page": 50}

    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(f"{BASE_URL}/matches", headers=headers, params=params)
            data = resp.json() if resp.status_code == 200 else []
            data_cache[day] = data
            return data
        except:
            return []


def build_html(day: str, data: list):
    seo = SEO_CONFIG[day]
    styles = """
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: -apple-system, sans-serif; background: #0f0f0f; color: #fff; padding: 20px; }
    .container { max-width: 700px; margin: 0 auto; }
    nav { display: flex; justify-content: center; gap: 15px; margin-bottom: 30px; border-bottom: 1px solid #222; padding-bottom: 15px; }
    nav a { color: #666; text-decoration: none; font-size: 13px; font-weight: 600; text-transform: uppercase; }
    nav a.active { color: #bb86fc; }
    .match-card { background: #161616; border-radius: 8px; padding: 20px; margin-bottom: 15px; border: 1px solid #222; }
    .match-header { display: flex; justify-content: space-between; font-size: 11px; color: #555; margin-bottom: 5px; text-transform: uppercase; letter-spacing: 0.5px; }
    .match-datetime { font-size: 12px; color: #888; margin-bottom: 15px; display: block; border-bottom: 1px solid #222; padding-bottom: 8px; }
    .teams { display: flex; justify-content: space-between; align-items: center; gap: 10px; }
    .team { flex: 1; display: flex; align-items: center; gap: 12px; font-weight: 600; font-size: 15px; overflow: hidden; }
    .team-right { flex-direction: row-reverse; text-align: right; }
    .team-icon { 
        width: 36px; height: 36px; border-radius: 50%; display: flex; 
        align-items: center; justify-content: center; font-size: 18px; 
        color: #000; font-weight: 800; flex-shrink: 0; 
    }
    .score { font-size: 22px; font-weight: 800; min-width: 70px; text-align: center; color: #fff; font-family: monospace; }
    .status-running { color: #ff4b4b; font-weight: bold; }
    footer { text-align: center; font-size: 10px; color: #333; margin-top: 40px; text-transform: uppercase; }
    """

    cards = ""
    for m in data:
        opps = m.get('opponents', [])
        t1 = opps[0]['opponent'] if len(opps) > 0 else None
        t2 = opps[1]['opponent'] if len(opps) > 1 else None

        t1_name = t1['name'] if t1 else "TBD"
        t2_name = t2['name'] if t2 else "TBD"

        # Безопасное извлечение счета
        res_map = {r['team_id']: r['score'] for r in m.get('results', []) if 'team_id' in r}
        score1 = res_map.get(t1['id'], 0) if t1 else 0
        score2 = res_map.get(t2['id'], 0) if t2 else 0

        g_slug = m.get('videogame', {}).get('slug', 'default')
        color = GAME_COLORS.get(g_slug, GAME_COLORS['default'])

        begin_at = m.get('begin_at')
        date_str, time_str = "TBD", ""
        if begin_at:
            dt = datetime.datetime.fromisoformat(begin_at.replace('Z', '+00:00')) + datetime.timedelta(hours=UTC_OFFSET)
            date_str = dt.strftime("%d.%m.%Y")
            time_str = dt.strftime("%H:%M")

        status_text = "LIVE" if m['status'] == 'running' else ("ЗАВЕРШЕН" if m['status'] == 'finished' else "ОЖИДАЕТСЯ")

        cards += f"""
        <div class="match-card">
            <div class="match-header">
                <span>{m.get('videogame', {}).get('name')} | {m.get('league', {}).get('name')}</span>
                <span class="status-{m['status']}">{status_text}</span>
            </div>
            <span class="match-datetime">📅 {date_str} &nbsp; ⏰ {time_str} (UTC+{UTC_OFFSET})</span>
            <div class="teams">
                <div class="team">
                    <div class="team-icon" style="background:{color}">{t1_name[0].upper()}</div>
                    <span>{t1_name}</span>
                </div>
                <div class="score">{score1} : {score2}</div>
                <div class="team team-right">
                    <div class="team-icon" style="background:{color}">{t2_name[0].upper()}</div>
                    <span>{t2_name}</span>
                </div>
            </div>
        </div>
        """

    schema_org = {
        "@context": "https://schema.org",
        "@type": "ItemList",
        "name": seo['title'],
        "description": seo['description'],
        "numberOfItems": len(data)
    }

    return f"""
    <!DOCTYPE html>
    <html lang="ru">
    <head>
        <meta charset="UTF-8">
        <title>{seo['title']}</title>
        <meta name="description" content="{seo['description']}">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <script type="application/ld+json">{json.dumps(schema_org)}</script>
        <style>{styles}</style>
    </head>
    <body>
        <div class="container">
            <nav>
                <a href="/yesterday" class="{'active' if day == 'yesterday' else ''}">Вчера</a>
                <a href="/today" class="{'active' if day == 'today' else ''}">Сегодня</a>
                <a href="/tomorrow" class="{'active' if day == 'tomorrow' else ''}">Завтра</a>
            </nav>
            <main>{cards if data else '<p style="text-align:center; color:#333; margin-top:50px;">Матчей не найдено</p>'}</main>
            <footer>{datetime.datetime.now().year} ESPORTS TRACKER</footer>
        </div>
    </body>
    </html>
    """


@app.get("/", response_class=HTMLResponse)
@app.get("/today", response_class=HTMLResponse)
@limiter.limit(USER_RATE_LIMIT)
async def page_today(request: Request):
    return build_html("today", await get_data("today"))


@app.get("/yesterday", response_class=HTMLResponse)
@limiter.limit(USER_RATE_LIMIT)
async def page_yesterday(request: Request):
    return build_html("yesterday", await get_data("yesterday"))


@app.get("/tomorrow", response_class=HTMLResponse)
@limiter.limit(USER_RATE_LIMIT)
async def page_tomorrow(request: Request):
    return build_html("tomorrow", await get_data("tomorrow"))


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
