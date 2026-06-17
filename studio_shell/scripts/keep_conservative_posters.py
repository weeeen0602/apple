from __future__ import annotations

import json
from pathlib import Path
from typing import Any

PAGE_PATH = Path(r"C:/Users/AI_1/Desktop/apple/studio_shell/pages/8_電影搜尋.py")
POSTER_PATH = Path(r"C:/Users/AI_1/Desktop/apple/studio_shell/data/movie_posters.json")
PLACEHOLDER = "https://placehold.co/300x450?text=%E6%9A%AB%E7%84%A1%E6%B5%B7%E5%A0%B1"


def load_movies() -> list[dict[str, Any]]:
    ns: dict[str, Any] = {"__file__": str(PAGE_PATH)}
    text = PAGE_PATH.read_text(encoding="utf-8")
    prefix = text.split("st.title(")[0]
    exec(prefix, ns)
    return ns["MOVIES"]


def is_conservative(title: str) -> bool:
    if any(mark in title for mark in ["特別場", "加映版", "特映版", "青春版"]):
        return False
    conservative_titles = {
        "緝魂", "角頭外傳：浪流連", "當男人戀愛時", "瀑布", "哭悲", "我沒有談的那場戀愛", "跟你老婆去旅行",
        "月老", "詭扯", "美國女孩", "咒", "少年吔", "哈勇家", "本日公休", "罪後真相", "初戀慢半拍",
        "售命", "童話·世界", "一家子兒咕咕叫", "流麻溝十五號", "關於我和鬼變成家人的那件事", "疫起", "周處除三害",
        "我的麻吉4個鬼", "請問，還有哪裡需要加強", "做工的人 電影版", "黑的教育", "山中森林", "惡女", "還錢",
        "鬼才之道", "愛的噩夢", "青春18x2 通往有你的旅程", "破浪男女", "小子", "老狐狸", "少男少女", "莎莉",
        "我家的事", "夜校女生", "命中註定那頭鵝", "有病才會喜歡你", "夏日最後的祕密", "刺心切骨", "白衣蒼狗",
        "左撇子女孩", "他年她日", "我們意外的勇氣", "獵人兄弟", "沙味", "高山上的熱氣球", "聽見歌 再唱",
        "兜兜風", "修行", "一家之主", "失控謊言", "再說一次我願意", "咒中人", "速命道", "愛是一把槍",
        "成功補習班", "車頂上的玄天上帝", "還魂", "明天比昨天長久", "南方時光", "阿姨", "我在這裡等你", "春行",
        "獨一無二", "晨霧", "昨日之歌", "月光下的我們", "逆風", "風中的信", "夏夜微光", "未完成的告白",
        "霓虹下", "回家的路上", "告別練習", "光的方向", "微光城市", "奶奶的配方", "最後一封家書", "潮聲1949",
        "灰樓", "第九層", "你的副歌", "逆光球場", "慢跑的人", "破門"
    }
    return title in conservative_titles


def main() -> None:
    movies = load_movies()
    posters: dict[str, Any] = json.loads(POSTER_PATH.read_text(encoding="utf-8"))
    movie_titles = {movie["title"] for movie in movies}
    kept = 0
    reset = 0
    for title, info in posters.items():
        if title not in movie_titles:
            continue
        if is_conservative(title):
            kept += 1
            continue
        info["poster"] = PLACEHOLDER
        info["source"] = None
        info["status"] = "placeholder"
        reset += 1
    POSTER_PATH.write_text(json.dumps(posters, ensure_ascii=False, indent=2), encoding="utf-8")
    print({"kept": kept, "reset": reset})


if __name__ == "__main__":
    main()
