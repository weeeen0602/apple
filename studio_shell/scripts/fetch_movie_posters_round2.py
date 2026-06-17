from __future__ import annotations

import json
import re
import time
from pathlib import Path
from urllib.parse import quote

import requests
from bs4 import BeautifulSoup

POSTERS_PATH = Path(r"C:/Users/AI_1/Desktop/apple/studio_shell/data/movie_posters.json")
PLACEHOLDER = "https://placehold.co/300x450?text=%E6%9A%AB%E7%84%A1%E6%B5%B7%E5%A0%B1"
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36",
    "Accept-Language": "zh-TW,zh;q=0.9,en;q=0.8",
}
SEARCH_PATTERNS = [
    "{title} 海報",
    "{title} 電影 海報",
    "{title} {year} 海報",
    "{title} movie poster",
    "site:themoviedb.org {title} {year}",
]


def validate_image(url: str) -> bool:
    try:
        r = requests.get(url, headers=HEADERS, timeout=20, stream=True)
        ok = r.status_code == 200 and str(r.headers.get("Content-Type", "")).startswith("image/")
        r.close()
        return ok
    except Exception:
        return False


def search_web(query: str) -> list[str]:
    url = f"https://html.duckduckgo.com/html/?q={quote(query)}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    links = []
    for a in soup.select("a.result__a"):
        href = a.get("href", "")
        if href:
            links.append(href)
    return links[:5]


def extract_tmdb_poster(page_url: str) -> str | None:
    r = requests.get(page_url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")
    for img in soup.find_all("img"):
        src = img.get("src", "")
        if any(key in src for key in ["w300_and_h450_face", "w220_and_h330_face", "original/"]):
            if "themoviedb" in src or "tmdb" in src:
                return src
    patterns = [
        r"https://media\.themoviedb\.org/t/p/w300_and_h450_face/[A-Za-z0-9._-]+",
        r"https://media\.themoviedb\.org/t/p/w220_and_h330_face/[A-Za-z0-9._-]+",
        r"https://image\.tmdb\.org/t/p/original/[A-Za-z0-9._-]+",
    ]
    for pattern in patterns:
        m = re.search(pattern, r.text)
        if m:
            return m.group(0)
    return None


def extract_generic_image(page_url: str) -> str | None:
    try:
        r = requests.get(page_url, headers=HEADERS, timeout=20)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
        for meta_name in ["og:image", "twitter:image"]:
            meta = soup.find("meta", attrs={"property": meta_name}) or soup.find("meta", attrs={"name": meta_name})
            if meta and meta.get("content"):
                img = meta.get("content")
                if validate_image(img):
                    return img
    except Exception:
        return None
    return None


def main() -> None:
    posters = json.loads(POSTERS_PATH.read_text(encoding="utf-8"))
    pending = [(title, info) for title, info in posters.items() if info.get("status") != "found"]
    recovered = 0

    for idx, (title, info) in enumerate(pending, start=1):
        year = info.get("year", "")
        found_url = None
        found_source = None
        status = info.get("status", "placeholder")

        print(f"[{idx}/{len(pending)}] searching: {title}")

        for pattern in SEARCH_PATTERNS:
            query = pattern.format(title=title, year=year)
            try:
                links = search_web(query)
            except Exception:
                links = []

            for link in links:
                try:
                    if "themoviedb.org" in link:
                        poster = extract_tmdb_poster(link)
                    else:
                        poster = extract_generic_image(link)
                    if poster and validate_image(poster):
                        found_url = poster
                        found_source = link
                        break
                except Exception:
                    continue
            if found_url:
                break
            time.sleep(0.2)

        if found_url:
            posters[title]["poster"] = found_url
            posters[title]["source"] = found_source
            posters[title]["status"] = "found_round2"
            recovered += 1
            print(f"  recovered: {title}")
        else:
            posters[title]["poster"] = posters[title].get("poster", PLACEHOLDER) or PLACEHOLDER
            posters[title]["status"] = status
            print(f"  still missing: {title}")

        time.sleep(0.3)

    POSTERS_PATH.write_text(json.dumps(posters, ensure_ascii=False, indent=2), encoding="utf-8")
    print({"pending": len(pending), "recovered": recovered, "remaining": len(pending) - recovered})


if __name__ == "__main__":
    main()
