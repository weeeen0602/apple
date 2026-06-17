from __future__ import annotations

import json
import re
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

PAGE_PATH = Path(r"C:/Users/AI_1/Desktop/apple/studio_shell/pages/8_電影搜尋.py")
OUTPUT_PATH = Path(r"C:/Users/AI_1/Desktop/apple/studio_shell/data/movie_posters.json")

SEARCH_URL = "https://www.themoviedb.org/search/movie"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}
PLACEHOLDER = "https://placehold.co/300x450?text=%E6%9A%AB%E7%84%A1%E6%B5%B7%E5%A0%B1"


def load_movies() -> list[dict[str, Any]]:
    ns: dict[str, Any] = {}
    text = PAGE_PATH.read_text(encoding="utf-8")
    prefix = text.split("st.title(")[0]
    exec(prefix, ns)
    return ns["MOVIES"]


def load_existing_results() -> dict[str, dict[str, Any]]:
    if not OUTPUT_PATH.exists():
        return {}
    try:
        data = json.loads(OUTPUT_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    return data if isinstance(data, dict) else {}


def find_tmdb_url(title: str, year: int) -> str | None:
    params = {"query": title, "language": "zh-TW"}
    r = requests.get(SEARCH_URL, params=params, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.select("a.result"):
        href = a.get("href", "")
        if href.startswith("/movie/"):
            full = "https://www.themoviedb.org" + href.split("?")[0]
            text = a.get_text(" ", strip=True)
            if str(year) in text or title in text:
                return full
    match = re.search(r'href="(/movie/\d+[^"]*)"', r.text)
    if match:
        return "https://www.themoviedb.org" + match.group(1).split("?")[0]
    return None


def extract_poster(page_url: str) -> str | None:
    r = requests.get(page_url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "w300_and_h450_face" in src or "w220_and_h330_face" in src:
            return src
    m = re.search(r"https://media\.themoviedb\.org/t/p/w300_and_h450_face/[A-Za-z0-9._-]+", r.text)
    if m:
        return m.group(0)
    return None


def main() -> None:
    movies = load_movies()
    existing_results = load_existing_results()
    results: dict[str, dict[str, Any]] = {}
    session = requests.Session()
    session.headers.update(HEADERS)

    for idx, movie in enumerate(movies, start=1):
        title = movie["title"]
        year = movie["year"]
        existing = existing_results.get(title, {})
        poster = PLACEHOLDER
        source = None
        status = "placeholder"
        duration = existing.get("duration")
        try:
            search_params = {"query": title, "language": "zh-TW"}
            r = session.get(SEARCH_URL, params=search_params, timeout=20)
            r.raise_for_status()
            soup = BeautifulSoup(r.text, "html.parser")
            url = None
            for a in soup.select("a.result"):
                href = a.get("href", "")
                if href.startswith("/movie/"):
                    full = "https://www.themoviedb.org" + href.split("?")[0]
                    text = a.get_text(" ", strip=True)
                    if str(year) in text or title in text:
                        url = full
                        break
            if not url:
                m = re.search(r'href="(/movie/\d+[^"]*)"', r.text)
                if m:
                    url = "https://www.themoviedb.org" + m.group(1).split("?")[0]
            if url:
                rp = session.get(url, timeout=20)
                rp.raise_for_status()
                soup2 = BeautifulSoup(rp.text, "html.parser")
                found = None
                for img in soup2.find_all("img"):
                    src = img.get("src", "")
                    if "w300_and_h450_face" in src or "w220_and_h330_face" in src:
                        found = src
                        break
                if not found:
                    m2 = re.search(r"https://media\.themoviedb\.org/t/p/w300_and_h450_face/[A-Za-z0-9._-]+", rp.text)
                    if m2:
                        found = m2.group(0)
                if found:
                    poster = found
                    source = url
                    status = "found"
        except Exception as e:
            status = f"error: {type(e).__name__}"

        results[title] = {
            "poster": poster,
            "source": source,
            "status": status,
            "year": year,
            "genre": movie["genre"],
        }
        if isinstance(duration, int) and duration > 0:
            results[title]["duration"] = duration
        print(f"[{idx}/{len(movies)}] {title}: {status}")
        time.sleep(0.2)

    OUTPUT_PATH.write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
    found_count = sum(1 for item in results.values() if item["status"] == "found")
    print({"total": len(results), "found": found_count, "placeholder": len(results) - found_count})


if __name__ == "__main__":
    main()
