from __future__ import annotations

import json
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup

POSTER_PATH = Path(r"C:/Users/AI_1/Desktop/apple/studio_shell/data/movie_posters.json")
PLACEHOLDER = "https://placehold.co/300x450?text=%E6%9A%AB%E7%84%A1%E6%B5%B7%E5%A0%B1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}


def search_tmdb(title: str, year: int) -> str | None:
    queries = [
        f"site:themoviedb.org/movie {title} {year}",
        f"site:themoviedb.org/movie {title} 電影",
        f"site:themoviedb.org/movie {title}",
    ]
    for q in queries:
        url = f"https://www.google.com/search?q={requests.utils.quote(q)}"
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code != 200:
            continue
        matches = re.findall(r"https://www\.themoviedb\.org/movie/\d+", r.text)
        if matches:
            return matches[0]
    return None


def extract_poster(url: str) -> str | None:
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    candidates = []
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if "themoviedb.org/t/p" in src or "media.themoviedb.org/t/p" in src:
            if any(size in src for size in ["w300_and_h450_face", "w220_and_h330_face", "original"]):
                candidates.append(src)
    for src in candidates:
        if "w300_and_h450_face" in src:
            return src
    if candidates:
        return candidates[0]
    m = re.search(r"https://media\.themoviedb\.org/t/p/w300_and_h450_face/[A-Za-z0-9._-]+", r.text)
    if m:
        return m.group(0)
    return None


def main() -> None:
    data = json.loads(POSTER_PATH.read_text(encoding="utf-8"))
    remaining = [(title, info) for title, info in data.items() if info.get("status") != "found"]
    improved = 0

    for idx, (title, info) in enumerate(remaining, start=1):
        year = info.get("year")
        print(f"[{idx}/{len(remaining)}] {title}")
        try:
            tmdb_url = search_tmdb(title, year)
            if tmdb_url:
                poster = extract_poster(tmdb_url)
                if poster and poster != PLACEHOLDER:
                    info["poster"] = poster
                    info["source"] = tmdb_url
                    info["status"] = "found"
                    improved += 1
                    print(f"  -> found {poster}")
                else:
                    print("  -> no poster on page")
            else:
                print("  -> no tmdb match")
        except Exception as e:
            print(f"  -> error {type(e).__name__}: {e}")
        time.sleep(0.3)

    POSTER_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    print({"improved": improved, "remaining": sum(1 for v in data.values() if v.get('status') != 'found')})


if __name__ == "__main__":
    main()
