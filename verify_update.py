from studio_shell.scripts.update_movies_from_in89 import load_movies_from_page, load_poster_map
movies = load_movies_from_page()
print(f'MOVIES 總數: {len(movies)}')
print('最後 12 部:')
for m in movies[-12:]:
    title = m.get('title', '')
    year = m.get('year', '')
    genre = m.get('genre', '')
    print(f'  - {title} ({year}, {genre})')
print()
posters = load_poster_map()
print(f'poster map 總數: {len(posters)}')
print('新增的 posters:')
for title in ['名偵探柯南 高速公路的墮天使', '美夢', '穿著Prada的惡魔2', '後室']:
    if title in posters:
        p = posters[title]
        poster_url = p.get('poster', '')
        print(f'  - {title}:')
        print(f'      poster: {poster_url[:80]}')
        print(f'      status: {p.get("status")}')
        print(f'      year: {p.get("year")}, genre: {p.get("genre")}')