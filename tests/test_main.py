import pytest
from httpx import AsyncClient, ASGITransport
import respx
from main import app, BASE_URL


@pytest.mark.asyncio
async def test_html_structure_unit():
    """Юнит-тест: Проверка корректности генерации HTML структуры"""
    from main import build_html

    test_data = [{"status": "finished", "opponents": [], "videogame": {"name": "Dota 2"}}]
    html = build_html("today", test_data)

    assert "<title>Киберспорт сегодня" in html
    assert "ESPORTS TRACKER" in html
    assert "Dota 2" in html
    assert 'class="active"' in html


@respx.mock
@pytest.mark.asyncio
async def test_integration_endpoints():
    """Интеграционный тест: Эндпоинты и работа с API через mock"""

    respx.get(f"{BASE_URL}/matches").respond(
        status_code=200,
        json=[{
            "status": "running",
            "begin_at": "2023-10-10T15:00:00Z",
            "videogame": {"slug": "cs-go", "name": "CS:GO"},
            "league": {"name": "Major"},
            "opponents": [
                {"opponent": {"id": 1, "name": "Team A"}},
                {"opponent": {"id": 2, "name": "Team B"}}
            ],
            "results": [{"team_id": 1, "score": 1}, {"team_id": 2, "score": 0}]
        }]
    )

    # Используем ASGITransport для новых версий httpx
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/")
        assert response.status_code == 200
        assert "Team A" in response.text
        assert "LIVE" in response.text

        response_tomorrow = await ac.get("/tomorrow")
        assert response_tomorrow.status_code == 200
        assert "Расписание матчей на завтра" in response_tomorrow.text


@respx.mock
@pytest.mark.asyncio
async def test_api_error_handling():
    """Тест устойчивости: Если API PandaScore недоступно (500 ошибка)"""
    respx.get(f"{BASE_URL}/matches").respond(status_code=500)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        response = await ac.get("/today")
        assert response.status_code == 200
        assert "Матчей не найдено" in response.text


@pytest.mark.parametrize("day", ["yesterday", "today", "tomorrow"])
def test_seo_config_completeness(day):
    """Юнит-тест: Проверка наличия всех SEO конфигов"""
    from main import SEO_CONFIG
    assert day in SEO_CONFIG
    assert "title" in SEO_CONFIG[day]
    assert len(SEO_CONFIG[day]["description"]) > 10
