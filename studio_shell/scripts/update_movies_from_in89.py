from __future__ import annotations

import json
import re
import time
from datetime import datetime
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

# ---------------------------------------------------------------------------
# 路徑與 URL
# ---------------------------------------------------------------------------
PAGE_PATH = Path(r"C:/Users/AI_1/Desktop/apple/studio_shell/pages/8_電影搜尋.py")
POSTER_PATH = Path(r"C:/Users/AI_1/Desktop/apple/studio_shell/data/movie_posters.json")
IN89_URL = "https://www.in89cinemax.com/film_list.aspx?TheaterId=2&type=Hot"
TMDB_SEARCH_URL = "https://www.themoviedb.org/search/movie"
PLACEHOLDER = "https://placehold.co/300x450?text=%E6%9A%AB%E7%84%A1%E6%B5%B7%E5%A0%B1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}

DEFAULT_YEAR = datetime.now().year
DEFAULT_GENRE = "其他"
DEFAULT_INTRO = ""

# ---------------------------------------------------------------------------
# 載入現有資料
# ---------------------------------------------------------------------------

def load_movies_from_page() -> list[dict[str, Any]]:
    """從 8_電影搜尋.py 的 MOVIES = [...] 區塊解析電影資料。"""
    text = PAGE_PATH.read_text(encoding="utf-8")

    # 定位 MOVIES = [ ... ] 的完整 JSON-like 區段
    start_match = re.search(r"\bMOVIES\s*=\s*\[", text)
    if not start_match:
        return []
    start = start_match.end() - 1  # 指向 '['

    bracket_depth = 0
    end = start
    for i, ch in enumerate(text[start:], start=start):
        if ch == "[":
            bracket_depth += 1
        elif ch == "]":
            bracket_depth -= 1
            if bracket_depth == 0:
                end = i + 1
                break

    movies_literal = text[start:end]
    # 把單引號轉雙引號、移除結尾逗號，使其成為合法 JSON
    movies_literal = movies_literal.replace("'", '"')
    movies_literal = re.sub(r",(\s*\])", r"\1", movies_literal)
    try:
        return json.loads(movies_literal)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"無法解析 8_電影搜尋.py 的 MOVIES 清單：{e}") from e


def load_poster_map() -> dict[str, dict[str, Any]]:
    if not POSTER_PATH.exists():
        return {}
    try:
        data = json.loads(POSTER_PATH.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else {}
    except (json.JSONDecodeError, OSError):
        return {}


# ---------------------------------------------------------------------------
# in89：抓現正熱映片名
# ---------------------------------------------------------------------------

def fetch_in89_movies(url: str = IN89_URL, timeout: int = 60) -> list[dict[str, Any]]:
    """從 in89 駁二電影院現正熱映頁面抓所有電影資料。

    使用 Playwright 渲染 Vue.js 動態頁面，回傳每部片的：
    - cn_name: 中文片名
    - en_name: 英文片名
    - version: 版本（如 2D數位英語）
    - runtime: 片長（分鐘）
    - rating: 分級
    - release: 上映日期 (YYYY-MM-DD)
    - img: 海報圖片 URL
    - href: 電影詳情頁 URL
    """
    if not HAS_PLAYWRIGHT:
        raise RuntimeError("需要安裝 playwright：uv pip install playwright && playwright install chromium")

    movies: list[dict[str, Any]] = []
    seen: set[str] = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        try:
            page = browser.new_page()
            page.goto(url, timeout=timeout * 1000, wait_until="domcontentloaded")
            # 等 Vue 渲染完成
            time.sleep(5)

            raw = page.eval_on_selector_all(
                ".movie_info",
                """els => els.map(el => {
                    const ps = el.querySelectorAll('p');
                    return {
                        cn_name: ps[0]?.textContent?.trim() || '',
                        en_name: ps[1]?.textContent?.trim() || '',
                        version: ps[2]?.textContent?.trim() || '',
                        runtime: ps[3]?.textContent?.trim() || '',
                        rating: ps[4]?.textContent?.trim() || '',
                        release: ps[5]?.textContent?.trim() || '',
                        img: el.querySelector('img')?.src || '',
                        href: el.querySelector('a')?.href || '',
                    };
                })""",
            )

            for m in raw:
                cn = m.get("cn_name", "")
                if cn and cn not in seen:
                    # 解析上映日期
                    release_text = m.get("release", "")
                    release_date = ""
                    if "上映日期" in release_text:
                        release_date = release_text.split(":")[-1].strip()
                    # 解析片長
                    runtime_text = m.get("runtime", "")
                    runtime_min = 0
                    if "片長" in runtime_text or "片  長" in runtime_text:
                        nums = re.findall(r"\d+", runtime_text)
                        if nums:
                            runtime_min = int(nums[0])
                    # 解析分級
                    rating_text = m.get("rating", "")
                    rating = ""
                    if "分級" in rating_text or "分  級" in rating_text:
                        rating = rating_text.split(":")[-1].strip()

                    movies.append({
                        "cn_name": cn,
                        "en_name": m.get("en_name", ""),
                        "version": m.get("version", ""),
                        "runtime": runtime_min,
                        "rating": rating,
                        "release_date": release_date,
                        "img": m.get("img", ""),
                        "href": m.get("href", ""),
                    })
                    seen.add(cn)
        finally:
            browser.close()

    return movies


def fetch_in89_titles(url: str = IN89_URL, timeout: int = 60) -> list[str]:
    """從 in89 抓片名列表（向後相容介面）。"""
    movies = fetch_in89_movies(url, timeout)
    return [m["cn_name"] for m in movies]


# ---------------------------------------------------------------------------
# TMDB：搜尋與抓 metadata
# ---------------------------------------------------------------------------

def _candidate_queries(title: str, year: int | None = None) -> list[str]:
    base = title.replace("：", " ").replace("·", " ").strip()
    short = title.split("：")[0].strip()
    queries = [title, base, short]
    if year:
        queries.extend([f"{title} {year}", f"{base} {year}", f"{short} {year}"])
    return list(dict.fromkeys(q for q in queries if q))


def _find_tmdb_result(
    session: requests.Session, query: str, year: int | None = None
) -> str | None:
    r = session.get(
        TMDB_SEARCH_URL, params={"query": query, "language": "zh-TW"}, timeout=20
    )
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    for a in soup.select("a.result"):
        href = a.get("href", "")
        if not href.startswith("/movie/"):
            continue
        text = a.get_text(" ", strip=True)
        if year and str(year) in text:
            return "https://www.themoviedb.org" + href.split("?")[0]
        if query.split()[0] in text:
            return "https://www.themoviedb.org" + href.split("?")[0]

    # fallback：抓第一個 /movie/ 連結
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/movie/"):
            return "https://www.themoviedb.org" + href.split("?")[0]
    return None


def _extract_year(text: str) -> int | None:
    """從文字中抓四碼年份，例如 '(2024)'。"""
    m = re.search(r"\b(\d{4})\b", text)
    if m:
        year = int(m.group(1))
        if 1900 <= year <= DEFAULT_YEAR + 2:
            return year
    return None


def _extract_genres(soup: BeautifulSoup) -> list[str]:
    """從 TMDB 詳情頁抓類型標籤，回傳中文名稱列表。"""
    genres: list[str] = []
    # TMDB 中文頁的類型通常在 a[href*="/genre/"] 裡
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "/genre/" in href:
            text = a.get_text(strip=True)
            if text and text not in genres:
                genres.append(text)
    return genres


def _map_tmdb_genre_to_local(tmdb_genres: list[str]) -> str:
    """把 TMDB 中文類型對應到本地 genre；對不上的回傳 DEFAULT_GENRE。"""
    priority = [
        ("恐怖", "恐怖"),
        ("驚悚", "驚悚"),
        ("懸疑", "懸疑"),
        ("愛情", "愛情"),
        ("劇情", "劇情"),
        ("喜劇", "喜劇"),
        ("動作", "動作"),
        ("犯罪", "犯罪"),
        ("科幻", "科幻"),
        ("奇幻", "奇幻"),
        ("動畫", "動畫"),
        ("家庭", "家庭"),
        ("溫馨", "劇情"),  # TMDB 沒有「溫馨」，歸到劇情
        ("紀錄片", "劇情"),
        ("歷史", "歷史"),
        ("戰爭", "動作"),
        ("音樂", "劇情"),
    ]
    for keyword, local in priority:
        if keyword in tmdb_genres:
            return local
    return DEFAULT_GENRE


def _extract_intro(soup: BeautifulSoup) -> str:
    """從 TMDB 詳情頁抓中文劇情簡介。"""
    # 常見的 overview 容器
    for selector in ["div.overview p", "p[data-testid='plot']", "div.overview"]:
        tag = soup.select_one(selector)
        if tag:
            text = tag.get_text(strip=True)
            if text:
                return text
    return ""


def _extract_poster_url(soup: BeautifulSoup) -> str | None:
    """從 TMDB 詳情頁抓 w300_and_h450_face 海報 URL。"""
    best: str | None = None
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "w300_and_h450_face" in src:
            return src
        if not best and "w220_and_h330_face" in src:
            best = src
    m = re.search(
        r"https://media\.themoviedb\.org/t/p/w300_and_h450_face/[A-Za-z0-9._-]+",
        str(soup),
    )
    if m:
        return m.group(0)
    return best


def enrich_movie_from_tmdb(title: str) -> dict[str, Any]:
    """對單一片名到 TMDB 搜尋並補齊 year / genre / intro / poster。"""
    session = requests.Session()
    session.headers.update(HEADERS)

    result = {
        "title": title,
        "year": DEFAULT_YEAR,
        "genre": DEFAULT_GENRE,
        "intro": DEFAULT_INTRO,
        "poster": PLACEHOLDER,
        "source": None,
        "status": "placeholder",
    }

    try:
        page_url: str | None = None
        for query in _candidate_queries(title):
            page_url = _find_tmdb_result(session, query)
            if page_url:
                break
            time.sleep(0.2)

        if not page_url:
            return result

        r = session.get(page_url, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # year：優先從搜尋結果標題抓，其次頁面文字
        year = _extract_year(soup.get_text(" ", strip=True))
        if year:
            result["year"] = year

        # genre
        tmdb_genres = _extract_genres(soup)
        if tmdb_genres:
            result["genre"] = _map_tmdb_genre_to_local(tmdb_genres)

        # intro
        intro = _extract_intro(soup)
        if intro:
            result["intro"] = intro

        # poster
        poster = _extract_poster_url(soup)
        if poster:
            result["poster"] = poster
            result["source"] = page_url
            result["status"] = "found"
        else:
            result["source"] = page_url

    except Exception as e:
        result["status"] = f"error: {type(e).__name__}"

    return result


# ---------------------------------------------------------------------------
# 寫回本地檔案
# ---------------------------------------------------------------------------

def _format_movie_dict(movie: dict[str, Any]) -> str:
    """把單一電影 dict 格式化成與 8_電影搜尋.py 一致的縮排字串。"""
    title = json.dumps(movie["title"], ensure_ascii=False)
    genre = json.dumps(movie["genre"], ensure_ascii=False)
    year = movie["year"]
    intro = json.dumps(movie["intro"], ensure_ascii=False)
    return f'    {{"title": {title}, "genre": {genre}, "year": {year}, "intro": {intro}}},'


def append_movies_to_page(new_movies: list[dict[str, Any]]) -> None:
    """把新電影 dict 插入 8_電影搜尋.py 的 MOVIES 清單尾端。"""
    if not new_movies:
        return

    text = PAGE_PATH.read_text(encoding="utf-8")

    # 找到 MOVIES = [ ... ] 的最後一個 ']'（在 render_main 之前）
    # 安全做法：定位最後一個 movie dict 後面的 '\n]\n\n# 或\ndef '
    match = re.search(r"(\n\])", text)
    if not match:
        raise RuntimeError("無法在 8_電影搜尋.py 找到 MOVIES 清單結尾 ]")

    insert_at = match.start()
    new_lines = "\n" + "\n".join(_format_movie_dict(m) for m in new_movies)
    new_text = text[:insert_at] + new_lines + text[insert_at:]
    PAGE_PATH.write_text(new_text, encoding="utf-8")


def update_poster_map(
    poster_map: dict[str, dict[str, Any]], enriched: list[dict[str, Any]]
) -> None:
    for movie in enriched:
        entry: dict[str, Any] = {
            "poster": movie.get("poster", PLACEHOLDER),
            "source": movie.get("source"),
            "status": movie.get("status", "placeholder"),
            "year": movie.get("year", DEFAULT_YEAR),
            "genre": movie.get("genre", DEFAULT_GENRE),
        }
        poster_map[movie["title"]] = entry


# ---------------------------------------------------------------------------
# 主流程
# ---------------------------------------------------------------------------

def update_from_in89(*, dry_run: bool = False) -> dict[str, Any]:
    """
    從 in89 抓現正熱映片單（含 metadata），對本地沒有的電影到 TMDB 補齊
    genre / intro，最後寫回 8_電影搜尋.py 與 movie_posters.json。
    回傳統計資訊 dict。
    """
    in89_movies = fetch_in89_movies()
    existing_titles = {m["title"] for m in load_movies_from_page()}
    new_movies = [m for m in in89_movies if m["cn_name"] not in existing_titles]

    if not new_movies:
        return {
            "in89_count": len(in89_movies),
            "new_count": 0,
            "added": [],
            "errors": [],
        }

    enriched: list[dict[str, Any]] = []
    errors: list[str] = []
    for m in new_movies:
        title = m["cn_name"]
        # 從 in89 已有資料建立基礎
        year = DEFAULT_YEAR
        if m.get("release_date"):
            try:
                year = int(m["release_date"][:4])
            except (ValueError, IndexError):
                pass

        info = {
            "title": title,
            "year": year,
            "genre": DEFAULT_GENRE,
            "intro": DEFAULT_INTRO,
            "poster": m.get("img") or PLACEHOLDER,
            "source": m.get("href") or "in89",
            "status": "in89",
            "runtime": m.get("runtime", 0),
            "rating": m.get("rating", ""),
            "version": m.get("version", ""),
        }

        # 用 TMDB 補 genre / intro（in89 沒提供）
        try:
            tmdb_info = enrich_movie_from_tmdb(title)
            if tmdb_info["genre"] != DEFAULT_GENRE:
                info["genre"] = tmdb_info["genre"]
            if tmdb_info["intro"]:
                info["intro"] = tmdb_info["intro"]
            if tmdb_info["status"].startswith("error:"):
                errors.append(f"{title}: {tmdb_info['status']}")
        except Exception as e:
            errors.append(f"{title}: {type(e).__name__}: {e}")

        enriched.append(info)
        time.sleep(0.2)

    if not dry_run:
        # 寫回 MOVIES 清單
        movies_to_append = [
            {
                "title": m["title"],
                "genre": m["genre"],
                "year": m["year"],
                "intro": m["intro"],
            }
            for m in enriched
        ]
        append_movies_to_page(movies_to_append)

        # 寫回 movie_posters.json
        poster_map = load_poster_map()
        update_poster_map(poster_map, enriched)
        POSTER_PATH.write_text(
            json.dumps(poster_map, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return {
        "in89_count": len(in89_movies),
        "new_count": len(enriched),
        "added": [m["title"] for m in enriched],
        "errors": errors,
    }


def main() -> None:
    stats = update_from_in89()
    print(stats)


if __name__ == "__main__":
    main()
