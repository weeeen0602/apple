from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

import requests
from bs4 import BeautifulSoup

POSTER_PATH = Path(r"C:/Users/AI_1/Desktop/apple/studio_shell/data/movie_posters.json")
PLACEHOLDER = "https://placehold.co/300x450?text=%E6%9A%AB%E7%84%A1%E6%B5%B7%E5%A0%B1"
SEARCH_URL = "https://www.themoviedb.org/search/movie"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


def candidate_queries(title: str, year: int) -> list[str]:
    base = title.replace("：", " ").replace("·", " ").strip()
    return list(dict.fromkeys([
        title,
        f"{title} {year}",
        base,
        f"{base} {year}",
        title.split("：")[0].strip(),
    ]))


def find_result(session: requests.Session, query: str, year: int) -> str | None:
    r = session.get(SEARCH_URL, params={"query": query, "language": "zh-TW"}, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for a in soup.select("a.result"):
        href = a.get("href", "")
        if not href.startswith("/movie/"):
            continue
        text = a.get_text(" ", strip=True)
        if str(year) in text or query.split()[0] in text:
            return "https://www.themoviedb.org" + href.split("?")[0]
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if href.startswith("/movie/"):
            return "https://www.themoviedb.org" + href.split("?")[0]
    return None


def extract_poster(session: requests.Session, url: str) -> str | None:
    r = session.get(url, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    best = None
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "w300_and_h450_face" in src:
            return src
        if not best and "w220_and_h330_face" in src:
            best = src
    return best


def main() -> None:
    data: dict[str, Any] = json.loads(POSTER_PATH.read_text(encoding="utf-8"))
    pending = [title for title, info in data.items() if info.get("status") != "found"]
    target = pending[: len(pending) // 2]
    session = requests.Session()
    session.headers.update(HEADERS)

    updated = 0
    for idx, title in enumerate(target, start=1):
        info = data[title]
        year = info.get("year")
        found = None
        source = None
        for query in candidate_queries(title, year):
            try:
                url = find_result(session, query, year)
                if not url:
                    continue
                poster = extract_poster(session, url)
                if poster and poster != PLACEHOLDER:
                    found = poster
                    source = url
                    break
            except Exception:
                continue
            finally:
                time.sleep(0.2)
        if found:
            info["poster"] = found
            info["source"] = source
            info["status"] = "found"
            updated += 1
            result = "found"
        else:
            result = "skip"
        print(f"[{idx}/{len(target)}] {title}: {result}")

    POSTER_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    remaining = sum(1 for item in data.values() if item.get("status") != "found")
    found_total = sum(1 for item in data.values() if item.get("status") == "found")
    print({"updated": updated, "found_total": found_total, "remaining": remaining})


if __name__ == "__main__":
    main()
